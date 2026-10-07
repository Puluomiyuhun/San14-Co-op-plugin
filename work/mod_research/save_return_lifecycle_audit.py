"""Offline audit only. Replays the existing worker shadow without its main().

No process access, save/load call, native storage access, or injector entry exists
in this script. All addresses are RVAs of the pinned captured image.
"""
from pathlib import Path
import hashlib, json, sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE / 'python_deps'), str(HERE)]
saved_args = sys.argv[:]
sys.argv = sys.argv[:1]
from verify_native_save_worker import run_case, d
sys.argv = saved_args

IMAGE_SHA = '5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
assert hashlib.sha256(d.image).hexdigest() == IMAGE_SHA
shadow_path = HERE / 'save_return_lifecycle_shadow.json'
shadow = json.loads(shadow_path.read_text(encoding='utf-8'))
assert shadow['result'] == 'PASS' and len(shadow['cases']) == 23

worker_inputs = [{}, {'prepare': False}, {'storage_ok': False}, {'status': -323},
    {'status': 1}, {'reused': True}, {'backing': True},
    {'storage_ok': False, 'backing': True}, {'old_flag': 0},
    {'prepare': False, 'old_flag': 0}, {'stream_present': False},
    {'status': -300, 'stream_present': False}]
worker_rows = [run_case(**case) for case in worker_inputs]
for row in worker_rows:
    assert 'manager_one_cleanup' in row['calls']
    assert 'manager_two_cleanup' in row['calls']

def instructions(start, end):
    return [f'{i.address:#x}: {i.mnemonic} {i.op_str}'.rstrip()
            for i in d.decoder.disasm(d.image[start:end], start)]

