#pragma once
#include "planning_period_owner.h"
#include <array>
// Trusted local host component. No JSON/TLS endpoint, game installer or permit.
// The caller must authenticate Room/PeriodCoordinator scope before conversion.
namespace planning_period_session {
namespace pp=planning_period_owner;
namespace ar=a_reward_save_owner;
using Id=std::array<unsigned char,16>;
struct Scope {
 Id room{},bindingEpoch{},timelineEpoch{};
 std::array<unsigned char,32> scopeDigest{};
 std::uint64_t period=0,baseSequence=0;
 pp::Date date{}; // viewer is local and independently checked against native.
};
struct Next {Scope scope{};ar::ph::Binding binding{};std::uint64_t retiredSerial=0;};
struct Report {
 bool initialized=false,retired=false,awaitingController=false,uncertain=false;
 DWORD thread=0;Scope scope{};ar::ph::Binding binding{};
 std::uint64_t historyCount=0;
 bool fullInputHeld=false,saveAuthorized=false,simulationPermit=false,worldReplacement=false;
};
bool MakeBinding(const Scope&,const checkpoint_native_input::Binding&,std::uint64_t localEpoch,ar::ph::Binding&)noexcept;
// Retain Session/Owner/Gate/Controllers until process exit. One Session per
// physical Owner bank; no reset or recovery of an ambiguous previous instance.
class Session final {
public:
 Session()=default;~Session()=delete;Session(const Session&)=delete;Session&operator=(const Session&)=delete;
 bool Initialize(a_save_user_owner::Owner&,a_save_upstream_gate::Owner&,
                 planning_input_interlock::Controller&,const Scope&,const ar::Config&,
                 uintptr_t base,uintptr_t root,uintptr_t world)noexcept;
 bool Submit(const Scope&,std::uint64_t sequence,const ar::rw::Command&)noexcept;
 bool Retire(const Scope&,pp::Receipt&)noexcept;
 bool PlanNext(const Scope&,Next&)noexcept;
 bool Rebind(const Next&,const ar::Config&)noexcept;
 bool Adopt(planning_input_interlock::Controller&)noexcept;
 // Configuration/history snapshot only; not fresh native execution evidence.
 void Snapshot(Report&)noexcept;
 bool Historical(std::uint64_t,Scope&,pp::Receipt&)noexcept;
private:
 bool current(pp::Report&)noexcept;
 bool plan(const Scope&,Next&)noexcept;
 SRWLOCK lock_=SRWLOCK_INIT;Report r_{};ar::Config config_{};
 a_save_user_owner::Owner*owner_=nullptr;a_save_upstream_gate::Owner*gate_=nullptr;
 planning_input_interlock::Controller*controller_=nullptr;
 struct History {Scope scope{};pp::Receipt receipt{};}history_[16]{};
};
}
