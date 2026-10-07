#include "save_checkpoint_pilot.h"
#include <intrin.h>
#include <cstring>
#include <cwchar>
#include <cstdio>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#ifndef SAVE_CHECKPOINT_FIXTURE
#include "save_checkpoint_profile.h"
#endif

extern "C" __declspec(dllexport) SaveCheckpointReportData SaveCheckpointReport={SAVE_REPORT_MAGIC,1};
static SaveCheckpointConfig cfg{};
static volatile LONG installed=0,claimed=0;
static uintptr_t base=0;
static void* volatile* hookSlot=nullptr;
static SaveUpdate originalUpdate=nullptr;
static SaveBinder bindRequest=nullptr;
static SaveQueue queueSave=nullptr;
static DWORD initialProtection=0;
static char basename[16]{};
static constexpr uintptr_t USER_VT=0x12CC4A8,USER_UPDATE=0x3F9B00,MANAGER=0x19E7310;
static constexpr wchar_t REMOTE_ROOT[]=L"C:\\Program Files (x86)\\Steam\\userdata\\391007908\\872410\\remote\\";
static constexpr wchar_t WORK_ROOT[]=L"C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\save_checkpoint_";
template<class T> static T at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static bool reject(LONG code){if(!SaveCheckpointReport.error)SaveCheckpointReport.error=code;return false;}

static bool hashFile(const wchar_t* path,const unsigned char* expected){
    HANDLE file=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;
    BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
    unsigned char data[65536],out[32];DWORD amount=0;bool ok=false;
    if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0 &&
       BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)>=0){
        ok=true;
        for(;;){
            if(!ReadFile(file,data,sizeof data,&amount,nullptr)){ok=false;break;}
            if(!amount)break;
            if(BCryptHashData(hash,data,amount,0)<0){ok=false;break;}
        }
        if(ok)ok=BCryptFinishHash(hash,out,32,0)>=0 && !memcmp(out,expected,32);
    }
    if(hash)BCryptDestroyHash(hash);
    if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);
    CloseHandle(file);return ok;
}

static bool pathsAndSlot(){
    if(cfg.slot>=50 || cfg.slot==34)return reject(30);
    if(cfg.intentPath[511] || cfg.targetPath[511] || !cfg.intentPath[0] || !cfg.targetPath[0])return reject(31);
    if(wcsstr(cfg.intentPath,L"..") || wcsstr(cfg.targetPath,L".."))return reject(31);
    _snprintf_s(basename,sizeof basename,_TRUNCATE,"svdexSC%02u.s14",cfg.slot);
#ifndef SAVE_CHECKPOINT_FIXTURE
    wchar_t wanted[512]{};
    _snwprintf_s(wanted,512,_TRUNCATE,L"%ls%hs",REMOTE_ROOT,basename);
    if(wcscmp(wanted,cfg.targetPath) || wcsncmp(cfg.intentPath,WORK_ROOT,wcslen(WORK_ROOT)))return reject(31);
    // No separators after the fixed workspace filename prefix.
    const wchar_t* suffix=cfg.intentPath+wcslen(WORK_ROOT);
    if(!*suffix || wcschr(suffix,L'\\') || wcschr(suffix,L'/') || wcschr(suffix,L':'))return reject(31);
#endif
    if(GetFileAttributesW(cfg.targetPath)!=INVALID_FILE_ATTRIBUTES)return reject(32);
    if(GetLastError()!=ERROR_FILE_NOT_FOUND)return reject(33); // Missing directory/access errors are not empty slots.
    return true;
}

static bool stringsIdle(){
    auto name=reinterpret_cast<const SaveShortString*>(base+0x201ED18);
    auto caption=reinterpret_cast<const SaveShortString*>(base+0x201ED38);
    return at<int32_t>(base+0x201ED10)==-1 && name->size==0 && caption->size==0 &&
        name->capacity==15 && caption->capacity==15 && !name->data[0] && !caption->data[0];
}

