#pragma once
#include "checkpoint_reward_owned_replay.h"
#include "checkpoint_persistent_bridge.h"
namespace checkpoint_planning_dispatcher {
namespace ph=checkpoint_planning_hold;namespace rw=checkpoint_reward_owned_replay;
using Original=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
enum class Mode:unsigned {ForwardOnly,UserSubsetSkip};
enum class Action:unsigned {Hold,Drain,Release};
enum class Error:unsigned {None,Config,Binding,Stale,Queue,Scope,Overlap,Source,Pending,Reward,Exception,Cleanup,Stopped};
struct Source {ph::Config admission{};rw::Config reward{};};
struct Config {
 ph::Binding binding{};Original original=nullptr;Mode mode=Mode::ForwardOnly;
 // These must be the retained physical bridge's functions, not approval booleans.
 int(*claim)(const CheckpointLoadWorkerFrame*,std::uint64_t)noexcept=nullptr;
 int(*current_owner)(CheckpointLoadWorkerOwner*)noexcept=nullptr;
 // Produces fresh concrete pointer/buffer configuration on this invocation's
 // actual thread. Host pins image/world throughout; never a full UI hold grant.
 bool(*sample)(void*,std::uintptr_t user,Source&)=nullptr;void*context=nullptr;
};
struct Report {
 Error error=Error::None;std::uint64_t action=0,revision=0,entries=0,active=0,finally_calls=0;
 std::uint64_t forwarded=0,body_returned=0,suppressed=0,abnormal=0,queued_sequence=0,completed_sequence=0;
 std::uint64_t reward_scopes=0,reward_completed=0,reward_destroyed=0,context_destroyed=0,hold_call=0,hold_revision=0;
 DWORD last_executor_thread=0;bool gate_requested=false,drain_requested=false,release_pending=false,stopped=false;
 bool covered_user_scope_held=false,covered_user_scope_drained=false,full_input_hold=false,room_ack_eligible=false;
 bool installed_in_game=false,all_game_threads_paused=false;
 rw::Report reward{};ph::Report admission{};
};
class Dispatcher final {
public:
 Dispatcher();~Dispatcher();Dispatcher(const Dispatcher&)=delete;Dispatcher&operator=(const Dispatcher&)=delete;
 bool Initialize(const Config&)noexcept;
 bool Request(const ph::Binding&,Action,std::uint64_t action)noexcept;
 bool Submit(const ph::Binding&,std::uint64_t sequence,const rw::Command&)noexcept;
 void Disconnect()noexcept;
 Report Snapshot()noexcept;
 void Before(const CheckpointLoadWorkerFrame&)noexcept;
 std::uint64_t Invoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
 void Finally(const CheckpointLoadWorkerFrame&,const CheckpointLoadWorkerExit&)noexcept;
 // AFTER may observe wrapper return; it is not evidence User body executed.
 static void BeforeCallback(const CheckpointLoadWorkerFrame*,void*)noexcept;
 static void FinallyCallback(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*)noexcept;
private:struct Impl;Impl*p_=nullptr;
};
// Resident dispatcher/config/source/code lifetime: stop all physical bridge
// callbacks before destruction. Disconnect revokes commands, not lifetime refs.
}
