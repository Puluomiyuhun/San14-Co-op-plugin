#include "checkpoint_persistent_logical_adapter.h"
#include "checkpoint_persistent_route_six_adapter.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace la=checkpoint_persistent_logical_adapter;
namespace rt=checkpoint_persistent_route;
namespace {
rt::Router router,otherRouter;rt::SixAdapter physical,otherPhysical;
la::Adapter adapters[2];
CheckpointLoadWorkerEntry entries[6]={CheckpointPersistentBridge0,CheckpointPersistentBridge1,CheckpointPersistentBridge2,CheckpointPersistentBridge3,CheckpointPersistentBridge4,CheckpointPersistentBridge5};
struct Ctx {unsigned generation,slot;bool worker;};Ctx contexts[2][6]{};
volatile LONG errors=0,beforeCounts[2][6]{},afterCounts[2][6]{},finallyCounts[2][6]{};
const char* scenario=nullptr;
thread_local const void* logicalFrames[80]{};thread_local unsigned frameDepth=0;
thread_local const CheckpointLoadWorkerFrame* ancestor=nullptr;
HANDLE ready=nullptr,go=nullptr;
DWORD WINAPI foreignClaim(LPVOID p){return la::Claim(static_cast<const CheckpointLoadWorkerFrame*>(p),123)?1u:0u;}
void check(bool b){if(!b)InterlockedIncrement(&errors);}
bool is(const char* s){return !strcmp(scenario,s);}
void mapping(const void* f,Ctx* c,unsigned stage){
    la::Mapping m{};check(la::CurrentMapping(&m));
    check(m.logicalFrame==f&&m.physicalFrame!=f&&m.generation==c->generation&&m.logicalSlot==c->slot&&
        m.physicalSlot==(c->worker?c->slot+4:c->slot)&&m.thread==GetCurrentThreadId()&&m.stage==stage);
}
void dispatchBefore(const CheckpointPushFrame* f,void* p) noexcept {
    auto* c=static_cast<Ctx*>(p);mapping(f,c,1);check(f->slot==c->slot);logicalFrames[frameDepth++]=f;
    InterlockedIncrement(&beforeCounts[c->generation-1][c->slot]);
    check(!la::Claim(reinterpret_cast<const CheckpointLoadWorkerFrame*>(f),888));
}
void dispatchAfter(const CheckpointPushFrame* f,void* p) noexcept {
    auto* c=static_cast<Ctx*>(p);mapping(f,c,3);check(frameDepth&&logicalFrames[frameDepth-1]==f);
    check(f->result_rax==0xFEDCBA9876543210ull);InterlockedIncrement(&afterCounts[c->generation-1][c->slot]);
}
void dispatchFinally(const CheckpointPushFrame* f,const CheckpointLoadWorkerExit*,void* p){
    auto* c=static_cast<Ctx*>(p);mapping(f,c,5);check(frameDepth&&logicalFrames[frameDepth-1]==f);if(frameDepth)--frameDepth;
    InterlockedIncrement(&finallyCounts[c->generation-1][c->slot]);
}
void workerBefore(const CheckpointLoadWorkerFrame* f,void* p){
    auto* c=static_cast<Ctx*>(p);mapping(f,c,1);check(f->slot==c->slot);logicalFrames[frameDepth++]=f;
    InterlockedIncrement(&beforeCounts[c->generation-1][c->slot+4]);
    auto copied=*f;check(!la::Claim(&copied,999));
    if(is("mutated-logical-frame")){
        auto* mutableFrame=const_cast<CheckpointLoadWorkerFrame*>(f);auto old=mutableFrame->args[0];mutableFrame->args[0]^=0x10;
        check(!la::Claim(f,999));mutableFrame->args[0]=old;
    }
    bool ownerCase=is("worker-read-owner")||is("dispatch-worker-read")||is("generation-cutover")||is("ancestor-frame-rejected")||is("cross-generation-owner");
    if(ownerCase&&c->slot==0){check(la::Claim(f,100+c->generation));ancestor=f;}
    if(ownerCase&&c->slot==1){
        CheckpointLoadWorkerOwner o{};
        if(is("cross-generation-owner")){check(!la::CurrentOwner(&o));}
        else {check(la::CurrentOwner(&o));check(o.slot==0&&o.token==100+c->generation&&o.owner_depth==1&&o.current_depth==2);}
        check(!la::Claim(f,777));if(ancestor)check(!la::Claim(ancestor,778));
    }
    if(is("cross-thread-frame")){auto h=CreateThread(nullptr,0,foreignClaim,const_cast<CheckpointLoadWorkerFrame*>(f),0,nullptr);check(WaitForSingleObject(h,5000)==WAIT_OBJECT_0);DWORD result=1;check(GetExitCodeThread(h,&result)&&result==0);CloseHandle(h);}
    if(is("direct-native-claim-refused")){check(CheckpointPersistentClaim(static_cast<const CheckpointLoadWorkerFrame*>([](){la::Mapping m{};la::CurrentMapping(&m);return m.physicalFrame;}()),123)==1);CheckpointLoadWorkerOwner o{};check(!la::CurrentOwner(&o));}
    if(is("before-seh"))RaiseException(0xE0610001,0,0,nullptr);
}
void workerAfter(const CheckpointLoadWorkerFrame* f,void* p){
    auto* c=static_cast<Ctx*>(p);mapping(f,c,3);check(frameDepth&&logicalFrames[frameDepth-1]==f);
    check(f->result_rax==0xFEDCBA9876543210ull);InterlockedIncrement(&afterCounts[c->generation-1][c->slot+4]);
    check(!la::Claim(f,901));if(is("after-seh"))RaiseException(0xE0610002,0,0,nullptr);
}
void workerFinally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){
    auto* c=static_cast<Ctx*>(p);mapping(f,c,5);check(frameDepth&&logicalFrames[frameDepth-1]==f);if(frameDepth)--frameDepth;
    InterlockedIncrement(&finallyCounts[c->generation-1][c->slot+4]);check(!la::Claim(f,902));
    la::Mapping m{};la::CurrentMapping(&m);check(x->depth==m.logicalWorkerDepth);
    if(is("finally-seh")||is("native-finally-seh"))RaiseException(0xE0610003,0,0,nullptr);
}
std::uint64_t native(std::uint64_t mode,std::uint64_t b,std::uint64_t,std::uint64_t){
    la::Mapping m{};check(la::CurrentMapping(&m));check(m.stage==2);
    if(m.physicalSlot>=4)check(!la::Claim(static_cast<const CheckpointLoadWorkerFrame*>(m.logicalFrame),903));
    if(mode==1)entries[5](0,0,0,0);
    if(mode==2)entries[4](1,0,0,0);
    if(mode==3)RaiseException(0xE0610011,0,0,nullptr);
    if(mode==4)throw std::runtime_error("native C++");
    if(mode==5){SetEvent(ready);WaitForSingleObject(go,5000);}
    if(mode==6){check(router.PublishForOfflineExercise(1,adapters[1].RouteGeneration()));entries[5](0,0,0,0);}
    if(mode==7&&b)entries[5](7,b-1,0,0);
    return 0xFEDCBA9876543210ull;
}
DWORD seh(unsigned slot,unsigned mode){__try{entries[slot](mode,0,0,0);return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
bool cpp(){try{entries[4](4,0,0,0);return false;}catch(const std::runtime_error&){return true;}}
DWORD WINAPI active(LPVOID){entries[4](5,0,0,0);return 0;}
DWORD WINAPI late(LPVOID){SetEvent(ready);WaitForSingleObject(go,5000);entries[5](0,0,0,0);return 0;}
DWORD WINAPI racing(LPVOID){for(unsigned i=0;i<1000;i++)entries[i%6](0,0,0,0);return 0;}
la::Config config(unsigned gen){
    la::Config c{};c.generation=gen;
    for(unsigned i=0;i<6;i++){
        auto& ctx=contexts[gen-1][i];ctx={gen,i<4?i:i-4,i>=4};
        if(i<4){c.dispatchBefore[i]=dispatchBefore;c.dispatchAfter[i]=dispatchAfter;c.dispatchFinally[i]=dispatchFinally;c.dispatchContexts[i]=&ctx;}
        else {c.workerBefore[i-4]=workerBefore;c.workerAfter[i-4]=workerAfter;c.workerFinally[i-4]=workerFinally;c.workerContexts[i-4]=&ctx;}
    }return c;
}
}
int main(int argc,char** argv){
    if(argc!=2)return 2;scenario=argv[1];
    check(adapters[0].Initialize(config(1)));check(adapters[1].Initialize(config(2)));check(!adapters[0].Initialize(config(1)));
    check(router.Initialize(rt::Config{adapters[0].RouteGeneration(),true}));check(physical.Initialize(router));
    auto c=physical.Configuration(reinterpret_cast<void*>(&native));
    if(is("cross-generation-owner")){check(otherRouter.Initialize(rt::Config{adapters[1].RouteGeneration(),false}));check(otherPhysical.Initialize(otherRouter));}
    for(unsigned i=0;i<6;i++){
        auto chosen=is("cross-generation-owner")&&i==5?otherPhysical.Configuration(reinterpret_cast<void*>(&native)):c;
        check(CheckpointPersistentBridgeConfigure(i,&chosen)==1);
    }
    CheckpointLoadWorkerOwner owner{};la::Mapping map{};check(!la::CurrentOwner(&owner)&&!la::CurrentMapping(&map));
    if(is("all-six-copy")||is("mutated-logical-frame")){for(auto f:entries)check(f(0,0,0,0)==0xFEDCBA9876543210ull);}
    else if(is("worker-read-owner")||is("ancestor-frame-rejected")||is("cross-generation-owner")){entries[4](1,0,0,0);}
    else if(is("cross-thread-frame")){entries[4](0,0,0,0);}
    else if(is("dispatch-worker-read")){entries[0](2,0,0,0);}
    else if(is("generation-cutover")){entries[4](6,0,0,0);check(beforeCounts[0][4]==1&&beforeCounts[0][5]==1&&beforeCounts[1][5]==0);entries[4](1,0,0,0);check(beforeCounts[1][4]==1&&beforeCounts[1][5]==1);}
    else if(is("before-seh")){check(seh(4,0)==0xE0610001);}
    else if(is("after-seh")){check(seh(4,0)==0xE0610002);}
    else if(is("finally-seh")){check(seh(4,0)==0);}
    else if(is("native-finally-seh")){check(seh(4,3)==0xE0610011);}
    else if(is("native-seh")){check(seh(4,3)==0xE0610011);}
    else if(is("dispatch-native-seh")){check(seh(0,3)==0xE0610011);}
    else if(is("native-cpp")){check(cpp());}
    else if(is("direct-native-claim-refused")){entries[4](0,0,0,0);}
    else if(is("active-cutover")||is("late-root")){
        ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);go=CreateEventW(nullptr,TRUE,FALSE,nullptr);bool delayed=is("late-root");
        auto h=CreateThread(nullptr,0,delayed?late:active,nullptr,0,nullptr);check(WaitForSingleObject(ready,5000)==WAIT_OBJECT_0);
        check(router.PublishForOfflineExercise(1,adapters[1].RouteGeneration()));entries[3](0,0,0,0);SetEvent(go);
        check(WaitForSingleObject(h,5000)==WAIT_OBJECT_0);CloseHandle(h);CloseHandle(ready);CloseHandle(go);
        check(delayed?finallyCounts[1][5]==1:finallyCounts[0][4]==1);check(finallyCounts[1][3]==1);
    }
    else if(is("concurrent")){HANDLE hs[4];for(auto& h:hs)h=CreateThread(nullptr,0,racing,nullptr,0,nullptr);for(auto h:hs){check(WaitForSingleObject(h,10000)==WAIT_OBJECT_0);CloseHandle(h);}}
    else if(is("invalid-config-terminal")){la::Adapter invalid;auto bad=config(1);bad.workerFinally[0]=nullptr;check(!invalid.Initialize(bad));check(!invalid.Initialize(config(1)));check(invalid.RouteGeneration().id==0);}
    else return 3;
    check(!la::CurrentOwner(&owner)&&!la::CurrentMapping(&map)&&!frameDepth&&!physical.Faults());
    rt::Report routing{};router.Snapshot(routing);check(!routing.active&&routing.entered==routing.released&&!routing.productionAdmission&&!routing.nativeSchedulerFence);
    if(is("cross-generation-owner")){rt::Report other{};otherRouter.Snapshot(other);check(!other.active&&other.entered==other.released&&!otherPhysical.Faults());}
    unsigned long long beforeTotal=0,afterTotal=0,finallyTotal=0;
    for(unsigned gen=0;gen<2;gen++){
        la::Report r{};adapters[gen].Snapshot(r);check(!r.active&&!r.faults&&r.before==r.finally&&r.initialized&&r.pinned&&!r.productionAdmission&&!r.nativeSchedulerFence);
        beforeTotal+=r.before;afterTotal+=r.after;finallyTotal+=r.finally;
        for(unsigned i=0;i<6;i++)check(beforeCounts[gen][i]==finallyCounts[gen][i]);
    }
    for(unsigned i=0;i<6;i++){
        CheckpointPersistentBridgeStats s{};CheckpointPersistentBridgeSnapshot(i,&s);check(!s.active&&s.started==s.finally_calls);
        check(s.cleanup_faults==((is("finally-seh")||is("native-finally-seh"))&&i==4?1:0));
    }
    std::printf("{\"passed\":%s,\"errors\":%ld,\"before\":%llu,\"after\":%llu,\"finally\":%llu,\"generation\":%llu,\"native_scheduler_fence\":false,\"production_admission\":false}\n",errors?"false":"true",errors,beforeTotal,afterTotal,finallyTotal,routing.current);
    return errors?1:0;
}
