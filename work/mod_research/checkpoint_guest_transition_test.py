"""Offline controller integration; every native and window object is synthetic."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from checkpoint_guest_transition import *
from checkpoint_visual_client_test import FakeTransport, BINDING, fixture_evidence, GateFixture
from checkpoint_visual_client import VisualClient, VisualError

HERE = Path(__file__).resolve().parent


class FakeNative:
    provenance = 'FIXTURE_ONLY'
    def __init__(self, fixture):
        self.f = fixture
        self.calls = []
        self.complete = False
        self.progress_state = None
        self.start_error = False
        self.release_error = False
        self.partial_world = False
        self.input_open = False
        self.ready_time = 250
        self.mutate_observation = lambda obs: obs
        self.mutate_progress = lambda p: p
        self.on_release = lambda: None

    def hold_input(self, context, target):
        self.calls.append('hold_input')
        self.context = context
        self.hold = InputHold(context, '2'*32, target.attachment, True)
        return self.hold

    def observe(self, hold):
        self.calls.append('observe')
        return self.mutate_observation(WorldObservation(hold.lease, deepcopy(self.f.host),
            deepcopy(self.f.new if self.complete else self.f.old), not self.input_open,
            not self.partial_world, self.f.c.state_contract, self.ready_time if self.complete else 0))

    def start_load(self, context, permit, parts, hold):
        self.calls.append('start_load')
        assert self.f.j.status()['status'] == 'INTENT'
        assert parts == self.f.j.verified_parts()
        self.permit = permit
        if self.start_error:
            raise TimeoutError('Outcome after publication unknown')

    def poll_load(self, hold):
        self.calls.append('poll_load')
        receipt = {'player':'B', 'epoch':self.f.g.identity['manifest']['epoch'],
            'checkpoint_id':self.f.g.identity['checkpoint_id'], 'intent':self.permit['intent'],
            'world_sha256':self.f.host['world_sha256'], 'viewer_force':2,
            'attachment':'c'*32, 'host_observation':self.f.host}
        return self.mutate_progress(LoadProgress(self.context, hold.lease,
            self.progress_state or ('COMPLETE' if self.complete else 'PENDING'),
            receipt if self.complete else None))

    def hold_and_retain_observers(self, hold):
        self.calls.append('hold_and_retain_observers')
        self.input_open = False

    def release_input(self, hold, grant):
        self.calls.append('release_input')
        self.on_release()
        self.input_open = True
        if self.release_error:
            raise TimeoutError('Release acknowledgement lost')
        return InputRelease(self.context, hold.lease, grant['token'], grant['attachment'], True)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='guest-transition-',dir=HERE)
        self.addCleanup(self.tmp.cleanup)
        self.f = GateFixture(self.tmp.name)
        self.transport = FakeTransport()
        self.client = VisualClient(self.transport, session='1'*32, timeout=.2)
        self.addCleanup(self.close)
        self.bridge = GateVisualBridge(self.client, evidence_provider=fixture_evidence,
                                       allow_fixture_evidence=True)
        self.native = FakeNative(self.f)
        self.flow = GuestTransition(self.f.g, self.bridge, self.native, allow_fixture_native=True)

    def close(self):
        if not self.client._closed:
            self.client.terminate_helper(accept_cover_loss=True)

    def start(self):
        return self.flow.start(BINDING)

    def finish(self):
        self.native.complete = True
        return self.flow.poll()

    def held(self):
        self.assertEqual(self.flow.phase, 'HELD')
        self.assertFalse(self.flow.status()['accept_planning_intents'])
        self.assertIn('hold_and_retain_observers', self.native.calls)
        self.assertLessEqual(self.native.calls.count('start_load'), 1)
        self.assertFalse(self.native.input_open)

    def test_full_cycle_uses_durable_journal_and_releases_input_last(self):
        self.assertEqual(self.start()['phase'], 'LOADING')
        self.assertFalse(self.flow.poll()['accept_planning_intents'])
        self.assertEqual(self.f.j.status()['status'], 'INTENT')
        self.native.on_release = lambda: self.assertFalse(self.flow.status()['accept_planning_intents'])
        status = self.finish()
        self.assertTrue(status['accept_planning_intents'])
        self.assertEqual(self.f.j.status()['status'], 'COMPLETED')
        self.assertEqual(self.native.calls[-1], 'release_input')
        self.assertEqual(self.native.calls.count('start_load'),1)
        self.assertFalse(status['native_gameplay_enabled'])

    def test_native_adapter_required_by_default(self):
        with self.assertRaises(VisualError):
            GuestTransition(self.f.g,self.bridge,self.native)

    def test_missing_visual_evidence_cannot_invoke_load(self):
        self.bridge.provider = None
        with self.assertRaises(VisualError): self.start()
        self.held()
        self.assertNotIn('start_load', self.native.calls)
        self.assertEqual(self.f.j.status()['status'], 'STAGED')

    def test_wrong_guest_target_rejected_before_input_or_load(self):
        with self.assertRaises(VisualError): self.flow.start(replace(BINDING,attachment='9'*32))
        self.assertEqual(self.native.calls, [])

    def test_duplicate_start_does_not_reload_or_abort_running_attempt(self):
        self.start()
        with self.assertRaises(VisualError): self.start()
        self.assertEqual(self.flow.phase, 'LOADING')
        self.assertEqual(self.native.calls.count('start_load'),1)

    def test_unknown_start_keeps_observers_and_records_late_completion_without_release(self):
        self.native.start_error = True
        with self.assertRaises(TimeoutError): self.start()
        self.held()
        self.assertEqual(self.f.j.status()['status'],'INTENT')
        self.native.complete = True
        self.assertEqual(self.flow.poll()['late_native_state'],'COMPLETE')
        self.assertNotIn('release_input',self.native.calls)
        self.assertNotIn('reveal',[x['op'] for x in self.transport.sent])
        self.assertEqual(self.f.j.status()['status'],'INTENT')

    def test_restart_from_intent_cannot_issue_another_load(self):
        self.start()
        other = GuestTransition(self.f.g,self.bridge,self.native,allow_fixture_native=True)
        with self.assertRaises(VisualError): other.start(BINDING)
        self.assertEqual(self.native.calls.count('hold_input'),1)
        self.assertEqual(self.native.calls.count('start_load'),1)

    def test_uncertain_progress_holds_without_retry(self):
        self.start(); self.native.progress_state='UNCERTAIN'
        with self.assertRaises(VisualError): self.flow.poll()
        self.held()

    def test_load_failure_never_prepares_or_reveals(self):
        self.start(); self.native.progress_state='FAILED'
        with self.assertRaises(VisualError): self.flow.poll()
        self.held()
        self.assertNotIn('prepare',[x['op'] for x in self.transport.sent])

    def test_foreign_attempt_completion_is_rejected(self):
        self.start()
        self.native.mutate_progress=lambda p:replace(p,context=replace(p.context,attempt='0'*32))
        with self.assertRaises(VisualError): self.finish()
        self.held()

    def test_partial_world_sample_cannot_complete_journal(self):
        self.start(); self.native.partial_world=True
        with self.assertRaises(VisualError): self.finish()
        self.held()
        self.assertEqual(self.f.j.status()['status'],'INTENT')

    def test_input_barrier_loss_keeps_cover(self):
        self.start(); self.native.input_open=True
        with self.assertRaises(VisualError): self.finish()
        self.held()
        self.assertNotIn('reveal',[x['op'] for x in self.transport.sent])

    def test_wrong_restored_faction_never_reveals(self):
        self.start()
        self.native.mutate_observation=lambda o:replace(o,guest={**o.guest,'viewer_force':12})
        with self.assertRaises(Exception): self.finish()
        self.held()
        self.assertNotIn('reveal',[x['op'] for x in self.transport.sent])

    def test_host_changed_while_renderer_waited_is_rechecked(self):
        self.start()
        def intercept(op,r):
            if op=='prepare': self.f.host['world_sha256']='0'*64
            return r
        self.transport.intercept=intercept
        with self.assertRaises(Exception): self.finish()
        self.held()
        self.assertNotIn('reveal',[x['op'] for x in self.transport.sent])

    def test_map_changed_after_capture_does_not_release(self):
        self.start()
        def intercept(op,r):
            if op=='prepare': self.native.ready_time=450
            return r
        self.transport.intercept=intercept
        with self.assertRaises(VisualError): self.finish()
        self.held()

    def test_disconnect_while_loading_retains_observers(self):
        self.start(); self.f.c.connection('B',False)
        with self.assertRaises(VisualError): self.flow.poll()
        self.held()

    def test_disconnect_during_reveal_never_releases_native_input(self):
        self.start()
        def intercept(op,r):
            if op=='reveal': self.f.c.connection('B',False)
            return r
        self.transport.intercept=intercept
        with self.assertRaises(Exception): self.finish()
        self.held()
        self.assertNotIn('release_input',self.native.calls)

    def test_lost_release_ack_reasserts_barrier_without_loading_again(self):
        self.start(); self.native.release_error=True
        with self.assertRaises(TimeoutError): self.finish()
        self.held()
        self.assertEqual(self.f.j.status()['status'],'COMPLETED')

    def test_connected_state_checked_after_release_callback(self):
        self.start(); self.native.on_release=lambda:self.f.c.connection('A',False)
        with self.assertRaises(VisualError): self.finish()
        self.held()

    def test_helper_fault_during_native_release_reasserts_input_barrier(self):
        self.start()
        self.native.on_release=lambda:self.client._trip('Synthetic helper EOF during release')
        with self.assertRaises(VisualError): self.finish()
        self.held()

    def test_world_changes_during_reveal_prevent_native_release(self):
        self.start()
        def intercept(op,r):
            if op=='reveal': self.f.host['world_sha256']='0'*64
            return r
        self.transport.intercept=intercept
        with self.assertRaises(Exception): self.finish()
        self.held()
        self.assertNotIn('release_input',self.native.calls)

    def test_ready_and_orders_use_combined_gate_and_new_attachment(self):
        self.start()
        with self.assertRaises(VisualError): self.flow.set_local_ready(True)
        def on_release():
            self.assertEqual(self.f.g.phase,'LIVE')
            with self.assertRaises(VisualError): self.flow.set_local_ready(True)
        self.native.on_release=on_release
        self.finish()
        with self.assertRaises(VisualError):
            self.flow.require_local_planning(self.f.c.epoch,'b'*32)
        self.flow.require_local_planning(self.f.c.epoch,'c'*32)
        self.flow.set_local_ready(True)

    def test_visual_prepare_timeout_keeps_input_and_observers(self):
        self.start()
        self.transport.intercept=lambda op,r:None if op=='prepare' else r
        with self.assertRaises(VisualError): self.finish()
        self.held()
        self.assertNotIn('release_input',self.native.calls)

    def test_live_status_does_not_retain_admission_after_disconnect(self):
        self.start(); self.finish(); self.f.c.connection('B',False)
        self.assertFalse(self.flow.status()['accept_planning_intents'])
        self.assertTrue(self.flow.status()['fresh_native_gate_required'])


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ControllerTests))
    folder=HERE/'checkpoint_guest_transition_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    files=['checkpoint_guest_transition.py','checkpoint_guest_transition_test.py',
           'checkpoint_visual_client.py','checkpoint_visual_client_bridge.py','checkpoint_visual_client_test.py']
    report={'result':'PASS' if result.wasSuccessful() else 'FAIL','tests_run':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),
            'real_game_access':False,'native_and_window_objects':'synthetic',
            'production_native_port_implemented':False,'two_client_game_roundtrip_proved':False,
            'source_sha256':{f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in files}}
    (folder/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(folder/'result.json'),**report},ensure_ascii=False))
    raise SystemExit(0 if result.wasSuccessful() else 1)
