#pragma once
#include "checkpoint_forward_native_session.h"
namespace checkpoint_forward_planning_observer {
enum class Point:unsigned {Before=1,After=2};
enum class Error:LONG {None=0,Config,Receipt,Epoch,Caller,Overlap,Memory,HistoricalAddress,Stack,Worker,World,Identity,Pending,Interface,Changed,Pair};
struct Config {
    uintptr_t base=0,persistentRootState=0,persistentMotorState=0,previousUser=0;
    std::uint64_t attempt=0,epoch=0;
    checkpoint_forward_native_session::Session* session=nullptr;
    // Authenticates supported image, transaction epoch and callback ownership.
    // Must be read-only/nonthrowing; true is NOT a global input or render proof.
    bool(*validate)(void*,Point,std::uint64_t attempt,std::uint64_t epoch)=nullptr;
    void* context=nullptr;
#ifdef CHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE
    const checkpoint_forward_native_session::Report* syntheticReceipt=nullptr;
    uintptr_t fixtureCaller=0;
#endif
};
struct Sample {
    uintptr_t states[5]{},stack=0,root=0,world=0,force=0,ruler=0,district=0,cache=0,worker=0,toolbar=0,panel=0;
    DWORD uiForceContext=0;
};
struct Report {
    std::uint32_t version=1,size=sizeof(Report);LONG error=0;DWORD exceptionCode=0;
    std::uint64_t attempt=0,epoch=0,userCall=0,identityWorkerCall=0,completedLoadCall=0,nativeRax=0;
    uintptr_t historicalLoad=0,historicalTitle=0,observedUser=0;
    DWORD thread=0;unsigned before=0,after=0,ignored=0,waitingForReceipt=0,inFlight=0;
    unsigned receiptBound=0,formalPlanningStack=0,identityMatched=0,requestCleared=0,uiObjectsPresent=0,nativeReturned=0,planningBoundaryObserved=0;
    unsigned previousUserAddressReused=0,uiForceContextMatches=0,sessionHadError=0,sessionStopRequested=0;
    unsigned oldStateDestructorsDirectlyObserved=0,allWorkersFinishedProven=0,fullWorldVerified=0,inputExclusionProven=0,pixelPresentationProven=0;
    Sample beforeSample{},afterSample{};unsigned char nativeXmm0[16]{};
    const char* failedField="none";
};
static_assert(sizeof(Report)==456);
struct Observer {
    SRWLOCK lock=SRWLOCK_INIT;Config config{};Report report{};
    volatile LONG initialized=0,claimed=0,error=0,inFlight=0,completed=0;
    struct FrameRecord {std::uint64_t args[4]{},caller_entry_rsp=0,call_id=0;DWORD slot=0,thread_id=0;} frame;
};
bool Initialize(Observer&,const Config&) noexcept;
void Before(const CheckpointPushFrame*,void*) noexcept;
void After(const CheckpointPushFrame*,void*) noexcept;
// Own receipt only. Valid for this attempt/epoch/call, not a perpetual readiness
// assertion. Does not read old Load/Title, game memory, or external validator.
void Snapshot(Observer&,Report&) noexcept;
}
