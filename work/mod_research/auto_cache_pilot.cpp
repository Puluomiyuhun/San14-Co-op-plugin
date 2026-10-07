#include "auto_cache_pilot.h"
#include "auto_cache_profile.h"
#include <intrin.h>
#include <cstring>
#include <cwchar>
#include <cstdio>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
extern "C" __declspec(dllexport) CacheReportData AutoCacheReport={CACHE_REPORT_MAGIC,1};
static CacheConfig cfg{};
static volatile LONG installed=0,claimed=0;
static uintptr_t base=0;
static void* volatile* hookSlot=nullptr;
static CacheUpdate originalUpdate=nullptr;
static CacheParameter parameter=nullptr;
static CacheScanner scanner=nullptr;
static DWORD initialProtection=0;
static constexpr uintptr_t USER_VT=0x12CC4A8,USER_UPDATE=0x3F9B00,STATE_MANAGER=0x19E7310;
template<class T>static T at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static bool reject(LONG code){if(!AutoCacheReport.error)AutoCacheReport.error=code;return false;}
static bool hashFile(const wchar_t* path,const unsigned char* expected){
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;
    BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;unsigned char data[65536],out[32];DWORD amount=0;bool ok=false;
    if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)>=0){
        ok=true;for(;;){if(!ReadFile(file,data,sizeof data,&amount,nullptr)){ok=false;break;}if(!amount)break;if(BCryptHashData(hash,data,amount,0)<0){ok=false;break;}}
        if(ok)ok=BCryptFinishHash(hash,out,32,0)>=0&&!memcmp(out,expected,32);
    }
    if(hash)BCryptDestroyHash(hash);if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);CloseHandle(file);return ok;
}
static bool exactCode(){for(const auto& p:CACHE_FINGERPRINTS)if(memcmp(reinterpret_cast<void*>(base+p.rva),p.bytes,p.size))return reject(52);return true;}
static bool stateGuard(void* self){
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    auto sm=base+STATE_MANAGER;
    if(at<uint64_t>(sm+0x10)!=5||at<uint64_t>(sm+0x30)!=0)return reject(10);
    auto stack=at<uintptr_t>(sm+0x20);
    if(!stack||at<uintptr_t>(stack+32)!=uintptr_t(self)||at<uintptr_t>(uintptr_t(self))!=base+USER_VT||at<uint32_t>(uintptr_t(self)+0x470)!=2||!at<uintptr_t>(uintptr_t(self)+0x478)||!at<uintptr_t>(uintptr_t(self)+0x618))return reject(11);
    for(unsigned i=0;i<5;++i){auto s=at<uintptr_t>(stack+8*i);if(!s||memcmp(reinterpret_cast<void*>(s+0x70),names[i],strlen(names[i])+1))return reject(12);}
    auto game=at<uintptr_t>(stack+16);if(at<uint32_t>(game+0x474)||at<uint32_t>(game+0x478))return reject(13);
    auto root=at<uintptr_t>(base+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);
    if(at<uintptr_t>(root)!=base+0x12AA6B0||at<uintptr_t>(world)!=base+0x12AA638)return reject(14);
    if(at<uint16_t>(world+0x34)!=203||at<uint8_t>(world+0x36)!=8||at<uint8_t>(world+0x37)!=11||at<uint8_t>(world+0x38)||at<uint8_t>(world+0x3A)!=12||at<uint32_t>(world+0x40)!=1||(at<uint32_t>(world+0x16A8)&0x100))return reject(15);
    auto force=at<uintptr_t>(root+0xDCA0+12*8),person=at<uintptr_t>(root+0x148+666*8),city=at<uintptr_t>(root+0xDAA8+19*8),district=at<uintptr_t>(root+0xDE40+11*8);
    if(at<uint16_t>(force+0x10)!=666||at<uint16_t>(person+0x10)!=666||at<uint8_t>(person+0x118)!=11||at<uint16_t>(person+0x11A)!=19||at<uint16_t>(city+0x10)!=19||at<uint8_t>(city+0x30)!=11||at<uint32_t>(city+0x3C)!=15204||at<uint8_t>(district+0x10)!=12||at<uint8_t>(district+0x14)!=18)return reject(16);
    unsigned active=0;for(unsigned i=1;i<=500;++i){auto army=at<uintptr_t>(root+0x7DF60+i*8);if(at<uint8_t>(army+0x10)&&at<uint16_t>(army+0x12)){++active;if(at<uint16_t>(army+0x12)==666)return reject(17);}}
    if(active!=56)return reject(18);
    auto manager=at<uintptr_t>(base+0x2025318);
    if(!manager||at<int32_t>(manager+8)!=0||at<int32_t>(manager+0x3EC)!=-1)return reject(19);
    AutoCacheReport.manager=manager;return true;
}
static bool emptyCache(){
    auto m=AutoCacheReport.manager;
    for(unsigned i=0;i<120;++i)if(at<uintptr_t>(m+0x20+i*8))return reject(30);
    auto sentinel=at<uintptr_t>(m+0x10);
    if(!sentinel||at<uint64_t>(m+0x18)||at<uintptr_t>(sentinel)!=sentinel||at<uintptr_t>(sentinel+8)!=sentinel)return reject(31);
    return true;
}
static bool guard(void* self){return exactCode()&&stateGuard(self)&&emptyCache();}
static bool validPath(){
    if(cfg.intentPath[511]||!cfg.intentPath[0]||wcsstr(cfg.intentPath,L".."))return reject(40);
#ifndef AUTO_CACHE_FIXTURE
    const wchar_t* prefix=L"C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\auto_cache_";
    if(wcsncmp(cfg.intentPath,prefix,wcslen(prefix)))return reject(40);
    const wchar_t* tail=cfg.intentPath+wcslen(prefix);if(!*tail||wcschr(tail,L'\\')||wcschr(tail,L'/')||wcschr(tail,L':'))return reject(40);
#endif
    return true;
}
static bool reserveIntent(){
    if(!validPath())return false;
    HANDLE file=CreateFileW(cfg.intentPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
    if(file==INVALID_HANDLE_VALUE)return reject(41);AutoCacheReport.intentCreated=1;
    char data[384];int size=sprintf_s(data,"{\"schema\":\"san14.cache-scan-once.v1\",\"pid\":%lu,\"thread\":%lu,\"manager\":%llu,\"status\":\"intent_uncertain_no_auto_retry\",\"native_parameter_rva\":3312928,\"native_scanner_rva\":8613616}\n",GetCurrentProcessId(),GetCurrentThreadId(),AutoCacheReport.manager);
    DWORD done=0;BOOL wrote=WriteFile(file,data,DWORD(size),&done,nullptr);BOOL flushed=FlushFileBuffers(file);CloseHandle(file);
    AutoCacheReport.intentFlushed=wrote&&done==DWORD(size)&&flushed;return AutoCacheReport.intentFlushed!=0||reject(42);
}
static bool scanOnce(void* self){
    if(!reserveIntent()||!guard(self))return false;
    auto root=at<uintptr_t>(base+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);unsigned char worldBefore[0x2200];memcpy(worldBefore,reinterpret_cast<void*>(world),sizeof worldBefore);
    auto rng=at<uint32_t>(base+0x18EB8B0);
    AutoCacheReport.parameterCalls++;int selector=parameter();AutoCacheReport.parameterValue=uint32_t(selector);if(selector!=0)return reject(43);
    AutoCacheReport.scannerCalls++;scanner(reinterpret_cast<void*>(AutoCacheReport.manager),selector);AutoCacheReport.scannerReturned=1;
    AutoCacheReport.worldUnchanged=at<uintptr_t>(base+0x1FCA1E0)==root&&at<uintptr_t>(root+0x85130)==world&&!memcmp(worldBefore,reinterpret_cast<void*>(world),sizeof worldBefore)&&at<uint32_t>(base+0x18EB8B0)==rng;
    if(!AutoCacheReport.worldUnchanged||!stateGuard(self))return reject(44);
    unsigned count=0;for(unsigned i=0;i<120;++i)if(at<uintptr_t>(AutoCacheReport.manager+0x20+i*8))++count;
    AutoCacheReport.cachedSlots=count;auto metadata=at<uintptr_t>(AutoCacheReport.manager+0x20+34*8);if(!metadata)return reject(45);
    const uintptr_t name=metadata+0x128;auto length=at<uint64_t>(name+16),capacity=at<uint64_t>(name+24);
    auto text=capacity>=16?at<uintptr_t>(name):name;
    AutoCacheReport.slot34Matched=length==13&&capacity>=13&&capacity<=32768&&!memcmp(reinterpret_cast<void*>(text),"svdexSC34.s14",14);
    return AutoCacheReport.slot34Matched!=0||reject(46);
}
static bool restoreSlot(){
    DWORD temp=0,ignored=0;if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&temp))return reject(20);
    void* old=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(AutoCacheReport.hook));
    AutoCacheReport.slotRestored=old==reinterpret_cast<void*>(AutoCacheReport.hook)||old==reinterpret_cast<void*>(originalUpdate);
    AutoCacheReport.protectionRestored=VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)!=0;return AutoCacheReport.slotRestored&&AutoCacheReport.protectionRestored;
}
static void __fastcall updateHook(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4){
    InterlockedIncrement(&AutoCacheReport.activeCallbacks);bool winner=InterlockedCompareExchange(&claimed,1,0)==0;
    if(winner){AutoCacheReport.status=2;AutoCacheReport.executorThread=GetCurrentThreadId();AutoCacheReport.caller=reinterpret_cast<uintptr_t>(_ReturnAddress());AutoCacheReport.state=uintptr_t(self);}
    bool restored=!winner||restoreSlot();
    __try{
        originalUpdate(self,a2,a3,a4);InterlockedIncrement(reinterpret_cast<volatile LONG*>(&AutoCacheReport.originalCalls));
        if(winner){__try{
#ifndef AUTO_CACHE_FIXTURE
            if(AutoCacheReport.caller!=base+0x50B785){reject(21);restored=false;}
#endif
            if(!restored||!guard(self))AutoCacheReport.status=5;
            else if(!cfg.execute)AutoCacheReport.status=3;
            else{bool success=scanOnce(self);AutoCacheReport.status=success?4:(AutoCacheReport.parameterCalls||AutoCacheReport.scannerCalls)?6:5;}
        }__except(EXCEPTION_EXECUTE_HANDLER){AutoCacheReport.exceptionCode=GetExceptionCode();AutoCacheReport.status=6;}}
    }__finally{InterlockedDecrement(&AutoCacheReport.activeCallbacks);}
}
extern "C" __declspec(dllexport) DWORD WINAPI InstallAutoCache(void* input){
    if(InterlockedCompareExchange(&installed,1,0)!=0)return 1001;AutoCacheReport.installerThread=GetCurrentThreadId();
    __try{
        cfg=*reinterpret_cast<const CacheConfig*>(input);
        if(cfg.magic!=CACHE_MAGIC||cfg.version!=1||cfg.execute>1||!validPath()){reject(50);AutoCacheReport.status=5;return 50;}
#ifdef AUTO_CACHE_FIXTURE
        base=cfg.testBase;parameter=reinterpret_cast<CacheParameter>(cfg.testParameter);scanner=reinterpret_cast<CacheScanner>(cfg.testScanner);
#else
        wchar_t path[32768]{};if(!GetModuleFileNameW(nullptr,path,32768)||!hashFile(path,CACHE_EXE_SHA)){reject(51);AutoCacheReport.status=5;return 51;}
        base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));parameter=reinterpret_cast<CacheParameter>(base+0x328D20);scanner=reinterpret_cast<CacheScanner>(base+0x836EF0);
