#include "autonomous_pilot.h"
#include <intrin.h>
#include <cstring>
#include <cwchar>

// One installation per loaded module. No worker, file, socket or game call in DllMain.
extern "C" __declspec(dllexport) PilotReportData PilotReport = {REPORT_MAGIC,1};
static PilotConfig config{};
static volatile LONG installed=0, claimed=0;
static uintptr_t gameBase=0;
static void* volatile* hookSlot=nullptr;
static UpdateFunction originalUpdate=nullptr;
static SubmitFunction nativeSubmit=nullptr;
static DWORD initialProtection=0;
static constexpr uintptr_t UPDATE_RVA=0x3F9B00, VTABLE_RVA=0x12CC4A8;
static const unsigned char submitPrefix[32]={0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0x6c,0x24,0xd9,0x48,0x81,0xec,0xa0,0,0,0,0x48,0xc7,0x45,0xc7,0xfe,0xff,0xff,0xff};
static const unsigned char updatePrefix[9]={0x40,0x56,0x48,0x83,0xec,0x40,0x48,0x8b,0xf1};
template<class T> static T readAt(uintptr_t a) { return *reinterpret_cast<T*>(a); }
static bool reject(LONG error) { PilotReport.error=error; return false; }

static bool guard(void* self, bool beforeSubmission) {
    const auto manager=gameBase+0x19E7310;
    auto count=readAt<uint64_t>(manager+0x10);
    auto stack=readAt<uintptr_t>(manager+0x20);
    if(count!=5 || !stack || readAt<uintptr_t>(stack+32)!=uintptr_t(self) ||
       readAt<uintptr_t>(uintptr_t(self))!=gameBase+VTABLE_RVA ||
       readAt<uint32_t>(uintptr_t(self)+0x470)!=2) return reject(10);
    auto root=readAt<uintptr_t>(gameBase+0x1FCA1E0);
    auto world=readAt<uintptr_t>(root+0x85130);
    if(readAt<uint16_t>(world+0x34)!=203 || readAt<uint8_t>(world+0x36)!=8 ||
       readAt<uint8_t>(world+0x37)!=11 || readAt<uint8_t>(world+0x3A)!=12) return reject(11);
    auto city=readAt<uintptr_t>(root+0xDAA8+19*8);
    auto person=readAt<uintptr_t>(root+0x148+666*8);
    auto districtId=readAt<uint8_t>(person+0x118);
    if(!districtId || districtId>51) return reject(12);
    auto district=readAt<uintptr_t>(root+0xDE40+districtId*8);
    if(readAt<uint16_t>(city+0x10)!=19 || readAt<uint16_t>(person+0x10)!=666 ||
       readAt<uint8_t>(district+0x10)!=12 || readAt<uint8_t>(city+0x30)!=districtId ||
       (beforeSubmission && readAt<uint16_t>(person+0x11A)!=readAt<uint16_t>(city+0x4E))) return reject(12);
    auto troops=readAt<uint32_t>(city+0x3C);
    auto actions=readAt<uint8_t>(district+0x14);
    if(beforeSubmission) {
        PilotReport.beforeGarrison=troops; PilotReport.beforeAction=actions;
        if(troops!=15204 || actions!=18) return reject(13);
    } else {
        PilotReport.afterGarrison=troops; PilotReport.afterAction=actions;
        if(troops!=13904 || actions!=17) return reject(14);
    }
    unsigned active=0, actorUnits=0;
    for(unsigned i=1;i<=500;i++) {
        auto unit=readAt<uintptr_t>(root+0x7DF60+i*8);
        if(readAt<uint8_t>(unit+0x10) && readAt<uint16_t>(unit+0x12)) {
            active++;
            if(readAt<uint16_t>(unit+0x12)==666) {
                actorUnits++;
                if(!beforeSubmission) {
                    PilotReport.unit=unit;
                    if(readAt<uint16_t>(unit+0x16)!=1300 || readAt<uint8_t>(unit+0x1B)!=4 ||
                       readAt<uint8_t>(unit+0x1C)!=11 || readAt<uint8_t>(unit+0x38)!=5 ||
                       readAt<uint16_t>(unit+0x3A)!=20) return reject(15);
                }
            }
        }
    }
    if(active!=(beforeSubmission?56U:57U) || actorUnits!=(beforeSubmission?0U:1U)) return reject(16);
    return true;
}

static bool restoreSlot() {
    DWORD temporary=0, ignored=0;
    if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&temporary)) return reject(20);
    void* replaced=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),
                                                     reinterpret_cast<void*>(PilotReport.hook));
    PilotReport.slotRestored=(replaced==reinterpret_cast<void*>(PilotReport.hook) ||
                             replaced==reinterpret_cast<void*>(originalUpdate));
    PilotReport.protectionRestored=VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)!=0;
    return PilotReport.slotRestored && PilotReport.protectionRestored;
}

