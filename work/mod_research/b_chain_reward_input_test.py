"""Two reward/input windows with actual ports/journals and explicit RPC doubles."""
from datetime import datetime
from pathlib import Path
import hashlib, io, json, unittest
import b_chain_reward_test as fixture
import player_input_rebind_port_test as window
import player_input_rebind_port as inputs
from b_chain_reward_input import Window

OUTPUT=None

class Cases(unittest.TestCase):
    def fixture(self):
        h=fixture.Harness(self);lease,body=h.install_input();r=h.open()
        # The load/rebind evidence is an explicit environment substitute;
        # b_chain_input_transition_test covers real service TLS independently.
        return h,r,body,lease

    def open(self,h,r,lease):
        return Window.open(r,lease,records=h.folder/f'input-window-{h.n}')

    def retire(self,h,r,w):
        if w.phase=='PLANNING':w.finish_input()
        r.cut.attest_attempted=True;h.cut_state='RETIRED_SHARED_CUT';r.poll()
        w.prepare_load()

    def next(self,h,lease):
        h.move();b=inputs.Binding.from_buffer_copy(bytes(lease.binding))
        b.period=h.g.period;b.epoch[:]=bytes.fromhex(h.g.epoch);b.attachment[:]=bytes.fromhex(h.g.attachments['B'])
        lease.rebind_after_load(b);h.s._chain_input_transitions[2]=dict(phase='REBOUND_HELD')
        r=h.open();r.native.transport.state=r.native.state
        return r

    def test_two_windows_reward_ready_load_rebind_then_reward_again(self):
        h,r,body,lease=self.fixture();w=self.open(h,r,lease)
        request=h.s.control.request;ready_states=[]
        def check_ready(q):
            if q['action']=='period_ready':
                ready_states.append(body.s.phase)
                self.assertEqual(body.s.phase,2);self.assertTrue(body.s.acknowledged)
                self.assertFalse(body.s.remoteExecutionPolicyOpen)
            return request(q)
        h.s.control.request=check_ready
        self.assertNotEqual(r.replica.port.binding[2],lease.local_binding[2])
        self.assertIs(r.replica.port.retained_input_lease,lease)
        w.finish_input();self.assertTrue(body.s.held);self.assertTrue(body.s.remoteExecutionPolicyOpen)
        h.reward(r);self.retire(h,r,w)
        self.assertEqual(body.s.phase,2);self.assertFalse(body.s.remoteExecutionPolicyOpen)
        r2=self.next(h,lease);w2=self.open(h,r2,lease);h.reward(r2);self.retire(h,r2,w2)
        self.assertEqual(h.w.calls,2);self.assertEqual(body.calls.count('PlayerInputAcquire'),2)
        self.assertEqual(body.s.leasesIssued,body.s.leasesCompleted)
        self.assertEqual(body.s.phase,2);self.assertTrue(body.s.held)
        self.assertIs(r.native.state,r2.native.state);self.assertEqual(body.s.publicationWrites,1)
        self.assertEqual(ready_states,[2,2])

    def test_load_hold_failure_never_sends_ready(self):
        h,r,body,lease=self.fixture();w=self.open(h,r,lease);w.finish_input()
        request=h.s.control.request;ready=[]
        def record(q):
            if q['action']=='period_ready':ready.append(q)
            return request(q)
        h.s.control.request=record
        call=lease.transport._perform
        def fail_load(name,raw):
            if name=='PlayerInputRequest' and inputs.Request.from_buffer_copy(raw).phase==2:
                raise inputs.common.RemoteCallUnknown('owned LOAD acknowledgement lost',dict(may_have_started=True))
            return call(name,raw)
        lease.transport._perform=fail_load
        r.cut.attest_attempted=True;h.cut_state='RETIRED_SHARED_CUT'
        with self.assertRaises(inputs.common.RemoteCallUnknown):r.poll()
        self.assertEqual(ready,[]);self.assertEqual(h.s.phase,'TERMINAL')
        self.assertTrue(lease.state.unknown)

    def test_missing_rebind_cannot_open(self):
        h,r,body,lease=self.fixture();h.s._chain_input_transitions[1]['phase']='CHECKING'
        with self.assertRaisesRegex(Exception,'acknowledged'):self.open(h,r,lease)
        self.assertNotIn('PlayerInputRequest',body.calls)

    def test_old_checkpoint_binding_refuses_before_open(self):
        h,r,body,lease=self.fixture();lease.binding.period-=1
        with self.assertRaises(Exception):self.open(h,r,lease)
        self.assertNotEqual(body.s.phase,0)

    def test_load_requires_native_reward_retirement(self):
        h,r,body,lease=self.fixture();w=self.open(h,r,lease);w.finish_input()
        with self.assertRaisesRegex(Exception,'not retired'):w.prepare_load()
        self.assertEqual(w.phase,'HELD');self.assertFalse(body.s.remoteExecutionPolicyOpen)
        self.assertEqual(body.s.phase,5)

    def test_second_unknown_reward_does_not_release_input_or_retry(self):
        h,r,body,lease=self.fixture();w=self.open(h,r,lease);h.reward(r);self.retire(h,r,w)
        r2=self.next(h,lease);w2=self.open(h,r2,lease);h.schedulers[1].fault='unknown'
        with self.assertRaises(Exception):h.reward(r2)
        calls=list(body.calls)
        with self.assertRaises(Exception):w2.finish_input()
        self.assertEqual(calls,body.calls);self.assertTrue(lease.state.unknown)
        self.assertTrue(body.s.held);self.assertEqual(h.schedulers[1].calls.count('BRewardSubmit'),1)

    def test_window_cannot_be_reopened(self):
        h,r,body,lease=self.fixture();self.open(h,r,lease);calls=list(body.calls)
        with self.assertRaisesRegex(Exception,'already attempted'):self.open(h,r,lease)
        self.assertEqual(calls,body.calls)

if __name__=='__main__':
    OUTPUT=fixture.PRIVATE/'b_chain_reward_input_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    OUTPUT.mkdir(parents=True);fixture.OUTPUT=OUTPUT
    paths={Path(m.__file__).resolve() for m in list(__import__('sys').modules.values()) if getattr(m,'__file__',None)}
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_relative_to(fixture.ROOT) and p.suffix=='.py'}
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Cases))
    (OUTPUT/'tests.log').write_text(stream.getvalue(),encoding='utf-8')
    stable=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in before.items())
    data=dict(result='PASS' if r.wasSuccessful() and stable else 'FAIL',tests=r.testsRun,sources=before,
        inputs_unchanged=stable,game_access=False,actual_TLS=False,actual_journal_and_checked_projection=True,
        native_window_load_authority_doubles=True,full_input_exclusion_proven=False,native_menu_capture_enabled=False)
    data['artifacts']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUTPUT.rglob('*') if p.is_file()}
    path=OUTPUT/'result.json';path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(stream.getvalue());print(path);raise SystemExit(data['result']!='PASS')
