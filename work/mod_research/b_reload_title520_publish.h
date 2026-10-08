#pragma once
#include "checkpoint_task_native_start.h"
#include "b_reload_title520_router.h"
namespace b_reload_title520_publish {
using Error=checkpoint_task_native_start::Error;
using Report=checkpoint_task_native_start::Report;
struct Config {
 uintptr_t base=0;std::uint64_t generation=0;
 checkpoint_native_task_provider::Provider* provider=nullptr;
 b_reload_title520_router::Router* activation=nullptr;
 bool publishRunner=false;
};
class Publisher final {
public:
 bool Initialize(const Config&) noexcept;
 // Called only after the Load.Finalize scope delivered actual 834B60 CONTEXT.
 bool OnStart(const checkpoint_native_task_provider::Capture&) noexcept;
 void Stop() noexcept;
 bool Snapshot(Report&) noexcept;
private:void* state_=nullptr;
};
}
