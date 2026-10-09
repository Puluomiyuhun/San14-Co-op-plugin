"""Actual retained Python factory + remote Prepare/Seal + external publisher.
Only owned host processes; archived mapped image/business data are fixture.
"""
from datetime import datetime
from pathlib import Path
import ctypes as C
from ctypes import wintypes as W
import hashlib,json,os,queue,shutil,struct,subprocess,sys,threading

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
from b_warm_rules_factory import RulesFactory,RulesBuild
from b_warm_rules_capture import RulesWorldCapture
from b_warm_rules_bridge_test import prepare_build,PRIOR,PRIOR_SHA
from human_rules_activation_publish_v2_counter_profile import generate
from b_warm_start_support import open_process_api
from checkpoint_push_start import process_birth
from human_rules_world_lifecycle import NextWorldRequest,Config
from human_rules_activation_room import rules,GAME_SHA
from b_warm_room import WarmRoom
from checkpoint_fresh_save_binding_test import manifest,select_direct
from room_session import digest
import pefile
from unittest.mock import patch
import b_warm_rules_factory as factory_module


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    paths.add(HERE/'b_warm_rules_factory_fixture.inc')
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix in ('.py','.inc')}


def build(run):
    sources=prepare_build(run);inputs=run/'inputs'
    # Validate actual copied headers used by this compiler against frozen pins.
    for name,wanted in json.loads((PRIOR/'result.json').read_text())['source_sha256'].items():
        assert sha(PRIOR/'src'/name)==wanted,name
    original=HERE/'human_rules_world_lifecycle_fixture.cpp'
    text=original.read_text();at=text.index(' Instance first=prepareInstance')
    host=run/'host.cpp';host.write_text(text[:at]+(HERE/'b_warm_rules_factory_fixture.inc').read_text(encoding='utf-8-sig'))
    # Frozen includes are copied by the predecessor and also independently pinned.
    include=PRIOR/'src/work/mod_research';private=PRIOR/'src/private'
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags=f'/nologo /std:c++17 /EHa /W4 /WX /O2 /MT /I"{run}" /I"{include}" /I"{private}" /I"{PRIOR/"src/outputs/san14-link"}"'
    def execute(label,cmd):
        script=run/f'build-{label}.cmd';script.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+cmd+'\n')
        p=subprocess.run(['cmd','/d','/c',str(script)],cwd=run,capture_output=True,timeout=60)
        (run/f'build-{label}.log').write_bytes(p.stdout+p.stderr)
        assert p.returncode==0,(label,p.stdout.decode(errors='replace'))
    execute('host',f'cl {flags} "{host}" /Fe:"{inputs/"factory-host.exe"}"')
    profile=generate(inputs/'first.dll',run/'human_rules_activation_publish_v2_fixture_counters.h')
    (run/'human_rules_activation_publish_v2_fixture_hashes.h').write_text('#pragma once\nconstexpr unsigned ExpectedFixture=1;\n'+
        'constexpr const char* ApprovedExeSha="'+sha(inputs/'factory-host.exe')+'";\n'+
        'constexpr const char* ApprovedStageSha="'+sha(inputs/'first.dll')+'";\n'+
        'constexpr const char* ApprovedImageSha="'+sha(inputs/'owned_rules_image.dll')+'";\n')
    # Quote-includes search the including file first: copy publisher/config to
    # this run so its fixture headers resolve to our new exact host fingerprint.
    for n in ('human_rules_activation_publish_v2.cpp','human_rules_activation_publish_v2_config.h'):
        shutil.copyfile(HERE/n,run/n)
    cmd=f'cl {flags} /DHUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE '+ ' '.join('"'+str(p)+'"' for p in
        (run/'human_rules_activation_publish_v2.cpp',include/'human_ai_runtime_subject.cpp',include/'human_ai_group_resolver.cpp'))
    execute('publisher',cmd+f' /Fe:"{inputs/"factory-publisher.exe"}"')
    return sources,inputs,profile


class Memory:
    def __init__(self,pid):
        self.base=0x10000000;self.k=C.WinDLL('kernel32',use_last_error=True)
        self.k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];self.k.OpenProcess.restype=W.HANDLE
        self.handle=self.k.OpenProcess(0x410,False,pid);assert self.handle
        self.k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];self.k.ReadProcessMemory.restype=W.BOOL
        self.k.CloseHandle.argtypes=[W.HANDLE];self.k.CloseHandle.restype=W.BOOL
    def read(self,address,size):
        value=C.create_string_buffer(size);n=C.c_size_t()
        assert self.k.ReadProcessMemory(self.handle,address,value,size,C.byref(n)) and n.value==size
        return value.raw
    def close(self):self.k.CloseHandle(self.handle)


