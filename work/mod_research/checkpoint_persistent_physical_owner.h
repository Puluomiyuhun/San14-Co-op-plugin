#pragma once
#include "checkpoint_load_hook_set.h"
#include "checkpoint_persistent_route_six_adapter.h"

// Trusted in-process composition API, NOT the remote ABI. The application must
// authenticate game build/attachment/slots before calling Install. Contexts,
// callbacks, original targets and this Owner stay alive until process exit.
// This owner publishes immutable physical entries; it grants no native load.
namespace checkpoint_persistent_physical_owner {
enum class Point:unsigned {BeforeConfigure,BeforePublish,AfterPublish,Verify};
enum class Error:unsigned {None,Config,Memory,Pin,Guard,ExistingBridge,Router,HookSet,Configure,Publish,Drift};
struct Config {
    checkpoint_load_hook_set::Binding hooks[6]{};
    // Only User may forward through a resident, locally authenticated wrapper.
    // Other slots forward their expected native original exactly.
    void* userForward=nullptr;
    // Installation uses an internal empty bootstrap generation (id 1). No
    // caller's Session is reachable until a separately initialized generation
    // is published. Production currently leaves bootstrap forwarding forever.
    bool (*validate)(void*,Point,unsigned) noexcept=nullptr;
    void* context=nullptr;
};
struct Report {
    unsigned initialized=0,installed=0,pinned=0,configured=0,published=0,publicationAttempts=0;
    Error error=Error::None;DWORD exception=0;
    bool stopped=false,hooksRetained=false,publicationUncertain=false,productionAdmission=false,nativeSchedulerFence=false;
    std::uint64_t rejectedTransitions=0,routeFaults=0;
    checkpoint_load_hook_set::Report hooks{};
    checkpoint_persistent_route::Report route{};
    CheckpointPersistentBridgeStats bridges[6]{};
    uintptr_t original[6]{},forward[6]{};
};
class Owner final {
public:
    Owner() noexcept=default;
    Owner(const Owner&)=delete;Owner& operator=(const Owner&)=delete;
    bool Install(const Config&) noexcept;
    // Only compiled own-process fixtures may transition generations. Production
    // refuses: a native task handoff protocol must be integrated separately.
    bool PublishForOfflineExercise(std::uint64_t expected,const checkpoint_persistent_route::Generation&) noexcept;
    bool Verify() noexcept;
    // Stops future publication; existing sessions must separately revoke their
    // queue admission. Never suppresses post-request recovery observations.
    void Stop() noexcept;
    void Snapshot(Report&) noexcept;
private:
    SRWLOCK lock_=SRWLOCK_INIT;volatile LONG once_=0,stopped_=0;
    Config config_{};Report report_{};
    checkpoint_load_hook_set::Set hooks_{};
    checkpoint_persistent_route::Router router_{};
    checkpoint_persistent_route::SixAdapter adapter_{};
    bool guard(Point,unsigned) noexcept;
    bool fail(Error,DWORD=0) noexcept;
    bool verifyLocked() noexcept;
};
}
