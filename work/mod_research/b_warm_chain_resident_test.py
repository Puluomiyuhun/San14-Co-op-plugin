"""Three-load resident: owned files, actual helper DLL, explicit game/load doubles."""
import ctypes as C
from datetime import datetime
import hashlib,io,json,os,shutil,sys,unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch
P=Path(__file__).resolve().parent;ROOT=P.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_chain_resident as subject
import b_warm_chain_coordinator_contract as wire
from b_warm_chain_coordinator_test import Input
from b_warm_profile_capture import profile_from_dict
import b_warm_staging as files
import b_warm_refresh_contract as refresh_wire
import b_warm_start_support as support
import checkpoint_complete_live_capture as capture
import a_save_runtime_control as transport

OUT=None;BUILD=None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class FilePort:
    """Writes only private fixture files, in place of the game's serializer."""
    def __init__(self,case,fail=None):self.case=case;self.fail=fail;self.events=[];self.aborted=[]
    def open_bank(self,index):self.events.append(('open',index));return dict(index=index)
    def authorize_next(self,bank,profile):
        self.case.assertIn(('retired',bank['index']-1),self.events);self.events.append(('authorize',bank['index']))
    def load(self,bank,profile,raw,*,target,previous,backup):
        self.current=bank['index'];self.case.assertEqual(files.read_file(target)[0],previous)
        self.case.assertEqual(backup.read_bytes(),target.read_bytes());self.events.append(('load',self.current))
        if self.current==self.fail:raise RuntimeError('explicit native substitute failure')
        target.write_bytes(raw);self.events.append(('retired',self.current));return dict(native_load_double=True)
    def abort(self):self.aborted.append(self.current)
    def finish(self):self.events.append(('finish',3))