class Reader:
    """Real RPM, synthetic owned GameReader environment/RTTI adapter."""
    def __init__(self,pid):self.pid=pid;self.memory=Memory(pid);self.sha256=GAME_SHA
    def pointer(self,at):return struct.unpack('<Q',self.memory.read(at,8))[0]
    def state_objects(self):
        stack=self.pointer(self.memory.base+0x19e7310+0x20)
        rows=[]
        for i in range(5):
            p=self.pointer(stack+i*8);name=self.memory.read(p+0x70,40).split(b'\0',1)[0].decode()
            rows.append((name,p))
        return rows
    def snapshot(self):
        root=self.pointer(self.memory.base+0x1fca1e0);world=self.pointer(root+0x85130)
        raw=self.memory.read(world+0x34,8);year,month,day=struct.unpack_from('<HBB',raw);force=raw[6]
        f=self.pointer(root+0xdca0+force*8);ruler=struct.unpack('<H',self.memory.read(f+0x10,2))[0]
        return dict(pid=self.pid,exe_sha256=self.sha256,date=dict(year=year,month=month,day=day),
            player=dict(force_id=force,ruler_id=ruler),state_stack=[n for n,_ in self.state_objects()])
    def require_type(self,at,name):
        vt={'CSan14Data':0x12aa6b0,'CWorldData':0x12aa638}[name]
        assert self.pointer(at)==self.memory.base+vt


