#include "checkpoint_live_storage_binding.h"
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <string>
namespace sb=checkpoint_live_storage_binding;
extern "C" { std::uint64_t BindingFixtureGeneration=1; void BindingFixtureContextInit(); }
alignas(16) static std::uintptr_t vt[16]{};
alignas(16) static std::uintptr_t object[2]{};
static unsigned failures=0,readCalls=0,hookCalls=0;
static bool ownerValid=true,hookValid=true,mutateDuringOwner=false,faultDuringOwner=false;
static sb::Config configuration{};
static void check(bool ok,const char* label){if(!ok){++failures;std::printf("FAIL %s\n",label);}}
__declspec(noinline) static bool __fastcall exists(void*,const char*){return true;}
__declspec(noinline) static std::int32_t __fastcall size(void*,const char*){return 7;}
__declspec(noinline) static std::int32_t __fastcall read(void*,const char*,void*,std::int32_t){++readCalls;return 7;}
__declspec(noinline) static std::int32_t __fastcall hook(void*,const char*,void*,std::int32_t){++hookCalls;return 99;}
__declspec(noinline) static std::int32_t __fastcall foreign(void*,const char*,void*,std::int32_t){return 22;}
static std::uint64_t birth(){FILETIME b{},e{},k{},u{};GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u);return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
static bool owner(void*,const sb::Attachment& a,sb::Point p)noexcept{
    if(faultDuringOwner)RaiseException(0xE0145101,0,0,nullptr);
    if(mutateDuringOwner&&p==sb::Point::Validate)++BindingFixtureGeneration;
    return ownerValid&&a.pid==configuration.attachment.pid&&a.birth==configuration.attachment.birth&&
        a.base==configuration.attachment.base&&a.attempt==configuration.attachment.attempt&&a.generation==configuration.attachment.generation&&
        !std::memcmp(a.id,configuration.attachment.id,32);
}
static bool ownedHook(void*,std::uintptr_t slot,std::uintptr_t original,std::uintptr_t bridge)noexcept{
    return hookValid&&slot==reinterpret_cast<std::uintptr_t>(vt)+8&&original==reinterpret_cast<std::uintptr_t>(&read)&&bridge==reinterpret_cast<std::uintptr_t>(&hook);
}
static void parseHex(const wchar_t* p,unsigned char* out){for(unsigned i=0;i<32;++i){unsigned v=0;swscanf_s(p+i*2,L"%2x",&v);out[i]=static_cast<unsigned char>(v);}}
static sb::Endpoint endpoint(void* p){sb::Endpoint e{};e.address=reinterpret_cast<std::uintptr_t>(p);std::memcpy(e.first32,p,32);return e;}
static DWORD WINAPI otherThread(void* p){return static_cast<sb::Context*>(p)->Valid()?0:1;}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=3)return 2;
    const std::wstring scenario=argv[1];const auto exe=reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
    auto& c=configuration;
    auto base=reinterpret_cast<std::uintptr_t>(VirtualAlloc(nullptr,0x1A00000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));check(base!=0,"owned layout allocates");if(!base)return 3;
    c.attachment.pid=GetCurrentProcessId();c.attachment.birth=birth();c.attachment.base=base;c.attachment.attempt=77;c.attachment.generation=5;c.attachment.id[0]=9;
    parseHex(L"42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025",c.attachment.gameSha256);
    c.moduleCount=1;auto& m=c.modules[0];m.base=exe;GetModuleFileNameW(nullptr,m.path,1024);
    auto* pe=reinterpret_cast<IMAGE_NT_HEADERS64*>(exe+reinterpret_cast<IMAGE_DOS_HEADER*>(exe)->e_lfanew);m.sizeOfImage=pe->OptionalHeader.SizeOfImage;m.timestamp=pe->FileHeader.TimeDateStamp;
    WIN32_FILE_ATTRIBUTE_DATA fa{};GetFileAttributesExW(m.path,GetFileExInfoStandard,&fa);m.fileSize=(std::uint64_t(fa.nFileSizeHigh)<<32)|fa.nFileSizeLow;
    parseHex(argv[2],m.fileSha256);native_storage_read::Sha256(reinterpret_cast<void*>(exe),4096,m.headerSha256);
    c.contextInit=endpoint(reinterpret_cast<void*>(&BindingFixtureContextInit));c.exists=endpoint(reinterpret_cast<void*>(&exists));c.size=endpoint(reinterpret_cast<void*>(&size));c.read=endpoint(reinterpret_cast<void*>(&read));
    c.ownedReadBridge=endpoint(reinterpret_cast<void*>(&hook));c.checkOwnedReadBridge=ownedHook;c.checkOwner=owner;
    c.counter=reinterpret_cast<std::uintptr_t>(&BindingFixtureGeneration);c.cachedGeneration=1;c.vtable=reinterpret_cast<std::uintptr_t>(vt);c.storage=reinterpret_cast<std::uintptr_t>(object);
    object[0]=c.vtable;vt[1]=c.read.address;vt[13]=c.exists.address;vt[15]=c.size.address;
    std::memcpy(c.contextCode,reinterpret_cast<void*>(c.contextInit.address),sizeof c.contextCode);
    *reinterpret_cast<std::uintptr_t*>(base+0x123CB28)=c.contextInit.address;
    auto* token=reinterpret_cast<std::uintptr_t*>(base+0x18D08B8);token[0]=base+0x2FCB90;token[1]=1;token[2]=c.storage;
    constexpr char version[]="STEAMREMOTESTORAGE_INTERFACE_VERSION014";
    std::memcpy(reinterpret_cast<void*>(base+0x12AA6B8),version,sizeof version);
    sb::Context binding;
    bool rejectOpen=false;
    if(scenario==L"bad-file-sha"){c.modules[0].fileSha256[0]^=1;rejectOpen=true;}
    if(scenario==L"bad-module-base"){c.modules[0].base+=4096;rejectOpen=true;}
    if(scenario==L"bad-module-owner"){c.read.moduleIndex=2;rejectOpen=true;}
    if(scenario==L"bad-module-path"){c.modules[0].path[0]=L'Z';rejectOpen=true;}
    if(scenario==L"bad-header"){c.modules[0].headerSha256[0]^=1;rejectOpen=true;}
    if(scenario==L"bad-attachment"){--c.attachment.birth;rejectOpen=true;}
    if(scenario==L"bad-version"){*reinterpret_cast<char*>(base+0x12AA6B8)='X';rejectOpen=true;}
    if(scenario==L"bad-fastpath"){c.contextCode[0x17]=0x75;rejectOpen=true;}
    if(scenario==L"bad-method-code"){c.read.first32[0]^=1;rejectOpen=true;}
    if(scenario==L"cross-page-code"){c.read.address=exe+m.sizeOfImage-16;rejectOpen=true;}
    const bool opened=binding.Open(c);check(opened!=rejectOpen,"expected Open result");
    if(rejectOpen){check(!binding.Valid()&&!binding.Api().read,"rejected config has no usable Api");}
    else if(opened){
        const auto api=binding.Api();check(api.read==&read&&api.validate&&api.storage==object,"immutable original API");
        bool expectValid=true;DWORD tokenProtection=0;
        if(scenario==L"generation-global"){++BindingFixtureGeneration;expectValid=false;}
        if(scenario==L"generation-token"){++token[1];expectValid=false;}
        if(scenario==L"storage-change"){token[2]+=8;expectValid=false;}
        if(scenario==L"vtable-change"){object[0]+=8;expectValid=false;}
        if(scenario==L"foreign-read-hook"){vt[1]=reinterpret_cast<std::uintptr_t>(&foreign);expectValid=false;}
        if(scenario==L"owned-read-hook"||scenario==L"unowned-read-hook"){vt[1]=reinterpret_cast<std::uintptr_t>(&hook);hookValid=scenario==L"owned-read-hook";expectValid=hookValid;}
        if(scenario==L"owner-invalidation"){ownerValid=false;expectValid=false;}
        if(scenario==L"owner-mutates-generation"){mutateDuringOwner=true;expectValid=false;}
        if(scenario==L"owner-fault"){faultDuringOwner=true;expectValid=false;}
        if(scenario==L"invalidated"){binding.Invalidate();expectValid=false;}
        if(scenario==L"token-noaccess"){VirtualProtect(reinterpret_cast<void*>(base+0x18D0000),4096,PAGE_NOACCESS,&tokenProtection);expectValid=false;}
        // This case intentionally exercises wrapper-independent ownership on a
        // new thread. Provider supplies the permitted boundary; no sticky game
        // thread ID is inferred from the installer.
        if(scenario==L"allowed-new-thread"){HANDLE t=CreateThread(nullptr,0,otherThread,&binding,0,nullptr);check(t!=nullptr,"new owned thread");if(t){WaitForSingleObject(t,3000);DWORD code=1;GetExitCodeThread(t,&code);check(code==0,"provider-approved new thread validates");CloseHandle(t);}}
        check(api.validate(api.validationContext)==expectValid,"validation rejects drift or accepts exact binding");
        if(tokenProtection){DWORD ignored=0;VirtualProtect(reinterpret_cast<void*>(base+0x18D0000),4096,tokenProtection,&ignored);}
        if(expectValid){check(api.read(api.storage,"fixture",nullptr,0)==7&&readCalls==1&&hookCalls==0,"preflight calls original regardless of owned slot bridge");}
        else{BindingFixtureGeneration=1;token[1]=1;ownerValid=true;mutateDuringOwner=false;faultDuringOwner=false;check(!binding.Valid(),"failure cannot revive after fields revert");}
    }
    sb::Report r{};binding.Snapshot(r);
    check(!r.contextInitCalls&&!r.steamCalls&&!r.hookWrites&&!r.loadAuthorized&&r.fixtureBuild==1,"adapter never calls Steam/ContextInit or publishes native work");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"opened\":%u,\"error\":%ld,\"exception\":%lu,\"pinned\":%u,\"validations\":%u,\"fixture_only\":true,\"game_access\":false,\"steam_calls\":0}\n",scenario.c_str(),failures?"false":"true",failures,r.opened,LONG(r.error),r.exceptionCode,r.modulesPinned,r.validationCalls);
    // Binding/Api lifetime ends with this owned process; modules remain PINned.
    return failures?1:0;
}
