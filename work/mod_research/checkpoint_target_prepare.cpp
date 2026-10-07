#include "checkpoint_target_prepare.h"
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
#define NATIVE_FILE_IDENTITY_FIXTURE
#endif
#include "native_file_identity_probe_guard.h"
#include "checkpoint_target_metadata_native.h"
#include "native_storage_read_core.h"
#include <bcrypt.h>
#include <cwchar>
#include <cstring>
#include <atomic>
#pragma comment(lib,"bcrypt.lib")

static TargetPrepareConfig cfg{};
static TargetPrepareReport report{};
static SRWLOCK reportLock=SRWLOCK_INIT,slotLock=SRWLOCK_INIT;
static volatile LONG installed=0,state=FP_NEW,stopped=0,callbacks=0,firstError=0,extraCallbacks=0;
static uintptr_t base=0,user=0,original=0,holder=0,storage=0,vtable=0,contextInit=0;
static void* volatile* slot=nullptr;
static DWORD originalProtection=0;
static std::atomic<DWORD> ownerThread{0};
static std::atomic<uint64_t> ownerCall{0};
static bool protectionKnown=false,pageDirty=false,hookPublished=false;
static ProbeGuardSnapshot pinned{};
static native_storage_read::Api api{};
static thread_local bool inOwnerAfter=false;
static thread_local unsigned callbackDepth=0;
static LONG loadState(){return InterlockedCompareExchange(&state,0,0);}
static void error(LONG code){InterlockedCompareExchange(&firstError,code,0);}
static void stage(const char* text){AcquireSRWLockExclusive(&reportLock);strncpy_s(report.stage,text,_TRUNCATE);ReleaseSRWLockExclusive(&reportLock);}
static bool currentGuard(){
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
    return cfg.testGuard&&cfg.testGuard(cfg.testContext);
#else
    return pinned.cacheMode==0 && probeGuard(base,user,pinned,false);
#endif
}
#ifndef CHECKPOINT_TARGET_PREPARE_FIXTURE
static bool hashPath(const wchar_t* path,const unsigned char expected[32]){
    HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(f==INVALID_HANDLE_VALUE)return false;
    BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE h=nullptr;bool ok=false;
    unsigned char buffer[65536],digest[32];DWORD count=0;
    if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptCreateHash(alg,&h,nullptr,0,nullptr,0,0)>=0){
        ok=true;for(;;){if(!ReadFile(f,buffer,sizeof buffer,&count,nullptr)){ok=false;break;}if(!count)break;
            if(BCryptHashData(h,buffer,count,0)<0){ok=false;break;}}
        if(ok)ok=BCryptFinishHash(h,digest,32,0)>=0&&!memcmp(digest,expected,32);
    }
    if(h)BCryptDestroyHash(h);if(alg)BCryptCloseAlgorithmProvider(alg,0);CloseHandle(f);return ok;
}
#endif
static bool imageMethod(uintptr_t address,bool pin){
    if(!address)return false;
    MEMORY_BASIC_INFORMATION mb{};
    if(VirtualQuery(reinterpret_cast<void*>(address),&mb,sizeof mb)!=sizeof mb||mb.State!=MEM_COMMIT||mb.Type!=MEM_IMAGE||
       (mb.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;
    DWORD p=mb.Protect&0xff;
    if(p!=PAGE_EXECUTE&&p!=PAGE_EXECUTE_READ&&p!=PAGE_EXECUTE_READWRITE&&p!=PAGE_EXECUTE_WRITECOPY)return false;
    HMODULE module=nullptr;
    DWORD flags=GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT;
    if(!GetModuleHandleExW(flags,reinterpret_cast<LPCWSTR>(address),&module)||module!=mb.AllocationBase)return false;
#ifndef CHECKPOINT_TARGET_PREPARE_FIXTURE
    wchar_t path[32768]{};
    if(!GetModuleFileNameW(module,path,32768))return false;
    // Explicit trusted installed-module paths, not arbitrary executable heap.
    const wchar_t* allowed[]={L"C:\\Program Files (x86)\\Steam\\steamclient64.dll",
        L"C:\\Program Files (x86)\\Steam\\steamapps\\common\\Romance_of_the_Three_Kingdoms_14\\steam_api64.dll"};
    if(_wcsicmp(path,allowed[0])&&_wcsicmp(path,allowed[1]))return false;
#endif
    if(pin){HMODULE pinnedModule=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
            reinterpret_cast<LPCWSTR>(address),&pinnedModule)||pinnedModule!=module)return false;}
    return true;
}
static bool restoreSlot(){
    if(!slot)return true;
    AcquireSRWLockExclusive(&slotLock);
    DWORD tmp=0,ignored=0;bool pointerOk=false,protectOk=false,needed=false;
    __try {
        __try {
            needed=protectionKnown&&(hookPublished||pageDirty);
            if(needed&&VirtualProtect(const_cast<void**>(slot),8,PAGE_READWRITE,&tmp)){
                pageDirty=true;
                auto old=InterlockedCompareExchangePointer(slot,reinterpret_cast<void*>(original),reinterpret_cast<void*>(&CheckpointPushBridge0));
                pointerOk=(old==reinterpret_cast<void*>(original)||old==reinterpret_cast<void*>(&CheckpointPushBridge0))&&
                    *slot==reinterpret_cast<void*>(original);
                if(*slot!=reinterpret_cast<void*>(&CheckpointPushBridge0))hookPublished=false;
            }
        }__except(EXCEPTION_EXECUTE_HANDLER){pointerOk=false;needed=true;}
        __try {
            if(needed&&protectionKnown&&pageDirty){
                protectOk=VirtualProtect(const_cast<void**>(slot),8,originalProtection,&ignored)!=0;
                if(protectOk)pageDirty=false;
            }
        }__except(EXCEPTION_EXECUTE_HANDLER){protectOk=false;}
    }__finally {ReleaseSRWLockExclusive(&slotLock);}
    if(!needed)return true; // an early install rejection never touches VT/page
    AcquireSRWLockExclusive(&reportLock);
    report.slotRestored=pointerOk;report.protectionRestored=protectOk;
    ReleaseSRWLockExclusive(&reportLock);
    if(!pointerOk||!protectOk)error(30);
    return pointerOk&&protectOk;
}
static void callbackFault(){
    AcquireSRWLockExclusive(&reportLock);++report.callbackFaults;ReleaseSRWLockExclusive(&reportLock);
    error(33);InterlockedExchange(&state,FP_UNCERTAIN);
}
static void storeException(DWORD code){
    AcquireSRWLockExclusive(&reportLock);report.exceptionCode=code;ReleaseSRWLockExclusive(&reportLock);
}
static bool validateStorage(void*){
    __try {
        if(!inOwnerAfter||GetCurrentThreadId()!=ownerThread||InterlockedCompareExchange(&stopped,0,0)||
           InterlockedCompareExchange(&extraCallbacks,0,0)||loadState()!=FP_READING||!currentGuard())return false;
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
        return cfg.testApi.validate(cfg.testApi.validationContext)&&api.storage==cfg.testApi.storage&&
            api.exists==cfg.testApi.exists&&api.size==cfg.testApi.size&&api.read==cfg.testApi.read;
#else
        if(memcmp(reinterpret_cast<void*>(base+0x12AA6B8),PROBE_STORAGE_VERSION,sizeof PROBE_STORAGE_VERSION)||
           probeAt<uintptr_t>(base+0x18D08B8)!=base+0x2FCB90||probeAt<uintptr_t>(base+0x123CB28)!=contextInit||
           probeAt<uintptr_t>(holder)!=storage||probeAt<uintptr_t>(storage)!=vtable||
           probeAt<uintptr_t>(vtable+0x68)!=uintptr_t(api.exists)||probeAt<uintptr_t>(vtable+0x78)!=uintptr_t(api.size)||
           probeAt<uintptr_t>(vtable+8)!=uintptr_t(api.read))return false;
        return imageMethod(contextInit,false)&&imageMethod(uintptr_t(api.exists),false)&&
            imageMethod(uintptr_t(api.size),false)&&imageMethod(uintptr_t(api.read),false);
#endif
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
static bool acquireStorage(){
    if(InterlockedCompareExchange(&stopped,0,0)||!currentGuard())return false;
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
    api=cfg.testApi;storage=uintptr_t(api.storage);vtable=0;
#else
    if(memcmp(reinterpret_cast<void*>(base+0x12AA6B8),PROBE_STORAGE_VERSION,sizeof PROBE_STORAGE_VERSION)||
       probeAt<uintptr_t>(base+0x18D08B8)!=base+0x2FCB90)return false;
    contextInit=probeAt<uintptr_t>(base+0x123CB28);
    if(!imageMethod(contextInit,true))return false;
    using ContextInit=void*(__cdecl*)(void*);
    AcquireSRWLockExclusive(&reportLock);++report.contextCalls;ReleaseSRWLockExclusive(&reportLock);
    holder=uintptr_t(reinterpret_cast<ContextInit>(contextInit)(reinterpret_cast<void*>(base+0x18D08B8)));
    if(!holder||(storage=probeAt<uintptr_t>(holder))==0||(vtable=probeAt<uintptr_t>(storage))==0)return false;
    api.storage=reinterpret_cast<void*>(storage);
    api.exists=reinterpret_cast<native_storage_read::FileExists>(probeAt<uintptr_t>(vtable+0x68));
    api.size=reinterpret_cast<native_storage_read::GetFileSize>(probeAt<uintptr_t>(vtable+0x78));
    api.read=reinterpret_cast<native_storage_read::FileRead>(probeAt<uintptr_t>(vtable+8));
#endif
    if(!imageMethod(uintptr_t(api.exists),true)||!imageMethod(uintptr_t(api.size),true)||!imageMethod(uintptr_t(api.read),true))return false;
    api.validate=&validateStorage;api.validationContext=nullptr;
    AcquireSRWLockExclusive(&reportLock);
    report.storage=storage;report.storageVtable=vtable;report.existsMethod=uintptr_t(api.exists);
    report.sizeMethod=uintptr_t(api.size);report.readMethod=uintptr_t(api.read);
    ReleaseSRWLockExclusive(&reportLock);
    return validateStorage(nullptr);
}
#include "checkpoint_target_prepare_leaf.inc"
static void doVerify(){
    native_storage_read::Input input{};
    input.localPath=cfg.localPath;input.basename=PROBE_BASENAME;input.expectedSize=report.expectedSize;
    memcpy(input.expectedSha256,report.expectedSha256,32);
    native_storage_read::Evidence evidence{};native_storage_read::Lease lease;
    AcquireSRWLockExclusive(&reportLock);++report.verifyAttempts;ReleaseSRWLockExclusive(&reportLock);
    bool ok=native_storage_read::Verify(input,api,lease,evidence);
    TargetPrepareLeaf leaf{};
    bool prepared=ok && doNativePrepare(lease,leaf);
    {AcquireSRWLockExclusive(&reportLock);report.leaf=leaf;ReleaseSRWLockExclusive(&reportLock);}
    bool releaseOk=true;
    if(lease.file!=INVALID_HANDLE_VALUE){releaseOk=CloseHandle(lease.file)!=0;if(releaseOk)lease.file=INVALID_HANDLE_VALUE;}
    // Identity proof is limited to these two synchronous reads; no pin spans load.
    AcquireSRWLockExclusive(&reportLock);
    report.existsCalls=evidence.existsCalls;report.sizeCalls=evidence.sizeCalls;report.readCalls=evidence.readCalls;
    memcpy(report.sizes,evidence.sizes,sizeof evidence.sizes);memcpy(report.readReturns,evidence.readReturns,sizeof evidence.readReturns);
    memcpy(report.localSha256,evidence.localSha256,32);memcpy(report.nativeSha256,evidence.nativeSha256,64);
    report.exceptionCode=evidence.exceptionCode;report.osError=evidence.osError;
    report.identityMatched=ok;report.verifiedSize=ok?static_cast<uint32_t>(lease.bytes.size()):0;
    report.localPinReleased=releaseOk;strncpy_s(report.stage,evidence.stage,_TRUNCATE);
    ReleaseSRWLockExclusive(&reportLock);
    if(!releaseOk){error(44);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    if(InterlockedCompareExchange(&stopped,0,0)){error(45);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    if(!ok){error(43);InterlockedExchange(&state,FP_REJECTED);return;}
    if(!prepared){error(46);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    if(!currentGuard()){error(47);InterlockedExchange(&state,FP_UNCERTAIN);return;}
    if(InterlockedCompareExchange(&state,FP_MATCHED,FP_READING)!=FP_READING){error(48);InterlockedExchange(&state,FP_UNCERTAIN);return;}
}
static void before(const CheckpointPushFrame* frame,void*) noexcept {
    InterlockedIncrement(&callbacks);++callbackDepth;
    __try {
      __try {
        if(callbackDepth>1||frame->call_id>1){InterlockedIncrement(&extraCallbacks);AcquireSRWLockExclusive(&reportLock);++report.reentrantClaims;ReleaseSRWLockExclusive(&reportLock);}
        if(InterlockedCompareExchange(&state,FP_CLAIMED,FP_ARMED)==FP_ARMED){
            ownerCall=frame->call_id;ownerThread=frame->thread_id;
            auto caller=probeAt<uintptr_t>(frame->caller_entry_rsp);
            AcquireSRWLockExclusive(&reportLock);
            report.claimCallId=ownerCall;report.executorThread=ownerThread;report.caller=caller;
            ReleaseSRWLockExclusive(&reportLock);
            // Restore BEFORE native original: exceptional exits then leave no VT hook.
            if(!restoreSlot()){InterlockedExchange(&state,FP_UNCERTAIN);return;}
            if(frame->args[0]!=user||callbackDepth!=1){error(31);InterlockedExchange(&state,FP_REJECTED);return;}
#ifndef CHECKPOINT_TARGET_PREPARE_FIXTURE
            if(report.caller!=base+0x50B785){error(32);InterlockedExchange(&state,FP_REJECTED);return;}
#endif
        }
      }__except(EXCEPTION_EXECUTE_HANDLER){storeException(GetExceptionCode());callbackFault();restoreSlot();}
    }__finally {--callbackDepth;InterlockedDecrement(&callbacks);}
}
static void after(const CheckpointPushFrame* frame,void*) noexcept {
    InterlockedIncrement(&callbacks);++callbackDepth;
    __try {
        if(frame->call_id==ownerCall&&frame->thread_id==ownerThread){
            AcquireSRWLockExclusive(&reportLock);report.originalReturned=1;report.originalRax=frame->result_rax;ReleaseSRWLockExclusive(&reportLock);
            if(loadState()==FP_CLAIMED){
                if(InterlockedCompareExchange(&extraCallbacks,0,0)||!currentGuard()){error(34);InterlockedExchange(&state,FP_REJECTED);}
                else if(InterlockedCompareExchange(&stopped,0,0))InterlockedExchange(&state,FP_CANCELLED);
                else if(!cfg.mode){stage("dry_guard_only");InterlockedExchange(&state,FP_DRY_DONE);}
                else if(InterlockedCompareExchange(&state,FP_READING,FP_CLAIMED)==FP_CLAIMED){
                    inOwnerAfter=true;
                    if(acquireStorage())doVerify();else {error(40);InterlockedExchange(&state,FP_REJECTED);}
                    inOwnerAfter=false;
                }
            }
        }
    }__except(EXCEPTION_EXECUTE_HANDLER){
        inOwnerAfter=false;AcquireSRWLockExclusive(&reportLock);report.exceptionCode=GetExceptionCode();++report.callbackFaults;ReleaseSRWLockExclusive(&reportLock);
        error(41);InterlockedExchange(&state,FP_UNCERTAIN);
    }
    --callbackDepth;InterlockedDecrement(&callbacks);
}
extern "C" __declspec(dllexport) DWORD WINAPI InstallTargetPrepare(void* argument){
    if(InterlockedCompareExchange(&installed,1,0))return 1;
    __try {
        cfg=*reinterpret_cast<const TargetPrepareConfig*>(argument);
        if(cfg.magic!=FILE_PROBE_MAGIC||cfg.size!=sizeof cfg||cfg.version!=1||cfg.mode>1||cfg.expectedPid!=GetCurrentProcessId()||
           cfg.localPath[511]||!cfg.localPath[0]||cfg.reserved[0]||cfg.reserved[1]||cfg.reserved[2]||cfg.reserved[3])return 2;
        FILETIME born{},exit{},kernel{},cpu{};
        if(!GetProcessTimes(GetCurrentProcess(),&born,&exit,&kernel,&cpu)||
           ((uint64_t(born.dwHighDateTime)<<32)|born.dwLowDateTime)!=cfg.expectedProcessBirth)return 3;
        base=cfg.expectedBase;user=cfg.expectedUser;if(!base||!user)return 4;
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
        slot=cfg.testSlot;if(!slot||!currentGuard())return 5;
        if(*slot!=cfg.testExpectedOriginal)return 9;
        report.expectedSize=cfg.testSize;memcpy(report.expectedSha256,cfg.testSha256,32);
#else
        if(base!=uintptr_t(GetModuleHandleW(nullptr))||wcscmp(cfg.localPath,PROBE_LOCAL_PATH))return 5;
        wchar_t path[32768]{};
        if(!GetModuleFileNameW(nullptr,path,32768)||!hashPath(path,PROBE_EXE_SHA))return 6;
        for(const auto& a:PROBE_ANCHORS)if(memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size))return 7;
        if(!probeGuard(base,user,pinned,true)||pinned.cacheMode!=0)return 8;
        slot=reinterpret_cast<void* volatile*>(base+PROBE_USER_VT+0x28);
        if(uintptr_t(*slot)!=base+PROBE_USER_UPDATE)return 9;
        report.expectedSize=PROBE_FILE_SIZE;memcpy(report.expectedSha256,PROBE_FILE_SHA,32);
#endif
        original=uintptr_t(*slot);
        CheckpointPushBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(original);bridge.before=before;bridge.after=after;
        if(!CheckpointPushBridgeConfigure(0,&bridge))return 10;
        report.mode=cfg.mode;report.base=base;report.user=user;report.slot=uintptr_t(slot);report.original=original;
        report.hook=uintptr_t(&CheckpointPushBridge0);report.installerThread=GetCurrentThreadId();
        AcquireSRWLockExclusive(&slotLock);
        void* prior=nullptr;bool protectedAgain=false;
        __try {
            if(InterlockedCompareExchange(&stopped,0,0)){InterlockedExchange(&state,FP_CANCELLED);return 14;}
            if(!VirtualProtect(const_cast<void**>(slot),8,PAGE_READWRITE,&originalProtection))return 11;
            protectionKnown=true;pageDirty=true;report.initialProtection=originalProtection;
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
            if(cfg.testFailAfterProtect)RaiseException(0xE0141001,0,0,nullptr);
#endif
            InterlockedExchange(&state,FP_ARMED);
            prior=InterlockedCompareExchangePointer(slot,reinterpret_cast<void*>(&CheckpointPushBridge0),reinterpret_cast<void*>(original));
            if(prior==reinterpret_cast<void*>(original))hookPublished=true;
#ifdef CHECKPOINT_TARGET_PREPARE_FIXTURE
            if(cfg.testPublishedEvent){SetEvent(cfg.testPublishedEvent);WaitForSingleObject(cfg.testContinueInstall,5000);}
#endif
            DWORD ignored=0;protectedAgain=VirtualProtect(const_cast<void**>(slot),8,originalProtection,&ignored)!=0;
            if(protectedAgain)pageDirty=false;
        }__finally {ReleaseSRWLockExclusive(&slotLock);}
        if(prior!=reinterpret_cast<void*>(original)||!protectedAgain){error(12);InterlockedExchange(&state,FP_REJECTED);restoreSlot();return 12;}
        if(InterlockedCompareExchange(&stopped,0,0)){restoreSlot();return 14;}
        return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){error(13);InterlockedExchange(&state,FP_UNCERTAIN);restoreSlot();return 13;}
}
extern "C" __declspec(dllexport) DWORD WINAPI StopTargetPrepare(void*){
    InterlockedExchange(&stopped,1);
    InterlockedCompareExchange(&state,FP_CANCELLED,FP_ARMED);
    InterlockedCompareExchange(&state,FP_CANCELLED,FP_CLAIMED);
    return restoreSlot()?0:1; // synchronous API already in progress is NOT cancelled
}
extern "C" __declspec(dllexport) DWORD WINAPI GetTargetPrepareReport(void* destination){
    TargetPrepareReport out;
    AcquireSRWLockShared(&reportLock);out=report;ReleaseSRWLockShared(&reportLock);
    out.state=loadState();out.error=InterlockedCompareExchange(&firstError,0,0);
    out.stopRequested=InterlockedCompareExchange(&stopped,0,0);out.callbackActive=InterlockedCompareExchange(&callbacks,0,0);
    CheckpointPushBridgeSnapshot(0,&out.bridge);out.modulePinned=out.bridge.module_pinned;
    out.bridgeDrainedSnapshot=out.bridge.active==0&&out.callbackActive==0;
    if(out.bridge.abnormal_exits&&!out.originalReturned){out.state=FP_UNCERTAIN;strncpy_s(out.stage,"original_abnormal_no_after",_TRUNCATE);}
    __try {
        if(slot){out.observedSlot=uintptr_t(*slot);MEMORY_BASIC_INFORMATION m{};
            if(VirtualQuery(const_cast<void**>(slot),&m,sizeof m)==sizeof m)out.observedProtection=m.Protect;}
        *reinterpret_cast<TargetPrepareReport*>(destination)=out;return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){return 1;}
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
