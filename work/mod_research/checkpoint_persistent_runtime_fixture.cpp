#include "checkpoint_dynamic_native_session.h"
#include "checkpoint_persistent_planning_observer.h"
#include "checkpoint_persistent_authorized_controller.h"
#include "checkpoint_persistent_input_hwbp.h"
#include <type_traits>
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include "checkpoint_persistent_logical_adapter.h"
#include "checkpoint_persistent_route_six_adapter.h"
#include "checkpoint_persistent_physical_owner.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <tuple>
namespace ti=checkpoint_dynamic_title_identity_adapter;namespace lc=checkpoint_dynamic_cc_load_lifecycle;namespace by=checkpoint_dynamic_cc_load_observer;namespace pc=checkpoint_identity_pair_commit;
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
namespace ns=checkpoint_dynamic_native_session;namespace rq=checkpoint_dynamic_load_request_commit;namespace bd=checkpoint_load_input_boundary;
static checkpoint_dynamic_file_profile::Profile fileProfile{};
static checkpoint_dynamic_title_identity_adapter::WorldProfile worldProfile{};
static ns::Session* currentSession=nullptr;
static checkpoint_load_input_boundary_fixture::Layout* currentLayout=nullptr;
#define session (*currentSession)
#define layout (*currentLayout)
namespace la=checkpoint_persistent_logical_adapter;
namespace rt=checkpoint_persistent_route;
namespace po=checkpoint_persistent_physical_owner;
static po::Owner physicalOwner;
// Game build/attachment validator remains an explicit fixture double. Real
// physical owner, page protection, bridge installation and queue Adapter run.
static bool physicalGuard(void*,po::Point,unsigned) noexcept {return true;}
static po::Report physicalReport(){po::Report r{};physicalOwner.Snapshot(r);return r;}
static unsigned generationIndex=0;
extern "C" int CheckpointPersistentObserverClaim(const CheckpointLoadWorkerFrame*f,std::uint64_t t) noexcept {return la::Claim(f,t)?1:0;}
extern "C" int CheckpointPersistentObserverCurrentOwner(CheckpointLoadWorkerOwner*o) noexcept {return la::CurrentOwner(o)?1:0;}

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
    ++readCalls;check(self==storage&&strcmp(reinterpret_cast<char*>(name),fileProfile.name)==0&&amount==fileProfile.size,"actual read arguments");
    if(scenario==L"read-exception"&&readCalls>=3)RaiseException(0xE014CC91,0,0,nullptr);
    memcpy(reinterpret_cast<void*>(data),archive.data(),archive.size());
    if((scenario==L"actual-byte-mismatch"&&readCalls>=3)||scenario==L"preflight-corrupt")reinterpret_cast<unsigned char*>(data)[15363]^=1;
    return 0xFEDCBA9800000000ull|fileProfile.size;
}
extern "C" void GuestSessionWorkerBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++workerCalls;check(a==0x1122334455667788ull&&b==0x8877665544332211ull&&c==0x123456789abcdef0ull,"generic four argument ABI");
    if(self==otherCallable){++otherBodies;return;}
    if(self==loadCallable){
        ++loadBodies;if(scenario==L"stop-during-load")session.Stop();if(scenario==L"load-exception")RaiseException(0xE014CC92,0,0,nullptr);
        GuestSessionReadInvoke(storage,uintptr_t(fileProfile.name),uintptr_t(buffer.data()),fileProfile.size);
        // Owned native-load double restores incoming host A, even when this
        // client's pre-load current view was already B. Not world deserialization.
        put<BYTE>(world+0x3A,worldProfile.source.force);put<BYTE>(world+0x165D,2);
        put<WORD>(world+0x34,worldProfile.year);put<BYTE>(world+0x36,worldProfile.month);put<BYTE>(world+0x37,worldProfile.day);
        put<DWORD>(base+0x201EC08,1);return;
    }
    check(self==titleCallable,"known generic callable dispatch");
    if(scenario==L"title-exception")RaiseException(0xE014CC93,0,0,nullptr);
    ++initializers;
    // Native Title worker/2FC850 substitute. Adapter never invokes this body.
    auto chosen=at<pc::Pair>(title+0x4A0);put<BYTE>(world+0x3A,chosen.person==personB?worldProfile.target.force:worldProfile.source.force);put<BYTE>(world+0x165D,1);
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
    put<uintptr_t>(root+0xDCA0+worldProfile.source.force*8,forceA);put<uintptr_t>(root+0xDCA0+worldProfile.target.force*8,forceB);put<uintptr_t>(root+0x148+worldProfile.source.ruler*8,personA);put<uintptr_t>(root+0x148+worldProfile.target.ruler*8,personB);put<uintptr_t>(root+0xDE40+worldProfile.source.district*8,districtA);put<uintptr_t>(root+0xDE40+worldProfile.target.district*8,districtB);
    put<uintptr_t>(forceA,base+0x129FE58);put<WORD>(forceA+0x10,worldProfile.source.ruler);put<BYTE>(forceA+0x47,BYTE(40+generationIndex));put<uintptr_t>(forceB,base+0x129FE58);put<WORD>(forceB+0x10,worldProfile.target.ruler);put<BYTE>(forceB+0x47,BYTE(60+generationIndex));
    put<uintptr_t>(personA,base+0x12A00D0);put<WORD>(personA+0x10,worldProfile.source.ruler);put<BYTE>(personA+0x118,worldProfile.source.district);put<uintptr_t>(personB,base+0x12A00D0);put<WORD>(personB+0x10,worldProfile.target.ruler);put<BYTE>(personB+0x118,worldProfile.target.district);
    put<uintptr_t>(districtA,base+0x129FEC8);put<BYTE>(districtA+0x10,worldProfile.source.force);put<BYTE>(districtA+0x11,1);put<WORD>(districtA+0x12,worldProfile.source.ruler);put<uintptr_t>(districtB,base+0x129FEC8);put<BYTE>(districtB+0x10,worldProfile.target.force);put<BYTE>(districtB+0x11,1);put<WORD>(districtB+0x12,worldProfile.target.ruler);
    put<uintptr_t>(title,base+0x12DAAF0);memcpy(reinterpret_cast<void*>(title+0x70),"CTitleState",12);put<DWORD>(title+0x47C,63);put<pc::Pair>(title+0x4A0,sourcePair);put<DWORD>(title+0x470,13);
    put<uintptr_t>(title+0x520+0x48,titleCallable);put<uintptr_t>(titleCallable,base+0x138E8C0);put<uintptr_t>(titleCallable+8,base+0x4DA390);put<uintptr_t>(loadCallable,base+0x138E8C0);put<uintptr_t>(loadCallable+8,base+0x508B40);put<uintptr_t>(otherCallable,base+0x138E8C0);put<uintptr_t>(otherCallable+8,base+0x1234);
    put<std::uint64_t>(base+0x19E7310+0x10,5);

    put<uintptr_t>(load,base+0x12DBD68);memcpy(reinterpret_cast<void*>(load+0x70),"CLoadState",11);put<DWORD>(load+0x470,1);put<uintptr_t>(load+0x48,closure);put<uintptr_t>(closure,base+0x12EA4D0);put<uintptr_t>(closure+8,title);put<uintptr_t>(base+0x12EA4D0+0x10,base+0x4FAC30);
    put<DWORD>(base+0x201ECD0,0xffffffff);sso(base+0x201ECE0,"");put<uintptr_t>(base+0x2025318,cache);put<DWORD>(cache+0x3EC,0xffffffff);put<uintptr_t>(base+0x19E7310+0x40,pending);
}
static unsigned userBodies=0,menuBodies=0,gameBodies=0;
static bool storageValid(void*){return true;}
static bool exists(void*,const char*n){return !strcmp(n,fileProfile.name);}
static std::int32_t fileSize(void*,const char*){return fileProfile.size;}
#include "checkpoint_persistent_runtime_planning.inc"
#include "checkpoint_persistent_runtime_admission.inc"
static bool sessionGuard(void*,ns::Point){return true;}
static bool requestGuard(void*,rq::Point p){
    if(scenario==L"stop-before-cas"&&p==rq::Point::BeforeCas)session.Stop();
    if(scenario==L"stop-after-cas"&&p==rq::Point::AfterCas)session.Stop();
    
    return !(scenario==L"post-cas-reject"&&p==rq::Point::AfterCas);
}
extern "C" void GuestSessionUserBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){
    if(planningContext&&self==planningContext->newUser){++planningBodies;if(scenario==L"planning-native-exception")RaiseException(0xE014CCAE,0,0,nullptr);return;}
    ++userBodies;check(self==layout.config.states[4],"original User");if(scenario!=L"input-missing-prefetch")runFixturePrefetch(self);if(scenario==L"user-exception")RaiseException(0xE014CCA1,0,0,nullptr);}
