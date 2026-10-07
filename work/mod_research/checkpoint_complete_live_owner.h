#pragma once
#include "checkpoint_live_storage_binding.h"

// Only data crosses the remote-call ABI. No callback/function pointers are accepted.
// One pinned module/owner/attempt; no reset, game discovery or post-CAS detach.
namespace checkpoint_complete_live_owner {
inline constexpr std::uint64_t Magic=0x53414E14434F5631ull;
inline constexpr unsigned Version=1;
struct Config {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Config),version=Version;
    std::uint32_t pid=0,reserved=0;
    std::uint64_t birth=0,base=0,attempt=0,epoch=0,generation=0;
    unsigned char attachment[32]{},ownerBinding[32]{},nonce[32]{},gameSha256[32]{};
    std::uint64_t states[5]{},root=0,world=0,cache=0,keyboard=0,toolbar=0,panel=0;
    std::uint64_t stack=0,stackCapacity=0,queue=0,queueCapacity=0;
    std::uint32_t rng=0,expectedMode=0,helperDeadlineMs=1000,reserved2=0;
    wchar_t localPath[512]{},installIntent[512]{},requestIntent[512]{},identityIntent[512]{};
    checkpoint_live_storage_binding::ModuleApproval storageModules[3]{};
    std::uint32_t storageModuleCount=0,vtableModuleIndex=0,counterModuleIndex=0,reserved3=0;
    checkpoint_live_storage_binding::Endpoint contextInit{},exists{},fileSize{},read{},ownedReadBridge{};
    std::uint64_t storage=0,storageVtable=0,storageCounter=0,cachedGeneration=0;
    unsigned char contextCode[0x65]{};
};
enum class Value:unsigned {
    OwnerState,OwnerError,OwnerException,OsError,InstallCalls,InstallIntentCreated,InstallIntentDurable,ModulePinned,Installed,StopRequested,RestoreCalls,RestoreReturned,
    SessionState,SessionError,SessionException,Armed,MenuBound,RequestInFlight,RequestSettled,CasPublished,MayHavePublished,HooksRestored,ActiveDispatch,ActiveWorker,ActiveRead,UserControllerCalls,DispatchUnpaired,
    QueueStage,QueueError,QueueNativeCalls,QueueNativeReturned,QueueVerified,QueueResolverCalls,QueueAuthorized,QueueStopped,QueueMayHaveQueued,
    ControllerError,ControllerBlocked,ControllerActive,ControllerStopped,ControllerFinished,ControllerOriginalCalls,ControllerAbnormal,ControllerQueueCalls,ControllerQueueReturned,ControllerAuthorizeCalls,ControllerAuthorized,ControllerCommit,ControllerBind,ControllerClosed,
    RequestState,RequestMenuCalls,RequestGameCalls,RequestReadAttempts,RequestCasAttempts,RequestCasApplied,RequestIntentCreated,RequestIntentDurable,RequestPostGuard,RequestOsError,RequestException,RequestObservedPending,
    BytesError,BytesWorkerBefore,BytesWorkerAfter,BytesWorkerFinally,BytesWorkerAbnormal,BytesReadBefore,BytesReadAfter,BytesReadFinally,BytesReadAbnormal,BytesMatched,BytesWorkerReturned,BytesObserved,BytesActiveWorker,BytesActiveRead,
    LifecycleError,LifecycleBound,LifecycleInFlight,LifecycleJoinReturned,LifecycleRequestCleared,LifecycleSuccessFlag,LifecycleExactPop,LifecycleFrozen,LifecycleReady,
    IdentityError,IdentityActive,IdentityAbnormal,IdentityCommitCalls,IdentityCasAttempts,IdentityCasApplied,IdentityIntentCreated,IdentityIntentDurable,IdentityNativeReturned,IdentityObserved,IdentityReady,
    PlanningError,PlanningException,PlanningBefore,PlanningAfter,PlanningInFlight,PlanningWaiting,PlanningReceiptBound,PlanningStack,PlanningIdentity,PlanningRequestCleared,PlanningUi,PlanningNativeReturned,PlanningObserved,PlanningUserReused,PlanningUiForceMatches,PlanningSessionError,PlanningSessionStop,
    HardwareError,HardwareEntered,HardwareCaptured,HardwareRestored,HardwareFinished,HardwareRestoreUncertain,
    StorageError,StorageValidations,StorageOpened,StorageInvalidated,
    GuardError,GuardChecks,GuardException,
    InputExclusionProven,FullWorldVerified,PixelPresentationProven,ReadyAuthorized,
    Count
};
struct HookReceipt {std::uint64_t slot=0,original=0,hook=0,observed=0;std::uint32_t protection=0,lastProtection=0,error=0,known=0,dirty=0,published=0,restored=0,reserved=0;};
struct BridgeReceipt {std::uint64_t started=0,returned=0,abnormal=0,beforeFaults=0,afterFaults=0,cleanupFaults=0;};
struct Report {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Report),version=Version;
    std::uint64_t sequence=0,attempt=0,epoch=0;
    std::uint64_t value[static_cast<unsigned>(Value::Count)]{};
    HookReceipt hooks[6]{};BridgeReceipt bridges[6]{};
    // Frozen, pointer-free core reports copied verbatim; numeric addresses are
    // diagnostics only. Python must not dereference them.
    unsigned char bytesReceipt[288]{},lifecycleReceipt[488]{},identityReceipt[344]{},hardwareReceipt[696]{};
    unsigned char requestReadSha[32]{};
    std::uint64_t planningAttempt=0,planningEpoch=0,planningUserCall=0,planningIdentityCall=0,planningCompletedCall=0,planningUser=0;
    unsigned char planningBeforeSample[128]{},planningAfterSample[128]{};
    char requestStage[64]{},planningFailure[64]{};
};
struct Description {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Description),version=Version;
    std::uint32_t configSize=sizeof(Config),reportSize=sizeof(Report),valueCount=static_cast<unsigned>(Value::Count),reserved=0;
    std::uint64_t module=0,dispatchBridge[4]{},workerBridge=0,readBridge=0,authorizedForward=0;
};
}
extern "C" __declspec(dllexport) DWORD WINAPI DescribeCheckpointCompleteLiveOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointCompleteLiveOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI GetCheckpointCompleteLiveOwnerReport(void*);
extern "C" __declspec(dllexport) DWORD WINAPI StopCheckpointCompleteLiveOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI RestoreCheckpointCompleteLiveOwnerBeforeCommit(void*);
