#include "checkpoint_live_storage_binding.h"
#include <bcrypt.h>
#include <cstring>
#include <cwchar>
#pragma comment(lib,"bcrypt.lib")

namespace checkpoint_live_storage_binding {
namespace {
constexpr char Version[]="STEAMREMOTESTORAGE_INTERFACE_VERSION014";
constexpr unsigned char GameSha[]={0x42,0xd5,0x3b,0xb4,0x2c,0x03,0x3c,0x60,0x27,0xb6,0xda,0x75,0xe8,0x07,0x7f,0x41,0x70,0xf4,0xd6,0x84,0xab,0xb0,0xf5,0x74,0x83,0xa6,0x61,0x22,0x5d,0x05,0x20,0x25};
constexpr unsigned char InitPrefix[]={0x40,0x53,0x48,0x83,0xec,0x20,0x48,0x8b,0x51,0x08,0x48,0x8b,0xd9,0x48,0x8b,0x05};
constexpr unsigned char InitBranch[]={0x48,0x3b,0xd0,0x74,0x42};
constexpr unsigned char InitReturn[]={0x48,0x8d,0x41,0x10,0x48,0x83,0xc4,0x20,0x5b,0xc3};
LONG get(volatile LONG& x)noexcept{return InterlockedCompareExchange(&x,0,0);}
template<class T>T at(std::uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool nonzero(const unsigned char* p,std::size_t n){unsigned x=0;for(std::size_t i=0;i<n;++i)x|=p[i];return x!=0;}
bool span(std::uintptr_t p,std::size_t n,std::uintptr_t image=0,bool execute=false){
    if(!p||!n||p+n<p)return false;const auto end=p+n;
    while(p<end){MEMORY_BASIC_INFORMATION m{};
        if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
            (m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;
        const DWORD prot=m.Protect&0xff;
        const bool readable=prot==PAGE_READONLY||prot==PAGE_READWRITE||prot==PAGE_WRITECOPY||prot==PAGE_EXECUTE_READ||prot==PAGE_EXECUTE_READWRITE||prot==PAGE_EXECUTE_WRITECOPY;
        if(!readable||(execute&&prot!=PAGE_EXECUTE_READ&&prot!=PAGE_EXECUTE_WRITECOPY)||
            (image&&(m.Type!=MEM_IMAGE||reinterpret_cast<std::uintptr_t>(m.AllocationBase)!=image)))return false;
        const auto next=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize;
        if(next<=p)return false;p=next<end?next:end;
    }return true;
}
std::uint64_t birth(){FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
bool trustedSteamPath(const wchar_t* path){
#ifdef CHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE
    return path&&*path; // Own PE only; never present in the production object.
#else
    return !_wcsicmp(path,L"C:\\Program Files (x86)\\Steam\\steamclient64.dll")||
        !_wcsicmp(path,L"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Romance_of_the_Three_Kingdoms_14\\steam_api64.dll");
#endif
}
bool fileHash(const ModuleApproval& a){
    HANDLE f=CreateFileW(a.path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(f==INVALID_HANDLE_VALUE)return false;
    BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
    LARGE_INTEGER size{};bool ok=GetFileSizeEx(f,&size)&&size.QuadPart>0&&std::uint64_t(size.QuadPart)==a.fileSize;
    unsigned char buffer[65536]{},digest[32]{};std::uint64_t total=0;
    if(ok)ok=BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0)>=0;
    while(ok){DWORD count=0;if(!ReadFile(f,buffer,sizeof buffer,&count,nullptr)){ok=false;break;}if(!count)break;
        total+=count;if(total>a.fileSize||BCryptHashData(hash,buffer,count,0)<0){ok=false;break;}}
    if(ok)ok=total==a.fileSize&&BCryptFinishHash(hash,digest,sizeof digest,0)>=0&&!std::memcmp(digest,a.fileSha256,32);
    if(hash)BCryptDestroyHash(hash);if(alg)BCryptCloseAlgorithmProvider(alg,0);
    if(!CloseHandle(f))ok=false;return ok;
}
}
bool Context::fail(Error e,DWORD exception,DWORD os)noexcept{
    InterlockedExchange(&active_,3);
    AcquireSRWLockExclusive(&reportLock_);
    if(report_.error==Error::None)report_.error=e;
    if(exception)report_.exceptionCode=exception;if(os)report_.osError=os;
    report_.invalidated=1;ReleaseSRWLockExclusive(&reportLock_);return false;
}
bool Context::module(unsigned i,bool open)noexcept{
    __try{
        if(i>=config_.moduleCount)return fail(Error::Module);
        const auto& a=config_.modules[i];
        if(!span(a.base,4096,a.base))return fail(Error::Page);
        const auto* dos=reinterpret_cast<const IMAGE_DOS_HEADER*>(a.base);
        if(dos->e_magic!=IMAGE_DOS_SIGNATURE||dos->e_lfanew<0x40||dos->e_lfanew>0x800)return fail(Error::ModuleHeader);
        const auto* nt=reinterpret_cast<const IMAGE_NT_HEADERS64*>(a.base+dos->e_lfanew);
        if(nt->Signature!=IMAGE_NT_SIGNATURE||nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC||
            nt->OptionalHeader.SizeOfImage!=a.sizeOfImage||nt->FileHeader.TimeDateStamp!=a.timestamp)return fail(Error::ModuleHeader);
        unsigned char hash[32]{};if(!native_storage_read::Sha256(reinterpret_cast<const void*>(a.base),4096,hash)||std::memcmp(hash,a.headerSha256,32))return fail(Error::ModuleHeader);
        HMODULE moduleHandle=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(a.base),&moduleHandle)||
            reinterpret_cast<std::uintptr_t>(moduleHandle)!=a.base)return fail(Error::Module,0,GetLastError());
        wchar_t path[1024]{};const DWORD count=GetModuleFileNameW(moduleHandle,path,1024);
        if(!count||count>=1024||_wcsicmp(path,a.path))return fail(Error::Module);
        if(open){
            if(!fileHash(a))return fail(Error::ModuleFile,0,GetLastError());
            HMODULE pinned=nullptr;
            if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(a.base),&pinned)||
                pinned!=moduleHandle)return fail(Error::Module,0,GetLastError());
            AcquireSRWLockExclusive(&reportLock_);++report_.modulesPinned;ReleaseSRWLockExclusive(&reportLock_);
        }return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Context::endpoint(const Endpoint& e)noexcept{
    __try{
        if(e.moduleIndex>=config_.moduleCount)return fail(Error::Module);
        const auto& m=config_.modules[e.moduleIndex];
        if(!e.address||e.address<m.base||e.address+32<e.address||e.address+32>m.base+m.sizeOfImage||
            !span(e.address,32,m.base,true))return fail(Error::Page);
        if(std::memcmp(reinterpret_cast<void*>(e.address),e.first32,32))return fail(Error::Code);
        HMODULE actual=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(e.address),&actual)||
            reinterpret_cast<std::uintptr_t>(actual)!=m.base)return fail(Error::Module);
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Context::inspect(Point point)noexcept{
    __try{
        if(get(active_)==3)return false;
        const auto& c=config_;const auto& a=c.attachment;const auto b=a.base;
        if(a.pid!=GetCurrentProcessId()||a.birth!=birth())return fail(Error::Attachment);
        if(!c.checkOwner(c.owner,a,point))return fail(Error::Owner);
        for(unsigned i=0;i<c.moduleCount;++i)if(!module(i,false))return false;
        if(!endpoint(c.contextInit)||!endpoint(c.exists)||!endpoint(c.size)||!endpoint(c.read))return false;
        if(c.ownedReadBridge.address&&!endpoint(c.ownedReadBridge))return false;
        if(!span(b+0x18D08B8,24)||!span(b+0x123CB28,8)||!span(b+0x12AA6B8,sizeof Version)||
            !span(c.contextInit.address,sizeof c.contextCode,c.modules[c.contextInit.moduleIndex].base,true))return fail(Error::Page);
        if(std::memcmp(reinterpret_cast<const void*>(b+0x12AA6B8),Version,sizeof Version)||
            at<std::uintptr_t>(b+0x18D08B8)!=b+0x2FCB90||at<std::uintptr_t>(b+0x123CB28)!=c.contextInit.address)return fail(Error::Token);
        if(std::memcmp(reinterpret_cast<void*>(c.contextInit.address),c.contextCode,sizeof c.contextCode))return fail(Error::Code);
        if(!span(c.counter,8,c.modules[c.counterModuleIndex].base)||
            at<std::uint64_t>(b+0x18D08B8+8)!=c.cachedGeneration||at<std::uint64_t>(c.counter)!=c.cachedGeneration)return fail(Error::Generation);
        if(at<std::uintptr_t>(b+0x18D08B8+16)!=c.storage||!span(c.storage,8)||at<std::uintptr_t>(c.storage)!=c.vtable)return fail(Error::Storage);
        if(!span(c.vtable,0x80,c.modules[c.vtableModuleIndex].base))return fail(Error::Vtable);
        if(at<std::uintptr_t>(c.vtable+0x68)!=c.exists.address||at<std::uintptr_t>(c.vtable+0x78)!=c.size.address)return fail(Error::Method);
        const auto readSlot=at<std::uintptr_t>(c.vtable+8);
        if(readSlot!=c.read.address){
            if(!c.ownedReadBridge.address||readSlot!=c.ownedReadBridge.address)return fail(Error::ReadSlot);
            if(!c.checkOwnedReadBridge||!c.checkOwnedReadBridge(c.owner,c.vtable+8,c.read.address,c.ownedReadBridge.address))return fail(Error::HookOwner);
        }
        // Re-read the lifetime graph after callbacks and module checks. This is
        // double-read consistency, not a lock against native object destruction.
        if(!c.checkOwner(c.owner,a,point))return fail(Error::Owner);
        if(at<std::uintptr_t>(b+0x123CB28)!=c.contextInit.address||at<std::uintptr_t>(b+0x18D08B8)!=b+0x2FCB90||
            at<std::uint64_t>(b+0x18D08B8+8)!=c.cachedGeneration||at<std::uint64_t>(c.counter)!=c.cachedGeneration)return fail(Error::Generation);
        if(at<std::uintptr_t>(b+0x18D08B8+16)!=c.storage||at<std::uintptr_t>(c.storage)!=c.vtable)return fail(Error::Storage);
        if(at<std::uintptr_t>(c.vtable+0x68)!=c.exists.address||at<std::uintptr_t>(c.vtable+0x78)!=c.size.address||at<std::uintptr_t>(c.vtable+8)!=readSlot)return fail(Error::Method);
        if(get(active_)==3)return false;
        AcquireSRWLockExclusive(&reportLock_);report_.readSlotWasOwnedBridge=readSlot!=c.read.address;ReleaseSRWLockExclusive(&reportLock_);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Context::Open(const Config& supplied)noexcept{
    if(InterlockedCompareExchange(&once_,1,0))return fail(Error::AlreadyUsed);
    __try{
        config_=supplied;const auto& c=config_;const auto& a=c.attachment;
#ifdef CHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE
        report_.fixtureBuild=1;
#else
        if(a.base!=reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr)))return fail(Error::Attachment);
#endif
        if(!a.pid||!a.birth||!a.base||!a.attempt||!a.generation||!nonzero(a.id,32)||std::memcmp(a.gameSha256,GameSha,32)||
            !c.checkOwner||!c.moduleCount||c.moduleCount>3||!c.storage||!c.vtable||!c.counter||
            c.counterModuleIndex>=c.moduleCount||c.vtableModuleIndex>=c.moduleCount||
            c.contextInit.moduleIndex>=c.moduleCount||c.exists.moduleIndex>=c.moduleCount||c.size.moduleIndex>=c.moduleCount||c.read.moduleIndex>=c.moduleCount||
            c.counterModuleIndex!=c.contextInit.moduleIndex||c.vtableModuleIndex!=c.exists.moduleIndex||c.vtableModuleIndex!=c.size.moduleIndex||c.vtableModuleIndex!=c.read.moduleIndex||
            bool(c.ownedReadBridge.address)!=bool(c.checkOwnedReadBridge)||c.ownedReadBridge.address==c.read.address)return fail(Error::Config);
        if((c.storage|c.vtable|c.counter)&7)return fail(Error::Config);
        if(std::memcmp(c.contextCode,InitPrefix,sizeof InitPrefix)||std::memcmp(c.contextCode+20,InitBranch,sizeof InitBranch)||
            std::memcmp(c.contextCode+0x5b,InitReturn,sizeof InitReturn)||std::memcmp(c.contextCode,c.contextInit.first32,32))return fail(Error::Code);
        std::int32_t displacement=0;std::memcpy(&displacement,c.contextCode+16,4);
        const auto calculated=std::int64_t(c.contextInit.address)+20+displacement;
        if(calculated<=0||std::uintptr_t(calculated)!=c.counter)return fail(Error::Generation);
        for(unsigned i=0;i<c.moduleCount;++i){const auto& m=c.modules[i];
            if(!m.base||m.sizeOfImage<4096||m.base+m.sizeOfImage<m.base||!m.path[0]||m.path[1023]||!m.fileSize||m.fileSize>512ull*1024*1024||
                !nonzero(m.fileSha256,32)||!nonzero(m.headerSha256,32))return fail(Error::Config);
            for(unsigned j=0;j<i;++j)if(m.base==c.modules[j].base)return fail(Error::Config);
        }
        if(!trustedSteamPath(c.modules[c.contextInit.moduleIndex].path)||!trustedSteamPath(c.modules[c.read.moduleIndex].path))return fail(Error::Module);
        if(!c.checkOwner(c.owner,a,Point::Open))return fail(Error::Owner);
        for(unsigned i=0;i<c.moduleCount;++i)if(!module(i,true))return false;
        if(!inspect(Point::Open))return false;
        api_.storage=reinterpret_cast<void*>(c.storage);api_.exists=reinterpret_cast<native_storage_read::FileExists>(c.exists.address);
        api_.size=reinterpret_cast<native_storage_read::GetFileSize>(c.size.address);api_.read=reinterpret_cast<native_storage_read::FileRead>(c.read.address);
        api_.validate=&Validate;api_.validationContext=this;
        AcquireSRWLockExclusive(&reportLock_);report_.opened=1;report_.holder=a.base+0x18D08B8+16;report_.storage=c.storage;report_.vtable=c.vtable;
        report_.originalRead=c.read.address;report_.counter=c.counter;report_.cachedGeneration=c.cachedGeneration;ReleaseSRWLockExclusive(&reportLock_);
        return InterlockedCompareExchange(&active_,2,0)==0;
    }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Context::Valid()noexcept{
    if(get(active_)!=2)return false;
    if(InterlockedCompareExchange(&validating_,1,0))return fail(Error::Reentrant);
    bool result=false;
    __try{AcquireSRWLockExclusive(&reportLock_);++report_.validationCalls;ReleaseSRWLockExclusive(&reportLock_);result=inspect(Point::Validate);}
    __finally{InterlockedExchange(&validating_,0);}
    return result&&get(active_)==2;
}
bool Context::Validate(void* p)noexcept{return p&&static_cast<Context*>(p)->Valid();}
native_storage_read::Api Context::Api()noexcept{return get(active_)==2?api_:native_storage_read::Api{};}
void Context::Invalidate()noexcept{fail(Error::Invalidated);}
void Context::Snapshot(Report& out)const noexcept{AcquireSRWLockShared(&reportLock_);out=report_;ReleaseSRWLockShared(&reportLock_);}
}
