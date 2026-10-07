#define CHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE
#include "checkpoint_dynamic_cc_load_lifecycle.h"
#include <cstdio>
#include <vector>
#include "native_storage_read_core.h"
#include <cstring>
#include <string>
namespace lc=checkpoint_dynamic_cc_load_lifecycle;
namespace by=checkpoint_dynamic_cc_load_observer;
extern "C" std::uint64_t CcLifecycleFixtureInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" std::uint64_t CcLifecycleFixtureOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CcLifecycleFixtureReturn();
static checkpoint_dynamic_file_profile::Profile profile{};
static lc::Lifecycle life;static by::Observer bytes;static lc::Config cfg;static std::string scenario;
static uintptr_t base=0,load=0,title=0,closure=0,cache=0,pending=0,callable=0;
static unsigned calls=0,failures=0;
template<class T>static void put(uintptr_t p,T v){memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
template<class T>static T at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static void check(bool x,const char*t){if(!x){++failures;std::printf("FAIL: %s\n",t);}}
static void sso(uintptr_t p,const char*n){memset(reinterpret_cast<void*>(p),0,32);memcpy(reinterpret_cast<void*>(p),n,strlen(n)+1);put<std::uint64_t>(p+16,strlen(n));put<std::uint64_t>(p+24,15);}
static bool byteGuard(void*,by::Point,uintptr_t l,uintptr_t t){return l==load&&t==title;}
static bool guard(void*,lc::Point p,uintptr_t l,uintptr_t t){return l==load&&t==title&&!(scenario=="guard-bind"&&p==lc::Point::Bind)&&!(scenario=="guard-after"&&p==lc::Point::After);}
static void fakePassedByteBoundary(){
    // Explicit synthetic byte-observer output. Its real worker/TLS/hash proof is
    // covered separately by checkpoint_dynamic_cc_load_observer's 31 real-bridge cases.
    auto&r=bytes.report;r.workerBefore=r.workerAfter=r.workerFinally=r.readBefore=r.readAfter=r.readFinally=1;
    r.bytesMatched=r.workerReturned=r.ownedReadCandidates=1;r.returned=profile.size;r.nativeResult=1;
    memcpy(r.sha256,profile.sha256,32);r.activeRead=r.activeWorker=0;
    if(scenario=="bad-byte-token")++r.token;
    if(scenario=="bad-byte-hash")r.sha256[0]^=1;
    if(scenario=="byte-error")InterlockedExchange(&bytes.error,LONG(by::Error::ReadHash));
    if(scenario=="missing-byte-finally")r.workerFinally=0;
}
extern "C" void CcLifecycleFixtureBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++calls;check(self==load&&a==0x123456789ABCDEF0ull&&b==0x1111222233334444ull&&c==0x5555666677778888ull,"native args preserved");
    if(scenario=="original-seh")RaiseException(0xE014CC51,0,0,nullptr);
    if(scenario=="original-cpp")throw 51;
    DWORD phase=at<DWORD>(load+0x470);
    if(phase==1){put<DWORD>(load+0x470,2);put<uintptr_t>(load+0x478+0x48,callable);if(scenario=="phase1-no-start")put<DWORD>(load+0x470,1);}
    if(phase==2){
        if(scenario=="wait-phase2"&&calls==2)return;
        fakePassedByteBoundary();put<uintptr_t>(load+0x478,0);put<uintptr_t>(load+0x480,0);put<uintptr_t>(load+0x4D8,0);
        if(scenario=="join-handle-left")put<uintptr_t>(load+0x4D8,0x7788);
        put<DWORD>(load+0x470,3);
    }
    if(phase==3)put<DWORD>(load+0x470,4);
    if(phase==4){
        put<DWORD>(load+8,scenario=="failure-status"?0x7FFFFFFE:0x7FFFFFFD);put<DWORD>(base+0x201EC08,scenario=="failure-result"?0:1);
        put<DWORD>(base+0x201ECD0,0xffffffff);put<DWORD>(base+0x201ECD4,0);put<DWORD>(base+0x201ECD8,0);sso(base+0x201ECE0,"");put<DWORD>(base+0x201ED00,0);put<DWORD>(cache+0x3EC,0xffffffff);
        put<std::uint64_t>(base+0x19E7310+0x30,1);put<DWORD>(pending,1);put<uintptr_t>(pending+8,0);
        if(scenario=="uncleared-slot")put<DWORD>(base+0x201ECD0,63);
        if(scenario=="uncleared-flags")put<DWORD>(base+0x201ECD8,1);
        if(scenario=="uncleared-name")sso(base+0x201ECE0,profile.name);
        if(scenario=="uncleared-cache")put<DWORD>(cache+0x3EC,63);
        if(scenario=="uncleared-tail")put<DWORD>(base+0x201ED00,1);
        if(scenario=="wrong-pop")put<DWORD>(pending,2);
        if(scenario=="two-pops")put<std::uint64_t>(base+0x19E7310+0x30,2);
        if(scenario=="stop-during-final")lc::Stop(life);
    }
}
static void tick(){auto r=CcLifecycleFixtureInvoke(load,0x123456789ABCDEF0ull,0x1111222233334444ull,0x5555666677778888ull);check(r==0xFEDCBA9876543210ull,"native RAX forwarded");}
static bool runSeh(){__try{tick();return false;}__except(GetExceptionCode()==0xE014CC51?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
int main(int argc,char**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=2)return 2;scenario=argv[1];std::vector<unsigned char> data(scenario=="success-large"?65537:513,0xA7);profile.slot=63;profile.size=std::uint32_t(data.size());strcpy_s(profile.name,"svdexccSC03.s14");check(native_storage_read::Sha256(data.data(),data.size(),profile.sha256),"real payload digest");
    base=uintptr_t(VirtualAlloc(nullptr,0x2100000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));load=uintptr_t(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    title=uintptr_t(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));closure=title+0x700;cache=title+0x800;pending=base+0x1000;callable=title+0x740;
    if(!base||!load||!title)return 3;
    put<uintptr_t>(load,base+0x12DBD68);memcpy(reinterpret_cast<void*>(load+0x70),"CLoadState",11);put<DWORD>(load+0x470,1);
    put<uintptr_t>(load+0x48,closure);put<uintptr_t>(closure,base+0x12EA4D0);put<uintptr_t>(closure+8,title);put<DWORD>(title+0x47C,63);
    put<uintptr_t>(base+0x12EA4D0+0x10,base+0x4FAC30);put<uintptr_t>(callable,base+0x138E8C0);put<uintptr_t>(callable+8,base+0x508B40);
    put<DWORD>(base+0x201ECD0,63);sso(base+0x201ECE0,profile.name);put<uintptr_t>(base+0x2025318,cache);put<DWORD>(cache+0x3EC,63);
    put<uintptr_t>(base+0x19E7310+0x40,pending);
    if(scenario=="wrong-closure-vt")put<uintptr_t>(closure,base+0x12EA4D8);
    if(scenario=="wrong-closure-method")put<uintptr_t>(base+0x12EA4D0+0x10,base+0x4FAC38);
    if(scenario=="wrong-title-slot")put<DWORD>(title+0x47C,34);
    if(scenario=="wrong-request-slot")put<DWORD>(base+0x201ECD0,34);
    if(scenario=="wrong-request-name")sso(base+0x201ECE0,"svdexSC34.s14");
    by::Config bc{};bc.profile=&profile;bc.base=base;bc.storage=title+0x600;bc.storageVtable=title+0x620;bc.readMethod=base+0x1234;bc.attemptToken=0x6302;bc.validateAttachment=byteGuard;
    check(by::Initialize(bytes,bc),"byte observer initialized unbound");
    auto callerProfile=profile;cfg.profile=&callerProfile;cfg.base=base;cfg.attemptToken=0x6302;cfg.bytes=&bytes;cfg.validateAttachment=guard;cfg.fixtureUpdateCaller=uintptr_t(&CcLifecycleFixtureReturn);
    if(scenario=="wrong-caller")++cfg.fixtureUpdateCaller;
    if(scenario=="profile-mismatch"){callerProfile.sha256[0]^=1;check(!lc::Initialize(life,cfg),"different profiles rejected");std::printf("{\"case\":\"profile-mismatch\",\"passed\":%s}\n",failures?"false":"true");return failures?1:0;}
    check(lc::Initialize(life,cfg),"lifecycle initialize");memset(&callerProfile,0,sizeof callerProfile);check(checkpoint_dynamic_file_profile::Same(life.profile,profile),"immutable lifecycle profile copy");check(!lc::Initialize(life,cfg),"lifecycle no reset");
    CheckpointPushBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(&CcLifecycleFixtureOriginal);bridge.before=lc::UpdateBefore;bridge.after=lc::UpdateAfter;bridge.context=&life;
    check(CheckpointPushBridgeConfigure(0,&bridge)==1,"real old bridge configured");
    bool propagated=false;
    if(scenario=="original-seh")propagated=runSeh();
    else if(scenario=="original-cpp"){try{tick();}catch(int value){propagated=value==51;}}
    else{
        for(unsigned i=0;i<(scenario=="wait-phase2"?5u:4u);++i){
            if(scenario=="missing-join"&&i==1)put<DWORD>(load+0x470,4);
            tick();
        }
    }
    lc::Report r{};lc::Snapshot(life,r);bool positive=scenario=="success"||scenario=="success-large"||scenario=="wait-phase2"||scenario=="snapshot-after-free";
    check(bool(r.receiptReady)==positive,"only ordered native-shaped lifecycle accepts");
    check(!r.directFinalizerObserved&&!r.planningReady&&!r.loadAuthorized,"no unseen finalize or ready claim");
    if(positive){check(r.bound&&r.workerStarted&&r.joinReturned&&r.requestCleared&&r.exactPop&&r.completionFrozen,"frozen milestones");check(r.joinedCall>r.boundCall&&r.completedCall>r.joinedCall&&r.phaseMask==30,"ordered receipt");}
    if(scenario=="snapshot-after-free"){
        DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_NOACCESS,&old)!=0,"old Load made unreadable");
        lc::Report late{};lc::Snapshot(life,late);check(late.receiptReady&&late.load==load&&late.title==title,"snapshot independent of freed Load");
        // Even a stale prefetched Update entry after completion is only forwarded
        // by integration; our BEFORE itself must not dereference the old Load.
        CheckpointPushFrame stale{};stale.args[0]=load;lc::UpdateBefore(&stale,&life);
    }
    CheckpointPushBridgeStats stats{};CheckpointPushBridgeSnapshot(0,&stats);
    if(scenario=="original-seh"||scenario=="original-cpp")check(propagated&&stats.abnormal_exits==1&&r.inFlight==1&&!r.receiptReady,"native exception leaves honest missing AFTER");
    else check(!r.inFlight,"normal after releases in-flight tracking");
    std::printf("{\"case\":\"%s\",\"passed\":%s,\"failures\":%u,\"error\":%ld,\"ready\":%u,\"report_bytes\":%zu,\"native_stub_calls\":%u,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,r.error,r.receiptReady,sizeof r,calls);
    return failures?1:0;
}
