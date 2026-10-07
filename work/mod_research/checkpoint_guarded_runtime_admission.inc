// Owned-process composition helper. All native game bodies remain doubles;
// hardware prefetch capture, ticket state and Controller itself are real.
#include "checkpoint_dynamic_native_queue_bridge.h"
#include "checkpoint_native_queue_adapter_profile.h"
namespace dq=checkpoint_dynamic_native_queue;
namespace qa=checkpoint_native_queue_adapter;
#undef session
namespace ad=checkpoint_persistent_authorized;
namespace hw=checkpoint_persistent_input_hwbp;
namespace pd=checkpoint_bound_input_pending;
extern "C" {
uintptr_t HwbpFixtureUser=0;
struct HardwareFixtureSnapshot {std::uint64_t gpr[16]{},rflags=0,reserved=0;std::uint8_t xmm[256]{};DWORD mxcsr=0,reserved2[3]{};};
HardwareFixtureSnapshot HwbpFixtureBefore{},HwbpFixtureAfter{};
alignas(16) unsigned char HwbpFixtureSeed[256]{};
std::int32_t HwbpFixtureFetched=-999;
void HwbpFixtureSite();extern unsigned char HwbpFixtureBeforeCall;
}
struct AdmissionBundle {
    ns::Session* gameSession=nullptr;RuntimeGuardBundle* guards=nullptr;ad::Controller controller{};hw::Context hardware{};ad::Config prepared{};dq::Options options{};
    pd::Binding binding{};uintptr_t menu=0,user=0,manager=0,queue=0;
    std::uint64_t generation=0;dq::Bridge queueBridge{};uintptr_t image=0,localRoot=0,localWorld=0,list=0,dialog=0;
};
static AdmissionBundle* admissionBundle=nullptr;
static void runFixturePrefetch(std::uint64_t self){HwbpFixtureUser=uintptr_t(self);HwbpFixtureSite();}
static bool admissionStatus(void*p,ad::SessionStatus&out) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);ns::Report r{};b.gameSession->Snapshot(r);
    out.admissionReady=r.initialized&&r.armed;out.stopped=r.stopRequested!=0;out.error=r.error;return true;
}
static bool bindAdmissionMenu(void*p,const ad::QueueReceipt&r) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);
    ns::QueueReceipt q{r.attempt,r.userCall,r.thread,r.user,r.menu,r.nativeQueueReturned};
    return b.gameSession->BindQueuedMenu(q);
}
static pd::Ticket oldTicket{};
static bool externalQueueGuard(void*p,qa::Point point) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);
    return gd::Context::QueueGuard(&b.guards->context,point);
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
static void prepareAdmission(ns::Config&c){
    auto*b=new AdmissionBundle;admissionBundle=b;b->gameSession=currentSession;b->guards=runtimeGuards;b->generation=generationIndex+2;
    b->menu=layout.config.menu;b->user=layout.config.states[4];b->manager=base+0x19E7310;b->queue=pending;
    b->binding.attempt.fill(BYTE(0xA1+generationIndex));b->binding.attachment.fill(0xB2);b->binding.owner_generation=b->generation;
    if(!generationIndex)check(ad::ConfigureForwardOriginal(&GuestSessionUserOriginal),"one immutable real User original");
    ad::Config ac{};ac.session={b,admissionStatus,bindAdmissionMenu};ac.generation=b->generation;ac.attempt=layout.config.attempt;
    ac.original=&GuestSessionUserOriginal;ac.expected_prefetch_site=uintptr_t(&HwbpFixtureBeforeCall);

    ac.next_before=c.userObservationBefore;ac.next_after=c.userObservationAfter;ac.next_finally=c.userObservationFinally;ac.next_context=c.userObservationContext;
    ac.pending.binding=b->binding;ac.pending.profile_base=base;memcpy(ac.pending.states,layout.config.states,sizeof ac.pending.states);
    const auto span=[](uintptr_t address,size_t size){return pd::Span{reinterpret_cast<const std::uint8_t*>(address),size};};
    ac.pending.user=span(b->user,0x668);ac.pending.toolbar=span(layout.toolbar,0x8C);ac.pending.game=span(layout.config.states[2],0x488);
    ac.pending.panel=span(layout.panel,0x1F8);ac.pending.manager=span(b->manager,0x50);ac.pending.stack=span(stackArray,0x30);
    ac.pending.load_cache=span(cache,0x3F4);ac.pending.expected_initial_cache_mode=0;

    put<std::uint64_t>(b->manager+0x30,0);put<std::uint64_t>(b->manager+0x38,0);put<uintptr_t>(b->manager+0x40,0);put<uintptr_t>(b->manager+0x48,b->user);put<DWORD>(cache+8,0);
    put<std::uint64_t>(b->manager+0x18,6);
    b->image=base;b->localRoot=root;b->localWorld=world;b->list=at<uintptr_t>(b->menu+0x470);b->dialog=at<uintptr_t>(b->menu+0x478);
    for(const auto& anchor:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size);
    dq::Options qo{};qo.controller=&b->controller;qo.validate_external=externalQueueGuard;qo.external_context=b;
    qo.fixture_native=nativeQueueDouble;qo.fixture_user_caller=uintptr_t(&GuestSessionUserReturn);
    b->prepared=ac;b->options=qo;
    c.userObservationBefore=ad::Controller::RoutedBefore;c.userObservationAfter=ad::Controller::RoutedAfter;c.userObservationFinally=ad::Controller::RoutedFinally;c.userObservationContext=&b->controller;
    c.context=b;c.userAfter=[](void*p,ns::Session&,const CheckpointPushFrame*f){static_cast<AdmissionBundle*>(p)->controller.SubmitUserAfter(f);};
    c.dispatchForwardTargets[0]=reinterpret_cast<void*>(&CheckpointPersistentAuthorizedOriginal);
}
static void initializeAdmission(ns::Config&){
    auto*b=admissionBundle;auto&ac=b->prepared;
    check(b->queueBridge.Initialize(b->options,ac),"real queue Adapter initialized only after guards and owned bridge bootstrap");
    ac.authorize_queue=authorizeFaultInjection;ac.authorize_queue_context=b;
    hw::Config hc{};hc.binding=b->binding;hc.site_rip=uintptr_t(&HwbpFixtureBeforeCall);
    check(hw::Initialize(b->hardware,hc),"fresh actual hardware context per generation");ac.prefetch_provider=hw::MakeProvider(b->hardware);
    check(b->controller.Initialize(ac)&&b->controller.ActivateForOfflineExercise(),"generation-bound input Controller activated in owned process only");
}
static void verifyAdmission(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"input Controller report");auto debug=queueReport();printf("QUEUE err=%u stage=%u calls=%u auth=%u\n",unsigned(debug.error),unsigned(debug.stage),debug.native_calls,debug.authorized);
    if(r.error!=ad::Error::None)printf("ADMISSION error=%u before=%u after=%u prefetch=%u begin=%u commit=%u routes=%u\n",unsigned(r.error),unsigned(r.before.error),unsigned(r.after.error),unsigned(r.prefetch.error),unsigned(r.begin),unsigned(r.commit),r.route_faults);
    check(r.error==ad::Error::None&&r.menu_bound==1&&r.commit_succeeded==1&&r.queue_returned==1,"real Controller ticket commit and Session menu binding");
    check(r.prefetch.captured==1&&r.prefetch.restored==1&&r.prefetch.original_code_unchanged&&!r.prefetch.restore_uncertain,"actual CPU context captured and restored");
    check(!memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"all six debug registers exactly restored");
    check(!r.active&&!r.route_active&&!r.route_faults&&r.route_started==r.route_finished,"Controller per-call route drained");
    check(queueReport().authorized==1&&queueReport().native_calls==1&&queueReport().resolver_calls==1&&queueReport().native_result_verified==1,"one authorization and queue per generation");
    printf("{\"admission_generation\":%llu,\"hardware_captured\":%u,\"restored\":%u,\"ticket_committed\":%u,\"menu_bound\":%u,\"route_active\":%u}\n",admissionBundle->generation,r.prefetch.captured,r.prefetch.restored,r.commit_succeeded,r.menu_bound,r.route_active);
}
static void verifyAdmissionAbnormal(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"abnormal input Controller report");
    check(r.error==ad::Error::Abnormal&&!r.active&&!r.route_active&&r.route_abnormal==1&&r.route_started==r.route_finished,"original exception drains actual Controller scope");
    check(r.prefetch.captured==1&&r.prefetch.finished==1&&r.prefetch.restored==1&&!r.prefetch.restore_uncertain&&r.prefetch.original_code_unchanged&&
        !memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"exception restores hardware context and native bytes");
    check(!r.menu_bound&&!r.commit_succeeded&&!queueReport().authorized&&!queueReport().native_calls&&queueReport().stopped,"exception cannot grant or bind a load menu");
    printf("{\"admission_generation\":%llu,\"expected_abnormal\":true,\"hardware_captured\":%u,\"restored\":%u,\"ticket_committed\":%u,\"menu_bound\":%u,\"route_active\":%u}\n",admissionBundle->generation,r.prefetch.captured,r.prefetch.restored,r.commit_succeeded,r.menu_bound,r.route_active);
}
static void verifyAdmissionRejected(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"rejected input Controller report");
    check(r.error!=ad::Error::None&&r.blocked&&!r.active&&!r.route_active&&r.route_started==r.route_finished,"pending/prefetch refusal drains Controller scope");
    check(!r.menu_bound&&!r.commit_succeeded&&!queueReport().authorized&&!queueReport().native_calls&&queueReport().stopped,"unclean input cannot authorize or queue a menu");
    check(r.prefetch.finished&&r.prefetch.restored&&!r.prefetch.restore_uncertain&&!memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"refusal still restores all hardware context");
    printf("{\"admission_generation\":%llu,\"expected_rejection\":true,\"error\":%u,\"hardware_captured\":%u,\"restored\":%u,\"ticket_committed\":%u,\"menu_bound\":%u,\"route_active\":%u}\n",admissionBundle->generation,unsigned(r.error),r.prefetch.captured,r.prefetch.restored,r.commit_succeeded,r.menu_bound,r.route_active);
}
static void verifyNoAdditionalAdmission(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"post-planning admission report");
    check(queueReport().authorized==1&&queueReport().native_calls==1&&queueReport().resolver_calls==1&&queueReport().native_result_verified==1&&r.queue_returned==1&&r.menu_bound==1,"new planning User never queues another load");
    check(!r.active&&!r.route_active&&!r.route_faults&&r.route_started==r.route_finished,"new planning User forwarding drains route");
}
static void verifyQueueNegative(){
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
    printf("{\"queue_generation\":%llu,\"native_calls\":%u,\"error\":%u,\"stopped\":true}\n",admissionBundle->generation,q.native_calls,unsigned(q.error));
}
#define session (*currentSession)
