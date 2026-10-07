from pathlib import Path
P=Path(__file__).resolve().parent
assert not (P/'checkpoint_persistent_native_session_fixture.cpp').exists(), 'One-time derivation only; edit successor directly'
s=(P/'checkpoint_guest_native_session_fixture.cpp').read_text()
s=s.replace('checkpoint_guest_native_session.h','checkpoint_persistent_native_session.h').replace('namespace ns=checkpoint_guest_native_session','namespace ns=checkpoint_persistent_native_session')
s=s.replace('#include <cstdio>','#include "checkpoint_persistent_logical_adapter.h"\n#include "checkpoint_persistent_route_six_adapter.h"\n#include <cstdio>')
s=s.replace('static ns::Session session;static checkpoint_load_input_boundary_fixture::Layout layout;', '''static ns::Session* currentSession=nullptr;
static checkpoint_load_input_boundary_fixture::Layout* currentLayout=nullptr;
#define session (*currentSession)
#define layout (*currentLayout)
namespace la=checkpoint_persistent_logical_adapter;
namespace rt=checkpoint_persistent_route;
static rt::Router router;static rt::SixAdapter routeAdapter;
static unsigned generationIndex=0;
extern "C" int CheckpointPersistentObserverClaim(const CheckpointLoadWorkerFrame*f,std::uint64_t t) noexcept {return la::Claim(f,t)?1:0;}
extern "C" int CheckpointPersistentObserverCurrentOwner(CheckpointLoadWorkerOwner*o) noexcept {return la::CurrentOwner(o)?1:0;}
''')
s=s.replace('static bool restoredInRequest=true;','')
s=s.replace('if(scenario==L"stop-restore-inflight"&&p==rq::Point::BeforeRead)restoredInRequest=session.RestoreBeforeCommit();','')
s=s.replace('++userBodies;check(self==layout.config.states[4],"original User");','++userBodies;check(self==layout.config.states[4],"original User");if(scenario==L"user-exception")RaiseException(0xE014CCA1,0,0,nullptr);')
s=s.replace('int wmain(int argc,wchar_t**argv){','static int runGeneration(int argc,wchar_t**argv){')
s=s.replace('fclose(file);setup();','fclose(file);setup();layout.config.attempt+=generationIndex;')
s=s.replace('memset(c.request.ownerBinding,0x63,32)','memset(c.request.ownerBinding,0x63+generationIndex,32)').replace('memset(c.identity.ownerBinding,0x63,32)','memset(c.identity.ownerBinding,0x63+generationIndex,32)')
s=s.replace('CheckpointLoadDispatchBridge0','CheckpointPersistentBridge0').replace('CheckpointLoadDispatchBridge1','CheckpointPersistentBridge1').replace('CheckpointLoadDispatchBridge2','CheckpointPersistentBridge2').replace('CheckpointLoadDispatchBridge3','CheckpointPersistentBridge3').replace('CheckpointLoadWorkerBridge0','CheckpointPersistentBridge4').replace('CheckpointLoadWorkerBridge1','CheckpointPersistentBridge5')
start=s.index('    GuestSessionSlots=reinterpret_cast<void**>');end=s.index('    GuestSessionUserInvoke(layout.config.states[4],1,2,3);ns::Report',start)
s=s[:start]+'''    if(!generationIndex){GuestSessionSlots=reinterpret_cast<void**>(alloc(0x1000));for(unsigned i=0;i<6;++i)GuestSessionSlots[i]=originals[i];}
    for(unsigned i=0;i<6;++i)c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};
    check(session.Initialize(c),"fresh Session owns fresh core objects");
    auto* logical=new la::Adapter;la::Config mapping{};mapping.generation=generationIndex+1;
    for(unsigned i=0;i<4;++i){mapping.dispatchBefore[i]=ns::Session::DispatchBefore;mapping.dispatchAfter[i]=ns::Session::DispatchAfter;mapping.dispatchFinally[i]=ns::Session::DispatchFinally;mapping.dispatchContexts[i]=currentSession;}
    mapping.workerBefore[0]=ns::Session::WorkerBefore;mapping.workerAfter[0]=ns::Session::WorkerAfter;mapping.workerFinally[0]=ns::Session::WorkerFinally;
    mapping.workerBefore[1]=ns::Session::ReadBefore;mapping.workerAfter[1]=ns::Session::ReadAfter;mapping.workerFinally[1]=ns::Session::ReadFinally;
    mapping.workerContexts[0]=mapping.workerContexts[1]=currentSession;
    check(logical->Initialize(mapping),"logical generation mapping");
    if(!generationIndex){
        rt::Config route{};route.initial=logical->RouteGeneration();route.allowOfflineTransitions=true;
        check(router.Initialize(route)&&routeAdapter.Initialize(router),"one persistent router");
        for(unsigned i=0;i<6;++i){auto bridgeConfig=routeAdapter.Configuration(originals[i]);check(CheckpointPersistentBridgeConfigure(i,&bridgeConfig)!=0,"one-time physical bridge config");GuestSessionSlots[i]=bridges[i];}
        DWORD protection=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&protection)!=0,"shared slot page readonly");
    }else{
        check(router.PublishForOfflineExercise(generationIndex,logical->RouteGeneration()),"exercise-only generation handoff");
        for(unsigned i=0;i<6;++i){auto bridgeConfig=routeAdapter.Configuration(originals[i]);check(!CheckpointPersistentBridgeConfigure(i,&bridgeConfig),"physical bridge cannot reset");}
    }
    check(session.ActivateForOfflineExercise(),"explicit fixture-only activation");
    for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"same persistent physical slot");
    if(scenario==L"user-exception"){
        bool caught=false;__try{GuestSessionUserInvoke(layout.config.states[4],1,2,3);}__except(GetExceptionCode()==0xE014CCA1?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
        ns::Report abnormal{};session.Snapshot(abnormal);
        check(caught&&abnormal.dispatchAbnormal==1&&!abnormal.activeDispatch&&!abnormal.menuBound,"dispatch native fault drains without queueing request");
        return finishReport(abnormal,true);
    }
'''+s[end:]
start=s.index('    if(scenario==L"wrong-queue-receipt"){');end=s.index('    check(r.menuBound',start);s=s[:start]+s[end:]
start=s.index('    const bool preRejected=');end=s.index('    check(r.casPublished',start);s=s[:start]+s[end:]
s=s.replace('    return finishReport(r,true);\n}', '''    la::Report logicalReport{};logical->Snapshot(logicalReport);
    check(!routeAdapter.Faults(),"route adapter no faults");
    rt::Report routing{};router.Snapshot(routing);check(!routing.active&&!routing.productionAdmission&&!routing.nativeSchedulerFence,"leases drained; no live authority");
    return finishReport(r,true);
}''')
s+='''
int wmain(int argc,wchar_t**argv){
    if(argc!=4)return 2;
    const std::wstring first=argv[1],folder=argv[3];
    ns::Session* retired=nullptr;ns::Report before{},after{};
    for(unsigned i=0;i<2;++i){
        generationIndex=i;currentSession=new ns::Session;currentLayout=new checkpoint_load_input_boundary_fixture::Layout;
        workerCalls=readCalls=updateCalls=initializers=loadBodies=otherBodies=joinCalls=userBodies=menuBodies=gameBodies=0;loadException=0;
        std::wstring caseName=i?L"success":first;
        std::wstring req=folder+L"/request-"+std::to_wstring(i)+L".intent",identity=folder+L"/identity-"+std::to_wstring(i)+L".intent";
        wchar_t* args[]={argv[0],caseName.data(),argv[2],req.data(),identity.data()};
        runGeneration(5,args);
        if(!i){retired=currentSession;retired->Snapshot(before);}
        else {retired->Snapshot(after);check(!memcmp(&before,&after,sizeof before),"retired Session report immutable across next generation");}
    }
    rt::Report report{};router.Snapshot(report);
    check(report.transitions==1&&report.generations==2&&report.entered==report.released&&!report.active,"two generations on one six-entry installation");
    printf("{\\"case\\":\\"%ls\\",\\"passed\\":%s,\\"failures\\":%u,\\"generations\\":%u,\\"leases\\":%llu,\\"game_access\\":false,\\"native_scheduler_fence\\":false}\\n",first.c_str(),failures?"false":"true",failures,report.generations,report.entered);
    return failures?1:0;
}
'''
(P/'checkpoint_persistent_native_session_fixture.cpp').write_text(s)
