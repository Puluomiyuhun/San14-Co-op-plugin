#pragma once
#include "checkpoint_push_bridge.h"
#include <windows.h>
inline constexpr std::uint64_t CheckpointLiveSessionMagic=0x53414E144C495631ull;
struct CheckpointLiveSessionConfig {
    std::uint64_t magic=CheckpointLiveSessionMagic;
    std::uint32_t size=sizeof(CheckpointLiveSessionConfig),version=1,pid=0,flags=0;
    std::uint64_t birth=0,base=0,attempt=0;
    unsigned char attachment[32]{};
    std::uint64_t root=0,world=0,states[5]{},toolbar=0,panel=0;
    std::uint32_t expectedUserThread=0,reserved32=0;
    wchar_t journal[512]{};
    std::uint64_t reserved[4]{};
};
static_assert(sizeof(CheckpointLiveSessionConfig)==1216);
struct CheckpointLiveThreadStat {
    std::uint32_t threadId=0,reserved=0;
    std::uint64_t before=0,after=0,firstCall=0,lastCall=0,pending=0;
};
static_assert(sizeof(CheckpointLiveThreadStat)==48);
struct CheckpointLiveSessionReport {
    std::uint32_t size=sizeof(CheckpointLiveSessionReport),version=2,installed=0,stopped=0;
    std::uint32_t error=0,exception=0,pid=0,ownerThread=0;
    std::uint64_t birth=0,base=0,attempt=0,user=0,slot=0,original=0,hook=0;
    std::uint64_t before=0,after=0,matchingBefore=0,matchingAfter=0,otherUser=0,unpaired=0;
    std::uint64_t firstCall=0,lastCall=0,firstCaller=0,lastCaller=0;
    std::uint64_t firstArgs[4]{},firstRax=0;
    unsigned char firstXmm0[16]{};
    std::uint32_t firstPair=0,contextVerified=0,slotRestored=0,protectionRestored=0;
    std::uint32_t modulePinned=0,journalCreated=0,journalFlushed=0,active=0;
    std::uint64_t bridgeStarted=0,bridgeReturned=0,bridgeAbnormal=0;
    std::uint32_t queueCalls=0,requestCas=0,loadRequested=0,fullInputHold=0;
    std::uint32_t schedulerFenceProven=0,completeSessionInstalled=0,reserved[2]{};
    std::uint32_t threadCount=0,threadOverflow=0;
    std::uint64_t threadMigrations=0;
    std::uint32_t lastObservedThread=0,mode=0;
    std::uint64_t matchedPairs=0;
    std::uint32_t pairOverflow=0,pairErrors=0;
    CheckpointLiveThreadStat threads[128]{};
    std::uint64_t lateBefore=0,lateAfter=0,pendingPairs=0;
};
extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointLiveSessionObserver(void*);
extern "C" __declspec(dllexport) DWORD WINAPI GetCheckpointLiveSessionReport(void*);
extern "C" __declspec(dllexport) DWORD WINAPI StopCheckpointLiveSessionObserver(void*);

static_assert(sizeof(CheckpointLiveSessionReport)==6520);
#ifdef CHECKPOINT_LIVE_USER_THREADS_FIXTURE
void CheckpointLiveThreadsFixturePublishGate(HANDLE ready,HANDLE release) noexcept;
#endif