class Cases(unittest.TestCase):
    def setUp(self):
        self.folder=OUT/self._testMethodName;self.folder.mkdir()
        self.target=self.folder/files.NAME;self.target.write_bytes(b'old owned slot')
        self.sources=[];self.raw_profiles=[]
        dates=[((203,8,11),(203,8,11)),((203,8,11),(203,8,21)),((203,8,21),(203,9,1))]
        for i,(before,loaded) in enumerate(dates):
            p=self.folder/f'source-{i}.s14';p.write_bytes(bytes([49+i])*(913+i));self.sources.append(p)
            self.raw_profiles.append(dict(file=dict(name=files.NAME,slot=63,size=p.stat().st_size,sha256=sha(p)),
                before=dict(zip(('year','month','day'),before)),loaded=dict(zip(('year','month','day'),loaded)),
                source=dict(ruler=666,force=12,district=11),target=dict(ruler=952,force=2,district=2),currentForce=12 if i==0 else 2))
        self.profiles=[profile_from_dict(x) for x in self.raw_profiles];self.initial=files.read_file(self.target)[0]
        self.run=self.folder/'run';self.run.mkdir()

    def test_three_files_native_publication_backups_and_rollover(self):
        port=FilePort(self);seen=[]
        with patch.object(files,'apply',side_effect=AssertionError('Python staging forbidden')):
            r=subject.run_three(port,self.profiles,self.target,self.sources,self.initial,self.run,on_complete=lambda i,r:seen.append(i))
        self.assertEqual(r['result'],'PASS_THREE_WARM_REFRESH_LOADS');self.assertEqual(seen,[0,1,2])
        self.assertEqual((self.run/'bank-3-old-target.s14').read_bytes(),self.sources[1].read_bytes())
        self.assertEqual(self.target.read_bytes(),self.sources[2].read_bytes());self.assertFalse(r['room_ready'])
        self.assertEqual(port.events[-1],('finish',3));self.assertEqual(port.aborted,[])

    def test_failed_third_keeps_second_and_does_not_finish(self):
        port=FilePort(self,2)
        with self.assertRaisesRegex(RuntimeError,'substitute failure'):subject.run_three(port,self.profiles,self.target,self.sources,self.initial,self.run)
        self.assertEqual(self.target.read_bytes(),self.sources[1].read_bytes());self.assertEqual(port.aborted,[2])
        self.assertNotIn(('finish',3),port.events)

    def test_lineage_reuse_and_wrong_month_refused_before_native(self):
        subject.validate_three(self.profiles)
        for change in ('month','sha','force','fourth'):
            profiles=[type(p).from_buffer_copy(bytes(p)) for p in self.profiles]
            if change=='month':profiles[2].loaded.month=8
            if change=='sha':profiles[2].file.sha256[:]=profiles[1].file.sha256
            if change=='force':profiles[2].currentForce=12
            if change=='fourth':profiles.append(profiles[-1])
            port=FilePort(self)
            with self.subTest(change=change),self.assertRaises(ValueError):subject.run_three(port,profiles,self.target,self.sources,self.initial,self.run)
            self.assertEqual(port.events,[])

    def bare(self):
        r=subject.Resident.__new__(subject.Resident);r.calls=N(uncertain=False);r.nonce=bytes([0x63])*32
        r.folder=self.run;r.serial=0;r.api=None;r.banks=[];r.prepared=True;r.ruler=952
        r.reader=N(pid=os.getpid());r.before=dict(pid=os.getpid(),birth=17,base=99)
        return r

    def test_unaccepted_retired_load_cannot_open_authorize_or_finish(self):
        r=self.bare();old=dict(module=10,warm_load_retired=True,refresh_load_retired=True)
        r.banks=[old]
        with self.assertRaisesRegex(ValueError,'fully accepted'):r.open_bank(1)
        new=dict(module=20);r.banks.append(new)
        with self.assertRaisesRegex(ValueError,'fully accepted'):r.authorize_next(new,self.profiles[1])
        r.banks.append(dict(module=30,warm_load_retired=True,refresh_load_retired=True,load_accepted=True))
        with self.assertRaises(ValueError):r.finish()

    def test_transport_logging_failure_stops_all_later_native_calls(self):
        r=self.bare();r.helper=dict(addresses={wire.EXPORTS[3]:123})
        with patch.object(transport,'remote_call',side_effect=OSError('evidence write failed')) as call:
            with self.assertRaises(OSError):r.hand(wire.Observe)
            self.assertTrue(r.calls.uncertain)
            with self.assertRaisesRegex(ValueError,'Unknown previous'):r.hand(wire.Observe)
            self.assertEqual(call.call_count,1)

    def native_helper(self):
        r=self.bare();dllpath=self.folder/'coordinator.dll';shutil.copyfile(BUILD/'coordinator.dll',dllpath)
        dll=C.WinDLL(str(dllpath));banks=[]
        for i in range(3):
            path=self.folder/f'bank-{i}.dll';shutil.copyfile(BUILD/'bank.dll',path);banks.append(C.WinDLL(str(path)))
        k=C.WinDLL('kernel32',use_last_error=True);k.VirtualAlloc.argtypes=[C.c_void_p,C.c_size_t,wire.U32,wire.U32];k.VirtualAlloc.restype=C.c_void_p
        memory=k.VirtualAlloc(None,4096,0x3000,4);self.assertTrue(memory)
        original=C.cast(k.GetCurrentProcessId,C.c_void_p).value;slots=(wire.U64*6).from_address(memory);data=Input()
        for i in range(6):slots[i]=original;data.slots[i]=memory+i*8;data.originals[i]=original
        def setbank(i,mode):
            data.mode=mode;data.seed=i;fn=banks[i].FixtureSet;fn.argtypes=[C.c_void_p];fn.restype=wire.U32;self.assertEqual(fn(C.byref(data)),0)
        for i in range(3):setbank(i,0)
        k.GetCurrentProcess.restype=C.c_void_p;k.GetProcessTimes.argtypes=[C.c_void_p]+[C.POINTER(wire.U64)]*4
        times=[wire.U64() for _ in range(4)];self.assertTrue(k.GetProcessTimes(k.GetCurrentProcess(),*[C.byref(x) for x in times]))
        r.before['birth']=times[0].value;r.helper=dict(addresses={n:C.cast(getattr(dll,n),C.c_void_p).value for n in wire.EXPORTS})
        r.native_refs=(dll,banks,data,slots)
        def local_rpc(api,address,raw,*args):
            buffer=C.create_string_buffer(raw,len(raw));fn=C.WINFUNCTYPE(wire.U32,C.c_void_p)(address);code=fn(buffer)
            return code,bytes(buffer)
        return r,banks,setbank,local_rpc,data

    def test_resident_calls_actual_helper_through_three_retained_banks(self):
        r,banks,setbank,rpc,data=self.native_helper()
        with patch.object(transport,'remote_call',side_effect=rpc),patch.object(subject,'capture_planning',side_effect=lambda *a,**k:dict(r.before)):
            r.hand(wire.Prepare,pid=os.getpid(),birth=r.before['birth'],first=banks[0]._handle,slots=list(data.slots),originals=list(data.originals))
            r.banks=[dict(module=banks[0]._handle,warm_load_retired=True,refresh_load_retired=True,load_accepted=True)]
            setbank(0,1)
            for i in (1,2):
                bank=dict(module=banks[i]._handle,index=i);r.banks.append(bank);r.authorize_next(bank,self.profiles[i]);self.assertTrue(bank['authorized'])
                with self.assertRaisesRegex(ValueError,'once-only'):r.authorize_next(bank,self.profiles[i])
                bank.update(warm_load_retired=True,refresh_load_retired=True,load_accepted=True);setbank(i,1)
            r.finish();state=r.hand(wire.Observe)
            self.assertEqual(list(state.completed),[1,1,1]);self.assertEqual(state.certificates[1].attempt,78)
            self.assertNotEqual(bytes(state.certificates[0]),bytes(state.certificates[1]))
            with self.assertRaises(ValueError):r.open_bank(3)

    def load_fixture(self,bad_snapshot=False,fail_completion_write=False):
        r=self.bare();r.timeout=2;r.bank_sha='a'*64;r.steam={};r.first_hooks=[]
        r.banks=[dict(index=i,module=100+i,warm_load_retired=True,refresh_load_retired=True,load_accepted=True) for i in (0,1)]
        bank=dict(index=2,module=102,authorized=True,folder=self.run,description=dict(readBridge=1234),path=self.folder/'unused.dll',addresses={
            'DescribeBWarmRefreshOwner':1,'InstallBWarmRefreshOwner':2,'GetBWarmRefreshReport':3})
        r.banks.append(bank);profile=self.profiles[2];raw=self.sources[2].read_bytes();backup=self.folder/'backup.s14';backup.write_bytes(self.target.read_bytes())
        snapshot=dict(date=dict(year=203,month=9,day=2 if bad_snapshot else 1),player=dict(force_id=2,ruler_id=952))
        r.reader.snapshot=lambda:dict(snapshot);r.api=N(modules=lambda:[])
        r.calls.call=lambda address,*a,**k:(0,bytes(refresh_wire.Description()) if address==1 else b'owned report')
        state=N(currentGeneration=3,banks=[100,101,102],completed=[1,1,1],certificateCount=2)
        r.hand=lambda kind:state
        def native_complete(*a,**k):self.target.write_bytes(raw);return dict(receipt_key='owned native load substitute')
        real_save=subject.save_new
        def save(path,value):
            if fail_completion_write and Path(path).name=='completion.json':raise OSError('final evidence failure')
            real_save(path,value)
        with ExitStack() as s:
            for obj,name,value in ((subject,'capture_planning',dict(r.before)),(subject,'storage_bindings',dict(write={})),
                (support,'live_hook_evidence',[]),(support,'build_config',N(attempt=77)),(subject,'wrap_owner_config',N()),
                (subject,'make_config',C.c_uint32(42)),(subject,'validate_completed',dict(retired=True)),
                (capture,'process_birth',17),(refresh_wire,'decode',N(warm=N(bank=b''))),
                (subject.bank_wire.old,'decode_description',bank['description'])):
                s.enter_context(patch.object(obj,name,return_value=value))
            s.enter_context(patch.object(subject,'completion',side_effect=native_complete));s.enter_context(patch.object(subject,'save_new',side_effect=save))
            if bad_snapshot or fail_completion_write:
                with self.assertRaises((ValueError,OSError)):r.load(bank,profile,raw,target=self.target,previous=self.initial,backup=backup)
                self.assertTrue(r._chain_failed);self.assertTrue(bank['warm_load_retired']);self.assertTrue(bank['refresh_load_retired'])
                self.assertFalse(bank.get('load_accepted',False))
                with self.assertRaises(ValueError):r.finish()
                with self.assertRaises(ValueError):r.load(bank,profile,raw,target=self.target,previous=self.initial,backup=backup)
            else:
                result=r.load(bank,profile,raw,target=self.target,previous=self.initial,backup=backup)
                self.assertTrue(bank['load_accepted']);self.assertTrue(result['target_lease_released']);r.finish()
                self.assertTrue((self.run/'completion.json').is_file())

    def test_third_load_body_accepts_only_after_postconditions(self):self.load_fixture()
    def test_third_load_wrong_final_world_is_terminal(self):self.load_fixture(bad_snapshot=True)
    def test_third_load_final_evidence_failure_is_terminal(self):self.load_fixture(fail_completion_write=True)

