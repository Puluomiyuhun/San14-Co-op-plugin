#include "checkpoint_title_identity_adapter.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
namespace ti=checkpoint_title_identity_adapter;namespace lc=checkpoint_cc_load_lifecycle;namespace by=checkpoint_cc_load_observer;namespace pc=checkpoint_identity_pair_commit;
extern "C" {
std::uint64_t GuestChainWorkerInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestChainReadInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestChainUpdateInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestChainWorkerOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestChainReadOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestChainUpdateOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void GuestChainWorkerReturn();void GuestChainReadReturn();void GuestChainUpdateReturn();
std::uint64_t GuestChainParent=0,GuestChainReadRax=0,GuestChainWorkerRax=0;
unsigned char GuestChainReadXmm[16]{},GuestChainWorkerXmm[16]{};
unsigned char GuestChainPattern[32]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16};
}
static ti::Adapter adapter;static lc::Lifecycle life;static by::Observer bytes;
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
static void workerBefore(const CheckpointLoadWorkerFrame*f,void*){by::WorkerBefore(f,&bytes);ti::Before(f,&adapter);}
static void workerAfter(const CheckpointLoadWorkerFrame*f,void*){by::WorkerAfter(f,&bytes);ti::After(f,&adapter);}
static void workerFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*){by::WorkerFinally(f,e,&bytes);ti::Finally(f,e,&adapter);}
static void invokeWorker(uintptr_t self){GuestChainWorkerInvoke(self,0x1122334455667788ull,0x8877665544332211ull,0x123456789abcdef0ull);}
extern "C" std::uint64_t GuestChainReadBody(std::uint64_t self,std::uint64_t name,std::uint64_t data,std::uint64_t amount){
    ++readCalls;check(self==storage&&strcmp(reinterpret_cast<char*>(name),by::TargetName)==0&&amount==by::TargetSize,"actual read arguments");
    if(scenario==L"read-exception")RaiseException(0xE014CC91,0,0,nullptr);
    memcpy(reinterpret_cast<void*>(data),archive.data(),archive.size());
    if(scenario==L"actual-byte-mismatch")reinterpret_cast<unsigned char*>(data)[15363]^=1;
    return 0xFEDCBA9800000000ull|by::TargetSize;
}
extern "C" void GuestChainWorkerBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++workerCalls;check(a==0x1122334455667788ull&&b==0x8877665544332211ull&&c==0x123456789abcdef0ull,"generic four argument ABI");
    if(self==otherCallable){++otherBodies;return;}
    if(self==loadCallable){
        ++loadBodies;if(scenario==L"load-exception")RaiseException(0xE014CC92,0,0,nullptr);
        GuestChainReadInvoke(storage,uintptr_t(by::TargetName),uintptr_t(buffer.data()),by::TargetSize);
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
extern "C" void GuestChainUpdateBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
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
    base=alloc(0x2100000);root=alloc(0x86000);world=alloc(0x4000);title=alloc(0x2000);load=alloc(0x1000);stackArray=alloc(0x3000);
    forceA=alloc(0x1000);forceB=alloc(0x1000);personA=alloc(0x1000);personB=alloc(0x1000);districtA=alloc(0x1000);districtB=alloc(0x1000);
    check(base&&root&&world&&title&&load&&stackArray&&forceA&&forceB&&personA&&personB&&districtA&&districtB,"allocations");
    sourcePair={forceA,personA};targetPair={forceB,personB};loadCallable=title+0x700;titleCallable=title+0x740;otherCallable=title+0x780;closure=title+0x800;cache=title+0x900;storage=title+0xD00;pending=base+0x1000;
    put<uintptr_t>(base+0x1FCA1E0,root);put<uintptr_t>(root,base+0x12AA6B0);put<uintptr_t>(root+0x85130,world);put<uintptr_t>(world,base+0x12AA638);
    put<WORD>(world+0x34,203);put<BYTE>(world+0x36,8);put<BYTE>(world+0x37,11);put<BYTE>(world+0x3A,12);put<DWORD>(world+0x40,1);put<BYTE>(world+0x165D,2);put<DWORD>(world+0x20A8,1);
    put<uintptr_t>(root+0xDCA0+12*8,forceA);put<uintptr_t>(root+0xDCA0+2*8,forceB);put<uintptr_t>(root+0x148+666*8,personA);put<uintptr_t>(root+0x148+952*8,personB);put<uintptr_t>(root+0xDE40+11*8,districtA);put<uintptr_t>(root+0xDE40+2*8,districtB);
    put<uintptr_t>(forceA,base+0x129FE58);put<WORD>(forceA+0x10,666);put<BYTE>(forceA+0x47,6);put<uintptr_t>(forceB,base+0x129FE58);put<WORD>(forceB+0x10,952);put<BYTE>(forceB+0x47,7);
    put<uintptr_t>(personA,base+0x12A00D0);put<WORD>(personA+0x10,666);put<BYTE>(personA+0x118,11);put<uintptr_t>(personB,base+0x12A00D0);put<WORD>(personB+0x10,952);put<BYTE>(personB+0x118,2);
    put<uintptr_t>(districtA,base+0x129FEC8);put<BYTE>(districtA+0x10,12);put<BYTE>(districtA+0x11,1);put<WORD>(districtA+0x12,666);put<uintptr_t>(districtB,base+0x129FEC8);put<BYTE>(districtB+0x10,2);put<BYTE>(districtB+0x11,1);put<WORD>(districtB+0x12,952);
    put<uintptr_t>(title,base+0x12DAAF0);memcpy(reinterpret_cast<void*>(title+0x70),"CTitleState",12);put<DWORD>(title+0x47C,63);put<pc::Pair>(title+0x4A0,sourcePair);put<DWORD>(title+0x470,13);
    put<uintptr_t>(title+0x520+0x48,titleCallable);put<uintptr_t>(titleCallable,base+0x138E8C0);put<uintptr_t>(titleCallable+8,base+0x4DA390);put<uintptr_t>(loadCallable,base+0x138E8C0);put<uintptr_t>(loadCallable+8,base+0x508B40);put<uintptr_t>(otherCallable,base+0x138E8C0);put<uintptr_t>(otherCallable+8,base+0x1234);
    auto rootState=stackArray+0x1000,motor=stackArray+0x2000;put<uintptr_t>(stackArray,rootState);put<uintptr_t>(stackArray+8,motor);put<uintptr_t>(stackArray+16,title);put<uintptr_t>(stackArray+24,load);memcpy(reinterpret_cast<void*>(rootState+0x70),"CRootState",11);memcpy(reinterpret_cast<void*>(motor+0x70),"CMotorGameState",16);put<uintptr_t>(base+0x19E7310+0x20,stackArray);put<std::uint64_t>(base+0x19E7310+0x10,4);
    put<uintptr_t>(load,base+0x12DBD68);memcpy(reinterpret_cast<void*>(load+0x70),"CLoadState",11);put<DWORD>(load+0x470,1);put<uintptr_t>(load+0x48,closure);put<uintptr_t>(closure,base+0x12EA4D0);put<uintptr_t>(closure+8,title);put<uintptr_t>(base+0x12EA4D0+0x10,base+0x4FAC30);
    put<DWORD>(base+0x201ECD0,63);sso(base+0x201ECE0,by::TargetName);put<uintptr_t>(base+0x2025318,cache);put<DWORD>(cache+0x3EC,63);put<uintptr_t>(base+0x19E7310+0x40,pending);
}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;scenario=argv[1];archive.resize(by::TargetSize);buffer.resize(by::TargetSize);
    FILE*file=nullptr;_wfopen_s(&file,argv[2],L"rb");if(!file)return 3;check(fread(archive.data(),1,archive.size(),file)==archive.size(),"complete archive bytes");check(fgetc(file)==EOF,"exact archive length");fclose(file);setup();
    by::Config bc{};bc.base=base;bc.storage=storage;bc.storageVtable=storage+16;bc.readMethod=uintptr_t(&GuestChainReadOriginal);bc.attemptToken=0xCC630030;bc.validateAttachment=byteGuard;bc.fixtureWorkerCaller=uintptr_t(&GuestChainWorkerReturn);bc.fixtureReadCaller=uintptr_t(&GuestChainReadReturn);bc.fixtureParentCaller=0xAABBCC1234567890ull;GuestChainParent=bc.fixtureParentCaller;check(by::Initialize(bytes,bc),"bytes initialize");
    lc::Config lcCfg{};lcCfg.base=base;lcCfg.attemptToken=bc.attemptToken;lcCfg.bytes=&bytes;lcCfg.validateAttachment=lifeGuard;lcCfg.fixtureUpdateCaller=uintptr_t(&GuestChainUpdateReturn);check(lc::Initialize(life,lcCfg),"lifecycle initialize");
    ti::Config tc{};tc.base=base;tc.attemptToken=bc.attemptToken;tc.lifecycle=&life;tc.bytes=&bytes;tc.intentPath=argv[3];memset(tc.ownerBinding,0x63,32);tc.validateAttachment=identityGuard;tc.fixtureWorkerCaller=uintptr_t(&GuestChainWorkerReturn);check(ti::Initialize(adapter,tc),"identity initialize before receipts exist");
    CheckpointLoadWorkerBridgeConfig wb{},rb{};wb.original=reinterpret_cast<void*>(&GuestChainWorkerOriginal);wb.before=workerBefore;wb.after=workerAfter;wb.finally=workerFinally;check(CheckpointLoadWorkerBridgeConfigure(0,&wb)==1,"generic worker bridge");rb.original=reinterpret_cast<void*>(&GuestChainReadOriginal);rb.before=by::ReadBefore;rb.after=by::ReadAfter;rb.finally=by::ReadFinally;rb.context=&bytes;check(CheckpointLoadWorkerBridgeConfigure(1,&rb)==1,"read bridge");
    CheckpointPushBridgeConfig ub{};ub.original=reinterpret_cast<void*>(&GuestChainUpdateOriginal);ub.before=lc::UpdateBefore;ub.after=lc::UpdateAfter;ub.context=&life;check(CheckpointPushBridgeConfigure(0,&ub)==1,"update bridge");
    invokeWorker(otherCallable);
    for(unsigned i=0;i<4;++i)check(GuestChainUpdateInvoke(load,1,2,3)==0xFEDCBA9876543210ull,"update full RAX forwarded");
    lc::Report lr{};lc::Snapshot(life,lr);by::Report brBefore{};by::Snapshot(bytes,brBefore);
    const bool bytesPass=scenario!=L"actual-byte-mismatch"&&scenario!=L"load-exception"&&scenario!=L"read-exception";
    check(bool(lr.receiptReady)==bytesPass&&bool(brBefore.observedWorkerAndBytes)==bytesPass,"real upstream chain success or refusal");
    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load),0x1000,PAGE_NOACCESS,&old)!=0,"old Load page inaccessible before Title dispatch");
    if(scenario==L"success-late"){put<DWORD>(title+0x470,15);put<std::uint64_t>(base+0x19E7310+0x10,3);}
    // Negative upstream cases still forward a synthetic Title call to prove the
    // adapter refuses pair mutation even if native scheduling proceeds anyway.
    bool titleException=titleInvokeWithException();
    ti::Report tr{};ti::Snapshot(adapter,tr);by::Report br{};by::Snapshot(bytes,br);lc::Report lrAfter{};lc::Snapshot(life,lrAfter);
    const bool positive=scenario==L"success-early"||scenario==L"success-late";
    check(bool(tr.receiptReady)==positive,"end-to-end identity receipt");check(lrAfter.receiptReady==lr.receiptReady,"frozen lifecycle independent of old Load page");
    check(br.token==lr.token&&lr.token==tr.token,"same attempt token throughout actual cores");
    if(bytesPass)check(lr.frozenBytes.workerCall==br.workerCall&&lr.frozenBytes.readCall==br.readCall,"actual nested call IDs frozen into lifecycle");
    check(workerCalls==3&&loadBodies==1&&otherBodies==1&&updateCalls==4&&joinCalls==1,"generic originals and dispatcher originals forwarded exactly once");
    check(readCalls==(scenario==L"load-exception"?0u:1u),"native FileRead substitute count");
    check(br.titleWorkers==1&&br.otherWorkers==2&&tr.otherWorkers==2,"nonowned generic worker transparent across both consumers");
    check(!br.activeRead&&!br.activeWorker&&!tr.active&&!tr.planningReady&&!tr.fullWorldVerified&&!tr.initializerCallsDirectlyObserved,"cleanup and bounded claims");
    CheckpointLoadWorkerOwner owner{};check(!CheckpointLoadWorkerCurrentOwner(&owner),"TLS owner restored");CheckpointLoadWorkerBridgeStats ws{},rs{};CheckpointLoadWorkerBridgeSnapshot(0,&ws);CheckpointLoadWorkerBridgeSnapshot(1,&rs);check(!ws.active&&!rs.active&&!ws.cleanup_faults&&!rs.cleanup_faults&&ws.native_started==3,"real bridges drained");
    if(bytesPass){check(!memcmp(br.sha256,by::TargetSha256,32)&&br.returned==by::TargetSize&&lr.joinReturned&&lr.completionFrozen,"full real archive hash and ordered lifecycle");check(tr.casApplied==1&&tr.intentDurable&&tr.casAttempts==1,"one durable atomic pair commit");}
    else check(!tr.casAttempts&&!tr.intentCreated&&at<pc::Pair>(title+0x4A0).person==sourcePair.person,"failed actual bytes/load blocks every identity write");
    if(positive){check(initializers==1&&tr.identityObserved&&tr.worldForceAfter==2&&tr.worldControlAfter==1,"native identity substitute observed");check(tr.originalRax==GuestChainWorkerRax&&tr.originalRax==0xAABBCCDD87654321ull&&!memcmp(tr.originalXmm0,GuestChainPattern,16)&&!memcmp(GuestChainWorkerXmm,GuestChainPattern,16),"worker RAX and XMM0 forwarded");check(br.readRax==GuestChainReadRax&&!memcmp(br.readXmm0,GuestChainReadXmm,16),"read ABI preserved");}
    if(scenario==L"load-exception"||scenario==L"read-exception")check(loadException==1&&br.workerAbnormal==1&&!br.workerReturned,"load native exception propagates to OS-thread harness");
    if(scenario==L"read-exception")check(br.readAbnormal==1&&rs.abnormal_exits==1,"nested FileRead exception propagates");
    if(scenario==L"title-exception")check(titleException&&tr.abnormal==1&&!tr.nativeReturned&&tr.casApplied&&tr.intentDurable&&initializers==0,"Title native exception propagates without fabricated success or rollback");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"bytes_ready\":%u,\"lifecycle_ready\":%u,\"identity_ready\":%u,\"bytes_error\":%ld,\"lifecycle_error\":%ld,\"identity_error\":%ld,\"workers\":%u,\"reads\":%u,\"updates\":%u,\"cas\":%u,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,br.observedWorkerAndBytes,lr.receiptReady,tr.receiptReady,br.error,lr.error,tr.error,workerCalls,readCalls,updateCalls,tr.casApplied);
    return failures?1:0;
}
