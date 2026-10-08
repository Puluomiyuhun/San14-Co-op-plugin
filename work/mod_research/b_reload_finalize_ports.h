// Real Load.Finalize scope for Title callback and +520 worker start.
#pragma once
#include "b_reload_title590_ports.h"
#include "b_reload_title520_publish.h"
namespace b_reload_finalize_ports {
using Error=b_reload_title590_ports::Error;
using Sample=b_reload_title590_ports::Sample;
using ScopeReport=b_reload_title590_ports::ScopeReport;
struct Config {uintptr_t base=0;std::uint64_t generation=0;checkpoint_native_task_provider::Provider* provider=nullptr;b_reload_title520_publish::Publisher* title520=nullptr;DWORD helperDeadlineMs=1000;};
struct Report {std::uint64_t generation=0;Error error=Error::None;unsigned stopped=0,scopeCount=0,completedScopes=0,active=0;unsigned callback=0,start520=0;Sample samples[2]{};ScopeReport scopes[4]{};bool parentSourcesInstalled=false,globalFence=false,ready=false;};
class Adapter final {
public:
 // Stable address, two immutable generations; all state retained to process exit.
 // Existing DR ownership (including a nested Load/Title scope) is refused.
 // The native scheduler must establish a compatible Finalize call boundary;
 // this adapter neither supplies that scheduler source nor arbitrates DR slots.
 bool Initialize(const Config&) noexcept;
 void Stop() noexcept;
 bool Snapshot(Report&) noexcept;
 static bool Configure(uintptr_t base) noexcept;
 static void* Entry() noexcept;
private:void* state_=nullptr;
};
}
