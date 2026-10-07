"""Freeze persistent hardware provider evidence without load/scheduling authority."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=ROOT/'checkpoint_persistent_input_hwbp_runs/20261007-174914-882311/result.json'
    test=json.loads(evidence.read_text());assert test['passed'] and len(test['cases'])==26
    for n,h in test['source_sha256'].items():assert sha(ROOT/n)==h,n
    handoff={
      'schema':'san14.persistent-input-hwbp.handoff.v1','offline_passed':True,'case_count':26,
      'evidence':{'path':str(evidence),'sha256':sha(evidence)},'source_sha256':test['source_sha256'],
      'generator_sha256':sha(ROOT/'checkpoint_persistent_input_hwbp_generate.py'),
      'production_obj_sha256':test['production_obj_sha256'],
      'game_access':False,'steam_access':False,'production_admission':False,'native_scheduler_fence':False,
      'problem':'Predecessor permanently published one global State pointer in Initialize, so a second fresh Context was rejected even after clean restoration.',
      'solution':[
        'One permanent vectored exception handler and pinned module runtime, initialized under a lock once. Runtime setup failure is terminal, never retried by another Context.',
        'Each address-stable Context gets an independently allocated immutable State and binding; no state reset, reuse, destroy or unload operation exists.',
        'Handler still selects only the current thread TLS route and validates the exact site, debug registers, thread, call and user.',
        'Registry validates that a Context address owns its opaque pointer. Copied handles and foreign/old-provider Contexts are refused without dereferencing an arbitrary pointer.',
        'Clean verified Finish releases that State TLS route. Restoration uncertainty retains an inert same-thread tombstone, preventing another generation Begin.',
        'All helper joins, original unchanged 33-byte native site validation, actual OS context capture and exact DR restoration logic remain from the predecessor.'
      ],
      'interfaces':{
        'header':'checkpoint_persistent_input_hwbp.h','namespace':'checkpoint_persistent_input_hwbp',
        'type_aliases':['Config','Context','Provider','HardwareReceipt','Binding','Observe','PendingReport','CaptureKind','Error'],
        'entry_points':['Initialize','Begin','Finish','Stop','Snapshot','MakeProvider','SnapshotRuntime'],
        'integration':'Change provider namespace/header only. MakeProvider returns the exact old Provider ABI accepted by persistent authorized Controller.',
        'lifetime':'Context must remain zero-initialized-before-use, address-stable and retained through process exit. Failed initialization also consumes the Context. Do not copy opaque handles.'
      },
      'new_cases':[
        'two-contexts: two actual hardware captures with distinct binding and unchanged first report.',
        'native-exception-two-contexts: first native exception propagates with exact DR restoration; second Context captures normally.',
        'repeat-context-initialize: same Context cannot reconfigure and original report is unchanged.',
        'concurrent-initialize: two distinct Contexts initialize concurrently with exactly one handler registration.',
        'copied-context-refused: copied opaque pointer cannot snapshot, begin, finish or reinitialize another State.',
        'restore-conflict-blocks-next: foreign debug register is not overwritten; old TLS remains and second generation cannot arm.',
        'deadline-blocks-next: expired arm helper is joined and cleaned, receipt remains uncertain and next generation is refused.',
        'failed-context-terminal: invalid site consumes its Context; a separate fresh Context may initialize normally.'
      ],
      'regression':'18 predecessor owned-process actual hardware tests reused read-only by changing only provider namespace; all pass.',
      'limitations':[
        'Owned memory/native instruction fixture, not the game process. No game operation was performed.',
        'The runtime installation OS failure branch is terminal by code inspection; actual OS AddVectoredExceptionHandler/GetModuleHandleEx failure was not artificially induced.',
        'Same-thread restoration tombstone is not a process-wide scheduler fence. Admission owner must still reject generation handoff when any old work or receipt is unresolved.',
        'Helper timeout is a refusal deadline, not a hard cleanup deadline; underlying helper is joined and never forcibly terminated.',
        'Hardware observation and clean restoration alone do not grant queue/load/input/presentation/world-ready authority.'
      ]
    }
    p=ROOT/'checkpoint_persistent_input_hwbp_handoff.json';p.write_text(json.dumps(handoff,indent=2),encoding='utf-8');print(json.dumps({'path':str(p),'sha256':sha(p)}))
if __name__=='__main__':main()
