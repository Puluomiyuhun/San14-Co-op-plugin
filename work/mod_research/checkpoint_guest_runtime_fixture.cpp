// Independent fixture extracted from checkpoint_planning_return_observer_session_fixture.cpp
// Frozen source SHA256: c3184fcf572a8a7380b622a2ff20a37e7b149821985b5e9dc132e0a401fdfa0f
#include "checkpoint_guest_native_session.h"
#include "checkpoint_planning_return_observer.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
namespace ti=checkpoint_title_identity_adapter;namespace lc=checkpoint_cc_load_lifecycle;namespace by=checkpoint_cc_load_observer;namespace pc=checkpoint_identity_pair_commit;
extern "C" {
std::uint64_t GuestSessionWorkerInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionReadInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionUpdateInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionWorkerOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionReadOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionUpdateOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void GuestSessionWorkerReturn();void GuestSessionReadReturn();void GuestSessionUpdateReturn();
void** GuestSessionSlots=nullptr;
std::uint64_t GuestSessionUserInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionMenuInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionGameInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionUserOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionMenuOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionGameOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void GuestSessionUserReturn();void GuestSessionMenuReturn();void GuestSessionGameReturn();
std::uint64_t GuestSessionParent=0,GuestSessionReadRax=0,GuestSessionWorkerRax=0;
unsigned char GuestSessionReadXmm[16]{},GuestSessionWorkerXmm[16]{};
unsigned char GuestSessionPattern[32]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16};
}
namespace ns=checkpoint_guest_native_session;namespace rq=checkpoint_load_request_commit;namespace bd=checkpoint_load_input_boundary;
namespace pr=checkpoint_planning_return_observer;
static std::uint64_t runtimeAttempt=0,runtimeEpoch=0;
static unsigned char runtimeBinding[32]{};
static pr::Observer planning;static uintptr_t planningUser=0;static unsigned planningBodies=0;
static ns::Session session;static checkpoint_load_input_boundary_fixture::Layout layout;
static uintptr_t base,root,world,title,load,stackArray,loadCallable,titleCallable,otherCallable,forceA,forceB,personA,personB,districtA,districtB,closure,cache,pending,storage;
static pc::Pair sourcePair,targetPair;static std::wstring scenario;static std::vector<unsigned char> archive,buffer;
static unsigned failures=0,workerCalls=0,readCalls=0,updateCalls=0,initializers=0,loadBodies=0,otherBodies=0,joinCalls=0;
static volatile LONG loadException=0;static HANDLE loadThread=nullptr;
template<class T>static void put(uintptr_t p,T x){memcpy(reinterpret_cast<void*>(p),&x,sizeof x);}
template<class T>static T at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static uintptr_t alloc(size_t size){return uintptr_t(VirtualAlloc(nullptr,size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));}
static void check(bool x,const char*s){if(!x){++failures;printf("FAIL: %s\n",s);}}
static void sso(uintptr_t p,const char*s){memset(reinterpret_cast<void*>(p),0,32);memcpy(reinterpret_cast<void*>(p),s,strlen(s)+1);put<std::uint64_t>(p+16,strlen(s));put<std::uint64_t>(p+24,15);}
static bool byteGuard(void*,by::Point,uintptr_t l,uintptr_t t){return l==load&&t==title;}
static bool lifeGuard(void*,lc::Point,uintptr_t l,uintptr_t t){return l==load&&t==title;}
static bool identityGuard(void*,ti::Point,uintptr_t t,uintptr_t r,uintptr_t w){return t==title&&r==root&&w==world;}
static void invokeWorker(uintptr_t self){GuestSessionWorkerInvoke(self,0x1122334455667788ull,0x8877665544332211ull,0x123456789abcdef0ull);}
extern "C" std::uint64_t GuestSessionReadBody(std::uint64_t self,std::uint64_t name,std::uint64_t data,std::uint64_t amount){
    ++readCalls;check(self==storage&&strcmp(reinterpret_cast<char*>(name),by::TargetName)==0&&amount==by::TargetSize,"actual read arguments");
    if(scenario==L"read-exception"&&readCalls>=3)RaiseException(0xE014CC91,0,0,nullptr);
    memcpy(reinterpret_cast<void*>(data),archive.data(),archive.size());
    if((scenario==L"actual-byte-mismatch"&&readCalls>=3)||scenario==L"preflight-corrupt")reinterpret_cast<unsigned char*>(data)[15363]^=1;
    return 0xFEDCBA9800000000ull|by::TargetSize;
}
extern "C" void GuestSessionWorkerBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++workerCalls;check(a==0x1122334455667788ull&&b==0x8877665544332211ull&&c==0x123456789abcdef0ull,"generic four argument ABI");
    if(self==otherCallable){++otherBodies;return;}
    if(self==loadCallable){
        ++loadBodies;if(scenario==L"stop-during-load")session.Stop();if(scenario==L"load-exception")RaiseException(0xE014CC92,0,0,nullptr);
        GuestSessionReadInvoke(storage,uintptr_t(by::TargetName),uintptr_t(buffer.data()),by::TargetSize);
        put<DWORD>(base+0x201EC08,1);return;
    }
    check(self==titleCallable,"known generic callable dispatch");
    if(scenario==L"title-exception")RaiseException(0xE014CC93,0,0,nullptr);
    ++initializers;
    // Native Title worker/2FC850 substitute. Adapter never invokes this body.
    auto chosen=at<pc::Pair>(title+0x4A0);put<BYTE>(world+0x3A,chosen.person==personB?2:12);put<BYTE>(world+0x165D,1);
    put<DWORD>(title+0x470,15);put<std::uint64_t>(base+0x19E7310+0x10,3);
}
static DWORD WINAPI loadEntry(void*){
    __try {invokeWorker(loadCallable);return 0;}
    __except(GetExceptionCode()==0xE014CC91||GetExceptionCode()==0xE014CC92?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){InterlockedExchange(&loadException,1);return 1;}
}
extern "C" void GuestSessionUpdateBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++updateCalls;check(self==load&&a==1&&b==2&&c==3,"update four argument ABI");
    auto phase=at<DWORD>(load+0x470);
    // Explicit native-body doubles, never direct writes to observer/lifecycle receipts.
    if(phase==1){put<uintptr_t>(load+0x478+0x48,loadCallable);put<DWORD>(load+0x470,2);loadThread=CreateThread(nullptr,0,loadEntry,nullptr,0,nullptr);check(loadThread!=nullptr,"OS worker creation");put<uintptr_t>(load+0x478,uintptr_t(loadThread));put<uintptr_t>(load+0x480,0x7788);put<uintptr_t>(load+0x4D8,uintptr_t(loadThread));}
    else if(phase==2){check(loadThread&&WaitForSingleObject(loadThread,10000)==WAIT_OBJECT_0,"actual OS worker join");if(loadThread)CloseHandle(loadThread);loadThread=nullptr;++joinCalls;put<uintptr_t>(load+0x478,0);put<uintptr_t>(load+0x480,0);put<uintptr_t>(load+0x4D8,0);put<DWORD>(load+0x470,3);}
    else if(phase==3)put<DWORD>(load+0x470,4);
    else if(phase==4){put<DWORD>(load+8,at<DWORD>(base+0x201EC08)==1?0x7FFFFFFD:0x7FFFFFFE);put<DWORD>(base+0x201ECD0,0xffffffff);sso(base+0x201ECE0,"");put<DWORD>(cache+0x3EC,0xffffffff);put<std::uint64_t>(base+0x19E7310+0x30,1);put<DWORD>(pending,1);put<uintptr_t>(pending+8,0);}
}
static bool titleInvokeWithException(){__try{invokeWorker(titleCallable);return false;}__except(GetExceptionCode()==0xE014CC93?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
static void setup(){
    check(layout.initialize(bd::Stage::MenuAfter),"synthetic planning layout");base=layout.config.base;root=layout.config.root;world=layout.config.world;title=alloc(0x2000);load=alloc(0x1000);stackArray=layout.stack;
    forceA=alloc(0x1000);forceB=alloc(0x1000);personA=alloc(0x1000);personB=alloc(0x1000);districtA=alloc(0x1000);districtB=alloc(0x1000);
    check(base&&root&&world&&title&&load&&stackArray&&forceA&&forceB&&personA&&personB&&districtA&&districtB,"allocations");
    sourcePair={forceA,personA};targetPair={forceB,personB};loadCallable=title+0x700;titleCallable=title+0x740;otherCallable=title+0x780;closure=title+0x800;cache=layout.config.cache;storage=title+0xD00;pending=base+0x1000;
    put<uintptr_t>(base+0x1FCA1E0,root);put<uintptr_t>(root,base+0x12AA6B0);put<uintptr_t>(root+0x85130,world);put<uintptr_t>(world,base+0x12AA638);
    put<WORD>(world+0x34,203);put<BYTE>(world+0x36,8);put<BYTE>(world+0x37,11);put<BYTE>(world+0x3A,12);put<DWORD>(world+0x40,1);put<BYTE>(world+0x165D,2);put<DWORD>(world+0x20A8,1);
    put<uintptr_t>(root+0xDCA0+12*8,forceA);put<uintptr_t>(root+0xDCA0+2*8,forceB);put<uintptr_t>(root+0x148+666*8,personA);put<uintptr_t>(root+0x148+952*8,personB);put<uintptr_t>(root+0xDE40+11*8,districtA);put<uintptr_t>(root+0xDE40+2*8,districtB);
    put<uintptr_t>(forceA,base+0x129FE58);put<WORD>(forceA+0x10,666);put<BYTE>(forceA+0x47,6);put<uintptr_t>(forceB,base+0x129FE58);put<WORD>(forceB+0x10,952);put<BYTE>(forceB+0x47,7);
    put<uintptr_t>(personA,base+0x12A00D0);put<WORD>(personA+0x10,666);put<BYTE>(personA+0x118,11);put<uintptr_t>(personB,base+0x12A00D0);put<WORD>(personB+0x10,952);put<BYTE>(personB+0x118,2);
    put<uintptr_t>(districtA,base+0x129FEC8);put<BYTE>(districtA+0x10,12);put<BYTE>(districtA+0x11,1);put<WORD>(districtA+0x12,666);put<uintptr_t>(districtB,base+0x129FEC8);put<BYTE>(districtB+0x10,2);put<BYTE>(districtB+0x11,1);put<WORD>(districtB+0x12,952);
    put<uintptr_t>(title,base+0x12DAAF0);memcpy(reinterpret_cast<void*>(title+0x70),"CTitleState",12);put<DWORD>(title+0x47C,63);put<pc::Pair>(title+0x4A0,sourcePair);put<DWORD>(title+0x470,13);
    put<uintptr_t>(title+0x520+0x48,titleCallable);put<uintptr_t>(titleCallable,base+0x138E8C0);put<uintptr_t>(titleCallable+8,base+0x4DA390);put<uintptr_t>(loadCallable,base+0x138E8C0);put<uintptr_t>(loadCallable+8,base+0x508B40);put<uintptr_t>(otherCallable,base+0x138E8C0);put<uintptr_t>(otherCallable+8,base+0x1234);
    put<std::uint64_t>(base+0x19E7310+0x10,5);

    put<uintptr_t>(load,base+0x12DBD68);memcpy(reinterpret_cast<void*>(load+0x70),"CLoadState",11);put<DWORD>(load+0x470,1);put<uintptr_t>(load+0x48,closure);put<uintptr_t>(closure,base+0x12EA4D0);put<uintptr_t>(closure+8,title);put<uintptr_t>(base+0x12EA4D0+0x10,base+0x4FAC30);
    put<DWORD>(base+0x201ECD0,0xffffffff);sso(base+0x201ECE0,"");put<uintptr_t>(base+0x2025318,cache);put<DWORD>(cache+0x3EC,0xffffffff);put<uintptr_t>(base+0x19E7310+0x40,pending);
}
static unsigned userBodies=0,menuBodies=0,gameBodies=0;static bool restoredInRequest=true;
static bool storageValid(void*){return true;}
static bool exists(void*,const char*n){return !strcmp(n,by::TargetName);}
static std::int32_t fileSize(void*,const char*){return by::TargetSize;}
static bool sessionGuard(void*,ns::Point){return true;}
static bool requestGuard(void*,rq::Point p){
    if(scenario==L"stop-before-cas"&&p==rq::Point::BeforeCas)session.Stop();
    if(scenario==L"stop-after-cas"&&p==rq::Point::AfterCas)session.Stop();
    if(scenario==L"stop-restore-inflight"&&p==rq::Point::BeforeRead)restoredInRequest=session.RestoreBeforeCommit();
    return !(scenario==L"post-cas-reject"&&p==rq::Point::AfterCas);
}
extern "C" void GuestSessionUserBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++userBodies;
    if(planningUser){
        ++planningBodies;check(self==planningUser&&a==0x1001&&b==0x1002&&c==0x1003,"rebuilt User four arguments forwarded");
        if(scenario==L"user-exception")RaiseException(0xE014CCAE,0,0,nullptr);
    }else check(self==layout.config.states[4],"original User");
}
static bool planningGuard(void*,pr::Point point,std::uint64_t attempt,std::uint64_t epoch){
    return attempt==layout.config.attempt&&epoch==runtimeEpoch&&!(scenario==L"epoch-after"&&point==pr::Point::After);
}
static bool invokePlanningUser(){
    __try {check(GuestSessionUserInvoke(planningUser,0x1001,0x1002,0x1003)==0xFEDCBA9876543210ull,"new User full RAX preserved");return false;}
    __except(GetExceptionCode()==0xE014CCAE?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}
}
static void rebuildPlanning(){
    // Explicit native reconstruction double, not evidence that game constructors
    // ran. Root/Motor are preserved; Game/Strategy/User are synthetic replacements.
    const auto game=alloc(4096),strategy=alloc(4096);
    planningUser=scenario==L"success-reused"?layout.config.states[4]:alloc(4096);
    const uintptr_t states[]={layout.config.states[0],layout.config.states[1],game,strategy,planningUser};
    const uintptr_t vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    for(unsigned i=0;i<5;++i){put<uintptr_t>(stackArray+i*8,states[i]);put<uintptr_t>(states[i],base+vt[i]);memcpy(reinterpret_cast<void*>(states[i]+0x70),names[i],strlen(names[i])+1);put<DWORD>(states[i]+0x68,0);put<uintptr_t>(states[i]+0x50,0);}
    const auto manager=base+0x19E7310;
    put<std::uint64_t>(manager+0x10,5);put<std::uint64_t>(manager+0x30,0);put<uintptr_t>(manager+0x48,planningUser);
    put<DWORD>(planningUser+0x470,2);put<DWORD>(planningUser+0x6C,3);
    auto worker=alloc(4096),callable=worker+0x100,iterator=worker+0x200,handle=worker+0x300;
    put<uintptr_t>(planningUser+0x50,worker);put<uintptr_t>(worker+8,handle);put<uintptr_t>(worker+0x50,callable);put<DWORD>(handle+0x10,GetCurrentThreadId());put<uintptr_t>(callable,base+0x12F2440);put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(callable+8,iterator);put<uintptr_t>(iterator,stackArray+32);
    for(unsigned i=1;i<4;++i)put<std::uint64_t>(callable+8+i*8,0x1000+i);
    const auto toolbar=alloc(4096),panel=alloc(4096),gamePanel=alloc(4096);
    put<uintptr_t>(planningUser+0x478,toolbar);put<uintptr_t>(planningUser+0x618,panel);put<LONG>(toolbar+0x88,-1);put<uintptr_t>(game+0x480,gamePanel);
    put<DWORD>(base+0x1A38EC8+0x28,0);put<DWORD>(base+0x19E7510+0x13C,1);put<DWORD>(base+0x1FCA518,2);
    put<LONG>(base+0x201ED10,-1);sso(base+0x201ED18,"");sso(base+0x201ED38,"");
    if(scenario==L"report-state"){auto report=alloc(4096);memcpy(reinterpret_cast<void*>(report+0x70),"CReportDisplayState",20);put<uintptr_t>(stackArray+40,report);put<std::uint64_t>(manager+0x10,6);}
}

extern "C" void GuestSessionMenuBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){++menuBodies;check(self==layout.config.menu,"original Menu");}
extern "C" void GuestSessionGameBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){
    ++gameBodies;check(self==layout.config.states[2],"original Game");
    if(at<DWORD>(cache+0x3EC)==63){put<DWORD>(base+0x201ECD0,63);sso(base+0x201ECE0,by::TargetName);}
}
static void userAfterController(void*,ns::Session&owner,const CheckpointPushFrame*f){
    // Explicit normal QueueMenu double. It runs only inside production Session's
    // User AFTER, after all hooks are armed; no constructor is called by Session.
    put<std::uint64_t>(base+0x19E7310+0x30,1);put<DWORD>(pending,0);put<uintptr_t>(pending+8,layout.config.menu);
    ns::QueueReceipt r{};r.attempt=layout.config.attempt;r.userCall=f->call_id;r.thread=f->thread_id;r.user=uintptr_t(f->args[0]);r.menu=layout.config.menu;r.nativeQueueReturned=true;
    if(scenario==L"wrong-queue-receipt")++r.userCall;
    check(owner.BindQueuedMenu(r)==(scenario!=L"wrong-queue-receipt"),"same-call menu binding gate");
}
static int finishReport(ns::Report&r,bool passedPhase){
    pr::Report p{};pr::Snapshot(planning,p);
    check(!r.inputExclusionProven&&!r.presentationProven&&!r.nativePlanningReady&&!r.fullWorldVerified,"Session unsupported authority stays false");
    check(!p.fullWorldVerified&&!p.inputExclusionProven&&!p.pixelPresentationProven&&!p.oldStateDestructorsDirectlyObserved&&!p.allWorkersFinishedProven,"planning observation is not authority");
    (void)passedPhase;
    return failures?1:0;
}

