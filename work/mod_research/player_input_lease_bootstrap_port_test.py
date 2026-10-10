"""Production Python HWND bootstrap over explicit owned OS/native call doubles.

Real provenance, copied production PE, both typed Transports and InputLease.
No target process, native DLL execution, hook installation or game/Steam access.
"""
from contextlib import ExitStack
from datetime import datetime
import argparse,ctypes as C,hashlib,io,json,sys,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import player_input_lease_bootstrap_port as boot
import player_input_lease_port as lease
from player_input_lease_port_test import InputBody
from b_reward_native_factory_test import OwnedOS,sha
from reward_observed_fixture import World
import pefile

OUTPUT=None;BUILD=None;APPROVED=None;ROWS=[];PRIVATE_INPUTS={}


class BootstrapOS(OwnedOS):
    def __init__(self,case):
        super().__init__(case)
        self.window=12345;self.window_thread=77;self.window_checks=0;self.polls=0;self.claimed=False
        native=SimpleNamespace(binding=(self.reader.pid,case.birth,case.b_world.epoch,case.b_world.attachment))
        self.input=InputBody(native);self.input.s.binding.seat=1
    def window_identity(self,api,window,thread):
        self.case.assertIs(api,self.api);self.case.assertEqual((window,thread),(self.window,self.window_thread))
        self.window_checks+=1
        if self.fault=='wrong-window' or (self.fault=='window-raced' and self.window_checks==2):
            raise RuntimeError('Owned window/source changed')
        self.case.assertFalse(self.claimed)
    def remote(self,api,address,raw,records,label):
        self.case.assertIs(api,self.api)
        if address==self.api.load_library_address():
            path=Path(raw.decode('utf-16le').rstrip('\0')).resolve()
            self.load_attempts.append(path.name);self.calls.append('LoadLibraryW:'+path.name)
            if self.fault=='unknown-load':raise boot.common.RemoteCallUnknown('owned unresolved LoadLibrary',{'may_have_started':True})
            self.case.assertEqual(sha(path),APPROVED[1]);self.case.assertEqual(path.parent,Path(records)/'module')
            with pefile.PE(str(path)) as pe:
                data=pe.get_memory_mapped_image();base=self.module_base
                self.memory.reserve(base,len(data));self.memory.put(base,data);self.allocations.append((base,len(data),0x20))
                self.modules.append((base,path))
                for export in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if export.name and export.name.startswith(b'PlayerInput'):self.exports[base+export.address]=export.name.decode()
            return base&0xffffffff,raw
        name=self.exports[address];self.calls.append(name)
        if name=='PlayerInputBootstrapBegin':
            self.configuration=boot.Config.from_buffer_copy(raw)
            if self.fault=='unknown-begin':raise boot.common.RemoteCallUnknown('owned Begin result lost',{'may_have_started':True})
            return 0,raw
        if name=='PlayerInputBootstrapSnapshot':
            q=boot.Report.from_buffer_copy(raw);self.polls+=1;cfg=self.configuration
            q.pid,q.birth,q.window,q.windowThread=cfg.input.pid,cfg.input.birth,cfg.input.window,cfg.windowThread
            q.module=self.modules[0][0];q.timeoutMs=cfg.timeoutMs;q.attempts=q.modulePinned=1;q.controlMessage=0xC002
            q.startTick=1000;q.deadlineTick=1000+q.timeoutMs
            # Two unrelated hook callbacks can precede the matching token.
            # callbackFinally counts all callbacks, while callbackClaims is one.
            q.state=1 if self.polls==1 else (2 if self.polls==2 else 3)
            q.hookInstalled=int(self.polls<=3);q.hookRemoved=int(self.polls>=4)
            q.callbackActive=int(self.polls in (2,3));q.callbackFinally=2 if self.polls<4 else 3
            q.callbackClaims=int(self.polls>=2);q.initializeThread=self.window_thread if self.polls>=2 else 0
            q.initializeAttempted=int(self.polls>=2);q.initializeSucceeded=int(self.polls>=3)
            q.initializeResult=0 if self.polls>=3 else 0xffffffff;q.endTick=1010 if self.polls>=3 else 0
            if self.fault=='never-drained' and self.polls>=3:q.callbackActive=1;q.hookInstalled=1;q.hookRemoved=0
            if self.fault=='bad-unhook' and self.polls>=4:q.hookRemoved=0
            if self.fault=='foreign-report':q.windowThread+=1
            if self.polls>=4 and self.fault is None:self.claimed=True
            return 0,bytes(q)
        return self.input.call(name,raw)
    def patches(self):
        stack=super().patches()
        stack.enter_context(patch.object(boot,'window_identity',side_effect=self.window_identity))
        return stack


