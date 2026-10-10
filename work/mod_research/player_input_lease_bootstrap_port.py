"""Explicit one-shot HWND-thread bootstrap for a retained local game owner.
Only called with an existing process API and approved native build. No process
search, automatic retry, automatic Planning release, DLL unload or GUI actions.
"""
import ctypes as C
from ctypes import wintypes as W
from dataclasses import dataclass
import hashlib,json,shutil,time
from pathlib import Path
import player_input_lease_port as lease
import a_runtime_reward_port as common
from a_runtime_reward_port import require,save_new
MAGIC=0x31544F4F424C4950
class InputConfig(lease.Packed):
    _fields_=[('header',lease.Header),('nonce',lease.U8*32),('pid',lease.U32),('birth',lease.U64),('base',lease.U64),('window',lease.U64),('binding',lease.Binding)]
class Config(lease.Packed):_fields_=[('header',lease.Header),('input',InputConfig),('windowThread',lease.U32),('timeoutMs',lease.U32)]
class Report(lease.Packed):
    _fields_=[('header',lease.Header),('nonce',lease.U8*32),('pid',lease.U32),('birth',lease.U64),('window',lease.U64),('windowThread',lease.U32)]+[
        (n,lease.U32) for n in ('state','error','initializeResult','initializeThread','hookInstalled','hookRemoved','modulePinned','uncertain','attempts','callbackClaims','controlMessage','timeoutMs')]+[
        (n,lease.U64) for n in ('startTick','deadlineTick','endTick','module')]+[
        (n,lease.U32) for n in ('initializeAttempted','initializeSucceeded','callbackActive','callbackFinally')]
assert tuple(C.sizeof(t) for t in (InputConfig,Config,Report))==(144,176,176)
@dataclass(frozen=True)
class Build:
    run:Path
    sha256:str

def approved(build):
    require(type(build) is Build,'Explicit input bootstrap build required')
    folder=Path(build.run).resolve(strict=True);record=folder/'result.json'
    require(hashlib.sha256(record.read_bytes()).hexdigest()==build.sha256,'Bootstrap result changed')
    data=json.loads(record.read_text(encoding='utf-8-sig'))
    require(data.get('result')=='PASS' and data.get('game_access') is False,'Passing owned bootstrap build required')
    for field in ('sources','private','artifacts'):
        require(type(data.get(field)) is dict and data[field],'Complete bootstrap provenance required')
        for name,h in data[field].items():
            p=Path(name)
            if not p.is_absolute():p=common.HERE/p if field=='sources' else folder/p
            require(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==h,'Bootstrap input changed: '+name)
    dll=Path(data['production_dll']).resolve(strict=True)
    artifacts={(Path(n) if Path(n).is_absolute() else folder/n).resolve():h for n,h in data['artifacts'].items()}
    require(dll.is_relative_to(folder) and dll.name=='player_input_lease_bootstrap.dll' and artifacts.get(dll)==hashlib.sha256(dll.read_bytes()).hexdigest(),'Exact independent bootstrap binary required')
    return dll,artifacts[dll]

def window_identity(api,window,window_thread):
    """Fresh public Win32 identity and unclaimed original WndProc, read only."""
    u=C.WinDLL('user32',use_last_error=True);pid=W.DWORD()
    u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetWindowThreadProcessId.restype=W.DWORD
    u.IsWindow.argtypes=[W.HWND];u.IsWindow.restype=W.BOOL
    u.IsWindowUnicode.argtypes=[W.HWND];u.IsWindowUnicode.restype=W.BOOL
    for name in ('GetWindowLongPtrA','GetClassLongPtrA'):
        fn=getattr(u,name);fn.argtypes=[W.HWND,C.c_int];fn.restype=C.c_ssize_t
    b=api.reader.memory.base
    require(u.IsWindow(window) and not u.IsWindowUnicode(window) and
        u.GetWindowThreadProcessId(window,C.byref(pid))==window_thread and pid.value==api.reader.pid and
        u.GetWindowLongPtrA(window,-4)==u.GetClassLongPtrA(window,-24)==b+0x5122F0 and
        api.reader.pointer(b+0x19055D0+0x18)==window,'Window/source already claimed or identity differs')

class Transport(common.RemoteTransport):
    def _perform(self,name,payload):
        import pefile
        with self.lock:
            try:
                self._identity();require(name in ('PlayerInputBootstrapBegin','PlayerInputBootstrapSnapshot'),'Exact bootstrap export required')
                pe=pefile.PE(str(self.dll))
                try:
                    symbols=[s for s in pe.DIRECTORY_ENTRY_EXPORT.symbols if s.name==name.encode('ascii')]
                    require(len(symbols)==1 and not symbols[0].forwarder,'Unique native bootstrap export required')
                    rva=symbols[0].address;expected=pe.get_data(rva,32);address=self.module+rva
                finally:pe.close()
                common.readable(self.api.reader,address,32,allocation=self.module,execute=True)
                require(len(expected)==32 and self.api.reader.memory.read(address,32)==expected,'Bootstrap code differs')
                self.calls+=1;result=common.remote_call(self.api,address,payload,self.records,f'{self.calls:04d}-{name}')
                self._identity();return result
            except BaseException as exc:self.failed=repr(exc);raise