def main():
    global OUT,BUILD
    BUILD=Path(sys.argv[1]).resolve()
    approval=json.loads((BUILD/'result.json').read_text());assert approval['result']=='PASS' and approval['chain_exports_passed']
    for section in ('sources','generated','binaries'):
        for p,h in approval[section].items():assert sha(p)==h,(section,p)
    OUT=PRIVATE/'b_warm_chain_resident_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUT.mkdir(parents=True)
    names={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and str(Path(m.__file__).resolve()).startswith(str(ROOT)) and str(m.__file__).endswith('.py')}
    names.add(Path(__file__).resolve());pins={str(p):sha(p) for p in names}
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUT/'tests.log').write_text(log.getvalue(),encoding='utf-8');stable=all(sha(p)==h for p,h in pins.items())
    report=dict(result='PASS' if result.wasSuccessful() and stable else 'FAIL',tests=result.testsRun,sources=pins,inputs_unchanged=stable,
        helper_build=dict(path=str(BUILD/'result.json'),sha256=sha(BUILD/'result.json')),game_process_access=False,steam_access=False,
        actual_owned_helper_DLL=True,native_load_RAM_are_explicit_doubles=True,
        artifacts={str(p):sha(p) for p in OUT.rglob('*') if p.is_file()})
    path=OUT/'result.json';path.write_text(json.dumps(report,indent=2)+'\n');print(log.getvalue());print(json.dumps(dict(result=report['result'],path=str(path),sha256=sha(path))))
    return int(report['result']!='PASS')
if __name__=='__main__':raise SystemExit(main())
