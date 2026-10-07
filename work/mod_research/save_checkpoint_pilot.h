#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstddef>

constexpr uint64_t SAVE_CONFIG_MAGIC=0x53414E1453565031ULL;
constexpr uint32_t SAVE_REPORT_MAGIC=0x1414E001;
struct SaveShortString { char data[16]; uint64_t size,capacity; };
struct SaveRequest { int32_t slot; uint32_t reserved; SaveShortString filename,caption; };
static_assert(sizeof(SaveShortString)==32 && sizeof(SaveRequest)==72);
static_assert(offsetof(SaveRequest,filename)==8 && offsetof(SaveRequest,caption)==40);

struct SaveCheckpointConfig {
    uint64_t magic;
    uint32_t version,execute,slot,reservedMustBeZero;
    wchar_t intentPath[512]; // Fresh workspace intent, created/flushed before binder.
    wchar_t targetPath[512]; // Must exactly equal standard native slot path.
#ifdef SAVE_CHECKPOINT_FIXTURE
    uintptr_t testBase,testBinder,testQueue;
#endif
};
struct SaveCheckpointReportData {
    uint32_t magic,version;
    volatile LONG status; // 0 new,1 armed,2 callback,3 dry,4 QUEUED NOT SAVED,5 reject,6 uncertain exception,7 cancelled
    LONG error;
    volatile LONG activeCallbacks,accepted;
    DWORD installerThread,executorThread,originalCalls,binderCalls,queueCalls;
    DWORD intentCreated,intentFlushed,binderReturned,queueReturned;
    DWORD slotRestored,protectionRestored,exceptionCode,dryStorageQuery;
    DWORD sourceStringsConsumed,requestGlobalsMatched,queueItemVerified,reserved;
    DWORD storageContextCalls,fileExistsCalls,remoteSlotAbsent,storageReserved;
    uint64_t base,caller,state,slot,original,hook,queuedState,queueBefore,queueAfter;
};
using SaveUpdate=void(__fastcall*)(void*,uintptr_t,uintptr_t,uintptr_t);
using SaveBinder=void(__fastcall*)(SaveRequest*);
using SaveQueue=void(__fastcall*)(void*,const char*,uintptr_t);
using SaveInstall=DWORD(WINAPI*)(void*);
