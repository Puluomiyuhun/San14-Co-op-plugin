#pragma once
#include "planning_checkpoint_save.h"
// Trusted synchronous host boundary, not an engine scheduler or simulation permit.
namespace planning_simulation_boundary {
using Run=bool(*)(void*)noexcept;
enum class Phase:unsigned {Idle,Running,Checkpoint,Failed};
struct Report {Phase phase=Phase::Idle;DWORD thread=0;planning_checkpoint_save::Evidence start{};
 planning_period_owner::Date checkpointDate{};std::uint64_t entered=0,returned=0,finallyCount=0;
 bool readyHeld=false,actualSimulation=false,simulationPermit=false,fullInputHeld=false;};
bool Execute(a_save_user_owner::Owner&,a_save_upstream_gate::Owner&,planning_input_interlock::Controller&,
 const planning_checkpoint_save::Evidence&,Run,void*)noexcept;
bool Snapshot(Report&)noexcept;
namespace detail {
struct Call {bool begin=true;planning_checkpoint_save::detail::Call checkpoint{};};
using Invoke=bool(*)(void*,const Call&)noexcept;
bool RegisterOwner(a_save_user_owner::Owner*,void*,Invoke)noexcept;
bool RegisterGate(a_save_upstream_gate::Owner*,void*,Invoke)noexcept;
bool InvokeOwner(const Call&)noexcept;
bool Held()noexcept;
void Rebound()noexcept; // only successful replacement lifecycle Rebind calls this
bool EffectiveDate(a_save_user_owner::Owner&,const void*,planning_period_owner::Date&)noexcept;
}
}
