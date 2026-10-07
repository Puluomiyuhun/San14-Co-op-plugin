#pragma once
#include "checkpoint_load_request_commit.h"
#include "checkpoint_load_hook_set.h"
#include "checkpoint_load_dispatch_bridge.h"
#include "checkpoint_persistent_bridge.h"
#include "checkpoint_title_identity_adapter.h"

// Per-generation successor: does not configure, install, restore or unload bridges.
// Logical adapter owns the exact callback scope; retain every Session until exit.
// Current cores retain the validated fixed archive/scenario profile. Production
// activation is closed until native scheduler/admission and dynamic profile bind.
namespace checkpoint_persistent_native_session {
enum class State:unsigned {New,Initialized,Armed,MenuQueued,MenuReady,RequestInFlight,ObservingLoad,LoadReceipt,IdentityReceipt,StoppedBeforeRequest,RetainingObservation,Rejected,Uncertain,HooksRestored};
enum class Point:unsigned {Initialize,Arm,BindMenu,BeforeRequest,AfterRequest,RestoreBeforeCommit};
enum class Error:LONG {None=0,Config,Initialize,Arm,Memory,DispatchPair,MenuBinding,Request,Controller,Restore};
class Session;
struct Config {
    // boundary.menu MUST be zero initially. Bound once, from normal QueueMenu
    // returned inside this Session's owned first User AFTER callback.
    checkpoint_load_request_commit::Config request{};
    checkpoint_cc_load_observer::Config bytes{};
    checkpoint_cc_load_lifecycle::Config lifecycle{};
    checkpoint_title_identity_adapter::Config identity{};
    // User/Menu/Game/Load update, generic callable, FileRead, in this order.
    checkpoint_load_hook_set::Binding hooks[6]{};
    // Descriptive binding only; this Session does not configure forwarding.
    // The future physical owner must authenticate its effective forwarding
    // target against this configuration. Targets stay resident until exit.
    void* dispatchForwardTargets[4]{};
    bool (*validate)(void*,Point)=nullptr;void* context=nullptr;
    // Nonthrowing controller: may issue one normal type0 queue-menu operation,
    // then immediately call BindQueuedMenu with its returned object. Must not
    // assume a bool proves native input exclusion/presentation ownership.
    void (*userAfter)(void*,Session&,const CheckpointPushFrame*)=nullptr;
    // Optional paired read-only observation for every User instance, including
    // the rebuilt User. Runs outside Session locks: BEFORE -> original -> AFTER.
    // Both or neither; callbacks/context must stay pinned and be nonthrowing.
    // A native original exception propagates through the bridge and omits AFTER.
    // Stop does not remove this observation; it never authorizes new requests.
    void (*userObservationBefore)(const CheckpointPushFrame*,void*) noexcept=nullptr;
    void (*userObservationAfter)(const CheckpointPushFrame*,void*) noexcept=nullptr;
    void* userObservationContext=nullptr;
#ifdef CHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE
    // Caller-label adaptation AND explicit offline activation. Never production.
    uintptr_t fixtureDispatchCaller[4]{};
#endif
};
struct QueueReceipt {std::uint64_t attempt=0,userCall=0;DWORD thread=0;uintptr_t user=0,menu=0;bool nativeQueueReturned=false;};
struct Report {
    State state=State::New;LONG error=0;DWORD exceptionCode=0;
    std::uint64_t attempt=0;uintptr_t menu=0;
    unsigned initialized=0,armed=0,menuBound=0,requestInFlight=0,requestSettled=0,casPublished=0,mayHavePublished=0,stopRequested=0,restoreRequested=0,hooksRestored=0;
    unsigned userControllerCalls=0,dispatchBefore[4]{},dispatchAfter[4]{},dispatchUnpaired=0;
    unsigned activeDispatch=0,activeWorker=0,activeRead=0;
    unsigned dispatchFinally[4]{},dispatchAbnormal=0;
    bool productionAdmission=false,nativeSchedulerFence=false;
    checkpoint_load_request_commit::Report request{};
    checkpoint_cc_load_observer::Report bytes{};
    checkpoint_cc_load_lifecycle::Report lifecycle{};
    checkpoint_title_identity_adapter::Report identity{};
    // Shared physical bridge statistics are deliberately absent. The owner
    // must separately check route/logical/bridge faults before issuing receipts.
    uintptr_t dispatchExpectedOriginal[4]{},dispatchEffectiveTarget[4]{};
    unsigned dispatchOverride[4]{};
    bool inputExclusionProven=false,presentationProven=false,nativePlanningReady=false,fullWorldVerified=false;
};
class Session {
public:
    bool Initialize(const Config&) noexcept;
    bool ActivateForOfflineExercise() noexcept;
    bool BindQueuedMenu(const QueueReceipt&) noexcept;
    // Never removes hooks or cancels an already published native request.
    // Once a request may be in flight, observations/identity recovery continue.
    void Stop() noexcept;
    // Compatibility refusal: a generation never restores shared physical hooks.
    bool RestoreBeforeCommit() noexcept;
    void Snapshot(Report&) noexcept;
    static void DispatchBefore(const CheckpointPushFrame*,void*) noexcept;
    static void DispatchAfter(const CheckpointPushFrame*,void*) noexcept;
    static void DispatchFinally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
    static void WorkerBefore(const CheckpointLoadWorkerFrame*,void*) noexcept;
    static void WorkerAfter(const CheckpointLoadWorkerFrame*,void*) noexcept;
    static void WorkerFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
    static void ReadBefore(const CheckpointLoadWorkerFrame*,void*) noexcept;
    static void ReadAfter(const CheckpointLoadWorkerFrame*,void*) noexcept;
    static void ReadFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
private:
    struct DispatchRecord {CheckpointPushFrame frame{};uintptr_t worker=0;bool accepted=false;};
    SRWLOCK lock_=SRWLOCK_INIT;Config config_{};Report report_{};
    checkpoint_load_request_commit::Committer request_{};
    checkpoint_cc_load_observer::Observer bytes_{};
    checkpoint_cc_load_lifecycle::Lifecycle lifecycle_{};
    checkpoint_title_identity_adapter::Adapter identity_{};
    // Physical hook ownership deliberately remains outside this generation.
    DispatchRecord dispatch_[4]{};
    wchar_t localPath_[512]{},requestIntent_[512]{},identityIntent_[1024]{};
    volatile LONG initialized_=0,armed_=0,accepting_=0,stop_=0,error_=0,menuBound_=0,menuOnce_=0,gameOnce_=0,userOnce_=0;
    volatile LONG requestActive_=0,requestSettled_=0,published_=0,mayPublished_=0,activeDispatch_=0,activeWorker_=0,activeRead_=0,restored_=0;
    volatile LONG userAfterActive_=0;std::uint64_t userAfterCall_=0;DWORD userAfterThread_=0;
    bool validate(Point) noexcept;
    void fail(Error,DWORD=0) noexcept;
    bool makeCall(const CheckpointPushFrame*,checkpoint_load_input_boundary::Stage,uintptr_t,checkpoint_load_input_boundary::Call&,uintptr_t&) noexcept;
    static bool requestGuard(void*,checkpoint_load_request_commit::Point) noexcept;
    void captureRequest() noexcept;
};
}