static int runBoundSession(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=5)return 2;scenario=argv[1];archive.resize(by::TargetSize);buffer.resize(by::TargetSize);
    FILE*file=nullptr;_wfopen_s(&file,argv[2],L"rb");if(!file)return 3;check(fread(archive.data(),1,archive.size(),file)==archive.size(),"complete local archive");check(fgetc(file)==EOF,"archive exact size");fclose(file);setup();layout.config.attempt=runtimeAttempt;
    ns::Config c{};c.request.boundary=layout.config;c.request.boundary.menu=0;c.request.localPath=argv[2];c.request.intentPath=argv[3];memcpy(c.request.ownerBinding,runtimeBinding,32);c.request.validate=requestGuard;
    c.request.storage={reinterpret_cast<void*>(storage),exists,fileSize,reinterpret_cast<native_storage_read::FileRead>(&GuestSessionReadOriginal),storageValid,nullptr};
    c.bytes.base=base;c.bytes.storage=storage;c.bytes.storageVtable=storage+16;c.bytes.readMethod=uintptr_t(&GuestSessionReadOriginal);c.bytes.attemptToken=layout.config.attempt;c.bytes.validateAttachment=byteGuard;c.bytes.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);c.bytes.fixtureReadCaller=uintptr_t(&GuestSessionReadReturn);c.bytes.fixtureParentCaller=0xAABBCC1234567890ull;GuestSessionParent=c.bytes.fixtureParentCaller;
    c.lifecycle.base=base;c.lifecycle.attemptToken=layout.config.attempt;c.lifecycle.validateAttachment=lifeGuard;c.lifecycle.fixtureUpdateCaller=uintptr_t(&GuestSessionUpdateReturn);
    c.identity.base=base;c.identity.attemptToken=layout.config.attempt;c.identity.intentPath=argv[4];memcpy(c.identity.ownerBinding,runtimeBinding,32);c.identity.validateAttachment=identityGuard;c.identity.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);
    c.validate=sessionGuard;c.userAfter=userAfterController;
    pr::Config planningConfig{};planningConfig.base=base;planningConfig.attempt=layout.config.attempt;planningConfig.epoch=runtimeEpoch;
    planningConfig.persistentRootState=layout.config.states[0];planningConfig.persistentMotorState=layout.config.states[1];planningConfig.previousUser=layout.config.states[4];planningConfig.session=&session;planningConfig.validate=planningGuard;planningConfig.fixtureCaller=uintptr_t(&GuestSessionUserReturn);
    if(scenario==L"stale-attempt")++planningConfig.attempt;
    check(planningConfig.syntheticReceipt==nullptr,"no synthetic upstream report supplied");
    check(pr::Initialize(planning,planningConfig),"observer bound to actual Session before hook installation");
    c.userObservationBefore=pr::Before;c.userObservationAfter=pr::After;c.userObservationContext=&planning;
    uintptr_t labels[]={uintptr_t(&GuestSessionUserReturn),uintptr_t(&GuestSessionMenuReturn),uintptr_t(&GuestSessionGameReturn),uintptr_t(&GuestSessionUpdateReturn)};memcpy(c.fixtureDispatchCaller,labels,sizeof labels);
    void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
    void* bridges[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};
    GuestSessionSlots=reinterpret_cast<void**>(alloc(0x1000));for(unsigned i=0;i<6;++i){GuestSessionSlots[i]=originals[i];c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};}
    DWORD protection=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&protection)!=0,"fixture slot page readonly");
    check(session.Initialize(c),"Session initializes before menu exists");check(session.ArmHooks(),"all six hook slots armed");for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"correct published slot");
    if(scenario==L"stop-before-user"){session.Stop();GuestSessionUserInvoke(layout.config.states[4],1,2,3);ns::Report r{};session.Snapshot(r);check(!r.menuBound&&!r.userControllerCalls&&!r.casPublished,"stop suppresses controller only, original forwards");check(session.RestoreBeforeCommit(),"precommit cleanup");session.Snapshot(r);return finishReport(r,true);}
    GuestSessionUserInvoke(layout.config.states[4],1,2,3);ns::Report r{};session.Snapshot(r);check(userBodies==1&&r.userControllerCalls==1,"normal User precedes controller");
    if(scenario==L"wrong-queue-receipt"){check(!r.menuBound&&r.error!=0,"bad queue receipt refuses request initialization");check(session.RestoreBeforeCommit(),"bad bind precommit hook cleanup only");session.Snapshot(r);return finishReport(r,true);}
    check(r.menuBound&&r.state==ns::State::MenuQueued,"menu bound at owned User AFTER");
    // Explicit dispatcher push/Init double: real Session will observe first
    // Menu Update via its already installed pointer, not a fixture distributor.
    put<std::uint64_t>(base+0x19E7310+0x10,6);put<uintptr_t>(stackArray+40,layout.config.menu);put<std::uint64_t>(base+0x19E7310+0x30,0);layout.setStage(bd::Stage::MenuAfter);
    GuestSessionMenuInvoke(layout.config.menu,0x1001,0x1002,0x1003);session.Snapshot(r);check(r.request.menuObserved&&menuBodies==1,"first native Menu Update paired");
    if(scenario==L"controller-error")check(!session.BindQueuedMenu({}),"out-of-bound controller error recorded");
    if(scenario==L"stop-before-game")session.Stop();
    layout.setStage(bd::Stage::GameBefore);GuestSessionGameInvoke(layout.config.states[2],0x1001,0x1002,0x1003);session.Snapshot(r);
    const bool preRejected=scenario==L"stop-before-game"||scenario==L"controller-error"||scenario==L"stop-before-cas"||scenario==L"stop-restore-inflight"||scenario==L"preflight-corrupt";
    if(preRejected){check(!r.casPublished&&!r.mayHavePublished&&gameBodies==1,"prepublication rejection never CAS, native still forwards");if(scenario==L"stop-restore-inflight")check(!restoredInRequest,"inflight Restore refused");check(session.RestoreBeforeCommit(),"settled pre-CAS hook cleanup");session.Snapshot(r);for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"all originals restored");return finishReport(r,true);}
    check(r.casPublished&&r.mayHavePublished&&r.request.casAttempts==1&&r.request.intentDurable&&r.request.read.matched&&readCalls==2,"durable request and actual Verify reads");
    if(scenario==L"post-cas-reject"||scenario==L"stop-after-cas")check(r.request.state==rq::State::Uncertain,"false after CAS retained as uncertain");
    if(scenario==L"stop-after-cas"){check(!session.RestoreBeforeCommit(),"published request cannot unhook");for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"post-CAS observers retained");}
    put<std::uint64_t>(base+0x19E7310+0x10,4);put<uintptr_t>(stackArray+16,title);put<uintptr_t>(stackArray+24,load);put<std::uint64_t>(base+0x19E7310+0x30,0);
    invokeWorker(otherCallable);
    for(unsigned i=0;i<4;++i)check(GuestSessionUpdateInvoke(load,1,2,3)==0xFEDCBA9876543210ull,"production Load dispatcher forwarding");
    session.Snapshot(r);const bool bytePass=scenario!=L"actual-byte-mismatch"&&scenario!=L"load-exception"&&scenario!=L"read-exception";
    check(bool(r.bytes.observedWorkerAndBytes)==bytePass&&bool(r.lifecycle.receiptReady)==bytePass,"real bytes/lifecycle generated in Session");
    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_NOACCESS,&old)!=0,"old Load noaccess");
    if(scenario==L"success-late"){put<DWORD>(title+0x470,15);put<std::uint64_t>(base+0x19E7310+0x10,3);}
    bool titleException=titleInvokeWithException();session.Snapshot(r);const bool identityPass=bytePass&&scenario!=L"title-exception";
    check(bool(r.identity.receiptReady)==identityPass,"identity adapter runs in real shared Session dispatcher");
    check(workerCalls==3&&loadBodies==1&&otherBodies==1&&updateCalls==4&&joinCalls==1,"original counts across single Session");
    check(!r.activeDispatch&&!r.activeWorker&&!r.activeRead&&!r.workerStats.active&&!r.readStats.active,"normally paired callbacks drained");
    if(bytePass)check(r.identity.casApplied==1&&r.identity.intentDurable,"valid upstream allows one atomic identity pair");else check(!r.identity.casAttempts&&!r.identity.intentCreated,"failed load bytes blocks pair");
    if(scenario==L"load-exception"||scenario==L"read-exception")check(loadException&&r.bytes.workerAbnormal==1,"Load exception propagated");
    if(scenario==L"title-exception")check(titleException&&r.identity.abnormal==1&&!r.identity.nativeReturned,"Title exception propagated");
    if(scenario==L"post-cas-reject")check(r.state==ns::State::Uncertain&&r.identity.receiptReady,"post-CAS error does not abandon identity recovery");
    if(scenario==L"stop-after-cas"||scenario==L"stop-during-load")check(r.state==ns::State::RetainingObservation&&r.identity.receiptReady,"Stop preserves in-progress observation and identity recovery");
    // Do not call RestoreBeforeCommit here: it intentionally requests Stop.
    // The original Session suite covers refusal to restore after publication.
    session.Snapshot(r);for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"published observer pointers retained");
    // Previous lifecycle snapshots are owned receipts. Neither planning nor
    // Session slot0 is allowed to touch dead Load/Title objects from this point.
    check(VirtualProtect(reinterpret_cast<void*>(title),0x2000,PAGE_NOACCESS,&old)!=0,"historical Title noaccess before new User");
    rebuildPlanning();const bool userException=invokePlanningUser();session.Snapshot(r);pr::Report p{};pr::Snapshot(planning,p);
    const bool planningPass=identityPass&&scenario!=L"report-state"&&scenario!=L"stale-attempt"&&scenario!=L"epoch-after"&&scenario!=L"user-exception";
    check(bool(p.planningBoundaryObserved)==planningPass,"actual Session receipts drive same-bridge new User observation");
    check(userBodies==2&&planningBodies==1&&r.userControllerCalls==1,"old/new original once each, controller never repeated");
    check(p.waitingForReceipt>=1,"early old User did not poison planning observer");
    if(planningPass){
        check(p.attempt==r.attempt&&p.identityWorkerCall==r.identity.workerCall&&p.completedLoadCall==r.lifecycle.completedCall,"planning receipt tied to actual Session producer IDs");
        check(p.nativeRax==0xFEDCBA9876543210ull&&!p.inFlight&&p.after==1&&!p.error,"paired original result recorded");
        for(unsigned i=0;i<16;++i)check(p.nativeXmm0[i]==255,"native XMM0 captured intact");
        check(bool(p.previousUserAddressReused)==(scenario==L"success-reused"),"old User ABA allowed by new receipt, not pointer inequality");
    }
    if(scenario==L"user-exception")check(userException&&p.inFlight==1&&!p.nativeReturned&&r.activeDispatch==1&&r.dispatchStats[0].abnormal_exits==1,"native User exception propagates with outstanding observation");
    else check(!r.activeDispatch&&!p.inFlight,"normal new User callbacks drain");
    if(scenario==L"stale-attempt")check(p.error==LONG(pr::Error::Receipt),"receipt from other attempt rejected");
    if(scenario==L"report-state")check(p.error==LONG(pr::Error::Stack),"old report still on formal stack blocks planning receipt");
    if(scenario==L"stop-after-cas")check(p.sessionStopRequested&&r.state==ns::State::RetainingObservation,"Stop retains planning observation, no completion authority");
    if(scenario==L"post-cas-reject")check(p.sessionHadError&&r.state==ns::State::Uncertain,"Session error remains visible even with observed planning");
    return finishReport(r,true);
}

#include "checkpoint_guest_runtime_fixture_control.inc"
