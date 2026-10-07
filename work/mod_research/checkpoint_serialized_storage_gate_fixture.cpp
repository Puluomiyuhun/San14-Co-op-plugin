// Reuse own-PE layout helpers and stable archived fastpath from the frozen
// binding fixture. Its old main is compiled but is never executed here.
#define wmain FrozenBindingFixtureMain
#include "checkpoint_live_storage_binding_fixture.cpp"
#undef wmain
#include "checkpoint_serialized_storage_gate.h"
#include <thread>
namespace sg=checkpoint_serialized_storage_gate;
static sg::Gate gate;
static HANDLE entered=nullptr,releaseOwner=nullptr;
static volatile LONG blockOwner=0,ownerEntered=0,recurseOwner=0,enterRecursion=0;
static bool recurseDuringOpen=false,nativeBodyChecks=false,bodyOtherValidation=false;
static bool gateOwner(void*,const sb::Attachment&a,sb::Point point)noexcept{
    if((point==sb::Point::Validate||recurseDuringOpen)&&InterlockedCompareExchange(&recurseOwner,0,0)&&!InterlockedCompareExchange(&enterRecursion,1,0)){
        check(!gate.Valid(),"recursive same-thread entrance refuses before lock");
    }
    if(point==sb::Point::Validate&&InterlockedCompareExchange(&blockOwner,0,0)&&!InterlockedCompareExchange(&ownerEntered,1,0)){
        SetEvent(entered);check(WaitForSingleObject(releaseOwner,4000)==WAIT_OBJECT_0,"controlled check released");
    }
    return owner(nullptr,a,point);
}
__declspec(noinline) static std::int32_t __fastcall gateRead(void*,const char*,void*,std::int32_t){
    ++readCalls;
    if(nativeBodyChecks){
        // A distinct actual thread validates while this native body remains on
        // stack. A lock held across the read would deadlock and time out here.
        const auto api=gate.Api();
        std::thread t([&]{bodyOtherValidation=api.validate(api.validationContext);});t.join();
    }
    return 7;
}
static void setupGate(const wchar_t* binarySha){
    auto& c=configuration;const auto exe=reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
    const auto base=reinterpret_cast<std::uintptr_t>(VirtualAlloc(nullptr,0x1A00000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    check(base!=0,"own game layout");
    c.attachment.pid=GetCurrentProcessId();c.attachment.birth=birth();c.attachment.base=base;c.attachment.attempt=77;c.attachment.generation=5;c.attachment.id[0]=9;
    parseHex(L"42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025",c.attachment.gameSha256);
    c.moduleCount=1;auto& m=c.modules[0];m.base=exe;GetModuleFileNameW(nullptr,m.path,1024);
    auto* pe=reinterpret_cast<IMAGE_NT_HEADERS64*>(exe+reinterpret_cast<IMAGE_DOS_HEADER*>(exe)->e_lfanew);
    m.sizeOfImage=pe->OptionalHeader.SizeOfImage;m.timestamp=pe->FileHeader.TimeDateStamp;
    WIN32_FILE_ATTRIBUTE_DATA fa{};GetFileAttributesExW(m.path,GetFileExInfoStandard,&fa);m.fileSize=(std::uint64_t(fa.nFileSizeHigh)<<32)|fa.nFileSizeLow;
    parseHex(binarySha,m.fileSha256);native_storage_read::Sha256(reinterpret_cast<void*>(exe),4096,m.headerSha256);
    c.contextInit=endpoint(reinterpret_cast<void*>(&BindingFixtureContextInit));c.exists=endpoint(reinterpret_cast<void*>(&exists));
    c.size=endpoint(reinterpret_cast<void*>(&size));c.read=endpoint(reinterpret_cast<void*>(&gateRead));c.checkOwner=gateOwner;
    c.counter=reinterpret_cast<std::uintptr_t>(&BindingFixtureGeneration);c.cachedGeneration=1;
    c.vtable=reinterpret_cast<std::uintptr_t>(vt);c.storage=reinterpret_cast<std::uintptr_t>(object);
    object[0]=c.vtable;vt[1]=c.read.address;vt[13]=c.exists.address;vt[15]=c.size.address;
    std::memcpy(c.contextCode,reinterpret_cast<void*>(c.contextInit.address),sizeof c.contextCode);
    *reinterpret_cast<std::uintptr_t*>(base+0x123CB28)=c.contextInit.address;
    auto* token=reinterpret_cast<std::uintptr_t*>(base+0x18D08B8);token[0]=base+0x2FCB90;token[1]=1;token[2]=c.storage;
    constexpr char version[]="STEAMREMOTESTORAGE_INTERFACE_VERSION014";
    std::memcpy(reinterpret_cast<void*>(base+0x12AA6B8),version,sizeof version);
    entered=CreateEventW(nullptr,TRUE,FALSE,nullptr);releaseOwner=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    check(entered&&releaseOwner,"owned synchronization events");
}
static bool waitQueued(){
    for(unsigned i=0;i<1000;++i){sg::Report r{};gate.Snapshot(r);if(r.queued)return true;Sleep(1);}return false;
}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=3)return 2;
    const std::wstring scenario=argv[1];setupGate(argv[2]);
    if(scenario==L"stop-before-open"){
        gate.Stop();check(!gate.Open(configuration)&&!gate.Valid()&&!gate.Api().read,"pre-open Stop cannot revive");
    }else if(scenario==L"recursive-open"){
        recurseDuringOpen=true;recurseOwner=1;check(!gate.Open(configuration),"Open callback recursion refuses");
    }else{
        check(gate.Open(configuration),"frozen Context opens through gate");const auto api=gate.Api();
        check(api.storage==object&&reinterpret_cast<std::uintptr_t>(api.exists)==configuration.exists.address&&
            reinterpret_cast<std::uintptr_t>(api.size)==configuration.size.address&&reinterpret_cast<std::uintptr_t>(api.read)==configuration.read.address&&api.validationContext==&gate,"only validation thunk/context replaced");
        if(scenario==L"concurrent-success"||scenario==L"stop-active-and-waiter"){
            blockOwner=1;bool a=false,b=false;
            std::thread first([&]{a=gate.Valid();});check(WaitForSingleObject(entered,4000)==WAIT_OBJECT_0,"first actual validator in owner callback");
            std::thread second([&]{b=api.validate(api.validationContext);});check(waitQueued(),"second real thread queues before Context.Valid");
            if(scenario==L"stop-active-and-waiter")gate.Stop();SetEvent(releaseOwner);first.join();second.join();
            check(scenario==L"concurrent-success"?(a&&b):(!a&&!b),"overlap succeeds or permanent Stop refuses both");
            if(scenario==L"concurrent-success")check(gate.Valid(),"overlap did not poison Context");
            else check(!gate.Valid()&&!api.validate(api.validationContext),"retained Api cannot revive stopped gate");
        }else if(scenario==L"recursive-valid"){
            recurseOwner=1;check(!api.validate(api.validationContext),"Api thunk rejects same-thread recursion");
            recurseOwner=0;check(!gate.Valid()&&!gate.Api().read,"recursion permanently invalidates");
        }else if(scenario==L"native-body-unlocked"){
            check(api.validate(api.validationContext),"before native read validates");nativeBodyChecks=true;
            check(api.read(api.storage,"fixture",nullptr,0)==7&&bodyOtherValidation&&readCalls==1,"native body permits independent thread validation");
            check(api.validate(api.validationContext),"after native read validates");
        }else if(scenario==L"generation-invalidated"){
            ++BindingFixtureGeneration;check(!gate.Valid(),"context generation drift refuses");BindingFixtureGeneration=1;
            check(!gate.Valid()&&!api.validate(api.validationContext)&&!gate.Api().read,"restoring generation does not revive");
        }else if(scenario==L"explicit-invalidate"){
            gate.Invalidate();check(!gate.Valid()&&!api.validate(api.validationContext),"explicit invalidation is permanent");
        }else if(scenario==L"repeated-open"){
            check(!gate.Open(configuration)&&!gate.Valid(),"repeated Open invalidates without reusing context");
        }else if(scenario==L"owner-fault"){
            faultDuringOwner=true;check(!gate.Valid(),"frozen Context contains owner SEH");faultDuringOwner=false;
            check(!gate.Valid(),"failed context cannot recover");
        }else if(scenario==L"success"){
            check(gate.Valid()&&api.validate(api.validationContext),"guard and API entrances share gate");
        }else check(false,"known scenario");
    }
    sg::Report r{};gate.Snapshot(r);
    check(r.maxActiveChecks<=1&&r.activeChecks==0,"Context.Valid calls serialized and drained");
    check(!r.nativeCalls&&!r.inputHeld&&!r.worldReady,"gate has no native/world/input authority");
    if(scenario==L"recursive-valid"||scenario==L"recursive-open")check(r.error==sg::Error::Recursion&&r.recursionRejected==1,"recursion diagnosed specifically");
    if(scenario==L"concurrent-success")check(r.error==sg::Error::None&&r.lastBinding.error==sb::Error::None&&r.queued>=1&&r.validationSucceeded==3,"actual concurrent receipt remains healthy");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"state\":%ld,\"error\":%ld,\"checks\":%u,\"success\":%u,\"queued\":%u,\"recursion\":%u,\"max_active\":%u,\"binding_error\":%ld,\"own_native_calls\":%u,\"game_access\":false,\"fixture_only\":true}\n",
        scenario.c_str(),failures?"false":"true",failures,LONG(r.state),LONG(r.error),r.validationAttempts,r.validationSucceeded,r.queued,r.recursionRejected,r.maxActiveChecks,LONG(r.lastBinding.error),readCalls);
    CloseHandle(entered);CloseHandle(releaseOwner);return failures?1:0;
}
