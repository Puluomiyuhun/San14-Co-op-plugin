"""Classify a complete narrow trace. Absence in an incomplete trace proves nothing."""
import argparse
import json
from pathlib import Path

KINDS = {'combat_gate', 'combat_entry', 'pairs_ready', 'pair_eligibility',
         'casualty_request', 'batch_boundary'}

def analyze(rows):
    events = [r for r in rows if r['event'] in KINDS]
    result = {'status': 'INCOMPLETE', 'branch': None, 'observed_events': len(events),
              'historical_run_a_cause_proven': False}
    if any(r['event'] in ('error', 'error_cleanup', 'process_exit') for r in rows):
        return dict(result, status='INVALID', reason='Observer reported an error or process exit')
    boundary = [r for r in events if r['event'] == 'batch_boundary']
    gate = [r for r in events if r['event'] == 'combat_gate' and r['subday'] == 10]
    if len(boundary) != 1 or len(gate) != 1:
        return dict(result, reason='Scheduled gate and completed stage12 boundary are required')
    if not rows or rows[-1] != {'event': 'detached', 'captured': True, 'registers_restored': True}:
        return dict(result, reason='Clean capture and register restoration are required')
    if not any(r['event'] == 'armed' for r in rows):
        return dict(result, status='INVALID', reason='Missing armed event')
    if [r['seq'] for r in events] != list(range(1, len(events)+1)):
        return dict(result, status='INVALID', reason='Noncontiguous event sequence')
    if events[-1] != boundary[0] or boundary[0]['stage'] != 13:
        return dict(result, status='INVALID', reason='Wrong terminal stage')
    if any(r['date'] != [203, 8, 11] or r['stage'] != 12 for r in events[:-1]):
        return dict(result, status='INVALID', reason='Outside expected stage/date')
    selected = events[events.index(gate[0])+1:-1]
    entries = [r for r in selected if r['event'] == 'combat_entry']
    ready = [r for r in selected if r['event'] == 'pairs_ready']
    decisions = [r for r in selected if r['event'] == 'pair_eligibility']
    damage = [r for r in selected if r['event'] == 'casualty_request']
    def invalid(reason):
        return dict(result, status='INVALID', reason=reason)
    if len(ready) > 1:
        return invalid('Repeated build-return unsupported')
    if not gate[0]['rbp_gate']:
        if selected:
            return invalid('Closed time gate nevertheless has combat events')
        branch = 'time_gate_closed'
    elif not entries:
        return invalid('Open time gate without recorded function entry')
    elif not ready:
        if decisions or damage or any(r['pending_94'] == 0 for r in entries):
            return invalid('Missing build-return incompatible with observed entry/processing')
        branch = 'pending_path_without_rebuild'
    else:
        if entries[0]['pending_94'] != 0 or ready[0]['seq'] < entries[0]['seq']:
            return invalid('Build-return incompatible with first function entry')
        if any(r['seq'] < ready[0]['seq'] for r in decisions+damage):
            return invalid('Processing before observed build-return')
        if ready[0]['build_result'] == 0:
            if decisions or damage:
                return invalid('Zero build result nevertheless has pair processing')
            branch = 'builder_returned_zero'
        elif ready[0]['pair_count'] == 0:
            if decisions or damage:
                return invalid('Empty rebuilt list nevertheless has pair processing')
            branch = 'rebuilt_list_empty'
        elif damage:
            branch = 'casualty_requests_observed'
        elif len(decisions) == ready[0]['pair_count'] and all(
                not r['eligibility_before_special_filter'] for r in decisions):
            branch = 'all_pairs_rejected_before_special_filter'
        else:
            branch = 'pairs_built_without_observed_casualty_requests'
    result.update(status='COMPLETE', branch=branch, entry_count=len(entries),
                  build_return_count=len(ready), eligibility_count=len(decisions),
                  eligible_before_special_filter=sum(bool(r['eligibility_before_special_filter']) for r in decisions),
                  casualty_request_count=len(damage),
                  observed_special_filter_values=sorted({r['special_filter'] for r in events}),
                  observed_world_165c_values=sorted({r['world_165c'] for r in events}),
                  selected_gate=gate[0], boundary=boundary[0], build_return=ready[0] if ready else None,
                  limitations=['Debugger changes timing; a new normal run cannot explain old run A.',
                               'No casualty request does not prove every combat effect absent.',
                               'Pair eligibility is sampled BEFORE the optional special filter.',
                               'Only selected fields and first scheduled batch are observed.'])
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze([json.loads(x) for x in args.trace.read_text(encoding='utf-8').splitlines()])
    with args.output.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('selected_gate','boundary','build_return')}, ensure_ascii=False))
