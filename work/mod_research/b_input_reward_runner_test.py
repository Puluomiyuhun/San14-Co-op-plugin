"""Actual B Runner/TLS/Session/bootstrap factory/InputLease/CheckedPort wiring.
Native window, module calls, load/reward business and RAM are explicit doubles.
"""
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,io,json,sys,threading,unittest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];PRIVATE=ROOT.parent/'mod_research'
sys.path[:0]=[str(PRIVATE/'python_deps'),str(ROOT/'outputs/san14-link')]
import b_reward_runner_test as prior
import b_reward_runner as oldrunner
import b_reward_native_port as native
import b_input_reward_runner as entry
import player_input_lease_bootstrap_port as boot
import player_input_lease_bootstrap_port_test as boot_test
from reward_observed_context import CheckedPort

BUILD=boot.Build(PRIVATE/'player_input_lease_bootstrap_runs/20261010-101506-064151','55359a4455a267b98c59d247a10aefe4c6c479582329bdf6cef28c543d91fb2e')
OUTPUT=None;ROWS=[]

class WindowOS(boot_test.BootstrapOS):
    def __init__(self,case):super().__init__(case);self.phases=[]
    def remote(self,api,address,raw,records,label):
        name=self.exports.get(address)
        result=super().remote(api,address,raw,records,label)
        if name=='PlayerInputBootstrapBegin':
            self.input.s.binding=self.configuration.input.binding
            self.input.s.pid=self.configuration.input.pid;self.input.s.birth=self.configuration.input.birth
        if name=='PlayerInputRequest':
            q=boot.lease.Request.from_buffer_copy(raw);phase=(q.phase,q.localReady);self.phases.append(phase)
            if self.case.input_fault=='ready-not-held' and phase==(0,1):self.input.s.held=0
            if (self.case.input_fault=='ready-unknown' and phase==(0,1)) or (self.case.input_fault=='load-unknown' and phase==(2,0)):
                raise boot.common.RemoteCallUnknown('owned input phase result lost',dict(may_have_started=True))
        return result