static bool guard(void* self){
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    auto manager=base+MANAGER;
    if(at<uint64_t>(manager+0x10)!=5 || at<uint64_t>(manager+0x30)!=0)return reject(10);
    auto stack=at<uintptr_t>(manager+0x20);
    if(!stack || at<uintptr_t>(stack+32)!=uintptr_t(self) || at<uintptr_t>(uintptr_t(self))!=base+USER_VT ||
       at<uint32_t>(uintptr_t(self)+0x470)!=2 || !at<uintptr_t>(uintptr_t(self)+0x478) ||
       !at<uintptr_t>(uintptr_t(self)+0x618))return reject(11);
    for(unsigned i=0;i<5;++i){
        auto state=at<uintptr_t>(stack+i*8);
        if(!state || memcmp(reinterpret_cast<void*>(state+0x70),names[i],strlen(names[i])+1))return reject(12);
    }
    if(!at<uintptr_t>(manager) || !at<uintptr_t>(manager+0x28) || !at<uintptr_t>(manager+0x40) ||
       at<uint64_t>(manager+0x38)<1 || at<uint64_t>(manager+0x38)>4096)return reject(13);
    auto root=at<uintptr_t>(base+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);
    if(at<uintptr_t>(root)!=base+0x12AA6B0 || at<uintptr_t>(world)!=base+0x12AA638)return reject(14);
    if(at<uint16_t>(world+0x34)!=203 || at<uint8_t>(world+0x36)!=8 || at<uint8_t>(world+0x37)!=11 ||
       at<uint8_t>(world+0x3A)!=12 || (at<uint32_t>(world+0x16A8)&0x100))return reject(15);
    auto force=at<uintptr_t>(root+0xDCA0+12*8),person=at<uintptr_t>(root+0x148+666*8);
    auto city=at<uintptr_t>(root+0xDAA8+19*8),district=at<uintptr_t>(root+0xDE40+11*8);
    if(at<uint16_t>(force+0x10)!=666 || at<uint16_t>(person+0x10)!=666 || at<uint8_t>(person+0x118)!=11 ||
       at<uint16_t>(person+0x11A)!=19 || at<uint16_t>(city+0x10)!=19 || at<uint8_t>(city+0x30)!=11 ||
       at<uint32_t>(city+0x3C)!=15204 || at<uint8_t>(district+0x10)!=12 || at<uint8_t>(district+0x14)!=18)return reject(16);
    unsigned active=0;
    for(unsigned i=1;i<=500;++i){
        auto army=at<uintptr_t>(root+0x7DF60+i*8);
        if(at<uint8_t>(army+0x10) && at<uint16_t>(army+0x12)){
            ++active;if(at<uint16_t>(army+0x12)==666)return reject(17);
        }
    }
    if(active!=56 || !stringsIdle())return reject(18);
    return pathsAndSlot();
}

