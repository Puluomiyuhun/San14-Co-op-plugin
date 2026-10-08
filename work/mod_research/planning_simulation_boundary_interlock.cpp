// Explicit observation-sealing successor. Other Controller behavior is frozen.
#include "planning_input_interlock.h"
#include "planning_period_owner.h"
#include "planning_checkpoint_save.h"
#include "planning_simulation_boundary.h"
#include <initializer_list>
namespace planning_input_interlock {
void Controller::clearObservation()noexcept {r_.observed=false;r_.coverage=0;r_.userStartedDelta=r_.userReturnedDelta=r_.userFinallyDelta=r_.heldDelta=r_.gameFinallyDelta=r_.uiDelta=r_.panelDelta=0;}
void Controller::fail(Error e)noexcept {if(r_.error==Error::None)r_.error=e;r_.uncertain=true;r_.observing=false;clearObservation();}
bool Controller::read(Report&x)noexcept {
 if(!c_.owner||!c_.gate||!c_.gate->MatchesOwner(c_.owner,c_.binding.native,c_.base,c_.root,c_.world))return false;
 if(!planning_period_owner::CurrentController(*c_.owner,c_.binding,this,!r_.initialized))return false;
 __try {const auto w=reinterpret_cast<const unsigned char*>(c_.world);if(r_.initialized&&(!([](a_save_user_owner::Owner&o,const void*c,const unsigned char*v){planning_period_owner::Date d{};return planning_simulation_boundary::detail::EffectiveDate(o,c,d)&&d.year==*reinterpret_cast<const unsigned short*>(v+0x34)&&d.month==v[0x36]&&d.day==v[0x37]&&d.viewer==v[0x3A];})(*c_.owner,this,w)))return false;}
 __except(EXCEPTION_EXECUTE_HANDLER){return false;}
 if(!ar::Snapshot(*c_.owner,x.reward))return false;c_.owner->Snapshot(x.owner);c_.gate->Snapshot(x.gate);
 __try {for(const auto*h:{&x.owner.hooks,&x.gate.hooks}){if(!h->initialized||h->count!=2||h->exceptionCode)return false;for(unsigned i=0;i<2;++i){const auto&e=h->entries[i];if(!e.known||!e.published||e.error||!e.binding.slot||!e.binding.hook||*e.binding.slot!=e.binding.hook)return false;}}}
 __except(EXCEPTION_EXECUTE_HANDLER){return false;}return true;
}
bool Controller::clean(const Report&x)const noexcept {
 return x.reward.bound&&x.reward.error==ar::Error::None&&!x.reward.uncertain&&!x.reward.active&&!x.reward.queued&&
 x.owner.armed&&!x.owner.stopped&&x.owner.error==a_save_user_owner::Error::None&&!x.owner.save_lane&&!x.owner.user_hold_requested&&!x.owner.active_scopes&&!x.owner.bridges[0].active&&!x.owner.bridges[1].active&&
 x.gate.armed&&!x.gate.stopped&&x.gate.error==ag::Error::None&&!x.gate.active&&!x.gate.bridges[0].active&&!x.gate.bridges[1].active&&!x.gate.bridges[2].active;
}
bool Controller::Initialize(const Config&c)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {if(r_.initialized||c_.owner||!c.owner||!c.gate||!c.base||!c.root||!c.world)__leave;c_=c;
  if(!read(r_)||!clean(r_)||!planning_period_owner::ClaimController(*c.owner,c.binding,this)){r_.error=Error::Config;__leave;}
  __try {const auto w=reinterpret_cast<const unsigned char*>(c_.world);year_=*reinterpret_cast<const unsigned short*>(w+0x34);month_=w[0x36];day_=w[0x37];viewer_=w[0x3A];}
  __except(EXCEPTION_EXECUTE_HANDLER){r_.error=Error::Identity;__leave;}
  r_.revision=r_.reward.readyRevision;r_.requested=r_.reward.readyFence;r_.thread=GetCurrentThreadId();r_.gateRevision=r_.gate.revision;r_.initialized=true;ok=true;
 }__finally {ReleaseSRWLockExclusive(&lock_);}return ok;}
