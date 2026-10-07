#define CHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE
#include "checkpoint_forward_planning_observer_v2.h"
#include <cstdio>
#include <cstring>
#include <string>
namespace pr=checkpoint_forward_planning_observer_v2;namespace ns=checkpoint_forward_native_session;
extern "C" std::uint64_t PlanningFixtureInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" std::uint64_t PlanningFixtureOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void PlanningFixtureReturn();
static pr::Observer observer;static ns::Report receipt;static pr::Config config;
static uintptr_t base,arena,root,world,states[5]{},stack,worker,callable,iterator,handle,cache,force,ruler,district,load,title;
static unsigned failures=0,nativeCalls=0;static std::string scenario;
template<class T>static void put(uintptr_t p,T value){memcpy(reinterpret_cast<void*>(p),&value,sizeof value);}
static void check(bool value,const char*message){if(!value){++failures;printf("FAIL: %s\n",message);}}
static uintptr_t allocate(size_t n){return uintptr_t(VirtualAlloc(nullptr,n,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));}
static void emptyString(uintptr_t p){put<std::uint64_t>(p+16,0);put<std::uint64_t>(p+24,15);}
static bool guard(void*,pr::Point point,std::uint64_t attempt,std::uint64_t epoch){return attempt==0x6303&&epoch==17&&!(scenario=="epoch-before"&&point==pr::Point::Before)&&!(scenario=="epoch-after"&&point==pr::Point::After);}
extern "C" void PlanningFixtureBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++nativeCalls;check(self==states[4]&&a==0x1001&&b==0x1002&&c==0x1003,"native User args forwarded");
    if(scenario=="native-exception")RaiseException(0xE014CCAE,0,0,nullptr);
    if(scenario=="modal-after")put<std::uint64_t>(base+0x19E7310+0x10,6);
}
static bool exceptional(){__try{PlanningFixtureInvoke(states[4],0x1001,0x1002,0x1003);return false;}__except(GetExceptionCode()==0xE014CCAE?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
static void setup(){
    base=allocate(0x2200000);arena=allocate(0x100000);root=arena+0x20000;world=arena+0xB0000;stack=arena+0x1000;
    worker=arena+0xA0000;callable=worker+0x100;iterator=worker+0x200;handle=worker+0x300;cache=arena+0x80000;force=arena+0x82000;ruler=arena+0x83000;district=arena+0x84000;load=allocate(4096);title=allocate(4096);
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};const uintptr_t vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    for(unsigned i=0;i<5;++i){states[i]=arena+0x10000+i*0x1000;
        if(i==2&&(scenario=="reuse-game-load"||scenario=="reuse-both"||scenario=="live-load-in-game"))states[i]=load;
        if(i==2&&scenario=="reuse-game-title")states[i]=title;
        if(i==4&&scenario=="reuse-user-load")states[i]=load;
        if(i==4&&(scenario=="reuse-user-title"||scenario=="reuse-both"||scenario=="live-title-in-user"||scenario=="reused-user-phase0"))states[i]=title;
        put<uintptr_t>(states[i],base+vt[i]);memcpy(reinterpret_cast<void*>(states[i]+0x70),names[i],strlen(names[i])+1);put<uintptr_t>(stack+i*8,states[i]);}
    auto manager=base+0x19E7310;put<std::uint64_t>(manager+0x10,5);put<uintptr_t>(manager+0x20,stack);put<uintptr_t>(manager+0x48,states[4]);
    put<DWORD>(states[4]+0x470,2);put<DWORD>(states[4]+0x6C,3);put<uintptr_t>(states[4]+0x50,worker);put<uintptr_t>(worker+8,handle);put<uintptr_t>(worker+0x50,callable);put<DWORD>(handle+0x10,GetCurrentThreadId());put<uintptr_t>(callable,base+0x12F2440);put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(callable+8,iterator);put<uintptr_t>(iterator,stack+32);
    for(unsigned i=1;i<4;++i)put<std::uint64_t>(callable+8+i*8,0x1000+i);
    put<uintptr_t>(base+0x1FCA1E0,root);put<uintptr_t>(root,base+0x12AA6B0);put<uintptr_t>(root+0x85130,world);put<uintptr_t>(world,base+0x12AA638);put<WORD>(world+0x34,203);put<BYTE>(world+0x36,8);put<BYTE>(world+0x37,11);put<BYTE>(world+0x3A,2);put<BYTE>(world+0x165D,1);put<DWORD>(world+0x40,1);
    put<uintptr_t>(root+0xDCA0+2*8,force);put<uintptr_t>(root+0x148+952*8,ruler);put<uintptr_t>(root+0xDE40+2*8,district);put<uintptr_t>(force,base+0x129FE58);put<WORD>(force+0x10,952);put<uintptr_t>(ruler,base+0x12A00D0);put<WORD>(ruler+0x10,952);put<BYTE>(ruler+0x118,2);put<uintptr_t>(district,base+0x129FEC8);put<BYTE>(district+0x10,2);put<BYTE>(district+0x11,1);put<WORD>(district+0x12,952);
    put<uintptr_t>(base+0x2025318,cache);put<LONG>(cache+0x3EC,-1);put<LONG>(base+0x201ECD0,-1);put<LONG>(base+0x201ED10,-1);emptyString(base+0x201ECE0);emptyString(base+0x201ED18);emptyString(base+0x201ED38);
    auto toolbar=arena+0x86000,panel=arena+0x87000,gamePanel=arena+0x88000;put<uintptr_t>(states[4]+0x478,toolbar);put<uintptr_t>(states[4]+0x618,panel);put<LONG>(toolbar+0x88,-1);put<uintptr_t>(states[2]+0x480,gamePanel);put<DWORD>(base+0x19E7510+0x13C,1);put<DWORD>(base+0x1FCA518,2);
    // Explicit synthetic upstream fixture receipt. Actual upstream core chain
    // and IPC are independently tested; this fixture does not claim their run.
    receipt.initialized=1;receipt.attempt=0x6303;receipt.casPublished=receipt.mayHavePublished=1;receipt.request.casApplied=1;receipt.request.intentDurable=true;receipt.request.read.matched=true;
    auto&i=receipt.identity;i.receiptReady=1;i.token=receipt.attempt;i.root=root;i.world=world;i.title=title;i.historicalLoad=load;i.workerCall=12;i.completionCall=9;i.target={force,ruler};
    auto&l=receipt.lifecycle;l.receiptReady=1;l.token=receipt.attempt;l.load=load;l.title=title;l.completedCall=9;l.successFlag=0x7FFFFFFD;l.nativeResult=1;l.frozenBytes.workerCall=6;l.frozenBytes.readCall=7;
    auto&b=receipt.bytes;b.observedWorkerAndBytes=1;b.bytesMatched=1;b.token=receipt.attempt;b.load=load;b.title=title;b.workerCall=6;b.readCall=7;b.returned=checkpoint_cc_load_observer::TargetSize;b.nativeResult=1;memcpy(b.sha256,checkpoint_cc_load_observer::TargetSha256,32);
    DWORD old=0;bool loadReused=false,titleReused=false;for(auto state:states){loadReused|=state==load;titleReused|=state==title;}
    if(!loadReused)check(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_NOACCESS,&old)!=0,"retired Load noaccess");
    if(!titleReused)check(VirtualProtect(reinterpret_cast<void*>(title),4096,PAGE_NOACCESS,&old)!=0,"retired Title noaccess");
    config.base=base;config.attempt=receipt.attempt;config.epoch=17;config.persistentRootState=states[0];config.persistentMotorState=states[1];config.previousUser=arena+0x18000;config.syntheticReceipt=&receipt;config.fixtureCaller=uintptr_t(&PlanningFixtureReturn);config.validate=guard;
}
int main(int argc,char**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=2)return 2;scenario=argv[1];setup();
    if(scenario=="reused-user")config.previousUser=states[4];
    if(scenario=="ui-context-different")put<DWORD>(base+0x1FCA518,12);
    if(scenario=="missing-receipt")receipt.identity.receiptReady=0;
    if(scenario=="wrong-stack")put<std::uint64_t>(base+0x19E7310+0x10,6);
    if(scenario=="historical-state")put<uintptr_t>(stack+16,title);
    if(scenario=="live-load-in-game"){put<uintptr_t>(states[2],base+0x12DBD68);memset(reinterpret_cast<void*>(states[2]+0x70),0,32);memcpy(reinterpret_cast<void*>(states[2]+0x70),"CLoadState",11);}
    if(scenario=="live-title-in-user"){put<uintptr_t>(states[4],base+0x12DAAF0);memset(reinterpret_cast<void*>(states[4]+0x70),0,32);memcpy(reinterpret_cast<void*>(states[4]+0x70),"CTitleState",12);}
    if(scenario=="reused-user-phase0")put<DWORD>(states[4]+0x470,0);
    if(scenario=="wrong-force")put<BYTE>(world+0x3A,12);
    if(scenario=="wrong-ruler")put<WORD>(force+0x10,666);
    if(scenario=="load-pending")put<LONG>(base+0x201ECD0,63);
    if(scenario=="queue-pending")put<std::uint64_t>(base+0x19E7310+0x30,1);
    if(scenario=="wrong-caller")++config.fixtureCaller;
    check(pr::Initialize(observer,config),"observer initializes");check(!pr::Initialize(observer,config),"one observer epoch only");
    CheckpointLoadDispatchBridgeConfig b{};b.original=reinterpret_cast<void*>(&PlanningFixtureOriginal);b.before=pr::Before;b.after=pr::After;b.context=&observer;check(CheckpointLoadDispatchBridgeConfigure(0,&b)==1,"actual four-slot bridge configured for independent fixture");
    if(scenario=="early-user-then-success"){receipt.identity.receiptReady=0;PlanningFixtureInvoke(states[4],0x1001,0x1002,0x1003);pr::Report early{};pr::Snapshot(observer,early);check(!early.error&&!early.before&&early.waitingForReceipt==1,"old User before identity receipt is ignored");receipt.identity.receiptReady=1;}
    unsigned char beforeStates[5][32]{},afterStates[5][32]{};for(unsigned i=0;i<5;++i)native_storage_read::Sha256(reinterpret_cast<void*>(states[i]),4096,beforeStates[i]);unsigned char beforeBase[32]{},beforeArena[32]{},afterBase[32]{},afterArena[32]{};native_storage_read::Sha256(reinterpret_cast<void*>(base),0x2200000,beforeBase);native_storage_read::Sha256(reinterpret_cast<void*>(arena),0x100000,beforeArena);
    bool exception=false;if(scenario=="native-exception")exception=exceptional();else check(PlanningFixtureInvoke(states[4],0x1001,0x1002,0x1003)==0xAABBCC1234567890ull,"full native RAX returned");
    pr::Report r{};pr::Snapshot(observer,r);const bool positive=scenario=="success"||scenario=="reused-user"||scenario=="ui-context-different"||scenario=="early-user-then-success"||scenario=="reuse-game-load"||scenario=="reuse-game-title"||scenario=="reuse-user-load"||scenario=="reuse-user-title"||scenario=="reuse-both";
    check(bool(r.planningBoundaryObserved)==positive,"only stable planning boundary accepted");check(nativeCalls==(scenario=="early-user-then-success"?2u:1u),"native original never suppressed");
    check(!r.oldStateDestructorsDirectlyObserved&&!r.allWorkersFinishedProven&&!r.fullWorldVerified&&!r.inputExclusionProven&&!r.pixelPresentationProven,"no unsupported authority claim");
    if(positive){check(!r.inFlight&&r.nativeReturned&&r.receiptBound&&r.formalPlanningStack&&r.identityMatched&&r.requestCleared,"complete before/after observation");check(r.nativeRax==0xAABBCC1234567890ull,"64-bit native return captured");check(bool(r.previousUserAddressReused)==(scenario=="reused-user"),"address reuse diagnostic only");check(bool(r.uiForceContextMatches)==(scenario!="ui-context-different"),"UI context diagnostic only");}
    if(scenario=="historical-state")check(r.error==LONG(pr::Error::Memory)&&r.exceptionCode==EXCEPTION_ACCESS_VIOLATION,"inaccessible current stack state rejected");
    if(scenario=="live-load-in-game")check(r.error==LONG(pr::Error::Stack)&&!r.exceptionCode,"live Load type is not a Game");
    if(scenario=="live-title-in-user")check(!r.planningBoundaryObserved&&r.ignored==1&&!r.before,"live Title type is not a User");
    if(scenario=="reused-user-phase0")check(r.error==LONG(pr::Error::Interface)&&!r.exceptionCode,"new User still must be phase2");
    if(scenario=="native-exception"){CheckpointLoadDispatchBridgeStats stats{};CheckpointLoadDispatchBridgeSnapshot(0,&stats);check(exception&&r.inFlight==1&&!r.nativeReturned&&stats.abnormal_exits==1,"original exception retained without fake after");}
    if(scenario=="modal-after")put<std::uint64_t>(base+0x19E7310+0x10,5); // only fixture's own native-body change
    native_storage_read::Sha256(reinterpret_cast<void*>(base),0x2200000,afterBase);native_storage_read::Sha256(reinterpret_cast<void*>(arena),0x100000,afterArena);for(unsigned i=0;i<5;++i)native_storage_read::Sha256(reinterpret_cast<void*>(states[i]),4096,afterStates[i]);const bool unchanged=!memcmp(beforeBase,afterBase,32)&&!memcmp(beforeArena,afterArena,32)&&!memcmp(beforeStates,afterStates,sizeof beforeStates);check(unchanged,"observer makes zero writes to synthetic native memory");
    printf("{\"case\":\"%s\",\"passed\":%s,\"failures\":%u,\"observed\":%u,\"error\":%ld,\"field\":\"%s\",\"report_bytes\":%zu,\"native_memory_unchanged\":%s,\"game_access\":false,\"synthetic_upstream_receipt\":true}\n",scenario.c_str(),failures?"false":"true",failures,r.planningBoundaryObserved,r.error,r.failedField,sizeof r,unchanged?"true":"false");
    return failures?1:0;
}
