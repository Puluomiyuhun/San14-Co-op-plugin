#define CHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE
#include "checkpoint_title_identity_adapter.h"
#include <cstdio>
#include <cstring>
#include <string>
namespace ti=checkpoint_title_identity_adapter;namespace lc=checkpoint_cc_load_lifecycle;namespace by=checkpoint_cc_load_observer;namespace pc=checkpoint_identity_pair_commit;
extern "C" {
std::uint64_t TitleIdentityFixtureInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t TitleIdentityFixtureOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void TitleIdentityFixtureReturn();
std::uint64_t TitleIdentityFixtureRax=0;unsigned char TitleIdentityFixtureXmm[16]{};
}
static ti::Adapter adapter;static lc::Lifecycle lifecycle;static by::Observer bytes;static ti::Config cfg;
static std::wstring scenario;static uintptr_t base,root,world,title,oldLoad,stackArray,callable,otherCallable,forceA,forceB,personA,personB,districtA,districtB;
static unsigned failures=0,nativeCalls=0,initializers=0;static pc::Pair source,target;
template<class T>static void put(uintptr_t p,T x){memcpy(reinterpret_cast<void*>(p),&x,sizeof x);}
template<class T>static T at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static void check(bool x,const char*s){if(!x){++failures;printf("FAIL: %s\n",s);}}
static uintptr_t alloc(size_t size){return uintptr_t(VirtualAlloc(nullptr,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));}
static bool byteGuard(void*,by::Point,uintptr_t,uintptr_t){return true;}
static bool lifeGuard(void*,lc::Point,uintptr_t,uintptr_t){return true;}
static bool environment(void*,ti::Point p,uintptr_t t,uintptr_t r,uintptr_t w){
    if(scenario==L"guard-before"&&p==ti::Point::Before)return false;
    if(scenario==L"guard-before-intent"&&p==ti::Point::BeforeIntent)return false;
    if(scenario==L"guard-before-cas"&&p==ti::Point::BeforeCompareExchange)return false;
    if(scenario==L"guard-after-cas"&&p==ti::Point::AfterCompareExchange)return false;
    if(scenario==L"guard-after"&&p==ti::Point::After)return false;
    if(scenario==L"guard-seh"&&p==ti::Point::BeforeIntent)RaiseException(0xE0146301,0,0,nullptr);
    if(scenario==L"cas-conflict"&&p==ti::Point::BeforeCompareExchange)put<pc::Pair>(title+0x4A0,{source.force,target.person});
    if(scenario==L"stop-before-cas"&&p==ti::Point::BeforeCompareExchange)ti::Stop(adapter);
    return t==title&&r==root&&w==world;
}
static void invoke(uintptr_t self){TitleIdentityFixtureInvoke(self,0x1234567812345678ull,0xFFEEDDCCBBAA9988ull,0x7766554433221100ull);}
extern "C" void TitleIdentityFixtureBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++nativeCalls;check(a==0x1234567812345678ull&&b==0xFFEEDDCCBBAA9988ull&&c==0x7766554433221100ull,"four integer arguments preserved");
    if(self==otherCallable)return;
    if(scenario==L"native-seh")RaiseException(0xE0146302,0,0,nullptr);
    if(scenario==L"native-cpp")throw 63;
    if(scenario==L"nested-other")invoke(otherCallable);
    ++initializers;
    // Explicit synthetic original4DA390/2FC850 body; the adapter never calls it.
    auto selected=at<pc::Pair>(title+0x4A0);
    if(scenario!=L"native-no-change")put<BYTE>(world+0x3A,selected.person==personB?2:12);
    put<BYTE>(world+0x165D,1);
    if(scenario==L"native-wrong-control")put<BYTE>(world+0x165D,2);
    if(scenario==L"transition-during-native"){
        put<DWORD>(title+0x470,15);put<std::uint64_t>(base+0x19E7310+0x10,3);
    }
    if(scenario==L"stop-during-native")ti::Stop(adapter);
}
static bool runSeh(){__try{invoke(callable);return false;}__except(GetExceptionCode()==0xE0146302?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
static void setupSyntheticReceipts(){
    // Lifecycle and byte core are independently tested. These are explicit
    // synthetic frozen receipts, not another Steam read/native join claim.
    by::Config b{};b.base=base;b.storage=title+0x1000;b.storageVtable=title+0x1020;b.readMethod=base+0x100;b.attemptToken=0xCC6303;b.validateAttachment=byteGuard;
    check(by::Initialize(bytes,b),"initialize bytes");
    lc::Config l{};l.base=base;l.attemptToken=b.attemptToken;l.bytes=&bytes;l.validateAttachment=lifeGuard;check(lc::Initialize(lifecycle,l),"initialize lifecycle");
    auto&r=bytes.report;r.load=oldLoad;r.title=title;r.workerCall=11;r.readCall=21;r.workerBefore=r.workerAfter=r.workerFinally=r.readBefore=r.readAfter=r.readFinally=1;
    r.bytesMatched=r.workerReturned=r.ownedReadCandidates=1;r.nativeResult=1;r.returned=by::TargetSize;memcpy(r.sha256,by::TargetSha256,32);
    auto&f=lifecycle.report;f.load=oldLoad;f.title=title;f.bound=f.workerStarted=f.joinReturned=f.requestCleared=f.exactPop=f.completionFrozen=1;
    f.successFlag=0x7FFFFFFD;f.nativeResult=1;f.boundCall=1;f.joinedCall=2;f.completedCall=4;by::Snapshot(bytes,f.frozenBytes);
    if(scenario==L"wrong-token")++f.token;
    if(scenario==L"missing-completion")f.completionFrozen=0;
    if(scenario==L"missing-join")f.joinReturned=0;
    if(scenario==L"bad-byte-hash")r.sha256[0]^=1;
}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=3)return 2;scenario=argv[1];
    base=alloc(0x2100000);root=alloc(0x86000);world=alloc(0x4000);title=alloc(0x2000);oldLoad=alloc(0x1000);stackArray=alloc(0x3000);
    forceA=alloc(0x1000);forceB=alloc(0x1000);personA=alloc(0x1000);personB=alloc(0x1000);districtA=alloc(0x1000);districtB=alloc(0x1000);
    if(!base||!root||!world||!title||!oldLoad||!stackArray||!forceA||!forceB||!personA||!personB||!districtA||!districtB)return 3;
    source={forceA,personA};target={forceB,personB};callable=title+0x700;otherCallable=title+0x740;
    put<uintptr_t>(base+0x1FCA1E0,root);put<uintptr_t>(root,base+0x12AA6B0);put<uintptr_t>(root+0x85130,world);put<uintptr_t>(world,base+0x12AA638);
    put<WORD>(world+0x34,203);put<BYTE>(world+0x36,8);put<BYTE>(world+0x37,11);put<BYTE>(world+0x3A,12);put<DWORD>(world+0x40,1);put<BYTE>(world+0x165D,2);put<DWORD>(world+0x20A8,1);
    put<uintptr_t>(root+0xDCA0+12*8,forceA);put<uintptr_t>(root+0xDCA0+2*8,forceB);put<uintptr_t>(root+0x148+666*8,personA);put<uintptr_t>(root+0x148+952*8,personB);put<uintptr_t>(root+0xDE40+11*8,districtA);put<uintptr_t>(root+0xDE40+2*8,districtB);
    put<uintptr_t>(forceA,base+0x129FE58);put<WORD>(forceA+0x10,666);put<BYTE>(forceA+0x47,6);put<uintptr_t>(forceB,base+0x129FE58);put<WORD>(forceB+0x10,952);put<BYTE>(forceB+0x47,7);
    put<uintptr_t>(personA,base+0x12A00D0);put<WORD>(personA+0x10,666);put<BYTE>(personA+0x118,11);put<uintptr_t>(personB,base+0x12A00D0);put<WORD>(personB+0x10,952);put<BYTE>(personB+0x118,2);
    put<uintptr_t>(districtA,base+0x129FEC8);put<BYTE>(districtA+0x10,12);put<BYTE>(districtA+0x11,1);put<WORD>(districtA+0x12,666);put<uintptr_t>(districtB,base+0x129FEC8);put<BYTE>(districtB+0x10,2);put<BYTE>(districtB+0x11,1);put<WORD>(districtB+0x12,952);
    put<uintptr_t>(title,base+0x12DAAF0);memcpy(reinterpret_cast<void*>(title+0x70),"CTitleState",12);put<DWORD>(title+0x47C,63);put<pc::Pair>(title+0x4A0,source);
    const bool early=scenario==L"early"||scenario==L"transition-during-native";
    put<DWORD>(title+0x470,early?13:15);put<uintptr_t>(title+0x520+0x48,callable);put<uintptr_t>(callable,base+0x138E8C0);put<uintptr_t>(callable+8,base+0x4DA390);put<uintptr_t>(otherCallable,base+0x138E8C0);put<uintptr_t>(otherCallable+8,base+0x1234);
    auto rootState=stackArray+0x1000,motor=stackArray+0x2000;put<uintptr_t>(stackArray,rootState);put<uintptr_t>(stackArray+8,motor);put<uintptr_t>(stackArray+16,title);put<uintptr_t>(stackArray+24,oldLoad);
    memcpy(reinterpret_cast<void*>(rootState+0x70),"CRootState",11);memcpy(reinterpret_cast<void*>(motor+0x70),"CMotorGameState",16);put<uintptr_t>(base+0x19E7310+0x20,stackArray);put<std::uint64_t>(base+0x19E7310+0x10,early?4:3);
    setupSyntheticReceipts();DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(oldLoad),0x1000,PAGE_NOACCESS,&old)!=0,"historical Load inaccessible throughout");
    if(scenario==L"wrong-owner")put<uintptr_t>(title+0x520+0x48,otherCallable);
    if(scenario==L"wrong-vtable")put<uintptr_t>(callable,base+0x138E8D0);
    if(scenario==L"wrong-stack")put<uintptr_t>(stackArray+16,rootState);
    if(scenario==L"wrong-phase")put<DWORD>(title+0x470,12);
    if(scenario==L"three-phase13")put<DWORD>(title+0x470,13);
    if(scenario==L"wrong-slot")put<DWORD>(title+0x47C,34);
    if(scenario==L"wrong-source")put<pc::Pair>(title+0x4A0,target);
    if(scenario==L"wrong-ruler")put<WORD>(forceB+0x10,951);
    if(scenario==L"wrong-person-id")put<WORD>(personB+0x10,951);
    if(scenario==L"wrong-district")put<BYTE>(personB+0x118,3);
    if(scenario==L"wrong-district-force")put<BYTE>(districtB+0x10,12);
    if(scenario==L"wrong-district-leader")put<WORD>(districtB+0x12,666);
    if(scenario==L"missing-person-map")put<uintptr_t>(root+0x148+952*8,0);
    if(scenario==L"wrong-world-source")put<BYTE>(world+0x3A,2);
    cfg.base=base;cfg.attemptToken=0xCC6303;cfg.lifecycle=&lifecycle;cfg.bytes=&bytes;cfg.intentPath=argv[2];memset(cfg.ownerBinding,0x63,32);cfg.validateAttachment=environment;cfg.fixtureWorkerCaller=uintptr_t(&TitleIdentityFixtureReturn);
    if(scenario==L"wrong-caller")++cfg.fixtureWorkerCaller;
    if(scenario==L"existing-intent"){auto f=CreateFileW(argv[2],GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);check(f!=INVALID_HANDLE_VALUE,"preexisting fixture intent");if(f!=INVALID_HANDLE_VALUE)CloseHandle(f);}
    check(ti::Initialize(adapter,cfg),"adapter initialize");check(!ti::Initialize(adapter,cfg),"no reset");
    CheckpointLoadWorkerBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(&TitleIdentityFixtureOriginal);bridge.before=ti::Before;bridge.after=ti::After;bridge.finally=ti::Finally;bridge.context=&adapter;check(CheckpointLoadWorkerBridgeConfigure(0,&bridge)==1,"real bridge configure");
    bool propagated=false;
    if(scenario==L"native-seh")propagated=runSeh();else if(scenario==L"native-cpp"){try{invoke(callable);}catch(int v){propagated=v==63;}}
    else{if(scenario==L"other-transparent")invoke(otherCallable);invoke(callable);if(scenario==L"duplicate-worker")invoke(callable);}
    ti::Report r{};ti::Snapshot(adapter,r);
    const bool positive=scenario==L"early"||scenario==L"late"||scenario==L"transition-during-native"||scenario==L"other-transparent"||scenario==L"nested-other";
    check(bool(r.receiptReady)==positive,"only exact identity handoff accepted");check(r.casAttempts<=1&&r.casApplied<=1,"at most one pair CAS");
    check(!r.active&&!r.planningReady&&!r.fullWorldVerified&&!r.initializerCallsDirectlyObserved,"finite cleanup and limited claim");
    CheckpointLoadWorkerOwner current{};check(!CheckpointLoadWorkerCurrentOwner(&current),"no stale worker TLS");CheckpointLoadWorkerBridgeStats stats{};CheckpointLoadWorkerBridgeSnapshot(0,&stats);check(!stats.active&&!stats.cleanup_faults,"real bridge drained");
    if(positive){check(r.commitReturned&&r.casApplied&&r.intentDurable&&r.postGuard&&r.identityObserved&&initializers==1,"one commit, original initializer substitute once");check(r.originalRax==0xABCD987612345678ull&&TitleIdentityFixtureRax==r.originalRax,"full native RAX preserved");unsigned char ff[16];memset(ff,0xff,16);check(!memcmp(r.originalXmm0,ff,16)&&!memcmp(TitleIdentityFixtureXmm,ff,16),"native XMM0 preserved");}
    if(scenario==L"other-transparent"||scenario==L"nested-other")check(r.otherWorkers==1&&nativeCalls==2,"shared nonTitle forwarded");
    if(scenario==L"native-seh"||scenario==L"native-cpp")check(propagated&&r.abnormal==1&&!r.nativeReturned&&r.casApplied&&r.intentDurable,"native exception propagates after committed pair; no rollback");
    if(scenario==L"cas-conflict")check(r.casAttempts==1&&!r.casApplied&&r.intentDurable,"CAS conflict retained no overwrite");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"error\":%ld,\"ready\":%u,\"report_bytes\":%zu,\"cas_attempts\":%u,\"cas_applied\":%u,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,r.error,r.receiptReady,sizeof r,r.casAttempts,r.casApplied);
    return failures?1:0;
}
