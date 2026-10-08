#include "planning_checkpoint_save.h"
namespace planning_checkpoint_save {
namespace detail {
namespace {a_save_user_owner::Owner*savedOwner=nullptr;a_save_upstream_gate::Owner*savedGate=nullptr;
 void*ownerContext=nullptr,*gateContext=nullptr;Invoke ownerInvoke=nullptr,gateInvoke=nullptr;
 planning_input_interlock::Controller*observedController=nullptr;planning_input_interlock::Report observation{};
 SRWLOCK registry=SRWLOCK_INIT;}
bool RegisterOwner(a_save_user_owner::Owner*o,void*v,Invoke f)noexcept {AcquireSRWLockExclusive(&registry);bool ok=false;
 if(o&&v&&f&&!savedOwner){savedOwner=o;ownerContext=v;ownerInvoke=f;ok=true;}ReleaseSRWLockExclusive(&registry);return ok;}
bool RegisterGate(a_save_upstream_gate::Owner*g,void*v,Invoke f)noexcept {AcquireSRWLockExclusive(&registry);bool ok=false;
 if(g&&v&&f&&!savedGate){savedGate=g;gateContext=v;gateInvoke=f;ok=true;}ReleaseSRWLockExclusive(&registry);return ok;}
bool RecordObservation(planning_input_interlock::Controller*c,a_save_user_owner::Owner*o,a_save_upstream_gate::Owner*g,
 const planning_input_interlock::Report&r)noexcept {AcquireSRWLockExclusive(&registry);bool ok=false;
 if(c&&o==savedOwner&&g==savedGate&&r.thread==GetCurrentThreadId()&&r.observed&&!r.observing&&!r.uncertain&&
    r.error==planning_input_interlock::Error::None&&r.coverage==planning_input_interlock::BoundedCoverage&&r.observation&&
    (c!=observedController||r.observation>observation.observation)){
  observedController=c;observation=r;ok=true;
 }ReleaseSRWLockExclusive(&registry);return ok;
}
bool LoadObservation(const Call&c,planning_input_interlock::Report&out)noexcept {AcquireSRWLockShared(&registry);bool ok=false;
 if(c.owner==savedOwner&&c.gate==savedGate&&c.controller==observedController&&c.evidence.observation==observation.observation&&
    c.evidence.readyRevision==observation.revision&&c.evidence.gateRevision==observation.gateRevision){out=observation;ok=true;}
 ReleaseSRWLockShared(&registry);return ok;
}
bool Same(const Evidence&a,const Evidence&b)noexcept {const auto&x=a.binding;const auto&y=b.binding;
 return x.native.attempt==y.native.attempt&&x.native.attachment==y.native.attachment&&x.native.owner_generation==y.native.owner_generation&&
 x.period==y.period&&x.epoch==y.epoch&&x.room_input_digest==y.room_input_digest&&a.date.year==b.date.year&&a.date.month==b.date.month&&
 a.date.day==b.date.day&&a.date.viewer==b.date.viewer&&a.periodSerial==b.periodSerial&&a.readyRevision==b.readyRevision&&
 a.gateRevision==b.gateRevision&&a.observation==b.observation&&a.cut==b.cut;}
bool SameStats(const CheckpointLoadWorkerBridgeStats&a,const CheckpointLoadWorkerBridgeStats&b)noexcept {
 return a.started==b.started&&a.native_started==b.native_started&&a.native_returned==b.native_returned&&a.before_calls==b.before_calls&&
 a.after_calls==b.after_calls&&a.finally_calls==b.finally_calls&&a.abnormal_exits==b.abnormal_exits&&a.cleanup_faults==b.cleanup_faults&&
 a.scope_claims==b.scope_claims&&a.rejected_claims==b.rejected_claims&&a.active==b.active&&a.configured==b.configured&&a.module_pinned==b.module_pinned;
}
bool InvokeOwner(const Call&c)noexcept {Invoke f=nullptr;void*v=nullptr;AcquireSRWLockShared(&registry);
 if(c.owner==savedOwner){f=ownerInvoke;v=ownerContext;}ReleaseSRWLockShared(&registry);return f&&f(v,c);}
bool run(const Call&c)noexcept {Invoke f=nullptr;void*v=nullptr;AcquireSRWLockShared(&registry);
 if(c.owner==savedOwner&&c.gate==savedGate){f=gateInvoke;v=gateContext;}ReleaseSRWLockShared(&registry);return f&&f(v,c);}
}
bool Submit(a_save_user_owner::Owner&o,a_save_upstream_gate::Owner&g,planning_input_interlock::Controller&controller,
 const Evidence&e,const checkpoint_fresh_save::Request&q)noexcept {
 detail::Call c{};c.owner=&o;c.gate=&g;c.controller=&controller;c.evidence=e;c.request=q;c.generation=q.generation;
 // Controller mutations require its trusted thread. Snapshot may clear stale
 // evidence on another thread, but cannot release the held Gate or Ready.
 controller.Snapshot(c.observed);
 const auto&r=c.observed;
 if(!r.initialized||!r.observed||r.observing||r.uncertain||r.error!=planning_input_interlock::Error::None||
 r.thread!=GetCurrentThreadId()||!r.requested||r.coverage!=planning_input_interlock::BoundedCoverage||
 !e.observation||r.observation!=e.observation||r.revision!=e.readyRevision||r.gateRevision!=e.gateRevision)return false;
 // Snapshot refreshes current fields; admission must use the immutable report
 // captured at successful EndObservation, not those refreshed counters.
 if(!detail::LoadObservation(c,c.observed))return false;
 return detail::run(c);
}
bool Copy(a_save_user_owner::Owner&o,a_save_upstream_gate::Owner&g,planning_input_interlock::Controller&controller,
 const Evidence&e,std::uint64_t generation,checkpoint_fresh_save::Artifact&out)noexcept {
 out={};
 detail::Call c{};c.action=detail::Action::Copy;c.owner=&o;c.gate=&g;c.controller=&controller;c.evidence=e;
 c.generation=generation;c.artifact=&out;const bool ok=detail::run(c);if(!ok)out={};return ok;
}
}
