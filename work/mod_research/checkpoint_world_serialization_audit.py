"""Bounded offline serialization audit; workspace archives and copied code only.

No GameReader, process/window APIs, Steam paths or game calls. Does not execute
legacy script drivers. World-field locations are memory offsets, NOT guessed
file offsets. This audit never returns a complete-world acceptance result.
"""
from pathlib import Path
import collections
import hashlib
import json
import re
import struct
import sys
import types

P = Path(__file__).resolve().parent
sys.path[:0] = [str(P / 'python_deps'), str(P)]
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_RDX, UC_X86_REG_R8, UC_X86_REG_RAX

IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
ARCHIVE = 'checkpoint_push_archives/20261006-204306-581930/mppush01.s14'
FORENSIC = 'private_checkpoint_exported_forensics.s14'
EXPECTED = {
    ARCHIVE: '88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c',
    FORENSIC: 'b9500d662fb4a394ce03279e8491616719d12a799b2881a67e9d2a5553c3914a',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(name):
    return json.loads((P / name).read_text(encoding='utf8'))


def native_header(raw):
    # Reviewed definitions only: the legacy driver after cases=[] writes old
    # reports, and is deliberately neither imported nor executed.
    path = P / 'private_checkpoint_load_shadow.py'
    source = path.read_text(encoding='utf8')
    assert source.count('\ncases=[]\n') == 1
    n = types.ModuleType('world_serialization_header_definitions')
    n.__file__ = str(path)
    exec(compile(source.split('\ncases=[]\n', 1)[0], str(path), 'exec'), n.__dict__)
    u = n.new()
    header, stream, source_buffer = n.MEM + 0x1000, n.MEM + 0x2000, n.MEM + 0x50000
    u.mem_map(source_buffer, 0x50000)
    u.mem_write(source_buffer, raw)
    n.execute(u, 0x2E32A0, (header,))
    u.mem_write(stream + 0x20, struct.pack('<I', 1))
    u.mem_write(stream + 0x30, n.q(source_buffer + 4) + n.q(source_buffer + len(raw)))
    u.mem_write(stream + 0x88, raw[:4])
    u.mem_write(stream + 0x8F, b'\0')
    reads, forbidden_writes = [], []

    def code(uc, address, size, context):
        if address == n.BASE + 0x3A9330:
            dest, length = uc.reg_read(UC_X86_REG_RDX), uc.reg_read(UC_X86_REG_R8)
            reads.append({'file_offset': n.u64(uc, stream + 0x30) - source_buffer,
                          'header_offset': dest - header if header <= dest < header + 0x150 else None,
                          'length': length})

    def write(uc, access, address, size, value, context):
        if n.BASE <= address < n.BASE + len(n.d.image) or source_buffer <= address < source_buffer + len(raw):
            forbidden_writes.append((address, size))

    a = u.hook_add(UC_HOOK_CODE, code)
    b = u.hook_add(UC_HOOK_MEM_WRITE, write)
    result = n.execute(u, 0x2FAAD0, (header, stream))
    u.hook_del(a)
    u.hook_del(b)
    parsed = bytes(u.mem_read(header, 0x150))
    consumed = n.u64(u, stream + 0x30) - source_buffer
    assert u.reg_read(UC_X86_REG_RAX) & 255 and n.i32(u, stream + 0x50) == 0
    assert consumed == 294 and len(reads) == 189 and not forbidden_writes
    assert bytes(u.mem_read(source_buffer, len(raw))) == raw
    return parsed, {'consumed': consumed, 'calls': len(reads), 'raw_read_mapping': reads,
                    'native_instructions': result['instructions'], 'stubs': result['stub_calls'],
                    'source_and_copied_image_unchanged': True,
                    'scope': 'Actual 2FAAD0/3A9330/memcpy on a borrowed immutable buffer in Unicorn. No open/close/Steam or world deserializer.'}


def main():
    image = (P / 'game-runtime-image.bin').read_bytes()
    assert sha(image) == IMAGE_SHA
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    anchors = []

    def anchor(at, expected):
        i = next(decoder.disasm(image[at:at + 15], at))
        text = i.mnemonic + ' ' + i.op_str
        assert text == expected, (hex(at), text, expected)
        anchors.append({'rva': hex(at), 'instruction': text, 'bytes': i.bytes.hex()})

    wanted = {
        0x2F7C28: 'call 0x2e7d30', 0x2F7959: 'call 0x2e7d30',
        0x2E7DA8: 'call 0x1d7740', 0x2E82EE: 'call qword ptr [r8 + 8]',
        0x2E835B: 'call qword ptr [rax + 0x28]',
        0x2F9A24: 'call 0x3aa390', 0x2F9A6D: 'call 0x3aa3e0',
        0x3AA390: 'mov eax, dword ptr [rip + 0x154151a]',
        0x3AA3E0: 'mov dword ptr [rip + 0x15414ca], ecx',
        0x2F97A1: 'lea rcx, [r13 + 0x34]', 0x2F97A8: 'call 0x2fa970',
        0x2FAA61: 'mov byte ptr [rdi + 3], al', 0x2FAAAD: 'mov byte ptr [rdi + 4], al',
        0x2FA3F8: 'lea rdx, [r13 + 0x3a]', 0x2FA405: 'call 0x3a9330', 0x2FA40C: 'call 0x3a93e0',
        0x2FA435: 'lea rdx, [r13 + 0x165d]', 0x2FA445: 'call 0x3a9330', 0x2FA44C: 'call 0x3a93e0',
        0x2EE647: 'call 0x2f76c0', 0x2EE69D: 'call 0x2f3410',
        0x2EE6A5: 'call 0x2eae80', 0x2EE6AA: 'call 0x2f2950',
        0x2F3B93: 'mov qword ptr [rdi + rax*8 + 0x148], rdx',
        0x207845: 'mov qword ptr [rbx + 0x148], 0',
        0x203721: 'mov qword ptr [rbx + 0x148], rax',
        0x203779: 'mov qword ptr [rbx + 0x158], rax',
        0x2E2DC5: 'call 0x3a7f50',
        0x2E2E12: 'mov word ptr [rsi + 0xc2], ax',
        0x2E2E23: 'mov word ptr [rsi + 0xc4], ax',
        0x2E2E34: 'mov word ptr [rsi + 0xc6], ax',
    }
    for at, expected in wanted.items():
        anchor(at, expected)
    assert image[0x217CF0:0x217CF9].hex() == '33c03942500f94c0c3'

    # Extract only immediate direct World-address Read/Write buffer arguments.
    # This is a partial callsite inventory, NOT a CFG proof or field semantics.
    ins = list(decoder.disasm(image[0x2F9610:0x2FA970], 0x2F9610))
    fields = collections.defaultdict(dict)
    for j, i in enumerate(ins):
        if i.mnemonic != 'call' or i.op_str not in ('0x3a9330', '0x3a93e0'):
            continue
        back = ins[max(0, j - 8):j]
        off = next((x for x in reversed(back) if x.mnemonic == 'lea' and re.fullmatch(r'rdx, \[r13 \+ 0x[0-9a-f]+\]', x.op_str)), None)
        size = next((x for x in reversed(back) if x.mnemonic == 'mov' and re.fullmatch(r'r8d, (?:[1248]|0x[0-9a-f]+)', x.op_str)), None)
        if off and size:
            key = int(off.op_str.split('0x')[1][:-1], 16), int(size.op_str.split(', ')[1], 0)
            kind = 'read_call_rva' if i.op_str == '0x3a9330' else 'write_call_rva'
            assert kind not in fields[key]
            fields[key][kind] = hex(i.address)
    direct = []
    for (offset, size), calls in sorted(fields.items()):
        assert set(calls) == {'read_call_rva', 'write_call_rva'}
        direct.append({'world_offset': hex(offset), 'length': size, **calls,
                       'meaning': 'local viewer force' if offset == 0x3A else 'local control/identity byte' if offset == 0x165D else 'opaque serialized value; semantics not inferred'})
    assert any(x['world_offset'] == '0x3a' and x['length'] == 1 for x in direct)
    assert any(x['world_offset'] == '0x165d' and x['length'] == 1 for x in direct)

    inv = read_json('native-checkpoint-inventory.json')
    tables = []
    for row in inv['arrays']:
        sample = row['representatives'][0]
        tables.append({'root_offset': hex(row['root_offset']), 'slots': row['count'],
                       'representative_type': sample['type'], 'serializer_rva': hex(sample['serializer_rva']),
                       'sampled_status_only': sample['status_only'], 'all_slot_payloads_verified': False})
    assert len(tables) == 39 and sum(x['slots'] for x in tables) == 60070

    samples = {}
    data = {}
    parsed = {}
    for name, expected in EXPECTED.items():
        raw = (P / name).read_bytes()
        assert sha(raw) == expected and len(raw) == 274880
        data[name] = raw
        header, proof = native_header(raw)
        previous = read_json('checkpoint_push_archives/20261006-204306-581930/result.json' if name == ARCHIVE else 'private_checkpoint_metadata_new_file.json')
        assert header.hex() == previous['parsed_header_hex']
        parsed[name] = header
        samples[name] = {'sha256': sha(raw), 'size': len(raw), 'format_version': struct.unpack_from('<I', raw)[0],
                         'date': {'year': struct.unpack_from('<H', header, 0xE2)[0], 'month': header[0xE4], 'day': header[0xE5]},
                         'ruler': header[0x10:0x16].decode('utf-16-le').rstrip('\0'),
                         'header_sha256': sha(header), 'native_header_proof': proof,
                         'accepted_A_export': name == ARCHIVE,
                         'role': 'passing archived A export' if name == ARCHIVE else 'forensic file from FAILED save lifecycle, comparison only; never an approved checkpoint'}
    a, b = data[ARCHIVE], data[FORENSIC]
    differences = [i for i in range(len(a)) if a[i] != b[i]]
    assert differences == [124, 126, 128] and a[294:] == b[294:]
    mapping = []
    for i in differences:
        read = next(x for x in samples[ARCHIVE]['native_header_proof']['raw_read_mapping'] if x['file_offset'] <= i < x['file_offset'] + x['length'])
        assert read['header_offset'] is not None
        mapping.append({'file_offset': i, 'parsed_metadata_offset': hex(read['header_offset'] + i - read['file_offset']), 'A_value': a[i], 'forensic_value': b[i]})
    assert [x['parsed_metadata_offset'] for x in mapping] == ['0xc2', '0xc4', '0xc6']
    sources = ['game-runtime-image.bin', 'runtime-pdata.bin', 'disasm_chained.py',
               'private_checkpoint_load_shadow.py', 'native-checkpoint-audit.json', 'native-checkpoint-inventory.json',
               'checkpoint-coverage-contract.txt', 'checkpoint-coverage-hex-contract.json',
               'checkpoint-coverage-audit.json', 'inplace-checkpoint-feasibility.json',
               'save_return_lifecycle_audit.json', 'save_return_lifecycle_shadow.json',
               'checkpoint_push_archives/20261006-204306-581930/result.json',
               'private_checkpoint_metadata_new_file.json', 'checkpoint_world_serialization_audit.py']
    report = {
        'schema': 'san14.checkpoint-world-serialization-audit.v1', 'result': 'OFFLINE_BOUNDED_EVIDENCE_VERIFIED',
        'game_access': False, 'steam_access': False, 'world_deserialization_executed': False,
        'full_world_verified': False, 'captured_image_sha256': IMAGE_SHA,
        'source_sha256': {n: sha((P / n).read_bytes()) for n in sources}, 'anchors': anchors,
        'fixed_tables': tables, 'fixed_slot_count': 60070,
        'status_only_representative_tables': sum(x['sampled_status_only'] for x in tables),
        'world_direct_buffer_fields': direct,
        'world_direct_inventory_limit': 'Only immediate World-relative scalar buffers. Version and World+44 branches remain significant. Nested helpers, arrays, dynamic containers and other serializers are not covered by this extraction; not a canonical complete digest schema.',
        'additional_proved_serialization': [
            {'object': 'CHexData', 'root_offset': '0xdfe0', 'slots': 48400, 'ranges': [[20,1],[22,2],[24,1],[25,1]], 'total_payload_bytes': 242000, 'evidence': 'checkpoint-coverage-hex-contract.json', 'limit': 'Ordinary archive+8C=0 direct fields only; not all map-related state.'},
            {'object': 'CWorldData current date', 'helper_rva': '0x2fa970', 'object_offset': '0x34', 'ranges': [[0,2],[2,1],[3,1],[4,1]], 'limit': 'Five bytes, not the entire six-byte local date storage including padding. No global file offset inferred.'},
            {'object': 'known global RNG', 'rva': '0x18eb8b0', 'length': 4, 'evidence': ['0x2f9a24 getter', '0x2f9a5d/0x2f9a64 stream read/write', '0x2f9a6d setter'], 'limit': 'Saved/restored by this serializer; not proof that all RNGs or post-initialization random consumption are covered.'},
        ],
        'reconstruction_not_copyable_addresses': [
            {'item': 'person-ID index root+148', 'evidence': '2F3410 after successful deserialization; 2F3B93 stores rebuilt person pointers', 'action': 'Compare stable IDs and records after rebuild; do not hash/copy pointer addresses.'},
            {'item': 'Army+148 display object', 'evidence': '207845 clears; 203721 assigns newly created display', 'action': 'Known local pointer exception only; unrelated army bytes remain authoritative/unknown.'},
            {'item': 'City+158 display object', 'evidence': '203779 assigns recreated display', 'action': 'Lifecycle/type check, not cross-client address equality.'},
            {'item': 'dynamic registry root+85128', 'evidence': '1D7740 serializes via virtual+28; 2F4C30 destroys and post-load reconstructs', 'action': 'Business payload is not disposable cache. Factory type, stable IDs, ordered membership and references still need full audit.'},
        ],
        'sidecars': {
            'evidence': 'save_return_lifecycle_audit.json / save_return_lifecycle_shadow.json',
            'native_files': [{'name': 'configS_SC.s14', 'version': 14, 'save_rva': '0x3a0690', 'serializer_rva': '0x3a0870'}, {'name': 'prdataN.s14', 'version': 7, 'save_rva': '0x39d500', 'serializer_rva': '0x39e060'}],
            'finding': 'Native Save worker independently attempts both sidecars regardless of main archive result and ignores their booleans. Main-save success therefore does not prove either sidecar succeeded.',
            'limits': 'Complete sidecar fields and local/shared rule classification remain unproved; do not transfer account/profile/config files wholesale or silently exclude gameplay-affecting options.',
            'adapter_json': 'Our protocol adapter.json is separate mod metadata, not either native sidecar. Existing offline prototype adapter JSON is explicitly synthetic.',
        },
        'sample_comparison': {'samples': samples, 'different_bytes': mapping, 'opaque_after_header_equal': True,
                              'opaque_equal_range': [294, len(a)], 'opaque_equal_bytes': len(a)-294,
                              'opaque_body_sha256': sha(a[294:]),
                              'interpretation': 'Different whole-file SHA does not imply different serialized body. Clock-derived header fields differ here, but no arbitrary header masking or semantic world equivalence is authorized. Equal opaque body is not a completed load or stable-world proof.'},
        'do_not_silently_normalize': ['World+3A and +165D are serialized and deliberately rebound for B; must be separately accounted for, not treated as unsaved UI.', 'City+A0/A4 economic differences after B initialization are real observed differences; no blanket viewpoint exemption.', 'World RNG, task/event/proposal state and unknown bytes.', 'CTroopsData+30 referenced object: serialization can construct/serialize it; pointer appearance does not make it cosmetic.'],
        'practical_next': ['Use this direct-field inventory plus exact hex schema to expand read-only diagnostics while keeping full_world_verified=false.', 'Build exhaustive physical-slot coverage, not only the 783 active semantic records; audit all dynamic registry types and non-World manager virtual+8 serializer.', 'Pin external rules/assets/build because 17 table representative methods only return stream status and serialize no payload.', 'For a future canonical serialized-world digest, first classify every nested serializer and explicit B identity change, then compare the same lifecycle stage. Whole file SHA remains transport identity only.'],
    }
    (P / 'checkpoint_world_serialization_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'result': report['result'], 'anchors': len(anchors), 'world_direct_fields': len(direct), 'headers_replayed': len(samples), 'opaque_body_equal_bytes': len(a)-294, 'full_world_verified': False}))


if __name__ == '__main__':
    main()
