"""Build-locked read-only mirror of native CTroopsData district getter.

Preserves native active-list order and both exclusion paths (0x210D40).
No game calls, hooks, writes, AI suppression or date advancement.
"""
import argparse
import json
from pathlib import Path
from domestic_reader import DomesticDecoder
from battle_observer import BattleObserver
from authority_reward import PLANNING_STACK
from reward_eligibility import pool_values


def person_valid(row):
    return row['slot'] != 0 and (5001 <= row['id'] <= 5100 or row['rank'] != 0)


def army_valid(model, identity):
    if identity is None:
        return False
    row = model['armies'][identity]
    return identity != 0 and row['flag'] != 0 and row['leader'] != 0


def leader_district(model, identity):
    leader = model['armies'][identity]['leader']
    person = model['persons'][leader if leader <= 6000 else 0]
    return person['district'] if person_valid(person) else 0


def army_force(model, identity):
    district = leader_district(model, identity)
    row = model['districts'][district if district <= 51 else 0]
    valid = row['id'] != 0 and row['force'] != 0 and row['kind'] != 0 and row['leader'] != 0
    return row['force'] if valid else 0


def excluded_armies(model):
    # Native 0x210D40: explicit pointer membership, followed by relation rows.
    excluded = set(model['excluded'])
    for first, second, third in model['relations']:
        if army_valid(model, second) and army_valid(model, third):
            force = army_force(model, third)
            if force != 51 and not 46 <= force <= 50:
                excluded.add(third)
        if army_valid(model, first):
            excluded.add(first)
    return excluded


def resolve_groups(model):
    excluded = excluded_armies(model)
    members = {i: [] for i in range(501)}
    for identity in model['order']:
        group = model['armies'][identity]['group']
        if 1 <= group <= 500 and identity not in excluded:
            members[group].append(identity)
    result = []
    for identity in range(501):
        first = members[identity][0] if members[identity] else None
        # Do NOT skip an invalid leader to find another member: native returns 0.
        district = leader_district(model, first) if first is not None else 0
        force = army_force(model, first) if first is not None else 0
        result.append({'id': identity, 'member_ids': members[identity], 'first_member_id': first,
                       'district_id': district, 'force_id': force,
                       'owner_resolved': 1 <= district <= 51 and 1 <= force <= 51})
    return result


