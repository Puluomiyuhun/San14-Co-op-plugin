#pragma once
#include "b_reload_lifecycle.h"
#include "b_reload_cold_registration_wait.h"
namespace b_reload_cold_registration {
struct Policy {SRWLOCK* producerLock=nullptr;volatile LONG* taskStarts=nullptr;uintptr_t threadStart=0;DWORD deadlineMs=1000;};
enum class Error:unsigned {None,Config,Initialize,Owner,Binding,Wait,Registration,Exception};
struct Report {Error error=Error::None;unsigned prepared=0,attempts=0,oldCalls=0,registered=0;uintptr_t base=0,provider=0;b_reload_cold_registration_wait::Report wait{};b_reload_root_activation::Report activation{};};
// Trusted, serialized startup preparation. The caller must publish PreparedPlan
// under its proved startup boundary and Arm before the actual initializer runs.
bool Prepare(const b_reload_lifecycle::Config&,const Policy&) noexcept;
bool Register(const CheckpointLoadWorkerFrame*) noexcept;
const Report& Snapshot() noexcept;
}
