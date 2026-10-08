#pragma once
#include "planning_period_owner.h"
// Trusted local host API for one CURRENT-DATE checkpoint under an observed
// Controller hold. Replaces Owner/Gate implementations; never link predecessors.
// Not a Room authority proof, full input/writer lock, or production Save permit.
namespace planning_checkpoint_save {
struct Evidence {
 checkpoint_planning_hold::Binding binding{};
 planning_period_owner::Date date{};
 std::uint64_t periodSerial=0,readyRevision=0,gateRevision=0,observation=0,cut=0;
};
bool Submit(a_save_user_owner::Owner&,a_save_upstream_gate::Owner&,
            planning_input_interlock::Controller&,const Evidence&,
            const checkpoint_fresh_save::Request&)noexcept;
// Copy succeeds once, only after the original Driver/report/storage completion.
// It releases this Save reservation, never Ready or the Gate's requested hold.
bool Copy(a_save_user_owner::Owner&,a_save_upstream_gate::Owner&,
          planning_input_interlock::Controller&,const Evidence&,std::uint64_t generation,
          checkpoint_fresh_save::Artifact&)noexcept;
namespace detail {
enum class Action:unsigned {Submit,Copy};
struct Call {
 Action action=Action::Submit;a_save_user_owner::Owner*owner=nullptr;
 a_save_upstream_gate::Owner*gate=nullptr;planning_input_interlock::Controller*controller=nullptr;
 Evidence evidence{};planning_input_interlock::Report observed{};
 checkpoint_fresh_save::Request request{};std::uint64_t generation=0;
 checkpoint_fresh_save::Artifact*artifact=nullptr;
};
using Invoke=bool(*)(void*,const Call&)noexcept;
// Internal links between these exact replacement translation units. Not IPC.
bool RegisterOwner(a_save_user_owner::Owner*,void*,Invoke)noexcept;
bool RegisterGate(a_save_upstream_gate::Owner*,void*,Invoke)noexcept;
bool InvokeOwner(const Call&)noexcept;
// Only called by the replacement Controller after its real delta checks pass.
bool RecordObservation(planning_input_interlock::Controller*,a_save_user_owner::Owner*,
                       a_save_upstream_gate::Owner*,const planning_input_interlock::Report&)noexcept;
bool Same(const Evidence&,const Evidence&)noexcept;
bool SameStats(const CheckpointLoadWorkerBridgeStats&,const CheckpointLoadWorkerBridgeStats&)noexcept;
}
}
