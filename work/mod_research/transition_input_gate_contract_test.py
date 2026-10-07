"""Meaningful offline protocol tests; none installs or exercises a live gate."""
from dataclasses import replace
from pathlib import Path
import json
import unittest

from transition_input_gate_contract import (
    CHANNELS, Binding, Boundary, ChannelEvidence, Cycle, GateError,
    NeutralInputGate, PhysicalState,
)

P = Path(__file__).resolve().parent
BINDING = Binding("a" * 32, "b" * 32)
GRANT = "c" * 32
THREAD = 77


def cycle(n, binding=BINDING, physical=None, **kw):
    return Cycle(binding, THREAD, n,
                 tuple(ChannelEvidence(c, n, n) for c in CHANNELS),
                 physical or PhysicalState(), **kw)


def boundary(n, binding=BINDING, **kw):
    return Boundary(binding, THREAD, n, **kw)


def armed(physical=None):
    gate = NeutralInputGate(BINDING, THREAD)
    gate.arm(boundary(1), cycle(1, physical=physical))
    return gate


def release_pending():
    gate = armed()
    gate.request_release(boundary(1), GRANT)
    return gate


class ContractTests(unittest.TestCase):
    def assert_closed(self, gate):
        self.assertFalse(gate.status()["contract_allows_input"])
        self.assertFalse(gate.status()["native_gate_complete"])
        self.assertFalse(gate.status()["game_input_actually_blocked"])

    def test_end_to_end_requires_later_neutral_cycle_and_ack(self):
        gate = armed(PhysicalState(keyboard_down=(30,)))
        self.assertTrue(gate.status()["neutral_publication_confirmed"])
        gate.observe_cycle(cycle(2, physical=PhysicalState(keyboard_down=(30,))))
        gate.request_release(boundary(2), GRANT)
        self.assertFalse(gate.status()["release_receipt_ready"])
        self.assertIsNone(gate.observe_cycle(cycle(3, physical=PhysicalState(keyboard_down=(30,)))))
        receipt = gate.observe_cycle(cycle(4))
        self.assert_closed(gate)
        gate.acknowledge_release(boundary(4), receipt, GRANT)
        self.assertTrue(gate.status()["contract_allows_input"])

    def test_arm_rejects_unstable_nonplanning_or_pending_work(self):
        variants = [dict(state="CLoadState"), dict(phase=1), dict(stable_planning=False),
                    dict(pending_menu=4), dict(pending_advance=True), dict(pending_dispatch=True)]
        for kw in variants:
            with self.subTest(**kw):
                gate = NeutralInputGate(BINDING, THREAD)
                with self.assertRaises(GateError):
                    gate.arm(boundary(1, **kw), cycle(1))
                self.assert_closed(gate)
                self.assertFalse(gate.status()["neutral_publication_confirmed"])

    def test_arm_requires_game_thread_on_boundary_and_observation(self):
        for b, c in [(replace(boundary(1), thread_id=78), cycle(1)),
                     (boundary(1), replace(cycle(1), thread_id=78))]:
            gate = NeutralInputGate(BINDING, THREAD)
            with self.assertRaises(GateError):
                gate.arm(b, c)
            self.assertFalse(gate.status()["neutral_publication_confirmed"])

    def test_arm_rejects_existing_posted_gameplay_message(self):
        gate = NeutralInputGate(BINDING, THREAD)
        with self.assertRaises(GateError):
            gate.arm(boundary(1), cycle(1, pending_gameplay_messages=1))
        self.assertFalse(gate.status()["neutral_publication_confirmed"])

    def test_every_channel_is_required_and_must_publish_neutral(self):
        for missing in CHANNELS:
            for kind in ("omit", "uncovered", "nonneutral", "stale_drain", "stale_publish"):
                with self.subTest(channel=missing, kind=kind):
                    c = cycle(1)
                    channels = []
                    for item in c.channels:
                        if item.name == missing:
                            if kind == "omit":
                                continue
                            item = replace(item, **{
                                "uncovered": {"covered": False}, "nonneutral": {"neutral": False},
                                "stale_drain": {"drain_cycle": 0}, "stale_publish": {"publish_cycle": 0},
                            }[kind])
                        channels.append(item)
                    gate = NeutralInputGate(BINDING, THREAD)
                    with self.assertRaises(GateError):
                        gate.arm(boundary(1), replace(c, channels=tuple(channels)))
                    self.assertFalse(gate.status()["neutral_publication_confirmed"])

    def test_duplicate_channel_does_not_replace_missing_coverage(self):
        c = cycle(1)
        c = replace(c, channels=c.channels[:-1] + (c.channels[0],))
        gate = NeutralInputGate(BINDING, THREAD)
        with self.assertRaises(GateError):
            gate.arm(boundary(1), c)

    def test_message_pump_and_worker_must_continue(self):
        for field in ("message_pump_continued", "worker_dispatch_continued"):
            with self.subTest(field=field):
                gate = armed()
                with self.assertRaises(GateError):
                    gate.observe_cycle(cycle(2, **{field: False}))
                self.assert_closed(gate)
                self.assertFalse(gate.status()["neutral_publication_confirmed"])
                gate.observe_cycle(cycle(3))
                self.assertTrue(gate.status()["neutral_publication_confirmed"])

    def test_all_physical_paths_block_release_even_with_neutral_publication(self):
        physical = [PhysicalState(keyboard_down=(30,)), PhysicalState(modifier_bits=0x22),
                    PhysicalState(mouse_buttons=(0,)), PhysicalState(mouse_motion_or_wheel=True),
                    PhysicalState(controller_buttons=(1,)), PhysicalState(controller_axes=(2,)),
                    PhysicalState(unknown=True)]
        for p in physical:
            with self.subTest(physical=p):
                gate = release_pending()
                self.assertIsNone(gate.observe_cycle(cycle(2, physical=p)))
                self.assert_closed(gate)
                receipt = gate.observe_cycle(cycle(3))
                self.assertIsNotNone(receipt)

    def test_posted_backlog_must_be_drained_before_release(self):
        gate = release_pending()
        self.assertIsNone(gate.observe_cycle(cycle(2, pending_gameplay_messages=3)))
        self.assertIsNone(gate.observe_cycle(cycle(3, pending_gameplay_messages=1)))
        receipt = gate.observe_cycle(cycle(4))
        gate.acknowledge_release(boundary(4), receipt, GRANT)
        self.assertEqual(gate.state, "OPEN")

    def test_old_neutral_cycle_cannot_satisfy_new_release_barrier(self):
        gate = armed()
        gate.observe_cycle(cycle(2))
        gate.request_release(boundary(2), GRANT)
        self.assertFalse(gate.status()["release_receipt_ready"])
        with self.assertRaises(GateError):
            gate.observe_cycle(cycle(2))
        self.assertFalse(gate.status()["release_receipt_ready"])
        self.assertIsNotNone(gate.observe_cycle(cycle(3)))

    def test_new_held_key_revokes_previously_eligible_receipt(self):
        gate = release_pending()
        receipt = gate.observe_cycle(cycle(2))
        self.assertIsNone(gate.observe_cycle(cycle(3, physical=PhysicalState(keyboard_down=(30,)))))
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(3), receipt, GRANT)
        self.assert_closed(gate)

    def test_new_neutral_cycle_supersedes_older_receipt(self):
        gate = release_pending()
        old = gate.observe_cycle(cycle(2))
        gate.observe_cycle(cycle(3))
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(3), old, GRANT)
        self.assert_closed(gate)
        # Rejection consumes eligibility: a new complete cycle is required.
        fresh = gate.observe_cycle(cycle(4))
        gate.acknowledge_release(boundary(4), fresh, GRANT)

    def test_wrong_attempt_attachment_or_generation_rejects_and_revokes(self):
        for b in [replace(BINDING, attempt="d" * 32), replace(BINDING, attachment="d" * 32),
                  replace(BINDING, generation=1)]:
            with self.subTest(binding=b):
                gate = release_pending()
                receipt = gate.observe_cycle(cycle(2))
                with self.assertRaises(GateError):
                    gate.observe_cycle(cycle(3, binding=b))
                with self.assertRaises(GateError):
                    gate.acknowledge_release(boundary(2), receipt, GRANT)
                self.assert_closed(gate)

    def test_partial_publication_failure_invalidates_release(self):
        gate = release_pending()
        receipt = gate.observe_cycle(cycle(2))
        c = cycle(3)
        c = replace(c, channels=tuple(replace(e, neutral=False) if e.name == "raw_keyboard" else e for e in c.channels))
        with self.assertRaises(GateError):
            gate.observe_cycle(c)
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(2), receipt, GRANT)
        self.assert_closed(gate)

    def test_ack_rechecks_pending_commands_and_current_boundary(self):
        for b in [boundary(2, pending_dispatch=True), boundary(2, pending_menu=0),
                  boundary(2, pending_advance=True), boundary(2, phase=1), boundary(1),
                  replace(boundary(2), thread_id=78)]:
            with self.subTest(boundary=b):
                gate = release_pending()
                receipt = gate.observe_cycle(cycle(2))
                with self.assertRaises(GateError):
                    gate.acknowledge_release(b, receipt, GRANT)
                self.assert_closed(gate)

    def test_cancelled_or_changed_controller_grant_cannot_release(self):
        gate = release_pending()
        receipt = gate.observe_cycle(cycle(2))
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(2), receipt, "d" * 32)
        gate.cancel_release()
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(2), receipt, GRANT)
        self.assert_closed(gate)
        gate.observe_cycle(cycle(3))
        gate.request_release(boundary(3), "d" * 32)
        new = gate.observe_cycle(cycle(4))
        gate.acknowledge_release(boundary(4), new, "d" * 32)

    def test_forged_receipt_cannot_release(self):
        gate = release_pending()
        receipt = gate.observe_cycle(cycle(2))
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(2), replace(receipt, nonce="0" * 32), GRANT)
        self.assert_closed(gate)

    def test_verified_attachment_handoff_closes_and_discards_old_evidence(self):
        gate = release_pending()
        old = gate.observe_cycle(cycle(2))
        new_binding = Binding(BINDING.attempt, "d" * 32, 1)
        gate.handoff_attachment(BINDING, new_binding, boundary(3, new_binding), cycle(3, new_binding), "e" * 32)
        self.assertEqual(gate.state, "HELD")
        self.assert_closed(gate)
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(3, new_binding), old, GRANT)
        gate.observe_cycle(cycle(4, new_binding))
        gate.request_release(boundary(4, new_binding), "f" * 32)
        self.assertIsNone(gate.observe_cycle(cycle(5, new_binding, PhysicalState(keyboard_down=(30,)))))
        fresh = gate.observe_cycle(cycle(6, new_binding))
        gate.acknowledge_release(boundary(6, new_binding), fresh, "f" * 32)
        self.assertEqual(gate.state, "OPEN")

    def test_handoff_rejects_unverified_shape_skipped_generation_and_old_cycle(self):
        for new, n, verification in [
            (Binding("f" * 32, "d" * 32, 1), 2, "e" * 32),
            (Binding(BINDING.attempt, "d" * 32, 2), 2, "e" * 32),
            (Binding(BINDING.attempt, BINDING.attachment, 1), 2, "e" * 32),
            (Binding(BINDING.attempt, "d" * 32, 1), 1, "e" * 32),
            (Binding(BINDING.attempt, "d" * 32, 1), 2, ""),
        ]:
            gate = armed()
            with self.assertRaises(GateError):
                gate.handoff_attachment(BINDING, new, boundary(n, new), cycle(n, new), verification)
            self.assertEqual(gate.binding, BINDING)
            self.assertFalse(gate.status()["neutral_publication_confirmed"])
            self.assert_closed(gate)

    def test_request_release_after_bad_observation_requires_fresh_good_cycle(self):
        gate = armed()
        with self.assertRaises(GateError):
            gate.observe_cycle(replace(cycle(2), channels=()))
        with self.assertRaises(GateError):
            gate.request_release(boundary(1), GRANT)
        gate.observe_cycle(cycle(3))
        gate.request_release(boundary(3), GRANT)

    def test_once_open_cannot_reuse_attempt_or_ack_twice(self):
        gate = release_pending()
        receipt = gate.observe_cycle(cycle(2))
        gate.acknowledge_release(boundary(2), receipt, GRANT)
        with self.assertRaises(GateError):
            gate.acknowledge_release(boundary(2), receipt, GRANT)
        with self.assertRaises(GateError):
            gate.arm(boundary(3), cycle(3))

    def test_type_confusion_not_treated_as_neutral_or_valid_sequence(self):
        bad = [replace(cycle(1), cycle_id=True),
               replace(cycle(1), physical=PhysicalState(modifier_bits=False)),
               replace(cycle(1), physical=PhysicalState(unknown=0)),
               replace(cycle(1), pending_gameplay_messages=False)]
        for c in bad:
            gate = NeutralInputGate(BINDING, THREAD)
            with self.assertRaises(GateError):
                gate.arm(boundary(1), c)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "schema": "san14.transition-input-gate-contract-tests.v1",
        "result": "PASS" if result.wasSuccessful() else "FAIL",
        "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
        "scope": "Trusted-adapter protocol and synthetic evidence only; actual machine-code omissions are tested separately in transition_input_gate_shadow.py.",
        "native_gate_complete": False, "game_process_access": False, "visible_windows_created": 0,
    }
    (P / "transition_input_gate_contract_test.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
