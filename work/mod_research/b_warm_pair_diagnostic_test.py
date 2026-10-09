"""Bounded diagnostic checks: actual files/builds, explicit memory/native doubles."""
from contextlib import ExitStack, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import hashlib
import io
import json
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_warm_pair_diagnostic as entry
import b_warm_pair_preflight as local
import b_warm_pair_preflight_test as local_test
from b_warm_coordinator_test import NativePortDouble
import b_warm_start as start
import b_warm_start_support as support
import checkpoint_complete_live_capture as capture
import a_save_local_binding as binding
import game_reader
# These production lazy dependencies are imported before source pins.
import run_autonomous_pilot,checkpoint_live_prefetch_start,a_save_runtime_control,b_warm_start_acceptance

OUTPUT=None;EVIDENCE=[]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReaderDouble:
    def __init__(self,pid=123):
        self.pid=pid;self.sha256=entry.GAME_SHA;self.closed=False;self.reads=0;self.drift=None
        self.memory=SimpleNamespace(base=0x140000000,read=self.read,handle=1)
        self.rows={self.memory.base+rva:raw for rva,_,raw in entry.rule_profiles()}

    def read(self,address,size):
        self.reads+=1
        value=self.rows[address]
        if self.drift and self.reads==self.drift:value=bytes([value[0]^1])+value[1:]
        if len(value)!=size:raise AssertionError('Wrong source read range')
        return value

    def close(self):self.closed=True


