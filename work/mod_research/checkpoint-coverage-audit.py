"""Offline coverage crosswalk and conservative historical-record comparison.

No live game access. Never turns a partial match into full-world verification.
"""
from collections import Counter
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1] / 'outputs' / 'san14-link'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_records(a, b):
    """Existing 783-record format: only the proven army display pointer normalizes.

    Known identity-sensitive economic fields remain mismatches. Unknown fields
    are not dropped. Membership changes are reported rather than intersected.
    """
    left, right = a['records'], b['records']
    result = {'missing_records': sorted(left.keys() - right.keys()),
              'extra_records': sorted(right.keys() - left.keys()),
              'length_mismatches': [], 'raw_differences': [],
              'display_pointer_differences': [], 'unresolved_differences': [],
              'full_world_verified': False}
    equal_bytes = different_bytes = display_bytes = 0
    for key in sorted(left.keys() & right.keys()):
        x, y = bytes.fromhex(left[key]), bytes.fromhex(right[key])
        if len(x) != len(y):
            result['length_mismatches'].append(key)
            continue
        differences = []
        unresolved = []
        display = []
        for offset, (before, after) in enumerate(zip(x, y), 0x10):
            if before == after:
                equal_bytes += 1
                continue
            row = {'offset': offset, 'before': before, 'after': after}
            differences.append(row)
            different_bytes += 1
            if key.startswith('army:') and 0x148 <= offset < 0x150:
                display.append(row)
                display_bytes += 1
            else:
                unresolved.append(row)
        if differences:
            result['raw_differences'].append({'record': key, 'bytes': differences})
        if display:
            result['display_pointer_differences'].append({'record': key, 'bytes': display})
        if unresolved:
            known_economic = key.startswith('city:') and all(0xA0 <= r['offset'] < 0xA8 for r in unresolved)
            result['unresolved_differences'].append({'record': key, 'bytes': unresolved,
                'classification': 'known_identity_sensitive_economy_still_requires_rule_fix' if known_economic else 'unclassified_must_not_ignore'})
    result.update({'equal_bytes': equal_bytes, 'raw_different_bytes': different_bytes,
                   'known_display_pointer_different_bytes': display_bytes,
                   'matched_existing_partial_record_contract': not any(result[k] for k in
                       ('missing_records', 'extra_records', 'length_mismatches', 'unresolved_differences'))})
    if 'global_rng' in a and 'global_rng' in b:
        result['global_rng_equal'] = a['global_rng'] == b['global_rng']
        result['global_rng_before_after'] = [a['global_rng'], b['global_rng']]
    if 'world_rng_fields_hex' in a and 'world_rng_fields_hex' in b:
        result['world_450_460_equal'] = a['world_rng_fields_hex'] == b['world_rng_fields_hex']
    if 'focused' in a and 'focused' in b:
        result['active_army_semantics_equal'] = a['focused']['all_active_units'] == b['focused']['all_active_units']
    if 'eligibility' in a and 'eligibility' in b:
        result['sampled_task_fields_equal'] = a['eligibility']['task_fields_sha256'] == b['eligibility']['task_fields_sha256']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare-before', type=Path)
    parser.add_argument('--compare-after', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'checkpoint-coverage-audit.json')
    args = parser.parse_args()
    if bool(args.compare_before) != bool(args.compare_after):
        parser.error('Both comparison inputs are required')
    if args.compare_before:
        report = compare_records(load(args.compare_before), load(args.compare_after))
        report['input_sha256'] = [sha(args.compare_before), sha(args.compare_after)]
    else:
        inventory = load(ROOT/'native-checkpoint-inventory.json')
        economy = load(ROOT/'economy-extended-after-restoration.json')
        before_path = ROOT/'startup-switch-traces/20261006-124754-542123/before.json'
        after_path = ROOT/'startup-switch-traces/20261006-124754-542123/after.json'
        before, after = load(before_path), load(after_path)
        counter = Counter(key.split(':')[0] for key in before['records'])
        catalogue = {
            'CCityData': {'existing': '52 slots +10..D0 in pilot; +10..168 in economy_reader',
                'readers': ['battle_observer.py', 'economy_reader.py', 'proposal_state_reader.py'],
                'gap': 'A0/A4 economic preview identity-sensitive; +158 is a reconstructed display pointer; other runtime fields not fully classified'},
            'CForceData': {'existing': '52 slots +10..40 in pilot; +10..1D0 in economy_reader',
                'readers': ['economy_reader.py', 'human_control_reader.py'],
                'gap': 'Extended raw payload has no full serializer-field or pointer-ownership classification'},
            'CDistrictData': {'existing': '52 slots +10..28 in pilot; economy records only districts linked by cities',
                'readers': ['battle_observer.py', 'economy_reader.py', 'human_control_reader.py'],
                'gap': 'Need native active district list order plus all-slot bytes; do not equate sorted IDs with native iteration'},
            'CHexData': {'existing': f"{len(economy['center_hexes'])} center slots +10..20, out of 48400",
                'readers': ['economy_reader.py'],
                'gap': 'Most map cells completely absent. checkpoint-coverage-hex.py prepares all-slot direct serialized field sampling'},
            'CAreaData': {'existing': f"{len(economy['areas'])} slots +10..98; native ordered list has {len(economy['native_area_order'])} members",
                'readers': ['economy_reader.py'],
                'gap': 'Derived +4A/+4C/+4E/+50 may change in economic queries; must compare at same stage/shared rules, not ignore'},
            'CObjectData': {'existing': '52 city links only, resolved object+14 endurance',
                'readers': ['proposal_state_reader.py'],
                'gap': 'All 3001 slot contents, non-city objects and other serialized fields not sampled'},
            'CPersonData': {'existing': f"{counter['person']} active/valid persons +10..198; {len(economy['assigned_officers'])} assigned officers +10..200",
                'readers': ['battle_observer.py', 'reward_eligibility.py', 'economy_reader.py'],
                'gap': '1651 physical slots serialized at root+737C0; semantic ID map root+148 is rebuilt and special IDs differ from physical slot; inactive/dead/new officers not fully covered'},
            'CArmyUnitData': {'existing': f"{counter['army']} active army payloads +10..200; BattleObserver reads whole 501-slot raw allocation but exports only selected active fields",
                'readers': ['battle_observer.py', 'troops_reader.py'],
                'gap': 'Need all 501 slots and active-order list; omission of inactive slots can miss stale lifecycle data. Only +148..150 is an audited display-pointer exception'},
            'CProposalData': {'existing': '31 slots raw00..30 and payload10..30, tagged with current viewer',
                'readers': ['proposal_state_reader.py'],
                'gap': 'Proposal ownership, generation and hidden backing dependencies not proved; may not silently exclude gameplay proposals as local UI'},
            'CTroopsData': {'existing': '501 slot-derived group ownership/membership; raw body not exported',
                'readers': ['troops_reader.py'],
                'gap': 'Serialized scalar +10..30 and nested +30 object remain outside reader; +30 is not automatically disposable display state'},
        }
        tables = []
        for table in inventory['arrays']:
            representative = table['representatives'][0]
            same_types = {x['type'] for x in table['representatives']}
            assert len(same_types) == 1
            name = representative['type']
            covered = catalogue.get(name)
            tables.append({'root_offset': table['root_offset'], 'count': table['count'],
                           'type': name, 'serializer_rva': representative['serializer_rva'],
                           'sampled_serializer_status_only': representative['status_only'],
                           'existing_reader_coverage': covered,
                           'next_required': ('shared rule/data payload source fingerprint; EXE hash alone insufficient'
                               if representative['status_only'] else 'full serialized field and referenced-child coverage')})
        assert len(tables) == 39 and sum(t['count'] for t in tables) == 60070
        assert len(catalogue) == 10 and sum(t['existing_reader_coverage'] is not None for t in tables) == 10
        trace_path = ROOT/'startup-switch-traces/20261006-124754-542123/trace.jsonl'
        trace = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines()]
        boundary = next(row for row in trace if row['event'] == 'checkpoint_sample_comparison')
        assert boundary['stage'] == 'title_selection_boundary' and boundary['different_records'] == 0
        report = {'schema': 'san14.checkpoint-coverage-audit.v1',
            'created': datetime.now().astimezone().isoformat(), 'game_access': False,
            'tables': tables,
            'summary': {'fixed_tables': 39, 'fixed_table_slots': 60070,
                'tables_touched_by_existing_readers': 10, 'payload_tables_not_touched': sum(
                    not t['sampled_serializer_status_only'] and not t['existing_reader_coverage'] for t in tables),
                'status_only_table_samples': 17, 'full_world_verified': False},
            'historical_783_record_lengths': sorted({(key.split(':')[0], len(bytes.fromhex(value))) for key, value in before['records'].items()}),
            'historical_title_boundary_comparison': boundary,
            'historical_A_planning_vs_B_planning': compare_records(before, after),
            'dynamic_registry': {
                'root_offset': 0x85128, 'serialized_by': 0x1D7740,
                'existing_coverage': 'reward_eligibility follows manager+10 active task list, preserving order, 6 allowlisted types, object+58..68 and officer ID lists',
                'gap': 'Does not enumerate registry maps/factory types, all object body fields, event queues or other active lists. Unknown task type correctly rejects instead of skipping.',
                'rule': 'Compare ordered type+stable object ID+payload+referenced officer/entity IDs, not addresses or pool-allocation totals'},
            'world': {
                'root_offset': 0x85130, 'serialized_by': 0x2F9610,
                'existing_coverage': ['date+34..38', 'local force+3A', 'mode+40', 'world+450..460',
                    'world+165D..167C rank-derived fields', 'option raw+16A8', '+20A8', 'global RNG at RVA18EB8B0'],
                'gap': 'Only listed fields; CWorldData serializer and additional manager dispatch are not completely mapped. Global RNG changes during native initialization cannot be silently normalized away.',
                'identity_allowance': 'B force/ruler binding, native rank/UI derivations separately verified; menu cache1FCA518 is not authority'},
            'minimum_same_process_test_contract': {
                'verdict_name': 'SINGLE_PROCESS_NATIVE_CHECKPOINT_RELOAD_PARTIAL_COVERAGE',
                'never_claims': ['full world verified', 'two real clients connected', 'safe next-period multiplayer enabled'],
                'stages': [
                    'A settled PLANNING_BOUNDARY: stop new commands; record date/cut/save hash and baseline; do not compare arbitrary later runtime states',
                    'B deserialize/title boundary before identity initializer: compare to reference from the SAME load stage and SAME authoritative file. Retain world payload, ordered memberships, dynamic task fields and all known serialized bytes.',
                    'B identity handoff: native selected force/ruler pair2/952 before initialization; never overwrite broad common-world memory to mask differences',
                    'B first stable planning state: force2/ruler952 and user state objects present; common business bytes must match or be specifically classified. Nine city A0/A4 changes remain an explicit rule-adaptation failure, not an allowed ignore range.',
                    'Repeat same snapshot with B binding at a matched stage, without time advancement, to look for duplicate tasks/proposals/settlement; compare membership and counters, not only object intersections',
                ],
                'allowed_local_reconstruction': ['Native UI/state object addresses', 'army+148 display pointer', 'city+158 display pointer, with audited native lifecycle and no borrowed A address', 'B local force/ruler and independently validated rank/UI identity derivatives'],
                'must_not_normalize': ['unknown bytes/padding without evidence', 'cityA0/A4 forecast values', 'area4A..50 query-derived values', 'RNG, tasks, proposal actions or event outcomes', 'CTroops+30 nested payload merely because it starts with a pointer'],
                'failure_rules': ['missing or extra records compared explicitly', 'unknown type/field difference blocks a claimed match', 'same-stage baseline required', 'stable repeated read is not an atomic snapshot', 'restore/verify slot34 after the bounded experiment'],
            },
            'prioritized_scans': [
                'All 48400 CHexData direct stream fields (+14 one byte, +16 two bytes, +18/+19 one byte each), including unowned/inactive cells',
                'All physical1651 persons and501 army slots plus ID map and native ordered memberships; city/force/district expanded bodies',
                'All3001 CObjectData payloads and501 CTroopsData scalar+nested payload; 31 proposals with ownership/regen checks',
                'Remaining12 payload-table families and17 status-only rule-table families; dynamic registry and World/full manager field mapping',
            ],
            'input_sha256': {str(path.relative_to(ROOT)): sha(path) for path in (
                ROOT/'native-checkpoint-inventory.json', ROOT/'economy-extended-after-restoration.json', before_path, after_path, trace_path)},
        }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = report['summary'] if 'summary' in report else {k: report[k] for k in ('matched_existing_partial_record_contract', 'full_world_verified')}
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
