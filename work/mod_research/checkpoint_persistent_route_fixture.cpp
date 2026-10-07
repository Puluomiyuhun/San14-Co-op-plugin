#include "checkpoint_persistent_route_worker_adapter.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
using namespace checkpoint_persistent_route;
namespace {
Router router;WorkerAdapter adapter;
struct Context {unsigned id;volatile LONG64 before=0,after=0,finally=0,abnormal=0;};
Context contexts[32]{};volatile LONG bad=0;
struct Seen {const CheckpointLoadWorkerFrame* frame;unsigned generation;};
thread_local Seen seen[128]{};thread_local unsigned nseen=0;
HANDLE enteredEvent=nullptr,continueEvent=nullptr;
void expect(bool v){if(!v)InterlockedIncrement(&bad);}
void before(const CheckpointLoadWorkerFrame* f,void* p){
    auto* c=static_cast<Context*>(p);InterlockedIncrement64(&c->before);
    seen[nseen++]={f,c->id};
    if(f->args[0]==20)RaiseException(0xE0420010,0,0,nullptr);
}
void after(const CheckpointLoadWorkerFrame* f,void* p){
    auto* c=static_cast<Context*>(p);expect(nseen&&seen[nseen-1].frame==f&&seen[nseen-1].generation==c->id);
    InterlockedIncrement64(&c->after);
    if(f->args[0]==21)RaiseException(0xE0420011,0,0,nullptr);
}
void finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){
    auto* c=static_cast<Context*>(p);expect(nseen&&seen[nseen-1].frame==f&&seen[nseen-1].generation==c->id);
    if(nseen)--nseen;InterlockedIncrement64(&c->finally);if(x->abnormal)InterlockedIncrement64(&c->abnormal);
    if(f->args[0]==22)RaiseException(0xE0420012,0,0,nullptr);
}
Generation gen(unsigned id){contexts[id-1].id=id;return Generation{id,before,after,finally,&contexts[id-1]};}
std::uint64_t native(std::uint64_t mode,std::uint64_t b,std::uint64_t,std::uint64_t){
    if(mode==10){expect(router.PublishForOfflineExercise(1,gen(2)));CheckpointLoadWorkerBridge1(0,0,0,0);}
    if(mode==11)RaiseException(0xE0420001,0,0,nullptr);
    if(mode==12){SetEvent(enteredEvent);WaitForSingleObject(continueEvent,5000);}
    if(mode==13&&b)CheckpointLoadWorkerBridge1(13,b-1,0,0);
    if(mode==14)throw std::runtime_error("native original exception");
    return 0xFEDCBA9876543210ull;
}
bool sehCall(unsigned mode,unsigned n=0){
    __try {CheckpointLoadWorkerBridge0(mode,n,0,0);return false;}
    __except(EXCEPTION_EXECUTE_HANDLER){return true;}
}
bool cppCall(){try{CheckpointLoadWorkerBridge0(14,0,0,0);return false;}catch(const std::runtime_error&){return true;}}
DWORD WINAPI blocked(LPVOID){CheckpointLoadWorkerBridge0(12,0,0,0);return 0;}
DWORD WINAPI delayed(LPVOID){SetEvent(enteredEvent);WaitForSingleObject(continueEvent,5000);CheckpointLoadWorkerBridge0(0,0,0,0);return 0;}
DWORD WINAPI racing(LPVOID){for(unsigned i=0;i<3000;i++)CheckpointLoadWorkerBridge0(0,0,0,0);return 0;}
struct Foreign {Lease* lease;bool released=false;};
DWORD WINAPI foreign(LPVOID p){auto* f=static_cast<Foreign*>(p);f->released=router.Release(*f->lease);return 0;}
void waitClose(HANDLE h){expect(WaitForSingleObject(h,10000)==WAIT_OBJECT_0);CloseHandle(h);}
}
int main(int argc,char** argv){
    if(argc!=2)return 2;const char* name=argv[1];
    bool enabled=strcmp(name,"default-closed")!=0;
    expect(router.Initialize(Config{gen(1),enabled}));expect(!router.Initialize(Config{gen(2),true}));
    expect(adapter.Initialize(router));expect(!adapter.Initialize(router));
    CheckpointLoadWorkerBridgeConfig c{};c.original=reinterpret_cast<void*>(&native);
    c.before=WorkerAdapter::Before;c.after=WorkerAdapter::After;c.finally=WorkerAdapter::Finally;c.context=&adapter;
    expect(CheckpointLoadWorkerBridgeConfigure(0,&c)==1);expect(CheckpointLoadWorkerBridgeConfigure(1,&c)==1);
    expect(CheckpointLoadWorkerBridgeConfigure(0,&c)==0);
    if(!strcmp(name,"baseline")){expect(CheckpointLoadWorkerBridge0(0,0,0,0)==0xFEDCBA9876543210ull);}
    else if(!strcmp(name,"default-closed")){expect(!router.PublishForOfflineExercise(1,gen(2)));}
    else if(!strcmp(name,"nested-inherits")){CheckpointLoadWorkerBridge0(10,0,0,0);expect(contexts[0].before==2&&contexts[1].before==0);CheckpointLoadWorkerBridge0(0,0,0,0);expect(contexts[1].before==1);}
    else if(!strcmp(name,"active-cutover")||!strcmp(name,"late-root")){
        enteredEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);continueEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        bool late=!strcmp(name,"late-root");auto h=CreateThread(nullptr,0,late?delayed:blocked,nullptr,0,nullptr);
        expect(WaitForSingleObject(enteredEvent,5000)==WAIT_OBJECT_0);expect(router.PublishForOfflineExercise(1,gen(2)));
        CheckpointLoadWorkerBridge0(0,0,0,0);SetEvent(continueEvent);waitClose(h);
        expect(late?contexts[1].finally==2:contexts[0].finally==1&&contexts[1].finally==1);
        CloseHandle(enteredEvent);CloseHandle(continueEvent);
    }
    else if(!strcmp(name,"race")){
        HANDLE hs[4]{};for(auto& h:hs)h=CreateThread(nullptr,0,racing,nullptr,0,nullptr);
        for(unsigned i=1;i<32;i++)expect(router.PublishForOfflineExercise(i,gen(i+1)));
        for(auto h:hs)waitClose(h);
        expect(!router.PublishForOfflineExercise(32,Generation{33,before,after,finally,&contexts[31]}));
    }
    else if(!strcmp(name,"native-seh")){expect(sehCall(11));expect(contexts[0].after==0&&contexts[0].abnormal==1);}
    else if(!strcmp(name,"native-cpp")){expect(cppCall());expect(contexts[0].after==0&&contexts[0].abnormal==1);}
    else if(!strcmp(name,"before-seh")){expect(sehCall(20));expect(contexts[0].after==0&&contexts[0].abnormal==1);}
    else if(!strcmp(name,"after-seh")){expect(sehCall(21));expect(contexts[0].after==1&&contexts[0].abnormal==1);}
    else if(!strcmp(name,"finally-seh")){expect(!sehCall(22));CheckpointLoadWorkerBridge0(0,0,0,0);}
    else if(!strcmp(name,"nested-overflow")){CheckpointLoadWorkerBridge0(13,67,0,0);expect(adapter.Faults()==4);}
    else if(!strcmp(name,"foreign-double-release")){
        Lease lease;expect(router.Acquire(lease));Foreign f{&lease};waitClose(CreateThread(nullptr,0,foreign,&f,0,nullptr));
        expect(!f.released);expect(router.Release(lease));expect(!router.Release(lease));expect(!router.Acquire(lease));
    }
    else if(!strcmp(name,"compare-and-stale-parent")){
        expect(!router.PublishForOfflineExercise(2,gen(3)));expect(!router.PublishForOfflineExercise(1,gen(1)));
        Lease p,l;expect(router.Acquire(p));expect(router.Release(p));expect(!router.Acquire(l,&p));
    }else return 3;
    Report r{};router.Snapshot(r);expect(r.active==0&&r.entered==r.released&&r.pinned&&!r.nativeSchedulerFence&&!r.productionAdmission);
    CheckpointLoadWorkerBridgeStats s0{},s1{};CheckpointLoadWorkerBridgeSnapshot(0,&s0);CheckpointLoadWorkerBridgeSnapshot(1,&s1);
    expect(!s0.active&&!s1.active);expect(s0.started==s0.finally_calls&&s1.started==s1.finally_calls);
    expect(s0.cleanup_faults==(!strcmp(name,"finally-seh")?1:0));expect(!s1.cleanup_faults);
    if(strcmp(name,"nested-overflow"))expect(adapter.Faults()==0);
    expect(!nseen);
    std::printf("{\"passed\":%s,\"errors\":%ld,\"entered\":%llu,\"released\":%llu,\"current\":%llu,\"adapter_faults\":%llu,\"native_scheduler_fence\":false,\"production_admission\":false}\n",bad?"false":"true",bad,r.entered,r.released,r.current,adapter.Faults());
    return bad?1:0;
}
