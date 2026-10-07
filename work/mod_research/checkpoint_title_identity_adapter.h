#pragma once
#include "checkpoint_cc_load_lifecycle.h"
#include "checkpoint_identity_pair_commit.h"
namespace checkpoint_title_identity_adapter {
namespace pair=checkpoint_identity_pair_commit;
enum class Point:std::uint32_t { Before=1,Preflight,BeforeIntent,BeforeCompareExchange,AfterCompareExchange,After };
enum class Error:LONG {None=0,Config=1,Memory=2,Receipt=3,Worker=4,Guard=5,World=6,Pair=7,Duplicate=8,Owner=9,Commit=10,After=11,Abnormal=12,Stopped=13};
struct Config {
    uintptr_t base=0;std::uint64_t attemptToken=0;
    checkpoint_cc_load_lifecycle::Lifecycle* lifecycle=nullptr;
    checkpoint_cc_load_observer::Observer* bytes=nullptr;
    const wchar_t* intentPath=nullptr;unsigned char ownerBinding[32]{};
    // Mandatory nonthrowing profile/transaction/storage/hook/lifetime and unique
    // intent ownership verification. No lock is held around this callback.
    // It is NOT a global game-thread fence, and MUST NOT dereference historical
    // receipt.load after teardown. Root must bind expected digest/path/attempt.
    bool (*validateAttachment)(void*,Point,uintptr_t title,uintptr_t root,uintptr_t world)=nullptr;
    void* validationContext=nullptr;
#ifdef CHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE
    uintptr_t fixtureWorkerCaller=0;
#endif
};
struct Report {
    std::uint32_t version=1,size=sizeof(Report);LONG error=0;std::uint32_t exceptionCode=0;
    std::uint64_t token=0,title=0,historicalLoad=0,completionCall=0,callable=0,workerCall=0,caller=0,root=0,world=0,originalRax=0;
    pair::Pair source{},target{},observedPair{};
    std::uint32_t thread=0,phaseBefore=0,phaseAfter=0,stackBefore=0,stackAfter=0;
    std::uint32_t beforeCalls=0,afterCalls=0,finallyCalls=0,otherWorkers=0,active=0,abnormal=0,stopped=0;
    std::uint32_t commitState=0,commitCalls=0,casAttempts=0,casApplied=0,intentCreated=0,intentDurable=0,postGuard=0,commitReturned=0;
    std::uint32_t commitException=0,commitOsError=0,nativeReturned=0,worldForceAfter=0,worldControlAfter=0,identityObserved=0,receiptReady=0;
    std::uint32_t initializerCallsDirectlyObserved=0,planningReady=0,fullWorldVerified=0;
    unsigned char originalXmm0[16]{};char commitStage[64]{};
};
static_assert(sizeof(Report)==344);
struct Adapter {
    SRWLOCK lock=SRWLOCK_INIT;Config config{};Report report{};pair::Committer committer{};
    wchar_t intentPath[1024]{};
    volatile LONG initialized=0,claimed=0,error=0,stopped=0;
    std::uint64_t call=0,args[4]{},rsp=0;
    std::uint32_t thread=0,slot=0;
};
bool Initialize(Adapter&,const Config&) noexcept;
void Before(const CheckpointLoadWorkerFrame*,void*) noexcept;
void After(const CheckpointLoadWorkerFrame*,void*) noexcept;
void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
void Snapshot(Adapter&,Report&) noexcept;
void Stop(Adapter&) noexcept;
}
