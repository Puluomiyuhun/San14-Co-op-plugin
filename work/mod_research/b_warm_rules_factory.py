"""Retained real rules Prepare/Seal factory; import performs no process access.

Caller supplies an already bound GameReader/ProcessAPI and an actual native
fence. No automatic Revoke, unload, process termination, retry or fence release.
"""
from dataclasses import dataclass
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
import shutil
import struct
import subprocess
import threading

from b_warm_rules_capture import RulesWorldCapture
from human_rules_world_lifecycle import Config,Descriptor,ModuleIdentity,ResidentPort,WorldGeneration,check_port
from checkpoint_complete_live_capture import module_approval,readable,process_birth
from checkpoint_live_prefetch_start import invoke

PRODUCTION_STAGE='29d0f6e83531f3892d075b84b632a614bdf485a61293574ba68d590dc2d0e1ac'
PRODUCTION_PUBLISHER='3f321110a79fc751978790fa1b545ffa0bbefba146a3be035f6fcdb272aef2f9'
GAME_SHA='42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
PRODUCTION_COUNTERS=((0x474d,bytes.fromhex('f04c0fb1056290020048898288000000'),0x2d7b8),
                     (0x5582,bytes.fromhex('f04c0fb105c582020048894230'),0x2d850))
EXPORTS=('HumanRulesActivationPrepare','HumanRulesActivationSeal','HumanRulesActivationReadReport',
         'HumanRulesActivationDescriptor','HumanRulesActivationState','HumanRulesActivationBinding')


