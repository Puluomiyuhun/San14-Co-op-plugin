"""Build the bounded offline contract; never opens the game or save directory."""
from pathlib import Path
from datetime import datetime
import hashlib,json
ROOT=Path(__file__).resolve().parent

def latest(pattern):
    path=max(ROOT.glob(pattern),key=lambda p:p.name)
    row=json.loads(path.read_text(encoding='utf-8'));assert row['result']=='PASS'
    return path,row
chain_path,chain=latest('checkpoint_push_native_chain_20*.json')
modes_path,modes=latest('checkpoint_push_native_chain_modes_20*.json')
assert len(chain['cases'])==18 and len(modes['cases'])==8
report={
 'schema':'san14.checkpoint-push-native-chain-contract.v1',
 'classification':'OFFLINE_NATIVE_CHAIN_VERIFIED_WITH_EXPLICIT_BOUNDARIES',
 'game_access':False,'save_files_written':False,'retired_entry_reenabled':False,
 'evidence':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cases':len(row['cases'])}
             for p,row in ((chain_path,chain),(modes_path,modes))],
 'chain':[
   '2FC750 consumes private request strings and binds explicit filename with slot=-1.',
   '2DF990 builds real CSaveState through4263C0/8333D0, copies empty64-byte callback and appends pending type0.',
   '50A150 event switch and50A7BA native command apply execute User exit/pause; dispatcher allocates fresh graphics context because native ctor+60 is zero, executes Save initialize/resume and appends Save to native stack.',
   '4AA650 transitions native Save phases0,1,2,3,4. Native thread lifecycle is stubbed; worker result publication is explicitly synthetic in this chain.',
   '465C10 appends native type1, clears bound request strings and cache; dispatcher calls native497A00/438490 and resumes/re-enters original User.',
   'Original five object addresses are retained in original order, original User remains phase2, no advance flag is set in model, no User destruction occurs.'
 ],
 'separate_worker_mode_test':{
   'native':'508CA0 -> 2EE740 -> real2E24B0/2F4B20 -> 2F7A10 explicit name path -> 2FCE40',
   'matrix':'cache+8 mode0/1 x cache+3F0 secondary0/1 x storage success/failure',
   'observed':'All eight cases request mppush01.s14 with stream mode0 (write). Native memory-read hook records no cache+8/+3F0 reads or writes in executed boundaries.',
   'substitutions':'Stream/backing constructors, storage open/commit, full2F7B50 serialization, locks, error text and sidecars are explicit stubs. Not full game worker execution.'},
 'cache_mode_meaning':{
   'constructor':'426320 calls835DD0 then426399 writes cache+8 from input mode and4263A6 writes+3F0 from input second field.',
   'menu_read':'4AA200 inspects cache+8 and chooses save for nonzero, load for zero.43BDFF reads+3F0 to choose storage-menu UI layout/initialization branch;43BF33 also reads+8 for UI callbacks.',
   'storage_mode':'2F7B21 xor r8d,r8d precedes2F7B2C call3A90C0, independently selecting write stream. Explicit nonempty filename branches at2F7ABC directly to2F7AE1, bypassing2F1650 standard-slot formatter.',
   'completion':'465CBE tail835DD0 ->836DF0 invalidates metadata/pending; no store to mode+8 or secondary+3F0.',
   'recommended_guard':'For this controlled attempt pin currently observed mode1 and secondary0 (from root preflight), require both unchanged before queue/after return, and never rewrite them. Mode0 is not a demonstrated worker requirement. Broader0/1 support is supported by these bounded paths but should not substitute for pinning the actual session.',
   'limit':'This audit does not prove that all transitively called UI/world/sidecar functions ignore these fields. Its claim is the actual native control/filename/mode chain and recorded executed memory reads.'},
 'strict_guards_to_implement':[
   'Supported EXE/image fingerprints and unchanged original User/Save vtable Update pointers; preserve original full64-bitRAX and all four register arguments. Exact native caller50B785 and same expected thread for submission.',
   'Exactly five stable planning states with original object addresses/types/names, User phase2, no pending menu/modal/date-advance requests, ordinary context (absent or inactive), validated UI pointers/coordinator state. No live input during accepted attempt.',
   'Root/world identity, test date203-08-11, ZhangLu ruler666 force12 and required city/army invariants. Treat this as a fixed test profile, not generic every-turn save support.',
   'Pending command count0; legitimate allocator vtable/functions; valid(capacity0,pointer0) or bounded nonzero vector. State stack has enough capacity or its native growth path is separately supported; do not assume pending vector preallocation.',
   'Cache pending=-1, mode/secondary pinned to observed baseline; valid empty ownership graph and all120 slot pointers zero for this controlled empty-cache fixture. Stale native +3E8/+3F8 values must not be rewritten.',
   'Save request globals idle using actual MSVC string representation (valid heap capacity may remain from prior calls), private filename exact and nonempty, explicit slot=-1. Use fresh zeroed64-byte callback; verify newly queued type0 and CSaveState vtable/name/phase plus empty copied callback.',
   'New one-use filename absent both locally and in native Steam storage; durable CREATE_NEW journal before binding/queueing. No retry or rollback after ambiguous partial native submission. Existing failed/retired entries and journals remain untouched.',
   'Native Save observation must associate the exact newly queued state above the five original objects; bind checks must hold before finalization. Observe worker-start/join, terminal flag, native finalizer return, native pop and original User return separately.',
   'Return guard checks identical original state/root/world identities, expected phase/date/business snapshot/RNG and file manifests. Worker flag alone, file header alone or a cleared request alone cannot mark success.',
   'Hook cleanup counters must balance every normal/error branch; passive cleanup cannot cancel an already queued save. Keep code module pinned if callbacks may still refer to it; timeout remains indeterminate/no-auto-retry.'
 ],
 'side_effect_boundaries':[
   'Real User pause/resume changes UI control/cursor/coordinator flags, temporarily closes UI, and may clear valid selection. Model shows recovery of ordinary controls; selection preservation is not promised.',
   'Native dispatcher allocates a0x188 graphics context; Save initialize allocates0x168 progress UI and requests save_in/save_loop. Their graphics/resource constructors and virtual methods are stubs here.',
   'Save worker main serialization is not pure by assumption: serialization work trees reset, error text changes, and known RNG serialization writes captured state back. No real concurrent quiescence proof in this VM.',
   'Worker attempts configS_SC.s14 and prdataN.s14 even on main failure and ignores their results. Both belong in before/after file evidence.',
   'Complete object serializer, Steam content identity/durability, OS worker synchronization and UI side effects remain unproven by the end-to-end synthetic-worker chain.',
   'No live entry executed by these scripts. The original type2 pilot remains retired.'
 ],
 'review_note':{'save_after_early_return':'At initial review saveAfter call_id mismatch returned before decrementing saveActiveCallbacks. Root subsequently reported this fixed by clearing observed and flowing through common decrement. Final candidate-source review is pending its completed refactor/fixtures; this was not an observed live failure.'}
}
path=ROOT/('checkpoint_push_native_chain_contract_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
with path.open('x',encoding='utf-8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'result':'PASS','path':str(path),'cases':26,'game_access':False}))
