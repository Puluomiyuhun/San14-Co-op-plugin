"""Offline negative controls for newly covered diagnostic fields."""
from copy import deepcopy
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'outputs' / 'san14-link'))
from proposal_state_reader import coverage_hashes, decode_proposal, ProposalStateReader


def main():
    source = ROOT / 'lockstep-traces' / 'proposal-durability-restored-o.json'
    original = json.loads(source.read_text(encoding='utf-8'))
    hashes = coverage_hashes(original)
    checks = []

    def changed(label, mutate, expected_key):
        modified = deepcopy(original)
        mutate(modified)
        observed = coverage_hashes(modified)
        assert observed[expected_key] != hashes[expected_key], label
        # The other domain should not be accidentally coupled to this change.
        other = next(k for k in hashes if k != expected_key)
        assert observed[other] == hashes[other], label
        checks.append({'case': label, 'passed': True})

    proposal_key = 'player_bound_proposal_payload_sha256'
    city_key = 'city_linked_durability_sha256'

    def alter_byte(data, offset):
        row = data['proposals'][1]
        raw = bytearray.fromhex(row['raw_00_30_hex'])
        raw[offset] ^= 1
        data['proposals'][1] = decode_proposal(bytes(raw), 1)

    changed('proposal parameter changes while old world sample could match',
            lambda x: alter_byte(x, 0x18), proposal_key)
    changed('unknown proposal byte retained in diagnostic digest',
            lambda x: alter_byte(x, 0x2F), proposal_key)
    changed('different local player context changes proposal identity',
            lambda x: x['context']['player'].update(force_id=13), proposal_key)
    changed('proposal slot order is retained',
            lambda x: x['proposals'].reverse(), proposal_key)
    changed('city-linked object durability changes independently of proposals',
            lambda x: x['city_linked_objects'][19].update(
                endurance_object_14=x['city_linked_objects'][19]['endurance_object_14'] + 1), city_key)

    raw = bytes.fromhex(original['proposals'][1]['raw_00_30_hex'])
    for label, record, slot in (
        ('truncated record rejected', raw[:-1], 1),
        ('unsupported slot rejected', raw, 31),
        ('unsupported proposal type rejected', raw[:0x10] + b'\xff\xff' + raw[0x12:], 1),
        ('unsupported person id rejected', raw[:0x14] + b'\xff\xff' + raw[0x16:], 1),
    ):
        try:
            decode_proposal(record, slot)
        except ValueError:
            checks.append({'case': label, 'passed': True})
        else:
            raise AssertionError(label)

    class ChangingReader(ProposalStateReader):
        def __init__(self):
            self.count = 0

        def capture_once(self):
            self.count += 1
            data = deepcopy(original)
            if self.count == 2:
                alter_byte(data, 0x18)
            return data

    try:
        ChangingReader().capture()
    except RuntimeError:
        checks.append({'case': 'unstable repeated reads rejected', 'passed': True})
    else:
        raise AssertionError('unstable capture accepted')
    report = {'mode': 'offline negative controls; no game access or mutation',
              'checks': checks, 'result': 'PASS',
              'limits': 'Validates diagnostic coverage and rejection, not actual gameplay or network replication'}
    with (ROOT / 'proposal-coverage-validation.json').open('x', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({'result': 'PASS', 'checks': len(checks)}))


if __name__ == '__main__':
    main()
