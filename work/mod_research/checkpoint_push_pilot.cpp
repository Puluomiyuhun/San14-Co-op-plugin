#include "checkpoint_push_pilot.h"
#include "checkpoint_push_bridge.h"
#include <intrin.h>
#include <cstring>
#include <cwchar>
#include <cstdio>
#include <initializer_list>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#ifndef CHECKPOINT_PUSH_FIXTURE
#include "checkpoint_push_profile.h"
#endif

extern "C" __declspec(dllexport) CheckpointPushReportData CheckpointPushReport={SAVE_REPORT_MAGIC,2};
static CheckpointPushConfig cfg{};
static volatile LONG installed=0,claimed=0;
static uintptr_t base=0;
static void* volatile* hookSlot=nullptr;
static SaveUpdate originalUpdate=nullptr;
static SaveBinder bindRequest=nullptr;
static SaveQueue queueSave=nullptr;
static DWORD initialProtection=0;
static char basename[16]="mppush01.s14";
static void* volatile* saveSlot=nullptr;
static SaveUpdate originalSave=nullptr;
static DWORD saveProtection=0;
static volatile LONG saveInstalled=0;
static constexpr uintptr_t USER_VT=0x12CC4A8,USER_UPDATE=0x3F9B00,MANAGER=0x19E7310;
static constexpr wchar_t REMOTE_ROOT[]=L"C:\\Program Files (x86)\\Steam\\userdata\\391007908\\872410\\remote\\";
static constexpr wchar_t WORK_ROOT[]=L"C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\checkpoint_push_";
static uintptr_t pinnedStates[5]{};
static uintptr_t pinnedRoot=0,pinnedWorld=0;
static uintptr_t pinnedCache=0,pinnedCacheSlots[120]{};
static bool restoreSlot();
static bool guard(void* self,bool returned=false);
template<class T> static T at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static bool reject(LONG code){if(!CheckpointPushReport.error)CheckpointPushReport.error=code;return false;}
static bool stringsIdle();
static bool cacheCleared(){
    auto cache=at<uintptr_t>(base+0x2025318),head=at<uintptr_t>(cache+0x10);
    if(!head||at<uintptr_t>(head)!=head||at<uintptr_t>(head+8)!=head||at<uint64_t>(cache+0x18)||
       at<int32_t>(cache+0x3EC)!=-1)return false;
    for(unsigned i=0;i<120;++i)if(at<uintptr_t>(cache+0x20+i*8))return false;
    return true;
}
static bool stringEquals(const SaveShortString* value,const char* expected){
    // Native 465C10 clears length and data[0], retaining heap storage/capacity.
    // Binder 510A0 can reuse that capacity even for this short new filename.
    __try{
        const uint64_t size=value->size,capacity=value->capacity;
        const size_t length=strlen(expected);
        if(size!=length || size>capacity || (capacity<16 && capacity!=15) || capacity>32768)return false;
        const char* data=capacity>=16?reinterpret_cast<const char*>(at<uintptr_t>(uintptr_t(value))):value->data;
        auto pointer=uintptr_t(data);
        if(pointer<0x10000 || pointer>0x00007FFFFFFFFFFFULL-length || memcmp(data,expected,length+1))return false;
        return value->size==size && value->capacity==capacity &&
            (capacity<16 || at<uintptr_t>(uintptr_t(value))==pointer);
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}

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
    if(cfg.slot!=0xFFFFFFFF)return reject(30); // This profile never selects a user or auto-save slot.
    if(cfg.intentPath[511] || cfg.targetPath[511] || !cfg.intentPath[0] || !cfg.targetPath[0])return reject(31);
    if(wcsstr(cfg.intentPath,L"..") || wcsstr(cfg.targetPath,L".."))return reject(31);
    const wchar_t* last=wcsrchr(cfg.targetPath,L'\\');
    if(!last || wcscmp(last+1,L"mppush01.s14"))return reject(31);
#ifndef CHECKPOINT_PUSH_FIXTURE
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

static bool restoreSaveSlot(){
    if(!saveSlot || !InterlockedCompareExchange(&saveInstalled,0,0))return true;
    DWORD temporary=0,ignored=0;
    if(!VirtualProtect(const_cast<void**>(saveSlot),8,PAGE_READWRITE,&temporary))return false;
    void* previous=InterlockedCompareExchangePointer(saveSlot,reinterpret_cast<void*>(originalSave),reinterpret_cast<void*>(CheckpointPushReport.saveHook));
    CheckpointPushReport.saveSlotRestored=previous==reinterpret_cast<void*>(CheckpointPushReport.saveHook)||previous==reinterpret_cast<void*>(originalSave);
    CheckpointPushReport.saveProtectionRestored=VirtualProtect(const_cast<void**>(saveSlot),8,saveProtection,&ignored)!=0;
    if(CheckpointPushReport.saveSlotRestored&&CheckpointPushReport.saveProtectionRestored){InterlockedExchange(&saveInstalled,0);return true;}
    return false;
}

static bool boundSaveRequest(){
    auto name=reinterpret_cast<const SaveShortString*>(base+0x201ED18);
    auto caption=reinterpret_cast<const SaveShortString*>(base+0x201ED38);
    return at<int32_t>(base+0x201ED10)==-1 && stringEquals(name,basename) && stringEquals(caption,"");
}

#include "checkpoint_push_save_callbacks.inc"

static bool installSaveObserver(){
    saveSlot=reinterpret_cast<void* volatile*>(base+0x12DC5F8+0x28);
    originalSave=reinterpret_cast<SaveUpdate>(*saveSlot);
#ifndef CHECKPOINT_PUSH_FIXTURE
    if(uintptr_t(originalSave)!=base+0x4AA650)return reject(65);
#endif
    CheckpointPushBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(originalSave);
    bridge.before=&saveBefore;bridge.after=&saveAfter;
    if(!CheckpointPushBridgeConfigure(1,&bridge))return reject(69);
    CheckpointPushReport.saveSlot=uintptr_t(saveSlot);CheckpointPushReport.saveOriginal=uintptr_t(originalSave);
    CheckpointPushReport.saveHook=uintptr_t(&CheckpointPushBridge1);
    if(!VirtualProtect(const_cast<void**>(saveSlot),8,PAGE_READWRITE,&saveProtection))return reject(66);
    void* previous=InterlockedCompareExchangePointer(saveSlot,reinterpret_cast<void*>(&CheckpointPushBridge1),reinterpret_cast<void*>(originalSave));
    DWORD ignored=0;bool protectedAgain=VirtualProtect(const_cast<void**>(saveSlot),8,saveProtection,&ignored)!=0;
    if(previous==reinterpret_cast<void*>(originalSave))InterlockedExchange(&saveInstalled,1);
    if(previous!=reinterpret_cast<void*>(originalSave)||!protectedAgain){restoreSaveSlot();return reject(67);}
    return true;
}

static bool stringsIdle(){
    auto name=reinterpret_cast<const SaveShortString*>(base+0x201ED18);
    auto caption=reinterpret_cast<const SaveShortString*>(base+0x201ED38);
    return at<int32_t>(base+0x201ED10)==-1 && stringEquals(name,"") && stringEquals(caption,"");
}

static bool pendingVectorReady(uintptr_t manager){
    auto count=at<uint64_t>(manager+0x30),capacity=at<uint64_t>(manager+0x38),data=at<uintptr_t>(manager+0x40);
    if(count || capacity>4096 || ((capacity==0)!=(data==0)))return false;
    if(data && (data<0x10000 || data>0x00007FFFFFFFFFFFULL-capacity*16))return false;
    const uintptr_t offsets[2]={0,0x28};
    for(auto offset:offsets){
        auto allocator=at<uintptr_t>(manager+offset);
        if(allocator<0x10000 || allocator>0x00007FFFFFFFFFF7ULL || at<uintptr_t>(allocator)!=base+0x1283498)return false;
    }
    auto vtable=base+0x1283498;
    return at<uintptr_t>(vtable+0x28)==base+0x12C840 && at<uintptr_t>(vtable+0x38)==base+0x12C290 &&
        at<uintptr_t>(vtable+0x40)==base+0x8388D0 && at<uintptr_t>(vtable+0x48)==base+0x1479B0;
}

static bool guard(void* self,bool returned){
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    auto manager=base+MANAGER;
    if(at<uint64_t>(manager+0x10)!=5 || at<uint64_t>(manager+0x30)!=0)return reject(10);
    auto stack=at<uintptr_t>(manager+0x20);
    if(!stack || at<uintptr_t>(stack+32)!=uintptr_t(self) || at<uintptr_t>(uintptr_t(self))!=base+USER_VT ||
       at<uint32_t>(uintptr_t(self)+0x470)!=2 || !at<uintptr_t>(uintptr_t(self)+0x478) ||
       !at<uintptr_t>(uintptr_t(self)+0x618))return reject(11);
    for(unsigned i=0;i<5;++i){
        auto state=at<uintptr_t>(stack+i*8);
        if(!state || state!=pinnedStates[i] || memcmp(reinterpret_cast<void*>(state+0x70),names[i],strlen(names[i])+1))return reject(12);
    }
    auto toolbar=at<uintptr_t>(uintptr_t(self)+0x478),panel=at<uintptr_t>(pinnedStates[2]+0x480);
    if(!toolbar||!panel||at<int32_t>(toolbar+0x88)!=-1||at<uint32_t>(pinnedStates[2]+0x47C)||
       at<uint32_t>(panel+0x1B0))return reject(70);
    for(auto offset:{0x4a8,0x4b0,0x4b8})if(at<uintptr_t>(uintptr_t(self)+offset))return reject(71);
    auto special=at<uintptr_t>(base+0x201EC70);
    if((special&&at<uint32_t>(special))||at<uint32_t>(base+0x1A38EC8+0x28)||
       at<uint32_t>(base+0x19E7510+0x13C)!=1)return reject(72);
    if(!pendingVectorReady(manager))return reject(13);
    auto root=at<uintptr_t>(base+0x1FCA1E0),world=at<uintptr_t>(root+0x85130);
    if(root!=pinnedRoot||world!=pinnedWorld||at<DWORD>(base+0x18EB8B0)!=CheckpointPushReport.beforeRng)return reject(73);
    if(at<uintptr_t>(root)!=base+0x12AA6B0 || at<uintptr_t>(world)!=base+0x12AA638)return reject(14);
    if(at<uint16_t>(world+0x34)!=203 || at<uint8_t>(world+0x36)!=8 || at<uint8_t>(world+0x37)!=11 ||
       at<uint8_t>(world+0x3A)!=12 || at<uint32_t>(world+0x40)!=1 || (at<uint32_t>(world+0x16A8)&0x100))return reject(15);
    auto cache=at<uintptr_t>(base+0x2025318);
    if(cache!=pinnedCache)return reject(78);
    if(!cache || (at<uint32_t>(cache+8)>1) || at<int32_t>(cache+0x3EC)!=-1 ||
       at<uint32_t>(cache+0x3F0)!=0 || at<uint64_t>(cache+0x18)!=0)return reject(19);
    if(at<uint32_t>(cache+8)!=CheckpointPushReport.cacheModeBefore)return reject(74);
    auto head=at<uintptr_t>(cache+0x10);
    if(!head||at<uintptr_t>(head)!=head||at<uintptr_t>(head+8)!=head)return reject(77);
    // Normal SaveLoad cancellation leaves its first50 menu entries while the
    // owned list is empty. Native clear zeroes these slots without dereferencing
    // them. This fixed profile permits exactly that observed shape or all-zero.
    unsigned entries=0;
    for(unsigned i=0;i<120;++i)if(at<uintptr_t>(cache+0x20+i*8)){if(i>=50)return reject(77);++entries;}
    if(entries!=0&&entries!=50)return reject(77);
    if(entries==50){
        auto first=at<uintptr_t>(cache+0x20);
        if(CheckpointPushReport.cacheModeBefore!=1||first<0x10000||first>0x00007FFFFFFFFFFFULL-50*0x1e0)return reject(77);
        for(unsigned i=0;i<50;++i)if(at<uintptr_t>(cache+0x20+i*8)!=first+i*0x1e0)return reject(77);
    }
    if(!returned)for(unsigned i=0;i<120;++i)if(at<uintptr_t>(cache+0x20+i*8)!=pinnedCacheSlots[i])return reject(78);
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
    return returned || pathsAndSlot();
}

struct DurableIntent {
    uint64_t magic;uint32_t version,pid,thread,slot;
    uint32_t year,month,day,force,ruler;char filename[16];
};
static bool reserveIntent(){
    DurableIntent data{SAVE_CONFIG_MAGIC,2,GetCurrentProcessId(),GetCurrentThreadId(),cfg.slot,203,8,11,12,666,{}};
    memcpy(data.filename,basename,strlen(basename)+1);
    HANDLE file=CreateFileW(cfg.intentPath,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return reject(41);
    CheckpointPushReport.intentCreated=1;
    DWORD written=0;BOOL wrote=WriteFile(file,&data,sizeof data,&written,nullptr);
    BOOL flushed=FlushFileBuffers(file);CloseHandle(file);
    CheckpointPushReport.intentFlushed=wrote && written==sizeof data && flushed;
    return CheckpointPushReport.intentFlushed!=0 || reject(42);
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
    CheckpointPushReport.storageContextCalls++;
    void* result=initialize(reinterpret_cast<void*>(base+0x18D08B8));
    if(!result)return reject(46);
    auto storage=at<uintptr_t>(uintptr_t(result));
    if(!storage || !at<uintptr_t>(storage))return reject(46);
    auto exists=reinterpret_cast<FileExists>(at<uintptr_t>(at<uintptr_t>(storage)+0x68));
    if(!exists)return reject(46);
    CheckpointPushReport.fileExistsCalls++;
    bool present=exists(reinterpret_cast<void*>(storage),basename);
    CheckpointPushReport.remoteSlotAbsent=present?0:1;
    return !present || reject(47);
}

static bool queueOnce(void* self){
    // The immutable intent survives exceptions, process exit and ambiguous completion.
    // Atomic boundary: Stop may cancel claims 0/1; claim3 is committed and is
    // never described as cancelled, even if observers are subsequently removed.
    if(CheckpointPushReport.stopRequested||InterlockedCompareExchange(&claimed,3,1)!=1)return reject(76);
    if(!reserveIntent() || !guard(self) || !remoteSlotVacant() || !guard(self) || !installSaveObserver())return false;
    SaveRequest request{};request.slot=int32_t(cfg.slot);
    request.filename.capacity=request.caption.capacity=15;
    request.filename.size=strlen(basename);memcpy(request.filename.data,basename,request.filename.size+1);
    CheckpointPushReport.binderCalls++;
    bindRequest(&request);CheckpointPushReport.binderReturned=1;
    CheckpointPushReport.sourceStringsConsumed=stringEquals(&request.filename,"") && stringEquals(&request.caption,"");
    CheckpointPushReport.requestGlobalsMatched=boundSaveRequest();
    if(!CheckpointPushReport.sourceStringsConsumed || !CheckpointPushReport.requestGlobalsMatched)return reject(43);
    const auto manager=base+MANAGER;
    CheckpointPushReport.queueBefore=at<uint64_t>(manager+0x30);
    if(CheckpointPushReport.queueBefore!=0)return reject(44);
    CheckpointPushReport.queueCalls++;
    alignas(16) unsigned char emptyCallback[64]{};
    queueSave(reinterpret_cast<void*>(manager),reinterpret_cast<const char*>(base+0x12AA8E0),0,emptyCallback);
    CheckpointPushReport.queueReturned=1;CheckpointPushReport.queueAfter=at<uint64_t>(manager+0x30);
    CheckpointPushReport.queuedAt=GetTickCount64();
    auto queue=at<uintptr_t>(manager+0x40),state=at<uintptr_t>(queue+8);
    CheckpointPushReport.queuedState=state;
    CheckpointPushReport.queueItemVerified=CheckpointPushReport.queueAfter==1 && at<uint32_t>(queue)==0 && state &&
        at<uintptr_t>(state)==base+0x12DC5F8 && at<uint32_t>(state+0x470)==0 &&
        !memcmp(reinterpret_cast<void*>(state+0x70),"CSaveState",11);
    return CheckpointPushReport.queueItemVerified!=0 || reject(45);
}

static bool restoreSlot(){
    if(!hookSlot||!CheckpointPushReport.accepted)return true;
    DWORD temporary=0,ignored=0;
    if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&temporary))return reject(20);
    void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(CheckpointPushReport.hook));
    CheckpointPushReport.slotRestored=previous==reinterpret_cast<void*>(CheckpointPushReport.hook)||previous==reinterpret_cast<void*>(originalUpdate);
    CheckpointPushReport.protectionRestored=VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)!=0;
    return CheckpointPushReport.slotRestored && CheckpointPushReport.protectionRestored;
}

