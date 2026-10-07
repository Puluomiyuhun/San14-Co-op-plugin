"""Read-only witnesses around controlled native checkpoint pilots.

No writes to game, debugger, native calls, or claim of full-world coverage.
Capture outputs are exclusive so a later run cannot erase an earlier witness.
"""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from run_second_force_reward import BattleObserver, capture, CHECKPOINT
from startup_identity_reader import capture_startup_context
from analyze_startup_switch import compare_records
from start_startup_switch import no_debugger

ROOT = Path(__file__).resolve().parent
FOLDER = ROOT/'checkpoint-cycle-live'
spec = importlib.util.spec_from_file_location('hex_fields', ROOT/'checkpoint-coverage-hex.py')
hex_fields = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hex_fields)


def inventory():
    return {p.name: {'size': p.stat().st_size,
                     'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(CHECKPOINT.parent.glob('*.s14'))}


def sample():
    reader = BattleObserver()
    try:
        no_debugger(reader)
        objects = capture(reader)
        context = capture_startup_context(reader)
        tiles = hex_fields.capture(reader, hex_fields.audit())
        assert objects == capture(reader) and context == capture_startup_context(reader)
        assert reader.pointer(reader.memory.base+0x12CC4A8+0x28) == reader.memory.base+0x3F9B00
        files = inventory()
        assert files == inventory(), 'Save files changed during inventory'
        return {'created': datetime.now().astimezone().isoformat(),
                'context': context, 'objects': objects, 'tiles': tiles,
                'save_files': files, 'original_update_slot_restored': True,
                'game_writes': 0, 'full_world_coverage': False}
    finally:
        reader.close()


def path(label, max_length=70):
    assert 1 <= len(label) <= max_length and re.fullmatch('[a-z0-9-]+', label)
    return FOLDER/(label+'.json')


def comparison(before, after):
    objects = compare_records(before['objects'], after['objects'])
    a, b = before['save_files'], after['save_files']
    return {'objects': objects,
            'all_48400_hex_serialized_fields_equal': before['tiles']['ordered_payload_hex'] == after['tiles']['ordered_payload_hex'],
            'hex_payload_bytes': after['tiles']['all_slot_payload_bytes'],
            'sampled_global_rng_equal': before['objects']['global_rng'] == after['objects']['global_rng'],
            'sampled_world_rng_fields_equal': before['objects']['world_rng_fields_hex'] == after['objects']['world_rng_fields_hex'],
            'save_files_added': sorted(b.keys()-a.keys()),
            'save_files_removed': sorted(a.keys()-b.keys()),
            'existing_save_files_changed': sorted(k for k in a.keys() & b.keys() if a[k] != b[k]),
            'full_world_coverage': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', help='Exclusive witness label')
    p.add_argument('--compare', nargs=2, metavar=('BEFORE', 'AFTER'))
    args = p.parse_args()
    assert bool(args.capture) != bool(args.compare)
    FOLDER.mkdir(exist_ok=True)
    if args.capture:
        target = path(args.capture)
        assert not target.exists(), 'Witness already exists'
        value = sample()
        with target.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        print(json.dumps({'witness': str(target), 'records': len(value['objects']['records']),
                          'hex_slots': value['tiles']['slot_count'],
                          'save_files': len(value['save_files']), 'game_writes': 0}))
    else:
        before, after = [json.loads(path(label).read_text(encoding='utf-8')) for label in args.compare]
        result = comparison(before, after)
        target = path('-vs-'.join(args.compare), max_length=144)
        with target.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
