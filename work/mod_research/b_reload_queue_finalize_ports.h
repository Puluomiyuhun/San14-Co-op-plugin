// Real Load.Finalize scope for Title callback and +520 worker start.
#pragma once
#include "b_reload_title590_ports.h"
#include "b_reload_title520_publish.h"
#include "b_reload_queue_parent_source.h"
namespace b_reload_queue_finalize_ports {
using Error=b_reload_title590_ports::Error;
using Sample=b_reload_title590_ports::Sample;
using ScopeReport=b_reload_title590_ports::ScopeReport;
struct Config {uintptr_t base=0;std::uint64_t generation=0;checkpoint_native_task_provider::Provider* provider=nullptr;b_reload_title520_publish::Publisher* title520=nullptr;DWORD helperDeadlineMs=1000;};
struct Report {std::uint64_t generation=0;Error error=Error::None;unsigned stopped=0,scopeCount=0,completedScopes=0,active=0;unsigned callback=0,start520=0,refused=0;Sample samples[2]{};ScopeReport scopes[4]{};b_reload_queue_parent_source::Binding binding{};std::uint64_t parentCall=0;uintptr_t caller=0,currentAtEntry=0,load=0,closure=0,title=0;bool parentSourcesInstalled=false,globalFence=false,ready=false;};
class Adapter final {
public:
 // Stable address, two immutable generations; all state retained to process exit.
 // Requires the new immutable queue parent scope and one of the four verified
 // scheduler Finalize callers. manager.current must remain zero. Existing DR
 // ownership is refused; the parent owner must still be in its queue phase.
 bool Initialize(const Config&) noexcept;
 void Stop() noexcept;
 bool Snapshot(Report&) noexcept;
 static bool Configure(uintptr_t base) noexcept;
 static void* Entry() noexcept;
private:void* state_=nullptr;
};
}
