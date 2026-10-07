"""Publish camera-route evidence without turning conditional static paths into observed causation."""
from pathlib import Path
from datetime import datetime
import hashlib,json,struct,sys
ROOT=Path(__file__).resolve().parent;OUT=ROOT.parents[1]/'outputs/san14-link'
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
b=(ROOT/'game-runtime-image.bin').read_bytes()
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
checks={
    0x15b0b5:'call 0x210ff0',0x15b119:'call 0xf720',0x15b11e:'lea rdx, [rax + 0x50]',
    0x15b12a:'call 0x322030',0x15b131:'je 0x15b1e8',0x15b14e:'call 0x321260',
    0x15b18e:'call 0x323e60',0x15b1a4:'call 0x325870',0x15b216:'call 0x16ea80',
    0x15b280:'call 0x1649c0',0x15b288:'call 0x164ae0',0x15b290:'call 0x164d30',
    0x322080:'cmp dword ptr [rax + 0x4c], 0',0x32208f:'cmp dword ptr [rbx + 0x1e0], 4',
    0x322096:'jge 0x322187',0x32216b:'call 0xfac0',0x32217e:'je 0x322187',
    0x164d3d:'call 0x164e00',0x164dcc:'call 0x3b35e0',0x164e78:'call 0x3b35e0',
    0x3b3690:'call 0x3b36b0',0x3b3774:'call 0x3aa7c0',
    0x3aa7c0:'cmp ecx, 2',0x3aa7c3:'jl 0x3aa815',0x3aa805:'mov dword ptr [rip + 0x15410a5], eax',
    0x1b4e0d:'call 0xd140',0x1b4e14:'call 0x161200',0x1b4e1b:'je 0x1b4fe6',
    0x1b4fac:'call 0x3b2e90',0x3b2f74:'call 0xfac0',0x3b2f7b:'je 0x3b2faa',0x3b2fa4:'call 0x3b2d80',
    0xfae0:'call 0x14f10',0xfaf0:'divss xmm0, dword ptr [rsp + 0x2c]',
    0xfb1e:'jbe 0xfb4b',0xfb3c:'mov eax, 1',0xfb4b:'xor eax, eax',
    0x166005:'call 0x15b070',0x1665f6:'call 0x15b070',
    0x166baf:'mov dword ptr [rax + 0x98], r12d',0x1691b5:'mov dword ptr [rax + 0x98], 1',
    0x16994e:'mov dword ptr [rax + 0x98], 1',0x16c6a1:'mov ecx, dword ptr [rax + 0x98]',
    0x16c6a7:'mov dword ptr [rbx + 0x94], ecx',
}
anchors=[]
for at,expected in checks.items():
    ins=next(md.disasm(b[at:at+15],at));actual=ins.mnemonic+' '+ins.op_str
    assert actual==expected,(hex(at),actual)
    anchors.append({'rva':hex(at),'instruction':actual,'bytes':ins.bytes.hex()})
base=struct.unpack_from('<Q',b,0x12cc4a8+0x28)[0]-0x3f9b00
vt=0x12abc60;col=struct.unpack_from('<Q',b,vt-8)[0]-base;td=struct.unpack_from('<I',b,col+12)[0]
name=b[td+16:td+144].split(b'\0',1)[0].decode('ascii')
assert name=='.?AVCUniqueTacticsScene@@'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
validation=read(ROOT/'visibility-fixture-validation.json');assert validation['result']=='PASS' and len(validation['cases'])==23
observer_validation=read(ROOT/'camera-route-validation.json');assert observer_validation['result']=='PASS'
dry=ROOT/'lockstep-traces/camera-route-dry-k'
trace=[json.loads(x) for x in (dry/'trace.jsonl').read_text().splitlines()]
assert trace[-1]=={'event':'detached','captured':False,'registers_restored':True}
idle=read(dry/'idle-comparison.json')
assert not idle['sampled_record_changes_excluding_known_runtime_pointer'] and idle['random_inputs_equal']
assert idle['focused_state_equal'] and idle['person_task_sample_equal']
current=read(ROOT/'lockstep-traces/camera-route-dry-k-after.json')
assert not current['debugger_attached'] and current['gameplay_sample_unchanged']
manifest_names=['survey-15b070.txt','survey-322030.txt','survey-fac0.txt','survey-14f10.txt','survey-321260.txt',
    'survey-164d30.txt','survey-164e00.txt','survey-3b35e0.txt','survey-3b36b0.txt','survey-1b4dd0.txt','survey-3b2e90.txt',
    'survey-3b2d80.txt','survey-3b2b10.txt','survey-166aa0.txt','survey-168ba0.txt','survey-169790.txt',
    'visibility-fixture-source.json','visibility-fixture-validation.json','visibility_fixture.cpp','visibility_fixture.exe',
    'observe_camera_route.cpp','observe_camera_route.exe','camera-route-validation.json','camera_route_payload_fixture.cpp',
    'start_camera_route_observer.py','make_camera_route_observer.py','publish_camera_route_research.py',
    'lockstep-traces/camera-route-dry-k/metadata.json','lockstep-traces/camera-route-dry-k/trace.jsonl',
    'lockstep-traces/camera-route-dry-k/before.json','lockstep-traces/camera-route-dry-k/after.json',
    'lockstep-traces/camera-route-dry-k/idle-comparison.json','lockstep-traces/camera-route-dry-k-after.json']
