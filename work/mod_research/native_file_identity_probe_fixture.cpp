#define NATIVE_FILE_IDENTITY_FIXTURE
#include "native_file_identity_probe.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <stdexcept>
#include <atomic>

using Export=DWORD(WINAPI*)(void*);
using Update=uint64_t(*)(void*,uintptr_t,uintptr_t,uintptr_t);
static std::wstring scenario;
static Export installFn=nullptr,stopFn=nullptr,getFn=nullptr;
static NativeFileIdentityConfig config;
static std::vector<unsigned char> bytes;
static std::atomic<unsigned> nativeCalls{0},guardCalls{0},readCalls{0};
static std::atomic<bool> guardOk{true};
static HANDLE entered=nullptr,proceed=nullptr;
static void* volatile* slot=nullptr;
static void* claimedEntry=nullptr;
static int userObject=0,storageObject=0,failures=0;
static bool argsOk=true,vtRestoredInsideOriginal=true,sehCaught=false,cppCaught=false;
static DWORD installResult=9999;
static constexpr uint64_t VALUE=0xfedcba9876543210ull;
static void check(bool ok,const char* label){if(!ok){++failures;std::printf("FAIL %s\n",label);}}
static DWORD protection(){MEMORY_BASIC_INFORMATION m{};VirtualQuery(const_cast<void**>(slot),&m,sizeof m);return m.Protect;}
static bool guard(void*){
    unsigned n=++guardCalls;
    if(scenario==L"stop-before-publication"&&n==1){SetEvent(entered);WaitForSingleObject(proceed,5000);}
    return guardOk.load();
}
static bool apiValidate(void*){return guardOk.load();}
static bool __fastcall exists(void* p,const char* name){return p==&storageObject&&!strcmp(name,"mppush01.s14");}
static int32_t __fastcall size(void*,const char*){return static_cast<int32_t>(bytes.size());}
static int32_t __fastcall read(void* p,const char* name,void* out,int32_t amount){
    ++readCalls;
    if(p!=&storageObject||strcmp(name,"mppush01.s14")||amount!=int32_t(bytes.size()))return -1;
    memcpy(out,bytes.data(),bytes.size());
    if(scenario==L"read-short")return 1;
    if(scenario==L"read-seh")RaiseException(0xE0142222,0,0,nullptr);
    if(scenario==L"stop-during-read")stopFn(nullptr);
    return amount;
}
static uint64_t original(void* self,uintptr_t a,uintptr_t b,uintptr_t c){
    unsigned n=++nativeCalls;
    void* wanted=scenario==L"wrong-self"?reinterpret_cast<void*>(uintptr_t(&userObject)+8):&userObject;
    if(self!=wanted||a!=0x1122334455667788ull||b!=0xFFEEDDCCBBAA0099ull||c!=0x123456789ABCDEF0ull)argsOk=false;
    if(*slot!=reinterpret_cast<void*>(&original)||protection()!=PAGE_READONLY)vtRestoredInsideOriginal=false;
    if(scenario==L"guard-drift-after-original")guardOk=false;
    if(scenario==L"stop-during-original")stopFn(nullptr);
    if(scenario==L"original-seh")RaiseException(0xE0141111,0,0,nullptr);
    if(scenario==L"original-cpp")throw std::runtime_error("original exception");
    if(scenario==L"concurrent-delayed-callback"&&n==1){SetEvent(entered);WaitForSingleObject(proceed,5000);}
    return VALUE;
}
static void invoke(void* entry){
    void* self=scenario==L"wrong-self"?reinterpret_cast<void*>(uintptr_t(&userObject)+8):&userObject;
    check(reinterpret_cast<Update>(entry)(self,0x1122334455667788ull,0xFFEEDDCCBBAA0099ull,0x123456789ABCDEF0ull)==VALUE,"RAX exact");
}
static void invokeSeh(void* entry){
    __try {invoke(entry);}
    __except(GetExceptionCode()==0xE0141111?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){sehCaught=true;}
}
static DWORD WINAPI invokeThread(void* entry){invoke(entry);return 0;}
static DWORD WINAPI installThread(void*){installResult=installFn(&config);return 0;}
static bool waitThread(HANDLE h){bool ok=WaitForSingleObject(h,5000)==WAIT_OBJECT_0;CloseHandle(h);return ok;}
static NativeFileIdentityReport snapshot(){NativeFileIdentityReport r{};check(getFn(&r)==0,"GetReport");return r;}

