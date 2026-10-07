"""Independent pure/mock launcher review. NEVER constructs a live process API."""
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import contextlib,copy,ctypes as C,hashlib,io,json,re,struct,sys,types,unittest
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import checkpoint_load_mode_contract as contract
import checkpoint_load_mode_start as launcher
from checkpoint_cache_graph import inspect_cache
from checkpoint_cache_graph_test import CacheGraphTests

OUT=ROOT/'checkpoint_load_mode_launcher_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
OUT.mkdir(parents=True,exist_ok=False)

def valid_report(execute):
    native=contract.Report();native.magic=contract.MAGIC;native.size=C.sizeof(native);native.version=1
    r=contract.decode(bytes(native));base=0x180000000
    before={'base':hex(base),'pinned_user':'0x200000','pinned_game':'0x300000','pinned_world':'0x400000',
            'cache_graph':{'cache':'0x500000'},'global_rng':1234,'cache_mode':1,
            'mode_hook_pages':{'user':{'protect':2},'load_update':{'protect':2}}}
    r.update(state=7 if execute else 3,execute=int(execute),base=base,user=0x200000,game=0x300000,world=0x400000,cache=0x500000,
             initialRng=1234,initialMode=1,userCaller=base+0x50B785,installerThread=19,queueThread=21,firstUserCallId=1)
    for name,count in [('user',2 if execute else 1),('menu',1 if execute else 0)]:
        r[name+'BeforeCalls']=r[name+'AfterCalls']=count
        for key in ('started','native_started','native_returned','before_calls','after_calls'):r[name+'Bridge'][key]=count
        r[name+'Bridge']['configured']=r[name+'Bridge']['module_pinned']=int(bool(count))
    for name,rva,original in [('userSlot',0x12CC4A8+0x28,0x3F9B00)]+([('menuSlot',0x12DB4C0+0x28,0x4AA200)] if execute else []):
        r[name].update(slot=base+rva,original=base+original,observed=base+original,hook=0x600000,
                       restored=1,protectionRestored=1,initialProtection=2,observedProtection=2)
    if execute:
        for key in ('intentCreated','intentFlushed','queueCalls','queueReturned','queueVerified','menuAssociation',
                    'menuOriginalReturned','menuGuardBefore','menuGuardAfter','cancelCalls','cancelReturned','cancelQueueVerified','returnSeen','returnMatched'):r[key]=1
        r.update(queueAfter=1,cancelAfter=1,returnedMode=0,returnedRng=1234,menuThread=21,returnThread=21,
                 menuCaller=base+0x50B785,queuedState=0x700000,returnUserCallId=2,menuCallId=1)
    return r,before

class FakeKernel:
    def __init__(self,wait=0,create=123,exitcode=0):self.wait=wait;self.create=create;self.exitcode=exitcode;self.freed=[];self.closed=[]
    def VirtualAllocEx(self,*args):return 0xabc000
    def CreateRemoteThread(self,*args):return self.create
    def WaitForSingleObject(self,*args):return self.wait
    def GetExitCodeThread(self,thread,pointer):pointer._obj.value=self.exitcode;return 1
    def CloseHandle(self,handle):self.closed.append(handle);return 1
    def VirtualFreeEx(self,handle,pointer,*args):self.freed.append(pointer);return 1

