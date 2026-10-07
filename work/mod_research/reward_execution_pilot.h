#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>

constexpr uint64_t REWARD_PROBE_MAGIC=0x53414E1452455831ULL;
constexpr uint32_t REWARD_REPORT_MAGIC=0x1414D001;
constexpr uint32_t PROBE_IDS[3]={97,759,904};
constexpr uint8_t PROBE_LOYALTY[3]={90,94,92};
constexpr uintptr_t NODE_POOL_RVA=0x19E1BF0, HANDLE_POOL_RVA=0x19E1C38;
constexpr uintptr_t PROBE_VTABLE_RVA=0x12CC4A8, PROBE_UPDATE_RVA=0x3F9B00;
// Integer-ID lists use 1024 slots. The unrelated pointer-list pool has 81920.
constexpr uint32_t REWARD_POOL_SLOTS=0x400;
struct RewardArgs { uintptr_t vtable,handle,funding; };
static_assert(sizeof(RewardArgs)==24);
using ProbeUpdate=void(__fastcall*)(void*,uintptr_t,uintptr_t,uintptr_t);
using ProbeCtor=RewardArgs*(__fastcall*)(RewardArgs*);
using ProbeAppend=uintptr_t(__fastcall*)(uintptr_t,uint32_t,uint8_t);
using ProbeDtor=void(__fastcall*)(RewardArgs*);
using ProbeInstall=DWORD(WINAPI*)(void*);
struct RewardProbeConfig {
    uint64_t magic;
    uint32_t version,execute;
#ifdef REWARD_FIXTURE
    uintptr_t testBase,testCtor,testAppend,testDtor;
    uintptr_t testPredicate,testSubmit;
#endif
};
struct RewardProbeReportData {
    uint32_t magic,version;
    volatile LONG status; // 0 new, 1 armed, 2 callback, 3 passed, 4 executed, 5 rejected, 6 exception, 7 cancelled
    LONG error;
    volatile LONG activeCallbacks,accepted;
    DWORD installerThread,executorThread,originalCalls,ctorCalls,appendCalls,dtorCalls;
    DWORD readbackCount,slotId,handleCleared,ownedSlotCleared,slotRestored,protectionRestored,exceptionCode,worldGuardUnchanged;
    DWORD readbackIds[3],reserved;
    uint64_t base,caller,hookSlot,original,hook,beforeNodes,afterNodes,beforeHandles,afterHandles;
};
static_assert(sizeof(RewardProbeReportData)==168);

constexpr uint32_t ELIGIBILITY_LIMIT=1024;
using EligibilityPredicate=int(__fastcall*)(uintptr_t);
using RewardSubmit=int(__fastcall*)(RewardArgs*);
struct RewardExecutionData {
    uint32_t magic,version,execute,predicateCalls,submitCalls,submitReturned,submitResult,postconditions;
    uint32_t loyaltyBefore[3],loyaltyAfter[3],goldBefore,goldAfter,actionsBefore,actionsAfter;
};
static_assert(sizeof(RewardExecutionData)==72);
