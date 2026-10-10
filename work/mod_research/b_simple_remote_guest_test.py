"""Actual B external entry/Console/Runner/TLS/Session, explicit OS/business seams.

File approval cases use actual archived build receipts and current source hashes.
Run cases replace only file preflight/native installation/RAM/native business and
window transport, never the production run, Operator, Console or typed lease.
"""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import contextlib,hashlib,io,json,sys,threading,time,unittest

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_input_reward_runner_test as base
import b_simple_remote_guest as entry
import simple_remote_console
from reward_observed_context import CheckedPort
from b_remote_session import REQUIRED_SOURCES

PAIR=PRIVATE/'b_warm_refresh_pair_runs/20261009-215046-831686/result.json'
HELPER=PRIVATE/'b_warm_coordinator_build_runs/20261009-181031-457801/result.json'
REWARD=PRIVATE/'b_reward_owner_runs/20261010-095208-139540'
STAGE=PRIVATE/'human_rules_activation_v2_runs/20261008-000431-509932/production.dll'
PUBLISHER=PRIVATE/'human_rules_activation_publish_v2_runs/20261008-000527-938626/inputs/publisher-production.exe'
OUTPUT=None;ROWS=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pins():
    result=base.prior.pins()
    result.update({str((HERE/n).resolve()):sha(HERE/n) for n in REQUIRED_SOURCES})
    return result


