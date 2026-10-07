#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include "checkpoint_push_bridge.h"
constexpr uint64_t LOAD_MODE_MAGIC=0x53414E144C4D4431ull;
enum LoadModeState:LONG { LM_NEW=0,LM_ARMED=1,LM_CLAIMED=2,LM_DRY_DONE=3,LM_QUEUED=4,
    LM_MENU_CALLBACK=5,LM_CANCEL_QUEUED=6,LM_USER_RETURNED=7,LM_REJECTED=8,LM_UNCERTAIN=9,LM_CANCELLED=10 };
enum LoadModeGuardStage:DWORD { LM_GUARD_INITIAL=0,LM_GUARD_MENU=1,LM_GUARD_RETURN=2 };
struct CheckpointLoadModeConfig {
    uint64_t magic=LOAD_MODE_MAGIC;
    uint32_t size=sizeof(CheckpointLoadModeConfig),version=1,execute=0,expectedPid=0;
    uint64_t expectedProcessBirth=0,expectedBase=0,expectedUser=0;
    wchar_t intentPath[512]{};
    uint64_t reserved[4]{};
#ifdef CHECKPOINT_LOAD_MODE_FIXTURE
    uintptr_t testQueue=0,testCancel=0;
#endif
};
#ifndef CHECKPOINT_LOAD_MODE_FIXTURE
static_assert(sizeof(CheckpointLoadModeConfig)==1104);
#endif
struct LoadModeSlotReport {
    uint64_t slot=0,original=0,hook=0,observed=0;
    uint32_t initialProtection=0,observedProtection=0,restored=0,protectionRestored=0;
};
struct CheckpointLoadModeReport {
    uint64_t magic=LOAD_MODE_MAGIC;
    uint32_t size=sizeof(CheckpointLoadModeReport),version=1;
    LONG state=LM_NEW,error=0;
    uint32_t execute=0,stopRequested=0,exceptionCode=0,callbackFaults=0;
    uint32_t callbackActive=0,userBeforeCalls=0,userAfterCalls=0,menuBeforeCalls=0,menuAfterCalls=0;
    uint32_t installerThread=0,queueThread=0,menuThread=0,returnThread=0;
    uint32_t intentCreated=0,intentFlushed=0,queueCalls=0,queueReturned=0,queueVerified=0;
    uint32_t menuAssociation=0,menuOriginalReturned=0,menuGuardBefore=0,menuGuardAfter=0;
    uint32_t cancelCalls=0,cancelReturned=0,cancelQueueVerified=0,returnSeen=0,returnMatched=0;
    uint32_t initialRng=0,returnedRng=0,initialMode=0,returnedMode=0;
    uint32_t nativeLoadAuthorized=0,customMetadataWrites=0,fullWorldVerified=0,nativeCancellationSeen=0;
    uint64_t base=0,user=0,game=0,world=0,cache=0,queuedState=0;
    uint64_t firstUserCallId=0,returnUserCallId=0,menuCallId=0,userCaller=0,menuCaller=0;
    uint64_t userRawRax=0,menuRawRax=0,queueBefore=0,queueAfter=0,cancelBefore=0,cancelAfter=0;
    LoadModeSlotReport userSlot{},menuSlot{};
    CheckpointPushBridgeStats userBridge{},menuBridge{};
    char stage[64]{};
};
extern "C" {
__declspec(dllexport) DWORD WINAPI InstallCheckpointLoadMode(void* config);
__declspec(dllexport) DWORD WINAPI StopCheckpointLoadMode(void*);
__declspec(dllexport) DWORD WINAPI GetCheckpointLoadModeReport(void* destination);
}
