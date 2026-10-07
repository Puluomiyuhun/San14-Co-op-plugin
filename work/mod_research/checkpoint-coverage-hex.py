"""Audited map-field coverage extension. Offline audit by default.

--capture is a read-only diagnostic for a future settled-map checkpoint test.
No debugger, thread suspension, native calls, writes or load operations.
Even a successful capture is partial coverage, never a full-world verdict.
"""
from datetime import datetime
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parents[1]/'outputs'/'san14-link'
IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
EXE_SHA = '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025'
COUNT = 48400
TABLE = 0xDFE0
FIELDS = [(0x14, 1), (0x16, 2), (0x18, 1), (0x19, 1)]
PLANNING = ['CRootState', 'CMotorGameState', 'CGameState', 'CStrategyState', 'CUserStrategyState']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def audit():
    sys.path.insert(0, str(ROOT/'python_deps'))
    from capstone import Cs, CS_ARCH_X86, CS_MODE_64
    image = (ROOT/'game-runtime-image.bin').read_bytes()
    require(hashlib.sha256(image).hexdigest() == IMAGE_SHA, 'Unknown captured image')
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    expected = {
        0x215594:'mov rdi, rcx',
        0x21559D:'mov r8d, 1', 0x2155A8:'lea rdx, [rcx + 0x14]',
        0x2155B5:'call 0x3a9330', 0x2155BC:'call 0x3a93e0',
        0x2155E0:'lea rdx, [rdi + 0x16]', 0x2155E4:'mov r8d, 2',
        0x2155EF:'call 0x3a9330', 0x2155F6:'call 0x3a93e0',
        0x215616:'mov r8d, 1', 0x21561C:'lea rdx, [rdi + 0x18]',
        0x215629:'call 0x3a9330', 0x215630:'call 0x3a93e0',
        0x21563A:'add rdi, 0x19',
        0x215658:'mov r8d, 1', 0x21565E:'mov rdx, rdi',
        0x21566A:'call 0x3a9330', 0x215682:'call 0x3a93e0',
    }
    anchors = []
    for at, wanted in expected.items():
        instruction = next(decoder.disasm(image[at:at+15], at))
        require(instruction.mnemonic+' '+instruction.op_str == wanted, f'Anchor changed at {at:x}')
        anchors.append({'rva': at, 'instruction': wanted, 'bytes': instruction.bytes.hex()})
    return {'schema': 'san14.checkpoint-hex-field-contract.v1', 'captured_image_sha256': IMAGE_SHA,
            'serializer_rva': 0x215580, 'table_root_offset': TABLE, 'slot_count': COUNT,
            'field_ranges': [{'offset': at, 'length': size} for at, size in FIELDS],
            'payload_bytes_per_slot': 5, 'payload_bytes_all_slots': COUNT*5, 'anchors': anchors,
            'interpretation': 'Direct object-address buffer arguments in the ordinary archive+8C==0 path. Field meaning beyond existing ownership+14 is not guessed.',
            'all_related_hex_state_proven': False, 'game_access': False}


def extract(raw, stride, count, expected_vtable):
    require(type(stride) is int and 0x20 <= stride <= 0x1000 and stride % 8 == 0, 'Unsupported slot extent')
    require(type(count) is int and 1 <= count <= COUNT, 'Bad slot count')
    require(len(raw) == stride*count and len(expected_vtable) == 8, 'Bad raw allocation extent')
    packed = bytearray()
    for slot in range(count):
        start = slot*stride
        require(raw[start:start+8] == expected_vtable, 'Heterogeneous/corrupt hex type')
        for offset, length in FIELDS:
            packed.extend(raw[start+offset:start+offset+length])
    require(len(packed) == count*5, 'Payload count mismatch')
    return bytes(packed)


