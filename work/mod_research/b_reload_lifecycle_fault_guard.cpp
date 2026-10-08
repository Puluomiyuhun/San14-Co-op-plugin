#include "b_reload_lifecycle_fault_guard.h"
#include <cstring>
namespace b_reload_lifecycle_fault_guard {
bool Gate::Initialize(tp::Provider&p,std::uint64_t previous,ns::Session&s,ad::Controller&a)noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=false;__try{if(p_||r_.initialized||!previous)__leave;tp::Report t{};ns::Report n{};ad::Report c{};
 if(!p.Snapshot(previous,t)||!a.Snapshot(c))__leave;s.Snapshot(n);if(t.generation!=previous||c.generation!=previous||n.attempt!=t.attempt)__leave;
 p_=&p;s_=&s;a_=&a;r_.thread=GetCurrentThreadId();r_.previous=previous;r_.initialized=true;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Gate::RegisterAndOpen(const tp::Config&next)noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=false;__try {
 if(!r_.initialized||r_.finished||GetCurrentThreadId()!=r_.thread)__leave;
 ++r_.attempts;r_.finished=true;r_.next=next.generation.callbacks.id;
 tp::Report t{};ns::Report n{};ad::Report c{};b_reload_root_activation::Report root{};
 if(!p_->Snapshot(r_.previous,t)||!a_->Snapshot(c)||!b_reload_root_activation::Snapshot(root)){r_.error=Error::Config;__leave;}s_->Snapshot(n);
 r_.inputError=c.error;r_.providerError=t.error;r_.sessionError=n.error;
 if(c.error!=ad::Error::None||c.blocked||c.stopped||c.active||c.route_active||c.route_faults||c.route_abnormal||c.route_started!=c.route_finished||c.prefetch.restore_uncertain){r_.error=Error::Input;__leave;}
 if(n.error||n.dispatchAbnormal||n.activeDispatch||n.activeWorker||n.activeRead){r_.error=Error::Session;__leave;}
 // StopRequested alone is not failure: completed Session retains observers after Stop.
 unsigned matched=0;bool rootClean=root.error==b_reload_root_activation::Error::None&&!root.uncertain&&root.gateEntries==root.gateFinishes;
 for(unsigned i=0;i<root.taskCount;++i){const auto&q=root.tasks[i];if(q.binding.generation!=r_.previous)continue;
  ++matched;rootClean=rootClean&&q.binding.attempt==t.attempt&&q.binding.epoch==t.epoch&&q.ports.generation==t.generation&&q.ports.attempt==t.attempt&&q.ports.epoch==t.epoch;
  if(q.abnormal)++r_.abnormalTasks;rootClean=rootClean&&q.finished&&!q.abnormal&&!q.ports.uncertain&&q.ports.restored&&q.ports.error==b_reload_root_worker_ports::Error::None;
 }
 if(!matched||!rootClean){r_.error=Error::Root;__leave;}
 if(t.error!=tp::Error::None||!t.closed||t.windowOpen||!t.threeJoins||!t.planning||!n.bytes.observedWorkerAndBytes||!n.lifecycle.receiptReady||!n.identity.receiptReady){r_.error=Error::Incomplete;__leave;}
 if(r_.previous==UINT64_MAX||next.generation.callbacks.id!=r_.previous+1||next.generation.attempt<=t.attempt||next.generation.epoch<=t.epoch||!next.session||next.session==s_){r_.error=Error::Next;__leave;}
 ++r_.registerCalls;if(!p_->Register(next)){r_.error=Error::Register;__leave;}r_.registered=true;
 ++r_.openCalls;if(!p_->OpenWindow(next.generation.callbacks.id)){r_.error=Error::Open;r_.uncertain=true;__leave;}r_.opened=true;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Gate::Snapshot(Report&out)noexcept {AcquireSRWLockShared(&lock_);out=r_;ReleaseSRWLockShared(&lock_);}
}
