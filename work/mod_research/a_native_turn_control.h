#pragma once
#include "checkpoint_native_input_pending_adapter.h"
namespace a_save_user_owner {class Owner;}
namespace a_save_upstream_gate {class Owner;}
namespace a_save_parent_adapter {bool CurrentBoundary(uintptr_t)noexcept;}
namespace a_native_turn {
enum class Action:unsigned {Begin,Refresh,End};
struct Call {Action action;std::uint64_t serial;const checkpoint_native_input_pending::Config*input=nullptr;};
// Immutable native module wiring; these callbacks never enter the wire ABI.
namespace detail {
using Invoke=bool(*)(void*,const Call&)noexcept;
bool RegisterOwner(a_save_user_owner::Owner*,void*,Invoke)noexcept;
bool RegisterGate(a_save_upstream_gate::Owner*,void*,Invoke)noexcept;
bool OwnerCall(a_save_user_owner::Owner*,const Call&)noexcept;
}
bool Transition(a_save_upstream_gate::Owner&,const Call&)noexcept;
bool Running()noexcept;
}