class Cases(unittest.TestCase):
    def setUp(self):
        local_test.OUTPUT=OUTPUT
        local_test.Cases.setUp(self)

    def inspect(self,reader,**kw):
        return entry.require_original_rules(reader,pid=123,birth=999,
            read_birth=kw.get('read_birth',lambda:999),range_check=kw.get('range_check',lambda a,n:None))

    def test_original_sources_and_each_of_six_patches_refused(self):
        r=ReaderDouble();answer=self.inspect(r)
        self.assertEqual(r.reads,12);self.assertTrue(answer['six_sources_original'])
        self.assertFalse(answer['input_exclusion_proven']);self.assertFalse(answer['scheduler_fence_proven'])
        for address in r.rows:
            with self.subTest(rva=hex(address-r.memory.base)):
                bad=ReaderDouble();v=bad.rows[address];bad.rows[address]=bytes([v[0]^1])+v[1:]
                with self.assertRaisesRegex(ValueError,'not original'):self.inspect(bad)
        EVIDENCE.append(dict(case='six-source-original-and-each-patch',actual_profiles=True,memory='DOUBLE'))

    def test_second_sample_birth_and_rx_failures_refuse(self):
        r=ReaderDouble();r.drift=7
        with self.assertRaisesRegex(ValueError,'not original'):self.inspect(r)
        births=iter([999,1000])
        with self.assertRaisesRegex(ValueError,'incarnation changed'):self.inspect(ReaderDouble(),read_birth=lambda:next(births))
        def no_rx(a,n):raise ValueError('Explicit RX range refusal')
        with self.assertRaisesRegex(ValueError,'RX'):self.inspect(ReaderDouble(),range_check=no_rx)
        with self.assertRaisesRegex(ValueError,'range check'):self.inspect(ReaderDouble(),range_check=lambda a,n:True)
        EVIDENCE.append(dict(case='sample-drift-birth-RX',native_reads='DOUBLE',write_calls=0))

    def command(self,mode):
        return [mode,'--pid','123','--plan',str(self.planpath),'--helper-build',str(self.args['helper_build']),
            '--helper-sha256',self.args['helper_sha256'],'--pair-build',str(self.args['pair_build']),
            '--pair-sha256',self.args['pair_sha256']]+(['--no-new-commands'] if mode=='--execute' else [])

    def run_main(self,mode,*,bad_rules=False,load_fail=False,close_fail=False):
        events=[];reader=ReaderDouble();owner=[];original=entry.require_original_rules
        native_root=self.folder/'runtime';native_root.mkdir()
        if bad_rules:
            address=next(iter(reader.rows));v=reader.rows[address];reader.rows[address]=b'\xff'+v[1:]
        def rules(r,*,pid,birth,**kw):
            events.append('rules')
            return original(r,pid=pid,birth=birth,read_birth=lambda:999,range_check=lambda a,n:None)
        def plan(*a):events.append('planning');return dict(pid=123,birth=999,base=reader.memory.base)
        actual_preflight=local.preflight
        def preflight(*a,**kw):events.append('preflight');return actual_preflight(*a,**kw)
        def new_reader(*,pid):events.append('reader');self.assertEqual(events[0],'preflight');return reader
        case=self;first=self.target.read_bytes();second=self.second.read_bytes()
        class Port(NativePortDouble):
            def __init__(self,*args,identity):
                case.assertEqual(identity,(123,999));case.assertTrue((native_root/'b_warm_start_claims/123-999.json').exists())
                super().__init__('second-load-failed' if load_fail else 'normal',case.target,first,second)
                self.calls=SimpleNamespace(uncertain=False);self.rule_checks=[];owner.append(self);events.append('resident')
            def close(self):
                super().close();events.append('port-close')
                if close_fail:raise RuntimeError('Explicit owned close failure')
        with ExitStack() as held,redirect_stdout(io.StringIO()):
            for module,name,value in ((local,'STEAM_HASHES',self.fake_hashes),(local,'preflight',preflight),
                (entry,'PRIVATE',native_root),(game_reader,'GameReader',new_reader),(capture,'process_birth',lambda r:999),
                (entry,'capture_planning',plan),(entry,'require_original_rules',rules),(entry,'require_no_debugger',lambda r:None),
                (entry,'refuse_prior_attempt',lambda p,b:events.append('prior-attempt-check')),
                (binding,'modules',lambda h:[]),(support,'storage_bindings',lambda *a,**kw:{}),
                (entry,'DiagnosticResident',Port)):
                held.enter_context(patch.object(module,name,value))
            code=entry.main(self.command(mode))
        results=list((native_root/'b_warm_pair_diagnostic_runs').glob('*/result.json'))
        self.assertEqual(len(results),1);report=json.loads(results[0].read_text())
        self.assertTrue(reader.closed)
        return code,report,events,owner,native_root

    def test_default_and_preflight_failure_never_open_reader(self):
        with patch.object(game_reader,'GameReader',side_effect=AssertionError('No process allowed')) as reader,redirect_stdout(io.StringIO()):
            self.assertEqual(entry.main([]),0)
            with patch.object(local,'preflight',side_effect=ValueError('local file/build rejected')):
                with self.assertRaisesRegex(ValueError,'local file'):entry.main(self.command('--check'))
            reader.assert_not_called()
        EVIDENCE.append(dict(case='default-or-local-preflight-failure',process_opens=0,claims=0))

    def test_check_real_preflight_no_claim_or_install(self):
        code,r,events,owners,root=self.run_main('--check')
        self.assertEqual(code,0);self.assertEqual(r['result'],'PASS_READ_ONLY_RULES_FREE_PAIR_CHECK')
        self.assertFalse((root/'b_warm_start_claims').exists());self.assertEqual(owners,[])
        self.assertEqual(events.count('preflight'),2)
        EVIDENCE.append(dict(case='check-only',order=events,result=r,memory='DOUBLE',actual_files_and_builds=True))

    def test_rules_refusal_precedes_claim_and_install(self):
        code,r,events,owners,root=self.run_main('--execute',bad_rules=True)
        self.assertEqual(code,1);self.assertEqual(r['result'],'REFUSED_BEFORE_CLAIM')
        self.assertFalse((root/'b_warm_start_claims').exists());self.assertEqual(owners,[])
        self.assertIn('not original',r['error'])
        EVIDENCE.append(dict(case='patched-source-before-claim',order=events,result=r))

    def test_execute_actual_file_staging_with_native_port_double(self):
        code,r,events,owners,root=self.run_main('--execute')
        self.assertEqual(code,0);self.assertEqual(r['result'],'PASS_TWO_WARM_DIAGNOSTIC_LOADS')
        self.assertTrue((root/'b_warm_start_claims/123-999.json').exists())
        self.assertEqual([x for x in owners[0].events if x[0]=='load'],[['load',0],['load',1]])
        self.assertEqual(self.target.read_bytes(),self.second.read_bytes())
        self.assertFalse(r['input_exclusion_proven']);self.assertFalse(r['scheduler_fence_proven'])
        EVIDENCE.append(dict(case='actual-file-two-load-orchestration',order=events,native_order=owners[0].events,
            native_port='DOUBLE',memory='DOUBLE',actual_preflight_builds=True,actual_windows_staging=True))

    def test_failed_second_load_keeps_claim_abort_lease_and_cleanup_record(self):
        code,r,events,owners,root=self.run_main('--execute',load_fail=True,close_fail=True)
        self.assertEqual(code,1);self.assertEqual(r['result'],'INCOMPLETE_RETAIN_EVIDENCE')
        self.assertTrue((root/'b_warm_start_claims/123-999.json').exists())
        self.assertTrue(owners[0].abort_lease_blocked);self.assertIn('close_error',r)
        self.assertFalse(r['native_drained']);self.assertFalse(r['staging_reuse_authorized'])
        self.assertEqual([x for x in owners[0].events if x[0]=='load'],[['load',0],['load',1]])
        EVIDENCE.append(dict(case='load-failed-cleanup-failed',order=events,native_order=owners[0].events,result=r,
            claim_retained=True,original_reports_retained=True,retry=False))

    def test_resident_inheritance_checks_each_native_edge(self):
        events=[];reader=ReaderDouble()
        def check(*a,**kw):events.append('check');return {'six_sources_original':True}
        def init(port,*a,**kw):port.reader=reader
        with patch.object(entry,'require_original_rules',check),patch.object(entry,'require_no_debugger',lambda r:None),\
             patch.object(entry.Resident,'__init__',init),\
             patch.object(entry.Resident,'open_bank',lambda s,i:events.append('open') or i),\
             patch.object(entry.Resident,'load',lambda *a:events.append('load') or {}),\
             patch.object(entry.Resident,'finish',lambda s:events.append('finish')):
            port=entry.DiagnosticResident(reader,identity=(123,999))
            port.open_bank(0);port.load({'index':0},None,b'');port.finish()
        self.assertEqual(events,['check','check','open','check','load','check','check','finish','check'])
        successful_order=list(events)
        stopped=[]
        with patch.object(entry,'require_original_rules',check),patch.object(entry,'require_no_debugger',lambda r:None),\
             patch.object(entry.Resident,'__init__',init),\
             patch.object(entry.Resident,'abort',lambda s:stopped.append(s.current)):
            port=entry.DiagnosticResident(reader,identity=(123,999));old={'index':0,'diagnostic_load_retired':True}
            second={'index':1,'install_completed':False};port.current=old
            with patch.object(port,'check_rules',side_effect=ValueError('second source rejected')):
                with self.assertRaisesRegex(ValueError,'second source'):port.load(second,None,b'')
            self.assertIs(port.current,second);port.abort()
            self.assertEqual(stopped,[second]);self.assertFalse(second['install_completed'])
            stopped.clear();third={'index':1}
            with patch.object(port,'check_rules',side_effect=[None,ValueError('post retirement source rejected')]),\
                 patch.object(entry.Resident,'load',return_value={}):
                with self.assertRaisesRegex(ValueError,'post retirement'):port.load(third,None,b'')
            self.assertTrue(third['diagnostic_load_retired']);port.abort();self.assertEqual(stopped,[])
            unfinished={'index':1,'install_completed':True}
            with patch.object(port,'check_rules',return_value=None),\
                 patch.object(entry.Resident,'load',side_effect=ValueError('unfinished native load')):
                with self.assertRaisesRegex(ValueError,'unfinished'):port.load(unfinished,None,b'')
            port.abort();self.assertEqual(stopped,[unfinished])
        EVIDENCE.append(dict(case='actual-subclass-edges',order=successful_order,parent_native_methods='DOUBLE',
            second_precheck_never_stops_previous=True,retired_failure_no_stop=True,unfinished_delegates_abort=True))


