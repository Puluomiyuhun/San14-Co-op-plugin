#pragma once
#include "checkpoint_push_bridge.h"
#include <windows.h>
#include "checkpoint_native_input_hwbp.h"
#include "checkpoint_bound_input_pending_adapter.h"
inline constexpr std::uint64_t CheckpointLivePrefetchMagic=0x53414E1450465631ull;
struct CheckpointLivePrefetchConfig {
    std::uint64_t magic=CheckpointLivePrefetchMagic;
    std::uint32_t size=sizeof(CheckpointLivePrefetchConfig),version=1,pid=0,flags=0;
    std::uint64_t birth=0,base=0,attempt=0;
    unsigned char attachment[32]{};
    std::uint64_t root=0,world=0,states[5]{},toolbar=0,panel=0;
    std::uint32_t expectedUserThread=0,reserved32=0;
    wchar_t journal[512]{};
    std::uint64_t reserved[4]{};
    std::uint64_t cache=0,stack=0,stackCapacity=0,queue=0,queueCapacity=0;
    std::uint32_t expectedMode=0,helperDeadlineMs=1000;
    std::uint64_t generation=0;
};
static_assert(sizeof(CheckpointLivePrefetchConfig)==1272);
struct CheckpointLivePrefetchThreadStat {
    std::uint32_t threadId=0,reserved=0;
    std::uint64_t before=0,after=0,firstCall=0,lastCall=0,pending=0;
};
static_assert(sizeof(CheckpointLivePrefetchThreadStat)==48);
struct CheckpointLivePrefetchReport {
    std::uint32_t size=sizeof(CheckpointLivePrefetchReport),version=3,installed=0,stopped=0;
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
    CheckpointLivePrefetchThreadStat threads[128]{};
    std::uint64_t lateBefore=0,lateAfter=0,pendingPairs=0;
    checkpoint_native_input_pending::Report pendingBefore{},pendingAfter{};
    checkpoint_native_input_hwbp::HardwareReceipt hardware{};
    std::uint32_t admissionClaimed=0,admissionStarted=0,admissionFinished=0,admissionClosed=0;
    std::uint32_t admissionErrors=0,admissionAbnormal=0,admissionBindError=0,admissionCloseError=0;
    std::uint32_t admissionBeginOk=0,admissionResolverCalls=0;
};
extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointLivePrefetchObserver(void*);
extern "C" __declspec(dllexport) DWORD WINAPI GetCheckpointLivePrefetchReport(void*);
extern "C" __declspec(dllexport) DWORD WINAPI StopCheckpointLivePrefetchObserver(void*);

static_assert(offsetof(CheckpointLivePrefetchConfig,cache)==1216);
static_assert(offsetof(CheckpointLivePrefetchReport,pendingBefore)==6520);
static_assert(sizeof(checkpoint_native_input_pending::Report)==72);
static_assert(sizeof(checkpoint_native_input_hwbp::HardwareReceipt)==696);
static_assert(offsetof(CheckpointLivePrefetchReport,hardware)==6664);
static_assert(sizeof(CheckpointLivePrefetchReport)==7400);
#ifdef CHECKPOINT_LIVE_USER_THREADS_FIXTURE
void CheckpointLiveThreadsFixturePublishGate(HANDLE ready,HANDLE release) noexcept;
#endif
