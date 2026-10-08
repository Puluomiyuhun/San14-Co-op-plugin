#pragma once
#include "planning_input_interlock_gate.h"
#include "a_reward_save_owner.h"
// One retained controller for the existing User/Save Owner and its exact Gate.
// No hooks are installed here. Call only on the trusted owner execution thread.
namespace planning_input_interlock {
namespace ar=a_reward_save_owner;namespace ag=a_save_upstream_gate;
enum Coverage:unsigned {User=1,GlobalUi=2,Panel=4};
enum Missing:unsigned {WindowMessages=1,RootConversion=2,DeviceCaches=4,ExternalConsumers=8,BackgroundWriters=16};
constexpr unsigned BoundedCoverage=User|GlobalUi|Panel;
constexpr unsigned Unresolved=WindowMessages|RootConversion|DeviceCaches|ExternalConsumers|BackgroundWriters;
enum class Error:unsigned {None,Config,Thread,Identity,Conflict,PartialRequest,Observation};
struct Config {a_save_user_owner::Owner*owner=nullptr;ag::Owner*gate=nullptr;ar::ph::Binding binding{};uintptr_t base=0,root=0,world=0;};
struct Report {
 Error error=Error::None;DWORD thread=0;std::uint64_t revision=0,gateRevision=0,observation=0;
 bool initialized=false,requested=false,observing=false,observed=false,uncertain=false;
 unsigned coverage=0,missing=Unresolved;std::uint64_t userStartedDelta=0,userReturnedDelta=0,userFinallyDelta=0,heldDelta=0,gameFinallyDelta=0,uiDelta=0,panelDelta=0;
 bool allInputHeld=false,roomReady=false,saveAuthorized=false,nativeGameplayEnabled=false;
 ar::Report reward{};a_save_user_owner::Report owner{};ag::Report gate{};
};
class Controller final {
public:
 bool Initialize(const Config&)noexcept;
 bool Request(bool value,std::uint64_t revision,bool&duplicate)noexcept;
 // A fresh window, followed by actual published Game and User calls. No setters
 // or caller-supplied counters can manufacture the successful observation.
 bool BeginObservation(std::uint64_t revision)noexcept;
 bool EndObservation(std::uint64_t revision)noexcept;
 void Snapshot(Report&)noexcept;
 // This bounded implementation NEVER issues a full-input/save/simulation permit.
 bool AuthorizeFullBoundary(std::uint64_t revision,unsigned*missing=nullptr)noexcept;
private:
 SRWLOCK lock_=SRWLOCK_INIT;Config c_{};Report r_{};Report before_{};unsigned short year_=0;unsigned char month_=0,day_=0,viewer_=0;
 bool read(Report&)noexcept;bool clean(const Report&)const noexcept;
 void clearObservation()noexcept;void fail(Error)noexcept;
};
}
