#include "checkpoint_session_ipc.h"
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
namespace ti=checkpoint_title_identity_adapter;namespace lc=checkpoint_cc_load_lifecycle;namespace by=checkpoint_cc_load_observer;namespace pc=checkpoint_identity_pair_commit;
extern "C" {
std::uint64_t IpcFixtureWorkerInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureReadInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureUpdateInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureWorkerOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureReadOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureUpdateOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void IpcFixtureWorkerReturn();void IpcFixtureReadReturn();void IpcFixtureUpdateReturn();
void** IpcFixtureSlots=nullptr;
std::uint64_t IpcFixtureUserInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureMenuInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureGameInvoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureUserOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureMenuOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t IpcFixtureGameOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void IpcFixtureUserReturn();void IpcFixtureMenuReturn();void IpcFixtureGameReturn();
std::uint64_t IpcFixtureParent=0,IpcFixtureReadRax=0,IpcFixtureWorkerRax=0;
unsigned char IpcFixtureReadXmm[16]{},IpcFixtureWorkerXmm[16]{};
unsigned char IpcFixturePattern[32]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16};
}
namespace ns=checkpoint_guest_native_session;namespace rq=checkpoint_load_request_commit;namespace bd=checkpoint_load_input_boundary;
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
static void invokeWorker(uintptr_t self){IpcFixtureWorkerInvoke(self,0x1122334455667788ull,0x8877665544332211ull,0x123456789abcdef0ull);}
extern "C" std::uint64_t IpcFixtureReadBody(std::uint64_t self,std::uint64_t name,std::uint64_t data,std::uint64_t amount){
    ++readCalls;check(self==storage&&strcmp(reinterpret_cast<char*>(name),by::TargetName)==0&&amount==by::TargetSize,"actual read arguments");
    if(scenario==L"read-exception"&&readCalls>=3)RaiseException(0xE014CC91,0,0,nullptr);
    memcpy(reinterpret_cast<void*>(data),archive.data(),archive.size());
    if((scenario==L"actual-byte-mismatch"&&readCalls>=3)||scenario==L"preflight-corrupt")reinterpret_cast<unsigned char*>(data)[15363]^=1;
    return 0xFEDCBA9800000000ull|by::TargetSize;
}
extern "C" void IpcFixtureWorkerBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    ++workerCalls;check(a==0x1122334455667788ull&&b==0x8877665544332211ull&&c==0x123456789abcdef0ull,"generic four argument ABI");
    if(self==otherCallable){++otherBodies;return;}
    if(self==loadCallable){
        ++loadBodies;if(scenario==L"stop-during-load")session.Stop();if(scenario==L"load-exception")RaiseException(0xE014CC92,0,0,nullptr);
        IpcFixtureReadInvoke(storage,uintptr_t(by::TargetName),uintptr_t(buffer.data()),by::TargetSize);
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
extern "C" void IpcFixtureUpdateBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
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
extern "C" void IpcFixtureUserBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){++userBodies;check(self==layout.config.states[4],"original User");}
extern "C" void IpcFixtureMenuBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){++menuBodies;check(self==layout.config.menu,"original Menu");}
extern "C" void IpcFixtureGameBody(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){
    ++gameBodies;check(self==layout.config.states[2],"original Game");
    if(at<DWORD>(cache+0x3EC)==63){put<DWORD>(base+0x201ECD0,63);sso(base+0x201ECE0,by::TargetName);}
}
static void userAfterController(void*,ns::Session&owner,const CheckpointPushFrame*f){
    // Explicit normal QueueMenu double. It runs only inside production Session's
    // User AFTER, after all hooks are armed; no constructor is called by Session.
    put<std::uint64_t>(base+0x19E7310+0x30,1);put<DWORD>(pending,0);put<uintptr_t>(pending+8,layout.config.menu);
    ns::QueueReceipt r{};r.attempt=layout.config.attempt;r.userCall=f->call_id;r.thread=f->thread_id;r.user=uintptr_t(f->args[0]);r.menu=layout.config.menu;r.nativeQueueReturned=true;
    if(scenario==L"wrong-queue-receipt")++r.userCall;
    owner.BindQueuedMenu(r); // Stop can legitimately race this synthetic queue.
}
static HANDLE shutdownEvent=nullptr;
static DWORD WINAPI ownerLoop(void*){
    ns::Report r{};
    while(WaitForSingleObject(shutdownEvent,10)==WAIT_TIMEOUT){session.Snapshot(r);if(r.armed||r.stopRequested)break;}
    session.Snapshot(r);if(!r.armed||r.stopRequested)return 0;
    IpcFixtureUserInvoke(layout.config.states[4],1,2,3);session.Snapshot(r);if(!r.menuBound)return 0;
    put<std::uint64_t>(base+0x19E7310+0x10,6);put<uintptr_t>(stackArray+40,layout.config.menu);put<std::uint64_t>(base+0x19E7310+0x30,0);layout.setStage(bd::Stage::MenuAfter);
    IpcFixtureMenuInvoke(layout.config.menu,0x1001,0x1002,0x1003);
    layout.setStage(bd::Stage::GameBefore);IpcFixtureGameInvoke(layout.config.states[2],0x1001,0x1002,0x1003);session.Snapshot(r);
    if(!r.casPublished)return 0;
    put<std::uint64_t>(base+0x19E7310+0x10,4);put<uintptr_t>(stackArray+16,title);put<uintptr_t>(stackArray+24,load);put<std::uint64_t>(base+0x19E7310+0x30,0);
    invokeWorker(otherCallable);for(unsigned i=0;i<4;++i)IpcFixtureUpdateInvoke(load,1,2,3);
    DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_NOACCESS,&old)!=0,"historical Load inaccessible");
    titleInvokeWithException();session.Snapshot(r);
    // All actual callbacks above use production Session. No report is assigned.
    // These are synthetic native game bodies; the IPC transport is real Win32.
    return 0;
}
static bool randomBytes(void*p,ULONG n){return BCryptGenRandom(nullptr,static_cast<PUCHAR>(p),n,BCRYPT_USE_SYSTEM_PREFERRED_RNG)>=0;}
static std::string hex(const unsigned char*p,size_t n){const char*h="0123456789abcdef";std::string out;for(size_t i=0;i<n;++i){out+=h[p[i]>>4];out+=h[p[i]&15];}return out;}
static bool parseWire(const wchar_t*text,unsigned char*out){
    if(!text||wcslen(text)!=32)return false;unsigned all=0;
    for(unsigned i=0;i<16;++i){unsigned v=0;for(unsigned j=0;j<2;++j){auto c=text[i*2+j];if(c>=L'0'&&c<=L'9')v=v*16+unsigned(c-L'0');else if(c>=L'a'&&c<=L'f')v=v*16+unsigned(c-L'a'+10);else return false;}out[i]=static_cast<unsigned char>(v);all|=v;}return all!=0;
}
static std::uint64_t ownBirth(){FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
static bool awaitBinding(unsigned char*attempt,unsigned char*intent,DWORD lifetime){
    // Dedicated parent-owned anonymous stdin pipe. No path, secret or pointer
    // is accepted; this is fixture bootstrap, not the formal Session IPC wire.
    HANDLE input=GetStdHandle(STD_INPUT_HANDLE);char line[80]{};DWORD used=0;const auto end=GetTickCount64()+lifetime;
    while(GetTickCount64()<end){DWORD available=0;if(!PeekNamedPipe(input,nullptr,0,nullptr,&available,nullptr))return false;
        if(!available){Sleep(10);continue;}DWORD got=0;char c=0;if(!ReadFile(input,&c,1,&got,nullptr)||got!=1)return false;
        if(c=='\n'){if(used!=70||memcmp(line,"BIND ",5)||line[37]!=' ')return false;wchar_t a[33]{},i[33]{};
            for(unsigned n=0;n<32;++n){a[n]=static_cast<unsigned char>(line[5+n]);i[n]=static_cast<unsigned char>(line[38+n]);}return parseWire(a,attempt)&&parseWire(i,intent);}
        if(used>=sizeof(line)-1)return false;line[used++]=c;
    }return false;
}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);DWORD client=0,idle=5000,lifetime=120000;bool deferred=false,staged=false,haveAttempt=false,haveIntent=false;
    unsigned char suffix[16]{},secret[32]{},attempt[16]{},intent[16]{};
    if((argc-1)%2)return 2;
    for(int i=1;i+1<argc;i+=2){
        if(!wcscmp(argv[i],L"--wire-attempt")){if(haveAttempt||!parseWire(argv[i+1],attempt))return 2;haveAttempt=true;continue;}
        if(!wcscmp(argv[i],L"--wire-intent")){if(haveIntent||!parseWire(argv[i+1],intent))return 2;haveIntent=true;continue;}
        wchar_t*tail=nullptr;auto value=wcstoul(argv[i+1],&tail,10);if(!tail||*tail)return 2;
        if(!wcscmp(argv[i],L"--client-pid"))client=value;else if(!wcscmp(argv[i],L"--idle-ms"))idle=value;
        else if(!wcscmp(argv[i],L"--lifetime-ms"))lifetime=value;else if(!wcscmp(argv[i],L"--defer-bind")&&value==1)deferred=true;
        else if(!wcscmp(argv[i],L"--staged")&&value==1)staged=true;else return 2;
    }
    if(!client||idle<100||idle>60000||lifetime<100||lifetime>300000)return 2;
    if(haveAttempt!=haveIntent||(deferred&&(haveAttempt||haveIntent))||(staged&&!deferred&&!haveAttempt))return 2;
    const auto stamp=ownBirth();if(!stamp)return 3;
    if(deferred){printf("{\"fixture_prepared\":true,\"server_pid\":%lu,\"server_birth\":\"%llu\",\"waiting_for_binding\":true,\"has_window\":false}\n",GetCurrentProcessId(),static_cast<unsigned long long>(stamp));fflush(stdout);
        if(!awaitBinding(attempt,intent,lifetime))return 2;haveAttempt=haveIntent=true;}
    scenario=L"ipc-success";
    wchar_t imagePath[32768]{};auto length=GetModuleFileNameW(nullptr,imagePath,_countof(imagePath));if(!length||length>=_countof(imagePath))return 3;
    auto slash=wcsrchr(imagePath,L'\\');if(!slash)return 3;*slash=0;std::wstring directory=imagePath;
    auto source=directory+L"\\checkpoint_push_archives\\20261006-204306-581930\\mppush01.s14";
    if(!randomBytes(suffix,16)||!randomBytes(secret,32)||(!haveAttempt&&!randomBytes(attempt,16))||(!haveIntent&&!randomBytes(intent,16)))return 3;
    auto id=hex(suffix,16);std::wstring wid(id.begin(),id.end());auto parent=directory+L"\\checkpoint_session_ipc_fixture_runs";
    std::wstring run;
    if(staged){auto a=hex(attempt,16);std::wstring wa(a.begin(),a.end());auto stage=directory+L"\\checkpoint_test_bootstrap_stages\\"+wa;
        auto attrs=GetFileAttributesW(stage.c_str());if(attrs==INVALID_FILE_ATTRIBUTES||!(attrs&FILE_ATTRIBUTE_DIRECTORY)||(attrs&FILE_ATTRIBUTE_REPARSE_POINT))return 3;
        source=stage+L"\\world.s14";auto marker=stage+L"\\stage-ready.json";attrs=GetFileAttributesW(marker.c_str());
        if(attrs==INVALID_FILE_ATTRIBUTES||(attrs&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)))return 3;
        attrs=GetFileAttributesW(source.c_str());if(attrs==INVALID_FILE_ATTRIBUTES||(attrs&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)))return 3;
        run=stage+L"\\native";
    }else{if(!CreateDirectoryW(parent.c_str(),nullptr)&&GetLastError()!=ERROR_ALREADY_EXISTS)return 3;run=parent+L"\\"+wid;}
    if(!CreateDirectoryW(run.c_str(),nullptr))return 3;
    auto local=run+L"\\svdexccSC03.s14",requestIntent=run+L"\\request.intent",identityIntent=run+L"\\identity.intent";
    if(!CopyFileW(source.c_str(),local.c_str(),TRUE))return 3;
    archive.resize(by::TargetSize);buffer.resize(by::TargetSize);FILE*f=nullptr;_wfopen_s(&f,local.c_str(),L"rb");if(!f)return 3;
    bool exact=fread(archive.data(),1,archive.size(),f)==archive.size()&&fgetc(f)==EOF;fclose(f);unsigned char hash[32]{};
    if(!exact||!native_storage_read::Sha256(archive.data(),archive.size(),hash)||memcmp(hash,by::TargetSha256,32))return 3;
    setup();
    ns::Config c{};c.request.boundary=layout.config;c.request.boundary.menu=0;c.request.localPath=local.c_str();c.request.intentPath=requestIntent.c_str();memset(c.request.ownerBinding,0x63,32);c.request.validate=requestGuard;
    c.request.storage={reinterpret_cast<void*>(storage),exists,fileSize,reinterpret_cast<native_storage_read::FileRead>(&IpcFixtureReadOriginal),storageValid,nullptr};
    c.bytes.base=base;c.bytes.storage=storage;c.bytes.storageVtable=storage+16;c.bytes.readMethod=uintptr_t(&IpcFixtureReadOriginal);c.bytes.attemptToken=layout.config.attempt;c.bytes.validateAttachment=byteGuard;c.bytes.fixtureWorkerCaller=uintptr_t(&IpcFixtureWorkerReturn);c.bytes.fixtureReadCaller=uintptr_t(&IpcFixtureReadReturn);c.bytes.fixtureParentCaller=0xAABBCC1234567890ull;IpcFixtureParent=c.bytes.fixtureParentCaller;
    c.lifecycle.base=base;c.lifecycle.attemptToken=layout.config.attempt;c.lifecycle.validateAttachment=lifeGuard;c.lifecycle.fixtureUpdateCaller=uintptr_t(&IpcFixtureUpdateReturn);
    c.identity.base=base;c.identity.attemptToken=layout.config.attempt;c.identity.intentPath=identityIntent.c_str();memset(c.identity.ownerBinding,0x63,32);c.identity.validateAttachment=identityGuard;c.identity.fixtureWorkerCaller=uintptr_t(&IpcFixtureWorkerReturn);
    c.validate=sessionGuard;c.userAfter=userAfterController;
    uintptr_t labels[]={uintptr_t(&IpcFixtureUserReturn),uintptr_t(&IpcFixtureMenuReturn),uintptr_t(&IpcFixtureGameReturn),uintptr_t(&IpcFixtureUpdateReturn)};memcpy(c.fixtureDispatchCaller,labels,sizeof labels);
    void* originals[]={reinterpret_cast<void*>(&IpcFixtureUserOriginal),reinterpret_cast<void*>(&IpcFixtureMenuOriginal),reinterpret_cast<void*>(&IpcFixtureGameOriginal),reinterpret_cast<void*>(&IpcFixtureUpdateOriginal),reinterpret_cast<void*>(&IpcFixtureWorkerOriginal),reinterpret_cast<void*>(&IpcFixtureReadOriginal)};
    void* bridges[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};
    IpcFixtureSlots=reinterpret_cast<void**>(alloc(4096));for(unsigned i=0;i<6;++i){IpcFixtureSlots[i]=originals[i];c.hooks[i]={IpcFixtureSlots+i,originals[i],bridges[i]};}DWORD protection=0;
    if(!VirtualProtect(IpcFixtureSlots,4096,PAGE_READONLY,&protection)||!session.Initialize(c))return 4;
    auto pipe=L"\\\\.\\pipe\\san14-checkpoint-"+wid;
    checkpoint_session_ipc::Config transport{};transport.session=&session;transport.pipeName=pipe.c_str();transport.expectedClientPid=client;transport.idleTimeoutMs=idle;transport.nativeAttempt=layout.config.attempt;memcpy(transport.secret,secret,32);memcpy(transport.attempt,attempt,16);memcpy(transport.expectedIntent,intent,16);
    checkpoint_session_ipc::Server server;if(!server.Open(transport))return 5;
    shutdownEvent=CreateWaitableTimerW(nullptr,TRUE,nullptr);if(!shutdownEvent)return 6;LARGE_INTEGER due{};due.QuadPart=-LONGLONG(lifetime)*10000;
    if(!SetWaitableTimer(shutdownEvent,&due,0,nullptr,nullptr,FALSE))return 6;
    HANDLE owner=CreateThread(nullptr,0,ownerLoop,nullptr,0,nullptr);if(!owner)return 6;
    auto secretHex=hex(secret,32),attemptHex=hex(attempt,16),intentHex=hex(intent,16);
    // Only this single parent-owned stdout handshake carries the secret. No
    // file/log/report receives it; root test must redact its captured stdout.
    printf("{\"ready\":true,\"pipe\":\"\\\\\\\\.\\\\pipe\\\\san14-checkpoint-%s\",\"server_pid\":%lu,\"server_birth\":\"%llu\",\"attempt\":\"%s\",\"intent\":\"%s\",\"secret\":\"%s\"}\n",id.c_str(),GetCurrentProcessId(),static_cast<unsigned long long>(stamp),attemptHex.c_str(),intentHex.c_str(),secretHex.c_str());fflush(stdout);
    SecureZeroMemory(secret,sizeof secret);SecureZeroMemory(transport.secret,sizeof transport.secret);SecureZeroMemory(secretHex.data(),secretHex.size());
    const bool ok=server.Run(shutdownEvent);session.Stop();WaitForSingleObject(owner,20000);CloseHandle(owner);CloseHandle(shutdownEvent);
    return ok&&!failures?0:7;
}
