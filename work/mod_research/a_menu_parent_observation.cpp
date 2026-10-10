#include "a_menu_parent_observation.h"
#include "a_save_parent_adapter.h"
#include "b_reload_parent_bridge.h"
#include <cstring>
extern "C" {alignas(8) __declspec(dllexport) a_menu_parent_observation::Record AMenuParentObservation{};}
namespace a_menu_parent_observation {
namespace {
SRWLOCK lock=SRWLOCK_INIT;
template<class T>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}
void blocked(Record&r,Reason reason){r.state=unsigned(State::Unknown);r.reason=unsigned(reason);}
bool same(const Binding&a,const Binding&b){return !memcmp(&a,&b,sizeof a);}
void capture(const Input&i,Record&r)noexcept {
 r.binding=i.binding;r.tick=GetTickCount64();r.thread=GetCurrentThreadId();r.runtimeStopped=i.stopped;r.runtimeError=i.runtimeError;r.planningState=i.planningState;r.repeatState=i.repeatState;
 __try {
  CheckpointLoadWorkerOwner parent{};
  if(!a_save_parent_adapter::CurrentBoundary(i.binding.base)||!BReloadParentCurrentOwner(&parent)||parent.slot||!parent.call_id||parent.token!=parent.call_id||parent.thread_id!=r.thread||parent.owner_depth!=1||parent.current_depth!=1){blocked(r,Reason::Boundary);return;}
  r.parentCall=parent.call_id;
  if(!i.identity||i.binding.pid!=GetCurrentProcessId()||!i.owner||!i.gate||!i.sample){blocked(r,Reason::Identity);return;}
  a_save_user_owner::Report owner{};a_save_upstream_gate::Report gate{};a_reward_save_owner::Report reward{};
  i.owner->Snapshot(owner);i.gate->Snapshot(gate);const bool gotReward=a_reward_save_owner::Snapshot(*i.owner,reward);
  r.ownerError=unsigned(owner.error);r.ownerStopped=owner.stopped;r.ownerActive=owner.active_scopes;r.gateError=unsigned(gate.error);r.gateStopped=gate.stopped;r.gateActive=gate.active;
  r.readyFence=reward.readyFence;r.gateRequested=gate.requested;r.rewardQueued=reward.queued;r.rewardActive=reward.active;r.rewardSequence=reward.submitted;r.rewardCompleted=reward.completed;
  if(i.retired){r.state=unsigned(State::Blocked);r.reason=unsigned(Reason::Retired);return;}
  if(i.stopped||i.runtimeError||!gotReward||!owner.armed||owner.stopped||r.ownerError||!gate.armed||gate.stopped||r.gateError||owner.active_scopes||gate.active||reward.uncertain||reward.error!=a_reward_save_owner::Error::None){blocked(r,Reason::Owner);return;}
  pending::Config p{};if(!i.sample(i.context,p)){blocked(r,Reason::Sample);return;}
  if(p.profile_base!=i.binding.base||p.states[4]!=i.binding.user||p.binding.owner_generation!=i.binding.generation||memcmp(p.binding.attempt.data(),i.binding.attempt,16)||memcmp(p.binding.attachment.data(),i.binding.attachment,16)){blocked(r,Reason::Identity);return;}
  pending::Adapter inspector;const auto bind=inspector.Bind(p);if(bind!=pending::Error::None){r.inspectorError=unsigned(bind);blocked(r,Reason::Bind);return;}
  const auto v=inspector.InspectCurrent(p.binding);
  r.inspectorError=unsigned(v.error);r.decision=unsigned(v.decision);r.menuCommand=v.menu_command;r.userPhase=v.user_phase;r.gameTransition=v.game_transition;r.loadQueued=v.load_queued;r.advance=v.advance;r.panelAdvance=v.panel_advance;r.stackCount=v.stack_count;r.queueCount=v.queue_count;
  r.current=at<uintptr_t>(uintptr_t(p.manager.data)+0x48);for(unsigned n=0;n<3;++n)r.selection[n]=at<uintptr_t>(uintptr_t(p.user.data)+0x4a8+n*8);
  if(v.error!=pending::Error::None){blocked(r,Reason::Inspector);return;}
  r.state=unsigned(v.decision==pending::Decision::QuiescentObserved?State::QuietObserved:
   (v.decision==pending::Decision::PlayerMenuPending||v.decision==pending::Decision::SelectionPending)?State::BusyObserved:State::Blocked);
  if(r.state==unsigned(State::Blocked))r.reason=unsigned(Reason::Inspector);
 }__except(EXCEPTION_EXECUTE_HANDLER){r.exceptionCode=GetExceptionCode();blocked(r,Reason::Exception);}
}
}
void Observe(const Input&i)noexcept {
 Record next{};capture(i,next);
 AcquireSRWLockExclusive(&lock);
 const auto previous=InterlockedCompareExchange64(&AMenuParentObservation.sequence,0,0);
 InterlockedExchange64(&AMenuParentObservation.sequence,previous+1);
 // Keep the publication counter odd throughout the payload copy.
 constexpr auto start=offsetof(Record,binding);
 memcpy(reinterpret_cast<unsigned char*>(&AMenuParentObservation)+start,reinterpret_cast<const unsigned char*>(&next)+start,sizeof(Record)-start);
 MemoryBarrier();InterlockedExchange64(&AMenuParentObservation.sequence,previous+2);
 ReleaseSRWLockExclusive(&lock);
}
void Snapshot(Record&out)noexcept {AcquireSRWLockShared(&lock);memcpy(&out,&AMenuParentObservation,sizeof out);ReleaseSRWLockShared(&lock);}
bool Read(const Binding&expected,std::uint64_t after,std::uint64_t now,std::uint64_t age,Record&out)noexcept {
 Snapshot(out);const auto sequence=std::uint64_t(out.sequence);
 return age&&age<=1000&&out.size==sizeof out&&out.version==1&&sequence&&!(sequence&1)&&sequence>after&&same(expected,out.binding)&&now>=out.tick&&now-out.tick<=age&&
  (out.state==unsigned(State::QuietObserved)||out.state==unsigned(State::BusyObserved))&&!out.uiPermission&&!out.rewardPermission&&!out.fullInputHold;
}
static_assert(offsetof(Record,sequence)%8==0,"atomic publication alignment");
}
