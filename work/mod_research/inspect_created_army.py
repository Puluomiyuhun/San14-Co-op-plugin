"""Read-only check of native command fields against the created army object.

Unknown fields retain offset labels; this does not assign unverified UI meanings.
"""
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'outputs' / 'san14-link'))
from battle_observer import BattleObserver
from game_reader import DATA_POINTER_RVA
from pilot_evidence import check_native_trace, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.trace.read_text().splitlines() if line]
    words = check_native_trace(rows)
    reader = BattleObserver()
    try:
        before = reader.capture()
        units = before['critical_state']['officer_units']
        require(len(units) == 1, 'Expected one Zhang Lu army')
        root = reader.pointer(reader.memory.base + DATA_POINTER_RVA)
        unit = reader.pointer(root + 0x7DF60 + units[0]['id'] * 8)
        reader.require_type(unit, 'CArmyUnitData')
        data = reader.memory.read(unit, 0x200)
        require(before == reader.capture() and data == reader.memory.read(unit, 0x200),
                'Army changed while sampling')
    finally:
        reader.close()
    # Source evidence: 0x2A2500 initialization and 0x2BBC60 route setter.
    mappings = [(0, 0x12, 'H'), (4, 0x14, 'H'), (8, 0x16, 'H'),
                (0x0c, 0x1b, 'B'), (0x10, 0x1c, 'B'),
                (0x14, 0x1d, 'B'), (0x18, 0x1e, 'B'), (0x1c, 0x1f, 'B')]
    mappings += [(0x20 + i * 4, 0x2c + i * 2, 'H') for i in range(5)]
    mappings += [(0x34, 0x37, 'B'), (0x38, 0x38, 'B'), (0x3c, 0x3a, 'H'),
                 (0x40, 0x56, 'B'), (0x44, 0x40, 'B'), (0x50, 0x41, 'B'),
                 (0x54, 0x42, 'H'), (0x58, 0x44, 'H'), (0x5c, 0x46, 'B'), (0x60, 0x48, 'H')]
    comparisons = []
    for source, dest, fmt in mappings:
        actual = struct.unpack_from('<' + fmt, data, dest)[0]
        expected = words[source // 4]
        comparisons.append({'command_offset': hex(source), 'army_offset': hex(dest),
                            'command_value': expected, 'army_value': actual, 'equal': actual == expected})
    for source, mask in [(0x48, 4), (0x4c, 8)]:
        actual = int(bool(data[0x26] & mask))
        expected = int(words[source // 4] == 1)
        comparisons.append({'command_offset': hex(source), 'army_offset': '0x26', 'bit_mask': mask,
                            'command_value': words[source // 4], 'expected_bit': expected,
                            'army_value': actual, 'equal': actual == expected})
    result = {'mode': 'read-only-native-command-effect-check', 'army_id': units[0]['id'],
              'matched': all(row['equal'] for row in comparisons), 'comparisons': comparisons,
              'uncompared': [{'command_offset': '0x64',
                              'reason': 'Only assigned to army+0x13e when order_code is 17; pilot order is 4'}],
              'scope': '25 raw command fields; offset labels do not establish behavior-option names'}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
