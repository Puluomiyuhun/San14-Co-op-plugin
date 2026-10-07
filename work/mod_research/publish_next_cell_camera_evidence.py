"""Publish J2 observations and bounded offline camera data flow. No game access."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python_deps'))
import capstone
from analyze_lockstep import baseline_difference, rows

TRACES = ROOT / 'lockstep-traces'
RUN = TRACES / 'next-cell-run-j2'
OUT = ROOT.parents[1] / 'outputs/san14-link'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
image = (ROOT / 'game-runtime-image.bin').read_bytes()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

def instruction(rva, expected=None):
    ins = next(md.disasm(image[rva:rva+15], rva))
    text = ins.mnemonic + ' ' + ins.op_str
    if expected is not None:
        assert text == expected, (hex(rva), text, expected)
    return {'rva': hex(rva), 'bytes': ins.bytes.hex(), 'instruction': text}

anchors = [
    (0xf794, 'lea rax, [rip + 0x19d7ef5]'),
    (0x80cc, 'lea rax, [rip + 0x123644d]'),
    (0x80d3, 'mov qword ptr [rdi + 0x50], rax'),
    (0x1292e, 'lea r9, [rcx + 0x1e4]'),
    (0x1293a, 'lea r8, [rcx + 0x1e0]'),
    (0x12941, 'lea rdx, [rcx + 0x10]'),
    (0x12945, 'call 0x9250'),
    (0x93aa, 'movsd xmm2, qword ptr [rbp - 0x50]'),
    (0x93af, 'mulsd xmm1, xmm2'),
    (0x93b9, None),
    (0x9417, 'cvtpd2ps xmm0, xmm2'),
    (0x941b, 'mov r8, r14'),
    (0x941e, 'mov rdx, rsi'),
    (0x9421, 'call 0xd190'),
    (0x1473f, 'lea r8, [rbx + 0x1e4]'),
    (0x14746, 'lea rdx, [rbx + 0x1e0]'),
    (0x1474d, 'cvtpd2ps xmm0, xmm2'),
    (0x14751, 'call 0xd190'),
    (0xd264, 'mov dword ptr [rdx], 6'),
    (0xd31d, 'mov dword ptr [rdx], r10d'),
    (0xd324, 'mov dword ptr [r8], eax'),
    (0xd32b, 'mov ecx, 0x2710'),
    (0xd394, 'mov rax, qword ptr [rcx + 0x280]'),
    (0xd3d9, 'call 0xd190'),
    (0xd3e3, 'movd xmm0, dword ptr [rcx + 0x234]'),
    (0xd3eb, 'movd xmm1, dword ptr [rcx + 0x230]'),
    (0xd3f9, 'divss xmm0, dword ptr [rip + 0x123169b]'),
    (0xd144, 'call 0xd390'),
    (0x16c601, 'call 0xd140'),
    (0x16c614, 'cmp eax, 3'),
    (0x16c617, 'jg 0x16c632'),
    (0x16c62d, 'jmp 0x163c80'),
    (0x16c637, 'jmp 0x16bef0'),
    (0x16bf49, 'and dword ptr [rcx + 0x70], 0xfffffffd'),
    (0x16bf4d, 'call 0x337200'),
    (0x336c2e, 'call 0xd390'),
    (0x336c4a, 'comiss xmm1, xmm0'),
    (0x336c4d, 'jb 0x336dc8'),
    (0x16c680, 'call 0x1622f0'),
    (0x16c697, 'call 0x15be80'),
]
static_instructions = [instruction(*a) for a in anchors]
types = read(ROOT / 'camera-types.json')
assert types['CMainCameraCtrl']['tables'] == [0x123e520]
assert 0x128f0 in types['CMainCameraCtrl']['methods'][0]
assert 0x141c0 in types['CMainCameraCtrl']['methods'][0]
assert 0x50 + 0x1e0 == 0x230 and 0x50 + 0x1e4 == 0x234
assert struct.unpack_from('<f', image, 0xd401 + 0x123169b)[0] == 10000.0

metadata = read(RUN / 'metadata.json')
analysis = read(RUN / 'next-cell-capture-analysis.json')
trace = rows(RUN / 'trace.jsonl')
counts = Counter(r['event'] for r in trace)
assert counts['worker_enter'] == counts['worker_return'] == 24
assert counts['next_cell_write'] == 1 and counts['movement_consume'] == 2
assert analysis['clean_detach'] and not analysis['errors']
assert not analysis['callbacks_still_active_at_stop']
assert len(analysis['jobs']) == 24
write, = analysis['writes']
assert write['writer']['rva'] == '0x2cd54e' and write['inside_observed_worker_callback']
assert (write['previous_observed'], write['observed_after']) == (24023, 23804)
consumers = analysis['consumers']
assert all(c['worker_90'] == 0 and c['task_done_70'] == 1 and not c['active_worker_callbacks'] for c in consumers)
assert consumers[1]['value_matches_latest_observed_write']
assert consumers[1]['date'] == [203, 8, 12]
job = next(j for j in analysis['jobs'] if j['write_sequences'])
assert job['working_ids'] == [36, 17, 61]
returned = next(r for r in trace if r.get('seq') == job['return_seq'])
assert returned['worker_90'] == 1 and returned['task_done_70'] == 0

ends = read(RUN / 'end-comparisons.json')
for key in ('after-run-b.json', 'after-stage-path-i2.json'):
    item = ends[key]
    assert not item['sampled_record_changes_excluding_known_runtime_pointer']
    assert item['focused_state_equal'] and item['person_task_sample_equal']
    assert not item['random_inputs_equal']
assert len(ends['after-run-a.json']['sampled_record_changes_excluding_known_runtime_pointer']) == 25
before = read(RUN / 'before.json')
restored = read(TRACES / 'restored-next-cell-j2.json')
restore_comparison = baseline_difference(before, restored)
assert not restore_comparison['sampled_record_changes_excluding_known_runtime_pointer']
assert restore_comparison['random_inputs_equal'] and restore_comparison['focused_state_equal']
assert restore_comparison['person_task_sample_equal']
assert restored['random_inputs']['global_18eb8b0'] == 3823646826
assert len(restored['records']) == 783
assert len(read(TRACES / 'after-next-cell-j2.json')['records']) == 785
closeout = read(TRACES / 'next-cell-j2-closeout.json')
assert not closeout['debugger_attached'] and closeout['original_strategy_update_restored']
assert closeout['save34_sha256'] == closeout['backup_sha256']
assert not closeout['rng_state_rewritten']
fixtures = [read(ROOT / n) for n in ('next-cell-fixtures.json', 'next-cell-validation.json')]
assert all(f['result'] == 'PASS' and f['observer_sha256'] == metadata['observer_sha256'] for f in fixtures)
camera = read(TRACES / 'camera-after-next-cell-j2.json')
camera_raw = bytes.fromhex(camera['singleton_hex'])
assert struct.unpack_from('<Q', camera_raw, 0x50)[0] - int(metadata['base'], 16) == 0x123e520
camera_summary = {k:v for k,v in camera.items() if not k.endswith('_hex')}
camera_summary['embedded_controller_50_vtable_rva'] = '0x123e520'
camera_summary['embedded_controller_50_type'] = 'CMainCameraCtrl'
camera_summary['scope'] = 'Single post-advance sample, before restoring save34. Not a camera trajectory or the view at combat in A/B/I2/J2.'

cancelled = rows(TRACES / 'next-cell-run-j/trace.jsonl')
assert cancelled[-1]['event'] == 'detached' and cancelled[-1]['registers_restored']
assert not cancelled[-1]['captured']
camera_evidence = {
    'finding': 'Camera distance level is an input to selected battle-effect management and creation branches.',
    'verification': 'Offline instruction/data-flow inspection with RTTI; post-run embedded vtable observed. No controlled live zoom/pan comparison yet.',
    'controller': {'singleton_rva':'0x19e7690', 'embedded_offset':'0x50', 'type':'CMainCameraCtrl', 'vtable_rva':'0x123e520'},
    'distance_to_level': [
        'CMainCameraCtrl virtual 0x128F0 passes controller+0x1E0/+0x1E4 to 0x9250.',
        '0x9250 uses a clamped distance in eye = target - direction * distance, then passes the same scalar to 0xD190.',
        'Virtual update 0x141C0 also passes a distance scalar to 0xD190 with those same output fields.',
        '0xD190 maps distance against seven thresholds to level 0..6 and a fractional output scaled by 10000.',
        'Controller offsets +0x1E0/+0x1E4 alias singleton+0x230/+0x234; 0xD390 returns level + fraction / 10000 when singleton+0x280 is null.',
        'The non-null +0x280 route also uses 0xD190, via the linked camera data; it must be observed in future camera traces.'
    ],
    'effect_branches': [
        '0x16C5F0 calls 0xD140 (which derives an integer from 0xD390). Above 3, it enters 0x16BEF0; that branch clears an effect flag and calls 0x337200 on linked effects.',
        'At lower levels 0x16C5F0 selects 0x163C80 or 0x16C6D0 according to an additional manager field.',
        'For effects with relevant flags, 0x336BF0 compares 0xD390 to the per-type threshold and returns null without creating the effect when the level is too large.'
    ],
    'limits': [
        'This establishes a camera-dependent effect branch, not two separate on-screen/off-screen combat simulators.',
        'No definite screen-frustum predicate that changes battle settlement has been identified here.',
        'The combat batch has its own builder/processor calls at 0x16C640; this does not certify every effect callee as free of gameplay, RNG or timing side effects.',
        'The position checks in 0x163C80/0x160E20 are not sufficient evidence of camera visibility; some compare unit world positions.',
        'Old traces have no camera trajectory, so neither the view at the first A divergence nor camera causation can be reconstructed.',
        'Shared RNG consumption from report/voice paths was observed in earlier research; a specific camera-to-RNG divergence is still unproven.'
    ],
    'instructions': static_instructions,
    'post_run_observation': camera_summary,
}
manifest_paths = [RUN / n for n in ('metadata.json','trace.jsonl','before.json','next-cell-capture-analysis.json','end-comparisons.json')]
manifest_paths += [TRACES / n for n in ('after-next-cell-j2.json','restored-next-cell-j2.json','next-cell-j2-closeout.json',
    'camera-after-next-cell-j2.json','next-cell-run-j/trace.jsonl')]
manifest_paths += [ROOT / n for n in ('observe_next_cell.cpp','observe_next_cell.exe','next-cell-fixtures.json',
    'next-cell-validation.json','camera-types.json','survey-f720.txt','survey-8090.txt','survey-128f0.txt',
    'survey-9250.txt','survey-141c0.txt','survey-d190.txt','survey-d390.txt','survey-d140.txt',
    'survey-16c5f0.txt','survey-16bef0.txt','survey-336bf0.txt','survey-16c640.txt','survey-160e20.txt',
    'movement-worker-static-evidence.json','capture_camera_candidate.py','publish_next_cell_camera_evidence.py')]
manifest = [{'path':str(p.relative_to(ROOT)), 'bytes':p.stat().st_size,
    'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in manifest_paths]
report = {
    'schema':'san14.lockstep-followup.next-cell-camera.v1', 'created':datetime.now().astimezone().isoformat(),
    'result':'NEXT_CELL_PRODUCER_CONFIRMED_IN_J2_CAMERA_EFFECT_BRANCH_CONFIRMED_STATICALLY_ROOT_CAUSE_OPEN',
    'metadata':metadata, 'event_counts':dict(counts), 'next_cell_observation':analysis,
    'callback_return_snapshot':{k:returned[k] for k in ('seq','thread','date','subday','progress_stage','worker_90','task_done_70')},
    'end_comparison':{n:{'differing_sampled_records':len(v['sampled_record_changes_excluding_known_runtime_pointer']),
        'focused_state_equal':v['focused_state_equal'],'person_task_sample_equal':v['person_task_sample_equal'],
        'random_inputs_equal':v['random_inputs_equal']} for n,v in ends.items()},
    'restoration': {'compared_to':'next-cell-run-j2/before.json', 'comparison':restore_comparison,
        'date':closeout['date'],'player':closeout['player'],'sampled_records':783,'debugger_attached':False,
        'original_strategy_update_restored':True,'save34_sha256':closeout['save34_sha256'],
        'backup_sha256':closeout['backup_sha256'],'rng_state_rewritten':False,
        'old_closeout_label_note':'The general closeout compares against earliest run A, not J2. Its RNG_DIFFERS label does not indicate a mismatch against J2 own starting RNG.'},
    'cancelled_j':{'clean_detach':True,'captured':False}, 'fixtures':fixtures, 'camera':camera_evidence,
    'original_a_root_cause_proven':False, 'guaranteed_next_cell_barrier_proven':False,
    'camera_changes_battle_outcome_proven':False, 'complete_world_determinism_proven':False,
    'two_client_test_performed':False, 'synchronization_patch_installed':False,
    'next_controlled_comparison': {
        'precondition':'Capture a common logical boundary after load initialization, include monitored RNG, ordered active lists and pending tasks; baseline mismatch invalidates a camera-only comparison.',
        'controls':['Same camera focus/zoom and speed, repeated control.', 'Change only focus so the combat area is on-screen versus off-screen.', 'Change only zoom while holding the same world focus.'],
        'observations':['Camera controller pose, level/fraction and +0x280 route during advance',
            'First combat gate, ordered pairs, processing phases and casualties',
            'RNG call sites/state chain', 'Next-cell completion versus logical consumers'],
        'interpretation':'Separate presentation-only differences from the earliest logical input/output difference. End-state agreement alone does not certify the intermediate battle sequence.',
        'status':'Offline plan only. No new recorder armed and no additional user replay requested this turn.'},
    'manifest':manifest,
}
destination = OUT / '下一格写入与镜头影响追查第八轮证据.json'
with destination.open('x', encoding='utf-8') as f:
    f.write(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
assert read(destination) == report
print(json.dumps({'result':'PASS','evidence':str(destination),'recorded_events':sum(counts[e] for e in ('worker_enter','worker_return','next_cell_write','movement_consume')),
    'camera_instruction_anchors':len(static_instructions),'restored_against_j2':True}, ensure_ascii=True))
