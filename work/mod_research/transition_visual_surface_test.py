"""Synthetic pixels and simulated presentation receipts only."""
import json
from pathlib import Path
import unittest
from transition_visual_surface import Frame, TransitionSurface, SurfaceError, PresentationReceipt


OLD = Frame(2, 2, bytes([20, 110, 60])*4, "old-fixture-world")
NEW = Frame(2, 2, bytes([90, 120, 50])*4, "new-fixture-world")


def paint(surface, ticket=None, outcome="PRESENTED", digest=None):
    ticket = ticket or surface.ticket
    return surface.acknowledge(PresentationReceipt(ticket, outcome, digest or ticket.frame.digest))


class SurfaceTests(unittest.TestCase):
    def waiting(self):
        s = TransitionSurface()
        s.begin("attempt-1", OLD, native_input_gate_ack=True)
        paint(s)
        s.native_started("attempt-1")
        return s

    def test_input_gate_and_painted_cover_precede_teardown(self):
        s = TransitionSurface()
        with self.assertRaises(SurfaceError):
            s.begin("attempt-1", OLD, native_input_gate_ack=False)
        s.begin("attempt-1", OLD, native_input_gate_ack=True)
        self.assertEqual(s.route_input("gameplay"), "CONSUME")
        with self.assertRaises(SurfaceError): s.native_started("attempt-1")
        self.assertTrue(paint(s)); s.native_started("attempt-1")

    def test_success_requires_verified_new_frame_paint_before_input_release(self):
        s = self.waiting()
        s.prepare_release("attempt-1", NEW, controller_grant="verified-1")
        self.assertTrue(s.input_held)
        with self.assertRaises(SurfaceError):
            s.commit_release("attempt-1", controller_grant="verified-1")
        paint(s)
        with self.assertRaises(SurfaceError):
            s.commit_release("attempt-1", controller_grant="wrong")
        s.commit_release("attempt-1", controller_grant="verified-1")
        self.assertFalse(s.input_held)
        self.assertEqual(s.route_input("gameplay"), "FORWARD")

    def test_all_native_lifecycle_labels_leave_old_picture_and_input_held(self):
        s = self.waiting()
        for state in ("Game teardown", "Title init", "Load init", "Load exit",
                      "Strategy init", "User phase 2", "empty state stack"):
            self.assertEqual(s.native_state_seen("attempt-1", state).frame, OLD)
            self.assertTrue(s.input_held)

    def test_progress_does_not_replace_old_picture_with_title_or_load_frame(self):
        s = self.waiting()
        t = s.progress("attempt-1", "重建地图")
        self.assertEqual(t.frame.rgb, OLD.rgb)
        self.assertEqual(s.route_input("recovery"), "CONSUME")

    def test_test_present_and_occlusion_are_not_visible_frame_ack(self):
        s = TransitionSurface(); s.begin("attempt-1", OLD, native_input_gate_ack=True)
        for outcome in ("TEST", "OCCLUDED", "DEVICE_REMOVED", "FAILED"):
            with self.assertRaises(SurfaceError): paint(s, outcome=outcome)
            self.assertFalse(s.may_start_native)

    def test_wrong_frame_receipt_cannot_release(self):
        s = self.waiting(); s.prepare_release("attempt-1", NEW, controller_grant="g")
        with self.assertRaises(SurfaceError): paint(s, digest=OLD.digest)
        with self.assertRaises(SurfaceError): s.commit_release("attempt-1", controller_grant="g")

    def test_later_occlusion_invalidates_earlier_visible_ack(self):
        s = TransitionSurface(); s.begin("attempt-1", OLD, native_input_gate_ack=True)
        paint(s); self.assertTrue(s.may_start_native)
        with self.assertRaises(SurfaceError): paint(s, outcome="OCCLUDED")
        self.assertFalse(s.may_start_native)

    def test_stale_presentation_after_progress_rejected(self):
        s = self.waiting(); old_ticket = s.ticket
        s.progress("attempt-1", "核对地图")
        with self.assertRaises(SurfaceError): paint(s, old_ticket)

    def test_wrong_attempt_cannot_advance_or_release(self):
        s = self.waiting()
        with self.assertRaises(SurfaceError): s.native_state_seen("old", "User phase 2")
        with self.assertRaises(SurfaceError): s.prepare_release("old", NEW, controller_grant="g")

    def test_failure_during_reveal_cancels_grant_and_keeps_recovery(self):
        s = self.waiting(); stale = s.prepare_release("attempt-1", NEW, controller_grant="g")
        failure = s.fail("attempt-1", "身份校验失败")
        self.assertEqual(failure.frame, OLD)
        self.assertIn("身份校验失败", failure.overlay)
        self.assertTrue(failure.recovery_actions)
        with self.assertRaises(SurfaceError): paint(s, stale)
        paint(s)
        with self.assertRaises(SurfaceError): s.commit_release("attempt-1", controller_grant="g")
        self.assertEqual(s.route_input("gameplay"), "CONSUME")
        self.assertEqual(s.route_input("recovery"), "HANDLE_RECOVERY_ONLY")

    def test_surface_loss_does_not_claim_picture_visible_or_unblock_game(self):
        s = self.waiting(); lost = s.surface_lost("attempt-1")
        self.assertFalse(s.available); self.assertTrue(s.input_held)
        with self.assertRaises(SurfaceError): paint(s, lost)
        s.repaint_after_loss("attempt-1"); paint(s)
        self.assertEqual(s.phase, "FAILED"); self.assertFalse(s.may_start_native)
        with self.assertRaises(SurfaceError): s.prepare_release("attempt-1", NEW, controller_grant="g")

    def test_release_never_reuses_same_surface_for_another_period(self):
        s = self.waiting(); s.prepare_release("attempt-1", NEW, controller_grant="g")
        paint(s); s.commit_release("attempt-1", controller_grant="g")
        with self.assertRaises(SurfaceError): s.begin("attempt-2", NEW, native_input_gate_ack=True)

    def test_frames_validate_bounds_and_immutable_pixel_buffer(self):
        for args in ((0, 2, b"", "r"), (8193, 1, b"", "r"),
                     (2, 2, bytearray(12), "r"), (2, 2, b"123", "r")):
            with self.assertRaises(SurfaceError): Frame(*args)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SurfaceTests))
    report = {"tests_run": result.testsRun, "failures": len(result.failures),
              "errors": len(result.errors), "passed": result.wasSuccessful(),
              "synthetic_only": True, "native_renderer_connected": False,
              "game_process_access": False, "game_screen_capture": False,
              "game_file_writes": False,
              "limits": "Only presentation contract and synthetic receipts; no actual native input interception or rendering guarantee."}
    Path(__file__).with_name("transition_visual_surface_test_results.json").write_text(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
