#include "checkpoint_planning_dispatcher.h"
#include <new>
#include <cstring>
#include <exception>
#include "reward_probe_fingerprints.h"
namespace checkpoint_planning_dispatcher {
namespace {
struct Lock {SRWLOCK&l;explicit Lock(SRWLOCK&v):l(v){AcquireSRWLockExclusive(&l);}~Lock(){ReleaseSRWLockExclusive(&l);}};
bool same(const ph::Binding&a,const ph::Binding&b){return a.native.attempt==b.native.attempt&&a.native.attachment==b.native.attachment&&a.native.owner_generation==b.native.owner_generation&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
struct Scope {void*owner=nullptr;Scope*previous=nullptr;std::uint64_t call=0,revision=0;DWORD thread=0;bool claimed=false,suppressed=false,returned=false,entered=false;};
thread_local Scope*top=nullptr;
}
struct Dispatcher::Impl {
 SRWLOCK lock=SRWLOCK_INIT;Config config{};Report report{};bool initialized=false,queued=false;std::uint64_t lastSubmitted=0;rw::Command command{};
 rw::Owner*running=nullptr;ph::Context*context=nullptr;
 void revoke(){queued=false;report.queued_sequence=0;if(running)RewardOwnedCancel(running);}
 void fault(Error e){report.error=e;report.stopped=true;report.gate_requested=true;report.covered_user_scope_held=false;report.covered_user_scope_drained=false;revoke();}
 bool source(std::uintptr_t user,Source&s){if(!config.sample(config.context,user,s)||!same(s.admission.binding,config.binding)||!same(s.reward.binding,config.binding)||s.reward.user!=user||s.admission.pending.states[4]!=user||s.reward.base!=s.admission.pending.profile_base)return false;
  #ifndef CHECKPOINT_PLANNING_DISPATCHER_OWNED_FIXTURE
  if(reinterpret_cast<std::uintptr_t>(config.original)!=s.reward.base+0x3F9B00||reinterpret_cast<std::uintptr_t>(s.admission.reward)!=s.reward.base+0x1D6DA0)return false;
  for(const auto&f:REWARD_FINGERPRINTS)if(f.rva==0x3F9B00&&std::memcmp(reinterpret_cast<void*>(s.reward.base+f.rva),f.bytes,sizeof f.bytes))return false;
#endif
  ph::pd::Adapter pending;if(pending.Bind(s.admission.pending)!=ph::pd::Error::None)return false;auto r=pending.InspectCurrent(config.binding.native);return r.error==ph::pd::Error::None&&r.decision==ph::pd::Decision::QuiescentObserved&&r.user_phase==2&&r.stack_count==5;
 }
 bool validScope(Scope*s){CheckpointLoadWorkerOwner owner{};return s&&s->owner==this&&s->claimed&&s->thread==GetCurrentThreadId()&&config.current_owner(&owner)&&owner.token==config.binding.native.owner_generation&&owner.slot==0&&owner.call_id==s->call&&owner.thread_id==s->thread&&owner.current_depth==owner.owner_depth;}
 void pump(std::uintptr_t user){
  rw::Command job{};std::uint64_t seq=0,revision=0;{Lock l(lock);if(report.stopped||!queued)return;job=command;seq=report.queued_sequence;revision=report.revision;queued=false;report.queued_sequence=0;}
  Source fresh{};if(!source(user,fresh)){Lock l(lock);fault(Error::Source);return;}
  auto*owner=RewardOwnedCreate(&fresh.reward);if(!owner){Lock l(lock);fault(Error::Reward);return;}
  fresh.admission.capture_owned_command=&RewardOwnedCapture;fresh.admission.replay_source_context=owner;
  auto*hold=PlanningHoldCreate(&fresh.admission);bool published=false;
  if(hold){Lock l(lock);if(!report.stopped&&report.revision==revision){running=owner;context=hold;published=true;++report.reward_scopes;report.last_executor_thread=GetCurrentThreadId();}}
  bool success=false;std::exception_ptr failure;
  try{if(published){
    // Real entry gate closure, deliberately NOT a fabricated menu-prefetch or
    // paired-body Hold receipt. Remote tickets are valid in HoldPending.
    if(PlanningHoldRequest(hold,&config.binding,unsigned(ph::Operation::Hold),1)==unsigned(ph::Status::Ok)&&RewardOwnedPrepare(owner,&job))success=RewardOwnedExecute(owner,hold,1)==1;
   }}catch(...){failure=std::current_exception();}
  rw::Report reward{};RewardOwnedSnapshot(owner,&reward);ph::Report admission{};if(hold)PlanningHoldSnapshot(hold,&admission);
  {Lock l(lock);if(published){running=nullptr;context=nullptr;}report.reward=reward;report.admission=admission;}
  const bool released=RewardOwnedDestroy(owner);if(hold)PlanningHoldDestroy(hold);
  {Lock l(lock);if(released)++report.reward_destroyed;if(hold)++report.context_destroyed;if(!released)fault(Error::Cleanup);else if(!success)fault(failure?Error::Exception:Error::Reward);else{++report.reward_completed;report.completed_sequence=seq;}}
  // On uncertain cleanup Owner is deliberately retained. No dangling Context
  // references remain (synchronous callbacks returned); world owner must stop.
  if(failure)std::rethrow_exception(failure);
 }
};
Dispatcher::Dispatcher():p_(new(std::nothrow)Impl){}
Dispatcher::~Dispatcher(){delete p_;}
bool Dispatcher::Initialize(const Config&c)noexcept{if(!p_||p_->initialized||!c.original||!c.claim||!c.current_owner||!c.sample||!c.binding.native.owner_generation||!c.binding.period||!c.binding.epoch||(c.mode!=Mode::ForwardOnly&&c.mode!=Mode::UserSubsetSkip))return false;p_->config=c;p_->initialized=true;return true;}
bool Dispatcher::Request(const ph::Binding&b,Action action,std::uint64_t n)noexcept{if(!p_)return false;auto&s=*p_;Lock l(s.lock);auto&r=s.report;if(!s.initialized||!same(b,s.config.binding)||r.stopped||!n||n<=r.action)return false;
 if(action==Action::Hold){if(r.gate_requested||r.release_pending)return false;r.gate_requested=true;r.drain_requested=false;}
 else if(action==Action::Drain){if(!r.gate_requested||r.release_pending)return false;r.drain_requested=true;}
 else if(action==Action::Release){if(!r.gate_requested)return false;r.release_pending=true;r.drain_requested=false;s.revoke();}
 else return false;r.action=n;++r.revision;r.covered_user_scope_held=false;r.covered_user_scope_drained=false;return true;}
bool Dispatcher::Submit(const ph::Binding&b,std::uint64_t seq,const rw::Command&c)noexcept{if(!p_)return false;auto&s=*p_;Lock l(s.lock);if(!s.initialized||!same(b,s.config.binding)||s.report.stopped||s.report.release_pending||s.report.drain_requested||s.queued||!seq||seq!=s.lastSubmitted+1)return false;s.command=c;s.queued=true;s.lastSubmitted=seq;s.report.queued_sequence=seq;s.report.covered_user_scope_drained=false;return true;}
void Dispatcher::Disconnect()noexcept{if(p_){Lock l(p_->lock);p_->fault(Error::Stopped);}}
Report Dispatcher::Snapshot()noexcept{if(!p_)return{};Lock l(p_->lock);return p_->report;}
void Dispatcher::Before(const CheckpointLoadWorkerFrame&f)noexcept{if(!p_||!p_->initialized)return;auto&s=*p_;auto*scope=new(std::nothrow)Scope;if(!scope){Lock l(s.lock);s.fault(Error::Scope);return;}scope->owner=p_;scope->previous=top;scope->call=f.call_id;scope->thread=f.thread_id;top=scope;
 bool eligible=f.slot==0&&f.thread_id==GetCurrentThreadId()&&f.call_id&&f.caller_entry_rsp;
 {Lock l(s.lock);++s.report.entries;++s.report.active;scope->revision=s.report.revision;if(s.report.active!=1){eligible=false;s.fault(Error::Overlap);}s.report.covered_user_scope_drained=false;s.report.covered_user_scope_held=false;}
 CheckpointLoadWorkerOwner prior{};const bool inherited=eligible&&s.config.current_owner(&prior)&&prior.token==s.config.binding.native.owner_generation&&prior.slot==0&&prior.call_id==f.call_id&&prior.thread_id==f.thread_id&&prior.current_depth==prior.owner_depth;
 scope->claimed=eligible&&(inherited||s.config.claim(&f,s.config.binding.native.owner_generation)!=0);if(!scope->claimed){Lock l(s.lock);s.fault(Error::Scope);}
}
std::uint64_t Dispatcher::Invoke(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){if(!p_||!p_->initialized)return 0;auto&s=*p_;auto*scope=top;
 const bool owned=s.validScope(scope)&&!scope->entered;if(owned)scope->entered=true;bool gate=false,stop=false;{Lock l(s.lock);gate=s.report.gate_requested;stop=s.report.stopped;}
 if(!owned){Lock l(s.lock);s.fault(Error::Scope);}
 try{
  if(owned&&gate&&s.config.mode==Mode::UserSubsetSkip){Source sample{};if(s.source(std::uintptr_t(a),sample)){scope->suppressed=true;{Lock l(s.lock);++s.report.suppressed;}if(!stop)s.pump(std::uintptr_t(a));scope->returned=true;return 0;}
   {Lock l(s.lock);s.fault(Error::Pending);} // Forward original state/menu handling.
  }
  {Lock l(s.lock);++s.report.forwarded;}const auto value=s.config.original(a,b,c,d);{Lock l(s.lock);++s.report.body_returned;}
  if(owned&&!gate&&!stop)s.pump(std::uintptr_t(a));if(owned)scope->returned=true;return value;
 }catch(...){Lock l(s.lock);++s.report.abnormal;s.fault(Error::Exception);throw;}
}
void Dispatcher::Finally(const CheckpointLoadWorkerFrame&f,const CheckpointLoadWorkerExit&exit)noexcept{if(!p_)return;auto&s=*p_;auto*scope=top;if(!scope||scope->owner!=p_||scope->call!=f.call_id||scope->thread!=GetCurrentThreadId()){Lock l(s.lock);s.fault(Error::Scope);return;}
 {Lock l(s.lock);auto&r=s.report;++r.finally_calls;if(r.active)--r.active;else s.fault(Error::Scope);if(exit.abnormal||!scope->returned)s.fault(Error::Exception);
  if(!r.stopped&&scope->claimed&&scope->suppressed&&scope->revision==r.revision){r.hold_call=f.call_id;r.hold_revision=r.revision;}
  if(!r.stopped&&r.release_pending&&!r.active){r.release_pending=false;r.gate_requested=false;}
  r.covered_user_scope_held=!r.stopped&&r.gate_requested&&!r.release_pending&&r.hold_revision==r.revision&&r.hold_call&&!r.active;
  r.covered_user_scope_drained=r.covered_user_scope_held&&!s.queued&&!s.running&&!r.active;
 }top=scope->previous;delete scope;
}
void Dispatcher::BeforeCallback(const CheckpointLoadWorkerFrame*f,void*p)noexcept{if(f&&p)static_cast<Dispatcher*>(p)->Before(*f);}
void Dispatcher::FinallyCallback(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*p)noexcept{if(f&&e&&p)static_cast<Dispatcher*>(p)->Finally(*f,*e);}
}
