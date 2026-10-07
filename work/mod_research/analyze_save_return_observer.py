"""Offline evidence summarizer. Never attaches to or changes the game."""
from pathlib import Path
import argparse
import hashlib
import json


def analyze(trace):
    records = [json.loads(line) for line in trace.read_text(encoding='utf8').splitlines() if line.strip()]
    calls = {}
    snapshots = []
    stacks = []
    for row in records:
        if 'stack' in row:
            snapshots.append(row)
            stack = [item['name'] for item in row['stack']]
            if not stacks or stacks[-1] != stack:
                stacks.append(stack)
        if row['event'] == 'callback':
            calls.setdefault((row['thread'], row['call_id']), []).append(row)
    summaries = []
    errors = []
    for key, group in calls.items():
        boundaries = [row['boundary'] for row in group]
        paired = boundaries == ['entry', 'native_ret', 'returned']
        if paired:
            a, b, c = group
            paired = (a['entry_rsp'] == b['rsp'] and int(c['rsp'], 16) == int(a['entry_rsp'], 16) + 8
                      and b['rax'] == c['rax'] and a['entry_args'] == b['entry_args'] == c['entry_args']
                      and a['callback'] == b['callback'] == c['callback'])
        if not paired:
            errors.append({'call': list(key), 'reason': 'unpaired_or_mismatched_callback'})
        summaries.append({'thread': key[0], 'call_id': key[1], 'callback': group[0]['callback'],
            'paired': paired, 'raw_edx': int(group[0]['rdx'], 16) & 0xffffffff,
            'event_kind_edx': (int(group[0]['rdx'], 16) & 0xffffffff)
                if group[0]['callback'] in ('enter', 'exit') else None,
            'return_rax': group[-1]['rax'] if paired else None,
            'boundaries': [{field: row.get(field) for field in ('boundary', 'sequence', 'phase',
                'control_pause', 'cursor_enabled', 'coordinator_flags', 'toolbar_pending',
                'panel_advance', 'advance_game', 'pending_count', 'cache_mode')}
                | {'stack': [state['name'] for state in row['stack']]} for row in group]})
    for row in records:
        if row['event'] in ('incomplete_error', 'error_cleanup', 'other_exception', 'thread_exit_pending_call', 'process_exit'):
            errors.append(row)
    ending = records[-1] if records else {}
    complete = (ending.get('event') == 'detached' and ending.get('complete') is True
                and ending.get('registers_restored') is True and not errors
                and {call['callback'] for call in summaries if call['paired']} == {'exit', 'pause', 'resume', 'enter'})
    return {'schema': 'san14.normal-menu-observation.v2',
        'result': 'CALLBACK_OBSERVATION_COMPLETE' if complete else 'INCOMPLETE',
        'trace': str(trace), 'trace_sha256': hashlib.sha256(trace.read_bytes()).hexdigest(),
        'records': len(records), 'callback_calls': summaries, 'state_sequences': stacks,
        'observed_dates': sorted({row['date_raw'] for row in snapshots}),
        'observed_global_rng': sorted({str(row.get('global_rng')) for row in snapshots}),
        'same_user_pointer_in_observations': len({row.get('user') for row in snapshots}) == 1,
        'all_four_callback_pairs_captured': bool(summaries) and all(call['paired'] for call in summaries)
            and {call['callback'] for call in summaries} == {'exit', 'pause', 'resume', 'enter'},
        'callback_threads': sorted({call['thread'] for call in summaries}),
        'all_snapshots_valid': bool(snapshots) and all(row['snapshot_valid'] for row in snapshots),
        'errors': errors, 'ending': ending,
        'scope': 'Normal menu User callbacks only; debugger changes timing; coarse samples are asynchronous.',
        'native_checkpoint_export_tested': False, 'full_world_equivalence_proven': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    args = parser.parse_args()
    report = analyze(args.trace)
    target = args.trace.with_name('analysis-v2.json')
    with target.open('x', encoding='utf8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