class Cases(base.Cases):
    def setUp(self):
        super().setUp();self.emitted=[]
        self.config['local']['steam_paths']={name:str(self.folder/name) for name in entry.startup.STEAM_HASHES}
        self.checked['sources']=pins()
        self.simple=dict(schema=entry.SCHEMA,startup=self.config,
            reward_build=dict(run=str(REWARD),sha256=sha(REWARD/'result.json')),
            input_build=dict(run=str(base.BUILD.run),sha256=base.BUILD.sha256),
            window=dict(handle=self.env.window,thread=self.env.window_thread,timeout_ms=50),
            report_key_path=str(self.report_path),cut_key_path=str(self.cut_path))
        self.after_open=None;self.request_interceptor=None
        request=self.link.control.request
        def intercepted(value):
            if self.request_interceptor is not None:return self.request_interceptor(value,request)
            return request(value)
        self.link.control.request=intercepted

    def actual_files(self):
        c=deepcopy(self.simple);v=c['startup']['local']
        v['pair_build']=dict(path=str(PAIR),sha256=sha(PAIR));v['helper_build']=dict(path=str(HELPER),sha256=sha(HELPER))
        v['rules_build']=dict(stage=str(STAGE),publisher=str(PUBLISHER))
        p=self.folder/'actual-sources.json'
        p.write_text(json.dumps(dict(result='PASS',inputs_unchanged=True,sources=pins())),encoding='utf-8')
        v['source_manifest']=dict(path=str(p),sha256=sha(p));return c

    def execute_console(self,commands):
        actual_runner=entry.Runner;actual_event=entry.Operator.event
        def factory(*a,**kw):self.runner=actual_runner(*a,**kw);return self.runner
        def event(operator,name,runner):
            self.runner_events.append(name);actual_event(operator,name,runner)
            if name=='reward-planning-open':
                reply=self.a.request(dict(action='reward_cut_prepare',epoch=self.c.epoch))
                self.assertTrue(reply['ok'],repr(reply))
                if self.after_open is not None:self.after_open(operator,runner)
        def open_native(**kw):
            env=base.prior.OwnedRewardOwner(self,**kw);port=base.native.NativePort.__new__(base.native.NativePort)
            port.session,port.guest=env.session,env.guest
            def unknown(exc):
                self.warm.calls.uncertain=True;self.session.phase='TERMINAL';self.session.boundary.hold(repr(exc))
            port.state=base.boot.common.SharedCallState(threading.RLock(),unknown)
            port.transport=SimpleNamespace(state=port.state);port.identity=env.identity
            def execute(command):
                self.assertTrue(self.env.input.s.held);self.assertTrue(self.env.input.s.leaseId)
                return port.state.invoke(lambda:env.execute(command))
            port.execute=execute
            for name in ('attach_journal','stop_restore','verify_restored'):setattr(port,name,getattr(env,name))
            port.checked_port=CheckedPort(env.sampler,port);env.checked_port=port.checked_port
            return port
        with self.env.patches(),patch.object(entry,'Runner',side_effect=factory), \
             patch.object(entry.Operator,'event',event),patch.object(entry,'check',return_value={'result':'OWNED_FILE_PREFLIGHT_DOUBLE'}), \
             patch.object(entry,'join_guest',return_value=self.link), \
             patch.object(base.oldrunner,'preflight',return_value=self.checked), \
             patch.object(base.native,'approved_build',return_value={'owned_approval_double':True}), \
             patch.object(base.prior.old.Runner,'_open',side_effect=lambda c,p,pins:self.open_owned(self.runner,c,p,pins)), \
             patch.object(base.prior.old,'require_original_rules',side_effect=self.original_rules), \
             patch.object(base.prior.old,'require_no_debugger',side_effect=lambda _:self.order.append('no-debugger-double')), \
             patch.object(base.native.NativePort,'open',side_effect=open_native):
            return entry.run(self.simple,no_game_input=True,stream=io.StringIO(commands),emit=self.emitted.append)

    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,events=self.runner_events,owner_events=self.owner_events,
            control_actions=self.control_actions,apply_generations=self.apply_generations,
            emissions=self.emitted,**extra))

    def test_real_files_builds_keys_without_process_save_or_network(self):
        c=self.actual_files()
        with patch.object(entry.startup,'preflight',side_effect=AssertionError('No live preflight')), \
             patch.object(entry.startup,'GameReader',side_effect=AssertionError('No process')), \
             patch.object(entry.startup.files,'read_file',side_effect=AssertionError('No save')), \
             patch.object(entry,'join_guest',side_effect=AssertionError('No network')):
            result=entry.check(c)
        self.assertEqual(result['result'],'PASS_FILES_ONLY');self.assertFalse(result['install_permission'])
        self.assertEqual(len(set(result['key_fingerprints'].values())),3)
        self.assertFalse(result['process_access']);self.assertFalse(result['save_access'])
        c['cut_key_path']=c['report_key_path']
        with self.assertRaisesRegex(ValueError,'keys must differ'):entry.check(c)
        self.evidence(file_approval=result)

    def test_current_console_source_required_no_join_on_missing_pin(self):
        c=self.actual_files();p=Path(c['startup']['local']['source_manifest']['path']);m=json.loads(p.read_text())
        del m['sources'][str((HERE/'simple_remote_console.py').resolve())]
        p.write_text(json.dumps(m));c['startup']['local']['source_manifest']['sha256']=sha(p)
        with patch.object(entry,'join_guest',side_effect=AssertionError('No network')):
            with self.assertRaisesRegex(ValueError,'simple_remote_console'):entry.run(c,no_game_input=True)
        self.assertFalse(self.warm.events);self.evidence(native_calls=0)

    def test_default_help_and_explicit_execute_condition_are_inert(self):
        with patch.object(entry,'read_config',side_effect=AssertionError('No config')), \
             patch.object(entry,'join_guest',side_effect=AssertionError('No network')), \
             contextlib.redirect_stdout(io.StringIO()) as text,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(entry.main([]),0)
            with self.assertRaises(SystemExit):entry.main(['--execute','--config','missing.json'])
        self.assertIn('WndProc remains',text.getvalue());self.assertIn('request_id',text.getvalue())
        with patch.object(entry,'check',side_effect=AssertionError('No check')):
            with self.assertRaisesRegex(ValueError,'no-game-input'):entry.run(self.simple,no_game_input=False)
        self.evidence(native_calls=0)

    def test_actual_tls_two_loads_original_id_dedup_and_held_cleanup(self):
        reward=dict(action='reward',request_id='1'*32,district_id=2,officer_ids=[101])
        ready=dict(action='ready',request_id='2'*32)
        self.begin();result=self.execute_console('\n'.join(json.dumps(x) for x in (reward,reward,ready))+'\n')
        self.assertFalse(self.thread_errors,self.thread_errors);self.assertEqual(self.b_world.calls,1)
        self.assertEqual(self.control_actions.count('reward_submit'),1)
        acks=[x for x in self.emitted if x['event']=='operator-ack' and x['request_id']=='1'*32]
        self.assertEqual([x['duplicate'] for x in acks],[False,True])
        self.assertEqual(acks[0]['result']['authority_ack']['request_id'],'1'*32)
        candidates=next(x for x in self.emitted if x['event']=='external-reward-planning-open')
        self.assertEqual(candidates['force_id'],2);self.assertEqual(candidates['district_id'],2)
        self.assertIn(101,candidates['observed_candidate_ids'])
        self.assertEqual(self.env.phases,[(0,0),(0,1),(2,0)])
        self.assertTrue(self.runner.operator.console.closed);self.assertEqual(len(self.runner.guest.history),2)
        self.assertTrue(result['cleanup']['input_owner_retained']);self.assertFalse(result['cleanup']['input_window_restored'])
        self.assertLess(self.owner_events.index('owner-stop-restore'),self.owner_events.index('second-native-load'))
        self.evidence(cleanup=result['cleanup'],shared_cut=self.mount.gate.receipt['cut'])

    def test_unknown_reward_closes_console_retains_owner_no_second_load(self):
        self.fault='reward-unknown';self.begin()
        commands=[dict(action='reward',request_id='3'*32,district_id=2,officer_ids=[101]),dict(action='ready',request_id='4'*32)]
        with self.assertRaises(Exception):self.execute_console('\n'.join(map(json.dumps,commands))+'\n')
        self.assertEqual(len(self.runner.guest.history),1);self.assertEqual(self.b_world.calls,1)
        self.assertTrue(self.runner.operator.console.closed);self.assertTrue(self.runner.reward.native.state.unknown)
        self.assertNotIn('second-native-load',self.owner_events);self.assertNotIn('owner-stop-restore',self.owner_events)
        self.assertTrue(self.runner.cleanup['retained_native_state']);self.evidence(cleanup=self.runner.cleanup)

    def test_eof_never_becomes_ready(self):
        self.fault='operator-eof';self.config['local']['wait_seconds']=1;self.begin()
        with self.assertRaisesRegex(ValueError,'planning timed out'):self.execute_console('')
        self.assertFalse(self.runner.finish_requested.is_set());self.assertEqual(len(self.runner.guest.history),1)
        self.assertNotIn('reward_cut_prepare',self.control_actions);self.assertNotIn('period_ready',self.control_actions)
        self.assertFalse(self.b_world.calls);self.assertTrue(self.runner.operator.console.closed)
        self.evidence(cleanup=self.runner.cleanup)

    def test_terminal_drains_inflight_console_before_native_terminal(self):
        self.fault='concurrent-terminal';entered=threading.Event();release=threading.Event();returned=threading.Event()
        terminal_entered=threading.Event();terminal_done=threading.Event();errors=[];events=[]
        actual_terminal=entry.native.Runner._terminal
        def observed_terminal(r,exc):
            events.append('native-terminal');self.assertTrue(returned.is_set());terminal_entered.set()
            return actual_terminal(r,exc)
        def request(value,original):
            reply=original(value)
            if value.get('action')=='reward_submit':
                events.append('callback-inflight');entered.set()
                if not release.wait(3):raise TimeoutError('test callback drain timeout')
                events.append('callback-return');returned.set()
            return reply
        self.request_interceptor=request
        def fail_concurrently():
            try:
                self.assertTrue(entered.wait(3))
                def terminate():
                    try:self.runner._terminal(RuntimeError('Owned external terminal'))
                    except BaseException as exc:errors.append(repr(exc))
                    finally:terminal_done.set()
                t=threading.Thread(target=terminate);t.start();time.sleep(.05)
                self.assertFalse(terminal_entered.is_set());self.assertFalse(terminal_done.is_set())
                release.set();t.join(3);self.assertFalse(t.is_alive())
            except BaseException as exc:errors.append(repr(exc));release.set()
        failthread=threading.Thread(target=fail_concurrently);failthread.start();self.begin()
        with patch.object(entry.native.Runner,'_terminal',observed_terminal):
            with self.assertRaises(Exception):self.execute_console(json.dumps(dict(action='reward',request_id='5'*32,district_id=2,officer_ids=[101]))+'\n')
        failthread.join(4);self.assertFalse(failthread.is_alive());self.assertFalse(errors,errors)
        self.assertTrue(terminal_entered.is_set());self.assertTrue(self.runner.operator.console.closed)
        self.assertEqual(len(self.runner.guest.history),1);self.assertNotIn('second-native-load',self.owner_events)
        self.assertLess(events.index('callback-return'),events.index('native-terminal'))
        self.evidence(concurrent_order=events,cleanup=self.runner.cleanup)


if __name__=='__main__':
    OUTPUT=PRIVATE/'b_simple_remote_guest_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    base.prior.predecessor.fixture.transport.OUTPUT=OUTPUT
    base.boot_test.BUILD=base.BUILD;base.boot_test.APPROVED=base.boot.approved(base.BUILD)
    before=pins();stream=io.StringIO()
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_')))
    after=pins();(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    private=[PAIR,HELPER,REWARD/'result.json',base.BUILD.run/'result.json',STAGE,PUBLISHER]
    result=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,sources=after,
        sources_unchanged=before==after,cases=ROWS,private_inputs={str(p):sha(p) for p in private},
        actual_entry_console_Runner_Session_TLS_bootstrap_factory_InputLease_CheckedPort=True,
        actual_file_build_approval=True,native_window_OS_RAM_load_reward_business_doubles=True,
        game_access=False,steam_access=False,full_world_verified=False,two_real_clients_verified=False,
        production_Session_open_executed=False,input_full_coverage=False,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    result['artifacts']={str(p):sha(p) for p in OUTPUT.rglob('*') if p.is_file()}
    p=OUTPUT/'result.json';p.write_text(json.dumps(result,indent=2)+'\n');print(p);raise SystemExit(result['result']!='PASS')
