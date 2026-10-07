"""Read-only local identity/cache diagnostics, not a bootstrap execution adapter.

Matching these sampled fields does not certify native menus, proposal ownership,
AI exclusion, synchronized world state or a safe point for changing identity.
The historical cache keys below are compatibility diagnostics: RVA 0x1FCA518
also has UI-selected-force writers. It is not a permanent identity binding.
"""
import argparse
import json
from pathlib import Path
import struct
from game_reader import GameReader


def capture_startup_context(reader):
    memory = reader.memory
    before = reader.snapshot()
    root = reader.pointer(memory.base+0x1FCA1E0)
    world = reader.pointer(root+0x85130)
    reader.require_type(world, 'CWorldData')
    u32 = lambda at: struct.unpack('<I', memory.read(at, 4))[0]
    world_fields = memory.read(world+0x165D, 31)
    result = {'schema': 'san14.startup-context-sample.v1', 'snapshot': before,
              'world_mode': u32(world+0x40), 'world_field_454': u32(world+0x454),
              'world_field_20a8': u32(world+0x20A8),
              'world_rank_derived_count': world_fields[0],
              'world_rank_arrays_hex': world_fields[1:].hex(),
              'cached_player_force_id': u32(memory.base+0x1FCA518),
              'global_rng': u32(memory.base+0x18EB8B0),
              'state_sample': None, 'native_gameplay_enabled': False,
              'scope': 'Current local player, one cached force ID, rank-derived arrays and active user-state fields only. No menu/AI/proposal correctness proof.'}
    states = reader.state_objects()
    if states[-1][0] == 'CUserStrategyState':
        state = states[-1][1]
        reader.require_type(state, 'CUserStrategyState')
        result['state_sample'] = {
            'phase_raw': u32(state+0x470),
            'ui_478_present': bool(int.from_bytes(memory.read(state+0x478, 8), 'little')),
            'panel_618_present': bool(int.from_bytes(memory.read(state+0x618, 8), 'little')),
            'copied_rank_slots_hex': memory.read(state+0x480, 40).hex(),
        }
    result['local_cached_force_matches'] = result['cached_player_force_id'] == before['player']['force_id']
    result['force_context_id'] = result['cached_player_force_id']
    result['force_context_semantics'] = ('UI force context with multiple native writers; historical cached_player_force_id '
                                       'and local_cached_force_matches keys are diagnostic aliases, never authorization or readiness.')
    if before != reader.snapshot() or states != reader.state_objects() or memory.read(world+0x165D,31) != world_fields:
        raise RuntimeError('Startup sample changed during observation')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    reader = GameReader()
    try:
        result = capture_startup_context(reader)
        if result != capture_startup_context(reader):
            raise RuntimeError('Startup sample is not stable')
        raw = json.dumps(result, ensure_ascii=False, indent=2)+'\n'
        if args.output:
            args.output.write_text(raw, encoding='utf-8')
        print(raw)
    finally:
        reader.close()


if __name__ == '__main__':
    main()