def bootstrap(api,*,build,binding,nonce,pid,birth,window,window_thread,call_state,records,timeout_ms=3000):
    require(type(call_state) is common.SharedCallState and type(binding) is lease.Binding,'Retained native call gate and binding required')
    require(type(timeout_ms) is int and 50<=timeout_ms<=5000 and type(nonce) is bytes and len(nonce)==32 and any(nonce),'Bounded bootstrap request required')
    require(all(any(getattr(binding,k)) for k in ('room','attachment','epoch')) and binding.period and binding.seat<2,'Nonempty input binding required')
    call_state.require_known()
    require(api.reader.pid==pid and common.process_birth(api.reader)==birth and api.reader.sha256==common.reward.SUPPORTED_SHA256,'Pinned game process differs')
    require(not hasattr(api,'_input_lease_bootstrap_attempt'),'One input bootstrap attempt per native API')
    window_identity(api,window,window_thread);source,dll_sha=approved(build)
    require(not any(Path(p).name.casefold()==source.name.casefold() for _,p in api.modules()),'Input bootstrap module already resident')
    root=Path(records);root.mkdir(parents=True,exist_ok=False)
    retained=dict(records=str(root),pid=pid,birth=birth,window=window,window_thread=window_thread,begin_attempted=False,complete=False)
    api._input_lease_bootstrap_attempt=retained
    try:
        folder=root/'module';folder.mkdir();dll=folder/source.name;shutil.copyfile(source,dll)
        require(hashlib.sha256(dll.read_bytes()).hexdigest()==dll_sha,'Copied bootstrap DLL changed')
        # Repeat identity after disk/build preparation. LoadLibrary does not run Initialize.
        window_identity(api,window,window_thread)
        call_state.invoke(lambda:common.remote_call(api,api.load_library_address(),str(dll).encode('utf-16le')+b'\0\0',root,'load-bootstrap'))
        modules=[a for a,p in api.modules() if Path(p).resolve()==dll.resolve()];require(len(modules)==1,'Loaded bootstrap module unresolved')
        module=modules[0];retained['module']=module
        calls=root/'calls';calls.mkdir()
        transport=Transport(api,module=module,dll=dll,dll_sha256=dll_sha,pid=pid,birth=birth,records=calls,call_state=call_state)
        q=Config();q.header=lease.Header(MAGIC,1,C.sizeof(q),1,0)
        q.input.header=lease.Header(lease.MAGIC,1,C.sizeof(q.input),1,0);q.input.nonce[:]=nonce
        q.input.pid=pid;q.input.birth=birth;q.input.base=api.reader.memory.base;q.input.window=window;q.input.binding=binding
        q.windowThread=window_thread;q.timeoutMs=timeout_ms
        save_new(root/'begin-intent.json',common.base.values(q));retained['begin_attempted']=True
        code,raw=transport.call('PlayerInputBootstrapBegin',bytes(q));require(type(raw) is bytes and len(raw)==C.sizeof(q),'Bootstrap Begin reply length differs')
        answer=Config.from_buffer_copy(raw);save_new(root/'begin-result.json',dict(exit=code,report=common.base.values(answer)))
        require(bytes(answer.header)[:20]==bytes(q.header)[:20] and bytes(answer)[24:]==bytes(q)[24:] and code==answer.header.result==0,'Bootstrap Begin refused or foreign')
        deadline=time.monotonic()+timeout_ms/1000+1;count=0
        while True:
            q=Report();q.header=lease.Header(MAGIC,1,C.sizeof(q),2,0);q.nonce[:]=nonce
            code,raw=transport.call('PlayerInputBootstrapSnapshot',bytes(q));count+=1
            require(type(raw) is bytes and len(raw)==C.sizeof(q),'Bootstrap Snapshot length differs')
            r=Report.from_buffer_copy(raw);save_new(root/f'snapshot-{count:04d}.json',dict(exit=code,report=common.base.values(r)))
            require(code==r.header.result==0 and bytes(r.header)[:20]==bytes(q.header)[:20] and bytes(r.nonce)==nonce and
                    (r.pid,r.birth,r.window,r.windowThread,r.module,r.timeoutMs)==(pid,birth,window,window_thread,module,timeout_ms),'Foreign bootstrap receipt')
            require(r.state in (1,2,3) and not r.error and not r.uncertain and r.attempts==1,'Native window bootstrap failed or unresolved')
            if r.state==3 and not r.callbackActive:
                require(r.initializeAttempted==r.initializeSucceeded==r.hookRemoved==r.modulePinned==r.callbackClaims==1 and r.callbackFinally>=r.callbackClaims and
                        r.initializeResult==r.hookInstalled==0 and r.initializeThread==window_thread,'Bootstrap callback/drain receipt incomplete')
                retained['complete']=True;save_new(root/'bootstrap-complete.json',common.base.values(r));break
            require(time.monotonic()<deadline,'Bootstrap completion not observed; retained owner, no retry')
            time.sleep(.01)
        input_calls=root/'input-calls';input_calls.mkdir()
        input_transport=lease.Transport(api,module=module,dll=dll,dll_sha256=dll_sha,pid=pid,birth=birth,records=input_calls,call_state=call_state)
        result=lease.InputLease(input_transport,nonce=nonce,binding=binding,pid=pid,birth=birth,window=window,records=root/'input-control')
        result.bootstrap_record=retained;return result
    except BaseException as exc:
        retained['failure']=repr(exc);exc.retained_input_bootstrap=retained
        try:save_new(root/'failed.json',retained)
        except BaseException as secondary:exc.bootstrap_record_error=repr(secondary)
        raise
