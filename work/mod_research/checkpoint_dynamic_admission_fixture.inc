// Owned-process composition helper. All native game bodies remain doubles;
// hardware prefetch capture, ticket state and Controller itself are real.
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
    ns::Session* gameSession=nullptr;ad::Controller controller{};hw::Context hardware{};
    pd::Binding binding{};uintptr_t menu=0,user=0,manager=0,queue=0;
    std::uint64_t generation=0;bool revoked=false,authorized=false;
    unsigned authorizeCalls=0,queueCalls=0;
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
static void revokeAdmission(void*p) noexcept {auto&b=*static_cast<AdmissionBundle*>(p);b.revoked=true;b.authorized=false;}
static bool authorizeAdmission(void*p,const pd::Ticket&t,const CheckpointPushFrame&f,const void*controller) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);++b.authorizeCalls;
    la::Mapping m{};
    b.authorized=!b.revoked&&controller==&b.controller&&t.serial&&t.call_id==f.call_id&&
        t.binding.attempt==b.binding.attempt&&t.binding.attachment==b.binding.attachment&&t.binding.owner_generation==b.generation&&
        la::CurrentMapping(&m)&&m.logicalFrame==&f&&m.generation==b.generation&&m.stage==3;
    return b.authorized;
}
static pd::Span queueAdmission(void*p){
    auto&b=*static_cast<AdmissionBundle*>(p);check(b.authorized&&!b.revoked,"real private ticket precedes native queue double");
    if(!b.authorized||b.revoked)return {};
    b.authorized=false;++b.queueCalls;
    put<std::uint64_t>(b.manager+0x30,1);put<std::uint64_t>(b.manager+0x38,1);put<uintptr_t>(b.manager+0x40,b.queue);
    put<DWORD>(b.queue,0);put<uintptr_t>(b.queue+8,b.menu);
    return {reinterpret_cast<const std::uint8_t*>(b.menu),0x480};
}
static pd::Span resolveAdmissionQueue(void*p,uintptr_t address,std::size_t bytes) noexcept {
    auto&b=*static_cast<AdmissionBundle*>(p);
    return address==b.queue&&bytes==16?pd::Span{reinterpret_cast<const std::uint8_t*>(address),16}:pd::Span{};
}
static void attachAdmission(ns::Config&c){
    auto*b=new AdmissionBundle;admissionBundle=b;b->gameSession=currentSession;b->generation=generationIndex+1;
    b->menu=layout.config.menu;b->user=layout.config.states[4];b->manager=base+0x19E7310;b->queue=pending;
    b->binding.attempt.fill(BYTE(0xA1+generationIndex));b->binding.attachment.fill(0xB2);b->binding.owner_generation=b->generation;
    if(!generationIndex)check(ad::ConfigureForwardOriginal(&GuestSessionUserOriginal),"one immutable real User original");
    ad::Config ac{};ac.session={b,admissionStatus,bindAdmissionMenu};ac.generation=b->generation;ac.attempt=layout.config.attempt;
    ac.original=&GuestSessionUserOriginal;ac.expected_prefetch_site=uintptr_t(&HwbpFixtureBeforeCall);
    ac.authorize_queue=authorizeAdmission;ac.authorize_queue_context=b;ac.queue=queueAdmission;ac.queue_context=b;
    ac.revoke_queue=revokeAdmission;ac.revoke_queue_context=b;
    ac.next_before=c.userObservationBefore;ac.next_after=c.userObservationAfter;ac.next_finally=c.userObservationFinally;ac.next_context=c.userObservationContext;
    ac.pending.binding=b->binding;ac.pending.profile_base=base;memcpy(ac.pending.states,layout.config.states,sizeof ac.pending.states);
    const auto span=[](uintptr_t address,size_t size){return pd::Span{reinterpret_cast<const std::uint8_t*>(address),size};};
    ac.pending.user=span(b->user,0x668);ac.pending.toolbar=span(layout.toolbar,0x8C);ac.pending.game=span(layout.config.states[2],0x488);
    ac.pending.panel=span(layout.panel,0x1F8);ac.pending.manager=span(b->manager,0x50);ac.pending.stack=span(stackArray,0x30);
    ac.pending.load_cache=span(cache,0x3F4);ac.pending.expected_initial_cache_mode=0;
    ac.pending.resolve_created_queue=resolveAdmissionQueue;ac.pending.queue_resolver_context=b;
    put<std::uint64_t>(b->manager+0x30,0);put<std::uint64_t>(b->manager+0x38,0);put<uintptr_t>(b->manager+0x40,0);put<uintptr_t>(b->manager+0x48,b->user);put<DWORD>(cache+8,0);
    hw::Config hc{};hc.binding=b->binding;hc.site_rip=uintptr_t(&HwbpFixtureBeforeCall);
    check(hw::Initialize(b->hardware,hc),"fresh actual hardware context per generation");ac.prefetch_provider=hw::MakeProvider(b->hardware);
    check(b->controller.Initialize(ac)&&b->controller.ActivateForOfflineExercise(),"generation-bound input Controller activated in owned process only");
    c.userObservationBefore=ad::Controller::RoutedBefore;c.userObservationAfter=ad::Controller::RoutedAfter;c.userObservationFinally=ad::Controller::RoutedFinally;c.userObservationContext=&b->controller;
    c.context=b;c.userAfter=[](void*p,ns::Session&,const CheckpointPushFrame*f){static_cast<AdmissionBundle*>(p)->controller.SubmitUserAfter(f);};
    c.dispatchForwardTargets[0]=reinterpret_cast<void*>(&CheckpointPersistentAuthorizedOriginal);
}
static void verifyAdmission(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"input Controller report");
    if(r.error!=ad::Error::None)printf("ADMISSION error=%u before=%u after=%u prefetch=%u begin=%u commit=%u routes=%u\n",unsigned(r.error),unsigned(r.before.error),unsigned(r.after.error),unsigned(r.prefetch.error),unsigned(r.begin),unsigned(r.commit),r.route_faults);
    check(r.error==ad::Error::None&&r.menu_bound==1&&r.commit_succeeded==1&&r.queue_returned==1,"real Controller ticket commit and Session menu binding");
    check(r.prefetch.captured==1&&r.prefetch.restored==1&&r.prefetch.original_code_unchanged&&!r.prefetch.restore_uncertain,"actual CPU context captured and restored");
    check(!memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"all six debug registers exactly restored");
    check(!r.active&&!r.route_active&&!r.route_faults&&r.route_started==r.route_finished,"Controller per-call route drained");
    check(admissionBundle->authorizeCalls==1&&admissionBundle->queueCalls==1,"one authorization and queue per generation");
    printf("{\"admission_generation\":%llu,\"hardware_captured\":%u,\"restored\":%u,\"ticket_committed\":%u,\"menu_bound\":%u,\"route_active\":%u}\n",admissionBundle->generation,r.prefetch.captured,r.prefetch.restored,r.commit_succeeded,r.menu_bound,r.route_active);
}
static void verifyAdmissionAbnormal(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"abnormal input Controller report");
    check(r.error==ad::Error::Abnormal&&!r.active&&!r.route_active&&r.route_abnormal==1&&r.route_started==r.route_finished,"original exception drains actual Controller scope");
    check(r.prefetch.captured==1&&r.prefetch.finished==1&&r.prefetch.restored==1&&!r.prefetch.restore_uncertain&&r.prefetch.original_code_unchanged&&
        !memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"exception restores hardware context and native bytes");
    check(!r.menu_bound&&!r.commit_succeeded&&!admissionBundle->authorizeCalls&&!admissionBundle->queueCalls&&admissionBundle->revoked,"exception cannot grant or bind a load menu");
    printf("{\"admission_generation\":%llu,\"expected_abnormal\":true,\"hardware_captured\":%u,\"restored\":%u,\"ticket_committed\":%u,\"menu_bound\":%u,\"route_active\":%u}\n",admissionBundle->generation,r.prefetch.captured,r.prefetch.restored,r.commit_succeeded,r.menu_bound,r.route_active);
}
static void verifyAdmissionRejected(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"rejected input Controller report");
    check(r.error!=ad::Error::None&&r.blocked&&!r.active&&!r.route_active&&r.route_started==r.route_finished,"pending/prefetch refusal drains Controller scope");
    check(!r.menu_bound&&!r.commit_succeeded&&!admissionBundle->authorizeCalls&&!admissionBundle->queueCalls&&admissionBundle->revoked,"unclean input cannot authorize or queue a menu");
    check(r.prefetch.finished&&r.prefetch.restored&&!r.prefetch.restore_uncertain&&!memcmp(r.prefetch.original_dr,r.prefetch.restored_dr,sizeof r.prefetch.original_dr),"refusal still restores all hardware context");
    printf("{\"admission_generation\":%llu,\"expected_rejection\":true,\"error\":%u,\"hardware_captured\":%u,\"restored\":%u,\"ticket_committed\":%u,\"menu_bound\":%u,\"route_active\":%u}\n",admissionBundle->generation,unsigned(r.error),r.prefetch.captured,r.prefetch.restored,r.commit_succeeded,r.menu_bound,r.route_active);
}
static void verifyNoAdditionalAdmission(){
    ad::Report r{};check(admissionBundle->controller.Snapshot(r),"post-planning admission report");
    check(admissionBundle->authorizeCalls==1&&admissionBundle->queueCalls==1&&r.queue_returned==1&&r.menu_bound==1,"new planning User never queues another load");
    check(!r.active&&!r.route_active&&!r.route_faults&&r.route_started==r.route_finished,"new planning User forwarding drains route");
}
#define session (*currentSession)