def pins():
    paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None)}
    paths.add(Path(__file__).resolve())
    paths.add(HERE/'human_ai_runtime_profile.h')
    return {str(p):sha(p) for p in sorted(paths) if p.is_relative_to(ROOT) and p.suffix in ('.py','.h')}


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_warm_pair_diagnostic_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    before=pins();stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8')
    sources=pins();stable=all(sources.get(k)==v for k,v in before.items())
    private={}
    for path in (local_test.HELPER,local_test.PAIR):
        private[str(path)]=sha(path);record=json.loads(path.read_text())
        for field in ('sources','private','generated','binaries'):private.update(record.get(field,{}))
    report=dict(result='PASS' if result.wasSuccessful() and result.testsRun==8 and stable else 'FAIL',tests=result.testsRun,
        family='san14.b-warm-pair-diagnostic-test.v1',sources=sources,private=private,inputs_unchanged=stable,
        cases=EVIDENCE,game_access=False,steam_access=False,native_load=False,
        actual_preflight_builds=True,actual_windows_files=True,reader_and_native_port='EXPLICIT_DOUBLES',
        artifacts={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()},
        failures=[(str(t),detail) for t,detail in result.failures+result.errors])
    (OUTPUT/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(OUTPUT/'result.json');print(stream.getvalue());raise SystemExit(0 if report['result']=='PASS' else 1)