manifest=[{'path':s,'sha256':hashlib.sha256((ROOT/s).read_bytes()).hexdigest(),'bytes':(ROOT/s).stat().st_size} for s in manifest_names]
report={
    'schema':'san14.lockstep-followup.camera-route.v1','created':datetime.now().astimezone().isoformat(),
    'result':'CAMERA_DEPENDENT_TACTICS_PRESENTATION_ROUTE_FOUND_NATIVE_VISIBILITY_VERIFIED_LIVE_CAUSAL_COMPARISON_PENDING',
    'native_scene_type':{'name':name,'vtable_rva':hex(vt),'constructor_rva':'0x321260'},
    'tactic_branch':{
        'source':'0x164F60/0x166090 -> 0x15B070',
        'camera_gate':'If the initial tactic predicate is satisfied, 0x322030 checks an option, actor-related qualifications, controller level < 4 and projected visibility via 0xFAC0.',
        'scene_route':'Predicate true -> construct CUniqueTacticsScene -> 0x323E60 -> register through 0x325870.',
        'ordinary_route':'Predicate false or initial predicate false -> allocate ordinary effect record -> 0x1649C0 / 0x164AE0 / 0x164D30.',
        'rng_path':'0x164D30 -> 0x164E00 and/or per-target call -> 0x3B35E0 -> 0x3B36B0 -> 0x3AA7C0; it consumes the shared state only when the selected variant count is at least 2 and the prerequisite branches permit the call.',
        'limits':'Static conditional reachability. It does not show that the unique route consumes fewer/more total draws, that either path caused an actual battle difference, or that every tactic qualifies.'},
    'visibility_predicate':{'rva':'0xFAC0','transform_rva':'0x14F10','semantics':'Transform the supplied position by the supplied 4x4 matrix, divide by w, test strict x/y bounds (-margin,margin) and depth (0,margin). A separate global bypass returns true.',
        'proof':validation,'live_camera_test_performed':False},
    'attack_sound':{'path':'0x1B4DD0 -> level <= 3 gate -> selected effect types -> 0x3B2E90 -> 0xFAC0 -> 0x3B2D80',
        'finding':'Projection visibility gates this positional sound route.',
        'rng_finding':'No direct call to the known shared RNG in inspected 0x3B2E90/0x3B2D80/0x3B2B10/0x3B43F0 bodies. Indirect calls and other dependencies remain outside that negative statement.'},
    'waiting':{'finding':'Known effect_pending_98 setters inspected here depend on native damage/state-change outcomes; the field is read into battle pending_94. No new demonstrated camera-to-pending write chain in this turn.',
        'reason_for_caution':'A camera-dependent effect branch is not itself proof that this waiting field differs.'},
    'original_a_root_cause_proven':False,'two_client_determinism_proven':False,
    'observer_preparation':{'validation':observer_validation,'dry_run_cleanly_detached':True,'idle_comparison':idle,
        'markers':['0x15B070 tactic dispatch','0x15B12F camera-dependent eligibility result','0x3AA805 primary RNG native pre-store','0x3F9344 combat gate'],
        'limits':['Only the primary RNG writer is hooked; a gap must be reported, not repaired by assumption.',
            'Eligibility true does not certify allocation or completion of a special scene.',
            'Gate samples and partial army records cannot prove equality of every intermediate animation.',
            'Hardware breakpoints affect wall-clock scheduling.'],
        'not_armed_for_replay_at_publication':True},
    'next_comparison':{'status':'Asked user to zoom out fully while remaining in save34 planning, then reply ready. No advance requested yet.',
        'plan':'Verify far-view level and unchanged gameplay/RNG first; record a far-view control. Restore and verify the same starting state before changing the view for comparison.',
        'attribution_rule':'A zoom comparison may also change visibility. Follow with fixed-zoom pan comparison if needed; do not label a compound view change as zoom-only causation.'},
    'instructions':anchors,'manifest':manifest,
}
path=OUT/'视野与战法演出路径追查第九轮证据.json'
with path.open('x',encoding='utf-8') as f:f.write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert read(path)==report
print(json.dumps({'result':'PASS','instruction_anchors':len(anchors),'native_visibility_cases':len(validation['cases']),'observer_ready':True,'live_comparison_pending':True},ensure_ascii=True))
