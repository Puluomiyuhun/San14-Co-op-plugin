"""Execute production NativePort.open over owned process/loader interfaces.

Real first formal Session completion, same GameReader, build provenance, DLL
copy, PE exports, Transport/SharedCallState, sampler and six-slot predicates.
Win32 module/process/Steam discovery and native call bodies are explicit doubles;
no production DLL is loaded/executed and no game or Steam process is accessed.
"""
from contextlib import ExitStack
from copy import deepcopy
from datetime import datetime
import ctypes as C
import hashlib,io,json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_reward_runner_test as fixture
import b_reward_native_port as port
import checkpoint_complete_live_capture as capture
from checkpoint_push_start import MemoryPage
import pefile

BUILD=PRIVATE/'b_reward_owner_runs/20261010-095208-139540'
BUILD_SHA='028ce8040e91c1b3a1b8d27b4a1e55bbdbe22e728204dec0f717419884974478'
OUTPUT=None;ROWS=[];PRIVATE_INPUTS={}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class Function:
    def __init__(self,fn):self.fn=fn
    def __call__(self,*args):return self.fn(*args)


class OwnedOS:
    """Only OS/module/storage/native ABI endpoints; factory is not substituted."""
    def __init__(self,case):
        self.case=case;self.reader=case.guest;self.memory=self.reader.memory
        self.modules=[];self.exports={};self.calls=[];self.load_attempts=[];self.configuration=None
        self.fault=None;self.module_base=0x780000000;self.handle=777
        self.allocations=[(self.memory.base,0x2240000,2)]
        self.storage_base=0x590000000;self.storage_vtable=self.storage_base+0x1000
        self.memory.reserve(self.storage_base,0x3000);self.allocations.append((self.storage_base,0x3000,2))
        self.read_original=self.storage_base+0x2000;self.memory.pack(self.storage_vtable+8,'<Q',self.read_original)
        self.storage=dict(storageVtable=self.storage_vtable,read=dict(address=self.read_original),
            storageModules=[dict(base=self.storage_base)],vtableModuleIndex=0)
        self.memory.k=SimpleNamespace(VirtualQueryEx=Function(self.query));self.memory.handle=self.handle
        def times(handle,*out):case.assertEqual(handle,self.handle);out[0]._obj.value=case.birth;return 1
        self.api=SimpleNamespace(reader=self.reader,handle=self.handle,modules=lambda:list(self.modules),
            load_library_address=lambda:0x771000000,k=SimpleNamespace(
                GetProcessId=Function(lambda handle:self.reader.pid),GetProcessTimes=Function(times)))
        self.cache=case.b_world.obj('owned-factory-cache',0x400)
        self.memory.pack(self.memory.base+0x2025318,'<Q',self.cache)
        self.stopped=self.restored=False

    def allocation(self,address,size):
        matches=[r for r in self.allocations if r[0]<=address and address+size<=r[0]+r[1]]
        if len(matches)!=1:raise RuntimeError('Owned page missing/overlapping '+hex(address))
        return matches[0]
    def query(self,handle,address,out,size):
        a,n,protection=self.allocation(address,8);v=out._obj
        v.BaseAddress=address&~0xfff;v.AllocationBase=a;v.RegionSize=0x1000;v.Protect=protection;v.State=0x1000
        return C.sizeof(MemoryPage)
    def readable(self,reader,address,size,*,allocation=None,execute=False):
        self.case.assertIs(reader,self.reader);a,n,p=self.allocation(address,size)
        if allocation is not None:self.case.assertEqual(a,allocation)
        if execute:self.case.assertEqual(p,0x20)
        self.memory.read(address,size)
    def module_approval(self,reader,module,path,expected):
        self.case.assertIs(reader,self.reader);path=Path(path).resolve()
        self.case.assertEqual(sha(path),expected);self.case.assertIn((module,path),self.modules)
        return dict(base=module,path=str(path),sha256=expected,owned_OS_module_approval=True)
    def storage_bindings(self,reader,modules,*,steam_paths):
        self.case.assertIs(reader,self.reader);self.case.assertEqual(modules,self.modules)
        self.case.assertIs(steam_paths,self.case.warm.steam)
        self.calls.append('storage-discovery-double');return deepcopy(self.storage)
    def remote(self,api,address,raw,records,label):
        self.case.assertIs(api,self.api)
        if address==self.api.load_library_address():
            path=Path(raw.decode('utf-16le').rstrip('\0')).resolve();self.load_attempts.append(path.name)
            self.calls.append('LoadLibraryW:'+path.name)
            if self.fault=='unknown-load':raise port.RemoteCallUnknown('owned unresolved module load',{'may_have_started':True})
            self.case.assertEqual(path.parent,Path(records)/'module')
            self.case.assertEqual(sha(path),sha(BUILD/'production'/path.name))
            with pefile.PE(str(path)) as pe:
                data=pe.get_memory_mapped_image();base=self.module_base;self.module_base+=0x1000000
                self.memory.reserve(base,len(data));self.memory.put(base,data);self.allocations.append((base,len(data),0x20))
                self.modules.append((base,path))
                for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if e.name and e.name.startswith(b'BReward'):self.exports[base+e.address]=e.name.decode()
            return base&0xffffffff,raw
        name=self.exports[address];self.calls.append(name)
        kind=dict(BRewardConfigure=port.Configure,BRewardSnapshot=port.Snapshot,
                  BRewardStop=port.base.Command,BRewardRestore=port.base.Command)[name]
        value=kind.from_buffer_copy(raw)
        if name=='BRewardConfigure':
            self.configuration=value
            self.case.assertEqual(len(raw),256)
            self.memory.pack(self.memory.base+0x12CC4D0,'<Q',address)
        elif name=='BRewardSnapshot':
            value.configured=value.nativeClean=1;value.armed=int(not self.restored);value.state=1
            value.stopped=value.admissionClosed=int(self.stopped)
            value.slotRestored=value.restoreVerified=int(self.restored)
        elif name=='BRewardStop':self.stopped=True
        elif name=='BRewardRestore':
            self.case.assertTrue(self.stopped);self.restored=True
            self.memory.pack(self.memory.base+0x12CC4D0,'<Q',self.memory.base+0x3F9B00)
        return 0,bytes(value)
    def patches(self):
        stack=ExitStack()
        stack.enter_context(patch.object(port,'storage_bindings',side_effect=self.storage_bindings))
        stack.enter_context(patch.object(port.common,'remote_call',side_effect=self.remote))
        stack.enter_context(patch.object(port.common,'process_birth',side_effect=lambda r:self.case.birth))
        stack.enter_context(patch.object(port.common,'module_approval',side_effect=self.module_approval))
        stack.enter_context(patch.object(port.common,'readable',side_effect=self.readable))
        stack.enter_context(patch.object(capture,'readable',side_effect=self.readable))
        return stack


