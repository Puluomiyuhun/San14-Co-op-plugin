#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>

constexpr uint64_t PILOT_MAGIC = 0x53414E3134503031ULL;
constexpr uint32_t REPORT_MAGIC = 0x1414A001;
constexpr uint32_t RECORDED_COMMAND[26] = {
    666,0,1300,4,11,157,7,18,48400,48400,48400,48400,48400,
    4,5,20,0,1,0,1,2,48400,48400,0,48400,48400
};
struct PilotConfig {
    uint64_t magic;
    uint32_t version, execute;
    uint32_t words[26];
#ifdef PILOT_FIXTURE
    uintptr_t testBase, testSubmit;
#endif
};
struct PilotReportData {
    uint32_t magic, version;
    volatile LONG status; // 0 new, 1 armed, 2 callback, 3 dry, 4 executed, 5 rejected, 6 exception, 7 cancelled
    LONG error;
    volatile LONG activeCallbacks, accepted;
    DWORD installerThread, executorThread, originalCalls, submitCalls;
    DWORD beforeGarrison, afterGarrison, beforeAction, afterAction;
    uint64_t base, caller, state, unit, slot, original, hook;
    DWORD slotRestored, protectionRestored, exceptionCode, reserved;
};
static_assert(sizeof(PilotReportData)==128);
using UpdateFunction = void(__fastcall*)(void*,uintptr_t,uintptr_t,uintptr_t);
using SubmitFunction = uintptr_t(__fastcall*)(const uint32_t*,uint32_t);
using InstallFunction = DWORD(WINAPI*)(void*);
