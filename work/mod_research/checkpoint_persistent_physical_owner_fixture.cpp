#include "checkpoint_persistent_physical_owner.h"
#include <cstdio>
#include <cstring>
namespace po=checkpoint_persistent_physical_owner;
static po::Owner owner;
static unsigned failures=0,before[2]{},after[2]{},finallyCount[2]{},nativeCalls=0;
static unsigned ids[2]={0,1};static const char* scenario="";
using Fn=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
static void* volatile* slots=nullptr;
static void check(bool ok,const char* why){if(!ok){++failures;printf("FAIL %s\n",why);}}
static std::uint64_t body(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){++nativeCalls;if(!strcmp(scenario,"exception"))RaiseException(0xE014CCBC,0,0,nullptr);return a+b+c+d;}
static void beforeCall(const CheckpointLoadWorkerFrame*,void*p){++before[*static_cast<unsigned*>(p)];}
static void afterCall(const CheckpointLoadWorkerFrame*,void*p){++after[*static_cast<unsigned*>(p)];}
static void finallyCall(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*p){++finallyCount[*static_cast<unsigned*>(p)];}
static checkpoint_persistent_route::Generation gen(unsigned i){return {i+2,beforeCall,afterCall,finallyCall,&ids[i]};}
static bool guard(void*,po::Point p,unsigned i) noexcept {
    if(!strcmp(scenario,"guard-before")&&p==po::Point::BeforeConfigure)return false;
    if(!strcmp(scenario,"guard-partial")&&p==po::Point::BeforePublish&&i==2)return false;
    if(!strcmp(scenario,"guard-after")&&p==po::Point::AfterPublish&&i==5)return false;
    if(!strcmp(scenario,"publish-conflict")&&p==po::Point::BeforePublish&&i==2){DWORD old=0;VirtualProtect(const_cast<void**>(slots),4096,PAGE_READWRITE,&old);InterlockedExchangePointer(slots+2,reinterpret_cast<void*>(&guard));VirtualProtect(const_cast<void**>(slots),4096,old,&old);}
    return true;
}
static bool invoke(unsigned i){__try{check(reinterpret_cast<Fn>(slots[i])(1,2,3,4)==10,"native result");return true;}__except(GetExceptionCode()==0xE014CCBC?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return false;}}
int main(int argc,char**argv){
    scenario=argc>1?argv[1]:"success";
    auto* page=VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);slots=reinterpret_cast<void*volatile*>(page);check(slots!=nullptr,"allocate slots");if(!slots)return 2;
    void* entries[]={reinterpret_cast<void*>(&CheckpointPersistentBridge0),reinterpret_cast<void*>(&CheckpointPersistentBridge1),reinterpret_cast<void*>(&CheckpointPersistentBridge2),reinterpret_cast<void*>(&CheckpointPersistentBridge3),reinterpret_cast<void*>(&CheckpointPersistentBridge4),reinterpret_cast<void*>(&CheckpointPersistentBridge5)};
    po::Config c{};c.context=&owner;c.validate=guard;
    for(unsigned i=0;i<6;++i){slots[i]=reinterpret_cast<void*>(&body);c.hooks[i]={slots+i,reinterpret_cast<void*>(&body),entries[i]};}
    DWORD old=0;check(VirtualProtect(page,4096,PAGE_READONLY,&old)!=FALSE,"read-only slots");
    if(!strcmp(scenario,"duplicate-slot"))c.hooks[5].slot=c.hooks[4].slot;
    if(!strcmp(scenario,"wrong-hook"))c.hooks[3].hook=entries[2];
    if(!strcmp(scenario,"original-bridge"))c.hooks[3].original=entries[1];
    if(!strcmp(scenario,"forward-bridge"))c.userForward=entries[1];
    if(!strcmp(scenario,"nonresident-original"))c.hooks[4].original=page;
    if(!strcmp(scenario,"existing-bridge")){CheckpointPersistentBridgeConfig b{};b.original=reinterpret_cast<void*>(&body);check(CheckpointPersistentBridgeConfigure(3,&b)!=0,"prior bridge config");}
    const bool expected=!strcmp(scenario,"success")||!strcmp(scenario,"stop")||!strcmp(scenario,"drift")||!strcmp(scenario,"exception")||!strcmp(scenario,"stale-generation")||!strcmp(scenario,"production");
    check(owner.Install(c)==expected,"installation disposition");po::Report r{};owner.Snapshot(r);
    check(!r.productionAdmission&&!r.nativeSchedulerFence,"no native load authority");
    if(expected){
        check(r.installed&&r.configured==6&&r.published==6&&r.hooksRetained&&owner.Verify(),"all six immutable slots installed");
        for(unsigned i=0;i<6;++i)check(invoke(i)==bool(strcmp(scenario,"exception")),"native normal/exception disposition");
        check(!before[0]&&!after[0]&&!finallyCount[0],"bootstrap forwards without touching uninitialized Session observers");
        if(strcmp(scenario,"production")){
            check(owner.PublishForOfflineExercise(1,gen(0)),"publish fully prepared fixture generation after bootstrap");
            for(unsigned i=0;i<6;++i)check(invoke(i)==bool(strcmp(scenario,"exception")),"prepared generation disposition");
            check(before[0]==6&&finallyCount[0]==6&&after[0]==(!strcmp(scenario,"exception")?0u:6u),"paired native finally path");
        }
        owner.Snapshot(r);check(!r.route.active&&!r.routeFaults&&r.route.entered==r.route.released,"router drained after native calls");
        if(!strcmp(scenario,"stop")){owner.Stop();check(!owner.PublishForOfflineExercise(2,gen(1)),"stopped owner refuses publication");check(invoke(0),"stop retains native forwarding");}
        else if(!strcmp(scenario,"drift")){check(VirtualProtect(page,4096,PAGE_READWRITE,&old)!=FALSE,"make fixture drift");InterlockedExchangePointer(slots+4,reinterpret_cast<void*>(&body));check(!owner.Verify()&&!owner.PublishForOfflineExercise(2,gen(1)),"foreign hook drift closes publication");}
        else if(!strcmp(scenario,"stale-generation")){check(!owner.PublishForOfflineExercise(1,gen(1)),"wrong expected generation rejects");}
        else if(!strcmp(scenario,"production")){check(!owner.PublishForOfflineExercise(1,gen(1)),"production transitions closed");}
        else if(!strcmp(scenario,"success")){check(owner.PublishForOfflineExercise(2,gen(1)),"fresh fixture generation");for(unsigned i=0;i<6;++i)check(invoke(i),"second generation original");check(before[0]==6&&after[0]==6&&finallyCount[0]==6&&before[1]==6&&after[1]==6&&finallyCount[1]==6,"old generation immutable routing records");}
    }else{
        const bool conflict=!strcmp(scenario,"publish-conflict"),partial=!strcmp(scenario,"guard-partial")||conflict,all=!strcmp(scenario,"guard-after");
        check(r.published==(partial?2u:all?6u:0u),"partial publication visible");
        if(conflict)check(r.publicationAttempts==3&&r.publicationUncertain,"failed slot attempt recorded separately from successful publication");
        check(r.stopped&&!r.installed,"failed installation terminal");
        for(unsigned i=0;i<r.published;++i)check(invoke(i),"retained partial hook still forwards");
    }
    check(!owner.Install(c),"owner cannot reset/reinstall");owner.Snapshot(r);
    check(!r.productionAdmission&&!r.nativeSchedulerFence,"closed final authority");
    printf("{\"case\":\"%s\",\"passed\":%s,\"failures\":%u,\"configured\":%u,\"published\":%u,\"generations\":%u,\"native_calls\":%u,\"game_access\":false}\n",scenario,failures?"false":"true",failures,r.configured,r.published,r.route.generations,nativeCalls);
    return failures?1:0;
}