def capture_model(reader):
    before = reader.snapshot()
    if before['state_stack'] != PLANNING_STACK:
        raise RuntimeError('编组研究读取要求停在可下令大地图')
    d = DomesticDecoder(reader)
    base, root = d.memory.base, d.root
    targets = {0x129FC08: 0x2F63E0, 0x123E2A0: 0x211420,
               0x12A00E8: 0x2119F0, 0x129FEE0: 0x211610}
    for slot, target in targets.items():
        if d.ptr(base + slot) != base + target:
            raise RuntimeError('编组读取的虚函数目标已改变')
    army_zero = d.ptr(root + 0x7DF60)
    group_zero = d.ptr(root + 0x7F000)
    person_zero = d.ptr(root + 0x737C0)
    district_zero = d.ptr(root + 0xDE40)
    model = {'armies': [], 'persons': {}, 'districts': [], 'order': [], 'excluded': [], 'relations': []}
    for identity in range(501):
        army = d.ptr(root + 0x7DF60 + identity * 8)
        group = d.ptr(root + 0x7F000 + identity * 8)
        if army != army_zero + identity * 0x200 or group != group_zero + identity * 0x40:
            raise RuntimeError('编组/部队对象表排列不匹配')
        d.require_type(army, 'CArmyUnitData')
        d.require_type(group, 'CTroopsData')
        raw = d.read(army + 0x10, 0x4A)
        model['armies'].append({'id': identity, 'flag': raw[0],
                                'leader': int.from_bytes(raw[2:4], 'little'),
                                'group': int.from_bytes(raw[0x48:0x4A], 'little')})
    for identity in {0} | {min(row['leader'], 6001) for row in model['armies']}:
        if identity > 6000:
            continue
        person = d.ptr(root + 0x148 + identity * 8)
        distance = person - person_zero
        # Special officer IDs are not their physical array indices.
        if distance < 0 or distance % 0x200 or (distance == 0) != (identity == 0):
            raise RuntimeError('武将对象表排列不匹配')
        d.require_type(person, 'CPersonData')
        model['persons'][identity] = {'slot': identity, 'id': d.uint(person + 0x10, 2),
                                      'district': d.uint(person + 0x118, 1), 'rank': d.uint(person + 0x11E, 1)}
    for identity in range(52):
        district = d.ptr(root + 0xDE40 + identity * 8)
        if district != district_zero + identity * 0x28:
            raise RuntimeError('军团对象表排列不匹配')
        d.require_type(district, 'CDistrictData')
        raw = d.read(district + 0x10, 4)
        model['districts'].append({'id': identity, 'force': raw[0], 'kind': raw[1],
                                   'leader': int.from_bytes(raw[2:4], 'little')})

    def unit_id(pointer, nullable=False):
        if pointer == 0 and nullable:
            return None
        offset = pointer - army_zero
        if offset < 0 or offset % 0x200 or offset // 0x200 > 500:
            raise RuntimeError('列表包含未知部队指针')
        return offset // 0x200

    for key, offset in [('order', 0x58), ('excluded', 0x68)]:
        pointers = pool_values(d, root + offset, 0x123E200, 0x201D3A0, 0x14000, 501, 8)
        model[key] = [unit_id(p) for p in pointers]
        if len(set(model[key])) != len(model[key]):
            raise RuntimeError('部队列表重复成员')
    # Relation nodes carry three pointers; +0x30/+0x38 are next/previous.
    if d.uint(root + 0x138, 8) != base + 0x12AA618:
        raise RuntimeError('未知编组排除关系列表')
    handle = d.ptr(root + 0x140, nullable=True)
    if handle:
        pool = base + 0x1FC9760
        if not d.uint(pool + 8, 8) or d.uint(pool + 0x40) != 64:
            raise RuntimeError('编组排除关系池不匹配')
        slot = d.uint(handle)
        if slot >= 64:
            raise RuntimeError('编组排除关系句柄越界')
        count = d.uint(d.ptr(pool + 0x28) + slot * 8, 8)
        if count > 500:
            raise RuntimeError('编组排除关系过多')
        node = d.ptr(d.ptr(pool + 0x10) + slot * 8, nullable=True)
        last, seen = 0, set()
        while node:
            if node in seen or len(seen) >= count or d.uint(node + 0x38, 8) != last:
                raise RuntimeError('编组排除关系链损坏')
            seen.add(node)
            model['relations'].append([unit_id(d.uint(node + i * 8, 8), True) for i in range(3)])
            last, node = node, d.ptr(node + 0x30, nullable=True)
        if len(seen) != count or d.uint(d.ptr(pool + 0x18) + slot * 8, 8) != last:
            raise RuntimeError('编组排除关系计数不匹配')
    d.verify_stable()
    if before != reader.snapshot():
        raise RuntimeError('读取编组时游戏状态发生变化')
    return model


def capture(reader):
    model = capture_model(reader)
    groups = resolve_groups(model)
    return {'schema': 'san14.troops-ownership.v1', 'mode': 'read-only-native-getter-mirror',
            'game_sha256': reader.sha256, 'date': reader.snapshot()['date'],
            'groups': groups, 'group_slots': len(groups), 'nonempty_groups': sum(bool(g['member_ids']) for g in groups),
            'ordered_army_count': len(model['order']), 'explicit_exclusions': model['excluded'],
            'relation_count': len(model['relations']), 'excluded_armies': sorted(excluded_armies(model)),
            'applied_to_game': False, 'native_calls_in_game': 0, 'atomic_snapshot': False,
            'scope': 'Repeated stable planning sample; outer AI routing and full two-client simulation remain unverified.'}


def main():
    parser = argparse.ArgumentParser(description='只读解析编组归属；不更改AI或推进游戏。')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reader = BattleObserver()
    try:
        result = capture(reader)
    finally:
        reader.close()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'groups'}, ensure_ascii=True))


if __name__ == '__main__':
    main()
