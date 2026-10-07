#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
constexpr uint64_t CACHE_MAGIC=0x53414E1443414331ULL;
constexpr uint32_t CACHE_REPORT_MAGIC=0x1414EC01;
struct CacheConfig {
    uint64_t magic;uint32_t version,execute;wchar_t intentPath[512];
#ifdef AUTO_CACHE_FIXTURE
    uintptr_t testBase,testParameter,testScanner;
#endif
};
struct CacheReportData {
    uint32_t magic,version;volatile LONG status;LONG error;
    volatile LONG activeCallbacks,accepted;
    DWORD installerThread,executorThread,originalCalls,parameterCalls,scannerCalls;
    DWORD intentCreated,intentFlushed,scannerReturned,parameterValue,cachedSlots;
    DWORD slotRestored,protectionRestored,exceptionCode,worldUnchanged,slot34Matched,reserved;
    uint64_t base,caller,state,slot,original,hook,manager;
};
using CacheUpdate=void(__fastcall*)(void*,uintptr_t,uintptr_t,uintptr_t);
using CacheParameter=int(__fastcall*)();
using CacheScanner=void(__fastcall*)(void*,int);
using CacheInstall=DWORD(WINAPI*)(void*);
