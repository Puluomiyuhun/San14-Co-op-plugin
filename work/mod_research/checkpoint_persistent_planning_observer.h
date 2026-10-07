#pragma once
#include "checkpoint_load_request_commit.h"
#include "checkpoint_title_identity_adapter.h"

// One observer per immutable generation. Physical hooks and generation routing
// belong to the retained owner. This module never discovers/installs/drives.
namespace checkpoint_persistent_planning {
enum class Point:unsigned {Before=1,After=2};
enum class Error:LONG {None=0,Config,Receipt,Epoch,Caller,Overlap,Memory,Stack,Worker,World,Identity,Pending,Interface,Changed,Pair,Abnormal};
struct Expected {
    std::uint32_t year=0,month=0,day=0,force=0,ruler=0,district=0,byteSize=0;
    unsigned char sha256[32]{};
};
// Raw, already-produced core receipts. A trusted provider copies these from
// the current retained Session; it does not synthesize booleans from room/UI
// status. Old Report POD is a stable transfer shape, not a Session dependency.
// A dynamic identity successor can explicitly copy its matching base fields.
struct Source {
    std::uint64_t attempt=0,epoch=0,generation=0;
    unsigned initialized=0,casPublished=0,mayHavePublished=0,stopRequested=0;
    LONG sessionError=0;
    checkpoint_load_request_commit::Report request{};
    checkpoint_cc_load_observer::Report bytes{};
    checkpoint_cc_load_lifecycle::Report lifecycle{};
    checkpoint_title_identity_adapter::Report identity{};
};
using SourceProvider=bool(*)(void*,Source&) noexcept;
struct Config {
    uintptr_t base=0,persistentRootState=0,persistentMotorState=0,previousUser=0;
    std::uint64_t attempt=0,epoch=0,generation=0;
    Expected expected{};
    SourceProvider source=nullptr;void* sourceContext=nullptr;
    // Authenticate supported image, same logical lease/frame, immutable epoch
    // and owner attachment. Never treat this as global input/worker exclusion.
    bool(*validate)(void*,Point,const CheckpointPushFrame&,std::uint64_t attempt,
                    std::uint64_t epoch,std::uint64_t generation) noexcept=nullptr;
    void* context=nullptr;
#ifdef CHECKPOINT_PERSISTENT_PLANNING_FIXTURE
    uintptr_t fixtureCaller=0;
#endif
};
struct Sample {
    uintptr_t states[5]{},stack=0,root=0,world=0,force=0,ruler=0,district=0,cache=0,worker=0,toolbar=0,panel=0;
    DWORD uiForceContext=0;
};
struct Report {
    std::uint32_t version=1,size=sizeof(Report);LONG error=0;DWORD exceptionCode=0;
    std::uint64_t attempt=0,epoch=0,generation=0,userCall=0,identityWorkerCall=0,completedLoadCall=0,nativeRax=0;
    Expected expected{};
    uintptr_t historicalLoad=0,historicalTitle=0,observedUser=0;
    DWORD thread=0;unsigned before=0,after=0,ignored=0,waitingForReceipt=0,inFlight=0;
    unsigned finallyCalls=0,abnormal=0;
    unsigned receiptBound=0,formalPlanningStack=0,identityMatched=0,requestCleared=0,uiObjectsPresent=0,nativeReturned=0,planningBoundaryObserved=0;
    unsigned previousUserAddressReused=0,uiForceContextMatches=0,sessionHadError=0,sessionStopRequested=0;
    unsigned oldStateDestructorsDirectlyObserved=0,allWorkersFinishedProven=0,fullWorldVerified=0,inputExclusionProven=0,pixelPresentationProven=0;
    Sample beforeSample{},afterSample{};unsigned char nativeXmm0[16]{};
    char failedField[64]="none";
};
struct Observer {
    SRWLOCK lock=SRWLOCK_INIT;Config config{};Report report{};
    volatile LONG initialized=0,claimed=0,error=0,inFlight=0,completed=0,frameReady=0;
    Source bound{};
    struct FrameRecord {std::uint64_t args[4]{},caller_entry_rsp=0,call_id=0;DWORD slot=0,thread_id=0;} frame;
};
bool Initialize(Observer&,const Config&) noexcept;
void Before(const CheckpointPushFrame*,void*) noexcept;
void After(const CheckpointPushFrame*,void*) noexcept;
void Finally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
// Reads only its retained receipt. An original exception omits AFTER and leaves
// inFlight nonzero; outer finally bridge still propagates/records that fault.
void Snapshot(Observer&,Report&) noexcept;
}
