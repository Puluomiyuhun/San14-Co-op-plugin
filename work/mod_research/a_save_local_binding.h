#pragma once
#include "checkpoint_native_input_pending_adapter.h"
// Current-process read-only span source for A Owner/Gate. Initialize before
// publishing consumers and retain it. No native calls or idle/permit booleans.
namespace a_save_local_binding {
namespace pending=checkpoint_native_input_pending;
struct Config {
 pending::Binding binding{};
 uintptr_t base=0,root=0,world=0,cache=0,states[5]{};
};
class Sampler final {
public:
 bool Initialize(const Config&)noexcept;
 bool Capture(pending::Config&)const noexcept;
 static bool Sample(void*,pending::Config&)noexcept;
private:
 volatile LONG initialized_=0;Config c_{};
};
}
