"""Freeze offline routing evidence; never authorizes a game operation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    paths=[ROOT/'checkpoint_persistent_route_runs/20261007-164632-900385/result.json',ROOT/'checkpoint_persistent_route_six_runs/20261007-164636-467182/result.json']
    for p in paths:
        j=json.loads(p.read_text());assert j['passed']
        for n,h in j['source_sha256'].items():assert sha(ROOT/n)==h,n
    names=sorted({n for p in paths for n in json.loads(p.read_text())['source_sha256']})
    result={
      'schema':'san14.persistent-route.handoff.v1','offline_passed':True,
      'case_count':20,'production_admission':False,'native_scheduler_fence':False,
      'game_access':False,'steam_access':False,'hook_installation':False,
      'source_sha256':{n:sha(ROOT/n) for n in names},
      'evidence':[{'path':str(p),'sha256':sha(p)} for p in paths],
      'objects':{n:sha(ROOT/n) for n in ('checkpoint_persistent_route_core.obj','checkpoint_persistent_route_worker_adapter.obj','checkpoint_persistent_route_six_adapter.obj','checkpoint_persistent_route_fixture.exe','checkpoint_persistent_route_six_fixture.exe')},
      'delivered':['Fixed-capacity immutable generation routing core; per-entry leases retain the same generation across Before/After/Finally.','Worker bridge adapter with bounded per-thread nested lease stack and guaranteed release even if the final observer raises.','Six-entry adapter wired to actual new MASM/native bridge; new Claim/CurrentOwner TLS explicitly used.','Default generation publication disabled; only named offline exercise entry can change generations.'],
      'tested':['Four concurrent threads and 12000 native bridge calls.','Deterministic old active callback survives cutover on its old generation.','Delayed root entering after cutover selects the new generation.','Same-router nested calls inherit their ancestor generation across all six physical entries.','Native SEH/C++ and Before/After/Finally observer SEH releases; original SEH survives another exception in final observer.','New bridge slots 4 and 5 preserve Claim/CurrentOwner nesting.','Cross-thread release refusal, double release, stale-parent rejection, bounded nested overflow, generation-capacity refusal.'],
      'contracts':['Each fresh Lease first Acquire belongs to one thread; concurrently acquiring the same Lease is unsupported.','Publish external Lease references only through normal thread synchronization; router/thread identity immutable after Acquire.','Selected() is owner-thread-only. Foreign release checks immutable identity before mutable active state.','Router, adapters, original functions, all callback code and contexts remain resident through process exit. No reset/unload/destructor cleanup is offered.','Generation capacity is 32, TLS adapter nesting capacity is 64; capacity exhaustion refuses observation/publication, never suppresses native forwarding.'],
      'limitations':['No proof that delayed old native work cannot enter as a new root and be selected onto the new generation.','No complete repeated-load owner, host-client room integration, game observer adapter, authority handoff, map cover, input hold, full world equality, or READY release.','Old dispatch bridge lacks a FINALLY callback and remains unsupported by the worker adapter.','Old Session and byte observers still use old slot mapping/Claim TLS; they cannot be directly attached to the new six-entry adapter.','Active counters and routed receipt balance are diagnostics, never native scheduler fences.'],
      'six_bridge_readonly_review':{'status':'No new ABI or cleanup blocker found in source delta review.','checked':['Six immutable slots and matching assembly slot IDs.','Original self-entry/call-helper refusal.','PIN failure terminal state rather than retry reset.','Before/After configurations require Finally.','Original ABI helper, stack allocation/unwind declarations, RAX/XMM0 forwarding unchanged in semantics.','Finally faults contained while unconditional TLS restore and active decrement remain in an outer Finally.'],'boundary':'Manual source delta review and owned-process combination tests; not game integration approval.'}
    }
    p=ROOT/'checkpoint_persistent_route_handoff.json';p.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'path':str(p),'sha256':sha(p)}))
if __name__=='__main__':main()
