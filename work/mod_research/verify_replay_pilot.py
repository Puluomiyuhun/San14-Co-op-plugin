"""Validate a real native-call substitution using trace and live-state evidence.

This only reads recorded evidence. It cannot modify the game or turn a missing
trace into a successful result.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import struct
from pilot_evidence import (check_native_trace, check_native_effect, check_restored,
                            load_json, require)

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--army-fields', type=Path, required=True)
    parser.add_argument('--final-restored', type=Path)
    args = parser.parse_args()
    metadata = load_json(args.trace.parent / 'metadata.json')
    native_trace = Path(metadata['native_trace'])
    original_rows = [json.loads(line) for line in native_trace.read_text().splitlines() if line]
    original_words = check_native_trace(original_rows)
    original_entry = next(row for row in original_rows if row['event'] == 'submit_entry')
    rows = [json.loads(line) for line in args.trace.read_text().splitlines() if line]
    substitutions = [row for row in rows if row['event'] == 'recorded_command_substituted']
    require(substitutions == [{'event': 'recorded_command_substituted', 'original_soldiers': 1000,
                               'recorded_soldiers': 1300, 'bytes': 104}],
            'Exactly one successful 1000-to-1300 substitution is required')
    # Apply the normal entry/caller/cleanup checks to the rest of this trace.
    replay_words = check_native_trace([row for row in rows if row['event'] != 'recorded_command_substituted'])
    require(replay_words == original_words, 'Executed payload differs from the captured native command')
    replay_entry = next(row for row in rows if row['event'] == 'submit_entry')
    original_metadata = load_json(native_trace.parent / 'metadata.json')
    require(metadata['pid'] == original_metadata['pid'], 'Different game process than the native capture')
    # Normal native calls need not run on one permanent thread. The actual pilot
    # used a different OS thread but the same natural player callsite. Do not
    # misreport that as fixed-thread replay or silently rewrite the observation.
    require(type(replay_entry['thread_id']) is int and replay_entry['thread_id'] > 0,
            'Missing game thread observation')
    expected_words = original_words.copy()
    expected_words[2] = 1000
    require((args.trace.parent / 'expected.bin').read_bytes() == struct.pack('<26I', *expected_words),
            'Expected command file differs from the permitted pilot')
    require((args.trace.parent / 'recorded.bin').read_bytes() == struct.pack('<26I', *original_words),
            'Recorded command file differs from the captured native command')
    before = load_json(ROOT / 'before-native-submit.json')
    after = load_json(args.after)
    effect = check_native_effect(before, after, replay_words)
    normal_after = load_json(ROOT / 'after-native-captured-submit.json')
    equal_to_normal = check_restored(normal_after, after)
    original_fields = load_json(ROOT / 'native-command-army-fields.json')
    replay_fields = load_json(args.army_fields)
    require(replay_fields == original_fields,
            'Final army command-related fields differ from the native submission')
    final_restore = {'result': 'PENDING', 'note': 'Native slot-34 reload after the pilot is still required'}
    if args.final_restored:
        final_restore = check_restored(before, load_json(args.final_restored))
    report = {
        'schema': 'san14.native-call-substitution-pilot.v1',
        'verified_at': datetime.now().astimezone().isoformat(timespec='seconds'),
        'result': 'PASS',
        'scope': 'One user-triggered native sortie call using an earlier recorded payload in the same process',
        'exe_sha256': after['exe_sha256'],
        'local_draft_soldiers': 1000,
        'recorded_command_soldiers': 1300,
        'game_data_written_by_pilot': True,
        'bytes_written': 104,
        'entry_rva': '0x1d1940',
        'caller_rva': '0x7149d9',
        'same_thread_id_as_earlier_native_capture': replay_entry['thread_id'] == original_entry['thread_id'],
        'earlier_native_thread_id': original_entry['thread_id'],
        'used_current_native_call_thread': True,
        'game_thread_id': replay_entry['thread_id'],
        'thread_note': 'The OS thread id changed between submissions. This pilot follows the natural call; a future adapter cannot assume one permanent thread id.',
        'command_words': replay_words,
        'debugger_detached_and_registers_restored': True,
        'observed_effect': effect,
        'focused_result_equals_normal_submission': equal_to_normal,
        'final_army_field_comparisons_equal_normal_submission': True,
        'final_army_fields_compared': len(replay_fields['comparisons']),
        'derived_field_example': {'command_offset': '0x60', 'input': 48400,
                                 'army_offset': '0x48', 'final_in_both_cases': 21433},
        'post_pilot_restore': final_restore,
        'autonomous_submission': False,
        'network_command_applied_to_second_game': False,
        'two_client_multiplayer': False,
        'limitations': [
            'Only this version, scenario, actor, source city and destination were tested',
            'UI confirmation still supplies the original native call; no autonomous game-thread queue exists',
            'Focused city/officer/district and active-army evidence does not cover the complete world or RNG',
            'Behavior-option names and one conditionally inactive command field remain unverified',
        ],
    }
    destination = ROOT.parents[1] / 'outputs' / 'san14-link' / '受限命令回放验证.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