write_sets = [
  {'scope': '0x2DF990 native type0 builder and tested empty callback',
   'writes': ['Fresh state allocation 0x4F0 bytes; native constructor 0x4263C0 and thread object constructor 0x8333D0 initialize it.',
              'State name at +0x70 through 0x509EC0; copied empty callback at +0x10 through 0x509E10 -> 0x3C6300 -> 0x3D3400.',
              'Manager pending vector at +0x30/+0x38/+0x40 and pending command {type=0, state=newState}; growth rounds capacity to a multiple of 64.'],
   'no_direct_store_identified': ['CWorld date', 'global RNG', 'existing CUserStrategyState phase'],
   'tested': 'Actual queue append, native constructor/name/callback and native null-buffer growth dispatch; allocator endpoints stubbed.',
   'not_proven': 'Executing the pending scheduler command, nonempty callback virtual copy/destruction, allocation failure/exception semantics.'},
  {'scope': '0x4A29D0 CSaveState initialize',
   'writes': ['Allocates 0x168-byte progress UI; constructs through 0x5D3730 and stores pointer at state+0x4E8.',
              'Calls 0x5D5840 to construct resources/layout, 0x5D7940 save_in and 0x5D7A30 save_loop, then UI virtual+0x38.'],
   'no_direct_store_identified': ['CWorld date', 'global RNG', 'existing CUserStrategyState phase'],
   'tested': 'Static instructions only for this function and selected UI leaves.',
   'not_proven': 'Transitive UI resource, sound, animation, allocator and virtual callback side effects. Do not classify initialize as world-pure.'},
  {'scope': '0x4AA650 CSaveState update and 0x4DA320/0x4F7050 phase helpers',
   'writes': ['state+0x470 phase: 0->1->2->3->4; state+0x474 timestamp on phase 0.',
              'Thread object at state+0x478 receives worker 0x508CA0 and native thread lifecycle calls.',
              '0x4DA370 resets main-result dword RVA 0x201EC2C to zero, AFTER call to thread-start helper 0x834B60.'],
   'no_direct_store_identified': ['CWorld date', 'global RNG', 'existing CUserStrategyState phase'],
   'tested': 'Actual update/top-state predicate/phase helper instructions; timing, OS thread construction/start/poll/join and Sleep are explicit stubs.',
   'not_proven': 'Native OS scheduling or concurrency. Start-before-result-reset is an observed ordering, not proof of an actual race.'},
  {'scope': '0x465C10 save completion; 0x10A60; 0x835DD0 -> 0x836DF0',
   'writes': ['Appends manager pending type1 command (pop), including pending-vector allocation if empty.',
              'RVA 0x201ED10=-1; request-name size RVA 0x201ED28=0 and first byte=0; caption size RVA 0x201ED48=0 and first byte=0. Existing heap/SSO representation is respected.',
              'Clears native cache list and 120 slot pointers; cache+0x3E0=0, +0x3E4=-1, +0x3F4=-1, +0x3EC=-1.',
              'Cache+0x3E8 and +0x3F8 are retained; fixture uses prior indices 56 and 114. Main-result flag is retained.'],
   'no_direct_store_identified': ['CWorld date', 'global RNG', 'existing CUserStrategyState phase'],
   'tested': 'Actual success/failure/error-text branches, type1 append, and native empty-cache clearing. Error dialog and manager getter are explicit stubs.',
   'not_proven': 'Scheduler pop, CSaveState destruction and underlying-state resume/enter callback. These are necessary to prove return to the same planning state.'},
  {'scope': '0x497A00 CSaveState deinitialize',
   'writes': ['UI virtual+0x40; virtual+0x28 with original RDX argument; virtual destructor with EDX=1; state+0x4E8=0.'],
   'no_direct_store_identified': ['CWorld date', 'global RNG', 'existing CUserStrategyState phase'],
   'tested': 'Static call sequence only.',
   'not_proven': 'Transitive UI callbacks/destructors and callback arguments.'},
  {'scope': '0x508CA0 worker',
   'writes': ['RVA 0x201EC2C is assigned this attempt result only after main finalization and both sidecar attempts.',
              'Calls 0x2EE740 then, if nonnull, 0x2FCE40. Only exact finalizer EAX=0 becomes success.',
              'Attempts 0x39C260 -> 0x3A0690 and 0x39C440 -> 0x39D500 regardless of main archive result; both return values ignored.'],
   'tested': '12 actual worker+finalizer control-flow cases, with preparation/storage/locks/destruction/error UI and whole sidecar calls stubbed. The separate lifecycle shadow executes the actual sidecar control functions.',
   'not_proven': 'Complete serializer side effects, real storage identity/durability, actual locks and native worker lifetime.'},
  {'scope': '0x2EE740 native save preparation',
   'writes': ['Native archive allocation/constructor; archive+0x18=0x5C, +0x24=0; caption copy at +0x30.',
              'Calls 0x2F4B20 to reset serialization work tables, then 0x2F7A10 to open/save explicit filename.',
              'Clears root error string rooted at root+0x85180 under the root+0x85170 lock; negative status uses 0x2EE0B0 to set error text then destroys archive and returns null.'],
   'tested': 'Static audit; nested serialization table reset is executed separately.',
   'not_proven': 'The complete archive constructor/open/serializer/caption helper graph and allocation exceptions.'},
  {'scope': '0x2F4B20 serialization work-table reset',
   'writes': ['RVA 0x1FCA320 word=1.',
              'Clears/frees nodes from two trees at pointers RVA 0x1FCA330 and 0x1FCA340; native 0x3B60D0 tree recursion.',
              'Resets sentinel left/parent/right pointers to self and counts RVA 0x1FCA338/RVA 0x1FCA348 to zero.'],
   'tested': 'Native empty and one-node-per-tree cases; only underlying heap free stubbed.',
   'not_proven': 'Arbitrary corrupt/shared trees. These are serialization work structures; this audit does not classify them as world business objects.'},
  {'scope': '0x2F7B50 / 0x2E7D30 / 0x2F9610 serialization',
   'writes': ['Stream fields and buffers, archive+0x1C position and +0x28 flag; error code archive+0x24=-323 for write error.',
              'Header generated through 0x2E2CF0 and written with 0x2FAAD0; broad full-object serializer 0x2E7D30 not exhaustively audited.',
              'CWorld serializer fragment 0x2F9A24..0x2F9A72 reads RNG via 0x3AA390 and writes captured value back through 0x3AA3E0 to RVA 0x18EB8B0.'],
   'tested': 'Actual RNG getter/serialization control/setter fragment in no-intervention and synthetic intervening-write cases.',
   'not_proven': 'Full-world purity or all object serializers. Single-thread RNG roundtrip is unchanged, but its real write can restore an earlier value if a consumer intervenes; no real race is asserted.'},
  {'scope': '0x2FCE40 finalizer',
   'writes': ['If status zero and stream present: optional stream transform then 0x3A6A10 storage commit; false sets archive+0x24=-300.',
              'Clears root error string; negative status calls 0x2EE0B0.',
              'Destroys/frees stream and backing objects, clears archive+0x10/+0x8; destroys archive except reusable root+0x851A0 archive.'],
   'tested': 'Actual finalizer branching and result propagation in 12 worker cases; storage/locks/error writer/destructors are explicit stubs.',
   'not_proven': 'A zero result alone does not certify new file data: a synthetic zero-status null-stream archive also returns zero.'},
  {'scope': '0x3A0690 configuration sidecar and 0x39D500 profile sidecar',
   'writes': ['When global RVA 0x2025F50 and its +0x108 are nonnull, may write configS_SC.s14 (version 14) and prdataN.s14 (version 7).',
              'Both call native open 0x3A90C0 with mode 0, then serializers 0x3A0870 or 0x39E060 and transform/close.',
              'Profile open receives low 32 bits of Steam user ID as fifth argument; this is not the RemoteStorage context itself.',
              'Serializer failure takes error-log path. Sidecar booleans are ignored by worker.'],
   'tested': 'Actual SSO/filename selection and control flow with open success/failure and serializer success/failure for each sidecar. Real storage, sidecar serializers and Steam interface are explicit stubs.',
   'not_proven': 'Transitive profile/config object changes or writes through their serializers; real file success and external effects.'}
]