class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUTPUT/self._testMethodName;self.folder.mkdir()
        self.b_world=World(2);self.guest=self.b_world.reader;self.birth=self.b_world.birth
        self.warm=SimpleNamespace(steam={});self.env=BootstrapOS(self)
        self.unknown=[];self.state=boot.common.SharedCallState(threading.RLock(),self.unknown.append)
        self.nonce=self.env.input.nonce;self.binding=self.env.input.s.binding
        self.records=self.folder/'bootstrap'
    def start(self):
        return boot.bootstrap(self.env.api,build=BUILD,binding=self.binding,nonce=self.nonce,pid=self.guest.pid,
            birth=self.birth,window=self.env.window,window_thread=self.env.window_thread,
            call_state=self.state,records=self.records,timeout_ms=50)
    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,calls=list(self.env.calls),window_checks=self.env.window_checks,
            native_input_calls=self.env.input.calls,unknown=self.state.unknown is not None,
            retained=getattr(self.env.api,'_input_lease_bootstrap_attempt',None),**extra))

    def test_real_factory_waits_callback_finally_stays_terminal(self):
        with self.env.patches():
            result=self.start();q=self.env.configuration
            self.assertIs(type(result),lease.InputLease);self.assertIs(result.state,self.state)
            self.assertEqual((q.input.pid,q.input.birth,q.input.base,q.input.window,q.windowThread,q.timeoutMs),
                (self.guest.pid,self.birth,self.guest.memory.base,self.env.window,self.env.window_thread,50))
            self.assertEqual(bytes(q.input.binding),bytes(self.binding));self.assertEqual(bytes(q.input.nonce),self.nonce)
            self.assertEqual((q.header.magic,q.header.op,q.input.header.magic,q.input.header.op),(boot.MAGIC,1,lease.MAGIC,1))
            self.assertEqual(self.env.polls,4);self.assertTrue(result.bootstrap_record['complete'])
            s=result.snapshot();self.assertEqual(s.phase,5);self.assertTrue(s.held)
            self.assertNotIn('PlayerInputRequest',self.env.calls)
            with self.assertRaisesRegex(RuntimeError,'acknowledged Planning'):result.begin(result.local_binding)
            self.assertNotIn('PlayerInputAcquire',self.env.calls)
        self.evidence(configure=boot.common.base.values(q),initial_phase=s.phase)

    def test_wrong_window_refused_before_load(self):
        self.env.fault='wrong-window'
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'window/source changed'):self.start()
        self.assertFalse(self.env.calls);self.assertFalse(self.records.exists());self.evidence()

    def test_window_changes_during_copy_refused_before_load(self):
        self.env.fault='window-raced'
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'window/source changed') as caught:self.start()
        self.assertEqual(self.env.window_checks,2);self.assertFalse(self.env.calls)
        self.assertFalse(caught.exception.retained_input_bootstrap['begin_attempted']);self.evidence()

    def test_unknown_load_latches_shared_gate_no_begin_or_retry(self):
        self.env.fault='unknown-load'
        with self.env.patches():
            with self.assertRaises(boot.common.RemoteCallUnknown) as caught:self.start()
            self.assertIs(caught.exception.retained_input_bootstrap,self.env.api._input_lease_bootstrap_attempt)
            before=list(self.env.calls)
            with self.assertRaisesRegex(RuntimeError,'outcome unknown'):self.start()
            self.assertEqual(self.env.calls,before)
        self.assertEqual(len(self.unknown),1);self.assertNotIn('PlayerInputBootstrapBegin',self.env.calls);self.evidence()

    def test_unknown_begin_forbids_snapshots(self):
        self.env.fault='unknown-begin'
        with self.env.patches(),self.assertRaises(boot.common.RemoteCallUnknown) as caught:self.start()
        self.assertTrue(caught.exception.retained_input_bootstrap['begin_attempted'])
        self.assertFalse(caught.exception.retained_input_bootstrap['complete'])
        self.assertNotIn('PlayerInputBootstrapSnapshot',self.env.calls);self.assertNotIn('PlayerInputSnapshot',self.env.calls)
        self.assertEqual(len(self.unknown),1);self.evidence()

    def test_complete_without_unhook_refuses_input_lease(self):
        self.env.fault='bad-unhook'
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'drain receipt incomplete'):self.start()
        self.assertNotIn('PlayerInputSnapshot',self.env.calls);self.assertFalse(self.env.api._input_lease_bootstrap_attempt['complete'])
        self.evidence()

    def test_unresolved_callback_cannot_return_or_retry(self):
        self.env.fault='never-drained'
        with self.env.patches():
            with self.assertRaisesRegex(RuntimeError,'completion not observed'):self.start()
            before=list(self.env.calls)
            with self.assertRaisesRegex(RuntimeError,'One input bootstrap'):self.start()
            self.assertEqual(self.env.calls,before)
        self.assertNotIn('PlayerInputSnapshot',self.env.calls);self.evidence()

    def test_foreign_callback_thread_receipt_refused(self):
        self.env.fault='foreign-report'
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'Foreign bootstrap receipt'):self.start()
        self.assertNotIn('PlayerInputSnapshot',self.env.calls);self.evidence()


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--build-run',type=Path,required=True);parser.add_argument('--build-sha256',required=True)
    args=parser.parse_args();BUILD=boot.Build(args.build_run,args.build_sha256);APPROVED=boot.approved(BUILD)
    PRIVATE_INPUTS={str(args.build_run.resolve()/'result.json'):args.build_sha256,str(APPROVED[0]):APPROVED[1]}
    OUTPUT=PRIVATE/'player_input_lease_bootstrap_port_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);after=pins()
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,
        sources=after,sources_unchanged=before==after,private_inputs=PRIVATE_INPUTS,cases=ROWS,
        production_bootstrap_and_both_typed_transports_executed=True,actual_build_copy_PE_checks=True,
        HWND_process_loader_native_bodies_RAM_OS_doubles=True,native_DLL_executed=False,
        game_access=False,steam_access=False,full_world_verified=False,input_exclusion_proven=False,
        failures=[(str(t),s) for t,s in result.failures+result.errors])
    report['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(report['result']!='PASS')
