#include "checkpoint_load_mode_pilot.h"
#include <cstring>
#include <cwchar>
#include <initializer_list>
#include <atomic>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
#include "checkpoint_load_mode_profile.h"
#endif
static CheckpointLoadModeConfig cfg{};
static CheckpointLoadModeReport report{};
static SRWLOCK reportLock=SRWLOCK_INIT;
static volatile LONG installed=0,state=LM_NEW,claim=0,stopped=0,active=0,firstError=0,menuClaim=0;
static uintptr_t base=0;
static std::atomic<DWORD> ownerThread{0};
static std::atomic<DWORD> menuOwnerThread{0},returnOwnerThread{0};
static std::atomic<uint64_t> firstCall{0},returnCall{0},menuCall{0};
static thread_local unsigned depth=0;
using Queue=void(__fastcall*)(void*,const char*,void*,void*);
using Cancel=uint64_t(__fastcall*)(void*);
static Queue nativeQueue=nullptr;
static Cancel nativeCancel=nullptr;
template<class T> static T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static LONG getState(){return InterlockedCompareExchange(&state,0,0);}
static bool isStopped(){return InterlockedCompareExchange(&stopped,0,0)!=0;}
static void error(LONG v){InterlockedCompareExchange(&firstError,v,0);}
static void stage(const char* s){AcquireSRWLockExclusive(&reportLock);strncpy_s(report.stage,s,_TRUNCATE);ReleaseSRWLockExclusive(&reportLock);}
#define REPORT(code) do{AcquireSRWLockExclusive(&reportLock);__try{code;}__finally{ReleaseSRWLockExclusive(&reportLock);}}while(0)
#ifdef CHECKPOINT_LOAD_MODE_FIXTURE
// Exercises the identical production REPORT macro with an exception while its
// lock is owned. No production export, game callback, or memory seam is added.
extern "C" __declspec(dllexport) DWORD WINAPI CheckpointLoadModeFixtureReportFault(void*) {
    DWORD seen=0;
    __try {REPORT(RaiseException(0xE0143005,0,0,nullptr));}
    __except(EXCEPTION_EXECUTE_HANDLER) {seen=GetExceptionCode();}
    REPORT(report.exceptionCode=seen);
    return seen==0xE0143005?0:1;
}
#endif
struct HookSlot {
    SRWLOCK lock=SRWLOCK_INIT;void* volatile* slot=nullptr;void* original=nullptr;void* hook=nullptr;
    DWORD protection=0;bool known=false,dirty=false,published=false;
};
static HookSlot userHook,menuHook;
static LoadModeSlotReport& slotReport(HookSlot& h){return &h==&userHook?report.userSlot:report.menuSlot;}
static bool restore(HookSlot& h){
    if(!h.slot)return true;
    AcquireSRWLockExclusive(&h.lock);bool needed=false,pointer=false,protection=false;DWORD old=0;
    __try {
        __try {needed=h.known&&(h.dirty||h.published);
            if(needed&&VirtualProtect(const_cast<void**>(h.slot),8,PAGE_READWRITE,&old)){
                h.dirty=true;auto previous=InterlockedCompareExchangePointer(h.slot,h.original,h.hook);
                pointer=(previous==h.original||previous==h.hook)&&*h.slot==h.original;
                if(*h.slot!=h.hook)h.published=false;}
        }__except(EXCEPTION_EXECUTE_HANDLER){needed=true;}
        __try {if(needed&&h.known&&h.dirty){protection=VirtualProtect(const_cast<void**>(h.slot),8,h.protection,&old)!=0;if(protection)h.dirty=false;}}
        __except(EXCEPTION_EXECUTE_HANDLER){protection=false;}
    }__finally {ReleaseSRWLockExclusive(&h.lock);}
    if(!needed)return true;
    REPORT(slotReport(h).restored=pointer;slotReport(h).protectionRestored=protection);
    if(!pointer||!protection)error(30);return pointer&&protection;
}
static void fail(LONG code,const char* why,bool uncertain=true){
    error(code);stage(why);InterlockedExchange(&state,uncertain?LM_UNCERTAIN:LM_REJECTED);restore(menuHook);restore(userHook);
}
static bool publish(HookSlot& h){
    AcquireSRWLockExclusive(&h.lock);bool ok=false;DWORD ignored=0;
    __try {
        if(!isStopped()&&VirtualProtect(const_cast<void**>(h.slot),8,PAGE_READWRITE,&h.protection)){
            h.known=true;h.dirty=true;REPORT(slotReport(h).initialProtection=h.protection);
            auto previous=InterlockedCompareExchangePointer(h.slot,h.hook,h.original);
            if(previous==h.original)h.published=true;
            const bool protectedAgain=VirtualProtect(const_cast<void**>(h.slot),8,h.protection,&ignored)!=0;
            if(protectedAgain)h.dirty=false;
            ok=previous==h.original&&protectedAgain;
        }
    }__finally {ReleaseSRWLockExclusive(&h.lock);}
    if(!ok)restore(h);return ok;
}
#include "checkpoint_load_mode_guard.inc"
static bool intentPathOk(){
    if(cfg.intentPath[511]||!cfg.intentPath[0]||wcsstr(cfg.intentPath,L".."))return false;
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
    const wchar_t* prefix=L"C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\checkpoint_load_mode_";
    const size_t length=wcslen(prefix);
    if(wcsncmp(cfg.intentPath,prefix,length))return false;
    auto suffix=cfg.intentPath+length;if(!*suffix||wcschr(suffix,L'\\')||wcschr(suffix,L'/')||wcschr(suffix,L':'))return false;
#endif
    return true;
}
static bool reserveIntent(){
    HANDLE f=CreateFileW(cfg.intentPath,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
    if(f==INVALID_HANDLE_VALUE)return false;REPORT(report.intentCreated=1);
    struct Intent{uint64_t magic,base,user;DWORD version,pid,thread,mode,secondary;};
    Intent data{LOAD_MODE_MAGIC,base,cfg.expectedUser,1,GetCurrentProcessId(),GetCurrentThreadId(),0,0};DWORD written=0;
    bool ok=WriteFile(f,&data,sizeof data,&written,nullptr)&&written==sizeof data&&FlushFileBuffers(f);CloseHandle(f);
    REPORT(report.intentFlushed=ok);return ok;
}
static bool exactPop(){auto m=base+0x19E7310,p=at<uintptr_t>(m+0x40);return at<uint64_t>(m+0x30)==1&&p&&at<DWORD>(p)==1&&at<uintptr_t>(p+8)==0;}
static void queueOnce(){
    if(isStopped()||InterlockedCompareExchange(&claim,2,1)!=1){fail(40,"stopped_before_commit",false);return;}
    if(!reserveIntent()||!modeGuard(cfg.expectedUser,LM_GUARD_INITIAL)||isStopped()){fail(41,"intent_or_guard_failed");return;}
    if(!publish(menuHook)){fail(42,"menu_hook_install_failed");return;}
    if(isStopped()||!modeGuard(cfg.expectedUser,LM_GUARD_INITIAL)){fail(43,"guard_before_queue_failed");return;}
    DWORD mode[2]={0,0};alignas(16) unsigned char callback[64]{};
    auto beforeCount=at<uint64_t>(base+0x19E7310+0x30);
    REPORT(report.queueBefore=beforeCount;++report.queueCalls);
    nativeQueue(reinterpret_cast<void*>(base+0x19E7310),reinterpret_cast<const char*>(base+0x12DD6E0),mode,callback);
    auto count=at<uint64_t>(base+0x19E7310+0x30),p=at<uintptr_t>(base+0x19E7310+0x40);
    auto queued=p?at<uintptr_t>(p+8):0;
    bool ok=count==1&&p&&at<DWORD>(p)==0&&queued&&at<uintptr_t>(queued)==base+0x12DB4C0&&
        !memcmp(reinterpret_cast<void*>(queued+0x70),"CSaveLoadState",15)&&!at<uintptr_t>(queued+0x48)&&
        at<DWORD>(pinned.cache+8)==0&&at<DWORD>(pinned.cache+0x3F0)==0&&at<int32_t>(pinned.cache+0x3EC)==-1;
    REPORT(report.queueReturned=1;report.queueAfter=count;report.queuedState=queued;report.queueVerified=ok);
    if(!ok){fail(44,"native_push_not_verified");return;}
    if(isStopped()){fail(45,"stopped_during_native_push");return;}
    if(InterlockedCompareExchange(&state,LM_QUEUED,LM_CLAIMED)!=LM_CLAIMED){fail(46,"state_changed_during_native_push");return;}
    stage("native_saveload_push_queued");
}
#include "checkpoint_load_mode_callbacks.inc"
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
static bool hashGame(const wchar_t* path,const unsigned char expected[32]){
    HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(f==INVALID_HANDLE_VALUE)return false;BCRYPT_ALG_HANDLE a=nullptr;BCRYPT_HASH_HANDLE h=nullptr;bool ok=false;
    unsigned char buffer[65536],digest[32];DWORD got=0;
    if(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptCreateHash(a,&h,nullptr,0,nullptr,0,0)>=0){
        ok=true;for(;;){if(!ReadFile(f,buffer,sizeof buffer,&got,nullptr)){ok=false;break;}if(!got)break;if(BCryptHashData(h,buffer,got,0)<0){ok=false;break;}}
        if(ok)ok=BCryptFinishHash(h,digest,32,0)>=0&&!memcmp(digest,expected,32);}
    if(h)BCryptDestroyHash(h);if(a)BCryptCloseAlgorithmProvider(a,0);CloseHandle(f);return ok;
}
#endif
extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointLoadMode(void* input){
    if(InterlockedCompareExchange(&installed,1,0))return 1;
    __try {
        cfg=*reinterpret_cast<const CheckpointLoadModeConfig*>(input);
        if(cfg.magic!=LOAD_MODE_MAGIC||cfg.size!=sizeof cfg||cfg.version!=1||cfg.execute>1||cfg.expectedPid!=GetCurrentProcessId()||
           cfg.reserved[0]||cfg.reserved[1]||cfg.reserved[2]||cfg.reserved[3]||!intentPathOk())return 2;
        FILETIME born{},ex{},ke{},us{};
        if(!GetProcessTimes(GetCurrentProcess(),&born,&ex,&ke,&us)||((uint64_t(born.dwHighDateTime)<<32)|born.dwLowDateTime)!=cfg.expectedProcessBirth)return 3;
        base=cfg.expectedBase;if(!base||!cfg.expectedUser)return 4;
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
        wchar_t path[32768]{};
        if(base!=uintptr_t(GetModuleHandleW(nullptr))||!GetModuleFileNameW(nullptr,path,32768)||!hashGame(path,LOAD_MODE_EXE_SHA))return 5;
        for(const auto& a:LOAD_MODE_ANCHORS)if(memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size))return 6;
        nativeQueue=reinterpret_cast<Queue>(base+0x411980);nativeCancel=reinterpret_cast<Cancel>(base+0x4D4AA0);
#else
        nativeQueue=reinterpret_cast<Queue>(cfg.testQueue);nativeCancel=reinterpret_cast<Cancel>(cfg.testCancel);
#endif
        userHook.slot=reinterpret_cast<void* volatile*>(base+0x12CC4A8+0x28);menuHook.slot=reinterpret_cast<void* volatile*>(base+0x12DB4C0+0x28);
        userHook.original=*userHook.slot;menuHook.original=*menuHook.slot;
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
        if(uintptr_t(userHook.original)!=base+0x3F9B00||uintptr_t(menuHook.original)!=base+0x4AA200)return 7;
#endif
        if(!nativeQueue||!nativeCancel||!modeGuard(cfg.expectedUser,LM_GUARD_INITIAL,true))return 8;
        userHook.hook=reinterpret_cast<void*>(&CheckpointPushBridge0);menuHook.hook=reinterpret_cast<void*>(&CheckpointPushBridge1);
        CheckpointPushBridgeConfig b{};b.original=userHook.original;b.before=userBefore;b.after=userAfter;
        if(!CheckpointPushBridgeConfigure(0,&b))return 9;
        b.original=menuHook.original;b.before=menuBefore;b.after=menuAfter;if(!CheckpointPushBridgeConfigure(1,&b))return 10;
        REPORT(report.execute=cfg.execute;report.base=base;report.user=cfg.expectedUser;report.game=pinned.states[2];report.world=pinned.world;report.cache=pinned.cache;
            report.initialRng=pinned.rng;report.initialMode=1;report.installerThread=GetCurrentThreadId();
            report.userSlot.slot=uintptr_t(userHook.slot);report.userSlot.original=uintptr_t(userHook.original);report.userSlot.hook=uintptr_t(userHook.hook);
            report.menuSlot.slot=uintptr_t(menuHook.slot);report.menuSlot.original=uintptr_t(menuHook.original);report.menuSlot.hook=uintptr_t(menuHook.hook));
        if(isStopped()){InterlockedExchange(&state,LM_CANCELLED);return 11;}
        InterlockedExchange(&state,LM_ARMED);stage("armed_user_boundary");
        if(!publish(userHook)){fail(12,"user_hook_publish_failed",false);return 12;}
        if(isStopped()){restore(userHook);return 11;}
        return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){REPORT(report.exceptionCode=GetExceptionCode());fail(13,"install_exception");return 13;}
}
extern "C" __declspec(dllexport) DWORD WINAPI StopCheckpointLoadMode(void*){
    InterlockedExchange(&stopped,1);LONG old=InterlockedCompareExchange(&claim,3,0);
    bool cancelled=old==0||(old==1&&InterlockedCompareExchange(&claim,3,1)==1);
    if(cancelled&&getState()!=LM_DRY_DONE&&getState()!=LM_REJECTED)InterlockedExchange(&state,LM_CANCELLED);
    else if(getState()!=LM_USER_RETURNED&&getState()!=LM_DRY_DONE&&getState()!=LM_REJECTED)InterlockedExchange(&state,LM_UNCERTAIN);
    const bool a=restore(menuHook),b=restore(userHook);return a&&b?0:1;
}
extern "C" __declspec(dllexport) DWORD WINAPI GetCheckpointLoadModeReport(void* dst){
    CheckpointLoadModeReport out;AcquireSRWLockShared(&reportLock);out=report;ReleaseSRWLockShared(&reportLock);
    out.state=getState();out.error=InterlockedCompareExchange(&firstError,0,0);out.stopRequested=isStopped();out.callbackActive=InterlockedCompareExchange(&active,0,0);
    CheckpointPushBridgeSnapshot(0,&out.userBridge);CheckpointPushBridgeSnapshot(1,&out.menuBridge);
    if(out.userBridge.abnormal_exits||out.menuBridge.abnormal_exits){out.state=LM_UNCERTAIN;strncpy_s(out.stage,"native_original_abnormal",_TRUNCATE);}
    __try {
        HookSlot* slots[]={&userHook,&menuHook};LoadModeSlotReport* entries[]={&out.userSlot,&out.menuSlot};
        for(unsigned i=0;i<2;++i)if(slots[i]->slot){entries[i]->observed=uintptr_t(*slots[i]->slot);MEMORY_BASIC_INFORMATION m{};
            if(VirtualQuery(const_cast<void**>(slots[i]->slot),&m,sizeof m)==sizeof m)entries[i]->observedProtection=m.Protect;}
        *reinterpret_cast<CheckpointLoadModeReport*>(dst)=out;return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){return 1;}
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