extern "C" void GuestSessionMenuBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){++menuBodies;check(self==layout.config.menu,"original Menu");restoreMenuUiDouble();}
extern "C" void GuestSessionGameBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){
    ++gameBodies;check(self==layout.config.states[2],"original Game");
    if(at<DWORD>(cache+0x3EC)==63){put<DWORD>(base+0x201ECD0,63);sso(base+0x201ECE0,fileProfile.name);}
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
    if(failures)printf("DETAIL request=%s state=%u os=%lu exception=%lu bytes=%ld life=%ld identity=%ld storage=%s storage_os=%lu boundary=%u\n",r.request.stage,unsigned(r.request.state),r.request.osError,r.request.exceptionCode,r.bytes.error,r.lifecycle.error,r.identity.error,r.request.read.stage,r.request.read.osError,unsigned(r.request.boundary.error));
    check(!r.inputExclusionProven&&!r.presentationProven&&!r.nativePlanningReady&&!r.fullWorldVerified,"no external guarantees fabricated");
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"state\":%u,\"error\":%ld,\"cas\":%u,\"may_published\":%u,\"identity_ready\":%u,\"stop\":%u,\"restored\":%u,\"phase_passed\":%s,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,unsigned(r.state),r.error,r.casPublished,r.mayHavePublished,r.identity.receiptReady,r.stopRequested,r.hooksRestored,passedPhase?"true":"false");return failures?1:0;
}
static int runGeneration(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=5)return 2;scenario=argv[1];
    FILE* measure=nullptr;_wfopen_s(&measure,argv[2],L"rb");if(!measure)return 3;
    fseek(measure,0,SEEK_END);fileProfile.size=static_cast<unsigned>(ftell(measure));fclose(measure);
    strcpy_s(fileProfile.name,"svdexccSC03.s14");fileProfile.slot=63;
    archive.resize(fileProfile.size);buffer.resize(fileProfile.size);
    worldProfile={203,8,BYTE(generationIndex?21:11),{WORD(generationIndex?766:666),12,BYTE(generationIndex?13:11)},{WORD(generationIndex?1052:952),2,BYTE(generationIndex?5:2)}};
    if(scenario==L"alternate-factions"){worldProfile.source.force=18;worldProfile.target.force=7;}

    FILE*file=nullptr;_wfopen_s(&file,argv[2],L"rb");if(!file)return 3;check(fread(archive.data(),1,archive.size(),file)==archive.size(),"complete local archive");check(fgetc(file)==EOF,"archive exact size");fclose(file);check(native_storage_read::Sha256(archive.data(),archive.size(),fileProfile.sha256),"dynamic expected digest");setup();layout.config.attempt+=generationIndex;
    layout.config.force=generationIndex?worldProfile.target.force:worldProfile.source.force;put<BYTE>(world+0x3A,layout.config.force);

    ns::Config c{};c.request.profile=c.bytes.profile=c.lifecycle.profile=c.identity.profile=&fileProfile;c.identity.worldProfile=worldProfile;c.request.boundary=layout.config;c.request.boundary.menu=0;c.request.localPath=argv[2];c.request.intentPath=argv[3];memset(c.request.ownerBinding,0x63+generationIndex,32);c.request.validate=requestGuard;
    c.request.storage={reinterpret_cast<void*>(storage),exists,fileSize,reinterpret_cast<native_storage_read::FileRead>(&GuestSessionReadOriginal),storageValid,nullptr};
    c.bytes.base=base;c.bytes.storage=storage;c.bytes.storageVtable=storage+16;c.bytes.readMethod=uintptr_t(&GuestSessionReadOriginal);c.bytes.attemptToken=layout.config.attempt;c.bytes.validateAttachment=byteGuard;c.bytes.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);c.bytes.fixtureReadCaller=uintptr_t(&GuestSessionReadReturn);c.bytes.fixtureParentCaller=0xAABBCC1234567890ull;GuestSessionParent=c.bytes.fixtureParentCaller;
    c.lifecycle.base=base;c.lifecycle.attemptToken=layout.config.attempt;c.lifecycle.validateAttachment=lifeGuard;c.lifecycle.fixtureUpdateCaller=uintptr_t(&GuestSessionUpdateReturn);
    c.identity.base=base;c.identity.attemptToken=layout.config.attempt;c.identity.intentPath=argv[4];memset(c.identity.ownerBinding,0x63+generationIndex,32);c.identity.validateAttachment=identityGuard;c.identity.fixtureWorkerCaller=uintptr_t(&GuestSessionWorkerReturn);
    c.validate=sessionGuard;c.userAfter=userAfterController;
    uintptr_t labels[]={uintptr_t(&GuestSessionUserReturn),uintptr_t(&GuestSessionMenuReturn),uintptr_t(&GuestSessionGameReturn),uintptr_t(&GuestSessionUpdateReturn)};memcpy(c.fixtureDispatchCaller,labels,sizeof labels);
    void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
    void* bridges[]={reinterpret_cast<void*>(&CheckpointPersistentBridge0),reinterpret_cast<void*>(&CheckpointPersistentBridge1),reinterpret_cast<void*>(&CheckpointPersistentBridge2),reinterpret_cast<void*>(&CheckpointPersistentBridge3),reinterpret_cast<void*>(&CheckpointPersistentBridge4),reinterpret_cast<void*>(&CheckpointPersistentBridge5)};
    if(!generationIndex){GuestSessionSlots=reinterpret_cast<void**>(alloc(0x1000));for(unsigned i=0;i<6;++i)GuestSessionSlots[i]=originals[i];}
    for(unsigned i=0;i<6;++i)c.hooks[i]={GuestSessionSlots+i,originals[i],bridges[i]};
    configurePlanning(c);attachAdmission(c);
    auto* logical=new la::Adapter;la::Config mapping{};mapping.generation=generationIndex+2;
    for(unsigned i=0;i<4;++i){mapping.dispatchBefore[i]=ns::Session::DispatchBefore;mapping.dispatchAfter[i]=ns::Session::DispatchAfter;mapping.dispatchFinally[i]=ns::Session::DispatchFinally;mapping.dispatchContexts[i]=currentSession;}
    mapping.workerBefore[0]=ns::Session::WorkerBefore;mapping.workerAfter[0]=ns::Session::WorkerAfter;mapping.workerFinally[0]=ns::Session::WorkerFinally;
    mapping.workerBefore[1]=ns::Session::ReadBefore;mapping.workerAfter[1]=ns::Session::ReadAfter;mapping.workerFinally[1]=ns::Session::ReadFinally;
    mapping.workerContexts[0]=mapping.workerContexts[1]=currentSession;
    check(logical->Initialize(mapping),"logical generation mapping");
    if(!generationIndex){
        DWORD protection=0;check(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&protection)!=0,"native slots read-only before owner publication");
        po::Config p{};memcpy(p.hooks,c.hooks,sizeof p.hooks);p.userForward=reinterpret_cast<void*>(&CheckpointPersistentAuthorizedOriginal);
        p.validate=physicalGuard;p.context=&physicalOwner;
        check(physicalOwner.Install(p),"real owner installs all six resident bridges once");
    }
    check(physicalOwner.Verify(),"all six original bindings/protections still owned");
    check(session.Initialize(c),"fresh Session initialized after physical ownership established");
    check(session.ActivateForOfflineExercise(),"explicit fixture-only activation");
    check(physicalOwner.PublishForOfflineExercise(generationIndex+1,logical->RouteGeneration()),"publish only the fully prepared generation after bootstrap");
    for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"same persistent physical slot");
    if(scenario==L"input-pending"||scenario==L"input-missing-prefetch"){
        if(scenario==L"input-pending")put<LONG>(layout.toolbar+0x88,13);
        GuestSessionUserInvoke(layout.config.states[4],1,2,3);
        ns::Report rejected{};session.Snapshot(rejected);verifyAdmissionRejected();
        check(userBodies==1&&!rejected.menuBound&&!rejected.casPublished&&!rejected.activeDispatch,"refusal forwards native once without load submission");
        return finishReport(rejected,true);
    }
    if(scenario.rfind(L"queue-",0)==0){
        GuestSessionUserInvoke(layout.config.states[4],1,2,3);verifyQueueNegative();
        ns::Report rejected{};session.Snapshot(rejected);check(!rejected.menuBound&&!rejected.casPublished,"queue failure never publishes load request");return finishReport(rejected,true);
    }
    if(scenario==L"user-exception"){
        bool caught=false;__try{GuestSessionUserInvoke(layout.config.states[4],1,2,3);}__except(GetExceptionCode()==0xE014CCA1?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
        ns::Report abnormal{};session.Snapshot(abnormal);
        check(caught&&abnormal.dispatchAbnormal==1&&!abnormal.activeDispatch&&!abnormal.menuBound,"dispatch native fault drains without queueing request");
        verifyAdmissionAbnormal();
        return finishReport(abnormal,true);
    }
    GuestSessionUserInvoke(layout.config.states[4],1,2,3);ns::Report r{};session.Snapshot(r);check(userBodies==1&&r.userControllerCalls==1,"normal User precedes controller");
    verifyAdmission();
    check(r.menuBound&&r.state==ns::State::MenuQueued,"menu bound at owned User AFTER");
    // Explicit dispatcher push/Init double: real Session will observe first
    // Menu Update via its already installed pointer, not a fixture distributor.
    put<std::uint64_t>(base+0x19E7310+0x10,6);put<uintptr_t>(stackArray+40,layout.config.menu);put<std::uint64_t>(base+0x19E7310+0x30,0);layout.setStage(bd::Stage::MenuAfter);
    GuestSessionMenuInvoke(layout.config.menu,0x1001,0x1002,0x1003);session.Snapshot(r);check(r.request.menuObserved&&menuBodies==1,"first native Menu Update paired");
    if(scenario==L"controller-error")check(!session.BindQueuedMenu({}),"out-of-bound controller error recorded");
    if(scenario==L"stop-before-game")session.Stop();
    layout.setStage(bd::Stage::GameBefore);GuestSessionGameInvoke(layout.config.states[2],0x1001,0x1002,0x1003);session.Snapshot(r);
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
    check(bool(r.identity.receiptReady)==identityPass,"dynamic identity adapter runs in shared Session dispatcher");
    if(identityPass)check(r.identity.capturedSource47==40+generationIndex&&r.identity.capturedTarget47==60+generationIndex,"opaque fields captured from new world");
    check(workerCalls==3&&loadBodies==1&&otherBodies==1&&updateCalls==4&&joinCalls==1,"original counts across single Session");
    check(!r.activeDispatch&&!r.activeWorker&&!r.activeRead,"normally paired callbacks drained");
    for(unsigned slot=0;slot<6;++slot){CheckpointPersistentBridgeStats stats{};check(CheckpointPersistentBridgeSnapshot(slot,&stats)&&!stats.active&&!stats.cleanup_faults,"shared native bridge drained without cleanup faults");}
    if(bytePass)check(r.identity.casApplied==1&&r.identity.intentDurable,"valid upstream allows one atomic identity pair");else check(!r.identity.casAttempts&&!r.identity.intentCreated,"failed load bytes blocks pair");
    if(scenario==L"load-exception"||scenario==L"read-exception")check(loadException&&r.bytes.workerAbnormal==1,"Load exception propagated");
    if(scenario==L"title-exception")check(titleException&&r.identity.abnormal==1&&!r.identity.nativeReturned,"Title exception propagated");
    if(scenario==L"post-cas-reject")check(r.state==ns::State::Uncertain&&r.identity.receiptReady,"post-CAS error does not abandon identity recovery");
    if(scenario==L"stop-after-cas"||scenario==L"stop-during-load")check(r.state==ns::State::RetainingObservation&&r.identity.receiptReady,"Stop preserves in-progress observation and identity recovery");
    check(!session.RestoreBeforeCommit(),"no post-CAS unhook API without independent terminal controller");session.Snapshot(r);for(unsigned i=0;i<6;++i)check(GuestSessionSlots[i]==bridges[i],"published observer pointers retained");
    observePlanningForFixture(identityPass);
    verifyNoAdditionalAdmission();
    la::Report logicalReport{};logical->Snapshot(logicalReport);
    check(!logicalReport.faults&&!logicalReport.active&&logicalReport.before==logicalReport.finally,"logical scope balances without mapping faults");
    check(!physicalReport().routeFaults,"route adapter no faults");
    rt::Report routing{};routing=physicalReport().route;check(!routing.active&&!routing.productionAdmission&&!routing.nativeSchedulerFence,"leases drained; no live authority");
    return finishReport(r,true);
}