static void __fastcall updateHook(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4) {
    InterlockedIncrement(&PilotReport.activeCallbacks);
    bool winner=InterlockedCompareExchange(&claimed,1,0)==0;
    if(winner) {
        PilotReport.status=2;
        PilotReport.executorThread=GetCurrentThreadId();
        PilotReport.caller=reinterpret_cast<uintptr_t>(_ReturnAddress());
        PilotReport.state=reinterpret_cast<uintptr_t>(self);
    }
    bool restored=!winner || restoreSlot();
    // Preserve the normal state update and all four integer/pointer arguments.
    originalUpdate(self,a2,a3,a4);
    InterlockedIncrement(reinterpret_cast<volatile LONG*>(&PilotReport.originalCalls));
    if(winner) {
        __try {
#ifndef PILOT_FIXTURE
            if(PilotReport.caller!=gameBase+0x50B785) { reject(21); restored=false; }
#endif
            if(!restored || !guard(self,true)) PilotReport.status=5;
            else if(!config.execute) PilotReport.status=3;
            else {
                PilotReport.submitCalls++;
                nativeSubmit(config.words,1);
                PilotReport.status=guard(self,false)?4:5;
            }
        } __except(EXCEPTION_EXECUTE_HANDLER) {
            PilotReport.exceptionCode=GetExceptionCode(); PilotReport.status=6;
        }
    }
    InterlockedDecrement(&PilotReport.activeCallbacks);
}

extern "C" __declspec(dllexport) DWORD WINAPI InstallPilot(void* input) {
    if(InterlockedCompareExchange(&installed,1,0)!=0) return 1001;
    PilotReport.installerThread=GetCurrentThreadId();
    __try {
        config=*reinterpret_cast<const PilotConfig*>(input);
        if(config.magic!=PILOT_MAGIC || config.version!=1 || config.execute>1 ||
           memcmp(config.words,RECORDED_COMMAND,sizeof(config.words))) {
            reject(30); PilotReport.status=5; return 30;
        }
#ifdef PILOT_FIXTURE
        gameBase=config.testBase;
        nativeSubmit=reinterpret_cast<SubmitFunction>(config.testSubmit);
#else
        wchar_t path[32768]{};
        if(!GetModuleFileNameW(nullptr,path,32768)) { reject(31); PilotReport.status=5; return 31; }
        const wchar_t* leaf=wcsrchr(path,L'\\'); leaf=leaf?leaf+1:path;
        if(_wcsicmp(leaf,L"SAN14PK_SC.exe")) { reject(31); PilotReport.status=5; return 31; }
        gameBase=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
        if(memcmp(reinterpret_cast<void*>(gameBase+0x1D1940),submitPrefix,sizeof(submitPrefix)) ||
           memcmp(reinterpret_cast<void*>(gameBase+UPDATE_RVA),updatePrefix,sizeof(updatePrefix))) {
            reject(32); PilotReport.status=5; return 32;
        }
        nativeSubmit=reinterpret_cast<SubmitFunction>(gameBase+0x1D1940);
#endif
        hookSlot=reinterpret_cast<void* volatile*>(gameBase+VTABLE_RVA+0x28);
        originalUpdate=reinterpret_cast<UpdateFunction>(*hookSlot);
#ifndef PILOT_FIXTURE
        if(reinterpret_cast<uintptr_t>(originalUpdate)!=gameBase+UPDATE_RVA) {
            reject(33); PilotReport.status=5; return 33;
        }
#endif
        auto manager=gameBase+0x19E7310;
        auto count=readAt<uint64_t>(manager+0x10);
        if(count!=5) { reject(10); PilotReport.status=5; return 10; }
        auto stack=readAt<uintptr_t>(manager+0x20);
        auto state=readAt<uintptr_t>(stack+32);
        if(!guard(reinterpret_cast<void*>(state),true)) { PilotReport.status=5; return PilotReport.error; }
        PilotReport.base=gameBase; PilotReport.slot=reinterpret_cast<uintptr_t>(hookSlot);
        PilotReport.original=reinterpret_cast<uintptr_t>(originalUpdate);
        PilotReport.hook=reinterpret_cast<uintptr_t>(&updateHook);
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,PAGE_READWRITE,&initialProtection)) {
            reject(34); PilotReport.status=5; return 34;
        }
        PilotReport.accepted=1; PilotReport.status=1;
        void* previous=InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(&updateHook),
                                                         reinterpret_cast<void*>(originalUpdate));
        DWORD ignored=0;
        if(!VirtualProtect(const_cast<void**>(hookSlot),8,initialProtection,&ignored)) {
            InterlockedCompareExchangePointer(hookSlot,reinterpret_cast<void*>(originalUpdate),reinterpret_cast<void*>(&updateHook));
            reject(35); PilotReport.status=5; return 35;
        }
        if(previous!=reinterpret_cast<void*>(originalUpdate)) { reject(36); PilotReport.status=5; return 36; }
        return 0;
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        PilotReport.exceptionCode=GetExceptionCode(); PilotReport.status=6; return 1002;
    }
}

extern "C" __declspec(dllexport) DWORD WINAPI CancelPilot(void*) {
    if(InterlockedCompareExchange(&claimed,2,0)!=0) return 1;
    if(!hookSlot || !PilotReport.accepted) return 2;
    if(!restoreSlot()) { PilotReport.status=5; return 3; }
    PilotReport.status=7; return 0;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID) { return TRUE; }
