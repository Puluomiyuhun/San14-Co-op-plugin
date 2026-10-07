"""Freeze per-call controller routing, not game or scheduling authority."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    evidence=ROOT/'checkpoint_persistent_authorized_runs/20261007-173714-124032/result.json'
    test=json.loads(evidence.read_text());assert test['passed'] and len(test['cases'])==20
    for n,h in test['source_sha256'].items():assert sha(ROOT/n)==h,n
    handoff={
      'schema':'san14.persistent-authorized.handoff.v1','offline_passed':True,'case_count':20,
      'evidence':{'path':str(evidence),'sha256':sha(evidence)},'source_sha256':test['source_sha256'],
      'derivation_inputs_sha256':{n:sha(ROOT/n) for n in ('checkpoint_authorized_forward_admission_controller.h','checkpoint_authorized_forward_admission_controller.cpp','checkpoint_authorized_forward_admission_bridge.asm','checkpoint_persistent_authorized_generate.py')},
      'production_obj_sha256':test['production_obj_sha256'],
      'game_access':False,'steam_access':False,'production_admission':False,'native_scheduler_fence':False,
      'interfaces':{
        'namespace':'checkpoint_persistent_authorized',
        'wrapper':'CheckpointPersistentAuthorizedOriginal; four integer register arguments, full RAX/XMM0 return.',
        'configure':'ConfigureForwardOriginal(native_original) once before hook publication; pins module; no reset.',
        'config':'SessionPort{context,status,bind_menu}; generation==pending.binding.owner_generation==logical route generation; immutable original must equal wrapper fixed original.',
        'callbacks':'Session.userObservationBefore/After/Finally -> Controller::RoutedBefore/RoutedAfter/RoutedFinally.',
        'submission':'Session.userAfter calls controller.SubmitUserAfter(frame), after RoutedAfter and before RoutedFinally.',
        'session_status':'admissionReady means initialized/armed generation accepts this owned attempt, separate stopped/error fields; it is not a UI scheduling fence.',
        'queue':'mandatory authorize_queue private-ticket handoff; queue callback; idempotent any-thread revoke_queue closes only this generation capability.',
        'activation':'ActivateForOfflineExercise is compiled to false without CHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE.'
      },
      'routing_contract':[
        'Each observed User BEFORE creates a thread-local call scope storing its immutable controller.',
        'Native wrapper validates logical mapping generation, frame address, call/thread, native stage and arguments; it never selects a mutable global last controller.',
        'The fixed global is only the native original function target. Calls without a valid admission observation still forward that target once, without admission.',
        'Scope remains alive through Session.userAfter and is removed in RoutedFinally. Original unwind preserves exception and releases running state.',
        'Missing/aborted AFTER or submission is terminal for that generation; cleanup does not fabricate a successful pending Close.',
        'Stop and fail revoke this generation queue capability without canceling an already submitted native queue entry.',
        'All controllers, adapters, callback targets and contexts remain resident to process exit.'
      ],
      'tested':[
        'Actual MASM original wrapper plus six-entry bridge, immutable router and logical adapter, not hand-fabricated route callbacks.',
        'Two generations, nested cutover, active old call with new thread/generation, delayed new roots, and four threads with 4000 calls.',
        'Native SEH/C++ propagation; nested unwind; error in first generation does not poison the second.',
        'Full 64-bit RAX and 128-bit XMM0 forwarding.',
        'Wrong generation/binding, wrong Submit timing, recursive forward target and direct native wrapper reentry rejection.',
        'Finally observer SEH clears TLS and blocks its own generation.',
        'Production object compiled without fixture macro and executed to verify activation remains false.'
      ],
      'limitations':[
        'Provider and SessionPort in these routing fixtures are explicit doubles. No successful hardware prefetch, private-ticket queue execution, complete Session load, or game data deserialization is claimed here.',
        'The invalid-admission case uses the actual pending core and a refusing provider; success integration is a separate task.',
        'Original production profile checks are only adapted in the fixture build. Production activation has no implemented authorization path.',
        'Routing isolation is not proof that old native work cannot enter after a generation switch. No live switch is permitted by these results.',
        'Fixture mode switching, current pointers and synthetic native original bodies are test controls, never network or game authority.'
      ],
      'independent_review':{'reviewer':'repeatability_audit','result':'No substantive old-call-to-new-controller defect found in read-only TLS wrapper review.','scope':'fixedOriginal once publication; generation/frame/call/thread/stage selected scope; exceptional running reset and Finally cleanup; overflow forwarding; Stop/fail queue revoke outside report lock; production activation false.','not_certified':'SessionPort/provider provenance, callback/context lifetimes or native scheduler fence.'}
    }
    p=ROOT/'checkpoint_persistent_authorized_handoff.json';p.write_text(json.dumps(handoff,indent=2),encoding='utf-8');print(json.dumps({'path':str(p),'sha256':sha(p)}))
if __name__=='__main__':main()