class Owned:
    def __init__(self,run,inputs,name):
        self.folder=run/name;self.folder.mkdir();self.lines=[];self.queue=queue.Queue()
        self.child=subprocess.Popen([str(inputs/'factory-host.exe'),'unused','unused',str(inputs/'owned_rules_image.dll'),str(inputs/'game-runtime-image.bin')],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        def consume():
            for line in self.child.stdout:self.lines.append(line);self.queue.put(line)
        self.thread=threading.Thread(target=consume,daemon=True);self.thread.start()
        row=self.receive('READY');assert row['pid']==self.child.pid
        self.reader=Reader(self.child.pid);self.api=open_process_api(self.reader)
        self.closed=False
    def receive(self,event):
        raw=self.queue.get(timeout=15);row=json.loads(raw);assert row['event']==event,(event,row);return row
    def command(self,text,event):self.child.stdin.write((text+'\n').encode());self.child.stdin.flush();return self.receive(event)
    def finish(self):
        final=self.command('q','FINAL');assert self.child.wait(timeout=10)==0;self.thread.join(2)
        (self.folder/'host.log').write_bytes(b''.join(self.lines));self.api.close();self.reader.memory.close();self.closed=True
        return final


def exercise(run,inputs,profile,name,negative=False):
    own=Owned(run,inputs,name);factory=None
    try:
        setting=rules(1,0);catalog=manifest();catalog['profile']['game_sha256']=GAME_SHA;catalog['profile']['rules_sha256']=digest(setting)
        room=WarmRoom(catalog);select_direct(room)
        birth=process_birth(own.reader)
        capture=RulesWorldCapture(own.reader,room,setting,pid=own.child.pid,birth=birth,
            read_birth=lambda:process_birth(own.reader),guard_check=lambda:None) # main thread waits for explicit commands
        approved=RulesBuild(inputs/'first.dll',inputs/'factory-publisher.exe',sha(inputs/'first.dll'),sha(inputs/'factory-publisher.exe'),
            sha(inputs/'factory-host.exe'),tuple((x['instruction_rva'],bytes.fromhex(x['bytes']),x['value_rva']) for x in profile['active_counters']),'OWNED_FIXTURE')
        factory=RulesFactory(capture,own.api,approved,own.folder,rulers={12:12,2:2})
        observed=capture.capture_loaded(NextWorldRequest(1,'1'*64,b'\1'*16,203,8,11),side='A',expected_ruler=12)
        if negative:
            own.command('x','NONIDLE')
            try:factory.prepare_rules(observed)
            except ValueError as exc:assert 'Native Prepare rejected' in str(exc)
            else:raise AssertionError('nonidle native accepted')
            assert factory.failed and not factory.uncertain and len(factory.retained)==1 and not factory.publishers
            try:factory.prepare_rules(observed)
            except ValueError as exc:assert 'held' in str(exc)
            else:raise AssertionError('failed factory replayed')
            row=factory.retained[0]
            assert int.from_bytes(own.reader.memory.read(row['addresses']['HumanRulesActivationState'],4),'little')==5
            final=own.finish()
            return dict(case=name,result='PASS',native_prepare_rejected=True,retry_refused=True,published=False,normal_exit=True)
        observations=[]
        for generation in (1,2):
            if generation==2:
                own.command('n','LOADED')
                observed=capture.capture_loaded(NextWorldRequest(2,'2'*64,b'\2'*16,203,8,21),side='B',expected_ruler=2)
            port=factory.prepare_rules(observed)
            own.command('b '+str(port.module.module),'BOUND')
            installed=port.install();executed=own.command('e','EXERCISED');restored=port.restore();port.retired=True
            observations.append(dict(generation=generation,viewer=Config.from_buffer_copy(observed.config).viewer,
                installed=installed,executed=executed,restored=restored,module=port.module.module))
        assert observations[0]['module']!=observations[1]['module'] and len(factory.retained)==2
        try:factory.prepare_rules(observed)
        except ValueError as exc:assert 'Fresh typed generation' in str(exc)
        else:raise AssertionError('claimed generation reused')
        # Inject only the log-failure window after a fake publisher creation;
        # no OS child/debugger is launched for this exception case.
        fake_calls=[]
        class FakeChild:
            pid=999999
            def wait(self,**kw):fake_calls.append('wait');raise AssertionError('must not wait')
            def kill(self):fake_calls.append('kill');raise AssertionError('must not kill')
        fake=FakeChild();row=dict(factory.retained[-1]);row['folder']=own.folder/'publisher-log-failure';row['folder'].mkdir()
        (row['folder']/'config.bin').write_bytes(row['world'].config)
        original_save=factory_module.save_new
        def disk_failure(path,value):
            if path.name=='install-process.json':raise OSError('explicit fake log failure')
            return original_save(path,value)
        with patch.object(factory_module.subprocess,'Popen',return_value=fake),patch.object(factory_module,'save_new',side_effect=disk_failure):
            try:factory._publish(row,'install')
            except OSError:pass
            else:raise AssertionError('injected log failure did not propagate')
        assert factory.uncertain and factory.failed and fake in factory.publishers and not fake_calls
        # Actual four publishers all completed/detached; fake never touched host.
        final=own.finish();assert final['resident_modules']==2
        return dict(case=name,result='PASS',generations=observations,normal_exit=True,actual_remote_prepare_seal=True,
            actual_external_publisher=True,actual_rules_capture=True,native_load=False,
            fake_publisher_log_failure_retained_unknown=True,fake_publisher_kill_calls=0)
    except BaseException:
        (own.folder/'host-failed.log').write_bytes(b''.join(own.lines))
        # Never kill an uncertain target/publisher. Owned clean, unpublished or
        # fully restored target may leave through its normal q assertions.
        if factory and factory.uncertain:
            (own.folder/'retained.json').write_text(json.dumps(dict(pid=own.child.pid,publishers=[p.pid for p in factory.publishers]))+'\n')
        elif not own.closed:
            try:own.finish()
            except BaseException:pass
        raise


def main():
    run=PRIVATE/'b_warm_rules_factory_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    result=dict(result='FAIL',family='san14.b-warm-rules-factory.v1',game_access=False,steam_access=False,cases=[])
    before=pins()
    prior_result=json.loads((PRIOR/'result.json').read_text())
    private={str(PRIOR/'result.json'):PRIOR_SHA}
    for name,wanted in prior_result['source_sha256'].items():private[str(PRIOR/'src'/name)]=wanted
    for name,wanted in prior_result['binary_sha256'].items():private[str(PRIOR/'inputs'/name)]=wanted
    # Existing real production pair is checked, never loaded into the fixture.
    production=RulesBuild(PRIVATE/'human_rules_activation_v2_runs/20261008-000431-509932/production.dll',
        PRIVATE/'human_rules_activation_publish_v2_runs/20261008-000527-938626/inputs/publisher-production.exe')
    private[str(production.stage)]=production.stage_sha;private[str(production.publisher)]=production.publisher_sha
    try:
        sources,inputs,profile=build(run);before.update(sources)
        result['cases']=[exercise(run,inputs,profile,'success'),exercise(run,inputs,profile,'prepare-refused',True)]
        result['result']='PASS'
    except BaseException as exc:
        import traceback
        result['error']=repr(exc);(run/'failure.txt').write_text(traceback.format_exc());print(traceback.format_exc())
    result['sources']=before
    result['inputs_unchanged']=all(Path(k).is_file() and sha(k)==v for k,v in {**before,**private}.items())
    if not result['inputs_unchanged']:result['result']='FAIL'
    result['private']=private
    result['production_artifacts_checked_only']=dict(stage=str(production.stage),publisher=str(production.publisher))
    result['binaries']={str(p):sha(p) for p in run.rglob('*') if p.is_file() and p.suffix in ('.exe','.dll','.obj')}
    result['generated']={str(p):sha(p) for p in run.iterdir() if p.is_file() and p.suffix in ('.h','.cpp','.cmd','.json')}
    result['artifacts']={str(p):sha(p) for p in run.rglob('*') if p.is_file() and p.suffix in ('.log','.bin','.json') and p.name not in ('game-runtime-image.bin','result.json')}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(run/'result.json')
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
