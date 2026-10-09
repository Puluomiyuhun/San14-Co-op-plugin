#pragma once
#include "checkpoint_native_input_core.h"
#include <array>

// Local input policy only. It never sets the reward Owner's ReadyFence: that
// predecessor also rejects already-authorized remote commands.
namespace player_input_policy {
enum class Phase:unsigned {Planning,Save,Load,EventWait,Running,Terminal};
struct Binding {
 std::array<unsigned char,16> room{},attachment{},epoch{};
 std::uint64_t period=0;unsigned seat=0;
};
struct State {Phase phase=Phase::Terminal;bool localReady=false;};
bool Valid(const Binding&)noexcept;
bool Same(const Binding&,const Binding&)noexcept;
bool Same(State,State)noexcept;
bool Valid(State)noexcept;
bool Hold(State)noexcept;
// Message reception is independent of command execution. This policy cannot
// authorize native work; its planning predicate is only an additional veto.
bool MayReceiveRemote(State)noexcept;
bool MayExecuteRemote(State)noexcept;
checkpoint_native_input::MessageDecision Decide(const checkpoint_native_input::Message&,
                                                uintptr_t window,State)noexcept;
}
