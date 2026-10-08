// Title +520 role successor. Frozen Load-only router remains unchanged.
#pragma once
#include "checkpoint_task_native_ports.h"
#include "b_reload_title520_bridge.h"
#include "checkpoint_task_completion_worker_ports.h"
// Resident wrapper for native threadObject+38. No slot installer or code patch.
// 83A930 waits on object+20 before calling this pointer at 83A9DD. The wrapper
// is valid only for the fixed two-integer-argument 834D10 native runner ABI.
namespace b_reload_title520_router {
enum class Error:unsigned {None,Stopped,Reentry,Source,Caller,NativeBinding,Initialize,Begin,Finish};
struct Report {
    std::uint64_t generation=0,creation=0,callId=0;
    uintptr_t control=0,threadObject=0,caller=0;
    DWORD thread=0;Error error=Error::None;
    unsigned selected=0,beforeNative=0,initialized=0,beginAttempted=0,armed=0,after=0,finally=0,abnormal=0,stopped=0;
    std::uint64_t resultRax=0;unsigned char resultXmm0[16]{};
    checkpoint_task_completion_worker_ports::Report ports{};
    bool sourcePointerInstalled=false,productionPublication=false,globalFence=false;
};
struct Statistics {std::uint64_t before=0,unknownForwarded=0,refused=0;CheckpointLoadWorkerBridgeStats bridge{};};
class Router final {
public:
    // Entire Router and registered Providers must remain at stable addresses
    // until process exit. Configure once, at most two immutable generations.
    bool Initialize(uintptr_t base,DWORD helperDeadlineMs=1000) noexcept;
    bool Register(checkpoint_native_task_provider::Provider&,std::uint64_t generation) noexcept;
    // Exact immutable registration, before first selection. No publication lease.
    bool ValidateRegistration(const checkpoint_native_task_provider::Provider&,uintptr_t base,std::uint64_t generation) noexcept;
    void Stop(std::uint64_t generation) noexcept;
    bool Snapshot(std::uint64_t generation,Report&) noexcept;
    void SnapshotStatistics(Statistics&) noexcept;
    static void* Entry() noexcept;
private:
    struct Binding {checkpoint_native_task_provider::Provider* provider=nullptr;std::uint64_t generation=0;
        checkpoint_task_completion_worker_ports::Context ports;Report report{};volatile LONG used=0,stopped=0;};
    SRWLOCK lock_=SRWLOCK_INIT;uintptr_t base_=0;DWORD deadline_=0;unsigned count_=0;bool ready_=false;
    Binding bindings_[2];std::uint64_t before_=0,unknown_=0,refused_=0;
    static thread_local Binding* active_;
    static void Before(const CheckpointLoadWorkerFrame*,void*) noexcept;
    static void After(const CheckpointLoadWorkerFrame*,void*) noexcept;
    static void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
    void before(const CheckpointLoadWorkerFrame&) noexcept;
};
}