// C++ report padding has no semantic value. Diagnostics proved the prior byte
// comparison differed only at outer padding offsets 12/13. Compare EVERY named
// field, including all refusal/capability flags, rather than ignoring reports.
static bool sameQueueReport(const dq::Report&a,const dq::Report&b){
    static_assert(sizeof(dq::Report)==144&&sizeof(qa::Report)==112,"review comparator after report schema changes");
    const auto native=[](const qa::Report&r){return std::tie(r.stage,r.error,r.exception,r.thread,r.call_id,r.ticket_serial,r.controller,r.user,r.menu,r.queue,r.queue_count,r.queue_capacity,r.authorized,r.native_calls,r.native_returned,r.native_result_verified,r.resolver_calls,r.stopped,r.may_have_queued,r.queue_capability_consumed,r.private_ticket_authenticated_by_adapter,r.world_ready);};
    return std::tie(a.generation,a.initialized,a.route_rejections,a.production_admission,a.native_scheduler_fence)==std::tie(b.generation,b.initialized,b.route_rejections,b.production_admission,b.native_scheduler_fence)&&native(a.native)==native(b.native);
}
int wmain(int argc,wchar_t**argv){
    if(argc!=4)return 2;
    const std::wstring first=argv[1],folder=argv[3];
    ns::Session* retired=nullptr;ns::Report before{},after{};dq::Bridge* retiredQueue=nullptr;dq::Report queueBefore{},queueAfter{};
    for(unsigned i=0;i<2;++i){
        generationIndex=i;currentSession=new ns::Session;currentLayout=new checkpoint_load_input_boundary_fixture::Layout;
        workerCalls=readCalls=updateCalls=initializers=loadBodies=otherBodies=joinCalls=userBodies=menuBodies=gameBodies=planningBodies=0;loadException=0;
        std::wstring caseName=first==L"queue-stale-ticket"?(i?first:L"success"):(i&&first!=L"alternate-factions"?L"success":first);
        std::wstring req=folder+L"/request-"+std::to_wstring(i)+L".intent",identity=folder+L"/identity-"+std::to_wstring(i)+L".intent";
        std::wstring localArchive=folder+L"\\"+std::to_wstring(i)+L"\\svdexccSC03.s14";
        wchar_t* args[]={argv[0],caseName.data(),localArchive.data(),req.data(),identity.data()};
        runGeneration(5,args);
        if(!i){retired=currentSession;retired->Snapshot(before);retiredQueue=&admissionBundle->queueBridge;retiredQueue->Snapshot(queueBefore);}
        else {retired->Snapshot(after);check(!memcmp(&before,&after,sizeof before),"retired Session report immutable across next generation");retiredQueue->Snapshot(queueAfter);check(sameQueueReport(queueBefore,queueAfter),"all retired queue report fields immutable across next generation");}
    }
    rt::Report report{};report=physicalReport().route;
    check(report.transitions==2&&report.generations==3&&report.entered==report.released&&!report.active,"two generations on one six-entry installation");
    const auto installed=physicalReport();check(installed.installed&&installed.configured==6&&installed.published==6&&installed.hooksRetained&&installed.error==po::Error::None,"physical owner remains singular and healthy after two loads");
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"generations\":%u,\"leases\":%llu,\"game_access\":false,\"native_scheduler_fence\":false}\n",first.c_str(),failures?"false":"true",failures,report.generations,report.entered);
    return failures?1:0;
}