struct DurableIntent {
    uint64_t magic;uint32_t version,pid,thread,slot;
    uint32_t year,month,day,force,ruler;char filename[16];
};
static bool reserveIntent(){
    DurableIntent data{SAVE_CONFIG_MAGIC,1,GetCurrentProcessId(),GetCurrentThreadId(),cfg.slot,203,8,11,12,666,{}};
    memcpy(data.filename,basename,strlen(basename)+1);
    HANDLE file=CreateFileW(cfg.intentPath,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return reject(41);
    SaveCheckpointReport.intentCreated=1;
    DWORD written=0;BOOL wrote=WriteFile(file,&data,sizeof data,&written,nullptr);
    BOOL flushed=FlushFileBuffers(file);CloseHandle(file);
    SaveCheckpointReport.intentFlushed=wrote && written==sizeof data && flushed;
    return SaveCheckpointReport.intentFlushed!=0 || reject(42);
}

static bool remoteSlotVacant(){
    // Exact native 836F76..836F90 sequence: ContextInit(&token), *result,
    // then SteamRemoteStorage v014 vtable+68 FileExists(filename).
    // 2FCB90 is this token's native callback selecting interface v014.
    if(at<uintptr_t>(base+0x18D08B8)!=base+0x2FCB90)return reject(46);
    using ContextInit=void*(__cdecl*)(void*);
    using FileExists=bool(__fastcall*)(void*,const char*);
    auto initialize=reinterpret_cast<ContextInit>(at<uintptr_t>(base+0x123CB28));
    if(!initialize)return reject(46);
    SaveCheckpointReport.storageContextCalls++;
    void* result=initialize(reinterpret_cast<void*>(base+0x18D08B8));
    if(!result)return reject(46);
    auto storage=at<uintptr_t>(uintptr_t(result));
    if(!storage || !at<uintptr_t>(storage))return reject(46);
    auto exists=reinterpret_cast<FileExists>(at<uintptr_t>(at<uintptr_t>(storage)+0x68));
    if(!exists)return reject(46);
    SaveCheckpointReport.fileExistsCalls++;
    bool present=exists(reinterpret_cast<void*>(storage),basename);
    SaveCheckpointReport.remoteSlotAbsent=present?0:1;
    return !present || reject(47);
}

static bool queueOnce(void* self){
    // The immutable intent survives exceptions, process exit and ambiguous completion.
    if(!reserveIntent() || !guard(self) || !remoteSlotVacant() || !guard(self))return false;
    SaveRequest request{};request.slot=int32_t(cfg.slot);
    request.filename.capacity=request.caption.capacity=15;
    request.filename.size=strlen(basename);memcpy(request.filename.data,basename,request.filename.size+1);
    SaveCheckpointReport.binderCalls++;
    bindRequest(&request);SaveCheckpointReport.binderReturned=1;
    SaveCheckpointReport.sourceStringsConsumed=request.filename.size==0 && request.caption.size==0;
    auto global=reinterpret_cast<const SaveShortString*>(base+0x201ED18);
    auto caption=reinterpret_cast<const SaveShortString*>(base+0x201ED38);
    SaveCheckpointReport.requestGlobalsMatched=at<uint32_t>(base+0x201ED10)==cfg.slot && global->capacity==15 &&
        global->size==strlen(basename) && !memcmp(global->data,basename,global->size+1) && caption->size==0;
    if(!SaveCheckpointReport.sourceStringsConsumed || !SaveCheckpointReport.requestGlobalsMatched)return reject(43);
    const auto manager=base+MANAGER;
    SaveCheckpointReport.queueBefore=at<uint64_t>(manager+0x30);
    if(SaveCheckpointReport.queueBefore!=0)return reject(44);
    SaveCheckpointReport.queueCalls++;
    queueSave(reinterpret_cast<void*>(manager),reinterpret_cast<const char*>(base+0x12AA8E0),0);
    SaveCheckpointReport.queueReturned=1;SaveCheckpointReport.queueAfter=at<uint64_t>(manager+0x30);
    auto queue=at<uintptr_t>(manager+0x40),state=at<uintptr_t>(queue+8);
    SaveCheckpointReport.queuedState=state;
    SaveCheckpointReport.queueItemVerified=SaveCheckpointReport.queueAfter==1 && at<uint32_t>(queue)==2 && state &&
        at<uintptr_t>(state)==base+0x12DC5F8 && at<uint32_t>(state+0x470)==0 &&
        !memcmp(reinterpret_cast<void*>(state+0x70),"CSaveState",11);
    return SaveCheckpointReport.queueItemVerified!=0 || reject(45);
}

static bool restoreSlot(){
    DWORD temporary=0,ignored=0;
    if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&temporary))return reject(20);
    void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(SaveCheckpointReport.hook));
    SaveCheckpointReport.slotRestored=previous==reinterpret_cast<void*>(SaveCheckpointReport.hook)||previous==reinterpret_cast<void*>(originalUpdate);
    SaveCheckpointReport.protectionRestored=VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)!=0;
    return SaveCheckpointReport.slotRestored && SaveCheckpointReport.protectionRestored;
}

static void __fastcall updateHook(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4){
    InterlockedIncrement(&SaveCheckpointReport.activeCallbacks);
    bool winner=InterlockedCompareExchange(&claimed,1,0)==0;
    if(winner){SaveCheckpointReport.status=2;SaveCheckpointReport.executorThread=GetCurrentThreadId();
        SaveCheckpointReport.caller=reinterpret_cast<uintptr_t>(_ReturnAddress());SaveCheckpointReport.state=uintptr_t(self);}
    bool restored=!winner||restoreSlot();
    __try{
        originalUpdate(self,a2,a3,a4);InterlockedIncrement(reinterpret_cast<volatile LONG*>(&SaveCheckpointReport.originalCalls));
        if(winner){
            __try{
#ifndef SAVE_CHECKPOINT_FIXTURE
                if(SaveCheckpointReport.caller!=base+0x50B785){reject(21);restored=false;}
#endif
                if(!restored||!guard(self))SaveCheckpointReport.status=5;
                else if(!cfg.execute){SaveCheckpointReport.dryStorageQuery=1;SaveCheckpointReport.status=remoteSlotVacant()&&guard(self)?3:5;}
                else SaveCheckpointReport.status=queueOnce(self)?4:5;
            }__except(EXCEPTION_EXECUTE_HANDLER){SaveCheckpointReport.exceptionCode=GetExceptionCode();SaveCheckpointReport.status=6;}
        }
    }__finally{InterlockedDecrement(&SaveCheckpointReport.activeCallbacks);}
}

