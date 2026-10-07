// Owned fixture adapters only. No fabricated successful upstream receipt: all
// report fields below are copied from the actual dynamic Session just run.
namespace pr=checkpoint_persistent_planning;
struct PlanningFixtureContext {
    ns::Session* actual=nullptr;pr::Observer* observer=nullptr;RuntimeGuardBundle* guards=nullptr;
    std::uint64_t epoch=0,generation=0;std::wstring caseName;
    unsigned producedReads=0;uintptr_t newUser=0;
};
static PlanningFixtureContext* planningContext=nullptr;
static unsigned planningBodies=0;
static bool planningSource(void*p,pr::Source&out)noexcept{
    auto&c=*static_cast<PlanningFixtureContext*>(p);ns::Report r{};c.actual->Snapshot(r);
    out.attempt=r.attempt;out.epoch=c.epoch;out.generation=c.generation;
    out.initialized=r.initialized;out.casPublished=r.casPublished;out.mayHavePublished=r.mayHavePublished;
    out.stopRequested=r.stopRequested;out.sessionError=r.error;
    static_assert(sizeof out.request==sizeof r.request&&sizeof out.bytes==sizeof r.bytes&&sizeof out.lifecycle==sizeof r.lifecycle);
    static_assert(std::is_trivially_copyable_v<decltype(r.request)>&&std::is_trivially_copyable_v<decltype(r.bytes)>&&std::is_trivially_copyable_v<decltype(r.lifecycle)>);
    memcpy(&out.request,&r.request,sizeof out.request);memcpy(&out.bytes,&r.bytes,sizeof out.bytes);memcpy(&out.lifecycle,&r.lifecycle,sizeof out.lifecycle);
    static_assert(offsetof(ti::Report,capturedSource47)==offsetof(checkpoint_title_identity_adapter::Report,originalXmm0));
    memcpy(&out.identity,&r.identity,offsetof(ti::Report,capturedSource47));out.identity.size=sizeof out.identity;
    memcpy(out.identity.originalXmm0,r.identity.originalXmm0,sizeof out.identity.originalXmm0);memcpy(out.identity.commitStage,r.identity.commitStage,sizeof out.identity.commitStage);
    // Negative controls alter only this transfer copy, never Session state.
    if(r.identity.receiptReady){++c.producedReads;
        if(c.caseName==L"planning-source-generation"||(c.caseName==L"planning-source-drift"&&c.producedReads>1))++out.generation;
        if(c.caseName==L"planning-missing-join")out.lifecycle.joinReturned=0;
    }
    return true;
}
static bool planningGuard(void*p,pr::Point point,const CheckpointPushFrame&f,std::uint64_t attempt,std::uint64_t epoch,std::uint64_t generation)noexcept{
    auto&c=*static_cast<PlanningFixtureContext*>(p);
    return gd::Context::PlanningGuard(&c.guards->context,point,f,attempt,epoch,generation);
}
static void configurePlanning(ns::Config&c){
    planningContext=new PlanningFixtureContext;auto&context=*planningContext;
    context.actual=currentSession;context.guards=runtimeGuards;context.observer=new pr::Observer;context.epoch=17+generationIndex;context.generation=generationIndex+2;context.caseName=scenario;
    pr::Config config{};config.base=base;config.persistentRootState=layout.config.states[0];config.persistentMotorState=layout.config.states[1];config.previousUser=layout.config.states[4];
    config.attempt=layout.config.attempt;config.epoch=context.epoch;config.generation=context.generation;
    config.expected={worldProfile.year,worldProfile.month,worldProfile.day,worldProfile.target.force,worldProfile.target.ruler,worldProfile.target.district,fileProfile.size,{}};
    memcpy(config.expected.sha256,fileProfile.sha256,32);if(scenario==L"planning-wrong-hash")config.expected.sha256[0]^=1;
    config.source=planningSource;config.sourceContext=&context;config.validate=planningGuard;config.context=&context;config.fixtureCaller=uintptr_t(&GuestSessionUserReturn);
    check(pr::Initialize(*context.observer,config),"planning observer uses immutable actual Session provider");
    check(!pr::Initialize(*context.observer,config),"same generation observer cannot be reset");
    c.userObservationBefore=pr::Before;c.userObservationAfter=pr::After;c.userObservationFinally=pr::Finally;c.userObservationContext=context.observer;
}
static void rebuildPlanningForFixture(){
    // Explicit native constructor double. It never writes any core receipt.
    auto&c=*planningContext;DWORD old=0;
    const bool reuse=scenario==L"planning-reuse-load";
    if(reuse){check(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_READWRITE,&old)!=0,"reuse destroyed Load allocation");memset(reinterpret_cast<void*>(load),0,4096);}
    const auto game=reuse?load:alloc(4096),strategy=alloc(4096);c.newUser=alloc(4096);
    uintptr_t states[]={layout.config.states[0],layout.config.states[1],game,strategy,c.newUser};
    const uintptr_t vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    for(unsigned i=0;i<5;++i){put<uintptr_t>(stackArray+i*8,states[i]);put<uintptr_t>(states[i],base+vt[i]);memcpy(reinterpret_cast<void*>(states[i]+0x70),names[i],strlen(names[i])+1);put<DWORD>(states[i]+0x68,0);put<uintptr_t>(states[i]+0x50,0);}
    const auto manager=base+0x19E7310;put<std::uint64_t>(manager+0x10,5);put<std::uint64_t>(manager+0x30,0);put<uintptr_t>(manager+0x48,c.newUser);
    put<DWORD>(c.newUser+0x470,2);put<DWORD>(c.newUser+0x6C,3);
    auto worker=alloc(4096),callable=worker+0x100,iterator=worker+0x200,handle=worker+0x300;
    put<uintptr_t>(c.newUser+0x50,worker);put<uintptr_t>(worker+8,handle);put<uintptr_t>(worker+0x50,callable);put<DWORD>(handle+0x10,GetCurrentThreadId());
    put<uintptr_t>(callable,base+0x12F2440);put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(callable+8,iterator);put<uintptr_t>(iterator,stackArray+32);
    for(unsigned i=1;i<4;++i)put<std::uint64_t>(callable+8+i*8,0x1000+i);
    const auto toolbar=alloc(4096),panel=alloc(4096),gamePanel=alloc(4096);
    put<uintptr_t>(c.newUser+0x478,toolbar);put<uintptr_t>(c.newUser+0x618,panel);put<LONG>(toolbar+0x88,-1);put<uintptr_t>(game+0x480,gamePanel);
    put<DWORD>(base+0x1A38EC8+0x28,0);put<DWORD>(base+0x19E7510+0x13C,1);put<DWORD>(base+0x1FCA518,worldProfile.target.force);
    put<LONG>(base+0x201ED10,-1);sso(base+0x201ED18,"");sso(base+0x201ED38,"");
    if(scenario==L"planning-wrong-date")put<BYTE>(world+0x37,1);
    if(scenario==L"planning-wrong-district")put<BYTE>(personB+0x118,BYTE(worldProfile.target.district+1));
    if(scenario==L"planning-old-report"){const auto report=alloc(4096);memcpy(reinterpret_cast<void*>(report+0x70),"CReportDisplayState",20);put<uintptr_t>(stackArray+40,report);put<std::uint64_t>(manager+0x10,6);}
}
static bool invokePlanningForFixture(){
    __try {check(GuestSessionUserInvoke(planningContext->newUser,0x1001,0x1002,0x1003)==0xFEDCBA9876543210ull,"same persistent bridge preserves native new User return");return false;}
    __except(GetExceptionCode()==0xE014CCAE?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}
}
static void observePlanningForFixture(bool identityPass){
    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(title),0x2000,PAGE_NOACCESS,&old)!=0,"historical Title is unreadable before planning");
    rebuildPlanningForFixture();const bool caught=invokePlanningForFixture();pr::Report r{};pr::Snapshot(*planningContext->observer,r);
    const bool rejected=scenario==L"planning-wrong-date"||scenario==L"planning-wrong-district"||scenario==L"planning-wrong-hash"||scenario==L"planning-source-generation"||scenario==L"planning-missing-join"||scenario==L"planning-source-drift"||scenario==L"planning-native-exception"||scenario==L"planning-old-report";
    check(bool(r.planningBoundaryObserved)==(identityPass&&!rejected),"actual dynamic Session receipt controls planning observation");
    check(planningBodies==1,"one actual new User native original runs");
    check(!r.fullWorldVerified&&!r.inputExclusionProven&&!r.pixelPresentationProven&&!r.allWorkersFinishedProven,"planning is observation, not global authorization");
    if(identityPass&&!rejected){check(r.expected.year==worldProfile.year&&r.expected.day==worldProfile.day&&r.expected.force==worldProfile.target.force&&r.expected.ruler==worldProfile.target.ruler&&r.expected.district==worldProfile.target.district&&r.expected.byteSize==fileProfile.size&&!memcmp(r.expected.sha256,fileProfile.sha256,32),"dynamic world/checkpoint projection binds current generation");check(!r.error&&!r.inFlight&&r.nativeReturned,"same-call observer completion");}
    if(scenario==L"planning-native-exception")check(caught&&r.inFlight==1&&!r.nativeReturned,"native User exception preserved without fabricated AFTER");
    if(scenario==L"planning-wrong-date")check(r.error==LONG(pr::Error::Epoch),"wrong date rejected");
    if(scenario==L"planning-wrong-district")check(r.error==LONG(pr::Error::Epoch),"wrong ruler district rejected");
    if(scenario==L"planning-wrong-hash"||scenario==L"planning-source-generation"||scenario==L"planning-source-drift"||scenario==L"planning-missing-join")check(r.error==LONG(pr::Error::Receipt),"produced upstream receipt contradiction rejected");
    if(scenario==L"planning-old-report")check(r.error==LONG(pr::Error::Epoch),"report state is not planning");
    printf("{\"planning_case\":\"%ls\",\"generation\":%llu,\"observed\":%u,\"error\":%ld,\"field\":\"%s\",\"actual_session_provider\":true,\"full_world_verified\":false}\n",scenario.c_str(),r.generation,r.planningBoundaryObserved,r.error,r.failedField);
}
