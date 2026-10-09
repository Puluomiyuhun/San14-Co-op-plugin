#pragma once
#include "b_reload_bootstrap.h"
#include "b_reload_cold_registration.h"
#include "b_reload_lifecycle_fault_guard.h"
// Retained in one DLL; trusted serialized host API, not a scheduler fence.
namespace b_reload_cold_bootstrap {
using Error=b_reload_bootstrap::Error;
using Report=b_reload_bootstrap::Report;
bool InitializeAndArm(const BReloadLifecycleBootstrapInfo&,checkpoint_native_task_provider::Provider&,const b_reload_cold_registration::Policy&) noexcept;
void Snapshot(Report&) noexcept;
class Runtime final {
public:
 Runtime()=default;~Runtime()=delete;
 bool InitializeAndArm(const BReloadLifecycleBootstrapInfo&,const b_reload_cold_registration::Policy&) noexcept;
 // Trusted native modules require this exact reference. This is not a public
 // remote API or a capability boundary against a malicious local host.
 checkpoint_native_task_provider::Provider& Provider() noexcept {return provider_;}
 bool OpenFirst(const checkpoint_native_task_provider::Config&) noexcept;
 bool BindCompleted(std::uint64_t,checkpoint_dynamic_native_session::Session&,checkpoint_persistent_authorized::Controller&) noexcept;
 bool OpenNext(const checkpoint_native_task_provider::Config&) noexcept;
 void Snapshot(Report&,b_reload_lifecycle::Report&,b_reload_root_activation::Report&,b_reload_lifecycle_fault_guard::Report&) noexcept;
private:
 checkpoint_native_task_provider::Provider provider_;
 b_reload_lifecycle_fault_guard::Gate* next_=new b_reload_lifecycle_fault_guard::Gate;
 uintptr_t image_=0;bool bootAttempted_=false,bootArmed_=false;
 DWORD host_=0;bool firstAttempted_=false,firstOpened_=false,bound_=false;
};
}
