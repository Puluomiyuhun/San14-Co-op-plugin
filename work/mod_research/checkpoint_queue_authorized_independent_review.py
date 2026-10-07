"""Read-only workspace evidence audit; no process, Steam, build or test execution."""
from datetime import datetime
import hashlib
import json
from pathlib import Path

P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))

def main():
    qpath=P/'checkpoint_native_queue_adapter_handoff.json'
    apath=P/'checkpoint_authorized_forward_admission_handoff.json'
    queue=read(qpath);authorized=read(apath);checks={}
    for prefix,h in [('queue',queue),('authorized',authorized)]:
        for name,digest in h['source_sha256'].items():checks[prefix+':source:'+name]=sha(P/name)==digest
    for name,digest in queue['artifact_sha256'].items():checks['queue:artifact:'+name]=sha(P/name)==digest
    qp=P/queue['own_process_tests']['path'];ap=Path(authorized['fixture_report'])
    checks['queue:report']=sha(qp)==queue['own_process_tests']['sha256']
    checks['authorized:report']=sha(ap)==authorized['fixture_report_sha256']
    for name,key in [('checkpoint_authorized_forward_admission_fixture.exe','fixture_binary_sha256'),
                     ('checkpoint_authorized_forward_admission_production.obj','production_controller_object_sha256'),
                     ('checkpoint_authorized_forward_admission_session_production.obj','production_session_object_sha256'),
                     ('checkpoint_authorized_forward_admission_notes.txt','notes_sha256'),
                     ('checkpoint_authorized_forward_admission_delta.txt','normalized_minimal_delta_sha256'),
                     ('checkpoint_live_runtime_guard_plan.json','runtime_guard_plan_sha256')]:
        checks['authorized:artifact:'+name]=sha(P/name)==authorized[key]
    qr=read(qp);ar=read(ap)
    checks['queue:20_cases']=qr['passed'] and len(qr['cases'])==20 and all(x['passed'] for x in qr['cases'])
    checks['authorized:14_cases']=ar['result']=='PASS' and len(ar['cases'])==14 and all(x['passed'] for x in ar['cases'])
    checks['authorized:unchanged_sources']=ar['source_unchanged_during_build_and_run'] is True
    cases={x['case']:x for x in ar['cases']}
    for case in ['stop-after-authorize','block-after-authorize']:
        row=cases[case];checks['unused_authorization_revoked:'+case]=row['adapter_authorized']==1 and row['adapter_stopped'] is True and row['adapter_native_calls']==0 and row['cas']==0
    checks['exception_no_retry']=cases['queue-exception']['adapter_native_calls']==1 and cases['queue-exception']['cas']==0 and cases['late-replay']['adapter_native_calls']==1
    checks['direct_private_ticket_handoff']=all(cases[n]['exact_ticket_frame']==1 for n in ['success-new','cross-thread-both','stop-after-authorize','wrong-call-authorize'])
    plan=read(P/'checkpoint_live_runtime_guard_plan.json')
    targets=[s for s in plan['assembly_requirements'] if 'dispatchForwardTargets[0]=' in s]
    checks['plan:authorized_target']=len(targets)==1 and 'CheckpointAuthorizedForwardAdmissionOriginal' in targets[0]
    checks['plan:serialization_thunk']=bool(plan['validator_dependency_graph'].get('concurrent_storage_validation'))
    profile=read(P/'checkpoint_native_queue_adapter_profile.json');image=(P/'game-runtime-image.bin').read_bytes()
    checks['archive:image_sha']=hashlib.sha256(image).hexdigest()==profile['image_sha256']
    for anchor in profile['anchors']:
        raw=bytes.fromhex(anchor['bytes']);start=anchor['rva']
        checks['archive:anchor:'+hex(start)]=image[start:start+len(raw)]==raw
    findings=[
        {'status':'REVIEWED','item':'Private ticket/frame transfer','evidence':'Controller UserAfter obtains a Ticket from its private paired pending adapter, consumes queue_once, then hands the actual Ticket/frame/&Controller directly to required authorize_queue. Adapter checks configured identity, binding/call/thread/return-site; it explicitly does not independently authenticate public Ticket values. Same Ticket returns to private Commit.'},
        {'status':'REQUIRED_OWNER_CONTRACT','item':'Unused authorization retirement','evidence':'Controller Stop/blocked after Authorize success may leave adapter authorization unconsumed. Owner must Adapter.Stop on aborted authorization/attempt retirement in addition to Controller/Session Stop. Actual composition fixture Close trace + owner Stop wrapper revoke it; both cases prove native_calls=0/CAS=0. A future carrier that omits this is not covered.'},
        {'status':'REVIEWED','item':'Once and exception boundaries','evidence':'Queue capability is consumed before native invocation; may_have_queued is set before the call. C++ and SEH exceptions are recorded/rethrown by Adapter, caught as terminal by controller, and never retried/undone. Stop is a request, not a fence or cancellation of native side effects.'},
        {'status':'REVIEWED','item':'Allocation and pending checks','evidence':'Exact pre-native header must match frozen authorized pointer/capacity. Count0/cap0 grows to64 entries according to archived recipe. Returned full capacity*16 span and 0x4C0 Menu are checked for readability, identity, aliasing, stack/cache/mode and stable repeated headers. Same adapter resolves exact pointer/extent once after native return.'},
        {'status':'CORRECTED_DOCUMENTATION','item':'Entry target naming','evidence':'Guard-plan assembly requirement now uses CheckpointAuthorizedForwardAdmissionOriginal; old BoundForward entry would omit the mandatory authorization callback. Compiled sources were not changed for this documentation correction.'},
        {'status':'REQUIRED_OWNER_CONTRACT','item':'Naturally concurrent storage validation','evidence':'Load/main and FileRead/worker may concurrently validate. Owner must serialize every Context.Valid entrance, including Api.validate thunk, and reject same-thread recursion before waiting. Lock inside checkOwner would be too late. Lock must not cross native original/queue/Steam call, worker join or Session Snapshot. This is validator serialization only, not input exclusion.'},
    ]
    output={'schema':'san14.queue-authorized-independent-review.v1','result':'NO_NEW_BLOCKER_IN_REVIEWED_OFFLINE_SCOPE' if all(checks.values()) else 'EVIDENCE_MISMATCH',
            'reviewer':'native_save_entry','queue_handoff':str(qpath),'queue_handoff_sha256':sha(qpath),'authorized_handoff':str(apath),'authorized_handoff_sha256':sha(apath),
            'checks':checks,'findings':findings,'game_access':False,'process_access':False,'tests_rerun':False,'frozen_sources_modified':False,
            'limits':['Native queue body is a fixture double; no live 411980 invocation was reviewed or performed here.',
                      'Native cache clear in the actual constructor is a real future side effect; the owner must approve its ownership/lifetime and retain any uncertain result.',
                      'No complete production owner/runtime validator, persistent intent, full-world equality, input/render barrier or actual multiplayer READY is established.',
                      'VirtualQuery and repeated reads do not lock native object lifetime or provide a scheduler fence.',
                      'Source hashes are matched to existing author-run tests; reviewer did not rerun the suites.']}
    dest=P/('checkpoint_queue_authorized_independent_review_'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
    dest.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'path':str(dest),'sha256':sha(dest),'checks':len(checks),'failed':[k for k,v in checks.items() if not v],'result':output['result']}))
    raise SystemExit(not all(checks.values()))

if __name__=='__main__':main()
