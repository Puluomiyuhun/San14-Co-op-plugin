#pragma once
#include "checkpoint_persistent_route_core.h"
#include "checkpoint_push_bridge.h"
#include "checkpoint_persistent_bridge.h"
// Explicit new API, never a redefinition of the frozen worker bridge globals.
// All contexts, adapters and callbacks remain resident until process exit.
namespace checkpoint_persistent_logical_adapter {
using DispatchFinally=void(*)(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*);
struct Config {
    std::uint64_t generation=0;
    CheckpointPushObserver dispatchBefore[4]{},dispatchAfter[4]{};
    DispatchFinally dispatchFinally[4]{};
    void* dispatchContexts[4]{};
    CheckpointLoadWorkerObserver workerBefore[2]{},workerAfter[2]{};
    CheckpointLoadWorkerFinally workerFinally[2]{};
    void* workerContexts[2]{};
};
struct Report {
    std::uint64_t generation=0,before=0,after=0,finally=0,active=0,faults=0,claims=0,rejectedClaims=0;
    unsigned initialized=0,pinned=0;
    bool nativeSchedulerFence=false,productionAdmission=false;
};
struct Mapping {
    std::uint64_t generation=0,call=0;
    unsigned physicalSlot=0,logicalSlot=0,thread=0,stage=0,logicalWorkerDepth=0;
    const void* physicalFrame=nullptr;
    const void* logicalFrame=nullptr;
};
class Adapter {
public:
    bool Initialize(const Config&) noexcept;
    checkpoint_persistent_route::Generation RouteGeneration() noexcept;
    void Snapshot(Report&) noexcept;
    static void Before(const CheckpointLoadWorkerFrame*,void*);
    static void After(const CheckpointLoadWorkerFrame*,void*);
    static void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
private:
    friend bool Claim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
    friend bool CurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
    Config config_{};volatile LONG once_=0;
    volatile LONG64 before_=0,after_=0,finally_=0,active_=0,faults_=0,claims_=0,rejectedClaims_=0;
    bool pinned_=false;
};
// Only the exact currently executing logical worker BEFORE frame may claim.
// Frame copies, ancestors, dispatch frames, AFTER/native/FINALLY callers reject.
// Frame pointers are callback-lifetime borrowed references, not durable tokens.
bool Claim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
// Maps physical 4/5 to logical 0/1. Requires a claim issued via this adapter and
// exact same-generation mapping. Depth counts logical worker/read scopes only.
bool CurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
// Diagnostic mapping only; never a native-call/admission capability.
bool CurrentMapping(Mapping*) noexcept;
}
