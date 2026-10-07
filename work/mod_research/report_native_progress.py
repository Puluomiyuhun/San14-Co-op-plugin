"""Record observed effects separately from unavailable native call evidence."""
import json
from pathlib import Path
import struct
import argparse
from pilot_evidence import check_native_effect, check_restored, check_checkpoint, check_native_trace, load_json

root = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--trace', type=Path)
parser.add_argument('--pilot-report', type=Path)
args = parser.parse_args()
before = load_json(root / 'before-native-submit.json')
after = load_json(root / 'after-native-submit.json')
restored = load_json(root / 'restored-34-first.json')
# This is the pre-confirmation destination draft, NOT a captured native call.
draft = (root / 'target-draft-0-before-behavior.bin').read_bytes()
words = list(struct.unpack('<26I', draft[4:108]))
report = {
    'schema': 'san14.sortie-pilot-progress.v1',
    'source': 'Observed live game snapshots before/after the user submitted a normal command and loaded slot 34',
    'normal_submit': check_native_effect(before, after, words),
    'restore_slot_34': check_restored(before, restored),
    'native_call_trace_captured': False,
    'native_call_trace_note': 'The observer timed out before this first submission; a second observation is pending',
    'game_data_written_by_pilot': False,
    'autonomous_replay_verified': False,
    'two_client_multiplayer_verified': False,
    'limitations': 'Focused state and semantic active-army comparison only; full world and RNG are not covered',
}
if args.trace:
    rows = [json.loads(line) for line in args.trace.read_text().splitlines() if line]
    command = check_native_trace(rows)
    second = check_native_effect(before, load_json(root / 'after-native-captured-submit.json'), command)
    report['native_call_trace_captured'] = True
    report['native_call_trace_note'] = 'Second normal submission captured and debugger detached with registers restored'
    report['captured_submit'] = second
    report['native_call'] = {'entry_rva': '0x1d1940', 'caller_rva': '0x7149d9',
                             'thread_id': next(r['thread_id'] for r in rows if r['event'] == 'submit_entry'),
                             'flags': 1, 'command_words': command}
    fields = load_json(root / 'native-command-army-fields.json')
    report['command_to_army_fields'] = {
        'direct_matches': sum(row['equal'] for row in fields['comparisons']),
        'checked_fields': len(fields['comparisons']),
        'differences': [row for row in fields['comparisons'] if not row['equal']],
        'note': 'One field changes between function entry and final army state; compare its final value again after the pilot'}
if args.pilot_report:
    pilot = load_json(args.pilot_report)
    if pilot.get('schema') != 'san14.native-call-substitution-pilot.v1' or pilot.get('result') != 'PASS':
        raise RuntimeError('Expected a verified pilot report')
    report['game_data_written_by_pilot'] = pilot['game_data_written_by_pilot']
    report['restricted_native_call_substitution'] = {
        'result': pilot['result'], 'local_draft_soldiers': pilot['local_draft_soldiers'],
        'executed_soldiers': pilot['recorded_command_soldiers'],
        'post_pilot_restore': pilot['post_pilot_restore'],
        'details': args.pilot_report.name,
        'autonomous_submission': False,
    }
check_checkpoint(root.parent / 'mod_test' / 'replay-checkpoint-34' / 'svdexSC34.s14')
target = root.parents[1] / 'outputs' / 'san14-link' / '出征执行与读档验证.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, ensure_ascii=True, indent=2))
