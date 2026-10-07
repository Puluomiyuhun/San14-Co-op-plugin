// Version 2 publishes the join + Title590-start successor bridge.
#pragma once
#include "b_reload_title590_ports.h"
#include "checkpoint_load_hook_set.h"

// Retained publication of the real CTitleState::Update vtable entry. This is
// independent of the six-entry Load owner; it never replaces or stacks it.
namespace b_reload_title_source_v2 {
enum class Error : unsigned {
    None, Config, AlreadyOwned, Source, Completion, Bridge, Hooks, Stopped,
    Publication, Verification, Exception
};
struct Config {
    uintptr_t base=0;
    b_reload_title590_ports::Adapter* firstGeneration=nullptr;
};
struct Report {
    Error error=Error::None;
    DWORD exception=0;
    uintptr_t base=0,slot=0,original=0,replacement=0;
    unsigned initialized=0,bridgeConfigured=0,publishAttempted=0,published=0;
    unsigned stopped=0,verified=0,verifyCalls=0,modulePinned=0,ownerModulePinned=0;
    // published records our successful CAS. Only verified plus Error::None
    // attests current ownership; a later competing write is never overwritten.
    checkpoint_load_hook_set::Report hooks{};
    // This one source cannot attest to the other task sources or room gates.
    bool parentSourcesInstalled=false,titleStartsInstalled=false;
    bool fullInputHold=false,roomReady=false,gameValidated=false;
};
class Owner final {
public:
    // One resident owner per process. The selected base, source slots, bridge,
    // completion adapters and backing state remain alive until process exit.
    // Initialize checks the original slot and native code before consuming the
    // global owner claim. ConfigureTitle may not have been called separately.
    bool Initialize(const Config&) noexcept;
    // Exactly one publication attempt; verifies code and pointer again before
    // fixed-address CAS. HookSet restores the original page protection.
    bool Publish() noexcept;
    bool Verify() noexcept;
    // Blocks publication if not yet claimed. An already published bridge stays
    // resident and transparent; stop generation adapters separately to stop
    // capture. This is neither callback drainage nor an uninstall operation.
    void Stop() noexcept;
    bool Snapshot(Report&) noexcept;
    Owner()=default;
    Owner(const Owner&)=delete;
    Owner& operator=(const Owner&)=delete;
private:
    void* state_=nullptr;
};
}
