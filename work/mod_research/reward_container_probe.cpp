#include "reward_container_probe.h"
#include <intrin.h>
#include <cstring>
#include <cwchar>
#ifndef REWARD_FIXTURE
#include "reward_probe_fingerprints.h"
#endif

// No order-submit function or network interface. The normal build rehearses one
// list lifecycle; REWARD_ELIGIBILITY instead calls only the person predicate.
extern "C" __declspec(dllexport) RewardProbeReportData RewardProbeReport={REWARD_REPORT_MAGIC,1};
static volatile LONG installed=0,claimed=0;
static uintptr_t gameBase=0;
static void* volatile* hookSlot=nullptr;
static ProbeUpdate originalUpdate=nullptr;
static ProbeCtor construct=nullptr;
static ProbeAppend append=nullptr;
static ProbeDtor destroy=nullptr;
static DWORD initialProtection=0;
template<class T> static T at(uintptr_t a) { return *reinterpret_cast<T*>(a); }
static bool reject(LONG e) { RewardProbeReport.error=e; return false; }

static bool guard(void* self) {
    auto manager=gameBase+0x19E7310;
    auto stack=at<uintptr_t>(manager+0x20);
    if(at<uint64_t>(manager+0x10)!=5 || !stack || at<uintptr_t>(stack+32)!=uintptr_t(self) ||
       at<uintptr_t>(uintptr_t(self))!=gameBase+PROBE_VTABLE_RVA || at<uint32_t>(uintptr_t(self)+0x470)!=2) return reject(10);
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0);
    auto world=at<uintptr_t>(root+0x85130);
    if(at<uint16_t>(world+0x34)!=203 || at<uint8_t>(world+0x36)!=8 ||
       at<uint8_t>(world+0x37)!=11 || at<uint8_t>(world+0x3A)!=12) return reject(11);
    auto city=at<uintptr_t>(root+0xDAA8+19*8);
    auto district=at<uintptr_t>(root+0xDE40+11*8);
    auto ruler=at<uintptr_t>(root+0x148+666*8);
    if(at<uint16_t>(city+0x10)!=19 || at<uint8_t>(city+0x30)!=11 || at<uint8_t>(district+0x10)!=12 ||
       at<uint16_t>(district+0x12)!=666 || at<uint16_t>(ruler+0x10)!=666 ||
       at<uint16_t>(ruler+0x11A)!=at<uint16_t>(city+0x4E)) return reject(12);
    if(at<uint32_t>(city+0x34)!=83308 || at<uint32_t>(city+0x3C)!=15204 || at<uint8_t>(district+0x14)!=18) return reject(13);
    for(unsigned i=0;i<3;i++) {
        auto person=at<uintptr_t>(root+0x148+PROBE_IDS[i]*8);
        if(at<uint16_t>(person+0x10)!=PROBE_IDS[i] || at<uint8_t>(person+0x118)!=11) return reject(14);
        if(at<uint8_t>(person+0x120)!=PROBE_LOYALTY[i] || at<uint16_t>(person+0x196)!=128 ||
           at<uint8_t>(person+0x11E)==1) return reject(15);
    }
    return true;
}

static bool poolGuard() {
    auto p=gameBase+NODE_POOL_RVA,h=gameBase+HANDLE_POOL_RVA;
    if(!at<uintptr_t>(p+8) || !at<uintptr_t>(p+0x10) || !at<uintptr_t>(p+0x18) ||
       !at<uintptr_t>(p+0x28) || at<uint32_t>(p+0x40)!=REWARD_POOL_SLOTS ||
       at<uint64_t>(h+0x38)!=REWARD_POOL_SLOTS || at<uint64_t>(p+0x30)>at<uint64_t>(p+0x38) ||
       at<uint64_t>(h+0x30)>=at<uint64_t>(h+0x38)) return reject(40);
    return true;
}

