// Owned integration adaptation; frozen source unchanged. Rebind actual core objects to one production Owner.
#include "checkpoint_bound_forward_admission_controller.h"
#include "checkpoint_forward_planning_observer.h"
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
namespace ns=checkpoint_forward_native_session;namespace rq=checkpoint_load_request_commit;namespace bd=checkpoint_load_input_boundary;
namespace pr=checkpoint_forward_planning_observer;
namespace ad=checkpoint_bound_forward_admission;namespace hw=checkpoint_native_input_hwbp;namespace pd=checkpoint_bound_input_pending;
static hw::Context& hardwareContext=checkpoint_complete_live_owner::owner.hardware;static unsigned resolvedQueues=0,preAdmissionCalls=0;
static CheckpointPushFrame capturedAdmissionFrame{};
static void wrongThreadAfter();
static bool authorizeForeign=false;
static ad::Controller admission;static std::vector<unsigned> admissionTrace;static unsigned queueBodies=0,originalDepth=0;static bool queueObservedAuthorization=false;
extern "C" {
uintptr_t HwbpFixtureUser=0;
struct HardwareFixtureSnapshot {std::uint64_t gpr[16]{},rflags=0,reserved=0;std::uint8_t xmm[256]{};DWORD mxcsr=0,reserved2[3]{};};
HardwareFixtureSnapshot HwbpFixtureBefore{},HwbpFixtureAfter{};
alignas(16) unsigned char HwbpFixtureSeed[256]{};
std::int32_t HwbpFixtureFetched=-999;
void HwbpFixtureSite();extern unsigned char HwbpFixtureBeforeCall;
}
static void admissionEvent(void*,ad::Event e)noexcept{admissionTrace.push_back(unsigned(e));if(authorizeForeign&&e==ad::Event::Authorize)wrongThreadAfter();}

