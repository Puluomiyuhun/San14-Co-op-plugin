"""Offline-only feasibility audit of native checkpoint restore versus raw copies.

Does not open a game process, invoke native functions, or make timing claims.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'python_deps'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
image = (HERE / 'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest() == IMAGE_SHA
decoder = Cs(CS_ARCH_X86, CS_MODE_64)

# Exact callsites, not function-name guesses or arbitrary byte-pattern matches.
expected = {
    0x2EE4EC: 'call 0x2f4c30',
    0x2EE4F8: 'call 0x2f7c90',
    0x2EE647: 'call 0x2f76c0',
    0x2EE698: 'xor r8d, r8d',
    0x2EE69B: 'xor edx, edx',
    0x2EE69D: 'call 0x2f3410',
    0x2EE6A5: 'call 0x2eae80',
    0x2EE6AA: 'call 0x2f2950',
    0x2F4C67: 'call 0x1c63c0',
    0x2F4C74: 'call 0xef97b4',
    0x2F4C79: 'mov qword ptr [rbx + 0x85128], r15',
    0x2F4CD3: 'call 0x207820',
    0x207840: 'call 0x1b2ae0',
    0x207845: 'mov qword ptr [rbx + 0x148], 0',
    0x2F5432: 'rep stosb byte ptr [rdi], al',
    0x2F54A5: 'call 0x3a5820',
    0x2F54B7: 'call 0x1c6020',
    0x2F54BF: 'mov qword ptr [rbx + 0x85128], r15',
    0x2F7959: 'call 0x2e7d30',
    0x2F7967: 'mov dword ptr [rbx + 0x24], 0xfffffda8',
    0x2E7D99: 'mov rcx, qword ptr [rax + 0x85128]',
    0x2E7DA8: 'call 0x1d7740',
    0x1D78CF: 'call 0x1d59b0',
    0x1D78E0: 'call qword ptr [rax + 0x28]',
    0x1D78F9: 'call 0x1c20e0',
    0x1D7911: 'call 0x1c2850',
    0x1D794A: 'call 0x172d0',
    0x1D7AD0: 'call 0x1d59b0',
    0x1D59E7: 'call 0x3a5820',
    0x1D59F9: 'call 0x1c6100',
    0x2E0D80: 'mov rcx, qword ptr [rdi]',
    0x2E0D89: 'call qword ptr [rax + 0x28]',
    0x2E3E6F: 'jmp qword ptr [rax + 0x20]',
    0x2E3E77: 'jmp qword ptr [rax + 0x38]',
    0x2F3B93: 'mov qword ptr [rdi + rax*8 + 0x148], rdx',
    0x2F3AD6: 'call 0x2e61d0',
    0x2F3B06: 'call 0x2e6270',
    0x2E629A: 'movzx edx, byte ptr [rbx + 0x11e]',
    0x2EB579: 'call 0x1d1750',
    0x2EB588: 'call qword ptr [rax + 0x38]',
    0x2F29BA: 'call 0x203700',
    0x20371C: 'call 0x1b0980',
    0x203721: 'mov qword ptr [rbx + 0x148], rax',
    0x2F2A6B: 'call 0x203730',
    0x203779: 'mov qword ptr [rbx + 0x158], rax',
    0x4DA3B9: 'call 0x2fc850',
}
anchors = []
for at, wanted in expected.items():
    instruction = next(decoder.disasm(image[at:at+15], at))
    actual = instruction.mnemonic + ' ' + instruction.op_str
    assert actual == wanted, (hex(at), actual, wanted)
    anchors.append({'rva': hex(at), 'instruction': actual, 'bytes': instruction.bytes.hex()})

inventory = json.loads((HERE / 'native-checkpoint-inventory.json').read_text('utf-8'))
assert inventory['complete_world_verified'] is False
tables = [{
    'root_offset': hex(a['root_offset']), 'capacity': a['count'],
    'representative_type': a['representatives'][0]['type'],
    'serializer': hex(a['representatives'][0]['serializer_rva']),
    'payload_status_only': a['representatives'][0]['status_only'],
} for a in inventory['arrays']]

report = {
    'schema': 'san14.inplace-checkpoint-feasibility.v1',
    'result': 'STATIC_NATIVE_RECONSTRUCTION_DEPENDENCIES_IDENTIFIED',
    'captured_image_sha256': IMAGE_SHA,
    'game_memory_reads': 0, 'game_memory_writes': 0,
    'game_calls': 0, 'debugger_attached': False,
    'anchors_verified': len(anchors), 'anchors': anchors,
    'native_tables': tables,
    'findings': [
        {
            'claim': 'Fixed record tables are traversed through existing local pointers at dispatcher level.',
            'evidence': ['2E7D30 fixed arrays', '2E0D80/2E0D89 existing record + virtual serializer'],
            'limits': 'This does not certify no allocations inside each serializer, all record coverage, or a supported live in-place API.',
        },
        {
            'claim': 'Dynamic objects must be destroyed/created and re-registered; raw field replacement is insufficient.',
            'evidence': ['2F4C67 destructor, 2F4C74 free, 2F54B7 constructor',
                         '1D78CF/1D7AD0 factory, 1D59E7 allocation, 1D59F9 constructor',
                         '1D78F9/1D7911 map insertion, 1D794A active-list insertion'],
            'limits': 'Concrete dynamic object class-to-event/task mapping is not fully audited.',
        },
        {
            'claim': 'Loading includes rebuilding indexes and active membership, not only serialized bytes.',
            'evidence': ['2F5432 clears root index region', '2F3B93 rebuilds person ID index',
                         '2F3AD6 rebuilds object list', '2F3B06 filters person status +11E for membership',
                         '2EAE80 dispatches virtual +38 and 2EB579 registry postpass'],
            'limits': 'Not every virtual +20/+38 implementation and secondary effect has been audited.',
        },
        {
            'claim': 'Transient rendered objects have local lifetimes separate from business records.',
            'evidence': ['207840 removes army display; 207845 clears Army+148',
                         '20371C rebuilds display; 203721 assigns Army+148',
                         '203779 assigns city+158', 'startup-switch-live-result.json records army +148 pointer changes'],
            'limits': 'Memory addresses cannot be copied between clients or blindly kept when an object changes existence.',
        },
        {
            'claim': 'Passing a temporary root into the deserializer is not an isolated staging implementation.',
            'evidence': ['2E7D92/2E7E02 and repeated global CSan14Data accesses in 2E7D30'],
            'limits': 'A sandbox/shadow interpreter or fully redirected globals would require separate engineering.',
        },
        {
            'claim': 'Native load has destructive steps before success; validation and a recovery checkpoint must precede it.',
            'evidence': ['2EE4EC cleanup before 2EE647 deserialize', '2F7967 can set an error after 2F7959 already traversed objects'],
            'limits': 'File hashes catch transfer corruption; they do not make native load transactional or guarantee semantic validity.',
        },
        {
            'claim': 'B identity must be rebound in the correct initialization stage after A state loads.',
            'evidence': ['4DA3B9 -> 2FC850', 'startup-switch-menu-result.json', 'economy-shadow-adapted.json'],
            'limits': 'Single-load basic menu success is not proof of repeated period reloads, all events, or unchanged economic rules without adaptation.',
        },
    ],
    'routes': [
        {'route': 'controlled_native_reload', 'first_version': True,
         'status': 'native constituent paths observed/audited, complete automatic loop unimplemented',
         'experience': 'Automatic synchronization overlay and brief pause; no manual slot picking intended. Underlying state restore is load-like.',
         'required': ['quiescent planning barrier', 'fully received/verified checkpoint before mutating B',
                      'native cleanup/deserialize/reconstruction in proper thread and state context',
                      'B identity and rule policy rebind', 'semantic world verification before reopening input',
                      'local camera/view restoration by values, never old object pointers'],
         'latency': 'not measured'},
        {'route': 'shortened_native_restore', 'first_version': False,
         'status': 'research candidate only',
         'experience': 'Could hide menus/title transition and reuse static assets, while retaining necessary reconstruction.',
         'required': ['profile controlled native reload first', 'audit UI/state exit-entry and thread/render barriers',
                      'prove removed work is pure presentation/static-resource work', 'repeated-round stress and object lifecycle coverage'],
         'latency': 'no proven saving; cannot promise seamless'},
        {'route': 'semantic_delta_patch', 'first_version': False,
         'status': 'not ready for arbitrary world restore',
         'required': ['complete per-type field ownership schema', 'create/delete/update/reference remapping',
                      'dynamic event/task ownership', 'all derived list/cache rebuilds', 'native UI invalidation',
                      'full digest and fallback checkpoint'],
         'latency': 'unknown; delta wire size does not remove application-side rebuild cost'},
    ],
    'acceptance_requirements': [
        'No duplicate economic settlement, RNG reseeding effects, events or reports across repeated boundary reloads.',
        'A-only and B-only army creation/destruction, death/capture, city/hex ownership, assignments, pending tasks and dynamic registry differences are all reconciled.',
        'Input remains closed on failure/uncertain load; a verified earlier checkpoint is the recovery path.',
        'Camera, zoom and safe local panel preferences may be retained; stale selected object references are cleared or re-resolved by ID.',
        'Measure A save, transfer, B cleanup, deserialization, postload, render rebuild, B initialization and hash check separately.',
    ],
    'full_state_coverage_verified': False,
    'automatic_guest_reload_implemented': False,
    'native_timing_measured': False,
}
(HERE / 'inplace-checkpoint-feasibility.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'result': report['result'], 'anchors_verified': len(anchors), 'native_timing_measured': False}))
