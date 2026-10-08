#include "planning_simulation_boundary.h"
namespace planning_checkpoint_save::detail {bool LoadObservation(const Call&,planning_input_interlock::Report&)noexcept;}
namespace planning_simulation_boundary {
namespace {SRWLOCK lock=SRWLOCK_INIT;Report state{};volatile LONG held=0;
 a_save_user_owner::Owner*owner=nullptr;a_save_upstream_gate::Owner*gate=nullptr;
 void*oc=nullptr,*gc=nullptr;detail::Invoke of=nullptr,gf=nullptr;}
namespace detail {
bool RegisterOwner(a_save_user_owner::Owner*o,void*c,Invoke f)noexcept {if(owner||!o||!c||!f)return false;owner=o;oc=c;of=f;return true;}
bool RegisterGate(a_save_upstream_gate::Owner*g,void*c,Invoke f)noexcept {if(gate||!g||!c||!f)return false;gate=g;gc=c;gf=f;return true;}
bool InvokeOwner(const Call&c)noexcept{return c.checkpoint.owner==owner&&of&&of(oc,c);}
bool Held()noexcept{return InterlockedCompareExchange(&held,0,0)!=0;}
void Rebound()noexcept {AcquireSRWLockExclusive(&lock);if(state.phase==Phase::Checkpoint){state.phase=Phase::Idle;state.readyHeld=false;InterlockedExchange(&held,0);}ReleaseSRWLockExclusive(&lock);}
}
bool Snapshot(Report&out)noexcept {AcquireSRWLockShared(&lock);out=state;ReleaseSRWLockShared(&lock);return true;}
bool Execute(a_save_user_owner::Owner&o,a_save_upstream_gate::Owner&g,planning_input_interlock::Controller&controller,
 const planning_checkpoint_save::Evidence&e,Run run,void*context)noexcept {
 if(&o!=owner||&g!=gate||!gf||!run)return false;
 detail::Call c{};c.checkpoint.owner=&o;c.checkpoint.gate=&g;c.checkpoint.controller=&controller;c.checkpoint.evidence=e;
 controller.Snapshot(c.checkpoint.observed);const auto&r=c.checkpoint.observed;
 if(!r.initialized||r.error!=planning_input_interlock::Error::None||r.uncertain||!r.observed||r.observing||
    r.thread!=GetCurrentThreadId()||r.revision!=e.readyRevision||r.gateRevision!=e.gateRevision||r.observation!=e.observation||
    !planning_checkpoint_save::detail::LoadObservation(c.checkpoint,c.checkpoint.observed))return false;
 AcquireSRWLockExclusive(&lock);if(state.phase!=Phase::Idle){ReleaseSRWLockExclusive(&lock);return false;}
 // Reserve before touching either native owner; a failed admitted attempt is terminal.
 state.phase=Phase::Running;state.thread=GetCurrentThreadId();state.start=e;state.readyHeld=true;InterlockedExchange(&held,1);
 ReleaseSRWLockExclusive(&lock);
 bool begun=gf(gc,c),ran=false,ok=false;
 if(begun){AcquireSRWLockExclusive(&lock);++state.entered;ReleaseSRWLockExclusive(&lock);
  __try {__try {ran=run(context);AcquireSRWLockExclusive(&lock);++state.returned;ReleaseSRWLockExclusive(&lock);}
   __except(EXCEPTION_EXECUTE_HANDLER){ran=false;}}
  __finally {AcquireSRWLockExclusive(&lock);++state.finallyCount;ReleaseSRWLockExclusive(&lock);}
  c.begin=false;if(ran)ok=gf(gc,c);
 }
 if(!ok)o.Stop();
 planning_period_owner::Report p{};planning_period_owner::Snapshot(o,p);
 AcquireSRWLockExclusive(&lock);state.phase=ok?Phase::Checkpoint:Phase::Failed;if(ok)state.checkpointDate=p.date;ReleaseSRWLockExclusive(&lock);
 return ok;
}
}