abi = {
  'call_site': '0x50B782 call [rax+0x28]',
  'registers': {'RCX': 'state RBX', 'RDX': 'RBP', 'R8': 'RSI', 'R9': 'RDI'},
  'nearby_predicate': '0x50B760 calls virtual+0x30, then tests EAX. This test belongs to the predicate, not Update.',
  'after_update': '0x50B785..0x50B799 restores nonvolatile registers/stack and returns without inspecting or changing RAX.',
  'conclusion': 'Immediate wrapper forwards Update RAX; semantic C++ return type and farther callers are not established. Preserve all four incoming register arguments and the original full 64-bit RAX.',
  'observed_returns': ['CSaveState phase0 returns clock-derived EAX (fixture 12345), phase3 returns 1, not-top returns 0.',
                       'CUserStrategyState phase5 stores phase6 then returns with EAX=5; tail helper branches can return their own values.'],
  'old_wrapper_issue': 'The old void Update wrapper may clobber RAX while decrementing callback counters/finally. This is a real ABI preservation gap, not an established explanation of the prior unwanted date advance.',
  'new_wrapper': 'Capture original function return in a uint64_t variable, perform cleanup, return captured value; forward all four original registers. Do not reduce to DWORD(self) based on current evidence.',
  'caller_instructions': instructions(0x50B730, 0x50B79A),
  'user_update_instructions': instructions(0x3F9B00, 0x3F9B70),
  'live_wrapper_created': False
}

report = {
 'schema': 'san14.save-return-lifecycle-audit.v1',
 'classification': 'OFFLINE_EVIDENCE_ONLY_NOT_LIVE_READY',
 'captured_image_sha256': IMAGE_SHA,
 'supported_game_exe_sha256': '42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025',
 'game_access': False, 'save_files_written': False, 'retired_entry_reenabled': False,
 'prior_failure': {'entry': '0x412520 / pending type2',
    'status': 'Retired; produced a forensic file but unexpectedly advanced the date after save. Not a passed checkpoint export.',
    'candidate_difference': '0x2DF990 builds pending type0 and 0x465C10 appends type1. The native scheduler and real UserStrategy pause/resume must demonstrate preservation of the existing User object and phase; queue numbers alone are not proof.',
    'forensic_report': 'private_checkpoint_metadata_new_file.json',
    'forensic_header': '203-08-11 Zhang Lu header predates observed later advancement; file header alone cannot certify a quiescent lifecycle.'},
 'direct_and_nested_write_sets': write_sets,
 'update_abi': abi,
 'offline_validation': {
    'lifecycle_cases': 23, 'lifecycle_result': 'PASS',
    'lifecycle_artifact': shadow_path.name,
    'lifecycle_artifact_sha256': hashlib.sha256(shadow_path.read_bytes()).hexdigest(),
    'worker_cases': len(worker_rows), 'worker_result': 'PASS', 'worker_rows': worker_rows,
    'limits': 'Copied native machine instructions in Unicorn with explicitly stubbed boundaries. Model world-prefix/RNG checks cover only fixture memory and do not replace a full native world or UI/thread/storage execution.'},
 'remaining_dependencies': [
    'Native scheduler type0 push/pause and type1 pop/resume must preserve the same existing UserStrategy object and phase2; parent audits this separately.',
    'Initialize/deinitialize transitive progress UI calls and error dialog are not proven world-pure; do not suppress them without lifecycle evidence.',
    'Complete main and sidecar serializers are not exhaustively audited; a broad claim that saving changes no world/RNG is unjustified.',
    'A live proposal must verify date, strategy phase, object identity, whole relevant business state and RNG before/after, rather than only the worker flag or file header.',
    'Manifest must account for configS_SC.s14 and prdataN.s14, since worker attempts both even if primary export fails.',
    'Actual worker/thread completion and external storage contents remain untested in this audit. Entry remains offline-only; no new live pilot is supplied.'
 ]
}
(HERE / 'save_return_lifecycle_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'result':'PASS','lifecycle_cases':23,'worker_cases':len(worker_rows),'classification':report['classification'],'game_access':False,'save_files_written':False}))