int wmain(int argc,wchar_t** argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    if(argc!=3)return 2;scenario=argv[1];
    entered=CreateEventW(nullptr,TRUE,FALSE,nullptr);proceed=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    bytes.resize(4096);for(size_t i=0;i<bytes.size();++i)bytes[i]=static_cast<unsigned char>((i*17+31)&255);
    HANDLE file=CreateFileW(argv[2],GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return 3;DWORD written=0;check(WriteFile(file,bytes.data(),DWORD(bytes.size()),&written,nullptr)&&written==bytes.size(),"fixture file create");CloseHandle(file);
    HMODULE dll=LoadLibraryW(L"native_file_identity_probe_fixture.dll");if(!dll)return 4;
    installFn=reinterpret_cast<Export>(GetProcAddress(dll,"InstallNativeFileIdentityProbe"));
    stopFn=reinterpret_cast<Export>(GetProcAddress(dll,"StopNativeFileIdentityProbe"));
    getFn=reinterpret_cast<Export>(GetProcAddress(dll,"GetNativeFileIdentityReport"));
    if(!installFn||!stopFn||!getFn)return 5;
    slot=reinterpret_cast<void* volatile*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    *slot=reinterpret_cast<void*>(&original);DWORD old=0;VirtualProtect(const_cast<void**>(slot),4096,PAGE_READONLY,&old);
    config.mode=scenario==L"dry"||scenario==L"install-publication-race"?0:1;
    config.expectedPid=GetCurrentProcessId();config.expectedBase=uintptr_t(GetModuleHandleW(nullptr));config.expectedUser=uintptr_t(&userObject);
    FILETIME born{},exit{},kernel{},cpu{};GetProcessTimes(GetCurrentProcess(),&born,&exit,&kernel,&cpu);
    config.expectedProcessBirth=(uint64_t(born.dwHighDateTime)<<32)|born.dwLowDateTime;
    wcsncpy_s(config.localPath,argv[2],_TRUNCATE);config.testSlot=slot;config.testExpectedOriginal=reinterpret_cast<void*>(&original);
    config.testGuard=guard;config.testApi={&storageObject,exists,size,read,apiValidate,nullptr};
    config.testSize=static_cast<uint32_t>(bytes.size());native_storage_read::Sha256(bytes.data(),bytes.size(),config.testSha256);
    if(scenario==L"wrong-original-stop")config.testExpectedOriginal=reinterpret_cast<void*>(&guard);
    if(scenario==L"install-exception-after-protect")config.testFailAfterProtect=1;

    if(scenario==L"stop-before-publication"){
        HANDLE it=CreateThread(nullptr,0,installThread,nullptr,0,nullptr);
        check(WaitForSingleObject(entered,5000)==WAIT_OBJECT_0,"prepublication guard entered");
        check(stopFn(nullptr)==0,"stop prepublication");SetEvent(proceed);check(waitThread(it),"install returned after stop");
        check(installResult==14,"installation cancelled before publication");
    }else if(scenario==L"install-publication-race"){
        config.testPublishedEvent=entered;config.testContinueInstall=proceed;
        HANDLE it=CreateThread(nullptr,0,installThread,nullptr,0,nullptr);
        check(WaitForSingleObject(entered,5000)==WAIT_OBJECT_0,"hook published before install return");
        claimedEntry=*slot;HANDLE tick=CreateThread(nullptr,0,invokeThread,claimedEntry,0,nullptr);
        bool claimed=false;
        for(unsigned n=0;n<500;++n){if(snapshot().claimCallId){claimed=true;break;}Sleep(1);}
        check(claimed,"before claimed while installer owns slot lock");
        SetEvent(proceed);check(waitThread(it)&&waitThread(tick),"publication race drains");check(installResult==0,"race install success");
    }else{
        installResult=installFn(&config);
        if(scenario==L"wrong-original-stop"||scenario==L"install-exception-after-protect"){
            check(installResult==(scenario==L"wrong-original-stop"?9u:13u),"expected install rejection");
            check(stopFn(nullptr)==0,"stop after rejected install");
        }else{
            check(installResult==0,"install success");claimedEntry=*slot;
            if(scenario==L"stop-before-claim")check(stopFn(nullptr)==0,"cancel before claim");
            if(scenario==L"original-seh")invokeSeh(claimedEntry);
            else if(scenario==L"original-cpp"){
                try{invoke(claimedEntry);}catch(const std::runtime_error& e){cppCaught=!strcmp(e.what(),"original exception");}
            }else if(scenario==L"concurrent-delayed-callback"){
                HANDLE first=CreateThread(nullptr,0,invokeThread,claimedEntry,0,nullptr);
                check(WaitForSingleObject(entered,5000)==WAIT_OBJECT_0,"first native delayed");
                HANDLE second=CreateThread(nullptr,0,invokeThread,claimedEntry,0,nullptr);
                check(waitThread(second),"prefetched concurrent entry returns");SetEvent(proceed);check(waitThread(first),"owner original returns");
            }else invoke(claimedEntry);
        }
    }
    auto r=snapshot();
    check(*slot==reinterpret_cast<void*>(&original)&&protection()==PAGE_READONLY,"actual VT and page restored");
    check(r.callbackActive==0&&r.bridge.active==0&&r.bridgeDrainedSnapshot==1,"callback and dispatcher drained snapshot");
    check(argsOk&&vtRestoredInsideOriginal,"args forwarded and early restore observed");
    check(r.verifyAttempts<=1&&readCalls<=2,"no repeated Verify or extra reads");
    if(scenario==L"read")check(r.state==FP_MATCHED&&r.identityMatched&&r.verifiedSize==bytes.size()&&r.readCalls==2&&r.localPinReleased,"full identity");
    if(scenario==L"dry"||scenario==L"install-publication-race")check(r.state==FP_DRY_DONE&&r.verifyAttempts==0&&r.contextCalls==0&&readCalls==0,"dry has no storage calls");
    if(scenario==L"stop-before-claim"||scenario==L"stop-during-original"||scenario==L"stop-before-publication")check(r.state==FP_CANCELLED&&r.verifyAttempts==0&&readCalls==0,"cancel before storage");
    if(scenario==L"original-seh"||scenario==L"original-cpp")check((sehCaught||cppCaught)&&r.state==FP_UNCERTAIN&&r.bridge.abnormal_exits==1&&r.bridge.after_calls==0&&r.verifyAttempts==0,"original exception propagates");
    if(scenario==L"guard-drift-after-original"||scenario==L"wrong-self")check(r.state==FP_REJECTED&&r.verifyAttempts==0,"bad boundary rejects");
    if(scenario==L"concurrent-delayed-callback")check(nativeCalls==2&&r.bridge.native_started==2&&r.bridge.native_returned==2&&r.reentrantClaims==1&&r.verifyAttempts==0&&r.state==FP_REJECTED,"concurrent originals once each, no probe");
    if(scenario==L"read-short"||scenario==L"read-seh")check(r.state==FP_REJECTED&&!r.identityMatched&&r.readCalls==1,"bad native read rejects");
    if(scenario==L"stop-during-read")check(r.state==FP_UNCERTAIN&&r.readCalls==1&&!r.identityMatched&&r.localPinReleased,"in-progress read not falsely cancelled");
    if(scenario!=L"concurrent-delayed-callback"&&scenario!=L"wrong-original-stop"&&scenario!=L"install-exception-after-protect"&&scenario!=L"stop-before-publication")check(nativeCalls==1,"original once");
    if(scenario==L"wrong-original-stop"||scenario==L"install-exception-after-protect"||scenario==L"stop-before-publication")check(nativeCalls==0&&r.bridge.started==0,"no original on rejected publication");
    check(!r.nativeLoadAuthorized&&!r.fullWorldVerified,"no load or world claim");
    HANDLE rw=CreateFileW(argv[2],GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    check(rw!=INVALID_HANDLE_VALUE,"local pin released to subsequent writer");
    std::vector<unsigned char> after(bytes.size());DWORD got=0;
    if(rw!=INVALID_HANDLE_VALUE){check(ReadFile(rw,after.data(),DWORD(after.size()),&got,nullptr)&&got==after.size()&&after==bytes,"fixture target bytes unchanged");CloseHandle(rw);}
    check(stopFn(nullptr)==0,"idempotent stop");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%d,\"state\":%ld,\"original_calls\":%u,\"bridge_started\":%llu,\"verify_attempts\":%u,\"read_calls\":%u,\"callback_active\":%u,\"slot_restored\":%u,\"page_restored\":%u,\"game_access\":false}\n",
        scenario.c_str(),failures?"false":"true",failures,long(r.state),nativeCalls.load(),r.bridge.started,r.verifyAttempts,r.readCalls,r.callbackActive,r.slotRestored,r.protectionRestored);
    CloseHandle(entered);CloseHandle(proceed);return failures?1:0;
}
