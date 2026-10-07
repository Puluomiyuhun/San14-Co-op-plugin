#pragma once
#include "checkpoint_dynamic_file_profile.h"
#include "checkpoint_dynamic_cc_load_observer.h"
#include "checkpoint_push_bridge.h"
namespace checkpoint_dynamic_cc_load_lifecycle {
enum class Point:std::uint32_t { Bind=1,Before=2,After=3 };
enum class Error:LONG { None=0,Config=1,Binding=2,Memory=3,Guard=4,Caller=5,Overlap=6,
    Phase=7,Bytes=8,Join=9,Completion=10,Stopped=11 };
struct Config {
    const checkpoint_dynamic_file_profile::Profile* profile=nullptr;
    uintptr_t base=0;
    std::uint64_t attemptToken=0;
    checkpoint_dynamic_cc_load_observer::Observer* bytes=nullptr;
    // Nonthrowing read-only exact-image/transaction/Load+Title lifetime check.
    // Called only inside the live Load Update boundaries, never by Snapshot.
    bool (*validateAttachment)(void*,Point,uintptr_t load,uintptr_t title)=nullptr;
    void* validationContext=nullptr;
#ifdef CHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE
    uintptr_t fixtureUpdateCaller=0;
#endif
};
struct Report {
    std::uint32_t version=1,size=sizeof(Report);LONG error=0;std::uint32_t exceptionCode=0;
    std::uint64_t token=0,load=0,title=0,completionClosure=0,worker=0;
    std::uint64_t boundCall=0,joinedCall=0,completedCall=0,lastCall=0,lastRax=0;
    std::uint32_t lastThread=0,phaseBefore=0,phaseAfter=0,phaseMask=0;
    std::uint32_t beforeCalls=0,afterCalls=0,otherUpdates=0,inFlight=0;
    std::uint32_t bound=0,workerStarted=0,joinReturned=0,requestCleared=0;
    std::uint32_t successFlag=0,nativeResult=0,exactPop=0,completionFrozen=0;
    std::uint32_t receiptReady=0,stopped=0,directFinalizerObserved=0,planningReady=0,loadAuthorized=0,reserved=0;
    unsigned char lastXmm0[16]{};
    checkpoint_dynamic_cc_load_observer::Report frozenBytes{};
};
static_assert(sizeof(Report)==488);
struct Lifecycle {
    SRWLOCK lock=SRWLOCK_INIT;Config config{};Report report{};checkpoint_dynamic_file_profile::Profile profile{};
    volatile LONG initialized=0,bound=0,inFlight=0,error=0,stopped=0,completed=0;
    // Frames are copied field-by-field to a plain record, avoiding extra ABI
    // alignment requirements for a process-lifetime owner object.
    std::uint64_t call=0,args[4]{},rsp=0;
    std::uint32_t thread=0,slot=0,beforePhase=0;
};
bool Initialize(Lifecycle&,const Config&) noexcept;
void UpdateBefore(const CheckpointPushFrame*,void*) noexcept;
void UpdateAfter(const CheckpointPushFrame*,void*) noexcept;
void Snapshot(Lifecycle&,Report&) noexcept; // strictly own memory, even after Load is freed
void Stop(Lifecycle&) noexcept;
}
