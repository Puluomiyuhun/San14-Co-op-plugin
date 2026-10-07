"""Freeze adapter evidence only. No native/game activation authority."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=ROOT/'checkpoint_persistent_logical_adapter_runs/20261007-170436-535150/result.json'
    test=json.loads(evidence.read_text());assert test['passed'] and len(test['cases'])==20
    for n,h in test['source_sha256'].items():assert sha(ROOT/n)==h,n
    handoff={
      'schema':'san14.persistent-logical-adapter.handoff.v1','offline_passed':True,'cases':20,
      'evidence':{'path':str(evidence),'sha256':sha(evidence)},'source_sha256':test['source_sha256'],
      'fixture_exe_sha256':test['fixture_exe_sha256'],'production_obj_sha256':test['production_obj_sha256'],
      'game_access':False,'steam_access':False,'production_admission':False,'native_scheduler_fence':False,
      'interfaces':{
        'header':'checkpoint_persistent_logical_adapter.h','namespace':'checkpoint_persistent_logical_adapter',
        'initialize':'Adapter.Initialize(Config) consumes configuration once, including failed attempts.',
        'routing':'Adapter.RouteGeneration() returns immutable generation id plus Before/After/Finally callbacks and context.',
        'config':'generation; dispatchBefore/After/Finally[4], dispatchContexts[4]; workerBefore/After/Finally[2], workerContexts[2].',
        'claim':'bool Claim(const CheckpointLoadWorkerFrame*, uint64_t) noexcept',
        'owner':'bool CurrentOwner(CheckpointLoadWorkerOwner*) noexcept',
        'mapping':'bool CurrentMapping(Mapping*) noexcept: diagnostics only; no native capability.'
      },
      'mapping':[
        'Physical slots 0..3 copy into CheckpointPushFrame, preserving slot, args, call/thread/caller and return payload.',
        'Physical slot 4 becomes logical worker slot 0; physical slot 5 becomes logical read slot 1.',
        'One logical frame address per active invocation; Before/After/Finally reuse that address and refresh values from the exact corresponding physical frame.',
        'Owner/worker Exit depth counts logical worker/read scopes; dispatch scopes do not inflate old worker depth semantics.',
        'CurrentOwner requires a successful Claim issued through this adapter, exact physical call/thread/slot, matching native owner depth and same immutable adapter/generation.'
      ],
      'verification':[
        'Actual six native/MASM bridge entries, production router and both adapter layers execute without fixture macros.',
        '20 owned-process cases include four threads with 4000 total calls, active cutover and late roots, nested dispatch/worker/read, and cross-router generation-owner rejection.',
        'Frame-copy, ancestor, mutated-frame, foreign-thread and non-Before claims refuse; direct native Claim is not accepted by logical CurrentOwner.',
        'Native SEH/C++ and Before/After/Finally SEH clean both logical TLS and route leases; original exception survives a second Finally exception.',
        'Production source builds /EHa /W4 /WX with no warnings. No old source, globals or symbols are redefined.'
      ],
      'limitations':[
        'Frozen observers still require explicit build-time/API shim integration; standalone adapter tests do not themselves claim game observer integration.',
        'Caller must retain adapters, callback code and contexts until process exit. Logical frame references expire after callback lifetime and are not durable capabilities.',
        'No callback-routing test proves native scheduler quiescence or authorizes a second live load.',
        'CurrentMapping exposes diagnostic physical addresses only. It is not a native-call capability.',
        'Native bridge and router behavior for delayed root work remains unchanged: entering after cutover chooses the current generation.'
      ],
      'root_session_readonly_review':{
        'files':['checkpoint_persistent_native_session.h','checkpoint_persistent_native_session.cpp'],
        'result':'No new blocking defect found in reviewed Finally/per-generation delta.',
        'observations':['Dispatch active decrement moved to Finally.','Only matching call records clear on Finally; overlapping calls cannot clear outer records.','Per-generation snapshots no longer use cumulative physical-bridge abnormalities.','A native Load exception may retain old lifecycle inFlight; Session DispatchPair error must continue rejecting completion, not be treated as repaired by decrementing counters.'],
        'authority':False
      }
    }
    p=ROOT/'checkpoint_persistent_logical_adapter_handoff.json';p.write_text(json.dumps(handoff,indent=2),encoding='utf-8');print(json.dumps({'path':str(p),'sha256':sha(p)}))
if __name__=='__main__':main()