class Cases(fixture.Cases):
    def setUp(self):
        super().setUp()
        self.offer_first();self.runner=fixture.old.Runner(self.config,self.link)
        ctx=self.runner._context(1,None);m=ctx['manifest']
        p=fixture.old.make_profile(self.runner.local,m['parts']['world.s14'],self.runner.local['initial_node'],m['node'],1)
        received=fixture.old.receive_bootstrap_staged(self.link.control,self.link.connect_download,
            checkpoint_id=ctx['checkpoint_id'],scope=ctx['scope'],epoch=ctx['epoch'],period=ctx['period'],
            cut=m['cut'],attachments=ctx['attachments'],directory=self.folder/'factory-first')
        self.open_owned(self.runner,ctx,p,self.checked['sources'])
        request=fixture.old.NextWorldRequest(2,ctx['checkpoint_id'],b'z'*16,203,8,11)
        self.assertTrue(self.runner.guest.apply(received,request,p)['ok'])
        self.profile=p;self.mount.open(self.artifacts[1],self.room.artifacts,self.prep)
        self.reward_scope=deepcopy(self.mount.flow.scope)
        self.env=OwnedOS(self)
        # Explicit native-load/helper environment: derive retirement from the
        # first accepted load double, not an invented formal Room receipt.
        completion=self.session.sessions[0]['result']['completion']
        self.warm.current=dict(index=0,warm_load_retired=completion['accepted']['result']=='PASS_WARM_LOAD_RETIRED',
            refresh_load_retired=completion['refresh']['leaseReleased']==1)
        self.warm.hand=lambda kind:SimpleNamespace(firstCompleted=int(self.warm.current['warm_load_retired']))
        self.warm.api=self.env.api;self.warm.steam={'owned':'storage discovery double'}
        self.session.factory=SimpleNamespace(uncertain=False)
        self.session._owners=(self.session.reader,self.session.control,self.session.warm,self.session.lifecycle,
            self.session.bridge,self.session.boundary,self.session.factory)
        with self.env.patches():
            self.warm.first_hooks=port.live_hook_evidence(self.guest,
                dict(base=self.guest.memory.base,nativeSlots=[(self.guest.memory.base+s,self.guest.memory.base+o) for s,o in port.SLOTS]),
                self.env.storage)
        self.build=port.NativeBuild(BUILD,sha(BUILD/'result.json'))
        self.native_records=self.folder/'actual-production-factory'

    def open_factory(self):
        return port.NativePort.open(session=self.session,guest=self.runner.guest,profile=self.profile,
            scope=self.reward_scope,records=self.native_records,build=self.build)
    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,calls=list(self.env.calls),load_attempts=list(self.env.load_attempts),
            formal_completions=len(self.runner.guest.history),session_phase=self.session.phase,
            warm_uncertain=self.warm.calls.uncertain,factory_uncertain=self.session.factory.uncertain,**extra))

    def test_actual_factory_payload_same_world_and_original_slots(self):
        with self.env.patches():
            native=self.open_factory();q=self.env.configuration
            self.assertEqual((q.base,q.root,q.world,q.cache),(self.guest.memory.base,self.b_world.root,self.b_world.world,self.env.cache))
            self.assertEqual(list(q.states),[a for _,a in self.guest.state_objects()])
            self.assertEqual((q.year,q.month,q.day,q.viewer,q.ruler),(203,8,11,2,952))
            self.assertEqual([(a.force,a.ruler,a.district) for a in q.actors],[(2,952,2),(12,666,11)])
            self.assertEqual((q.context.pid,q.context.birth,q.context.period),(self.guest.pid,self.birth,2))
            self.assertEqual(bytes(q.context.native.attachment).hex(),self.runner.guest.attachments['B'])
            self.assertEqual((q.storageVtable,q.readOriginal),(self.env.storage_vtable,self.env.read_original))
            self.assertIs(native.checked_port.sampler.reader,self.session.reader)
            native.checked_port.observe()
            native.checked_port.retire('owned cut retirement');restored=native.stop_restore()
            self.assertTrue(restored['native_bridge_restored']);self.assertTrue(self.env.restored)
        self.assertEqual(self.env.load_attempts,['checkpoint_planning_hold.dll','b_reward_owner.dll'])
        self.evidence(configure=port.base.values(q),restoration=restored)

    def test_unretired_first_load_refuses_before_module_or_configure(self):
        self.warm.current['refresh_load_retired']=False
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'fully retired') as caught:self.open_factory()
        self.assertIs(caught.exception.retained_native_port,self.session._b_reward_native)
        self.assertEqual(self.session.phase,'TERMINAL');self.assertFalse(self.env.calls)
        self.evidence()

    def test_sixth_storage_slot_conflict_refuses_before_load(self):
        self.b_world.memory.pack(self.env.storage_vtable+8,'<Q',self.env.read_original+16)
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'index 5'):self.open_factory()
        self.assertFalse(self.env.load_attempts);self.assertIsNone(self.env.configuration)
        self.evidence()

    def test_user_slot_conflict_refuses_before_load(self):
        self.b_world.memory.pack(self.guest.memory.base+0x12CC4D0,'<Q',self.guest.memory.base+0x3F9B08)
        with self.env.patches(),self.assertRaisesRegex(RuntimeError,'index 0'):self.open_factory()
        self.assertFalse(self.env.load_attempts);self.evidence()

    def test_copied_dll_tamper_refuses_before_load(self):
        copy=port.shutil.copyfile
        def damaged(source,target):
            result=copy(source,target)
            with Path(target).open('ab') as stream:stream.write(b'owned-tamper')
            return result
        with self.env.patches(),patch.object(port.shutil,'copyfile',side_effect=damaged), \
             self.assertRaisesRegex(RuntimeError,'Copied B binary differs'):self.open_factory()
        self.assertFalse(self.env.load_attempts);self.evidence()

    def test_profile_ruler_not_current_world_refuses_before_load(self):
        self.profile.target.ruler=953
        with self.env.patches(),self.assertRaisesRegex(ValueError,'Date/viewer/planning boundary changed'):self.open_factory()
        self.assertFalse(self.env.load_attempts);self.assertIsNone(self.env.configuration)
        self.evidence()

    def test_unknown_module_load_latches_shared_owners_no_retry(self):
        self.env.fault='unknown-load'
        with self.env.patches(),self.assertRaises(port.RemoteCallUnknown) as caught:self.open_factory()
        self.assertTrue(self.warm.calls.uncertain);self.assertTrue(self.session.factory.uncertain)
        self.assertEqual(self.session.phase,'TERMINAL');self.assertIs(caught.exception.retained_native_port,self.session._b_reward_native)
        self.assertEqual(len(self.env.load_attempts),1);self.assertIsNone(self.env.configuration)
        with self.env.patches(),self.assertRaises(Exception):self.open_factory()
        self.assertEqual(len(self.env.load_attempts),1);self.evidence()

    def test_second_owner_refused_without_a_second_loadlibrary(self):
        with self.env.patches():
            native=self.open_factory();before=list(self.env.calls)
            with self.assertRaisesRegex(RuntimeError,'One B reward owner'):self.open_factory()
            self.assertEqual(self.env.calls,before)
            native.checked_port.retire('owned end');native.stop_restore()
        self.evidence()


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix=='.py'}

if __name__=='__main__':
    full=sha(BUILD/'result.json');assert full==BUILD_SHA
    PRIVATE_INPUTS[str(BUILD/'result.json')]=full
    approved=port.approved_build(port.NativeBuild(BUILD,full))
    for p in [approved['dll'],*approved['dependencies']]:PRIVATE_INPUTS[str(p)]=sha(p)
    OUTPUT=PRIVATE/'b_reward_native_factory_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    fixture.predecessor.fixture.transport.OUTPUT=OUTPUT
    before=pins();stream=io.StringIO()
    suite=unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_'))
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite);after=pins()
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    report=dict(result='PASS' if result.wasSuccessful() and before==after else 'FAIL',tests=result.testsRun,
        sources=after,sources_unchanged=before==after,private_inputs=PRIVATE_INPUTS,cases=ROWS,
        production_factory_executed=True,production_native_install_executed=False,actual_build_copy_PE_and_six_slots=True,
        actual_first_formal_Session_TLS_and_GameReader=True,native_business_loader_RAM_RTTI_storage_OS_doubles=True,
        game_access=False,steam_access=False,full_world_verified=False,input_exclusion_proven=False,
        failures=[(str(t),s) for t,s in result.failures+result.errors])
    report['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(report['result']!='PASS')
