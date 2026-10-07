"""Read-only preview of candidate human ownership at audited outer AI gates.

No hook, write, game function call, network or time advancement. Predictions
are potential wrapper routing, NOT observed AI calls or proof of movement.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from authority_reward import capture_context, PLANNING_STACK
from battle_observer import BattleObserver
from domestic_reader import DomesticDecoder
from troops_reader import capture_model, resolve_groups


def routing(route, force, district, viewer, main, humans, option_bit):
    native = bool(option_bit or (force != viewer if route == 'force' else district != main[viewer]))
    if option_bit or force not in main or (route != 'force' and not 1 <= district <= 51):
        candidate = 'HOLD'
    elif force in humans and (route == 'force' or district == main[force]):
        candidate = 'BYPASS_HUMAN_DECISION'
    else:
        candidate = 'NATIVE'
    return {'native_outer_dispatch': native, 'candidate_policy': candidate,
            'candidate_outer_dispatch': native if candidate == 'NATIVE' else False if candidate == 'BYPASS_HUMAN_DECISION' else None}


def capture(reader, humans):
    if len(humans) != 2 or len(set(humans)) != 2 or any(type(f) is not int or not 1 <= f <= 51 for f in humans):
        raise ValueError('当前预览要求两个不同的有效势力编号')
    initial = reader.snapshot()
    if initial['state_stack'] != PLANNING_STACK:
        raise RuntimeError('请停在可下令的大地图')
    viewer = initial['player']['force_id']
    if viewer not in humans:
        raise RuntimeError('当前本机玩家必须属于本轮两个人类势力')
    contexts = [capture_context(reader, f) for f in humans]
    if contexts[0]['districts'] != contexts[1]['districts'] or contexts[0]['persons'] != contexts[1]['persons']:
        raise RuntimeError('跨势力采样期间状态变化')
    districts = contexts[0]['districts']
    people = {p['id']: p for p in contexts[0]['persons']}
    d = DomesticDecoder(reader)
    world = d.ptr(d.root + 0x85130)
    raw_option = d.uint(world + 0x16a8)
    flag = bool((raw_option >> 8) & 1)
    main = {}
    forces = []
    for force in sorted({row['force_id'] for row in districts if row['valid']}):
        obj = d.ptr(d.root + 0xdca0 + force * 8)
        d.require_type(obj, 'CForceData')
        ruler = d.uint(obj + 0x10, 2)
        ruler_person = people.get(ruler)
        # Force 51 in this save has a listed district but ruler ID zero.
        # Native main-district lookup still admits its kind-1 district.
        # Preserve non-human routing; never promote it to a selectable player.
        if force in humans and (ruler_person is None or not ruler_person['native_valid']):
            raise RuntimeError('人类势力没有有效君主')
        # Same ordered-list selection as native 0x20C110, not district ID order.
        found = next((row for row in districts if row['force_id'] == force and
                      (row['leader_id'] == ruler or row['kind_raw'] == 1)), None)
        if found is None or not found['valid']:
            raise RuntimeError('无法验证主军团')
        main[force] = found['id']
        forces.append({'force_id': force, 'ruler_id': ruler,
                       'ruler_name': ruler_person['name'] if ruler_person else f'未设君主（势力{force}）',
                       'main_district_id': found['id'], 'human': force in humans})
    for c in contexts:
        if main.get(c['command_force_id']) != c['main_district_id']:
            raise RuntimeError('主军团解析不一致')
    if len(set(main[f] for f in humans)) != 2:
        raise RuntimeError('人类势力主军团发生冲突')
    for row in forces:
        row.update(routing('force', row['force_id'], 0, viewer, main, humans, flag))
    district_rows = []
    for row in districts:
        if not row['valid']:
            continue
        district_rows.append({**row, 'is_main': row['id'] == main[row['force_id']],
                              **routing('district', row['force_id'], row['id'], viewer, main, humans, flag)})
    district_ids = {row['id']: row for row in district_rows}
    focused = reader.capture()
    army_rows = []
    for unit in focused['all_active_units']:
        person = people.get(unit['officer_id'])
        if person is None or not person['native_valid'] or person['district_id'] not in district_ids:
            raise RuntimeError('部队主将或军团归属无法验证')
        district = district_ids[person['district_id']]
        if district['force_id'] != person['force_id']:
            raise RuntimeError('主将势力与军团不符')
        army_rows.append({**unit, 'officer_name': person['name'], 'force_id': person['force_id'],
                          'district_id': person['district_id'],
                          **routing('army', person['force_id'], person['district_id'], viewer, main, humans, flag)})
    group_model = capture_model(reader)
    group_rows = []
    for group in resolve_groups(group_model):
        if not group['member_ids']:
            continue
        group_rows.append({**group, **routing('group', group['force_id'], group['district_id'],
                                             viewer, main, humans, flag)})
    ai = d.ptr(d.memory.base + 0x1a1f6c0)
    d.require_type(ai, 'CAIManager')
    ai_config = {'global_gate': d.uint(ai + 0x30), 'per_force_entry_count': d.uint(ai + 0x68, 8)}
    d.verify_stable()
    if (initial != reader.snapshot() or focused != reader.capture()
            or contexts != [capture_context(reader, f) for f in humans]
            or group_model != capture_model(reader)):
        raise RuntimeError('采样期间状态变化，请在规划界面重新读取')
    summary = {}
    for label, rows in [('forces', forces), ('districts', district_rows), ('armies', army_rows), ('army_groups', group_rows)]:
        summary[label] = {'count': len(rows), 'native_outer_dispatch': sum(r['native_outer_dispatch'] for r in rows),
                          'candidate_policy': dict(Counter(r['candidate_policy'] for r in rows)),
                          'newly_protected': [r.get('id', r.get('force_id')) for r in rows
                                              if r['native_outer_dispatch'] and r['candidate_policy'] == 'BYPASS_HUMAN_DECISION']}
    return {'schema': 'san14.human-control-preview.v2', 'mode': 'read-only-routing-preview',
            'game_sha256': reader.sha256, 'date': initial['date'], 'viewer_force_id': viewer,
            'human_forces': humans, 'world_16a8_bit8': flag, 'ai_config': ai_config,
            'forces': forces, 'districts': district_rows, 'armies': army_rows, 'army_groups': group_rows, 'summary': summary,
            'army_groups_decoded': True, 'group_slots_scanned': 501,
            'group_explicit_exclusions': group_model['excluded'], 'group_relation_count': len(group_model['relations']),
            'applied_to_game': False, 'observed_ai_calls': False,
            'movement_preservation_verified': False, 'sample_stable': True, 'atomic_snapshot': False,
            'scope': 'Potential routing at four audited outer wrappers; planning preview covers forces, districts, active armies and nonempty groups. Group getter mirrored including ordered filtering, with separate copied-native-code correlation. Full AI coverage, live transition relations, native pause and downstream movement remain unverified.'}


def main():
    parser = argparse.ArgumentParser(description='只读查看两个人类势力的候选AI控制范围，不修改游戏。')
    parser.add_argument('--forces', nargs=2, type=int, default=[12, 2])
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('双人控制范围含编组预览.json'))
    args = parser.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    reader = BattleObserver()
    try:
        result = capture(reader, args.forces)
    finally:
        reader.close()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('只读控制范围预览完成；没有关闭AI、切换玩家或推进日期。')
    for row in result['forces']:
        if row['human']:
            units = [r for r in result['armies'] if r['force_id'] == row['force_id']]
            print(f"{row['ruler_name']}：主军团{row['main_district_id']}，现存部队{len(units)}支")
    print(json.dumps(result['summary'], ensure_ascii=False))
    print(str(args.output.resolve()))


if __name__ == '__main__':
    main()