#endif
        AutoCacheReport.base=base;hookSlot=reinterpret_cast<void* volatile*>(base+USER_VT+0x28);originalUpdate=reinterpret_cast<CacheUpdate>(*hookSlot);
#ifndef AUTO_CACHE_FIXTURE
        if(uintptr_t(originalUpdate)!=base+USER_UPDATE){reject(53);AutoCacheReport.status=5;return 53;}
#endif
        auto stack=at<uintptr_t>(base+STATE_MANAGER+0x20);if(!stack||!guard(reinterpret_cast<void*>(at<uintptr_t>(stack+32)))){AutoCacheReport.status=5;return AutoCacheReport.error;}
        AutoCacheReport.slot=uintptr_t(hookSlot);AutoCacheReport.original=uintptr_t(originalUpdate);AutoCacheReport.hook=uintptr_t(&updateHook);
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&initialProtection)){reject(54);AutoCacheReport.status=5;return 54;}
        AutoCacheReport.accepted=1;AutoCacheReport.status=1;
        void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(&updateHook),reinterpret_cast<void*>(originalUpdate));DWORD ignored=0;
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)){InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(&updateHook));reject(55);AutoCacheReport.status=5;return 55;}
        if(previous!=reinterpret_cast<void*>(originalUpdate)){reject(56);AutoCacheReport.status=5;return 56;}return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){AutoCacheReport.exceptionCode=GetExceptionCode();AutoCacheReport.status=6;return 1002;}
}
extern "C" __declspec(dllexport) DWORD WINAPI CancelAutoCache(void*){
    if(InterlockedCompareExchange(&claimed,2,0)!=0)return 1;if(!hookSlot||!AutoCacheReport.accepted)return 2;if(!restoreSlot()){AutoCacheReport.status=5;return 3;}AutoCacheReport.status=7;return 0;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
