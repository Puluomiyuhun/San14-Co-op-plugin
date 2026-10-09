#include "a_save_abort_owner.h"
#include "a_save_parent_adapter.h"
// Explicit pending-User successor of covered Owner; do not link both.
#include "a_save_pending_user_owner.h"
#include "a_save_covered_owner.h"
// Explicit checkpoint-under-held-Ready implementation successor. Never link the predecessor.
#include "a_save_report_owner.h"
#include "a_reward_save_owner.h"
#include "planning_period_owner.h"
#include "planning_checkpoint_save.h"
#include <exception>
#include "planning_input_interlock_gate.h"
// ABI-compatible report Owner implementation successor. Never link both.
#include <cstring>
#include <new>

// Explicit implementation successor; the frozen predecessor is never compiled
// into this target. This does not turn point-in-time checks into an input lock.
namespace a_save_report_owner {
namespace {
struct State {
 const a_save_user_owner::Owner* owner=nullptr;
 a_save_early_guard::Guard guard;
 checkpoint_native_input_pending::Binding binding{};
 uintptr_t base=0,root=0,world=0,user=0;
 unsigned short cursor=0;
 std::uint64_t generation=0;
 volatile LONG claimed=0,ready=0,pinned=0,revoked=0,boundary=0,decision=0;
 volatile LONG64 submitRejected=0,entrySuppressed=0,afterRejected=0,storageRejected=0,copyRejected=0;
};
State state;
LONG read(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
void record(Boundary b,a_save_early_guard::Decision d,bool revoke)noexcept {
 InterlockedExchange(&state.boundary,LONG(b));InterlockedExchange(&state.decision,LONG(d));
 if(revoke)InterlockedExchange(&state.revoked,1);
}
// Save states have a six-entry manager stack; the early guard's five-entry
// planning condition is intentionally not relaxed. This separate negative
// check pins report identities/queue shape/cursor throughout the Save lane.
bool fields()noexcept {__try {
 const auto&s=state;
 if(at<uintptr_t>(s.base+0x1FCA1E0)!=s.root||at<uintptr_t>(s.root+0x85130)!=s.world||
    at<uintptr_t>(s.root)!=s.base+0x12AA6B0||at<uintptr_t>(s.world)!=s.base+0x12AA638||
    at<uintptr_t>(s.user)!=s.base+0x12CC4A8||at<unsigned>(s.user+0x660)||
    at<std::uint64_t>(s.base+0x1FC98B8)||at<unsigned short>(s.world+0x165A)!=s.cursor)return false;
 const auto h=at<uintptr_t>(s.base+0x1FC98B0);
 return h>=0x10000&&h<UINTPTR_MAX-0x20&&at<uintptr_t>(h)==h&&at<uintptr_t>(h+8)==h&&
        at<uintptr_t>(h+16)==h&&at<unsigned char>(h+0x19)==1;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool ready(const a_save_user_owner::Config&c,const a_save_user_owner::Owner*o)noexcept {__try {
 // Physical User/Save bridge bank and its report sidecar have ONE owner. A
 // failed initializer retains this claim; a second object may not race/rebind.
 if(InterlockedCompareExchange(&state.claimed,1,0))return false;
 checkpoint_native_input_pending::Config input{};if(!c.sample_input(c.input_context,input)||input.profile_base!=c.base)return false;
 auto&s=state;s.owner=o;s.base=c.base;s.root=at<uintptr_t>(c.base+0x1FCA1E0);s.world=at<uintptr_t>(s.root+0x85130);s.user=input.states[4];s.binding=c.input_binding;
 a_save_early_guard::Config cfg{};cfg.base=s.base;cfg.root=s.root;cfg.world=s.world;cfg.user=s.user;cfg.binding=s.binding;
 if(!s.guard.Initialize(cfg))return false;InterlockedExchange(&s.ready,1);return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool observe(Boundary point,bool revoke)noexcept {
 const auto r=state.guard.Observe(state.binding);
 if(r.decision!=a_save_early_guard::Decision::QuietReportsObserved){record(point,r.decision,revoke);return false;}
 if(read(state.pinned)&&!fields()){record(point,a_save_early_guard::Decision::Drift,revoke);return false;}
 return true;
}
}
bool Snapshot(const a_save_user_owner::Owner*o,Report&r)noexcept {
 r={};if(!o||!read(state.ready)||o!=state.owner)return false;r.attached=true;
 r.submitRejected=InterlockedCompareExchange64(&state.submitRejected,0,0);r.entrySuppressed=InterlockedCompareExchange64(&state.entrySuppressed,0,0);
 r.afterRejected=InterlockedCompareExchange64(&state.afterRejected,0,0);r.storageRejected=InterlockedCompareExchange64(&state.storageRejected,0,0);r.copyRejected=InterlockedCompareExchange64(&state.copyRejected,0,0);
 r.lastBoundary=Boundary(read(state.boundary));r.lastDecision=a_save_early_guard::Decision(read(state.decision));r.revoked=read(state.revoked)!=0;return true;
}
}

namespace a_reward_save_owner {
namespace {
struct Lane {a_save_user_owner::Owner*owner=nullptr;SRWLOCK*lock=nullptr;volatile LONG*armed=nullptr,*stopped=nullptr,*ownerError=nullptr;bool*save=nullptr,*hold=nullptr,*checkpoint=nullptr;std::uint64_t*scopes=nullptr;checkpoint_native_input_pending::Binding input{};uintptr_t base=0,root=0,world=0,user=0;Config config{};Report report{};rw::Command command{};rw::Owner*running=nullptr;bool periodRetired=false;};Lane lane;
bool binding(const ph::Binding&a,const ph::Binding&b){return a.native.attempt==b.native.attempt&&a.native.attachment==b.native.attachment&&a.native.owner_generation==b.native.owner_generation&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
LONG load(volatile LONG*p){return InterlockedCompareExchange(p,0,0);}
bool healthy(){auto&s=lane;return s.owner&&load(s.armed)&&!load(s.stopped)&&!load(s.ownerError)&&s.report.error==Error::None;}
void fault(Error e,bool uncertain=false){auto&s=lane;if(s.report.error==Error::None)s.report.error=e;s.report.queued=false;s.report.uncertain|=uncertain;InterlockedExchange(s.stopped,1);InterlockedCompareExchange(s.ownerError,LONG(a_save_user_owner::Error::Input),0);if(s.running)RewardOwnedCancel(s.running);}
bool source(Source&out){auto&s=lane;if(!s.config.sample(s.config.context,s.user,s.command.command_force,out)||!binding(out.admission.binding,s.config.binding)||!binding(out.reward.binding,s.config.binding)||out.reward.base!=s.base||out.reward.root!=s.root||out.reward.world!=s.world||out.reward.user!=s.user||out.reward.authorized_force!=s.command.command_force||out.admission.pending.profile_base!=s.base||out.admission.pending.states[4]!=s.user)return false;
#ifndef A_REWARD_SAVE_OWNER_FIXTURE
 if(uintptr_t(out.admission.reward)!=s.base+0x1D6DA0)return false;
#endif
 checkpoint_native_input_pending::Adapter a;if(a.Bind(out.admission.pending)!=checkpoint_native_input_pending::Error::None)return false;auto r=a.InspectCurrent(s.input);return r.error==checkpoint_native_input_pending::Error::None&&r.decision==checkpoint_native_input_pending::Decision::QuiescentObserved&&r.stack_count==5&&r.user_phase==2;
}
}
bool Bind(a_save_user_owner::Owner&o,const Config&c) noexcept {auto&s=lane;if(&o!=s.owner||!s.lock)return false;AcquireSRWLockExclusive(s.lock);bool ok=false;__try {if(!healthy()||s.periodRetired||s.report.bound||*s.scopes||*s.save||*s.hold||!c.sample||!c.binding.period||!c.binding.epoch||c.binding.native.attempt!=s.input.attempt||c.binding.native.attachment!=s.input.attachment||c.binding.native.owner_generation!=s.input.owner_generation)__leave;s.config=c;s.report.bound=true;ok=true;}__finally{ReleaseSRWLockExclusive(s.lock);}return ok;}
bool Submit(a_save_user_owner::Owner&o,const ph::Binding&b,std::uint64_t seq,const rw::Command&c) noexcept {auto&s=lane;if(&o!=s.owner||!s.lock)return false;AcquireSRWLockExclusive(s.lock);bool ok=false;__try {if(!healthy()||s.periodRetired||!s.report.bound||!binding(b,s.config.binding)||*s.scopes||*s.save||*s.hold||s.report.readyFence||s.report.queued||s.report.active||!seq||seq!=s.report.submitted+1)__leave;s.command=c;s.report.submitted=seq;s.report.queued=true;ok=true;}__finally{ReleaseSRWLockExclusive(s.lock);}return ok;}
bool Cancel(a_save_user_owner::Owner&o,const ph::Binding&b,std::uint64_t seq) noexcept {auto&s=lane;if(&o!=s.owner||!s.lock)return false;AcquireSRWLockExclusive(s.lock);bool ok=false;__try {if(s.periodRetired||!s.report.bound||!binding(b,s.config.binding)||seq!=s.report.submitted||(!s.report.queued&&!s.report.active))__leave;s.report.queued=false;++s.report.cancelled;if(s.running)RewardOwnedCancel(s.running);if(s.report.active)fault(Error::Cancelled,true);ok=true;}__finally{ReleaseSRWLockExclusive(s.lock);}return ok;}
bool ReadyFence(a_save_user_owner::Owner&o,const ph::Binding&b,bool value,std::uint64_t revision) noexcept {auto&s=lane;if(&o!=s.owner||!s.lock)return false;AcquireSRWLockExclusive(s.lock);bool ok=false;__try {if(!healthy()||s.periodRetired||!s.report.bound||!binding(b,s.config.binding)||*s.scopes||*s.save||*s.hold||(s.checkpoint&&*s.checkpoint)||s.report.queued||s.report.active||!revision||revision<=s.report.readyRevision)__leave;s.report.readyFence=value;s.report.readyRevision=revision;ok=true;}__finally{ReleaseSRWLockExclusive(s.lock);}return ok;}
bool Snapshot(a_save_user_owner::Owner&o,Report&r) noexcept {auto&s=lane;r={};if(&o!=s.owner||!s.lock)return false;AcquireSRWLockShared(s.lock);r=s.report;ReleaseSRWLockShared(s.lock);return true;}
}

namespace a_save_covered_owner {
namespace {volatile LONG64 selected=0,claimed=0,returned=0,finished=0,rejected=0;}
bool Snapshot(const a_save_user_owner::Owner*o,Report&out)noexcept {
 out={};a_save_report_owner::Report identity{};if(!a_save_report_owner::Snapshot(o,identity))return false;
 out={std::uint64_t(InterlockedCompareExchange64(&selected,0,0)),std::uint64_t(InterlockedCompareExchange64(&claimed,0,0)),std::uint64_t(InterlockedCompareExchange64(&returned,0,0)),std::uint64_t(InterlockedCompareExchange64(&finished,0,0)),std::uint64_t(InterlockedCompareExchange64(&rejected,0,0))};return true;
}
}

namespace a_save_pending_user {
namespace {volatile LONG64 selected=0,claimed=0,returned=0,finished=0,rejected=0;}
bool Snapshot(const a_save_user_owner::Owner*o,Report&out)noexcept {
 out={};a_save_report_owner::Report identity{};if(!a_save_report_owner::Snapshot(o,identity))return false;
 out={std::uint64_t(InterlockedCompareExchange64(&selected,0,0)),std::uint64_t(InterlockedCompareExchange64(&claimed,0,0)),std::uint64_t(InterlockedCompareExchange64(&returned,0,0)),std::uint64_t(InterlockedCompareExchange64(&finished,0,0)),std::uint64_t(InterlockedCompareExchange64(&rejected,0,0))};return true;
}
}

extern "C" {alignas(8) a_save_abort::Receipt ASaveAbortReceipt{};}
namespace a_save_abort {
namespace {a_save_user_owner::Owner*owner=nullptr;void*context=nullptr;bool(*retire)(void*,std::uint64_t)noexcept=nullptr;}
bool Retire(a_save_user_owner::Owner&o,std::uint64_t generation)noexcept {return &o==owner&&retire&&retire(context,generation);}
bool Snapshot(uintptr_t base,std::uint64_t generation,DWORD thread,Receipt&out)noexcept {
 out={};const auto seq=InterlockedCompareExchange64(reinterpret_cast<volatile LONG64*>(&ASaveAbortReceipt.sequence),0,0);if(!seq||(seq&1))return false;
 out=ASaveAbortReceipt;MemoryBarrier();return seq==InterlockedCompareExchange64(reinterpret_cast<volatile LONG64*>(&ASaveAbortReceipt.sequence),0,0)&&out.size==sizeof out&&out.version==1&&out.retired==1&&out.base==base&&out.generation==generation&&out.thread==thread&&out.owner==uintptr_t(owner)&&out.driverError==54;
}
}
namespace a_save_user_owner {
namespace pending=checkpoint_native_input_pending;
namespace fs=checkpoint_fresh_save;
namespace sb=checkpoint_live_storage_binding;
namespace rp=a_save_report_owner;
namespace ar=a_reward_save_owner;
namespace {
LONG value(volatile LONG*p) noexcept{return InterlockedCompareExchange(p,0,0);}
constexpr std::uintptr_t slotRva[2]={0x12CC4A8+0x28,0x12DC5F8+0x28};
constexpr std::uintptr_t originalRva[2]={0x3F9B00,0x4AA650};
void* hook(unsigned i) noexcept{return i?reinterpret_cast<void*>(&ASaveUserOwnerBridge1):reinterpret_cast<void*>(&ASaveUserOwnerBridge0);}
bool same(const sb::Attachment&a,const sb::Attachment&b) noexcept{
 return a.pid==b.pid&&a.birth==b.birth&&a.base==b.base&&a.attempt==b.attempt&&a.generation==b.generation&&
  !std::memcmp(a.id,b.id,32)&&!std::memcmp(a.gameSha256,b.gameSha256,32);
}
}
struct Owner::Impl {
 Config config{};fs::Driver driver;checkpoint_serialized_storage_gate::Gate gate;
 checkpoint_load_hook_set::Set hooks;SRWLOCK control=SRWLOCK_INIT;
 unsigned char nativePrefix[2][32]{};
 volatile LONG once=0,initialized=0,armed=0,stopped=0,error=0,codeReady=0;
 std::uint64_t holdRevision=0,heldScopes=0,activeScopes=0;
 bool hold=false,holdObserved=false,saveLane=false;
 bool checkpointActive=false;planning_checkpoint_save::Evidence checkpointEvidence{};
 planning_input_interlock::Controller*checkpointController=nullptr;a_save_upstream_gate::Owner*checkpointGate=nullptr;
 std::uint64_t checkpointGeneration=0,checkpointConsumedSerial=0,checkpointConsumedObservation=0;
 static bool checkpoint(void*,const planning_checkpoint_save::detail::Call&)noexcept;
 uintptr_t coveredStates[5]{};std::uint64_t coveredCall=0,coveredGeneration=0;DWORD coveredThread=0;uintptr_t coveredSave=0;
 static bool abortDrain(void*v,std::uint64_t generation)noexcept {
  auto&s=*static_cast<Impl*>(v);const auto thread=GetCurrentThreadId();
  if(!a_save_parent_adapter::CurrentBoundary(s.config.base)||!s.checkpointController)return false;
  planning_input_interlock::Report controller{};s.checkpointController->Snapshot(controller);
  if(!controller.initialized||controller.thread!=thread||controller.observing)return false;
  CheckpointLoadWorkerOwner parent{};
  if(!BReloadParentCurrentOwner(&parent)||parent.slot||parent.thread_id!=thread||parent.token!=parent.call_id||parent.owner_depth!=1||parent.current_depth!=1)return false;
  bool ok=false;AcquireSRWLockExclusive(&s.control);
  __try {__try {
   const auto r=s.driver.Snapshot();
   if(!value(&s.initialized)||!value(&s.armed)||!value(&s.stopped)||!generation||generation!=s.checkpointGeneration||generation!=rp::state.generation||r.generation!=generation||
      r.status!=fs::Status::Uncertain||r.error!=54||r.binds!=1||r.queues!=1||r.phase_mask!=31||!r.worker_started||!r.worker_joined||!r.native_success||!r.finalizer_returned||
      r.return_matched||r.file_bytes_verified||r.completed_requests||r.active||r.abnormal||r.entries!=r.exits||s.activeScopes||s.coveredCall||ar::lane.report.active||ar::lane.report.queued||!s.slots())__leave;
   for(unsigned i=0;i<2;++i){CheckpointLoadWorkerBridgeStats bridge{};if(!ASaveUserOwnerBridgeSnapshot(i,&bridge)||bridge.active)__leave;}
   // Error 54 occurs after the returned User's planning check and finalizer.
   // Recheck actual removal and task ownership at the authenticated boundary;
   // never dereference the retired Save pointer, which may have been freed.
   if(rp::at<uintptr_t>(s.config.base+0x1FCA1E0)!=rp::state.root||rp::at<uintptr_t>(rp::state.root+0x85130)!=rp::state.world)__leave;
   const auto manager=s.config.base+0x19E7310,stack=rp::at<uintptr_t>(manager+0x20);
   if(!stack||rp::at<std::uint64_t>(manager+0x10)!=5||rp::at<std::uint64_t>(manager+0x30)||rp::at<uintptr_t>(manager+0x48))__leave;
   bool tasks=true;for(unsigned i=0;i<5;++i)if(rp::at<uintptr_t>(stack+i*8)!=s.coveredStates[i]||rp::at<uintptr_t>(s.coveredStates[i]+0x50))tasks=false;if(!tasks)__leave;
   checkpoint_native_input_pending::Config fresh{};if(!s.config.sample_input(s.config.input_context,fresh)||fresh.profile_base!=s.config.base||fresh.binding.attempt!=s.config.input_binding.attempt||fresh.binding.attachment!=s.config.input_binding.attachment||fresh.binding.owner_generation!=s.config.input_binding.owner_generation||memcmp(fresh.states,s.coveredStates,sizeof s.coveredStates))__leave;
   if(rp::at<std::uint64_t>(manager+0x10)!=5||rp::at<std::uint64_t>(manager+0x30)||rp::at<uintptr_t>(manager+0x48)||rp::at<uintptr_t>(manager+0x20)!=stack)__leave;
   if(!s.saveLane){a_save_abort::Receipt receipt{};ok=a_save_abort::Snapshot(s.config.base,generation,thread,receipt);__leave;}
   InterlockedIncrement64(reinterpret_cast<volatile LONG64*>(&ASaveAbortReceipt.sequence));
   ASaveAbortReceipt.base=s.config.base;ASaveAbortReceipt.owner=uintptr_t(a_save_abort::owner);ASaveAbortReceipt.generation=generation;ASaveAbortReceipt.thread=thread;ASaveAbortReceipt.ownerError=unsigned(value(&s.error));ASaveAbortReceipt.driverError=r.error;
   s.saveLane=false;ASaveAbortReceipt.retired=1;MemoryBarrier();InterlockedIncrement64(reinterpret_cast<volatile LONG64*>(&ASaveAbortReceipt.sequence));ok=true;
   // Keep error, Driver Uncertain, pinned/revoked report, claim and reservation.
  }__except(EXCEPTION_EXECUTE_HANDLER){ok=false;}}
  __finally{ReleaseSRWLockExclusive(&s.control);}return ok;
 }
 bool pinCoveredStates()noexcept {
  checkpoint_native_input_pending::Config p{};
  if(!config.sample_input(config.input_context,p)||p.profile_base!=config.base||p.binding.attempt!=config.input_binding.attempt||p.binding.attachment!=config.input_binding.attachment||p.binding.owner_generation!=config.input_binding.owner_generation||p.states[4]!=rp::state.user)return false;
  for(auto state:p.states)if(!state)return false;memcpy(coveredStates,p.states,sizeof coveredStates);return true;
 }
 bool coveredSource()noexcept {
  if(!slots())return false;
#ifndef A_SAVE_USER_OWNER_FIXTURE
  const auto address=config.base+0x509640;MEMORY_BASIC_INFORMATION m{};
  if(VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof m)!=sizeof m||m.Type!=MEM_IMAGE||m.State!=MEM_COMMIT||uintptr_t(m.AllocationBase)!=config.base||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
  constexpr unsigned char expected[]={0x63,0xb7,0xbf,0x40,0x19,0x81,0xa4,0xcd,0x0f,0xf3,0x97,0x6f,0x75,0xfd,0xcc,0x76,0x1e,0x8e,0xa8,0xee,0x3d,0xf6,0xb6,0x97,0xab,0x5d,0xa8,0xe1,0xdd,0x0e,0x41,0x16};
  unsigned char hash[32]{};if(!native_storage_read::Sha256(reinterpret_cast<void*>(address),0x35,hash)||memcmp(hash,expected,32))return false;
  // The top check calls the fixed manager singleton. An initialized CRT guard
  // excludes the cold branch that would reconstruct the existing manager.
  const auto singleton=config.base+0xF690;MEMORY_BASIC_INFORMATION sm{};
  if(VirtualQuery(reinterpret_cast<void*>(singleton),&sm,sizeof sm)!=sizeof sm||sm.Type!=MEM_IMAGE||sm.State!=MEM_COMMIT||uintptr_t(sm.AllocationBase)!=config.base||(sm.Protect!=PAGE_EXECUTE_READ&&sm.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
  constexpr unsigned char singletonHash[]={0xc0,0x4d,0xff,0x10,0xf1,0x6d,0x1b,0xf9,0x30,0xf6,0xb4,0xec,0xf5,0xe7,0xbe,0xc6,0x09,0x11,0xe8,0x3f,0x11,0xd8,0x16,0x13,0x04,0x2f,0x53,0x72,0xad,0xfe,0x44,0xfe};
  if(!native_storage_read::Sha256(reinterpret_cast<void*>(singleton),0x81,hash)||memcmp(hash,singletonHash,32))return false;
  const auto guard=rp::at<int>(config.base+0x19E7360);if(!guard||guard==-1)return false;
  constexpr unsigned char epilogue[]={0x48,0x83,0xc4,0x40,0x5e,0xc3};
  if(memcmp(reinterpret_cast<void*>(config.base+0x3FA0AE),epilogue,sizeof epilogue))return false;
#endif
  return true;
 }
 bool coveredShape(const CheckpointLoadWorkerFrame&f,bool claimed)noexcept {__try {
  const auto report=driver.Snapshot();auto caller=config.base+0x50B785;
#ifdef A_SAVE_USER_OWNER_FIXTURE
  caller=config.caller;
#endif
  if(f.slot||f.thread_id!=GetCurrentThreadId()||!f.call_id||!f.caller_entry_rsp||*reinterpret_cast<const uintptr_t*>(f.caller_entry_rsp)!=caller||f.args[0]!=coveredStates[4]||activeScopes!=1||
    report.status!=fs::Status::Queued||report.error||!report.generation||report.generation!=rp::state.generation||report.binds!=1||report.queues!=1||!report.save_state||!rp::read(rp::state.pinned)||rp::read(rp::state.revoked)||!coveredSource()||!rp::fields())return false;
  const auto manager=config.base+0x19E7310;const auto stack=rp::at<uintptr_t>(manager+0x20);
  if(!stack||rp::at<std::uint64_t>(manager+0x10)!=6||rp::at<std::uint64_t>(manager+0x30)||rp::at<uintptr_t>(manager+0x48)!=coveredStates[4]||rp::at<unsigned>(coveredStates[4]+0x470)!=2)return false;
  for(unsigned i=0;i<5;++i)if(rp::at<uintptr_t>(stack+i*8)!=coveredStates[i])return false;
  const auto save=rp::at<uintptr_t>(stack+40);
  if(save!=report.save_state||save==coveredStates[4]||rp::at<uintptr_t>(save)!=config.base+0x12DC5F8||memcmp(reinterpret_cast<void*>(save+0x70),"CSaveState",11)||rp::at<unsigned>(save+0x470)>4)return false;
  CheckpointLoadWorkerOwner physical{};
  if(claimed){if(coveredCall!=f.call_id||coveredThread!=f.thread_id||coveredGeneration!=report.generation||coveredSave!=save||!ASaveUserOwnerCurrentOwner(&physical)||physical.call_id!=f.call_id||physical.slot||physical.thread_id!=f.thread_id||physical.token!=report.generation||physical.owner_depth!=1||physical.current_depth!=1)return false;}
  else if(ASaveUserOwnerCurrentOwner(&physical))return false;
  // Re-read the shape around field/source checks. This only accepts an exact
  // owned covered state; it does not certify unrelated writers are excluded.
  if(!rp::fields()||rp::at<std::uint64_t>(manager+0x10)!=6||rp::at<std::uint64_t>(manager+0x30)||rp::at<uintptr_t>(manager+0x20)!=stack||rp::at<uintptr_t>(stack+40)!=save)return false;
  for(unsigned i=0;i<5;++i)if(rp::at<uintptr_t>(stack+i*8)!=coveredStates[i])return false;
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool pendingShape(const CheckpointLoadWorkerFrame&f,bool claimed)noexcept {__try {
  const auto report=driver.Snapshot();auto caller=config.base+0x50B785;
#ifdef A_SAVE_USER_OWNER_FIXTURE
  caller=config.caller;
#endif
  if(f.slot||f.thread_id!=GetCurrentThreadId()||!f.call_id||!f.caller_entry_rsp||rp::at<uintptr_t>(f.caller_entry_rsp)!=caller||f.args[0]!=coveredStates[4]||activeScopes!=1||
     !checkpointActive||!checkpointController||!checkpointGate||checkpointGeneration!=report.generation||report.status!=fs::Status::Queued||report.error||!report.generation||report.generation!=rp::state.generation||report.binds!=1||report.queues!=1||!report.save_state||
     !rp::read(rp::state.pinned)||rp::read(rp::state.revoked)||!coveredSource()||!rp::fields()||value(&stopped)||value(&error))return false;
  pending::Config p{};if(!config.sample_input(config.input_context,p)||p.profile_base!=config.base||p.binding.attempt!=config.input_binding.attempt||p.binding.attachment!=config.input_binding.attachment||p.binding.owner_generation!=config.input_binding.owner_generation||memcmp(p.states,coveredStates,sizeof coveredStates))return false;
  pending::Adapter inspect;if(inspect.Bind(p)!=pending::Error::None)return false;const auto check=inspect.InspectCurrent(config.input_binding);
  const auto m=config.base+0x19E7310,stack=rp::at<uintptr_t>(m+0x20),queue=rp::at<uintptr_t>(m+0x40);
  if(check.error!=pending::Error::None||check.decision!=pending::Decision::UnownedStateQueue||check.stack_count!=5||check.queue_count!=1||uintptr_t(p.manager.data)!=m||uintptr_t(p.stack.data)!=stack||uintptr_t(p.queue.data)!=queue||p.queue.size<16||rp::at<uintptr_t>(m+0x48)!=coveredStates[4])return false;
  if(rp::at<unsigned>(queue)||rp::at<uintptr_t>(queue+8)!=report.save_state||rp::at<uintptr_t>(report.save_state)!=config.base+0x12DC5F8||memcmp(reinterpret_cast<void*>(report.save_state+0x70),"CSaveState",11)||rp::at<unsigned>(report.save_state+0x470))return false;
  CheckpointLoadWorkerOwner physical{};
  if(claimed){if(coveredCall!=f.call_id||coveredThread!=f.thread_id||coveredGeneration!=report.generation||coveredSave!=report.save_state||!ASaveUserOwnerCurrentOwner(&physical)||physical.call_id!=f.call_id||physical.slot||physical.thread_id!=f.thread_id||physical.token!=report.generation||physical.owner_depth!=1||physical.current_depth!=1)return false;}
  else if(ASaveUserOwnerCurrentOwner(&physical))return false;
  if(!rp::fields()||rp::at<std::uint64_t>(m+0x10)!=5||rp::at<std::uint64_t>(m+0x30)!=1||rp::at<uintptr_t>(m+0x20)!=stack||rp::at<uintptr_t>(m+0x40)!=queue||rp::at<unsigned>(queue)||rp::at<uintptr_t>(queue+8)!=report.save_state)return false;
  for(unsigned i=0;i<5;++i)if(rp::at<uintptr_t>(stack+i*8)!=coveredStates[i])return false;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}

 bool fail(Error e) noexcept{InterlockedCompareExchange(&error,LONG(e),0);return false;}
 bool slots(bool rawOnly=false) noexcept {
  __try {
   for(unsigned i=0;i<2;++i){
    const auto original=config.base+originalRva[i];
    if(value(&codeReady)){
     MEMORY_BASIC_INFORMATION page{};
     if(VirtualQuery(reinterpret_cast<void*>(original),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
        (page.Protect!=PAGE_EXECUTE_READ&&page.Protect!=PAGE_EXECUTE_WRITECOPY)||
        (i==0?!ASaveUpstreamUserPrefix(config.base,nativePrefix[i]):std::memcmp(reinterpret_cast<const void*>(original),nativePrefix[i],32)!=0))return false;
    }
    auto p=*reinterpret_cast<void*volatile*>(config.base+slotRva[i]);
    if(rawOnly){if(p!=reinterpret_cast<void*>(config.base+originalRva[i]))return false;}
    else if(value(&armed)){if(p!=hook(i))return false;}
    else if(p!=hook(i)&&p!=reinterpret_cast<void*>(config.base+originalRva[i]))return false;
   }
   return true;
  }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
 }
 static bool storageOwner(void*v,const sb::Attachment&a,sb::Point p) noexcept {
  auto&s=*static_cast<Impl*>(v);
  if(rp::read(rp::state.pinned)&&(rp::read(rp::state.revoked)||!rp::fields())){
   InterlockedIncrement64(&rp::state.storageRejected);rp::record(rp::Boundary::Storage,a_save_early_guard::Decision::Drift,true);return false;
  }
  return same(a,s.config.storage.attachment)&&s.slots()&&s.config.storage.checkOwner&&
   s.config.storage.checkOwner(s.config.storage.owner,a,p);
 }
 static bool storageReadBridge(void*v,std::uintptr_t slot,std::uintptr_t original,std::uintptr_t bridge) noexcept {
  auto&s=*static_cast<Impl*>(v);
  return s.config.storage.checkOwnedReadBridge&&s.config.storage.checkOwnedReadBridge(s.config.storage.owner,slot,original,bridge);
 }
 bool idleUser(const CheckpointLoadWorkerFrame&f) noexcept {
  namespace pd=checkpoint_native_input_pending;
  auto caller=config.base+0x50B785;
#ifdef A_SAVE_USER_OWNER_FIXTURE
  caller=config.caller;
#endif
  if(f.thread_id!=GetCurrentThreadId()||!f.call_id||!f.caller_entry_rsp||*reinterpret_cast<const std::uintptr_t*>(f.caller_entry_rsp)!=caller)return false;
  pd::Config c{};
  if(!config.sample_input(config.input_context,c)||c.profile_base!=config.base||c.states[4]!=f.args[0]||
     reinterpret_cast<std::uintptr_t>(c.manager.data)!=config.base+0x19E7310||
     reinterpret_cast<std::uintptr_t>(c.load_cache.data)!=*reinterpret_cast<const std::uintptr_t*>(config.base+0x2025318)||
     c.binding.attempt!=config.input_binding.attempt||c.binding.attachment!=config.input_binding.attachment||
     c.binding.owner_generation!=config.input_binding.owner_generation)return false;
  pd::Adapter inspector;if(inspector.Bind(c)!=pd::Error::None)return false;
  const auto result=inspector.InspectCurrent(config.input_binding);
  return result.error==pd::Error::None&&result.decision==pd::Decision::QuiescentObserved&&result.stack_count==5&&result.user_phase==2;
 }
 static bool select(CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);bool forward=true;
  AcquireSRWLockExclusive(&s.control);
  __try {__try {
   ++s.activeScopes;f->reserved_58=3; // tracked transparent/raw ordinary scope
   if(!value(&s.armed))__leave;
   if(s.activeScopes!=1){s.fail(Error::Overlap);s.driver.Stop();__leave;}
   if(s.saveLane){
    if(f->slot==0&&s.pendingShape(*f,false)){
     const auto r=s.driver.Snapshot();s.coveredCall=f->call_id;s.coveredThread=f->thread_id;s.coveredGeneration=r.generation;s.coveredSave=r.save_state;
     InterlockedIncrement64(&a_save_pending_user::selected);f->reserved_58=7;__leave;
    }
    if(f->slot==0&&s.coveredShape(*f,false)){
     const auto r=s.driver.Snapshot();s.coveredCall=f->call_id;s.coveredThread=f->thread_id;s.coveredGeneration=r.generation;s.coveredSave=r.save_state;
     InterlockedIncrement64(&a_save_covered_owner::selected);f->reserved_58=6;__leave;
    }
    if(f->slot==0&&!value(&s.stopped)&&!value(&s.error)&&!rp::observe(rp::Boundary::Entry,true)){
     // Suppress exactly this rejected invocation. There was no native return
     // and no Driver Before/After claim. Cancel, never wait for a flush that
     // this very suppression would prevent. Later calls forward transparently.
     InterlockedIncrement64(&rp::state.entrySuppressed);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();
     f->reserved_58=4;f->result_rax=0;std::memset(f->result_xmm0,0,sizeof f->result_xmm0);forward=false;__leave;
    }
    if(f->slot==1&&!rp::fields()){rp::record(rp::Boundary::Entry,a_save_early_guard::Decision::Drift,true);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}
    f->reserved_58=1;__leave;
   }
   // Stop revokes new work, including User suppression. Keep the earlier
   // saveLane branch: a save already bound must still finish its evidence.
   if(value(&s.stopped)||value(&s.error))__leave;
   if(f->slot==0&&ar::lane.report.queued){
    if(!s.slots()||!s.idleUser(*f)||!rp::observe(rp::Boundary::Entry,false)){ar::fault(ar::Error::Source);s.driver.Stop();__leave;}
    ar::lane.report.queued=false;ar::lane.report.active=1;ar::lane.report.thread=GetCurrentThreadId();
    f->reserved_58=5;f->result_rax=0;std::memset(f->result_xmm0,0,sizeof f->result_xmm0);forward=false;__leave;
   }
   if(f->slot==0&&(s.hold||ar::lane.report.readyFence)){
    s.holdObserved=false;
    if(!s.slots()||!s.idleUser(*f)){s.fail(Error::Input);s.driver.Stop();__leave;}
    f->reserved_58=2;f->result_rax=0;std::memset(f->result_xmm0,0,sizeof f->result_xmm0);forward=false;
   }
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Input);s.driver.Stop();}}
  __finally{ReleaseSRWLockExclusive(&s.control);}
  return forward;
 }
 static void reward(const CheckpointLoadWorkerFrame*f,void*) {
  auto&l=ar::lane;ar::Source fresh{};checkpoint_reward_owned_replay::Owner*owner=nullptr;checkpoint_planning_hold::Context*hold=nullptr;std::exception_ptr failure;bool success=false;
  try {
   if(!f||!ASaveUserOwnerClaim(f,l.input.owner_generation))throw ar::Error::Scope;
   CheckpointLoadWorkerOwner physical{};if(!ASaveUserOwnerCurrentOwner(&physical)||physical.thread_id!=GetCurrentThreadId()||physical.call_id!=f->call_id||physical.slot||physical.token!=l.input.owner_generation||physical.current_depth!=physical.owner_depth)throw ar::Error::Scope;
   if(!ar::source(fresh))throw ar::Error::Source;
   owner=RewardOwnedCreate(&fresh.reward);if(!owner)throw ar::Error::Replay;
   AcquireSRWLockExclusive(l.lock);l.running=owner;++l.report.created;const bool live=ar::healthy();ReleaseSRWLockExclusive(l.lock);if(!live)throw ar::Error::Cancelled;
   fresh.admission.capture_owned_command=&RewardOwnedCapture;fresh.admission.replay_source_context=owner;hold=PlanningHoldCreate(&fresh.admission);if(!hold)throw ar::Error::Replay;
   if(PlanningHoldRequest(hold,&l.config.binding,unsigned(checkpoint_planning_hold::Operation::Hold),1)!=unsigned(checkpoint_planning_hold::Status::Ok)||!RewardOwnedPrepare(owner,&l.command)||RewardOwnedExecute(owner,hold,1)!=1)throw ar::Error::Replay;
   success=true;
  }catch(ar::Error e){AcquireSRWLockExclusive(l.lock);ar::fault(e);ReleaseSRWLockExclusive(l.lock);}catch(...){failure=std::current_exception();AcquireSRWLockExclusive(l.lock);ar::fault(ar::Error::Exception,true);ReleaseSRWLockExclusive(l.lock);}
  checkpoint_reward_owned_replay::Report rr{};checkpoint_planning_hold::Report pr{};if(owner)RewardOwnedSnapshot(owner,&rr);if(hold)PlanningHoldSnapshot(hold,&pr);
  AcquireSRWLockExclusive(l.lock);l.running=nullptr;ReleaseSRWLockExclusive(l.lock);
  const bool released=!owner||RewardOwnedDestroy(owner);if(hold)PlanningHoldDestroy(hold);
  AcquireSRWLockExclusive(l.lock);l.report.reward=rr;l.report.admission=pr;if(owner&&released)++l.report.destroyed;if(!released)ar::fault(ar::Error::Cleanup,true);if(success&&released&&ar::healthy())l.report.completed=l.report.submitted;else if(rr.native_returned)l.report.uncertain=true;ReleaseSRWLockExclusive(l.lock);
  if(failure)std::rethrow_exception(failure);
 }
 static void before(const CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);
  // Partial publication is transparent. Submit cannot succeed before Arm.
  if(f->reserved_58==1||f->reserved_58==6||f->reserved_58==7)s.driver.Before(*f);
  if(f->reserved_58==7){if(s.pendingShape(*f,true))InterlockedIncrement64(&a_save_pending_user::claimed);else{InterlockedIncrement64(&a_save_pending_user::rejected);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}}
  if(f->reserved_58==6){if(s.coveredShape(*f,true))InterlockedIncrement64(&a_save_covered_owner::claimed);else{InterlockedIncrement64(&a_save_covered_owner::rejected);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}}
 }
 static void after(const CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);
  if(f->reserved_58==7){
   if(!s.pendingShape(*f,true)){InterlockedIncrement64(&a_save_pending_user::rejected);rp::record(rp::Boundary::After,a_save_early_guard::Decision::Drift,true);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}
   else InterlockedIncrement64(&a_save_pending_user::returned);
   s.driver.After(*f);
  }
  if(f->reserved_58==6){
   if(f->result_rax!=0||!s.coveredShape(*f,true)){InterlockedIncrement64(&a_save_covered_owner::rejected);rp::record(rp::Boundary::After,a_save_early_guard::Decision::Drift,true);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}
   else InterlockedIncrement64(&a_save_covered_owner::returned);
   s.driver.After(*f);
  }
  if(f->reserved_58==1){
   const bool reports=f->slot==0?rp::observe(rp::Boundary::After,true):rp::fields();
   if(!reports){InterlockedIncrement64(&rp::state.afterRejected);rp::record(rp::Boundary::After,a_save_early_guard::Decision::Drift,true);s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}
   s.driver.After(*f);
  }
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);
  if(f->reserved_58==1||f->reserved_58==6||f->reserved_58==7)s.driver.Finally(*f,*e);
  if(f->reserved_58==7){InterlockedIncrement64(&a_save_pending_user::finished);s.coveredCall=0;s.coveredThread=0;s.coveredGeneration=0;s.coveredSave=0;}
  if(f->reserved_58==6){InterlockedIncrement64(&a_save_covered_owner::finished);s.coveredCall=0;s.coveredThread=0;s.coveredGeneration=0;s.coveredSave=0;}
  const auto report=s.driver.Snapshot();
  // Storage callbacks can run under Driver's mutex and therefore only record
  // revocation there. Propagate it to the public Owner terminal state here.
  if(rp::read(rp::state.revoked)){s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();}
  AcquireSRWLockExclusive(&s.control);
  __try {
   if(s.activeScopes)--s.activeScopes;else s.fail(Error::Overlap);
   if(f->reserved_58==5){ar::lane.report.active=0;++ar::lane.report.finally;if(e->abnormal){++ar::lane.report.abnormal;ar::fault(ar::Error::Exception,true);}}
   if(f->reserved_58==2&&!e->abnormal){++s.heldScopes;s.holdObserved=!s.activeScopes&&!value(&s.error);}
   if(report.status==fs::Status::Complete){s.saveLane=false;InterlockedExchange(&rp::state.pinned,0);}
  }__finally{ReleaseSRWLockExclusive(&s.control);}
 }
};
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c) noexcept {
 auto&s=*p_;if(InterlockedCompareExchange(&s.once,1,0))return s.fail(Error::Used);
 bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {__try {
  if(value(&s.stopped)){s.fail(Error::Stopped);__leave;}
  unsigned any=0;for(auto n:c.room_id)any|=n;
  if(!c.base||c.base>UINTPTR_MAX-0x2300000||!c.room_epoch||!any||c.storage.attachment.base!=c.base||!c.storage.checkOwner||!c.sample_input||!c.input_binding.owner_generation){s.fail(Error::Config);__leave;}
  s.config=c;
  if(!rp::ready(c,this)){s.fail(Error::Input);__leave;}
  if(!s.pinCoveredStates()){s.fail(Error::Input);__leave;}
  if(!s.slots(true)){s.fail(Error::RawSlot);__leave;}
  auto&l=ar::lane;l.owner=this;l.lock=&s.control;l.armed=&s.armed;l.stopped=&s.stopped;l.ownerError=&s.error;l.save=&s.saveLane;l.hold=&s.hold;l.checkpoint=&s.checkpointActive;l.scopes=&s.activeScopes;l.input=c.input_binding;l.base=c.base;l.root=rp::state.root;l.world=rp::state.world;l.user=rp::state.user;
  if(!ARewardSaveOwnerSuppressedConfigure(&Impl::reward)){s.fail(Error::Bridge);__leave;}
  auto binding=c.storage;binding.owner=&s;binding.checkOwner=Impl::storageOwner;
  if(binding.checkOwnedReadBridge)binding.checkOwnedReadBridge=Impl::storageReadBridge;
  if(!s.gate.Open(binding)){s.fail(Error::Storage);__leave;}
  fs::Config fc{};fc.base=c.base;
  std::memcpy(fc.save_directory,c.save_directory,sizeof fc.save_directory);std::memcpy(fc.intent_directory,c.intent_directory,sizeof fc.intent_directory);
  fc.claim=ASaveUserOwnerClaim;fc.owner=ASaveUserOwnerCurrentOwner;fc.storage=s.gate.Api();
#ifdef A_SAVE_USER_OWNER_FIXTURE
  fc.binder=c.binder;fc.queue=c.queue;fc.caller=c.caller;
#endif
  if(!s.driver.Initialize(fc)){s.fail(Error::Driver);__leave;}
  // Driver verified the supported image and saved instruction profile. Keep
  // the two raw entry prefixes pinned as well, so a later entry detour cannot
  // silently become this owner's alleged native original.
  for(unsigned i=0;i<2;++i)std::memcpy(s.nativePrefix[i],reinterpret_cast<const void*>(c.base+originalRva[i]),32);
  InterlockedExchange(&s.codeReady,1);
  if(!s.slots(true)){s.fail(Error::RawSlot);__leave;}
  ASaveUserOwnerBridgeConfig bc{};bc.size=sizeof bc;bc.select=Impl::select;bc.before=Impl::before;bc.after=Impl::after;bc.finally=Impl::finally;bc.context=&s;
  checkpoint_load_hook_set::Binding hooks[2]{};
  for(unsigned i=0;i<2;++i){
   bc.original=reinterpret_cast<void*>(c.base+originalRva[i]);
   if(!ASaveUserOwnerBridgeConfigure(i,&bc)){s.fail(Error::Bridge);__leave;}
   hooks[i]={reinterpret_cast<void*volatile*>(c.base+slotRva[i]),bc.original,hook(i)};
  }
  if(!s.hooks.Initialize(hooks,2)){s.fail(Error::Hooks);__leave;}
  if(value(&s.stopped)){s.fail(Error::Stopped);__leave;}
  if(!planning_checkpoint_save::detail::RegisterOwner(this,&s,Impl::checkpoint)){s.fail(Error::Used);__leave;}
  a_save_abort::owner=this;a_save_abort::context=&s;a_save_abort::retire=&Impl::abortDrain;InterlockedExchange(&s.initialized,1);ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Config);}}
 __finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
bool Owner::Arm() noexcept {
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {
  if(!value(&s.initialized)||value(&s.armed)||value(&s.error)||value(&s.stopped))__leave;
  if(!s.slots(true)||!s.gate.Valid()){s.fail(Error::RawSlot);__leave;}
  // Save first, admission User last. Slot CAS/protection restoration are real;
  // this does not purport to stop all engine or input threads.
  if(value(&s.stopped))__leave;
  if(!s.hooks.Publish(1)){s.fail(Error::Arm);__leave;}
  if(value(&s.stopped))__leave;
  if(!s.hooks.Publish(0)){s.fail(Error::Arm);__leave;}
  if(value(&s.stopped))__leave;
  InterlockedExchange(&s.armed,1);ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
bool Owner::Submit(const fs::Request&q) noexcept {
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {__try {
  if(!value(&s.armed)||value(&s.error)||value(&s.stopped)||s.hold||s.saveLane||s.activeScopes||ar::lane.report.queued||ar::lane.report.active||ar::lane.report.readyFence)__leave;
  if(rp::read(rp::state.revoked)){s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();__leave;}
  if(q.room_epoch!=s.config.room_epoch||std::memcmp(q.room_id,s.config.room_id,32))__leave;
  const auto reportCursor=*reinterpret_cast<const unsigned short*>(rp::state.world+0x165A);
  if(!rp::observe(rp::Boundary::Submit,false)){InterlockedIncrement64(&rp::state.submitRejected);__leave;}
  if(!s.slots()||!s.gate.Valid()){s.fail(Error::Storage);s.driver.Stop();__leave;}
  if(reportCursor!=*reinterpret_cast<const unsigned short*>(rp::state.world+0x165A)){
   InterlockedIncrement64(&rp::state.submitRejected);rp::record(rp::Boundary::Submit,a_save_early_guard::Decision::Drift,false);__leave;
  }
  if(!value(&s.stopped)){ok=s.driver.Submit(q);if(ok){
   rp::state.cursor=reportCursor;rp::state.generation=q.generation;InterlockedExchange(&rp::state.pinned,1);s.saveLane=true;
  }}
 }__except(EXCEPTION_EXECUTE_HANDLER){
  InterlockedIncrement64(&rp::state.submitRejected);rp::record(rp::Boundary::Submit,a_save_early_guard::Decision::Unreadable,true);
  s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();
 }
 }__finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
bool Owner::SetUserHold(bool hold,std::uint64_t revision) noexcept {
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {
  if(!value(&s.armed)||value(&s.error)||value(&s.stopped)||s.saveLane||s.activeScopes||ar::lane.report.queued||ar::lane.report.active||ar::lane.report.readyFence||!revision||revision<=s.holdRevision)__leave;
  if(!s.slots()){s.fail(Error::RawSlot);s.driver.Stop();__leave;}
  s.hold=hold;s.holdObserved=false;s.holdRevision=revision;ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.control);}return ok;
}
void Owner::Stop() noexcept {
 auto&s=*p_;InterlockedExchange(&s.stopped,1);s.driver.Stop();AcquireSRWLockExclusive(&s.control);if(ar::lane.owner==this){ar::lane.report.queued=false;if(ar::lane.running)RewardOwnedCancel(ar::lane.running);}ReleaseSRWLockExclusive(&s.control);
 // No Gate.Stop/RestoreAll/unload: a bound save and cached frames may continue.
}
void Owner::Snapshot(Report&out) noexcept {
 auto&s=*p_;out={};out.error=Error(value(&s.error));out.initialized=value(&s.initialized);out.armed=value(&s.armed);out.stopped=value(&s.stopped);
 out.save=s.driver.Snapshot();s.gate.Snapshot(out.storage);s.hooks.Snapshot(out.hooks);
 for(unsigned i=0;i<2;++i)ASaveUserOwnerBridgeSnapshot(i,&out.bridges[i]);
 AcquireSRWLockExclusive(&s.control);
 __try {out.hold_revision=s.holdRevision;out.held_scopes=s.heldScopes;out.active_scopes=s.activeScopes;out.user_hold_requested=s.hold&&!value(&s.stopped);out.user_subset_held=s.hold&&s.holdObserved&&!s.activeScopes&&!value(&s.error)&&!value(&s.stopped);out.save_lane=s.saveLane;}
 __finally{ReleaseSRWLockExclusive(&s.control);}
}
bool Owner::CopyArtifact(std::uint64_t generation,fs::Artifact&out) noexcept{
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
  __try {
   if(s.checkpointActive||!value(&s.initialized)||!rp::read(rp::state.ready)||rp::state.owner!=this)__leave;
   // The sidecar pins the currently admitted generation. Old artifacts may be
   // retained by Driver, but cannot be re-exported under a newer report sample.
   if(!generation||generation!=rp::state.generation){InterlockedIncrement64(&rp::state.copyRejected);rp::record(rp::Boundary::Copy,a_save_early_guard::Decision::Binding,false);__leave;}
   // IPC polls CopyArtifact during the six-state Save phase. NotReady is not a
   // planning failure, and must not turn a healthy in-progress save into fault.
   const auto saved=s.driver.Snapshot();
   if(saved.generation!=generation||saved.status!=fs::Status::Complete)__leave;
   if(rp::read(rp::state.revoked)||!rp::observe(rp::Boundary::Copy,true)||!rp::fields()){
    rp::record(rp::Boundary::Copy,a_save_early_guard::Decision::Drift,true);InterlockedIncrement64(&rp::state.copyRejected);
    s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();__leave;
   }
   if(!value(&s.error)&&!value(&s.stopped))ok=s.driver.CopyArtifact(generation,out);
  }
 __finally{ReleaseSRWLockExclusive(&s.control);}return ok;
}
}

#include "planning_checkpoint_save_lifecycle.inc"
#include "planning_checkpoint_save_owner_entry.inc"