#include "checkpoint_push_user_callbacks.inc"

extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointPush(void* input){
    // Distinct candidate: 2DF990/type0. Old private_checkpoint_save stays retired.
    if(InterlockedCompareExchange(&installed,1,0)!=0)return 1001;
    CheckpointPushReport.installerThread=GetCurrentThreadId();
    __try{
        cfg=*reinterpret_cast<const CheckpointPushConfig*>(input);
        if(cfg.magic!=SAVE_CONFIG_MAGIC||cfg.version!=2||cfg.execute>1||cfg.reservedMustBeZero){reject(50);CheckpointPushReport.status=5;return 50;}
#ifdef CHECKPOINT_PUSH_FIXTURE
        base=cfg.testBase;bindRequest=reinterpret_cast<SaveBinder>(cfg.testBinder);queueSave=reinterpret_cast<SaveQueue>(cfg.testQueue);
#else
        wchar_t path[32768]{};
        if(!GetModuleFileNameW(nullptr,path,32768)||!hashFile(path,SAVE_EXE_SHA)){reject(51);CheckpointPushReport.status=5;return 51;}
        base=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        for(const auto& anchor:SAVE_FINGERPRINTS)
            if(memcmp(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size)){reject(52);CheckpointPushReport.status=5;return 52;}
        bindRequest=reinterpret_cast<SaveBinder>(base+0x2FC750);queueSave=reinterpret_cast<SaveQueue>(base+0x2DF990);
#endif
        CheckpointPushReport.base=base;
        hookSlot=reinterpret_cast<void* volatile*>(base+USER_VT+0x28);originalUpdate=reinterpret_cast<SaveUpdate>(*hookSlot);
#ifndef CHECKPOINT_PUSH_FIXTURE
        if(uintptr_t(originalUpdate)!=base+USER_UPDATE){reject(53);CheckpointPushReport.status=5;return 53;}
        if(at<uintptr_t>(base+0x12DC5F8+0x28)!=base+0x4AA650){reject(65);CheckpointPushReport.status=5;return 65;}
#endif
        auto stack=at<uintptr_t>(base+MANAGER+0x20);
        if(!stack || at<uint64_t>(base+MANAGER+0x10)!=5)return 10;
        for(unsigned i=0;i<5;++i)pinnedStates[i]=at<uintptr_t>(stack+i*8);
        pinnedRoot=at<uintptr_t>(base+0x1FCA1E0);pinnedWorld=at<uintptr_t>(pinnedRoot+0x85130);
        CheckpointPushReport.pinnedUser=pinnedStates[4];CheckpointPushReport.pinnedGame=pinnedStates[2];
        CheckpointPushReport.pinnedWorld=pinnedWorld;
        CheckpointPushReport.beforeRng=at<DWORD>(base+0x18EB8B0);
        pinnedCache=at<uintptr_t>(base+0x2025318);
        CheckpointPushReport.cacheModeBefore=at<DWORD>(pinnedCache+8);
        for(unsigned i=0;i<120;++i)pinnedCacheSlots[i]=at<uintptr_t>(pinnedCache+0x20+i*8);
        if(!stack||!guard(reinterpret_cast<void*>(at<uintptr_t>(stack+32)))){CheckpointPushReport.status=5;return CheckpointPushReport.error;}
        CheckpointPushBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(originalUpdate);
        bridge.before=&userBefore;bridge.after=&userAfter;
        if(!CheckpointPushBridgeConfigure(0,&bridge)){reject(75);CheckpointPushReport.status=5;return 75;}
        CheckpointPushReport.slot=uintptr_t(hookSlot);CheckpointPushReport.original=uintptr_t(originalUpdate);CheckpointPushReport.hook=uintptr_t(&CheckpointPushBridge0);
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&initialProtection)){reject(54);CheckpointPushReport.status=5;return 54;}
        CheckpointPushReport.accepted=1;CheckpointPushReport.status=1;
        void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(&CheckpointPushBridge0),reinterpret_cast<void*>(originalUpdate));
        DWORD ignored=0;
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)){
            InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(&CheckpointPushBridge0));
            reject(55);CheckpointPushReport.status=5;return 55;
        }
        if(previous!=reinterpret_cast<void*>(originalUpdate)){reject(56);CheckpointPushReport.status=5;return 56;}
        return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){CheckpointPushReport.exceptionCode=GetExceptionCode();CheckpointPushReport.status=6;restoreSaveSlot();restoreSlot();return 1002;}
}
extern "C" __declspec(dllexport) DWORD WINAPI CancelCheckpointPush(void*){
    if(InterlockedCompareExchange(&claimed,2,0)!=0)return 1;
    if(!hookSlot||!CheckpointPushReport.accepted)return 2;
    if(!restoreSlot()){CheckpointPushReport.status=5;return 3;}
    CheckpointPushReport.status=7;return 0;
}
extern "C" __declspec(dllexport) DWORD WINAPI StopCheckpointPushObserver(void*){
    // This only removes passive observation. It cannot cancel or replay a queued native save.
    InterlockedExchange(reinterpret_cast<volatile LONG*>(&CheckpointPushReport.stopRequested),1);
    LONG was=InterlockedCompareExchange(&claimed,2,0);
    bool cancelled=was==0;
    if(was==1)cancelled=InterlockedCompareExchange(&claimed,2,1)==1;
    if(cancelled)CheckpointPushReport.status=7;
    const bool save=restoreSaveSlot(),user=!hookSlot||restoreSlot();
    return save&&user?0:1;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
