"""Offline guard tests use synthetic post-command data, never a game process."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from pilot_evidence import check_native_trace, check_native_effect, check_restored, load_json

ROOT = Path(__file__).resolve().parent


def rehash(snapshot):
    data = json.dumps(snapshot['critical_state'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    snapshot['critical_state_sha256'] = hashlib.sha256(data).hexdigest()


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.before = load_json(ROOT / 'before-native-submit.json')
        self.words = [0] * 26
        self.words[0], self.words[2] = 666, 1300
        self.words[3:8] = [4, 11, 157, 7, 18]
        self.words[13:16] = [4, 5, 20]
        used = {u['id'] for u in self.before['all_active_units']}
        army_id = next(i for i in range(1, 501) if i not in used)
        self.unit = {'id': army_id, 'officer_id': 666, 'soldiers': 1300, 'formation_id': 4,
                     'naval_formation_id': 11, 'tactic_ids': [157, 7, 18], 'order_code': 4,
                     'destination_type': 5, 'destination_id': 20}
        self.after = copy.deepcopy(self.before)
        self.after['critical_state']['city']['garrison'] -= 1300
        self.after['critical_state']['district']['action_points'] -= 1
        self.after['critical_state']['officer_units'] = [self.unit]
        self.after['all_active_units'].append(self.unit)
        rehash(self.after)
        self.trace = [{'event': 'submit_entry', 'flags': 1, 'caller_rva': 0x7149D9, 'words': self.words},
                      {'event': 'detached', 'captured': True, 'registers_restored': True}]

    def test_synthetic_nominal_effect(self):
        self.assertEqual(check_native_effect(self.before, self.after, check_native_trace(self.trace))['result'], 'PASS')

    def test_wrong_callsite(self):
        self.trace[0]['caller_rva'] = 0x30930
        with self.assertRaisesRegex(RuntimeError, 'player submission'):
            check_native_trace(self.trace)

    def test_missing_cleanup(self):
        with self.assertRaisesRegex(RuntimeError, 'detach'):
            check_native_trace(self.trace[:-1])

    def test_duplicate_capture(self):
        with self.assertRaisesRegex(RuntimeError, 'Exactly one'):
            check_native_trace([self.trace[0]] + self.trace)

    def test_double_cost(self):
        self.after['critical_state']['city']['garrison'] -= 1300
        rehash(self.after)
        with self.assertRaisesRegex(RuntimeError, 'garrison'):
            check_native_effect(self.before, self.after, self.words)

    def test_existing_army_changed(self):
        self.after['all_active_units'][0]['soldiers'] += 1
        with self.assertRaisesRegex(RuntimeError, 'existing army'):
            check_native_effect(self.before, self.after, self.words)

    def test_wrong_destination(self):
        self.unit['destination_id'] = 19
        rehash(self.after)
        with self.assertRaisesRegex(RuntimeError, 'differs'):
            check_native_effect(self.before, self.after, self.words)

    def test_digest_tampering(self):
        self.after['critical_state']['city']['garrison'] += 1
        with self.assertRaisesRegex(RuntimeError, 'digest'):
            check_native_effect(self.before, self.after, self.words)

    def test_restore_before(self):
        self.assertEqual(check_restored(self.before, copy.deepcopy(self.before))['result'], 'PASS')

    def test_restore_rejects_pending_army(self):
        with self.assertRaisesRegex(RuntimeError, 'baseline'):
            check_restored(self.before, self.after)


if __name__ == '__main__':
    unittest.main(verbosity=2)
