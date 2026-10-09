#include "a_save_abort_owner.h"
#include "a_save_dispatch_host.h"
namespace a_save_dispatch_host {
namespace pi=planning_input_interlock;namespace pp=planning_period_owner;namespace pcs=planning_checkpoint_save;namespace fs=checkpoint_fresh_save;
bool Host::quiet(a_save_user_owner::Report&u)noexcept {c_.owner->Snapshot(u);a_save_upstream_gate::Report g{};c_.gate->Snapshot(g);
 if(u.active_scopes||u.save.active||u.bridges[0].active||u.bridges[1].active||g.active)return false;
 for(const auto&b:g.bridges)if(b.active)return false;return true;}
void Host::release()noexcept {if(r_.lease){ReleaseSRWLockExclusive(c_.producer);r_.lease=false;++r_.releases;r_.lastReleaseThread=GetCurrentThreadId();}}
bool Host::Initialize(const Config&c)noexcept {if(r_.initialized||!c.owner||!c.gate||!c.controller||!c.mailbox||!c.producer)return false;
 mb::Report m{};c.mailbox->Snapshot(m);pi::Report x{};c.controller->Snapshot(x);pp::Report p{};
 if(!m.initialized||m.stopped||m.host!=GetCurrentThreadId()||!x.initialized||x.thread!=m.host||x.error!=pi::Error::None||!x.requested||x.observing||!pp::Snapshot(*c.owner,p)||p.thread!=m.host||p.retired||!pp::CurrentController(*c.owner,p.binding,c.controller))return false;
 c_=c;r_.initialized=true;r_.thread=m.host;r_.serial=p.serial;return true;}
bool Host::BindPeriod(pi::Controller&controller)noexcept {if(!r_.initialized||GetCurrentThreadId()!=r_.thread||r_.frame||r_.lease||r_.state!=State::Complete)return false;
 mb::Report m{};c_.mailbox->Snapshot(m);pp::Report p{};pi::Report x{};controller.Snapshot(x);
 if(m.stopped||!m.count||m.records[m.count-1].state!=mb::State::Delivered||!pp::Snapshot(*c_.owner,p)||p.retired||p.serial!=r_.serial+1||p.thread!=r_.thread||!x.initialized||x.thread!=r_.thread||x.error!=pi::Error::None||!x.requested||x.observing||!pp::CurrentController(*c_.owner,p.binding,&controller))return false;
 c_.controller=&controller;r_.serial=p.serial;r_.state=State::Idle;submitted_=false;return true;}
bool Host::stoppedBoundary()noexcept {a_save_user_owner::Report u{};if(!quiet(u)){r_.state=State::Unknown;return false;}
 // Cancellation before Submit cannot have created a Save. Once accepted,
 // require observed native Driver Complete or zero-bind Cancelled. Never
 // manufacture Copy/Delivered or explicitly release Ready. Owner Stop may
 // forward User after drain; no full input exclusion is claimed.
 if(submitted_&&u.save.status==fs::Status::Uncertain&&u.save.error==54&&u.save.generation==pending_.request.generation&&a_save_abort::Retire(*c_.owner,pending_.request.generation)){
  c_.owner->Snapshot(u);if(!u.save_lane&&quiet(u)){release();r_.state=State::Unknown;return true;}return false;}
 if((!submitted_&&!u.save_lane)||(u.save.generation==pending_.request.generation&&
   ((u.save.status==fs::Status::Complete&&u.save.worker_joined&&u.save.finalizer_returned&&u.save.return_matched&&u.save.file_bytes_verified)||
    (u.save.status==fs::Status::Cancelled&&!u.save.binds&&!u.save.queues)))){
  release();r_.state=submitted_?State::Unknown:State::Stopped;return true;}
 r_.state=State::Unknown;return false;}
bool Host::BeforeFrame()noexcept {if(!r_.initialized||GetCurrentThreadId()!=r_.thread||r_.frame)return false;
 a_save_user_owner::Report u{};if(!quiet(u))return false;mb::Report m{};c_.mailbox->Snapshot(m);
 if(m.stopped){stoppedBoundary();return false;}if(r_.state==State::Stopped||r_.state==State::Unknown)return false;
 r_.frame=true;if(r_.state!=State::Idle||!m.count||m.records[m.count-1].state!=mb::State::Queued)return true;
 if(!TryAcquireSRWLockExclusive(c_.producer)){r_.frame=false;return false;}r_.lease=true;
 pi::Report x{};c_.controller->Snapshot(x);revision_=x.revision;
 if(!c_.controller->BeginObservation(revision_)){r_.frame=false;r_.state=State::Unknown;c_.mailbox->Stop();stoppedBoundary();return false;}
 r_.state=State::Observing;return true;}
bool Host::AfterFrame()noexcept {if(!r_.initialized||GetCurrentThreadId()!=r_.thread||!r_.frame)return false;
 a_save_user_owner::Report u{};if(!quiet(u))return false;r_.frame=false;mb::Report m{};c_.mailbox->Snapshot(m);
 if(m.stopped){if(r_.state==State::Observing)c_.controller->EndObservation(revision_);return stoppedBoundary();}
 if(r_.state==State::Observing){if(!c_.controller->EndObservation(revision_)){c_.mailbox->Stop();return stoppedBoundary();}
  pi::Report x{};c_.controller->Snapshot(x);pp::Report p{};
  if(!pp::Snapshot(*c_.owner,p)||p.serial!=r_.serial||!c_.mailbox->Take(pending_)){c_.mailbox->Stop();return stoppedBoundary();}
  ++r_.observations;evidence_.binding=p.binding;evidence_.date=p.date;evidence_.periodSerial=p.serial;evidence_.readyRevision=x.revision;evidence_.gateRevision=x.gateRevision;evidence_.observation=x.observation;evidence_.cut=p.reward.completed;
  // InvokeOwner may commit even if a later Gate check returns false.
  submitted_=true;
  if(!pcs::Submit(*c_.owner,*c_.gate,*c_.controller,evidence_,pending_.request)){c_.mailbox->Unknown(pending_);return stoppedBoundary();}
  ++r_.submits;r_.state=State::Submitted;
  if(!c_.mailbox->Accept(pending_)){c_.mailbox->Stop();r_.state=State::Unknown;return false;}return true;
 }
 if(r_.state==State::Submitted&&u.save.status==fs::Status::Complete){fs::Artifact a{};
  if(!pcs::Copy(*c_.owner,*c_.gate,*c_.controller,evidence_,pending_.request.generation,a)){c_.mailbox->Stop();return stoppedBoundary();}
  if(!c_.mailbox->Complete(pending_,a)){c_.mailbox->Stop();return stoppedBoundary();}
  ++r_.copies;r_.state=State::Complete;release();
 }return true;}
bool Host::Snapshot(Report&out)const noexcept {if(!r_.initialized||GetCurrentThreadId()!=r_.thread)return false;out=r_;return true;}
}