class ReviewTests(unittest.TestCase):
    def test_cpp_header_and_ctypes_complete_abi(self):
        header=(ROOT/'checkpoint_load_mode_pilot.h').read_text()
        body=re.search(r'struct CheckpointLoadModeReport \{(.*?)\n\};',header,re.S).group(1)
        sizes={'uint64_t':(8,8),'uint32_t':(4,4),'LONG':(4,4),'LoadModeSlotReport':(48,8),'CheckpointPushBridgeStats':(64,8),'char':(1,1)}
        expected={};offset=0
        for statement in body.split(';'):
            statement=statement.strip()
            if not statement:continue
            kind,decl=statement.split(None,1);size,alignment=sizes[kind]
            for item in decl.split(','):
                name,amount=re.match(r'(\w+)(?:\[(\d+)\])?',item.strip()).groups();amount=int(amount or 1)
                offset=(offset+alignment-1)//alignment*alignment;expected[name]=offset;offset+=size*amount
        self.assertEqual((offset+7)//8*8,592);self.assertEqual(C.sizeof(contract.Report),592)
        self.assertEqual(expected,{name:getattr(contract.Report,name).offset for name,_ in contract.Report._fields_})
        self.assertIn('nativeCancellationSeen',expected)
        config=struct.pack('<QIIIIQQQ',contract.MAGIC,1104,1,0,100,200,300,400)+bytes(1024+32)
        self.assertEqual(len(config),1104)

    def test_decode_rejects_incomplete_abi(self):
        native=contract.Report();native.magic=contract.MAGIC;native.size=592;native.version=1;raw=bytes(native)
        for bad in (raw[:-1],raw+bytes(1),bytes(8)+raw[8:],raw[:12]+struct.pack('<I',2)+raw[16:]):
            with self.subTest(length=len(bad)),self.assertRaises(ValueError):contract.decode(bad)

    def test_report_rejects_incomplete_native_lifecycle(self):
        for execute in (False,True):
            valid,before=valid_report(execute);self.assertTrue(contract.report_ok(valid,execute,before))
            cases=[('state',6),('callbackActive',1),('error',1),('stopRequested',1),('exceptionCode',5),('nativeLoadAuthorized',1),
                   ('customMetadataWrites',1),('fullWorldVerified',1),('nativeCancellationSeen',1),('user',8),('cache',8),('initialRng',2)]
            if execute:cases += [('queueCalls',2),('intentFlushed',0),('cancelReturned',0),('cancelQueueVerified',0),('returnMatched',0),('returnedMode',1),('returnedRng',99),('menuThread',0),('returnThread',0),('returnUserCallId',1)]
            else:cases += [('queueCalls',1),('intentCreated',1),('cancelCalls',1),('returnSeen',1)]
            for key,value in cases:
                bad=copy.deepcopy(valid);bad[key]=value
                with self.subTest(execute=execute,key=key):self.assertFalse(contract.report_ok(bad,execute,before))
            for component,key,value in [('userBridge','active',1),('userBridge','native_returned',0),('menuBridge','abnormal_exits',1),('userSlot','observedProtection',4),('userSlot','observed',9)]:
                bad=copy.deepcopy(valid);bad[component][key]=value
                with self.subTest(execute=execute,component=component,key=key):self.assertFalse(contract.report_ok(bad,execute,before))

    def test_distinct_worker_threads_between_paired_callbacks(self):
        # The production bridge pairs each individual before/after invocation.
        # The engine may move later frame callbacks to another worker.
        valid,before=valid_report(True)
        valid.update(queueThread=21,menuThread=22,returnThread=23)
        self.assertTrue(contract.report_ok(valid,True,before))

    def test_get_report_completed_frees_buffer(self):
        k=FakeKernel();native=contract.Report();native.magic=contract.MAGIC;native.size=592;native.version=1
        api=types.SimpleNamespace(k=k,handle=17);reader=types.SimpleNamespace(memory=types.SimpleNamespace(read=lambda p,n:bytes(native)))
        self.assertEqual(launcher.get_report(api,reader,1234)['size'],592);self.assertEqual(k.freed,[0xabc000]);self.assertEqual(k.closed,[123])

    def test_get_report_timeout_retains_buffer(self):
        for wait in (258,0xffffffff):
            k=FakeKernel(wait=wait);api=types.SimpleNamespace(k=k,handle=17);reader=types.SimpleNamespace(memory=None)
            with self.subTest(wait=wait),self.assertRaises(AssertionError):launcher.get_report(api,reader,1234)
            self.assertEqual(k.freed,[]);self.assertEqual(k.closed,[123])

    def test_get_report_create_or_decode_failure_cleanup(self):
        for create,exitcode in ((0,0),(123,1),(123,0)):
            k=FakeKernel(create=create,exitcode=exitcode);api=types.SimpleNamespace(k=k,handle=17);reader=types.SimpleNamespace(memory=types.SimpleNamespace(read=lambda p,n:b'bad'))
            with self.subTest(create=create,exitcode=exitcode),self.assertRaises((AssertionError,ValueError)):launcher.get_report(api,reader,1234)
            self.assertEqual(k.freed,[0xabc000]);self.assertEqual(k.closed,[123] if create else [])

    def test_default_main_never_constructs_writer_api(self):
        calls=[]
        class Reader:
            def __init__(self):calls.append('readonly_reader')
            def close(self):calls.append('reader_close')
        def forbidden(*a,**k):raise AssertionError('writer/native API reached')
        modules={'battle_observer':types.SimpleNamespace(BattleObserver=Reader),
                 'run_autonomous_pilot':types.SimpleNamespace(ProcessAPI=forbidden,pefile=None),
                 'checkpoint_live_capture':types.SimpleNamespace(sample=forbidden)}
        directory=OUT/'default';directory.mkdir();sample={'result':'PASS','reasons':[]}
        with patch.dict(sys.modules,modules),patch.object(sys,'argv',['checkpoint_load_mode_start.py']),patch.object(launcher,'ROOT',directory),patch.object(launcher,'precheck',return_value=sample),contextlib.redirect_stdout(io.StringIO()):launcher.main()
        self.assertEqual(calls,['readonly_reader','reader_close'])
        self.assertFalse(list(directory.glob('*claim*')))
        result=list(directory.rglob('result.json'));self.assertEqual(len(result),1);self.assertEqual(json.loads(result[0].read_text())['result'],'PASS')

    def test_exact_fixture_gate_hash_and_cases(self):
        cases=tuple(f'case{i}' for i in range(10));source={'source.cpp':'a'*64};approved='b'*64
        evidence={'schema':'san14.checkpoint-load-mode-fixtures.v1','result':'PASS','game_process_access':False,'production_config_bytes':1104,'report_bytes':592,
                  'dll_sha256':approved,'source_sha256':source,'fixture_dll_sha256':'c'*64,'fixture_binary_sha256':'d'*64,
                  'cases':[{'case':x,'passed':True,'exit_code':0} for x in cases]}
        def fake_sha(path):return {'checkpoint_load_mode_pilot.dll':approved,'checkpoint_load_mode_fixture.dll':'c'*64,'checkpoint_load_mode_fixture.exe':'d'*64}.get(Path(path).name,'e'*64)
        def run(value):
            with patch.dict(sys.modules,{'checkpoint_load_mode_test':types.SimpleNamespace(CASES=cases,fingerprint=lambda:source)}),patch.object(launcher,'load',side_effect=lambda p:copy.deepcopy(value) if Path(p).name=='evidence.json' else {'result':'PASS'}),patch.object(launcher,'sha',side_effect=fake_sha):return launcher.fixture_gate(Path('evidence.json'))
        self.assertEqual(run(evidence)['dll_sha256'],approved)
        for key,value in [('dll_sha256','f'*64),('source_sha256',{}),('fixture_dll_sha256','f'*64),('fixture_binary_sha256','f'*64),('report_bytes',520),('result','INCOMPLETE'),('game_process_access',True),('cases',evidence['cases'][:-1])]:
            bad=copy.deepcopy(evidence);bad[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):run(bad)

    def test_group_nodes_can_remain_unindexed(self):
        f=CacheGraphTests();f.setUp();f.node(slot=None)
        graph=inspect_cache(f.read,f.cache);self.assertEqual(graph['unindexed_owned_nodes'],1)

    def test_head_cannot_hide_inside_data_payload(self):
        f=CacheGraphTests();f.setUp();node=f.node(slot=None);head=node+0x20
        f.q(f.cache+0x410,head);f.q(head,head);f.q(head+8,head)
        with self.assertRaises(ValueError):inspect_cache(f.read,f.cache)

if __name__=='__main__':
    stream=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReviewTests);result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (OUT/'unittest.txt').write_text(stream.getvalue(),encoding='utf8')
    paths=['checkpoint_load_mode_start.py','checkpoint_load_mode_contract.py','checkpoint_load_mode_capture.py','checkpoint_cache_graph.py','checkpoint_load_mode_pilot.h','checkpoint_load_mode_launcher_test.py']
    report={'schema':'san14.checkpoint-load-mode-launcher-review.v1','result':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
            'failures':[{'test':str(test),'failure':error} for test,error in result.failures+result.errors],
            'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths},
            'game_access':False,'production_dll_loaded':False,'scope':'Real Python launcher/contract/cache functions with ctypes ABI and mocks. No game process or native call. Does not prove actual production hook lifecycle.'}
    (OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':report['result'],'tests':result.testsRun,'path':str(OUT/'result.json'),'failures':report['failures']}));raise SystemExit(not result.wasSuccessful())