bool Controller::Request(bool value,std::uint64_t revision,bool&duplicate)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;duplicate=false;
 __try {if(planning_simulation_boundary::detail::Held()||!r_.initialized||r_.error!=Error::None||r_.observing||!revision||GetCurrentThreadId()!=r_.thread)__leave;
  if(!read(r_)){fail(Error::Identity);__leave;}if(!clean(r_))__leave;
  if(revision<r_.revision)__leave;
  if(revision==r_.revision){duplicate=r_.requested==value&&r_.reward.readyRevision==revision&&r_.reward.readyFence==value&&r_.gate.revision==r_.gateRevision&&r_.gate.requested==value;ok=duplicate;__leave;}
  if(r_.gate.revision!=r_.gateRevision||r_.reward.readyRevision!=r_.revision||r_.reward.readyFence!=r_.requested){fail(Error::Conflict);__leave;}
  clearObservation();
  // Closing first fences User; opening first releases Gate while User remains
  // fenced. Partial failure never pretends rollback or successful observation.
  if(value){if(!ar::ReadyFence(*c_.owner,c_.binding,true,revision))__leave;
   if(!c_.gate->Hold(c_.binding.native,true,r_.gateRevision+1)){fail(Error::PartialRequest);__leave;}}
  else {if(!c_.gate->Hold(c_.binding.native,false,r_.gateRevision+1)){fail(Error::PartialRequest);__leave;}
   if(!ar::ReadyFence(*c_.owner,c_.binding,false,revision)){fail(Error::PartialRequest);__leave;}}
  ++r_.gateRevision;r_.revision=revision;r_.requested=value;if(!read(r_)||!clean(r_)){fail(Error::PartialRequest);__leave;}ok=true;
 }__finally {ReleaseSRWLockExclusive(&lock_);}return ok;}
bool Controller::BeginObservation(std::uint64_t revision)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {if(!r_.initialized||r_.error!=Error::None||r_.observing||GetCurrentThreadId()!=r_.thread)__leave;clearObservation();
  if(!revision||revision!=r_.revision||!r_.requested)__leave;
  if(!read(r_)){fail(Error::Identity);__leave;}if(!clean(r_)||r_.reward.readyRevision!=revision||!r_.reward.readyFence||r_.gate.revision!=r_.gateRevision||!r_.gate.requested){fail(Error::Conflict);__leave;}
  before_=r_;r_.observing=true;ok=true;
 }__finally {ReleaseSRWLockExclusive(&lock_);}return ok;}
bool Controller::EndObservation(std::uint64_t revision)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {if(!r_.initialized||r_.error!=Error::None||!r_.observing||GetCurrentThreadId()!=r_.thread)__leave;r_.observing=false;
  if(revision!=r_.revision||!read(r_)||!clean(r_)||r_.reward.readyRevision!=revision||!r_.reward.readyFence||r_.gate.revision!=r_.gateRevision||!r_.gate.requested){fail(Error::Observation);__leave;}
  auto delta=[](std::uint64_t a,std::uint64_t b){return a>=b?a-b:UINT64_MAX;};
  const auto&u=r_.owner.bridges[0];const auto&v=before_.owner.bridges[0];
  r_.userStartedDelta=delta(u.native_started,v.native_started);r_.userReturnedDelta=delta(u.native_returned,v.native_returned);r_.userFinallyDelta=delta(u.finally_calls,v.finally_calls);r_.heldDelta=delta(r_.owner.held_scopes,before_.owner.held_scopes);
  r_.gameFinallyDelta=delta(r_.gate.bridges[0].finally_calls,before_.gate.bridges[0].finally_calls);r_.uiDelta=delta(r_.gate.uiSuppressed,before_.gate.uiSuppressed);r_.panelDelta=delta(r_.gate.panelSuppressed,before_.gate.panelSuppressed);
  bool healthy=true;for(unsigned i=0;i<3;++i)healthy=healthy&&r_.gate.bridges[i].abnormal_exits==before_.gate.bridges[i].abnormal_exits&&r_.gate.bridges[i].cleanup_faults==before_.gate.bridges[i].cleanup_faults;
  if(r_.userStartedDelta||r_.userReturnedDelta||r_.userFinallyDelta!=1||r_.heldDelta!=1||r_.gameFinallyDelta!=1||r_.uiDelta!=1||r_.panelDelta!=1||!r_.gate.coveredGlobalUiHeld||!r_.gate.coveredPanelHeld||!healthy||u.abnormal_exits!=v.abnormal_exits||u.cleanup_faults!=v.cleanup_faults||r_.gate.uiForwarded!=before_.gate.uiForwarded||r_.gate.panelForwarded!=before_.gate.panelForwarded){fail(Error::Observation);__leave;}
  r_.observed=true;r_.coverage=BoundedCoverage;++r_.observation;
  if(!planning_checkpoint_save::detail::RecordObservation(this,c_.owner,c_.gate,r_)){fail(Error::Observation);__leave;}ok=true;
 }__finally {ReleaseSRWLockExclusive(&lock_);}return ok;}
void Controller::Snapshot(Report&out)noexcept {AcquireSRWLockExclusive(&lock_);__try {
 if(r_.initialized&&(!read(r_)||!clean(r_)||r_.reward.readyRevision!=r_.revision||r_.reward.readyFence!=r_.requested||r_.gate.revision!=r_.gateRevision))clearObservation();out=r_;
 }__finally {ReleaseSRWLockExclusive(&lock_);}}
bool Controller::AuthorizeFullBoundary(std::uint64_t revision,unsigned*missing)noexcept {(void)revision;if(missing)*missing=Unresolved;return false;}
}
