"""Real coordinator/journal/presentation/surface/input modules, fixture backend."""
from pathlib import Path
import json
import unittest

from test_checkpoint_presentation import PresentationTests
from authoritative_sync import SyncError
from checkpoint_local_transition import CheckpointLocalTransition, frame_id
from transition_visual_surface import Frame, PresentationReceipt
from transition_input_gate_contract import CHANNELS, Boundary, ChannelEvidence, Cycle, PhysicalState, GateError

HERE = Path(__file__).resolve().parent
OLD_FRAME = Frame(2, 2, bytes([32, 96, 64]) * 4, "old-local-fixture")
NEW_FRAME = Frame(2, 2, bytes([96, 128, 48]) * 4, "new-local-fixture")
THREAD = 77


class LocalTransitionTests(unittest.TestCase):
    def setUp(self):
        self.f = PresentationTests("test_full_visual_barrier_keeps_room_held_until_new_map")
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.t = CheckpointLocalTransition(self.f.c, self.f.j, THREAD)

    def boundary(self, n, binding=None):
        return Boundary(binding or self.t.binding, THREAD, n)

    def cycle(self, n, physical=None, *, binding=None, pending=0):
        return Cycle(binding or self.t.binding, THREAD, n,
                     tuple(ChannelEvidence(c, n, n) for c in CHANNELS),
                     physical or PhysicalState(), pending_gameplay_messages=pending)

    def paint(self, ticket=None):
        ticket = ticket or self.t.surface.ticket
        return PresentationReceipt(ticket, "PRESENTED", ticket.frame.digest)

    def load(self, physical=None):
        t, f = self.t, self.f
        t.begin_cover(OLD_FRAME, view="e" * 32, surface="f" * 32, window_mode="windowed",
                      boundary=self.boundary(1), cycle=self.cycle(1, physical))
        old_paint = self.paint()
        t.acknowledge_cover(old_paint)
        permit = t.reserve_load(f.host, f.old_guest, self.boundary(1))
        self.assertEqual(f.j.status()["status"], "INTENT")
        new = t.expected_loaded_binding(f.guest["attachment"])
        receipt = {"player": "B", "epoch": f.p.manifest["epoch"],
            "checkpoint_id": f.p.checkpoint_id, "intent": permit["intent"],
            "world_sha256": f.host["world_sha256"], "viewer_force": 2,
            "attachment": f.guest["attachment"], "host_observation": f.host}
        t.complete_load(receipt, f.host, f.guest, self.boundary(2, new),
                        self.cycle(2, physical, binding=new))
        self.assertEqual(f.j.status()["status"], "COMPLETED")
        return old_paint

    def prepare(self, physical=None):
        old = self.load(physical)
        t = self.t
        t.map_frame_presented(NEW_FRAME, {**self.f.frame,
            "presentation": t.presentation.nonce, "frame": frame_id(NEW_FRAME)})
        t.begin_reveal(self.f.host, self.f.guest)
        return old

    def reveal(self, physical=None):
        old = self.prepare(physical)
        self.t.acknowledge_reveal(self.paint(), self.boundary(2))
        return old

    def assert_blocked(self):
        s = self.t.status()
        self.assertFalse(s["accept_planning_intents"])
        self.assertFalse(s["native_gameplay_enabled"])
        self.assertFalse(s["native_input_interception_implemented"])
        self.assertFalse(s["native_visual_cover_implemented"])
        ready_before = set(self.f.c.ready)
        with self.assertRaises(SyncError):
            self.t.set_local_ready(True)
        self.assertEqual(self.f.c.ready, ready_before)

    def test_real_modules_durable_load_and_visual_physical_barriers(self):
        self.prepare()
        self.assertEqual(self.f.c.phase, "PLANNING")
        self.assertEqual(self.t.presentation.phase, "REVEALING")
        self.assertEqual(self.t.inputs.state, "HELD")
        self.assert_blocked()  # coordinator PLANNING does not grant admission
        self.t.acknowledge_reveal(self.paint(), self.boundary(2))
        self.assertEqual(self.t.presentation.phase, "LIVE")
        self.assertEqual(self.t.inputs.state, "RELEASE_PENDING")
        self.assert_blocked()  # actual reveal still needs a NEW neutral cycle
        receipt = self.t.observe_cycle(self.cycle(3))
        self.assertIsNotNone(receipt)
        self.assert_blocked()  # receipt creation itself does not open input
        self.t.acknowledge_input_release(receipt, self.boundary(3), self.f.host, self.f.guest)
        s = self.t.status()
        self.assertTrue(s["accept_planning_intents"])
        self.assertEqual(s["attachment"], "c" * 32)
        self.assertEqual(s["evidence_source"], "SYNTHETIC_FIXTURE")
        self.t.set_local_ready(True)
        self.assertEqual(self.f.c.ready, {"B"})
        with self.assertRaises(SyncError):
            self.t.require_local_planning(self.f.p.manifest["epoch"], "b" * 32)

    def test_held_old_key_unknown_device_and_posted_messages_all_wait(self):
        held = PhysicalState(keyboard_down=(30,), modifier_bits=0x22)
        self.reveal(held)
        for n, physical, pending in [
            (3, held, 0), (4, held, 0), (5, PhysicalState(unknown=True), 0),
            (6, PhysicalState(), 2), (7, PhysicalState(controller_axes=(1,)), 0),
        ]:
            self.assertIsNone(self.t.observe_cycle(self.cycle(n, physical, pending=pending)))
            self.assert_blocked()
        receipt = self.t.observe_cycle(self.cycle(8))
        self.t.acknowledge_input_release(receipt, self.boundary(8), self.f.host, self.f.guest)
        self.assertTrue(self.t.status()["accept_planning_intents"])

    def test_old_visual_receipt_after_planning_latches_closed(self):
        old = self.prepare()
        self.assertEqual(self.f.c.phase, "PLANNING")
        with self.assertRaises(ValueError):
            self.t.acknowledge_reveal(old, self.boundary(2))
        self.assertEqual(self.t.phase, "HELD")
        self.assertEqual(self.t.inputs.state, "HELD")
        self.assert_blocked()

    def test_input_receipt_superseded_by_new_held_key_cannot_release(self):
        self.reveal()
        old = self.t.observe_cycle(self.cycle(3))
        self.assertIsNone(self.t.observe_cycle(self.cycle(4, PhysicalState(keyboard_down=(30,)))))
        with self.assertRaises(GateError):
            self.t.acknowledge_input_release(old, self.boundary(4), self.f.host, self.f.guest)
        self.assertEqual(self.t.phase, "HELD")
        self.assertTrue(self.t.status()["new_recovery_cover_required"])
        self.assertIsNone(self.t.observe_cycle(self.cycle(5)))  # drain continues, no auto-release
        self.assert_blocked()

    def test_disconnect_revokes_receipt_and_reconnect_never_autoreleases(self):
        self.reveal()
        receipt = self.t.observe_cycle(self.cycle(3))
        self.f.c.connection("B", False)
        self.assert_blocked()
        self.assertEqual(self.t.inputs.state, "HELD")
        self.f.c.connection("B", True)
        self.assertIsNone(self.t.observe_cycle(self.cycle(4)))
        with self.assertRaises(SyncError):
            self.t.acknowledge_input_release(receipt, self.boundary(4), self.f.host, self.f.guest)
        self.assert_blocked()

    def test_wrong_attachment_cycle_after_verified_handoff_fails_closed(self):
        old_binding = self.t.binding
        self.load()
        self.assertEqual(self.t.binding.generation, old_binding.generation + 1)
        self.assertEqual(self.t.inputs.state, "HELD")
        with self.assertRaises(GateError):
            self.t.observe_cycle(self.cycle(3, binding=old_binding))
        self.assert_blocked()
        self.assertEqual(self.f.c.phase, "RECONCILING")

    def test_bad_loaded_world_never_handoffs_attachment(self):
        t, f = self.t, self.f
        t.begin_cover(OLD_FRAME, view="e" * 32, surface="f" * 32, window_mode="borderless",
                      boundary=self.boundary(1), cycle=self.cycle(1))
        t.acknowledge_cover(self.paint())
        permit = t.reserve_load(f.host, f.old_guest, self.boundary(1))
        new = t.expected_loaded_binding(f.guest["attachment"])
        bad = {"player": "B", "epoch": f.p.manifest["epoch"], "checkpoint_id": f.p.checkpoint_id,
               "intent": permit["intent"], "world_sha256": "0" * 64, "viewer_force": 2,
               "attachment": f.guest["attachment"], "host_observation": f.host}
        with self.assertRaises(SyncError):
            t.complete_load(bad, f.host, f.guest, self.boundary(2, new), self.cycle(2, binding=new))
        self.assertEqual(t.binding.attachment, "b" * 32)
        self.assertEqual(f.j.status()["status"], "INTENT")
        self.assert_blocked()

    def test_fresh_world_must_still_match_at_final_input_ack(self):
        self.reveal()
        receipt = self.t.observe_cycle(self.cycle(3))
        with self.assertRaises(SyncError):
            self.t.acknowledge_input_release(receipt, self.boundary(3),
                self.f.host, {**self.f.guest, "viewer_force": 12})
        self.assert_blocked()

    def test_disconnect_after_open_closes_admission_without_claiming_native_rearm(self):
        self.reveal()
        receipt = self.t.observe_cycle(self.cycle(3))
        self.t.acknowledge_input_release(receipt, self.boundary(3), self.f.host, self.f.guest)
        self.assertTrue(self.t.status()["accept_planning_intents"])
        self.f.c.connection("A", False)
        s = self.t.status()
        self.assertFalse(s["accept_planning_intents"])
        self.assertEqual(s["input_phase"], "OPEN")
        self.assertTrue(s["fresh_native_gate_required"])
        self.assertTrue(s["new_recovery_cover_required"])
        self.assertFalse(s["native_input_interception_implemented"])
        self.f.c.connection("A", True)
        self.assert_blocked()


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LocalTransitionTests))
    report = {"schema": "san14.checkpoint-local-transition-integration.v1",
        "result": "PASS" if result.wasSuccessful() else "FAIL", "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "modules": ["PeriodCoordinator", "CheckpointJournal", "MapWaitGate", "TransitionSurface", "NeutralInputGate"],
        "controller": "checkpoint_local_transition.CheckpointLocalTransition",
        "synthetic_only": True, "backend_receipts": "SYNTHETIC_FIXTURE",
        "native_gameplay_enabled": False, "real_game_access": False,
        "native_visual_cover_implemented": False, "native_input_interception_implemented": False}
    (HERE / "checkpoint_local_transition_test.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
