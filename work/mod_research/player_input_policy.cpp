#include "player_input_policy.h"
#include <algorithm>
namespace player_input_policy {
bool Valid(const Binding&b)noexcept {
 auto any=[](const auto&v){return std::any_of(v.begin(),v.end(),[](auto x){return x!=0;});};
 return b.period&&b.seat<2&&any(b.room)&&any(b.attachment)&&any(b.epoch);
}
bool Same(const Binding&a,const Binding&b)noexcept {return a.room==b.room&&a.attachment==b.attachment&&a.epoch==b.epoch&&a.period==b.period&&a.seat==b.seat;}
bool Same(State a,State b)noexcept {return a.phase==b.phase&&a.localReady==b.localReady;}
bool Valid(State s)noexcept {return unsigned(s.phase)<=unsigned(Phase::Terminal)&&(s.phase==Phase::Planning||!s.localReady);}
bool Hold(State s)noexcept {return !Valid(s)||s.phase!=Phase::Planning||s.localReady;}
bool MayReceiveRemote(State s)noexcept {return Valid(s)&&s.phase!=Phase::Terminal;}
bool MayExecuteRemote(State s)noexcept {return Valid(s)&&s.phase==Phase::Planning;}
checkpoint_native_input::MessageDecision Decide(const checkpoint_native_input::Message&m,uintptr_t w,State s)noexcept {
 // Only the predecessor's audited messages are suppressed. Paint/timer/window
 // lifecycle remain available during simulation and loading. No broad Enter or
 // mouse exception is inferred from an unverified report/modal-state label.
 return checkpoint_native_input::ClassifyMessage(m,w,Hold(s));
}
}