class Cases(prior.Cases):
    def setUp(self):
        super().setUp();self.input_fault=None;self.env=WindowOS(self);self.warm.api=self.env.api
        self.control_actions=[];self.apply_generations=[];request=self.link.control.request
        def observed_request(value):self.control_actions.append(value.get('action'));return request(value)
        self.link.control.request=observed_request
        for name in entry.SOURCES:
            p=HERE/name;self.checked['sources'][str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()

    def open_owned(self,runner,context,profile,pins):
        super().open_owned(runner,context,profile,pins);apply=runner.guest.apply
        def observed_apply(received,request,p):self.apply_generations.append(request.generation);return apply(received,request,p)
        runner.guest.apply=observed_apply

    def execute(self):
        self.runner=entry.Runner(self.config,self.link,native_build={'owned_business_double':True},
            input_build=BUILD,window=self.env.window,window_thread=self.env.window_thread,input_timeout_ms=50,
            report_key_path=self.report_path,cut_key_path=self.cut_path,on_event=self.on_event)
        def open_native(**kw):
            env=prior.OwnedRewardOwner(self,**kw);port=native.NativePort.__new__(native.NativePort)
            port.session,port.guest=env.session,env.guest
            def unknown(exc):
                self.warm.calls.uncertain=True;self.session.phase='TERMINAL';self.session.boundary.hold(repr(exc))
            port.state=boot.common.SharedCallState(threading.RLock(),unknown)
            port.transport=SimpleNamespace(state=port.state);port.identity=env.identity
            def execute(command):
                self.assertTrue(self.env.input.s.held);self.assertTrue(self.env.input.s.leaseId)
                return port.state.invoke(lambda:env.execute(command))
            port.execute=execute
            for name in ('attach_journal','stop_restore','verify_restored'):setattr(port,name,getattr(env,name))
            port.checked_port=CheckedPort(env.sampler,port);env.checked_port=port.checked_port
            return port
        with self.env.patches(),patch.object(oldrunner,'preflight',return_value=self.checked), \
             patch.object(native,'approved_build',return_value={'owned_approval_double':True}), \
             patch.object(prior.old.Runner,'_open',side_effect=lambda c,p,pins:self.open_owned(self.runner,c,p,pins)), \
             patch.object(prior.old,'require_original_rules',side_effect=self.original_rules), \
             patch.object(prior.old,'require_no_debugger',side_effect=lambda _:self.order.append('no-debugger-double')), \
             patch.object(native.NativePort,'open',side_effect=open_native):
            return self.runner.run()

    def evidence(self,**extra):
        ROWS.append(dict(case=self._testMethodName,input_phases=self.env.phases,input_calls=self.env.input.calls,
            bootstrap_calls=self.env.calls,owner_events=self.owner_events,
            control_actions=self.control_actions,apply_generations=self.apply_generations,
            formal_completions=len(self.runner.guest.history),cleanup=self.runner.cleanup,
            shared_unknown=self.runner.reward.native.state.unknown,**extra))

    def test_bootstrap_attach_ready_remote_reward_load_ack_and_end_held(self):
        self.begin();result=self.execute();self.assertFalse(self.thread_errors,self.thread_errors)
        self.assertEqual(self.env.phases,[(0,0),(0,1),(2,0)])
        self.assertEqual(self.env.input.calls.count('PlayerInputAcquire'),1)
        self.assertEqual(self.env.input.calls.count('PlayerInputComplete'),1)
        self.assertEqual(self.env.input.s.phase,2);self.assertTrue(self.env.input.s.held)
        self.assertIs(self.runner.input.state,self.runner.reward.native.state)
        self.assertIs(self.runner.reward.native.checked_port.input_lease,self.runner.input)
        self.assertEqual(len(self.runner.guest.history),2)
        self.assertTrue(result['cleanup']['input_owner_retained']);self.assertFalse(result['cleanup']['input_window_restored'])
        self.assertTrue(result['cleanup']['audited_window_messages_held'])
        self.assertIn('WndProc remains retained',result['cleanup']['source_restore_scope'])
        self.assertEqual(self.env.input.s.binding.epoch[:],list(bytes.fromhex(self.runner.reward.replica.port.binding[2])))
        self.evidence()

    def test_known_window_refusal_before_install_cannot_ready_or_load(self):
        self.fault='input-window-rejected';self.env.fault='wrong-window';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(self.apply_generations,[2]);self.assertFalse(self.env.calls)
        self.assertNotIn('reward_cut_prepare',self.control_actions);self.assertNotIn('period_ready',self.control_actions)
        self.assertNotIn('reward-planning-open',self.runner_events);self.assertFalse(self.b_world.calls)
        self.evidence()

    def test_unknown_bootstrap_no_planning_ready_or_second_load(self):
        self.fault='input-bootstrap-unknown';self.env.fault='unknown-begin';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.runner.guest.history),1);self.assertFalse(self.runner.finish_requested.is_set())
        self.assertNotIn('reward-planning-open',self.runner_events);self.assertFalse(self.env.phases)
        self.assertTrue(self.runner.reward.native.state.unknown);self.assertFalse(self.b_world.calls)
        self.assertNotIn('second-native-load',self.owner_events);self.assertFalse(self.runner.reward.cut.prepared)
        self.evidence()

    def test_unknown_ready_ack_does_not_prepare_cut_or_load(self):
        self.fault='input-ready-unknown';self.input_fault='ready-unknown';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.runner.guest.history),1);self.assertFalse(self.runner.finish_requested.is_set())
        self.assertFalse(self.runner.reward.cut.prepared);self.assertNotIn('second-native-load',self.owner_events)
        self.assertIn('reward_submit',self.control_actions)
        self.assertNotIn('reward_cut_prepare',self.control_actions);self.assertNotIn('period_ready',self.control_actions)
        self.assertFalse(self.runner.reward.cut.ready_attempted);self.assertEqual(self.apply_generations,[2])
        self.assertTrue(self.runner.reward.native.state.unknown);self.assertTrue(self.env.input.s.held)
        self.assertNotIn('PlayerInputAcquire',self.env.input.calls)
        self.evidence()

    def test_unknown_load_ack_blocks_second_native_load(self):
        self.fault='input-load-unknown';self.input_fault='load-unknown';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertEqual(len(self.runner.guest.history),1);self.assertEqual(self.b_world.calls,1)
        self.assertTrue(self.runner.reward.restore_attempted);self.assertTrue(self.owner.released)
        self.assertNotIn('second-native-load',self.owner_events);self.assertTrue(self.runner.reward.native.state.unknown)
        self.assertEqual(self.apply_generations,[2])
        self.assertTrue(self.env.input.s.held);self.evidence()

    def test_ready_ack_without_held_policy_cannot_send_cut(self):
        self.fault='input-ready-not-held';self.input_fault='ready-not-held';self.begin()
        with self.assertRaises(Exception):self.execute()
        self.assertIn('reward_submit',self.control_actions)
        self.assertNotIn('reward_cut_prepare',self.control_actions);self.assertNotIn('period_ready',self.control_actions)
        self.assertEqual(self.apply_generations,[2]);self.assertNotIn('PlayerInputAcquire',self.env.input.calls)
        self.assertFalse(self.runner.finish_requested.is_set());self.assertEqual(self.env.input.s.phase,5)
        self.assertTrue(self.env.input.s.held);self.evidence()

if __name__=='__main__':
    OUTPUT=PRIVATE/'b_input_reward_runner_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    prior.predecessor.fixture.transport.OUTPUT=OUTPUT;boot_test.BUILD=BUILD;boot_test.APPROVED=boot.approved(BUILD)
    before=prior.pins();stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_')))
    after=prior.pins();(OUTPUT/'test.log').write_text(stream.getvalue(),encoding='utf-8');print(stream.getvalue())
    result=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,sources=after,
        inputs_unchanged=before==after,cases=ROWS,private={str(BUILD.run/'result.json'):BUILD.sha256},
        actual_Runner_Session_TLS_bootstrap_factory_InputLease_CheckedPort=True,
        native_Window_OS_RAM_load_reward_business_doubles=True,production_game_access=False,steam_access=False,
        first_load_input_owner_installed=False,full_input_coverage=False,
        failures=[(str(t),s) for t,s in r.failures+r.errors])
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    p=OUTPUT/'result.json';p.write_text(json.dumps(result,indent=2)+'\n');print(p);raise SystemExit(result['result']!='PASS')