static bool constructAndRead(RewardArgs* args) {
    auto pool=gameBase+NODE_POOL_RVA;
    RewardProbeReport.ctorCalls++;
    if(construct(args)!=args || args->vtable!=gameBase+0x123E210 || !args->handle) return reject(41);
    auto slot=at<uint32_t>(args->handle);
    RewardProbeReport.slotId=slot;
    if(slot>=REWARD_POOL_SLOTS) return reject(42);
    auto heads=at<uintptr_t>(pool+0x10),tails=at<uintptr_t>(pool+0x18),counts=at<uintptr_t>(pool+0x28);
    if(at<uintptr_t>(heads+slot*8) || at<uintptr_t>(tails+slot*8) || at<uint64_t>(counts+slot*8)) return reject(43);
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0);
    args->funding=at<uintptr_t>(root+0xDAA8+19*8);
    for(unsigned i=0;i<3;i++) {
        RewardProbeReport.appendCalls++;
        auto node=append(pool,slot,1);
        if(!node) return reject(44);
        *reinterpret_cast<uint32_t*>(node)=PROBE_IDS[i];
    }
    if(at<uint64_t>(counts+slot*8)!=3) return reject(45);
    auto node=at<uintptr_t>(heads+slot*8);
    uintptr_t previous=0;
    for(unsigned i=0;i<3;i++) {
        if(!node || at<uintptr_t>(node+0x10)!=previous) return reject(46);
        RewardProbeReport.readbackIds[i]=at<uint32_t>(node);
        RewardProbeReport.readbackCount++;
        if(RewardProbeReport.readbackIds[i]!=PROBE_IDS[i]) return reject(47);
        previous=node; node=at<uintptr_t>(node+8);
    }
    if(node || at<uintptr_t>(tails+slot*8)!=previous) return reject(48);
    return true;
}

static bool roundtrip() {
    if(!poolGuard()) return false;
    auto p=gameBase+NODE_POOL_RVA,h=gameBase+HANDLE_POOL_RVA;
    RewardProbeReport.beforeNodes=at<uint64_t>(p+0x30);
    RewardProbeReport.beforeHandles=at<uint64_t>(h+0x30);
    RewardArgs args{};
    RewardProbeReport.slotId=0xFFFFFFFF;
    bool passed=false;
    __try { passed=constructAndRead(&args); }
    __finally {
        // Clear partially constructed lists too. No reward handler is invoked.
        RewardProbeReport.dtorCalls++;
        destroy(&args);
        RewardProbeReport.handleCleared=args.handle==0;
        auto slot=RewardProbeReport.slotId;
        if(slot<REWARD_POOL_SLOTS) {
            RewardProbeReport.ownedSlotCleared=
                !at<uintptr_t>(at<uintptr_t>(p+0x10)+slot*8) &&
                !at<uintptr_t>(at<uintptr_t>(p+0x18)+slot*8) &&
                !at<uint64_t>(at<uintptr_t>(p+0x28)+slot*8);
        }
        RewardProbeReport.afterNodes=at<uint64_t>(p+0x30);
        RewardProbeReport.afterHandles=at<uint64_t>(h+0x30);
    }
    if(!RewardProbeReport.handleCleared || (RewardProbeReport.slotId<REWARD_POOL_SLOTS && !RewardProbeReport.ownedSlotCleared) ||
       RewardProbeReport.beforeNodes!=RewardProbeReport.afterNodes ||
       RewardProbeReport.beforeHandles!=RewardProbeReport.afterHandles) return reject(49);
    return passed;
}

#ifdef REWARD_ELIGIBILITY
#include "reward_eligibility_probe.inc"
#endif

static bool restoreSlot() {
    DWORD temporary=0,ignored=0;
    if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&temporary)) return reject(20);
    void* old=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(RewardProbeReport.hook));
    RewardProbeReport.slotRestored=old==reinterpret_cast<void*>(RewardProbeReport.hook) || old==reinterpret_cast<void*>(originalUpdate);
    RewardProbeReport.protectionRestored=VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)!=0;
    return RewardProbeReport.slotRestored && RewardProbeReport.protectionRestored;
}

static void __fastcall updateHook(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4) {
    InterlockedIncrement(&RewardProbeReport.activeCallbacks);
    bool winner=InterlockedCompareExchange(&claimed,1,0)==0;
    if(winner) {
        RewardProbeReport.status=2;
        RewardProbeReport.executorThread=GetCurrentThreadId();
        RewardProbeReport.caller=reinterpret_cast<uintptr_t>(_ReturnAddress());
    }
    bool restored=!winner || restoreSlot();
    originalUpdate(self,a2,a3,a4);
    InterlockedIncrement(reinterpret_cast<volatile LONG*>(&RewardProbeReport.originalCalls));
    if(winner) {
        __try {
#ifndef REWARD_FIXTURE
            if(RewardProbeReport.caller!=gameBase+0x50B785) { reject(21); restored=false; }
#endif
            if(!restored || !guard(self)) RewardProbeReport.status=5;
            else {
#ifdef REWARD_ELIGIBILITY
                bool passed=queryRewardEligibility();
#else
                bool passed=roundtrip();
#endif
                RewardProbeReport.worldGuardUnchanged=guard(self);
                RewardProbeReport.status=passed && RewardProbeReport.worldGuardUnchanged?3:5;
            }
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            RewardProbeReport.exceptionCode=GetExceptionCode(); RewardProbeReport.status=6;
        }
    }
    InterlockedDecrement(&RewardProbeReport.activeCallbacks);
}