static pr::Observer& planning=checkpoint_complete_live_owner::owner.planning;static uintptr_t planningUser=0;static unsigned planningBodies=0;
static void captureBefore(const CheckpointPushFrame* f,void* context)noexcept{if(f)capturedAdmissionFrame=*f;pr::Before(f,context);}
static DWORD WINAPI foreignAfterThread(void*){ad::Controller::After(&capturedAdmissionFrame,&admission);return 0;}
static void wrongThreadAfter(){auto h=CreateThread(nullptr,0,foreignAfterThread,nullptr,0,nullptr);if(h){WaitForSingleObject(h,5000);CloseHandle(h);}}
static ns::Session& session=checkpoint_complete_live_owner::owner.session;static checkpoint_load_input_boundary_fixture::Layout layout;
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
        ++loadBodies;if(scenario==L"stop-during-load")StopCheckpointCompleteLiveOwner(nullptr);if(scenario==L"load-exception")RaiseException(0xE014CC92,0,0,nullptr);
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
static unsigned defaultControllerCalls=0;
static void defaultUserAfter(void*,ns::Session&,const CheckpointPushFrame*)noexcept{++defaultControllerCalls;}
static unsigned userBodies=0,menuBodies=0,gameBodies=0;static bool restoredInRequest=true;
static void createOwnedDebugConflict();
static bool storageValid(void*){return true;}
static bool exists(void*,const char*n){return !strcmp(n,by::TargetName);}
static std::int32_t fileSize(void*,const char*){return by::TargetSize;}
static bool sessionGuard(void*,ns::Point){return true;}
static bool requestGuard(void*,rq::Point p){
    if(scenario==L"stop-before-cas"&&p==rq::Point::BeforeCas)StopCheckpointCompleteLiveOwner(nullptr);
    if(scenario==L"stop-after-cas"&&p==rq::Point::AfterCas)StopCheckpointCompleteLiveOwner(nullptr);
    if(scenario==L"stop-restore-inflight"&&p==rq::Point::BeforeRead)restoredInRequest=session.RestoreBeforeCommit();
    return !(scenario==L"post-cas-reject"&&p==rq::Point::AfterCas);
}
extern "C" void GuestSessionUserBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++userBodies;
    if(planningUser){
        ++planningBodies;check(self==planningUser&&a==0x1001&&b==0x1002&&c==0x1003,"rebuilt User four arguments forwarded");
        if(scenario==L"user-exception")RaiseException(0xE014CCAE,0,0,nullptr);
    }else {
        check(self==layout.config.states[4]&&a==1&&b==2&&c==3,"old User four args survive wrapper");
        ++originalDepth;
        if(scenario==L"entry-ui"&&originalDepth==1)put<LONG>(layout.toolbar+0x88,13);
        if(scenario==L"original-exception")RaiseException(0xE014ADA1,0,0,nullptr);
        if(scenario==L"stop-original")StopCheckpointCompleteLiveOwner(nullptr);
        if(scenario==L"controller-stop-original")admission.Stop();
        if(scenario==L"wrong-thread-original")wrongThreadAfter();
        if(scenario==L"wrong-frame-original"){auto mismatch=capturedAdmissionFrame;mismatch.args[1]^=1;ad::Controller::After(&mismatch,&admission);}
        if(scenario==L"reentry"&&originalDepth==1)GuestSessionUserInvoke(self,a,b,c);
        if(scenario==L"hardware-stop-active")hw::Stop(hardwareContext);
        if(scenario!=L"missing-prefetch"){
            HwbpFixtureUser=self;admissionTrace.push_back(100);HwbpFixtureSite();admissionTrace.push_back(101);
        }
        if(scenario==L"hardware-repeat-site")HwbpFixtureSite();
        if(scenario==L"hardware-restore-conflict")createOwnedDebugConflict();
        if(scenario==L"late-ui")put<LONG>(layout.toolbar+0x88,19);
        --originalDepth;
    }
}
static bool planningGuard(void*,pr::Point point,std::uint64_t attempt,std::uint64_t epoch){
    return attempt==layout.config.attempt&&epoch==17&&!(scenario==L"epoch-after"&&point==pr::Point::After);
}
struct OwnedDebugConflict {HANDLE target=nullptr;bool ok=false;};
static DWORD WINAPI changeOwnedDebug(void* context){
    auto& d=*static_cast<OwnedDebugConflict*>(context);if(SuspendThread(d.target)==DWORD(-1))return 1;
    CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;d.ok=GetThreadContext(d.target,&c)!=0;
    if(d.ok){c.Dr1=0xABCDEF00;d.ok=SetThreadContext(d.target,&c)!=0;}
    if(ResumeThread(d.target)==DWORD(-1))d.ok=false;return 0;
}
static void createOwnedDebugConflict(){
    OwnedDebugConflict d{};check(DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&d.target,0,FALSE,DUPLICATE_SAME_ACCESS)!=0,"duplicate only this owned fixture thread");
    auto h=CreateThread(nullptr,0,changeOwnedDebug,&d,0,nullptr);check(h&&WaitForSingleObject(h,5000)==WAIT_OBJECT_0&&d.ok,"independent owned debugger mutates DR1");
    if(h)CloseHandle(h);if(d.target)CloseHandle(d.target);
}
static bool invokePlanningUser(){
    __try {check(GuestSessionUserInvoke(planningUser,0x1001,0x1002,0x1003)==0xFEDCBA9876543210ull,"new User full RAX preserved");return false;}
    __except(GetExceptionCode()==0xE014CCAE?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}
}
static void rebuildPlanning(){
    // Explicit native reconstruction double, not evidence that game constructors
    // ran. Root/Motor are preserved; Game/Strategy/User are synthetic replacements.
    const auto game=alloc(4096),strategy=alloc(4096);
    planningUser=(scenario==L"success-reused"||scenario==L"cross-thread-reused")?layout.config.states[4]:alloc(4096);
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
static pd::Span nativeQueueDouble(void*) {
    ++queueBodies;ad::Report ar{};check(admission.Snapshot(ar),"queue report owner thread");
    queueObservedAuthorization=ar.begin==pd::Error::None&&ar.after.pending_admission_candidate&&ar.prefetch.capture_kind==hw::CaptureKind::HardwareExecuteContext&&ar.prefetch.captured==1&&ar.prefetch.restored==1&&ar.prefetch.error==hw::Error::None;
    check(queueObservedAuthorization,"actual Begin authorization precedes native queue double");
    admissionTrace.push_back(102);
    // The adapter never writes these bytes: the original queue body double does.
    put<uintptr_t>(base+0x19E7310+0x40,pending);put<std::uint64_t>(base+0x19E7310+0x38,1);
    put<DWORD>(cache+8,0);put<std::uint64_t>(base+0x19E7310+0x30,1);put<DWORD>(pending,0);put<uintptr_t>(pending+8,layout.config.menu);
    if(scenario==L"queue-exception")RaiseException(0xE014ADA2,0,0,nullptr);
    if(scenario==L"stop-queue")StopCheckpointCompleteLiveOwner(nullptr);
    if(scenario==L"wrong-menu")put<uintptr_t>(layout.config.menu,base+0x12DBD68);
    auto returned=layout.config.menu;
    if(scenario==L"foreign-menu"){
        returned=alloc(4096);memcpy(reinterpret_cast<void*>(returned),reinterpret_cast<void*>(layout.config.menu),0x480);
    }
    return {reinterpret_cast<const std::uint8_t*>(returned),0x480};
}
static bool invokeInitialUser(){
    __try {check(GuestSessionUserInvoke(layout.config.states[4],1,2,3)==0xFEDCBA9876543210ull,"old User full RAX preserved");return false;}
    __except(GetExceptionCode()==0xE014ADA1?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}
}
struct OwnedInvoker {HANDLE done=nullptr,release=nullptr,handle=nullptr;bool planning=false,exception=false;DWORD tid=0;};
static OwnedInvoker initialInvoker{},planningInvoker{};
static DWORD WINAPI ownedInvoke(void*p){auto& w=*static_cast<OwnedInvoker*>(p);w.tid=GetCurrentThreadId();
    if(w.planning){const auto worker=at<uintptr_t>(planningUser+0x50),handle=at<uintptr_t>(worker+8);put<DWORD>(handle+0x10,w.tid);w.exception=invokePlanningUser();}
    else w.exception=invokeInitialUser();
    SetEvent(w.done);WaitForSingleObject(w.release,10000);return 0;}
static bool runOwned(OwnedInvoker& w,bool planningCall){w.planning=planningCall;w.done=CreateEventW(nullptr,TRUE,FALSE,nullptr);w.release=CreateEventW(nullptr,TRUE,FALSE,nullptr);w.handle=CreateThread(nullptr,0,ownedInvoke,&w,0,nullptr);check(w.handle!=nullptr,"actual callback thread created");check(WaitForSingleObject(w.done,10000)==WAIT_OBJECT_0,"actual callback thread completes invocation");return w.exception;}
static void joinOwned(OwnedInvoker&w){if(!w.handle)return;SetEvent(w.release);check(WaitForSingleObject(w.handle,10000)==WAIT_OBJECT_0,"retained callback thread joins");CloseHandle(w.handle);CloseHandle(w.done);CloseHandle(w.release);w.handle=nullptr;}
static int finishReport(ns::Report&r,bool passedPhase){
    joinOwned(initialInvoker);joinOwned(planningInvoker);
    pr::Report p{};pr::Snapshot(planning,p);
    ad::Report ar{};check(admission.Snapshot(ar),"admission final snapshot");
    if(scenario==L"cross-thread-first"||scenario==L"cross-thread-both"||scenario==L"cross-thread-reused"||scenario==L"poststop-other-thread"){
        check(ar.initialized_thread==GetCurrentThreadId()&&ar.call_thread==initialInvoker.tid&&ar.call_thread!=ar.initialized_thread,"callback binds real worker rather than installer thread");
        check(ar.error==ad::Error::None&&!ar.blocked&&ar.finished&&ar.callback_bindings==1&&ar.ignored_before>=1&&ar.ignored_original>=1&&ar.ignored_after>=1,"finished controller ignores later frame before thread validation");
        if(scenario!=L"cross-thread-first")check(planningInvoker.tid!=initialInvoker.tid&&planningInvoker.tid!=ar.initialized_thread,"new User uses a distinct simultaneously alive worker");
    }
    if(scenario==L"authorize-foreign-after"||scenario==L"wrong-thread-original"||scenario==L"wrong-frame-original")check(ar.blocked&&ar.error==ad::Error::Pair&&!ar.queue_calls&&!r.casPublished,"foreign or mismatched actual callback terminally blocks before queue");
    if(r.initialized){
        check(r.dispatchExpectedOriginal[0]==uintptr_t(&GuestSessionUserOriginal),"expected slot value remains actual native original");
        check(r.dispatchEffectiveTarget[0]==uintptr_t(scenario==L"default-forward"?&GuestSessionUserOriginal:&CheckpointBoundForwardAdmissionOriginal),"separate immutable dispatch target observed");
        check(r.dispatchOverride[0]==(scenario==L"default-forward"?0u:1u),"explicit forwarding override status");
        for(unsigned i=1;i<4;++i)check(!r.dispatchOverride[i]&&r.dispatchExpectedOriginal[i]==r.dispatchEffectiveTarget[i],"other dispatch slots retain default original forwarding");
    }
    if(ar.menu_bound){
        check(ar.provider_begin&&ar.provider_snapshot&&ar.prefetch.capture_kind==hw::CaptureKind::HardwareExecuteContext&&ar.prefetch.site_rip==uintptr_t(&HwbpFixtureBeforeCall)&&ar.prefetch.captured==1&&ar.prefetch.restored==1&&ar.prefetch.finished==1&&!ar.prefetch.restore_uncertain,"bound menu rests on actual hardware site and completed restoration");
        check(resolvedQueues==1,"exact newly allocated queue resolved once after native return");
    }
    check(!ar.full_input_hold&&!ar.game_hook_installed,"partial admission cannot claim input hold");
    printf("ADMISSION queue=%u commit=%u bind=%u close=%u scope=%u/%u abnormal=%u error=%u prefetch=%u pending_after=%u trace=",ar.queue_calls,ar.commit_succeeded,ar.menu_bound,ar.closed,ar.scope_started,ar.scope_finished,ar.original_abnormal,unsigned(ar.error),unsigned(ar.prefetch.error),unsigned(ar.after.decision));
    for(auto event:admissionTrace)printf("%u,",event);puts("");
    check(!r.inputExclusionProven&&!r.presentationProven&&!r.nativePlanningReady&&!r.fullWorldVerified,"Session unsupported authority stays false");
    check(!p.fullWorldVerified&&!p.inputExclusionProven&&!p.pixelPresentationProven&&!p.oldStateDestructorsDirectlyObserved&&!p.allWorkersFinishedProven,"planning observation is not authority");
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"session_state\":%u,\"session_error\":%ld,\"cas\":%u,\"identity_ready\":%u,\"stop\":%u,\"phase_passed\":%s,\"planningBoundaryObserved\":%u,\"planning_error\":%ld,\"planning_field\":\"%s\",\"planning_inflight\":%u,\"session_active_dispatch\":%u,\"old_user_calls\":%u,\"new_user_calls\":%u,\"user_controller_calls\":%u,\"old_user_ignored_waiting\":%u,\"previous_user_address_reused\":%u,\"attempt\":%llu,\"identity_worker_call\":%llu,\"load_completion_call\":%llu,\"planning_user_call\":%llu,\"report_bytes\":%zu,\"upstream_receipts_fabricated\":false,\"game_access\":false,\"admission_queue\":%u,\"admission_commit\":%u,\"admission_bind\":%u,\"admission_error\":%u,\"hardware_prefetch_error\":%u,\"pending_error\":%u,\"scope_started\":%u,\"scope_finished\":%u,\"queue_bodies\":%u,\"native_fetched\":%d,\"initialized_thread\":%lu,\"call_thread\":%lu,\"planning_thread\":%lu,\"callback_bindings\":%u,\"admission_blocked\":%s,\"admission_finished\":%s,\"admission_active\":%s,\"slot_initially_native\":true,\"dispatch_override\":%u,\"expected_native_original\":%llu,\"effective_dispatch_target\":%llu,\"hardware_capture_kind\":%u,\"hardware_captured\":%u,\"hardware_restored\":%u,\"hardware_finished\":%u,\"hardware_restore_uncertain\":%u,\"hardware_error\":%u,\"hardware_site_rip\":%llu,\"hardware_call_id\":%llu,\"queue_resolutions\":%u,\"pre_admission_original_calls\":%u,\"initial_cache_mode\":0,\"initial_queue_vector_empty\":true}\n",
        scenario.c_str(),failures?"false":"true",failures,unsigned(r.state),r.error,r.casPublished,r.identity.receiptReady,r.stopRequested,passedPhase?"true":"false",p.planningBoundaryObserved,p.error,p.failedField,p.inFlight,r.activeDispatch,userBodies-planningBodies,planningBodies,r.userControllerCalls,p.waitingForReceipt,p.previousUserAddressReused,p.attempt,p.identityWorkerCall,p.completedLoadCall,p.userCall,sizeof p,ar.queue_calls,ar.commit_succeeded,ar.menu_bound,unsigned(ar.error),unsigned(ar.prefetch.error),unsigned(ar.after.error),ar.scope_started,ar.scope_finished,queueBodies,HwbpFixtureFetched,ar.initialized_thread,ar.call_thread,planningInvoker.tid,ar.callback_bindings,ar.blocked?"true":"false",ar.finished?"true":"false",ar.active?"true":"false",r.dispatchOverride[0],r.dispatchExpectedOriginal[0],r.dispatchEffectiveTarget[0],unsigned(ar.prefetch.capture_kind),ar.prefetch.captured,ar.prefetch.restored,ar.prefetch.finished,ar.prefetch.restore_uncertain,unsigned(ar.prefetch.error),ar.prefetch.site_rip,ar.prefetch.call_id,resolvedQueues,preAdmissionCalls);
    return failures?1:0;
}

