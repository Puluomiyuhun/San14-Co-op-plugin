#include "checkpoint_persistent_route_six_adapter.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
using namespace checkpoint_persistent_route;
namespace {
Router route;SixAdapter adapter;
CheckpointLoadWorkerEntry entry[6]={CheckpointPersistentBridge0,CheckpointPersistentBridge1,CheckpointPersistentBridge2,CheckpointPersistentBridge3,CheckpointPersistentBridge4,CheckpointPersistentBridge5};
struct Count {unsigned id;volatile LONG before[6]{},after[6]{},finally[6]{};};
Count c[2]{{1},{2}};volatile LONG errors=0;HANDLE ready=nullptr,go=nullptr;
thread_local unsigned ids[128]{};thread_local unsigned depth=0;
void check(bool b){if(!b)InterlockedIncrement(&errors);}
void before(const CheckpointLoadWorkerFrame* f,void* p){
    auto* x=static_cast<Count*>(p);check(f->slot<6);ids[depth++]=x->id;InterlockedIncrement(&x->before[f->slot]);
    if(f->args[0]==30){check(SixAdapter::Claim(f,1000+x->id));}
    if(f->args[0]==31){CheckpointLoadWorkerOwner o{};check(SixAdapter::CurrentOwner(o)&&o.token==1000+x->id&&o.slot==4);check(!SixAdapter::Claim(f,2000));}
    if(f->args[0]==20)RaiseException(0xE0420020,0,0,nullptr);
}
void after(const CheckpointLoadWorkerFrame* f,void* p){
    auto* x=static_cast<Count*>(p);check(depth&&ids[depth-1]==x->id);InterlockedIncrement(&x->after[f->slot]);
    if(f->args[0]==21)RaiseException(0xE0420021,0,0,nullptr);
}
void finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit*,void* p){
    auto* x=static_cast<Count*>(p);check(depth&&ids[depth-1]==x->id);if(depth)--depth;InterlockedIncrement(&x->finally[f->slot]);
    if(f->args[0]==22||f->args[0]==23)RaiseException(0xE0420022,0,0,nullptr);
}
Generation g(unsigned id){return Generation{id,before,after,finally,&c[id-1]};}
std::uint64_t native(std::uint64_t mode,std::uint64_t,std::uint64_t,std::uint64_t){
    if(mode==10){check(route.PublishForOfflineExercise(1,g(2)));for(auto f:entry)f(0,0,0,0);}
    if(mode==11||mode==23)RaiseException(0xE0420011,0,0,nullptr);
    if(mode==12){SetEvent(ready);WaitForSingleObject(go,5000);}
    if(mode==14)throw std::runtime_error("native");
    if(mode==30)entry[5](31,0,0,0);
    return 0x0123456789ABCDEF;
}
DWORD seh(unsigned slot,unsigned mode){__try{entry[slot](mode,0,0,0);return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
bool cpp(unsigned slot){try{entry[slot](14,0,0,0);return false;}catch(const std::runtime_error&){return true;}}
DWORD WINAPI active(LPVOID){entry[4](12,0,0,0);return 0;}
DWORD WINAPI late(LPVOID){SetEvent(ready);WaitForSingleObject(go,5000);entry[5](0,0,0,0);return 0;}
}
int main(int argc,char** argv){
    if(argc!=2)return 2;const char* name=argv[1];
    check(route.Initialize(Config{g(1),true}));check(adapter.Initialize(route));
    auto cfg=adapter.Configuration(reinterpret_cast<void*>(&native));
    for(unsigned i=0;i<6;i++)check(CheckpointPersistentBridgeConfigure(i,&cfg)==1);
    if(!strcmp(name,"all-six-normal")){for(auto f:entry)check(f(0,0,0,0)==0x0123456789ABCDEF);}
    else if(!strcmp(name,"all-six-exceptions")){
        for(unsigned i=0;i<6;i++){
            check(seh(i,11)==0xE0420011);check(seh(i,20)==0xE0420020);check(seh(i,21)==0xE0420021);
            check(seh(i,22)==0);check(seh(i,23)==0xE0420011);check(cpp(i));
            check(entry[i](0,0,0,0)==0x0123456789ABCDEF);
        }
    }
    else if(!strcmp(name,"nested-cross-six-cutover")){
        entry[0](10,0,0,0);for(unsigned i=0;i<6;i++)check(c[0].before[i]==(i==0?2:1)&&c[1].before[i]==0);
        for(auto f:entry)f(0,0,0,0);
    }
    else if(!strcmp(name,"nested-worker-read-owner")){entry[4](30,0,0,0);CheckpointLoadWorkerOwner owner{};check(!SixAdapter::CurrentOwner(owner));}
    else if(!strcmp(name,"active-cutover")||!strcmp(name,"late-root")){
        ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);go=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        bool delayed=!strcmp(name,"late-root");auto h=CreateThread(nullptr,0,delayed?late:active,nullptr,0,nullptr);
        check(WaitForSingleObject(ready,5000)==WAIT_OBJECT_0);check(route.PublishForOfflineExercise(1,g(2)));
        entry[3](0,0,0,0);SetEvent(go);check(WaitForSingleObject(h,5000)==WAIT_OBJECT_0);CloseHandle(h);CloseHandle(ready);CloseHandle(go);
        check(delayed?c[1].finally[5]==1:c[0].finally[4]==1);check(c[1].finally[3]==1);
    }else return 3;
    Report r{};route.Snapshot(r);check(!r.active&&r.entered==r.released&&!r.nativeSchedulerFence&&!r.productionAdmission&&!adapter.Faults()&&!depth);
    for(unsigned i=0;i<6;i++){
        CheckpointPersistentBridgeStats s{};check(CheckpointPersistentBridgeSnapshot(i,&s)==1);
        check(!s.active&&s.started==s.finally_calls);check(s.cleanup_faults==(!strcmp(name,"all-six-exceptions")?2:0));
        check(c[0].before[i]==c[0].finally[i]&&c[1].before[i]==c[1].finally[i]);
    }
    std::printf("{\"passed\":%s,\"errors\":%ld,\"entered\":%llu,\"released\":%llu,\"current\":%llu,\"physical_entries\":6,\"native_scheduler_fence\":false,\"production_admission\":false}\n",errors?"false":"true",errors,r.entered,r.released,r.current);
    return errors?1:0;
}
