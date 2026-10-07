#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstddef>

constexpr uint64_t SAVE_CONFIG_MAGIC=0x53414E1450534832ULL;
constexpr uint32_t SAVE_REPORT_MAGIC=0x1414E201;
struct SaveShortString { char data[16]; uint64_t size,capacity; };
struct SaveRequest { int32_t slot; uint32_t reserved; SaveShortString filename,caption; };
static_assert(sizeof(SaveShortString)==32 && sizeof(SaveRequest)==72);
static_assert(offsetof(SaveRequest,filename)==8 && offsetof(SaveRequest,caption)==40);

struct CheckpointPushConfig {
    uint64_t magic;
    uint32_t version,execute,slot,reservedMustBeZero;
    wchar_t intentPath[512]; // Fresh workspace intent, created/flushed before binder.
    wchar_t targetPath[512]; // Must exactly equal fixed private checkpoint filename.
#ifdef CHECKPOINT_PUSH_FIXTURE
    uintptr_t testBase,testBinder,testQueue;
#endif
};
struct CheckpointPushReportData {
    uint32_t magic,version;
    volatile LONG status; // 0 new,1 armed,2 callback,3 dry,4 queued,5 reject,6 uncertain,7 cancelled,8 returned to SAME User
    LONG error;
    volatile LONG activeCallbacks,accepted;
    DWORD installerThread,executorThread,originalCalls,binderCalls,queueCalls;
    DWORD intentCreated,intentFlushed,binderReturned,queueReturned;
    DWORD slotRestored,protectionRestored,exceptionCode,dryStorageQuery;
    DWORD sourceStringsConsumed,requestGlobalsMatched,queueItemVerified,reserved;
    DWORD storageContextCalls,fileExistsCalls,remoteSlotAbsent,storageReserved;
    uint64_t base,caller,state,slot,original,hook,queuedState,queueBefore,queueAfter;
    DWORD saveCallbacks,saveOriginalCalls,saveActiveCallbacks,savePhaseMask;
    DWORD saveAssociationOk,saveWorkerStarted,saveWorkerJoined,saveNativeSuccess;
    DWORD saveFinalizerCalled,saveFinalizerReturned,saveGlobalsCleared,saveObservationDone;
    DWORD saveSlotRestored,saveProtectionRestored,saveObservationError,saveReserved;
    uint64_t saveSlot,saveOriginal,saveHook,queuedAt,finalizedAt;
    DWORD returnSeen,returnMatched,returnThread,stopRequested;
    DWORD beforeRng,afterRng,cacheModeBefore,cacheModeAfter;
    uint64_t pinnedUser,pinnedGame,pinnedWorld,returnedAt,firstUserCallId,lastUserCallId;
    uint64_t userRawRax,saveRawRax;
};
static_assert(sizeof(CheckpointPushReportData)==384);
using SaveUpdate=uint64_t(__fastcall*)(void*,uintptr_t,uintptr_t,uintptr_t);
using SaveBinder=void(__fastcall*)(SaveRequest*);
using SaveQueue=void(__fastcall*)(void*,const char*,uintptr_t,void*);
using SaveInstall=DWORD(WINAPI*)(void*);
