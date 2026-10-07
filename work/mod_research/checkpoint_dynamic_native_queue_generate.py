raise SystemExit("Historical derivation draft; do not rerun over reviewed source files")
from pathlib import Path
p=Path('work/mod_research')
s=(p/'checkpoint_dynamic_admission_fixture.inc').read_text()
s=s.replace('#undef session','#include "checkpoint_dynamic_native_queue_bridge.h"\n#include "checkpoint_native_queue_adapter_profile.h"\nnamespace dq=checkpoint_dynamic_native_queue;\nnamespace qa=checkpoint_native_queue_adapter;\n#undef session')
s=s.replace('std::uint64_t generation=0;bool revoked=false,authorized=false;\n    unsigned authorizeCalls=0,queueCalls=0;', 'std::uint64_t generation=0;dq::Bridge queueBridge{};uintptr_t image=0,localRoot=0,localWorld=0,list=0,dialog=0;')
a=s.index('static void revokeAdmission(');b=s.index('static void attachAdmission(',a)
s=s[:a]+'''static pd::Ticket oldTicket{};
static bool externalQueueGuard(void*p,qa::Point) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);
    return b.image&&b.localRoot&&b.localWorld&&at<uintptr_t>(b.image+0x2025318)==layout.config.cache&&b.gameSession==currentSession;
}
static bool authorizeFaultInjection(void*p,const pd::Ticket&t,const CheckpointPushFrame&f,const void*c) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);auto candidate=t;
    if(scenario==L"queue-wrong-generation")++candidate.binding.owner_generation;
    if(scenario==L"queue-stale-ticket")candidate=oldTicket;
    if(scenario==L"queue-wrong-controller")c=&b;
    if(scenario==L"queue-copied-frame"){auto copy=f;return dq::Bridge::Authorize(&b.queueBridge,candidate,copy,c);}
    const bool ok=dq::Bridge::Authorize(&b.queueBridge,candidate,f,c);oldTicket=t;
    if(scenario==L"queue-stop-authorized")b.controller.Stop();
    return ok;
}
static void nativeQueueDouble(void* manager,const char* name,void* mode,void* closureArg){
    auto&b=*admissionBundle;check(uintptr_t(manager)==b.manager&&uintptr_t(name)==b.image+0x12DD6E0&&!strcmp(name,"CSaveLoadState"),"actual adapter native call recipe");
    const unsigned char zero[64]{};check(!memcmp(mode,zero,8)&&!memcmp(closureArg,zero,64),"actual native arguments mode and closure");
    put<std::uint64_t>(b.manager+0x30,1);put<std::uint64_t>(b.manager+0x38,64);put<uintptr_t>(b.manager+0x40,b.queue);
    put<DWORD>(b.queue,0);put<uintptr_t>(b.queue+8,b.menu);
    for(auto offset:{0x48,0x50,0x68,0x470,0x478})put<uintptr_t>(b.menu+offset,0);
    if(scenario==L"queue-stop-native")b.controller.Stop();
    if(scenario==L"queue-native-exception")RaiseException(0xE014D001,0,0,nullptr);
}
static void restoreMenuUiDouble(){auto&b=*admissionBundle;put<uintptr_t>(b.menu+0x470,b.list);put<uintptr_t>(b.menu+0x478,b.dialog);}
static qa::Report queueReport(){dq::Report r{};check(admissionBundle->queueBridge.Snapshot(r),"actual queue adapter report");return r.native;}
''' +s[b:]
s=s.replace('    ac.authorize_queue=authorizeAdmission;ac.authorize_queue_context=b;ac.queue=queueAdmission;ac.queue_context=b;\n    ac.revoke_queue=revokeAdmission;ac.revoke_queue_context=b;','')
s=s.replace('    ac.pending.resolve_created_queue=resolveAdmissionQueue;ac.pending.queue_resolver_context=b;','')
needle='    hw::Config hc{};'
insert='''    b->image=base;b->localRoot=root;b->localWorld=world;b->list=at<uintptr_t>(b->menu+0x470);b->dialog=at<uintptr_t>(b->menu+0x478);
    for(const auto& anchor:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size);
    dq::Options qo{};qo.controller=&b->controller;qo.validate_external=externalQueueGuard;qo.external_context=b;
    qo.fixture_native=nativeQueueDouble;qo.fixture_user_caller=uintptr_t(&GuestSessionUserReturn);
    check(b->queueBridge.Initialize(qo,ac),"real native queue Adapter bound to same generation pending config");
    ac.authorize_queue=authorizeFaultInjection;ac.authorize_queue_context=b;
'''
s=s.replace(needle,insert+needle)
s=s.replace('admissionBundle->authorizeCalls==1&&admissionBundle->queueCalls==1','queueReport().authorized==1&&queueReport().native_calls==1&&queueReport().resolver_calls==1&&queueReport().native_result_verified==1')
s=s.replace('!admissionBundle->authorizeCalls&&!admissionBundle->queueCalls&&admissionBundle->revoked','!queueReport().authorized&&!queueReport().native_calls&&queueReport().stopped')
s=s.replace('#define session (*currentSession)','''static void verifyQueueNegative(){
    ad::Report r{};admissionBundle->controller.Snapshot(r);auto q=queueReport();
    const bool native=scenario==L"queue-native-exception"||scenario==L"queue-stop-native";
    check(r.error!=ad::Error::None&&!r.menu_bound&&!r.commit_succeeded&&!r.active&&!r.route_active,"real Adapter rejection blocks menu binding and drains Controller");
    check(q.stopped&&q.native_calls==unsigned(native)&&!q.native_result_verified&&!q.resolver_calls,"rejection or uncertain native result never resolves queue");
    check(r.prefetch.restored&&!r.prefetch.restore_uncertain&&!memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"negative path restores exact debug registers");
    if(native)check(q.may_have_queued&&q.queue_capability_consumed&&at<std::uint64_t>(admissionBundle->manager+0x30)==1,"uncertain queue retained without undo");
    if(scenario==L"queue-native-exception")check(q.error==qa::Error::NativeException&&!q.native_returned,"real Adapter records native exception");
    if(scenario==L"queue-wrong-generation"||scenario==L"queue-stale-ticket")check(q.error==qa::Error::Ticket,"real Adapter rejects wrong generation or stale ticket");
    if(scenario==L"queue-wrong-controller")check(q.error==qa::Error::Controller,"real Adapter rejects wrong Controller");
    GuestSessionUserInvoke(admissionBundle->user,1,2,3);
    check(queueReport().native_calls==q.native_calls,"later User never retries rejected or uncertain queue");
    printf("{\\"queue_generation\\":%llu,\\"native_calls\\":%u,\\"error\\":%u,\\"stopped\\":true}\\n",admissionBundle->generation,q.native_calls,unsigned(q.error));
}
#define session (*currentSession)''')
(p/'checkpoint_dynamic_native_queue_fixture.inc').write_text(s)
f=(p/'checkpoint_dynamic_complete_fixture.cpp').read_text().replace('checkpoint_dynamic_admission_fixture.inc','checkpoint_dynamic_native_queue_fixture.inc')
f=f.replace('++menuBodies;check(self==layout.config.menu,"original Menu");','++menuBodies;check(self==layout.config.menu,"original Menu");restoreMenuUiDouble();')
needle='    if(scenario==L"user-exception"){' # only runGeneration occurrence? body uses equality different
f=f.replace(needle,'''    if(scenario.rfind(L"queue-",0)==0){
        GuestSessionUserInvoke(layout.config.states[4],1,2,3);verifyQueueNegative();
        ns::Report rejected{};session.Snapshot(rejected);check(!rejected.menuBound&&!rejected.casPublished,"queue failure never publishes load request");return finishReport(rejected,true);
    }
'''+needle)
f=f.replace('std::wstring caseName=i&&first!=L"alternate-factions"?L"success":first;','std::wstring caseName=first==L"queue-stale-ticket"?(i?first:L"success"):(i&&first!=L"alternate-factions"?L"success":first);')
(p/'checkpoint_dynamic_native_queue_fixture.cpp').write_text(f)
t=(p/'checkpoint_dynamic_complete_test.py').read_text().replace('checkpoint_dynamic_complete_fixture','checkpoint_dynamic_native_queue_fixture').replace('checkpoint_dynamic_admission_fixture.inc','checkpoint_dynamic_native_queue_fixture.inc').replace('checkpoint_dynamic_complete_test.py','checkpoint_dynamic_native_queue_test.py').replace('checkpoint_dynamic_complete_runs','checkpoint_dynamic_native_queue_runs')
t=t.replace("UNITS=['", "UNITS=['checkpoint_native_queue_adapter_core','checkpoint_dynamic_native_queue_bridge','")
t=t.replace("DEFS='", "DEFS='/DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE ")
a=t.index('CASES=');b=t.index('\n',a)
t=t[:a]+"CASES=['success','queue-wrong-generation','queue-stale-ticket','queue-wrong-controller','queue-copied-frame','queue-stop-authorized','queue-stop-native','queue-native-exception','user-exception','input-pending','input-missing-prefetch']"+t[b:]
t=t.replace('checkpoint_persistent_planning_observer.cpp\')','checkpoint_dynamic_native_queue_bridge.cpp\')')
t=t.replace("sources.update([", "sources.update(['checkpoint_native_queue_adapter_profile.h',")
t=t.replace("'san14.dynamic-complete-core-integration.v1'", "'san14.dynamic-native-queue-integration.v1'")
t=t.replace('Native queue/load/file-read/title bodies are synthetic.', 'Native QueueMenu/load/file-read/title bodies are synthetic; queue authorization, validation, span resolution, Stop and native exception handling use the frozen real native queue Adapter through the new per-generation bridge.')
(p/'checkpoint_dynamic_native_queue_test.py').write_text(t)
