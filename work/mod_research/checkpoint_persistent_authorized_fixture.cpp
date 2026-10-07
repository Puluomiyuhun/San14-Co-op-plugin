#include "checkpoint_persistent_authorized_controller.h"
#include "checkpoint_persistent_route_six_adapter.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace ad=checkpoint_persistent_authorized;
namespace rt=checkpoint_persistent_route;
namespace la=checkpoint_persistent_logical_adapter;
extern "C" std::uint64_t PersistentAuthorizedFixtureNative(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
struct alignas(16) Return {std::uint64_t rax=0,padding=0;unsigned char xmm[16]{};};
extern "C" void PersistentAuthorizedFixtureCall(void*,std::uint64_t,std::uint64_t,Return*);
namespace {
ad::Controller controllers[2];la::Adapter logical[2];rt::Router router;rt::SixAdapter physical;
unsigned char user[0x480]{};const char* scenario=nullptr;
volatile LONG errors=0,nativeCalls=0,providerBegins=0,providerFinishes=0,queueCalls=0,revokes[2]{};
HANDLE ready=nullptr,go=nullptr;
void check(bool b){if(!b)InterlockedIncrement(&errors);}
bool is(const char* x){return !strcmp(x,scenario);}
bool status(void*,ad::SessionStatus& s) noexcept{s={true,false,0};return true;}
bool bind(void*,const ad::QueueReceipt&) noexcept{return false;}
bool begin(void*,ad::hw::Observe,void*,const ad::hw::Binding&,std::uint64_t,const void*) noexcept{InterlockedIncrement(&providerBegins);return false;}
void finish(void*) noexcept{InterlockedIncrement(&providerFinishes);}
bool snapshot(void*,ad::hw::HardwareReceipt& r) noexcept{r={};return true;}
bool authorize(void*,const ad::pd::Ticket&,const CheckpointPushFrame&,const void*) noexcept{return false;}
ad::pd::Span queue(void*){InterlockedIncrement(&queueCalls);return {};}
void revoke(void* p) noexcept{InterlockedIncrement(static_cast<volatile LONG*>(p));}
void throwFinally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept{RaiseException(0xE0710010,0,0,nullptr);}
void submitBefore(const CheckpointPushFrame* f,void* p) noexcept{static_cast<ad::Controller*>(p)->SubmitUserAfter(f);}
void emptyAfter(const CheckpointPushFrame*,void*) noexcept{}
void call(unsigned mode){Return result{};PersistentAuthorizedFixtureCall(reinterpret_cast<void*>(&CheckpointPersistentBridge0),reinterpret_cast<std::uint64_t>(user),mode,&result);check(result.rax==0xFEDCBA9876543210ull);for(unsigned i=0;i<16;i++)check(result.xmm[i]==i+0x70);}
DWORD seh(unsigned mode){__try{call(mode);return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
bool cpp(){try{call(2);return false;}catch(const std::runtime_error&){return true;}}
DWORD WINAPI worker(LPVOID){call(4);return 0;}
DWORD WINAPI delayed(LPVOID){SetEvent(ready);WaitForSingleObject(go,5000);call(0);return 0;}
DWORD WINAPI many(LPVOID){for(unsigned i=0;i<1000;i++)call(0);return 0;}
ad::Config config(unsigned i){
    ad::Config c{};c.session={&controllers[i],status,bind};c.generation=i+1;c.attempt=i+11;c.pending.binding.owner_generation=c.generation;
    c.pending.states[4]=reinterpret_cast<std::uintptr_t>(user);c.original=PersistentAuthorizedFixtureNative;
    c.pending.profile_base=reinterpret_cast<std::uintptr_t>(&PersistentAuthorizedFixtureNative)-0x3F9B00;
    c.expected_prefetch_site=c.pending.profile_base+0x3F9DAF;
    c.prefetch_provider={&controllers[i],begin,finish,snapshot};c.authorize_queue=authorize;c.queue=queue;
    c.revoke_queue=revoke;c.revoke_queue_context=const_cast<LONG*>(&revokes[i]);return c;
}
}
extern "C" std::uint64_t PersistentAuthorizedFixtureBody(std::uint64_t,std::uint64_t mode,std::uint64_t,std::uint64_t){
    InterlockedIncrement(&nativeCalls);
    if(mode==1)RaiseException(0xE0710001,0,0,nullptr);
    if(mode==2)throw std::runtime_error("native original");
    if(mode==3){check(router.PublishForOfflineExercise(1,logical[1].RouteGeneration()));call(0);}
    if(mode==4){SetEvent(ready);WaitForSingleObject(go,5000);}
    if(mode==5)controllers[0].Stop();
    if(mode==6)call(1);
    if(mode==7){check(CheckpointPersistentAuthorizedOriginal(reinterpret_cast<std::uint64_t>(user),0,0,0)==0xFEDCBA9876543210ull);}
    return 0xFEDCBA9876543210ull;
}
int main(int argc,char** argv){
    if(argc!=2)return 2;scenario=argv[1];
    if(is("recursive-forward-target")){
        check(!ad::ConfigureForwardOriginal(CheckpointPersistentBridge0));check(!ad::ConfigureForwardOriginal(PersistentAuthorizedFixtureNative));
        ad::ForwardReport r{};ad::SnapshotForward(r);check(!r.configured&&!r.pinned);
        std::printf("{\"passed\":%s,\"errors\":%ld,\"production_admission\":false}\n",errors?"false":"true",errors);return errors?1:0;
    }
    check(ad::ConfigureForwardOriginal(PersistentAuthorizedFixtureNative));check(!ad::ConfigureForwardOriginal(PersistentAuthorizedFixtureNative));
    for(unsigned i=0;i<2;i++){
        auto cfg=config(i);
        if(is("finally-observer-seh"))cfg.next_finally=throwFinally;
        if(is("submit-before")){cfg.next_before=submitBefore;cfg.next_after=emptyAfter;cfg.next_context=&controllers[i];}
        check(controllers[i].Initialize(cfg));check(!controllers[i].Initialize(cfg));
        la::Config c{};c.generation=i+1;c.dispatchBefore[0]=ad::Controller::RoutedBefore;
        c.dispatchAfter[0]=ad::Controller::RoutedAfter;c.dispatchFinally[0]=ad::Controller::RoutedFinally;c.dispatchContexts[0]=&controllers[i];
        check(logical[i].Initialize(c));
    }
    check(router.Initialize(rt::Config{logical[0].RouteGeneration(),true}));check(physical.Initialize(router));
    auto bridge=physical.Configuration(reinterpret_cast<void*>(&CheckpointPersistentAuthorizedOriginal));check(CheckpointPersistentBridgeConfigure(0,&bridge)==1);
    if(is("default-closed")){call(0);check(!providerBegins&&!queueCalls);}
    else if(is("production-activation-closed")){
#ifdef CHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE
        check(false);
#else
        check(!controllers[0].ActivateForOfflineExercise());call(0);check(!providerBegins&&!queueCalls);
#endif
    }
    else if(is("unowned-forward")){Return r{};PersistentAuthorizedFixtureCall(reinterpret_cast<void*>(&CheckpointPersistentAuthorizedOriginal),reinterpret_cast<std::uint64_t>(user),0,&r);check(r.rax==0xFEDCBA9876543210ull);call(0);}
    else if(is("two-generations")){call(0);check(router.PublishForOfflineExercise(1,logical[1].RouteGeneration()));call(0);}
    else if(is("nested-cutover")){call(3);call(0);}
    else if(is("native-seh")){check(seh(1)==0xE0710001);}
    else if(is("native-cpp")){check(cpp());}
    else if(is("nested-seh")){check(seh(6)==0xE0710001);}
    else if(is("exception-then-next-generation")){check(seh(1)==0xE0710001);check(router.PublishForOfflineExercise(1,logical[1].RouteGeneration()));call(0);}
    else if(is("stop-during-original")){call(5);call(0);}
    else if(is("finally-observer-seh")){call(0);}
    else if(is("duplicate-wrapper-native")){call(7);}
    else if(is("submit-before")){call(0);}
    else if(is("mismatched-binding-generation")){ad::Controller bad;auto cfg=config(0);cfg.pending.binding.owner_generation=9;check(!bad.Initialize(cfg));check(!bad.Initialize(config(0)));}
    else if(is("active-cutover")||is("late-root")){
        ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);go=CreateEventW(nullptr,TRUE,FALSE,nullptr);bool late=is("late-root");
        auto h=CreateThread(nullptr,0,late?delayed:worker,nullptr,0,nullptr);check(WaitForSingleObject(ready,5000)==WAIT_OBJECT_0);
        check(router.PublishForOfflineExercise(1,logical[1].RouteGeneration()));call(0);SetEvent(go);
        check(WaitForSingleObject(h,5000)==WAIT_OBJECT_0);CloseHandle(h);CloseHandle(ready);CloseHandle(go);
    }
    else if(is("concurrent")){HANDLE hs[4];for(auto& h:hs)h=CreateThread(nullptr,0,many,nullptr,0,nullptr);for(auto h:hs){check(WaitForSingleObject(h,10000)==WAIT_OBJECT_0);CloseHandle(h);}}
    else if(is("invalid-admission-refuses")){
        check(controllers[0].ActivateForOfflineExercise());call(0);ad::Report r{};controllers[0].Snapshot(r);check(r.blocked&&r.error!=ad::Error::None&&!r.queue_calls&&!queueCalls);
    }
    else if(is("wrong-generation-route")){
        // Existing generation 2 retains generation 1 controller deliberately.
        // Exact mapping refuses admission and still forwards immutable native.
        la::Adapter bad;la::Config c{};c.generation=3;c.dispatchBefore[0]=ad::Controller::RoutedBefore;c.dispatchAfter[0]=ad::Controller::RoutedAfter;c.dispatchFinally[0]=ad::Controller::RoutedFinally;c.dispatchContexts[0]=&controllers[0];
        check(bad.Initialize(c));check(router.PublishForOfflineExercise(1,bad.RouteGeneration()));call(0);
    }
    else return 3;
    ad::Report r[2]{};for(unsigned i=0;i<2;i++){
        check(controllers[i].Snapshot(r[i]));check(!r[i].route_active&&r[i].route_started==r[i].route_finished&&!r[i].active);
        check(!r[i].production_admission&&!r[i].native_scheduler_fence&&!r[i].full_input_hold&&!r[i].queue_calls);
    }
    if(is("two-generations")||is("active-cutover")||is("exception-then-next-generation"))check(r[0].route_original==1&&r[1].route_original==1);
    if(is("nested-cutover"))check(r[0].route_original==2&&r[1].route_original==1);
    if(is("late-root"))check(r[0].route_original==0&&r[1].route_original==2);
    if(is("exception-then-next-generation"))check(r[0].route_abnormal==1&&r[1].error==ad::Error::None);
    if(is("finally-observer-seh"))check(r[0].route_faults==1&&r[0].blocked&&r[0].error==ad::Error::Abnormal);
    if(is("duplicate-wrapper-native")||is("submit-before"))check(r[0].blocked&&r[0].error==ad::Error::Pair&&!queueCalls);
    if(!is("invalid-admission-refuses"))check(!providerBegins&&!providerFinishes);
    rt::Report route{};router.Snapshot(route);check(!route.active&&route.entered==route.released&&!physical.Faults());
    CheckpointPersistentBridgeStats stats{};CheckpointPersistentBridgeSnapshot(0,&stats);check(!stats.active&&!stats.cleanup_faults&&stats.started==stats.finally_calls);
    ad::ForwardReport forward{};ad::SnapshotForward(forward);check(forward.configured&&forward.pinned&&!forward.production_admission);
    if(is("unowned-forward")||is("wrong-generation-route")||is("duplicate-wrapper-native"))check(forward.unowned_forwards==1);else check(!forward.unowned_forwards);
    std::printf("{\"passed\":%s,\"errors\":%ld,\"native_calls\":%ld,\"controller1_calls\":%llu,\"controller2_calls\":%llu,\"unowned_forwards\":%llu,\"queue_calls\":%ld,\"provider_begins\":%ld,\"provider_finishes\":%ld,\"native_scheduler_fence\":false,\"production_admission\":false}\n",errors?"false":"true",errors,nativeCalls,r[0].route_original,r[1].route_original,forward.unowned_forwards,queueCalls,providerBegins,providerFinishes);
    return errors?1:0;
}
