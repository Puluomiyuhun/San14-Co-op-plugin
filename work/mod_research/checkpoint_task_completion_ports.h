#pragma once
#include "checkpoint_task_native_start.h"
// Companion to the frozen six-entry owner. It never installs a game hook,
// invokes a native task, publishes a generation, or supplies synthetic captures.
namespace checkpoint_task_completion {
enum class Error:unsigned {None,Config,Capacity,Binding,Occupied,Helper,Context,Deadline,Restore,Provider,Order,Exception,Stopped};
struct Config {
    uintptr_t base=0;std::uint64_t generation=0;
    checkpoint_native_task_provider::Provider* provider=nullptr;
    CheckpointPushObserver nextBefore=nullptr,nextAfter=nullptr;
    checkpoint_persistent_logical_adapter::DispatchFinally nextFinally=nullptr;void* nextContext=nullptr;
    DWORD helperDeadlineMs=1000;
#ifdef CHECKPOINT_TASK_COMPLETION_FIXTURE
    uintptr_t fixtureLoadCaller=0,fixtureTitleCaller=0;
#endif
};
struct Sample {std::uint64_t call=0,creation=0;uintptr_t rip=0;DWORD thread=0,rawFlags=0,mxcsr=0;unsigned role=0,accepted=0;
    std::uint64_t gpr[16]{};unsigned char xmm[256]{};};
struct ScopeReport {std::uint64_t call=0;uintptr_t owner=0;DWORD thread=0;unsigned title=0,armed=0,after=0,finally=0,abnormal=0,restored=0,uncertain=0,hits=0;
    Error error=Error::None;DWORD osError=0;std::uint64_t originalDr[6]{},restoredDr[6]{};};
struct Report {std::uint64_t generation=0;Error error=Error::None;unsigned stopped=0,scopeCount=0,completedScopes=0,active=0,unknownTitle=0;
    unsigned accepted[3]{};Sample joins[3]{};ScopeReport scopes[64]{};
    bool gameInstaller=false,parentSourcesInstalled=false,titleStartsInstalled=false,globalFence=false,ready=false;
};
class Adapter final {
public:
    // Retain at a stable address until process exit. Two immutable generations;
    // at most 64 native call scopes each. Capacity exhaustion refuses new capture.
    bool Initialize(const Config&) noexcept;
    void Stop() noexcept;
    bool Snapshot(Report&) noexcept;
    static void LoadBefore(const CheckpointPushFrame*,void*) noexcept;
    static void LoadAfter(const CheckpointPushFrame*,void*) noexcept;
    static void LoadFinally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*);
    // Configure one OS-loaded finally bridge for the actual Title Update ABI.
    // It uses the otherwise unused frozen worker bridge slot1. It must be
    // configured before installing this entry in a separately reviewed owner.
    static bool ConfigureTitle(uintptr_t base) noexcept;
    static void* TitleEntry() noexcept;
private:void* state_=nullptr;
};
}
