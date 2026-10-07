#define CHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE
#include "checkpoint_dynamic_cc_load_observer.h"
#include <cstdio>
#include "native_storage_read_core.h"
#include <cstring>
#include <string>
#include <vector>
namespace obs=checkpoint_dynamic_cc_load_observer;
extern "C" {
std::uint64_t CcLoadFixtureWorkerInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CcLoadFixtureReadInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CcLoadFixtureWorkerOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CcLoadFixtureReadOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void CcLoadFixtureWorkerReturn();void CcLoadFixtureReadReturn();
std::uint64_t CcLoadFixtureParent=0,CcLoadFixtureReadRax=0,CcLoadFixtureWorkerRax=0;
unsigned char CcLoadFixtureReadXmm[16]{},CcLoadFixtureWorkerXmm[16]{};
unsigned char CcLoadFixturePattern[32]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16};
}
static checkpoint_dynamic_file_profile::Profile profile{};
static obs::Observer observer;
static obs::Config config;
static std::string scenario;
static std::vector<unsigned char> source,buffer;
static unsigned char load[0x600]{},title[0x600]{};
static uintptr_t callable[2]{},titleCallable[2]{},storage[4]{};
static unsigned workerCalls=0,readCalls=0,failures=0;
static HANDLE entered=nullptr,proceed=nullptr;
static void check(bool value,const char*text){if(!value){++failures;std::printf("FAIL: %s\n",text);}}
template<class T>static void put(uintptr_t address,T value){memcpy(reinterpret_cast<void*>(address),&value,sizeof value);}
static bool validate(void*,obs::Point point,uintptr_t l,uintptr_t t){
    if(scenario=="guard-bind"&&point==obs::Point::Bind)return false;
    if(scenario=="guard-worker"&&point==obs::Point::WorkerBefore)return false;
    if(scenario=="guard-read"&&point==obs::Point::ReadAfter)return false;
    if(scenario=="guard-seh"&&point==obs::Point::ReadAfter)RaiseException(0xE014CC09,0,0,nullptr);
    return l==uintptr_t(load)&&t==uintptr_t(title);
}
static std::uint64_t invokeRead(){
    const char*name=scenario=="wrong-name"?"svdexSC34.s14":profile.name;
    auto count=scenario=="wrong-size"?profile.size-1:profile.size;
    auto data=scenario=="bad-buffer"?uintptr_t(0x1234):uintptr_t(buffer.data());
    auto self=uintptr_t(storage)+(scenario=="wrong-storage"?8:0);
    return CcLoadFixtureReadInvoke(self,uintptr_t(name),data,count);
}
extern "C" std::uint64_t CcLoadFixtureReadBody(std::uint64_t self,std::uint64_t name,std::uint64_t data,std::uint64_t amount){
    ++readCalls;
    check(self==uintptr_t(storage)||scenario=="wrong-storage","original read self forwarded");
    check(name!=0&&amount>0,"original read integer args forwarded");
    if(scenario=="read-seh")RaiseException(0xE014CC01,0,0,nullptr);
    if(scenario=="read-cpp")throw 73;
    if(scenario=="stop-during-read")obs::Stop(observer);
    if(scenario=="concurrent-unowned"&&readCalls==1){SetEvent(entered);WaitForSingleObject(proceed,5000);}
    if(data>=0x10000){memcpy(reinterpret_cast<void*>(data),source.data(),size_t(amount));if(scenario=="wrong-hash")reinterpret_cast<unsigned char*>(data)[111]^=1;}
    const auto count=scenario=="short-read"?profile.size-1:scenario=="negative-read"?0xffffffffu:std::uint32_t(amount);
    return 0xFEDCBA9800000000ull|count;
}
extern "C" std::uint64_t CcLoadFixtureWorkerBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++workerCalls;check(a==0x1122334455667788ull&&b==0x8877665544332211ull&&c==0x123456789abcdef0ull,"original worker args forwarded");
    if(self==uintptr_t(titleCallable))return 0;
    if(scenario=="worker-seh")RaiseException(0xE014CC02,0,0,nullptr);
    if(scenario=="worker-cpp")throw 74;
    if(scenario=="stop-before-read")obs::Stop(observer);
    if(scenario!="missing-read"){
        invokeRead();if(scenario=="duplicate-read")invokeRead();
    }
    put<DWORD>(config.base+0x201EC08,scenario=="native-failure"?0u:1u);
    return 0;
}
static void invokeWorker(uintptr_t self){CcLoadFixtureWorkerInvoke(self,0x1122334455667788ull,0x8877665544332211ull,0x123456789abcdef0ull);}
static DWORD WINAPI workerThread(void*){invokeWorker(uintptr_t(callable));return 0;}
static bool runSeh(){__try{invokeWorker(uintptr_t(callable));return false;}__except(GetExceptionCode()==0xE014CC01||GetExceptionCode()==0xE014CC02?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
static void configureBridges(){
    CheckpointLoadWorkerBridgeConfig w{},r{};
    w.original=reinterpret_cast<void*>(&CcLoadFixtureWorkerOriginal);w.before=obs::WorkerBefore;w.after=obs::WorkerAfter;w.finally=obs::WorkerFinally;w.context=&observer;
    r.original=reinterpret_cast<void*>(&CcLoadFixtureReadOriginal);r.before=obs::ReadBefore;r.after=obs::ReadAfter;r.finally=obs::ReadFinally;r.context=&observer;
    check(CheckpointLoadWorkerBridgeConfigure(0,&w)==1,"configure worker bridge");check(CheckpointLoadWorkerBridgeConfigure(1,&r)==1,"configure read bridge");
}
int main(int argc,char**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    if(argc!=3)return 2;scenario=argv[1];
    FILE*f=nullptr;fopen_s(&f,argv[2],"rb");if(!f)return 3;
    fseek(f,0,SEEK_END);auto length=ftell(f);rewind(f);if(length<257||length>0x100000)return 3;
    source.resize(size_t(length));buffer.resize(size_t(length));profile.size=std::uint32_t(length);profile.slot=63;strcpy_s(profile.name,"svdexccSC03.s14");
    check(fread(source.data(),1,source.size(),f)==source.size(),"read archived bytes");fclose(f);check(native_storage_read::Sha256(source.data(),source.size(),profile.sha256),"hash real source bytes");
    if(scenario=="wrong-profile-hash")profile.sha256[0]^=1;auto callerProfile=profile;config.profile=&callerProfile;
    config.base=uintptr_t(VirtualAlloc(nullptr,0x2100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));if(!config.base)return 4;
    config.storage=uintptr_t(storage);config.storageVtable=uintptr_t(storage)+16;config.readMethod=uintptr_t(&CcLoadFixtureReadOriginal);config.attemptToken=0xCC630001;
    config.validateAttachment=validate;config.fixtureWorkerCaller=uintptr_t(&CcLoadFixtureWorkerReturn);config.fixtureReadCaller=uintptr_t(&CcLoadFixtureReadReturn);config.fixtureParentCaller=0xABCDEF7766554433ull;
    CcLoadFixtureParent=config.fixtureParentCaller;
    put<uintptr_t>(uintptr_t(load),config.base+0x12DBD68);put<DWORD>(uintptr_t(load)+0x470,1);
    callable[0]=config.base+0x138E8C0;callable[1]=config.base+0x508B40;
    titleCallable[0]=config.base+0x138E8C0;titleCallable[1]=config.base+0x4DA390;
    put<uintptr_t>(uintptr_t(load)+0x478+0x48,uintptr_t(callable));
    if(scenario=="wrong-worker-owner")put<uintptr_t>(uintptr_t(load)+0x478+0x48,uintptr_t(titleCallable));
    if(scenario=="wrong-worker-vtable")++callable[0];
    if(scenario=="wrong-worker-caller")++config.fixtureWorkerCaller;
    if(scenario=="wrong-read-caller")++config.fixtureReadCaller;
    if(scenario=="wrong-parent")++CcLoadFixtureParent;
    if(scenario=="bad-binding")put<DWORD>(uintptr_t(load)+0x470,2);
    check(obs::Initialize(observer,config),"initialize once");memset(&callerProfile,0,sizeof callerProfile);check(checkpoint_dynamic_file_profile::Same(observer.profile,profile),"owns immutable profile copy");
    check(!obs::Initialize(observer,config),"second initialize rejected");
    const bool bound=obs::BindLoad(observer,uintptr_t(load),uintptr_t(title));
    check(bound==(scenario!="bad-binding"&&scenario!="guard-bind"),"binding contract");
    check(!obs::BindLoad(observer,uintptr_t(load),uintptr_t(title)),"binding cannot be repeated");
    configureBridges();
    bool propagated=false;
    if(scenario=="worker-seh"||scenario=="read-seh")propagated=runSeh();
    else if(scenario=="worker-cpp"||scenario=="read-cpp"){try{invokeWorker(uintptr_t(callable));}catch(int value){propagated=value==73||value==74;}}
    else if(scenario=="concurrent-unowned"){
        entered=CreateEventW(nullptr,TRUE,FALSE,nullptr);proceed=CreateEventW(nullptr,TRUE,FALSE,nullptr);
        HANDLE thread=CreateThread(nullptr,0,workerThread,nullptr,0,nullptr);check(thread!=nullptr,"worker thread created");
        check(WaitForSingleObject(entered,5000)==WAIT_OBJECT_0,"owned read active");
        // Different thread uses a separate buffer; it must never inherit TLS.
        std::vector<unsigned char>other(profile.size);CcLoadFixtureReadInvoke(uintptr_t(storage),uintptr_t(profile.name),uintptr_t(other.data()),profile.size);
        SetEvent(proceed);check(WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"worker joined in fixture");CloseHandle(thread);CloseHandle(entered);CloseHandle(proceed);
    }else if(scenario=="unowned-only")invokeRead();
    else{
        invokeWorker(uintptr_t(callable));
        if(scenario=="duplicate-worker")invokeWorker(uintptr_t(callable));
        if(scenario=="title-transparent")invokeWorker(uintptr_t(titleCallable));
    }
    obs::Report r{};obs::Snapshot(observer,r);
    const bool positive=scenario=="success"||scenario=="title-transparent"||scenario=="concurrent-unowned";
    check(bool(r.observedWorkerAndBytes)==positive,"accept exact bytes and one owned normal worker only");
    check(!r.activeRead&&!r.activeWorker,"observer scopes cleared");
    check(!r.loadAuthorized&&!r.joined&&!r.planningReady,"observation not load completion");
    CheckpointLoadWorkerOwner owner{};check(!CheckpointLoadWorkerCurrentOwner(&owner),"no stale TLS owner");
    CheckpointLoadWorkerBridgeStats ws{},rs{};CheckpointLoadWorkerBridgeSnapshot(0,&ws);CheckpointLoadWorkerBridgeSnapshot(1,&rs);
    check(ws.active==0&&rs.active==0&&!ws.cleanup_faults&&!rs.cleanup_faults,"real bridges drained without cleanup faults");
    if(positive){
        check(r.bytesMatched&&r.workerReturned&&r.nativeResult==1&&!memcmp(r.sha256,profile.sha256,32),"actual archive hash observed");
        check(r.readRax==(0xFEDCBA9800000000ull|profile.size)&&r.workerRax==0xaabbccdd87654321ull,"full RAX recorded");
        check(!memcmp(r.readXmm0,CcLoadFixturePattern+16,16)&&!memcmp(r.workerXmm0,CcLoadFixturePattern,16),"original XMM0 recorded");
        check(CcLoadFixtureWorkerRax==r.workerRax&&CcLoadFixtureReadRax==r.readRax,"RAX reaches native caller unchanged");
        check(!memcmp(CcLoadFixtureReadXmm,CcLoadFixturePattern+16,16)&&!memcmp(CcLoadFixtureWorkerXmm,CcLoadFixturePattern,16),"XMM0 reaches native caller unchanged");
    }
    if(scenario=="title-transparent")check(r.titleWorkers==1&&r.otherWorkers==1&&workerCalls==2,"title original transparently forwarded");
    if(scenario=="concurrent-unowned")check(r.unownedReads==1&&readCalls==2&&r.ownedReadCandidates==1,"concurrent read kept separate");
    if(scenario=="worker-seh"||scenario=="worker-cpp"||scenario=="read-seh"||scenario=="read-cpp")check(propagated&&r.workerAbnormal==1&&!r.workerReturned,"native exception propagates and no fake normal return");
    if(scenario=="read-seh"||scenario=="read-cpp")check(r.readAbnormal==1&&rs.abnormal_exits==1&&ws.abnormal_exits==1,"nested abnormal scopes finally paired");
    std::printf("{\"case\":\"%s\",\"passed\":%s,\"failures\":%u,\"error\":%ld,\"observed\":%u,\"report_bytes\":%zu,\"worker_calls\":%u,\"read_calls\":%u,\"game_access\":false,\"world_load_authorized\":false}\n",scenario.c_str(),failures?"false":"true",failures,r.error,r.observedWorkerAndBytes,sizeof r,workerCalls,readCalls);
    return failures?1:0;
}