int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=5)return 2;scenario=argv[1];archive.resize(by::TargetSize);buffer.resize(by::TargetSize);
    FILE*file=nullptr;_wfopen_s(&file,argv[2],L"rb");if(!file)return 3;check(fread(archive.data(),1,archive.size(),file)==archive.size(),"complete local archive");check(fgetc(file)==EOF,"archive exact size");fclose(file);setup();
    ns::Config c{};c.request.boundary=layout.config;c.request.boundary.menu=0;c.request.localPath=argv[2];c.request.intentPath=argv[3];memset(c.request.ownerBinding,0x63,32);c.request.validate=requestGuard;
    c.request.storage={reinterpret_cast<void*>(storage),exists,fileSize,reinterpret_cast<native_storage_read::FileRead>(&GuestSessionReadOriginal),storageValid,nullptr};
    c.bytes.base=base;c.bytes.storage=storage;c.bytes.storageVtable=storage+16;c.bytes.readMethod=uintptr_t(&GuestSessionReadOriginal);c.bytes.attemptToken=layout.config.attempt;c.bytes.validateAttachment=byteGuard;c.bytes.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);c.bytes.fixtureReadCaller=uintptr_t(&GuestSessionReadReturn);c.bytes.fixtureParentCaller=0xAABBCC1234567890ull;GuestSessionParent=c.bytes.fixtureParentCaller;
    c.lifecycle.base=base;c.lifecycle.attemptToken=layout.config.attempt;c.lifecycle.validateAttachment=lifeGuard;c.lifecycle.fixtureUpdateCaller=uintptr_t(&GuestSessionUpdateReturn);
    c.identity.base=base;c.identity.attemptToken=layout.config.attempt;c.identity.intentPath=argv[4];memset(c.identity.ownerBinding,0x63,32);c.identity.validateAttachment=identityGuard;c.identity.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);
    c.validate=sessionGuard;c.userAfter=ad::Controller::UserAfter;c.context=&admission;
    pr::Config planningConfig{};planningConfig.base=base;planningConfig.attempt=layout.config.attempt;planningConfig.epoch=17;
    planningConfig.persistentRootState=layout.config.states[0];planningConfig.persistentMotorState=layout.config.states[1];planningConfig.previousUser=layout.config.states[4];planningConfig.session=&session;planningConfig.validate=planningGuard;planningConfig.fixtureCaller=uintptr_t(&GuestSessionUserReturn);
    if(scenario==L"stale-attempt")++planningConfig.attempt;
    check(planningConfig.syntheticReceipt==nullptr,"no synthetic upstream report supplied");
    check(pr::Initialize(planning,planningConfig),"observer bound to actual Session before hook installation");
    ad::Config ac{};ac.session=&session;ac.attempt=layout.config.attempt;ac.original=&GuestSessionUserOriginal;
    ac.expected_prefetch_site=uintptr_t(&HwbpFixtureBeforeCall)+(scenario==L"wrong-site"?1:0);
    ac.queue=nativeQueueDouble;ac.next_before=captureBefore;ac.next_after=pr::After;ac.next_context=&planning;ac.trace=admissionEvent;
    ac.pending.binding.attempt.fill(0xA1);ac.pending.binding.attachment.fill(0xB2);ac.pending.binding.owner_generation=17;
    ac.pending.profile_base=base;memcpy(ac.pending.states,layout.config.states,sizeof ac.pending.states);
    const auto span=[](uintptr_t address,size_t size){return pd::Span{reinterpret_cast<const std::uint8_t*>(address),size};};
    ac.pending.user=span(layout.config.states[4],0x668);ac.pending.toolbar=span(layout.toolbar,0x8C);
    ac.pending.game=span(layout.config.states[2],0x488);ac.pending.panel=span(layout.panel,0x1F8);
    ac.pending.manager=span(base+0x19E7310,0x50);ac.pending.stack=span(stackArray,0x30);ac.pending.queue={};ac.pending.load_cache=span(cache,0x3F4);
    ac.pending.expected_initial_cache_mode=0;
    ac.pending.resolve_created_queue=[](void*,uintptr_t address,std::size_t bytes)noexcept->pd::Span{++resolvedQueues;if(address!=pending||bytes!=16)return {};return {reinterpret_cast<const std::uint8_t*>(pending),16};};
    put<std::uint64_t>(base+0x19E7310+0x30,0);put<std::uint64_t>(base+0x19E7310+0x38,0);put<uintptr_t>(base+0x19E7310+0x40,0);
    put<uintptr_t>(base+0x19E7310+0x48,layout.config.states[4]);put<DWORD>(cache+8,0);
    hw::Config hardware{};hardware.binding=ac.pending.binding;hardware.site_rip=uintptr_t(&HwbpFixtureBeforeCall);
    check(hw::Initialize(hardwareContext,hardware),"hardware provider initialized for actual owned native site");ac.prefetch_provider=hw::MakeProvider(hardwareContext);
    if(scenario==L"player-pending"||scenario==L"restore-native-slot")put<LONG>(layout.toolbar+0x88,6);
    check(admission.Initialize(ac),"shared admission controller binds actual pending buffers");
    c.userObservationBefore=ad::Controller::Before;c.userObservationAfter=ad::Controller::After;c.userObservationContext=&admission;
    uintptr_t labels[]={uintptr_t(&GuestSessionUserReturn),uintptr_t(&GuestSessionMenuReturn),uintptr_t(&GuestSessionGameReturn),uintptr_t(&GuestSessionUpdateReturn)};memcpy(c.fixtureDispatchCaller,labels,sizeof labels);
    void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
    void* bridges[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};
    GuestSessionSlots=reinterpret_cast<void**>(alloc(0x1000));for(unsigned i=0;i<6;++i){GuestSessionSlots[i]=originals[i];c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};}
    check(GuestSessionSlots[0]==reinterpret_cast<void*>(&GuestSessionUserOriginal),"fixture never preinstalls wrapper");
    c.dispatchForwardTargets[0]=reinterpret_cast<void*>(&CheckpointBoundForwardAdmissionOriginal);
    if(scenario==L"default-forward"){
        c.dispatchForwardTargets[0]=nullptr;c.userObservationBefore=nullptr;c.userObservationAfter=nullptr;c.userObservationContext=nullptr;c.userAfter=defaultUserAfter;
    }
    if(scenario==L"bad-native-original")c.hooks[0].original=reinterpret_cast<void*>(&GuestSessionGameOriginal);
    if(scenario==L"forward-hook-cycle")c.dispatchForwardTargets[0]=bridges[0];
    DWORD protection=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&protection)!=0,"fixture slot page readonly");
    if(scenario==L"bad-native-original"||scenario==L"forward-hook-cycle"){
        check(!session.Initialize(c),"invalid native expectation or recursive target rejected before arm");
        for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"rejected initialization leaves native slots untouched");
        ns::Report rejected{};session.Snapshot(rejected);check(!rejected.armed&&!rejected.casPublished&&!userBodies&&!queueBodies&&!rejected.dispatchStats[0].configured,"no forwarding publication or native call on invalid config");
        return finishReport(rejected,true);
    }
    check(session.Initialize(c),"Session initializes before menu exists");
    for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"Initialize does not preinstall a wrapper");
    if(scenario==L"pre-admission-original-forward"){
        const auto configured=reinterpret_cast<ad::Original>(bridges[0]);
        check(configured(layout.config.states[4],1,2,3)==0xFEDCBA9876543210ull,"configured not-yet-accepting dispatcher forwards native once");
        ++preAdmissionCalls;ad::Report early{};admission.Snapshot(early);ns::Report earlySession{};session.Snapshot(earlySession);
        check(userBodies==1&&!early.blocked&&early.error==ad::Error::None&&!early.active&&!early.scope_started&&!early.callback_bindings&&!early.provider_begin&&!early.prefetch.entered&&!queueBodies&&!earlySession.userControllerCalls,"no BEFORE means no provider or authorization and no poisoned attempt");
        check(admissionTrace.size()==2&&admissionTrace[0]==100&&admissionTrace[1]==101,"pre-admission native body alone executes");admissionTrace.clear();
    }
    check(session.ArmHooks(),"all six hook slots armed");for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"correct published slot");
    if(scenario==L"stop-before-user")StopCheckpointCompleteLiveOwner(nullptr);
    if(scenario==L"controller-stop-before")admission.Stop();
    authorizeForeign=scenario==L"authorize-foreign-after";
    const bool crossThread=scenario==L"cross-thread-first"||scenario==L"cross-thread-both"||scenario==L"cross-thread-reused"||scenario==L"poststop-other-thread";
    const bool originalException=crossThread?runOwned(initialInvoker,false):invokeInitialUser();ns::Report r{};session.Snapshot(r);ad::Report ar{};admission.Snapshot(ar);
    if(scenario==L"default-forward"||scenario==L"restore-native-slot"){
        check(!originalException&&userBodies==1&&!queueBodies&&!r.casPublished,"native body ran once with no request");
        if(scenario==L"default-forward")check(defaultControllerCalls==1&&!ar.original_calls&&!ar.scope_started&&r.dispatchStats[0].native_returned==1,"null override uses native directly without wrapper");
        else check(ar.blocked&&ar.scope_started==1&&ar.closed==1&&HwbpFixtureFetched==6,"actual scoped wrapper rejects original pending input");
        const auto cached=reinterpret_cast<ad::Original>(bridges[0]);
        check(RestoreCheckpointCompleteLiveOwnerBeforeCommit(nullptr)==0,"pre-CAS restoration succeeds");
        for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"restoration returns actual native values, never wrapper");
        check(cached(layout.config.states[4],1,2,3)==0xFEDCBA9876543210ull,"cached immutable dispatch still forwards native once");
        session.Snapshot(r);check(userBodies==2&&!queueBodies&&!r.casPublished&&!r.activeDispatch&&r.hooksRestored,"late forwarding does not revive requests");
        return finishReport(r,true);
    }
    if(ar.after_calls){
        check(ar.native_rax==0xFEDCBA9876543210ull,"AFTER observes full original RAX across common wrapper");
        for(auto byte:ar.native_xmm0)check(byte==255,"AFTER observes original XMM0 across common wrapper");
    }
    const bool reject=scenario==L"hardware-stop-active"||scenario==L"hardware-repeat-site"||scenario==L"hardware-restore-conflict"||scenario==L"authorize-foreign-after"||scenario==L"wrong-thread-original"||scenario==L"wrong-frame-original"||scenario==L"controller-stop-original"||scenario==L"controller-stop-before"||scenario==L"player-pending"||scenario==L"entry-ui"||scenario==L"late-ui"||scenario==L"missing-prefetch"||scenario==L"wrong-site"||scenario==L"wrong-menu"||scenario==L"foreign-menu"||scenario==L"queue-exception"||scenario==L"original-exception"||scenario==L"reentry"||scenario==L"stop-original"||scenario==L"stop-before-user"||scenario==L"stop-queue";
    if(reject){
        const bool queued=scenario==L"wrong-menu"||scenario==L"foreign-menu"||scenario==L"queue-exception"||scenario==L"stop-queue";
        check(!r.menuBound&&!r.casPublished&&!r.request.casAttempts&&!ar.menu_bound,"rejected admission never binds or publishes CAS");
        check(queueBodies==(queued?1u:0u)&&ar.queue_calls==queueBodies,"refused pending never invokes original queue");
        check(userBodies==(scenario==L"reentry"?2u:1u),"original continues despite refusal");
        const unsigned expectedScope=(scenario==L"stop-before-user"||scenario==L"controller-stop-before")?0u:1u;
        check(ar.scope_started==expectedScope&&ar.scope_finished==expectedScope,"Scope spans admitted original; stopped late calls forward without admission");
        if(scenario==L"hardware-stop-active")check(ar.prefetch.error==hw::Error::Stopped&&ar.prefetch.restored&&!ar.prefetch.observer_calls,"hardware Stop closes observer without suppressing original");
        if(scenario==L"hardware-repeat-site")check(ar.prefetch.error==hw::Error::Repeated&&ar.prefetch.restored&&ar.prefetch.observer_calls==1,"repeated hardware boundary cannot authorize even when pending looks clean");
        if(scenario==L"hardware-restore-conflict")check(ar.prefetch.error==hw::Error::RestoreConflict&&ar.prefetch.restore_uncertain&&!ar.prefetch.restored&&ar.after.pending_admission_candidate,"clean pending alone cannot authorize after DR ownership conflict");
        if(scenario==L"player-pending"||scenario==L"entry-ui"){
            const int expected=scenario==L"player-pending"?6:13;
            check(HwbpFixtureFetched==expected&&at<LONG>(layout.toolbar+0x88)==-1,"native original alone latches and clears player's request");
            check(ar.prefetch.pending.menu_command==expected&&!ar.after.pending_admission_candidate,"transient request remains rejection after original cleared it");
        }
        if(scenario==L"late-ui")check(HwbpFixtureFetched==-1&&at<LONG>(layout.toolbar+0x88)==19,"after-prefetch UI remains intact and blocks admission");
        if(scenario==L"missing-prefetch")check(ar.after.error==pd::Error::NoCleanPrefetch,"missing real prefetch cannot fabricate receipt");
        if(scenario==L"wrong-site")check(ar.prefetch.captured==1&&ar.prefetch.site_rip!=ac.expected_prefetch_site&&ar.error==ad::Error::Prefetch,"wrong callsite cannot produce admission");
        if(scenario==L"original-exception"){
            check(originalException&&ar.original_abnormal==1&&!ar.after_calls&&!r.dispatchAfter[0]&&r.dispatchStats[0].abnormal_exits==1,"original SEH propagates without fake AFTER");
            HwbpFixtureUser=layout.config.states[4];HwbpFixtureSite();ad::Report later{};admission.Snapshot(later);
            check(later.prefetch.error==ar.prefetch.error&&later.scope_finished==1,"outside-original site cannot update expired Scope report");
        }else check(!originalException&&r.dispatchStats[0].active==0,"normal dispatch drained");
        if(scenario==L"reentry")check(ar.reentry==1&&r.error!=0,"nested original forwards but latches admission rejection");
        if(queued)check(at<std::uint64_t>(base+0x19E7310+0x30)==1,"rejected queued result retained, never cancelled or hidden");
        // Frozen Session first-User policy consumes the controller opportunity
        // even after refusal; same attempt cannot silently retry on a later frame.
        if(scenario==L"player-pending"||scenario==L"entry-ui"||scenario==L"missing-prefetch"){
            const auto oldCalls=userBodies;GuestSessionUserInvoke(layout.config.states[4],1,2,3);session.Snapshot(r);
            check(userBodies==oldCalls+1&&!queueBodies&&!r.casPublished&&r.userControllerCalls==1,"subsequent original frame runs, refused attempt never retries queue");
        }
        return finishReport(r,true);
    }
    check(userBodies==1+preAdmissionCalls&&r.userControllerCalls==1&&queueBodies==1&&ar.commit_succeeded==1&&ar.menu_bound==1&&ar.closed==1,"real paired admission and queue commit bound once");
    const unsigned expectedTrace[]={0,1,100,101,2,4,5,102,6,7,8,9};
    check(admissionTrace.size()==sizeof(expectedTrace)/sizeof(*expectedTrace)&&!memcmp(admissionTrace.data(),expectedTrace,sizeof expectedTrace),"BEFORE original mid-prefetch AFTER authorize queue commit bind close ordering");
    check(r.menuBound&&r.state==ns::State::MenuQueued,"menu bound at owned User AFTER");
    if(scenario==L"poststop-other-thread")admission.Stop();
    // Explicit dispatcher push/Init double: real Session will observe first
    // Menu Update via its already installed pointer, not a fixture distributor.
    put<std::uint64_t>(base+0x19E7310+0x10,6);put<uintptr_t>(stackArray+40,layout.config.menu);put<std::uint64_t>(base+0x19E7310+0x30,0);layout.setStage(bd::Stage::MenuAfter);
    GuestSessionMenuInvoke(layout.config.menu,0x1001,0x1002,0x1003);session.Snapshot(r);check(r.request.menuObserved&&menuBodies==1,"first native Menu Update paired");
    if(scenario==L"controller-error")check(!session.BindQueuedMenu({}),"out-of-bound controller error recorded");
    if(scenario==L"stop-before-game")StopCheckpointCompleteLiveOwner(nullptr);
    layout.setStage(bd::Stage::GameBefore);GuestSessionGameInvoke(layout.config.states[2],0x1001,0x1002,0x1003);session.Snapshot(r);
    const bool preRejected=scenario==L"stop-before-game"||scenario==L"controller-error"||scenario==L"stop-before-cas"||scenario==L"stop-restore-inflight"||scenario==L"preflight-corrupt";
    if(preRejected){check(!r.casPublished&&!r.mayHavePublished&&gameBodies==1,"prepublication rejection never CAS, native still forwards");if(scenario==L"stop-restore-inflight")check(!restoredInRequest,"inflight Restore refused");check(RestoreCheckpointCompleteLiveOwnerBeforeCommit(nullptr)==0,"settled pre-CAS hook cleanup");session.Snapshot(r);for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==originals[i],"all originals restored");return finishReport(r,true);}
    check(r.casPublished&&r.mayHavePublished&&r.request.casAttempts==1&&r.request.intentDurable&&r.request.read.matched&&readCalls==2,"durable request and actual Verify reads");
    if(scenario==L"post-cas-reject"||scenario==L"stop-after-cas")check(r.request.state==rq::State::Uncertain,"false after CAS retained as uncertain");
    if(scenario==L"stop-after-cas"){check(RestoreCheckpointCompleteLiveOwnerBeforeCommit(nullptr)!=0,"published request cannot unhook");for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"post-CAS observers retained");}
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
    rebuildPlanning();const bool userException=(crossThread&&scenario!=L"cross-thread-first")?runOwned(planningInvoker,true):invokePlanningUser();session.Snapshot(r);pr::Report p{};pr::Snapshot(planning,p);
    const bool planningPass=identityPass&&scenario!=L"report-state"&&scenario!=L"stale-attempt"&&scenario!=L"epoch-after"&&scenario!=L"user-exception";
    check(bool(p.planningBoundaryObserved)==planningPass,"actual Session receipts drive same-bridge new User observation");
    check(userBodies==2+preAdmissionCalls&&planningBodies==1&&r.userControllerCalls==1,"old/new original once each, controller never repeated");
    check(p.waitingForReceipt>=1,"early old User did not poison planning observer");
    if(planningPass){
        check(p.attempt==r.attempt&&p.identityWorkerCall==r.identity.workerCall&&p.completedLoadCall==r.lifecycle.completedCall,"planning receipt tied to actual Session producer IDs");
        check(p.nativeRax==0xFEDCBA9876543210ull&&!p.inFlight&&p.after==1&&!p.error,"paired original result recorded");
        for(unsigned i=0;i<16;++i)check(p.nativeXmm0[i]==255,"native XMM0 captured intact");
        check(bool(p.previousUserAddressReused)==(scenario==L"success-reused"||scenario==L"cross-thread-reused"),"old User ABA allowed by new receipt, not pointer inequality");
    }
    if(scenario==L"user-exception")check(userException&&p.inFlight==1&&!p.nativeReturned&&r.activeDispatch==1&&r.dispatchStats[0].abnormal_exits==1,"native User exception propagates with outstanding observation");
    else check(!r.activeDispatch&&!p.inFlight,"normal new User callbacks drain");
    if(scenario==L"stale-attempt")check(p.error==LONG(pr::Error::Receipt),"receipt from other attempt rejected");
    if(scenario==L"report-state")check(p.error==LONG(pr::Error::Stack),"old report still on formal stack blocks planning receipt");
    if(scenario==L"stop-after-cas")check(p.sessionStopRequested&&r.state==ns::State::RetainingObservation,"Stop retains planning observation, no completion authority");
    if(scenario==L"post-cas-reject")check(p.sessionHadError&&r.state==ns::State::Uncertain,"Session error remains visible even with observed planning");
    return finishReport(r,true);
}