def capture(reader, contract):
    require(reader.sha256 == EXE_SHA, 'Unsupported game executable')
    m = reader.memory
    snapshot = reader.snapshot()
    require(snapshot['state_stack'] == PLANNING, 'Requires an idle planning map; not a load worker')
    require(snapshot['date']['day'] in (1, 11, 21), 'Not a ten-day planning boundary')
    states = reader.state_objects()
    require([name for name, _ in states] == PLANNING, 'Planning state stack changed')
    user_state = states[-1][1]
    reader.require_type(user_state, 'CUserStrategyState')
    user_phase = m.read(user_state+0x470, 4)
    require(user_phase == struct.pack('<I', 2), 'Player menus not yet at verified phase2')
    # Presence only: these are local UI object addresses, not shared data.
    reader.pointer(user_state+0x478)
    reader.pointer(user_state+0x618)
    for anchor in contract['anchors']:
        wanted = bytes.fromhex(anchor['bytes'])
        require(m.read(m.base+anchor['rva'], len(wanted)) == wanted, 'Live serializer anchor changed')
    root = reader.pointer(m.base+0x1FCA1E0)
    reader.require_type(root, 'CSan14Data')
    table = m.read(root+TABLE, COUNT*8)
    pointers = struct.unpack('<'+str(COUNT)+'Q', table)
    first, second = pointers[:2]
    stride = second-first
    require(0x20 <= stride <= 0x1000 and stride % 8 == 0, 'Unknown contiguous hex slot extent')
    require(all(p == first+i*stride and 0x10000 <= p < 0x7FFFFFFFFFFF for i, p in enumerate(pointers)), 'Noncontiguous/invalid hex table')
    reader.require_type(first, 'CHexData')
    vtable = m.read(first, 8)
    method = struct.unpack('<Q', m.read(struct.unpack('<Q', vtable)[0]+0x28, 8))[0]
    require(method == m.base+contract['serializer_rva'], 'Wrong hex serializer')
    raw = m.read(first, COUNT*stride)
    packed = extract(raw, stride, COUNT, vtable)
    # Repeat whole buffers, not just date/pointer headers. Still not atomic.
    require(raw == m.read(first, len(raw)), 'Hex allocation changed during sample')
    require(table == m.read(root+TABLE, len(table)), 'Hex table changed during sample')
    require(root == reader.pointer(m.base+0x1FCA1E0) and snapshot == reader.snapshot(), 'Game context changed')
    require(states == reader.state_objects() and user_phase == m.read(user_state+0x470, 4), 'Player planning state changed')
    tagged = b'san14.hex.stream-fields.v1\0'+struct.pack('<II', TABLE, COUNT)+packed
    return {'schema': 'san14.checkpoint-hex-payload-sample.v1', 'created': datetime.now().astimezone().isoformat(),
            'context': snapshot, 'table_root_offset': TABLE, 'slot_count': COUNT, 'observed_slot_extent': stride,
            'field_ranges': contract['field_ranges'], 'ordered_payload_hex': packed.hex(),
            'ordered_payload_sha256': hashlib.sha256(tagged).hexdigest(),
            'all_slot_payload_bytes': len(packed), 'identity_or_pointer_fields_normalized': False,
            'sample_consistency': 'Same complete table/raw allocation read twice; no process suspension; not atomic',
            'native_save_roundtrip_verified': False, 'full_world_verified': False,
            'game_memory_writes': 0, 'native_calls': 0, 'debugger_attached': False}


def selfcheck():
    vt = struct.pack('<Q', 0x10000)
    raw = bytearray(0x20*3)
    for i in range(3):
        raw[i*0x20:i*0x20+8] = vt
        for o, n in FIELDS:
            raw[i*0x20+o:i*0x20+o+n] = bytes([i+o])*n
    got = extract(raw, 0x20, 3, vt)
    require(len(got) == 15, 'Synthetic extraction count')
    # A noncenter cell mutation must affect the digest, without dropping slot0.
    other = bytearray(raw); other[2*0x20+0x19] ^= 1
    require(extract(other, 0x20, 3, vt) != got, 'Last cell mutation missed')
    other = bytearray(raw); other[0x20] ^= 1
    try:
        extract(other, 0x20, 3, vt)
    except ValueError:
        pass
    else:
        raise AssertionError('Wrong vtable did not fail')
    return {'pure_extraction': 'PASS', 'last_slot_mutation': 'DETECTED', 'wrong_vtable': 'REJECTED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    contract = audit()
    contract['synthetic_guard_checks'] = selfcheck()
    if args.capture:
        require(args.output is not None and not args.output.exists(), 'Capture requires a fresh --output path')
        sys.path.insert(0, str(OUT))
        from game_reader import GameReader
        reader = GameReader()
        try:
            result = capture(reader, contract)
        finally:
            reader.close()
    else:
        result = contract
    path = args.output or ROOT/'checkpoint-coverage-hex-contract.json'
    with path.open('x' if args.capture else 'w', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('anchors', 'ordered_payload_hex')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
