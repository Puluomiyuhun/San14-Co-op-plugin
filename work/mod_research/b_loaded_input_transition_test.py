"""Real two-checkpoint TLS/GuestCompletion chain; explicit native/window doubles."""
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import hashlib,io,json,unittest
import b_input_reward_runner_test as prior
import b_loaded_input_transition as transition
import player_input_rebind_port as inputs

OUTPUT=None

class RebindBody:
    def __init__(self,old,mode):
        self.s=inputs.Snapshot.from_buffer_copy(bytes(old));self.mode=mode;self.calls=[]
    def call(self,name,raw):
        self.calls.append(name)
        if name=='PlayerInputSnapshot':
            q=inputs.Snapshot.from_buffer_copy(raw);r=inputs.Snapshot.from_buffer_copy(bytes(self.s));r.header=q.header;r.nonce[:]=q.nonce
            return 0,bytes(r)
        assert name=='PlayerInputRebind'
        q=inputs.Rebind.from_buffer_copy(raw);self.s.binding=q.nextBinding
        self.s.revision=self.s.acknowledgedRevision=q.revision
        if self.mode=='unknown':raise inputs.common.RemoteCallUnknown('owned lost Rebind reply',dict(may_have_started=True))
        return 0,bytes(q)

class Cases(prior.Cases):
    def exercise(self,mode=None):
        old_finish=prior.entry.Runner.finish_native;self.fault='transition-test' if mode else None
        def finish(runner):
            # Reuse the actual acknowledged two-load test's bytes and shared
            # call gate. This is a successor-window double, not a live upgrade.
            self.body=RebindBody(self.env.input.s,mode)
            transport=inputs.Transport.__new__(inputs.Transport);transport.state=runner.input.state;transport._perform=self.body.call
            self.next_input=inputs.InputLease(transport,nonce=runner.input.nonce,
                binding=inputs.Binding.from_buffer_copy(bytes(runner.input.binding)),pid=runner.local['pid'],birth=runner.local['birth'],
                window=runner.window,records=runner.records/'successor-input-double',wait_seconds=.1)
            if mode=='stale-room':self.c.epoch='f'*32
            if mode=='no-formal-completion':runner.guest.history.pop()
            if mode=='changed-native-receipt':runner.guest.history[-1]['native_receipt']='f'*64
            if mode=='retired-rules':runner.session.lifecycle.current.retired=True
            self.transition=transition.rebind_after_second_load(runner.session,runner.guest,self.next_input,records=runner.records/'post-load-input')
            self.retained_phases=(runner.session.phase,runner.guest.phase)
            with self.assertRaisesRegex(ValueError,'already attempted'):
                transition.rebind_after_second_load(runner.session,runner.guest,self.next_input,records=runner.records/'repeated')
            return old_finish(runner)
        self.begin()
        with patch.object(prior.entry.Runner,'finish_native',finish):return self.execute()
    def test_two_formal_loads_then_authenticated_new_binding_still_held(self):
        result=self.exercise();self.assertFalse(self.thread_errors,self.thread_errors)
        self.assertEqual(self.retained_phases,('TWO_LOADS_RETAINED','TWO_COMPLETIONS_RETAINED'))
        self.assertEqual(self.next_input.binding.period,3)
        self.assertEqual(bytes(self.next_input.binding.attachment).hex(),self.runner.guest.attachments['B'])
        self.assertEqual(bytes(self.next_input.binding.epoch).hex(),self.runner.guest.epoch)
        self.assertEqual(self.body.calls.count('PlayerInputRebind'),1)
        self.assertNotIn('PlayerInputRequest',self.body.calls);self.assertTrue(self.body.s.held)
        self.assertEqual(self.body.s.phase,2);self.assertFalse(self.transition['third_checkpoint_enabled'])
        self.assertFalse(self.transition['input_planning_open']);self.assertEqual(len(self.runner.guest.history),2)
        self.assertTrue(result['cleanup']['native_cleanup_verified'])
    def test_room_epoch_drift_does_not_rebind(self):
        with self.assertRaisesRegex(ValueError,'settled'):self.exercise('stale-room')
        self.assertNotIn('PlayerInputRebind',self.body.calls);self.assertTrue(self.body.s.held)
    def test_missing_formal_completion_does_not_rebind(self):
        with self.assertRaisesRegex(ValueError,'formal completions'):self.exercise('no-formal-completion')
        self.assertNotIn('PlayerInputRebind',self.body.calls)
    def test_retired_world_rules_do_not_rebind(self):
        with self.assertRaisesRegex(ValueError,'human rules'):self.exercise('retired-rules')
        self.assertNotIn('PlayerInputRebind',self.body.calls)
    def test_formal_completion_must_match_local_native_receipt(self):
        with self.assertRaisesRegex(ValueError,'another native receipt'):self.exercise('changed-native-receipt')
        self.assertNotIn('PlayerInputRebind',self.body.calls)
    def test_unknown_rebind_never_retries_or_opens_input(self):
        with self.assertRaises(inputs.common.RemoteCallUnknown):self.exercise('unknown')
        self.assertEqual(self.body.calls.count('PlayerInputRebind'),1);self.assertTrue(self.body.s.held)
        self.assertTrue(self.next_input.state.unknown);self.assertIsNotNone(self.next_input.failed)
        self.assertNotIn('PlayerInputRequest',self.body.calls)

if __name__=='__main__':
    OUTPUT=prior.PRIVATE/'b_loaded_input_transition_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');OUTPUT.mkdir(parents=True)
    prior.prior.predecessor.fixture.transport.OUTPUT=OUTPUT;prior.boot_test.BUILD=prior.BUILD;prior.boot_test.APPROVED=prior.boot.approved(prior.BUILD)
    before=prior.prior.pins();stream=io.StringIO()
    r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.TestSuite(Cases(n) for n in Cases.__dict__ if n.startswith('test_')))
    after=prior.prior.pins();(OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8')
    result=dict(result='PASS' if r.wasSuccessful() and before==after else 'FAIL',tests=r.testsRun,sources=after,inputs_unchanged=before==after,
        actual_two_checkpoint_TLS_Session_GuestCompletion=True,native_RAM_window_load_reward_doubles=True,
        production_bootstrap_successor_selected=False,game_access=False,**transition.FLAGS)
    result['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    path=OUTPUT/'result.json';path.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(stream.getvalue());print(path);raise SystemExit(result['result']!='PASS')