def need(ok,text):
    if not ok:raise ValueError(text)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_new(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


@dataclass(frozen=True)
class RulesBuild:
    stage: Path
    publisher: Path
    stage_sha: str=PRODUCTION_STAGE
    publisher_sha: str=PRODUCTION_PUBLISHER
    executable_sha: str=GAME_SHA
    counters: tuple=PRODUCTION_COUNTERS
    source_kind: str='LOCAL_NATIVE_PROVIDER'

    def __post_init__(self):
        need(isinstance(self.stage, Path) and isinstance(self.publisher, Path),'Explicit approved paths required')
        need(self.source_kind in ('LOCAL_NATIVE_PROVIDER','OWNED_FIXTURE'),'Unknown build provenance')
        need(all(type(s) is str and len(s)==64 and all(c in '0123456789abcdef' for c in s)
                 for s in (self.stage_sha,self.publisher_sha,self.executable_sha)),'Invalid build hash')
        if self.source_kind=='LOCAL_NATIVE_PROVIDER':
            need((self.stage_sha,self.publisher_sha,self.executable_sha,self.counters)==
                 (PRODUCTION_STAGE,PRODUCTION_PUBLISHER,GAME_SHA,PRODUCTION_COUNTERS),'Unsupported production build')
        need(len(self.counters)==2 and all(type(x) is tuple and len(x)==3 and type(x[0]) is int and x[0]>0 and
             type(x[1]) is bytes and 1<=len(x[1])<=16 and type(x[2]) is int and x[2]>0 for x in self.counters),
             'Exact build-time counter anchors required')
        self.check()

    def check(self):
        need(sha(self.stage)==self.stage_sha and sha(self.publisher)==self.publisher_sha,'Approved rules build changed')


class RulesFactory:
    def __init__(self, capture, api, build, records, *, rulers):
        need(type(capture) is RulesWorldCapture and type(build) is RulesBuild,'Retained typed native capture/build required')
        need(api.reader is capture.reader,'API and capture must share the retained reader')
        self.capture,self.api,self.build=capture,api,build
        self.records=Path(records).resolve(strict=True)
        need(self.records.is_dir(),'Existing private records directory required')
        self.rulers=dict(rulers)
        need(set(self.rulers)==set(capture.scope['bindings'][p]['force_id'] for p in ('A','B')) and
             all(type(x) is int and 0<x<6000 for x in self.rulers.values()),'Exact two viewer/ruler expectations required')
        self.retained=[];self.publishers=[];self.claimed=set();self.failed=None;self.uncertain=False
        self._lock=threading.RLock()
        k=api.k
        k.GetProcessId.argtypes=[W.HANDLE];k.GetProcessId.restype=W.DWORD
        k.GetProcessTimes.argtypes=[W.HANDLE]+[C.c_void_p]*4;k.GetProcessTimes.restype=W.BOOL
        k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];k.QueryFullProcessImageNameW.restype=W.BOOL
        self._identity()

    def _identity(self,module=None):
        need(self.failed is None and not self.uncertain,'Rules factory held; no dependent target call')
        self.build.check();self.capture._check()
        k=self.api.k;handle=self.api.handle
        need(k.GetProcessId(handle)==self.capture.pid,'API process changed')
        times=[C.c_uint64() for _ in range(4)]
        need(k.GetProcessTimes(handle,*(C.byref(x) for x in times)) and times[0].value==self.capture.birth and
             process_birth(self.capture.reader)==self.capture.birth,'Process creation time changed')
        path=C.create_unicode_buffer(32768);size=W.DWORD(len(path))
        need(k.QueryFullProcessImageNameW(handle,0,path,C.byref(size)) and sha(Path(path.value))==self.build.executable_sha,
             'Actual process executable differs from approved build')
        debugged=W.BOOL()
        need(k.CheckRemoteDebuggerPresent(handle,C.byref(debugged)) and not debugged.value,'Debugger still owns process')
        if module is not None:
            row=next((r for r in self.retained if r.get('module')==module.module),None)
            need(row is not None and row['path'].is_file() and sha(row['path'])==self.build.stage_sha,'Resident module file differs')
            matches=[b for b,p in self.api.modules() if p.resolve()==row['path']]
            need(matches==[module.module],'Resident module mapping changed')
            current=module_approval(self.capture.reader,module.module,row['path'],self.build.stage_sha)
            need(current==row['approval'],'Resident PE identity changed')

    def _current(self,world):
        c=Config.from_buffer_copy(world.config)
        return self.capture.export_current(world,expected_ruler=self.rulers[c.viewer])

    def _scope(self,world):
        self.capture._check()
        c=Config.from_buffer_copy(world.config)
        need(c.viewer in self.rulers,'Unknown local viewer')
        # Fresh capture rechecks Room/rules and preserves the actual generation epoch.
        self._current(world)

    def _call(self,row,label,address,payload):
        self._identity()
        save_new(row['folder']/(label+'-intent.json'),dict(address=address,input_sha256=hashlib.sha256(payload).hexdigest(),
            input_size=len(payload),retry=False))
        try:
            result=invoke(self.api,address,payload)
        except BaseException as exc:
            self.uncertain=bool(getattr(exc,'may_have_started',True) and not getattr(exc,'completed',False))
            save_new(row['folder']/(label+'-failure.json'),dict(error=repr(exc),uncertain=self.uncertain,
                thread_id=getattr(exc,'thread_id',None),cleanup_errors=getattr(exc,'cleanup_errors',None)))
            raise
        save_new(row['folder']/(label+'-result.json'),dict(exit=result[0]))
        return result[0]

    def prepare_rules(self,observed):
        with self._lock:
            self._identity()
            need(type(observed) is WorldGeneration and observed.generation not in self.claimed,'Fresh typed generation required')
            need(self._current(observed)==observed.config,'Observed world changed before preparation')
            folder=self.records/('rules-'+str(observed.generation));folder.mkdir()
            row=dict(folder=folder,path=folder/'resident.dll',world=observed,module=None)
            self.retained.append(row);self.claimed.add(observed.generation)
            save_new(folder/'claim.json',dict(pid=self.capture.pid,birth=self.capture.birth,generation=observed.generation,
                checkpoint=observed.checkpoint,config_sha256=hashlib.sha256(observed.config).hexdigest(),automatic_retry=False))
            try:
                import pefile
                with row['path'].open('xb') as out, self.build.stage.open('rb') as inp:shutil.copyfileobj(inp,out)
                need(sha(row['path'])==self.build.stage_sha,'Copied stage differs')
                pe=pefile.PE(str(row['path']))
                try:rvas={e.name.decode():e.address for e in pe.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
                finally:pe.close()
                need(set(EXPORTS)<=set(rvas),'Missing rules exports')
                need(not any(p.resolve()==row['path'] for _,p in self.api.modules()),'Stage already resident before claim')
                # LoadLibraryW returns a DWORD-truncated HMODULE on x64; actual
                # module discovery/PE identity, not this exit value, identifies it.
                self._call(row,'load',self.api.load_library_address(),str(row['path']).encode('utf-16le')+b'\0\0')
                matches=[b for b,p in self.api.modules() if p.resolve()==row['path']]
                need(len(matches)==1,'Fresh loaded module not found')
                module=matches[0];row['module']=module
                row['approval']=module_approval(self.capture.reader,module,row['path'],self.build.stage_sha)
                addresses={n:module+rvas[n] for n in EXPORTS};row['addresses']=addresses
                for name in EXPORTS[:3]:readable(self.capture.reader,addresses[name],32,allocation=module,execute=True)
                need(self._current(observed)==observed.config,'World changed after module load')
                need(self._call(row,'prepare',addresses['HumanRulesActivationPrepare'],observed.config)==0,'Native Prepare rejected; no retry')
                read=self.capture.reader.memory.read
                raw=read(addresses['HumanRulesActivationDescriptor'],C.sizeof(Descriptor))
                d=Descriptor.from_buffer_copy(raw);c=Config.from_buffer_copy(observed.config)
                need(d.magic==0x31544753524C5548 and d.version==1 and d.size==C.sizeof(Descriptor) and
                     (d.pid,d.birth,d.image,d.module)==(self.capture.pid,self.capture.birth,c.image,module) and
                     d.fixture==int(self.build.source_kind=='OWNED_FIXTURE') and d.preparation_state==2 and d.site_count==6 and
                     any(d.nonce) and not d.reserved,'Prepared descriptor identity differs')
                need(read(addresses['HumanRulesActivationBinding'],C.sizeof(Config))==observed.config,'Prepared native binding differs')
                need(self._current(observed)==observed.config,'World changed before Seal')
                seal=struct.pack('<II',1,72)+bytes(d.nonce)+bytes(c.room)+bytes(c.epoch)
                need(self._call(row,'seal',addresses['HumanRulesActivationSeal'],seal)==0,'Native Seal rejected; no retry')
                module_id=ModuleIdentity(self.capture.pid,self.capture.birth,module,addresses['HumanRulesActivationDescriptor'],
                    bytes(d.nonce),self.build.stage_sha,rvas['HumanRulesActivationState'],rvas['HumanRulesActivationBinding'],
                    self.build.counters,self.build.source_kind)
                row['identity']=module_id
                (folder/'config.bin').write_bytes(observed.config)
                port=ResidentPort(observed,module_id,read=read,identity_check=self._identity,
                    publisher=lambda operation:self._publish(row,operation),export_current=self._current,check_scope=self._scope)
                row['port']=port
                witness=port.observe(False)
                save_new(folder/'prepared.json',dict(result='SEALED_NOT_INSTALLED',witness=witness,approval=row['approval'],
                    retained=True,ready=False))
                return port
            except BaseException as exc:
                self.failed=repr(exc)
                save_new(folder/'held.json',dict(error=self.failed,uncertain=self.uncertain,retained=True,
                    revoked=False,unloaded=False,ready=False))
                raise

    def _publish(self,row,operation):
        with self._lock:
            self._identity(row['identity'])
            need(operation in ('install','restore'),'Unknown source operation')
            folder=row['folder'];log=folder/(operation+'-publisher.log')
            need(not log.exists(),'Publication already attempted; no replay')
            need((folder/'config.bin').read_bytes()==row['world'].config,'Publisher Config file changed')
            m=row['identity'];c=Config.from_buffer_copy(row['world'].config)
            args=[str(self.build.publisher),operation,str(m.pid),str(m.birth),str(c.image),str(m.descriptor),
                  str(row['path']),m.nonce.hex(),str(folder/'config.bin')]
            save_new(folder/(operation+'-intent.json'),dict(args=args,automatic_retry=False))
            try:
                with log.open('xb') as output:
                    # Unknown begins before process creation: interruption may
                    # occur after OS success but before assignment/logging.
                    self.uncertain=True
                    child=subprocess.Popen(args,stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                    self.publishers.append(child)
                    save_new(folder/(operation+'-process.json'),dict(pid=child.pid))
                    try:child.wait(timeout=20)
                    except BaseException:
                        self.uncertain=True # retained child may own a debug event
                        raise
                rows=[json.loads(s) for s in log.read_text().splitlines() if s.startswith('{')]
                need(rows,'Missing publisher result')
                report=rows[-1]
                self.uncertain=report.get('uncertain') is not False or report.get('detached') is not True
                need(child.returncode==0 and not self.uncertain,'Publisher did not finish cleanly')
                self._identity(row['identity'])
                return child.returncode,report
            except BaseException as exc:
                self.failed=repr(exc)
                save_new(folder/(operation+'-held.json'),dict(error=self.failed,uncertain=self.uncertain,
                    publisher_pids=[p.pid for p in self.publishers],revoked=False,unloaded=False))
                raise
