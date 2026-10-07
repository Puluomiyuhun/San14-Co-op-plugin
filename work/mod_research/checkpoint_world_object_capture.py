"""Read all physical CObjectData slots without injecting or calling game code.

This captures one previously traced ordinary-archive table. Repeated reads
are stability observations, not an atomic checkpoint or a Ready permission.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'outputs/san14-link'))
from checkpoint_world_coverage_extension_schema import (
    GAME_SHA256, ROOT_OFFSET, SLOT_COUNT, validate_payload_records, compare_payloads)

PLAN = ['CRootState', 'CMotorGameState', 'CGameState', 'CStrategyState', 'CUserStrategyState']
VTABLE = 0x129FDF0
SERIALIZER = 0x216140


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


class Reads:
    def __init__(self, reader):
        self.reader = reader
        self.spans = {}

    def read(self, address, size):
        data = self.reader(address, size)
        if type(data) is not bytes or len(data) != size:
            raise ValueError('partial_read')
        key = (address, size)
        if key in self.spans and self.spans[key] != data:
            raise ValueError('observed_memory_changed')
        self.spans[key] = data
        return data

    def pointer(self, address):
        value, = struct.unpack('<Q', self.read(address, 8))
        if not 0x10000 <= value < 0x7fffffffffff or value % 8:
            raise ValueError('invalid_pointer')
        return value


def inspect(reads, base, root, anchors):
    for anchor in anchors:
        expected = bytes.fromhex(anchor['bytes'])
        if reads.read(base + int(anchor['rva'], 16), len(expected)) != expected:
            raise ValueError('live_serializer_profile_mismatch')
    if reads.pointer(base + VTABLE + 0x28) != base + SERIALIZER:
        raise ValueError('virtual_serializer_mismatch')
    if reads.pointer(base + 0x1FCA1E0) != root:
        raise ValueError('root_changed')
    table_address = root + ROOT_OFFSET
    table = reads.read(table_address, SLOT_COUNT * 8)
    pointers = struct.unpack('<' + 'Q' * SLOT_COUNT, table)
    if len(set(pointers)) != SLOT_COUNT:
        raise ValueError('aliased_physical_slots')
    first, second = {}, {}
    for output in (first, second):
        for index, address in enumerate(pointers):
            if not 0x10000 <= address < 0x7fffffffffff - 24 or address % 8:
                raise ValueError('invalid_object_pointer')
            raw = reads.read(address, 24)
            if struct.unpack_from('<Q', raw)[0] != base + VTABLE:
                raise ValueError('object_type_mismatch')
            output[index] = raw[0x10:0x18]
        # Identity and ordering must also survive each entire table pass.
        reads.read(table_address, SLOT_COUNT * 8)
        if reads.pointer(base + 0x1FCA1E0) != root:
            raise ValueError('root_changed')
    a = validate_payload_records(first, game_build_sha256=GAME_SHA256)
    b = validate_payload_records(second, game_build_sha256=GAME_SHA256)
    comparison = compare_payloads(a, b)
    if not comparison['all_this_table_payloads_equal']:
        raise ValueError('payload_changed')
    return a, comparison


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--capture', action='store_true')
    mode.add_argument('--replay', type=Path)
    parser.add_argument('--pid', type=int)
    args = parser.parse_args()
    folder = HERE / 'checkpoint_world_object_capture_runs' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    folder.mkdir(parents=True)
    frozen = json.loads((HERE / 'checkpoint_world_coverage_extension_handoff.json').read_text(encoding='utf-8'))
    for name, expected in frozen['source_sha256'].items():
        if sha(HERE / name) != expected:
            raise ValueError('frozen_schema_dependency_changed')
    from checkpoint_world_coverage_extension_native import audit
    anchors = audit((HERE / 'game-runtime-image.bin').read_bytes())
    reader = None
    try:
        if args.capture:
            from game_reader import GameReader
            from checkpoint_dispatch_handoff_live import birth
            reader = GameReader(args.pid)
            before = reader.snapshot()
            if before['state_stack'] != PLAN:
                raise ValueError('idle_planning_map_required')
            base = reader.memory.base
            root = reader.pointer(base + 0x1FCA1E0)
            owner_birth = birth(reader.memory.handle)
            reads = Reads(reader.memory.read)
            payload, comparison = inspect(reads, base, root, anchors)
            # The exact vtable above is checked for every slot; verify its RTTI
            # from a representative real object as an additional local check.
            reader.require_type(reader.pointer(root + ROOT_OFFSET), 'CObjectData')
            after = reader.snapshot()
            if before != after or owner_birth != birth(reader.memory.handle):
                raise ValueError('metadata_or_process_changed')
            sample = dict(base=base, root=root, process_birth=owner_birth,
                before=before, after=after, repeated_metadata_equal=True,
                reads=[[a, n, data.hex()] for (a, n), data in sorted(reads.spans.items())])
            write(folder / 'memory-transcript.json', sample)
        else:
            sample = json.loads(args.replay.read_text(encoding='utf-8'))
            if sample['before'] != sample['after'] or sample['before']['state_stack'] != PLAN:
                raise ValueError('transcript_metadata_rejected')
            memory = {(a, n):bytes.fromhex(data) for a, n, data in sample['reads']}
            if len(memory) != len(sample['reads']):
                raise ValueError('duplicate_transcript_spans')
            reads = Reads(lambda a, n:memory[(a, n)])
            payload, comparison = inspect(reads, sample['base'], sample['root'], anchors)
        (folder / 'object-payload.bin').write_bytes(payload.ordered_payload)
        result = dict(result='PASS_COMPLETE_OBJECT_TABLE', game_access=bool(args.capture),
            game_writes=0, game_function_calls=0, injected=False,
            source_transcript=str(args.replay) if args.replay else str(folder / 'memory-transcript.json'),
            current_world_provenance_verified=False, atomic_world_snapshot=False,
            full_world_verified=False, authorize_load_or_ready=False,
            date=sample['after']['date'], player=sample['after']['player'],
            physical_slots=SLOT_COUNT, payload_bytes=len(payload.ordered_payload),
            serialized_schema=payload.evidence(), repeated_table_comparison=comparison,
            profile_anchors=len(anchors), distinct_read_spans=len(reads.spans),
            allocation_stride_assumed=False, includes_slot_zero_and_inactive=True,
            source_sha256={name:sha(HERE / name) for name in (
                'checkpoint_world_object_capture.py', 'checkpoint_world_coverage_extension_schema.py',
                'checkpoint_world_coverage_extension_native.py', 'game-runtime-image.bin')},
            limits=['One ordinary serialized table, not all world state.',
                'Pointers are local capture locators; payload comparison uses physical slot index.',
                'Repeated samples can miss intervening changes and do not provide a scheduling fence.',
                'No encoded .s14 file was decoded; payload offsets are not full-file offsets.'])
        write(folder / 'result.json', result)
        print(json.dumps(dict(result=result['result'], path=str(folder / 'result.json'),
            slots=SLOT_COUNT, payload_bytes=len(payload.ordered_payload), game_access=bool(args.capture))))
    except Exception as exc:
        write(folder / 'failure.json', dict(result='REJECTED', error=repr(exc),
            game_writes=0, game_function_calls=0, injected=False, authorize_load_or_ready=False))
        raise
    finally:
        if reader:
            reader.close()


if __name__ == '__main__':
    main()
