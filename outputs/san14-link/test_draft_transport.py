"""Offline rejection checks for the read-only transport boundary."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile

from live_draft_demo import canonical, validate_packet
from sortie_reader import pointer_vector


class DraftTransportTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).with_name("出征草稿-含战法.json")
        self.payload = json.loads(path.read_text(encoding="utf-8"))
        self.token = "offline-test-token"

    def packet(self, payload=None):
        payload = copy.deepcopy(self.payload if payload is None else payload)
        return {"token": self.token, "payload": payload,
                "payload_sha256": hashlib.sha256(canonical(payload)).hexdigest()}

    def test_captured_draft_preserves_destination_and_troops(self):
        receipt = validate_packet(self.packet(), self.token)
        self.assertFalse(receipt["applied_to_game"])
        unit = receipt["partial_order"]["units"][0]
        self.assertEqual((unit["officer_name"], unit["soldiers"], unit["destination"]["name"]),
                         ("张鲁", 1300, "长安"))
        self.assertEqual([(t["slot"], t["id"], t["name"]) for t in unit["tactics"]],
                         [(1, 157, "万法归一"), (2, 7, "激励"), (3, 18, "鼓舞")])

    def test_altered_tactic_is_rejected(self):
        packet = self.packet()
        packet["payload"]["partial_order"]["units"][0]["tactics"][0]["id"] = 1
        with self.assertRaises(ValueError):
            validate_packet(packet, self.token)

    def test_altered_troop_count_is_rejected(self):
        packet = self.packet()
        packet["payload"]["partial_order"]["units"][0]["soldiers"] = 9999
        with self.assertRaises(ValueError):
            validate_packet(packet, self.token)

    def test_mismatching_inner_checksum_is_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["partial_order"]["source_city"]["id"] = 20
        with self.assertRaises(ValueError):
            validate_packet(self.packet(payload), self.token)

    def test_wrong_token_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet(self.packet(), "a-different-token")

    def test_execution_claim_is_rejected_even_with_valid_hash(self):
        for key in ("submitted", "replay_supported"):
            with self.subTest(key=key):
                payload = copy.deepcopy(self.payload)
                payload[key] = True
                with self.assertRaises(ValueError):
                    validate_packet(self.packet(payload), self.token)

    def test_corrupt_vector_is_rejected_before_following_pointer(self):
        import struct

        class CorruptMemory:
            def __init__(self, header):
                self.header = header
                self.calls = 0

            def read(self, address, length):
                self.calls += 1
                if self.calls != 1:
                    raise AssertionError("Followed a corrupt vector pointer")
                return self.header

        for fields in ((0x10000, 0xFFFF, 0x10008),
                       (0x10000, 0x10008, 0x7FFFFFFF0000),
                       (0x10001, 0x10009, 0x10009)):
            with self.subTest(fields=fields):
                memory = CorruptMemory(struct.pack("<QQQ", *fields))
                with self.assertRaises(RuntimeError):
                    pointer_vector(memory, 0x12340)
                self.assertEqual(memory.calls, 1)

    def test_failed_run_replaces_an_old_pass_report(self):
        import live_draft_demo
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "result.json"
            report.write_text('{"result":"PASS"}', encoding="utf-8")
            with patch("sys.argv", ["live_draft_demo.py", "--output", str(report)]), \
                    patch.object(live_draft_demo, "run_live_demo", side_effect=RuntimeError("Game closed")), \
                    patch("builtins.print"):
                self.assertEqual(live_draft_demo.main(), 1)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8"))["result"], "FAIL")


if __name__ == "__main__":
    unittest.main()