extern "C" __declspec(dllexport) DWORD WINAPI InstallSaveCheckpoint(void* input){
#ifndef SAVE_CHECKPOINT_FIXTURE
    // RETIRED: queue412520/type2 replaces the current state. It is not a
    // save-and-return entry when called from CUserStrategyState. No live retry.
    (void)input;return 9001;
#endif
    if(InterlockedCompareExchange(&installed,1,0)!=0)return 1001;
    SaveCheckpointReport.installerThread=GetCurrentThreadId();
    __try{
        cfg=*reinterpret_cast<const SaveCheckpointConfig*>(input);
        if(cfg.magic!=SAVE_CONFIG_MAGIC||cfg.version!=1||cfg.execute>1||cfg.reservedMustBeZero){reject(50);SaveCheckpointReport.status=5;return 50;}
#ifdef SAVE_CHECKPOINT_FIXTURE
        base=cfg.testBase;bindRequest=reinterpret_cast<SaveBinder>(cfg.testBinder);queueSave=reinterpret_cast<SaveQueue>(cfg.testQueue);
#else
        wchar_t path[32768]{};
        if(!GetModuleFileNameW(nullptr,path,32768)||!hashFile(path,SAVE_EXE_SHA)){reject(51);SaveCheckpointReport.status=5;return 51;}
        base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        for(const auto& anchor:SAVE_FINGERPRINTS)
            if(memcmp(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size)){reject(52);SaveCheckpointReport.status=5;return 52;}
        bindRequest=reinterpret_cast<SaveBinder>(base+0x2FC750);queueSave=reinterpret_cast<SaveQueue>(base+0x412520);
#endif
        SaveCheckpointReport.base=base;
        hookSlot=reinterpret_cast<void* volatile*>(base+USER_VT+0x28);originalUpdate=reinterpret_cast<SaveUpdate>(*hookSlot);
#ifndef SAVE_CHECKPOINT_FIXTURE
        if(uintptr_t(originalUpdate)!=base+USER_UPDATE){reject(53);SaveCheckpointReport.status=5;return 53;}
#endif
        auto stack=at<uintptr_t>(base+MANAGER+0x20);
        if(!stack||!guard(reinterpret_cast<void*>(at<uintptr_t>(stack+32)))){SaveCheckpointReport.status=5;return SaveCheckpointReport.error;}
        SaveCheckpointReport.slot=uintptr_t(hookSlot);SaveCheckpointReport.original=uintptr_t(originalUpdate);SaveCheckpointReport.hook=uintptr_t(&updateHook);
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&initialProtection)){reject(54);SaveCheckpointReport.status=5;return 54;}
        SaveCheckpointReport.accepted=1;SaveCheckpointReport.status=1;
        void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(&updateHook),reinterpret_cast<void*>(originalUpdate));
        DWORD ignored=0;
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)){
            InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(&updateHook));
            reject(55);SaveCheckpointReport.status=5;return 55;
        }
        if(previous!=reinterpret_cast<void*>(originalUpdate)){reject(56);SaveCheckpointReport.status=5;return 56;}
        return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){SaveCheckpointReport.exceptionCode=GetExceptionCode();SaveCheckpointReport.status=6;return 1002;}
}
extern "C" __declspec(dllexport) DWORD WINAPI CancelSaveCheckpoint(void*){
    if(InterlockedCompareExchange(&claimed,2,0)!=0)return 1;
    if(!hookSlot||!SaveCheckpointReport.accepted)return 2;
    if(!restoreSlot()){SaveCheckpointReport.status=5;return 3;}
    SaveCheckpointReport.status=7;return 0;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
