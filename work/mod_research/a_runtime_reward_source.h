#pragma once
#include "a_reward_save_owner.h"
// Local-only source builder. No process discovery, publication or remote pointers.
namespace a_runtime_reward_source {
namespace ar=a_reward_save_owner;namespace ph=checkpoint_planning_hold;
struct Actor {unsigned force=0,ruler=0,district=0;};
struct Config {
 uintptr_t base=0,root=0,world=0,user=0;ph::Binding binding{};
 unsigned year=0,month=0,day=0,viewer=0;Actor actors[2]{};
 bool(*sample_input)(void*,checkpoint_native_input_pending::Config&)=nullptr;void*input_context=nullptr;
};
class SourceProvider final {
public:
 bool Initialize(const Config&)noexcept;
 bool Capture(uintptr_t user,unsigned actor,ar::Source&)noexcept;
 static bool Sample(void*,uintptr_t,unsigned,ar::Source&)noexcept;
 bool Failed()const noexcept;
private:
 Config c_{};volatile LONG state_=0;uintptr_t raw_=0;volatile LONG thread_=0;
 bool identity()const noexcept;
 static bool Validate(void*,const ph::Binding&)noexcept;
};
}
