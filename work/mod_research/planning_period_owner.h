#pragma once
#include "planning_input_interlock.h"
// Logical periods on the SAME retained physical Owner/root/world/User only.
// No hook reset, simulation call, world replacement or full-input authority.
namespace planning_period_owner {
namespace ar=a_reward_save_owner;
struct Date {unsigned short year=0;unsigned char month=0,day=0,viewer=0;};
struct Receipt {
 std::uint64_t serial=0;ar::ph::Binding binding{};Date date{};
 ar::Report reward{};std::uint64_t gateRevision=0,observation=0;
};
struct Report {
 bool tracked=false,retired=false;DWORD thread=0;std::uint64_t serial=0,retiredCount=0;
 ar::ph::Binding binding{};Date date{};ar::Report reward{};
 bool fullInputHeld=false,saveAuthorized=false,simulationPermit=false,worldReplacement=false;
};
// Called by the explicit interlock implementation successor. One Controller
// may claim each logical period; a second object cannot reset observation state.
bool ClaimController(a_save_user_owner::Owner&,const ar::ph::Binding&,const void*)noexcept;
// Reads the logical lifecycle before ANY multi-step Controller mutation. A
// retired Controller must not release Gate then fail its old reward binding.
bool CurrentController(a_save_user_owner::Owner&,const ar::ph::Binding&,const void*,bool unclaimed=false)noexcept;
bool Retire(a_save_user_owner::Owner&,a_save_upstream_gate::Owner&,
            planning_input_interlock::Controller&,const ar::ph::Binding&,Receipt&)noexcept;
bool Rebind(a_save_user_owner::Owner&,a_save_upstream_gate::Owner&,
            const ar::Config&,std::uint64_t retiredSerial)noexcept;
bool Snapshot(a_save_user_owner::Owner&,Report&)noexcept;
bool Historical(a_save_user_owner::Owner&,std::uint64_t serial,Receipt&)noexcept;
}