extern "C" __declspec(dllexport) DWORD WINAPI InstallRewardProbe(void* input) {
    if(InterlockedCompareExchange(&installed,1,0)!=0) return 1001;
    RewardProbeReport.installerThread=GetCurrentThreadId();
    __try {
        auto config=*reinterpret_cast<const RewardProbeConfig*>(input);
        if(config.magic!=REWARD_PROBE_MAGIC || config.version!=1 || config.reserved) { reject(30); RewardProbeReport.status=5; return 30; }
#ifdef REWARD_FIXTURE
        gameBase=config.testBase;
        construct=reinterpret_cast<ProbeCtor>(config.testCtor);
        append=reinterpret_cast<ProbeAppend>(config.testAppend);
        destroy=reinterpret_cast<ProbeDtor>(config.testDtor);
#ifdef REWARD_ELIGIBILITY
        eligibilityPredicate=reinterpret_cast<EligibilityPredicate>(config.testPredicate);
#endif
#else
        wchar_t path[32768]{};
        if(!GetModuleFileNameW(nullptr,path,32768)) { reject(31); RewardProbeReport.status=5; return 31; }
        const wchar_t* leaf=wcsrchr(path,L'\\'); leaf=leaf?leaf+1:path;
        if(_wcsicmp(leaf,L"SAN14PK_SC.exe")) { reject(31); RewardProbeReport.status=5; return 31; }
        gameBase=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        for(const auto& fingerprint:REWARD_FINGERPRINTS) {
            if(memcmp(reinterpret_cast<void*>(gameBase+fingerprint.rva),fingerprint.bytes,32)) {
                reject(32); RewardProbeReport.status=5; return 32;
            }
        }
        construct=reinterpret_cast<ProbeCtor>(gameBase+0x22600);
        append=reinterpret_cast<ProbeAppend>(gameBase+0x171B0);
        destroy=reinterpret_cast<ProbeDtor>(gameBase+0x83E0);
#ifdef REWARD_ELIGIBILITY
        for(const auto& fingerprint:ELIGIBILITY_FINGERPRINTS) {
            if(memcmp(reinterpret_cast<void*>(gameBase+fingerprint.rva),fingerprint.bytes,fingerprint.size)) {
                reject(32); RewardProbeReport.status=5; return 32;
            }
        }
        eligibilityPredicate=reinterpret_cast<EligibilityPredicate>(gameBase+0x1D4270);
#endif
#endif
        hookSlot=reinterpret_cast<void* volatile*>(gameBase+PROBE_VTABLE_RVA+0x28);
        originalUpdate=reinterpret_cast<ProbeUpdate>(*hookSlot);
#ifndef REWARD_FIXTURE
        if(reinterpret_cast<uintptr_t>(originalUpdate)!=gameBase+PROBE_UPDATE_RVA) { reject(33); RewardProbeReport.status=5; return 33; }
#endif
        auto manager=gameBase+0x19E7310;
        if(at<uint64_t>(manager+0x10)!=5) { reject(10); RewardProbeReport.status=5; return 10; }
        auto state=at<uintptr_t>(at<uintptr_t>(manager+0x20)+32);
        if(!guard(reinterpret_cast<void*>(state)) || !poolGuard()) { RewardProbeReport.status=5; return RewardProbeReport.error; }
        RewardProbeReport.base=gameBase; RewardProbeReport.hookSlot=reinterpret_cast<uintptr_t>(hookSlot);
        RewardProbeReport.original=reinterpret_cast<uintptr_t>(originalUpdate);
        RewardProbeReport.hook=reinterpret_cast<uintptr_t>(&updateHook);
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&initialProtection)) { reject(34); RewardProbeReport.status=5; return 34; }
        RewardProbeReport.accepted=1; RewardProbeReport.status=1;
        void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(&updateHook),reinterpret_cast<void*>(originalUpdate));
        DWORD ignored=0;
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)) {
            InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(&updateHook));
            reject(35); RewardProbeReport.status=5; return 35;
        }
        if(previous!=reinterpret_cast<void*>(originalUpdate)) { reject(36); RewardProbeReport.status=5; return 36; }
        return 0;
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        RewardProbeReport.exceptionCode=GetExceptionCode(); RewardProbeReport.status=6; return 1002;
    }
}
extern "C" __declspec(dllexport) DWORD WINAPI CancelRewardProbe(void*) {
    if(InterlockedCompareExchange(&claimed,2,0)!=0) return 1;
    if(!hookSlot || !RewardProbeReport.accepted) return 2;
    if(!restoreSlot()) { RewardProbeReport.status=5; return 3; }
    RewardProbeReport.status=7; return 0;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID) { return TRUE; }
