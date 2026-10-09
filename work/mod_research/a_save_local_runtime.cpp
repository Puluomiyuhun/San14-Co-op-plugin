#include "a_save_local_runtime.h"
#include <cstring>
#include <new>
namespace a_save_local_runtime {
namespace {
std::uint64_t birth()noexcept {FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}
bool nonzero(const unsigned char*p,size_t n){unsigned value=0;for(size_t i=0;i<n;++i)value|=p[i];return value!=0;}
bool nativeBinding(const checkpoint_native_input::Binding&a,const checkpoint_native_input::Binding&b){return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
bool terminated(const wchar_t*p,size_t n){return p[0]&&wmemchr(p,L'\0',n)!=nullptr;}
}
bool Runtime::identity()const noexcept {if(!copied_||GetCurrentProcessId()!=c_.pid||birth()!=c_.birth||uintptr_t(GetModuleHandleW(nullptr))!=c_.base)return false;
 __try {if(at<uintptr_t>(c_.base+0x1FCA1E0)!=c_.source.root||at<uintptr_t>(c_.source.root+0x85130)!=c_.source.world||at<uintptr_t>(c_.base+0x2025318)!=c_.source.cache)return false;
 const auto w=c_.source.world;const auto force=at<uintptr_t>(c_.source.root+0xDCA0+c_.force*8);
 return at<std::uint16_t>(w+0x34)==c_.year&&at<std::uint8_t>(w+0x36)==c_.month&&at<std::uint8_t>(w+0x37)==c_.day&&at<std::uint8_t>(w+0x3A)==c_.force&&force&&at<std::uint16_t>(force+0x10)==c_.ruler;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void Runtime::fail(Error e)noexcept {AcquireSRWLockExclusive(&lock_);if(r_.error==Error::None)r_.error=e;ReleaseSRWLockExclusive(&lock_);}
bool Runtime::storageOwner(void*v,const sb::Attachment&a,sb::Point)noexcept {auto&s=*static_cast<Runtime*>(v);const auto&b=s.c_.storage.attachment;
 // Do not consult Owner/Gate/Driver or take their locks from this callback.
 return s.identity()&&a.pid==b.pid&&a.birth==b.birth&&a.base==b.base&&a.attempt==b.attempt&&a.generation==b.generation&&!memcmp(a.id,b.id,32)&&!memcmp(a.gameSha256,b.gameSha256,32);}
bool Runtime::planningSample(void*v,uintptr_t user,unsigned actor,a_reward_save_owner::Source&out){auto&s=*static_cast<Runtime*>(v);out={};
 if(!s.identity()||user!=s.c_.source.states[4]||actor!=s.c_.force)return false;
 checkpoint_native_input_pending::Config pending{};if(!s.sampler_.Capture(pending))return false;
 out.admission.binding=s.c_.planning;out.admission.pending=pending;out.admission.reward=reinterpret_cast<ph::RewardOriginal>(s.c_.base+0x1D6DA0);
 out.reward.binding=s.c_.planning;out.reward.base=s.c_.base;out.reward.root=s.c_.source.root;out.reward.world=s.c_.source.world;out.reward.user=user;
 out.reward.authorized_force=s.c_.force;out.reward.authorized_ruler=s.c_.ruler;
 // Deliberately leave replay ctor/append/dtor/predicate/capture/buffers empty.
 // This supplies only lifecycle::fresh's read-only identity/pending contract.
 // Runtime exposes no reward Submit and reports no completed reward receipt.
 return true;}
bool Runtime::rawInline()const noexcept {__try {for(const auto&p:plans_.gate.patches)if(!p.size||p.size>sizeof p.before||memcmp(reinterpret_cast<void*>(p.address),p.before,p.size))return false;
 return plans_.parent.site&&!memcmp(reinterpret_cast<void*>(plans_.parent.site),plans_.parent.before,5);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool Runtime::Prepare(const Config&c,Plans&out)noexcept {out={};if(InterlockedCompareExchange(&once_,1,0)){fail(Error::Used);return false;}
 if(!c.pid||!c.birth||!c.base||!c.nativeRoomEpoch||!nonzero(c.roomId,32)||!c.year||c.month<1||c.month>12||(c.day!=1&&c.day!=11&&c.day!=21)||!c.force||c.force>=51||c.ruler>=1000||
 !terminated(c.saveDirectory,512)||!terminated(c.intentDirectory,512)||c.source.base!=c.base||!nativeBinding(c.planning.native,c.source.binding)||!c.planning.period||!c.planning.epoch||!nonzero(c.planning.room_input_digest.data(),32)||
 c.storage.attachment.pid!=c.pid||c.storage.attachment.birth!=c.birth||c.storage.attachment.base!=c.base||c.storage.checkOwner||c.storage.checkOwnedReadBridge||c.storage.owner||c.storage.ownedReadBridge.address){fail(Error::Config);return false;}
 c_=c;copied_=true;if(!identity()){fail(Error::Identity);return false;}
 if(!sampler_.Initialize(c.source)){fail(Error::Sampler);return false;}checkpoint_native_input_pending::Config pending{};
 if(!sampler_.Capture(pending)){fail(Error::Sampler);return false;}checkpoint_native_input_pending::Adapter inspector;
 if(inspector.Bind(pending)!=checkpoint_native_input_pending::Error::None){fail(Error::Sampler);return false;}
 try {owner_=new a_save_user_owner::Owner;gate_=new a_save_upstream_gate::Owner;}catch(...){fail(Error::Owner);return false;}
 a_save_user_owner::Config owner{};owner.base=c.base;owner.room_epoch=c.nativeRoomEpoch;memcpy(owner.room_id,c.roomId,32);wcscpy_s(owner.save_directory,c.saveDirectory);wcscpy_s(owner.intent_directory,c.intentDirectory);
 owner.storage=c.storage;owner.storage.owner=this;owner.storage.checkOwner=storageOwner;owner.sample_input=a_save_local_binding::Sampler::Sample;owner.input_context=&sampler_;owner.input_binding=c.source.binding;
 if(!owner_->Initialize(owner)){fail(Error::Owner);return false;}
 a_save_upstream_gate::Config gate{};gate.base=c.base;gate.root=c.source.root;gate.world=c.source.world;gate.saveOwner=owner_;gate.binding=c.source.binding;gate.sample=a_save_local_binding::Sampler::Sample;gate.context=&sampler_;
 if(!gate_->Initialize(gate)||!gate_->PreparedPlan(plans_.gate)){fail(Error::Gate);return false;}
 planning_input_interlock::Config planning{};planning.owner=owner_;planning.gate=gate_;planning.binding=c.planning;planning.base=c.base;planning.root=c.source.root;planning.world=c.source.world;
 a_save_parent_adapter::Config parent{planning,&controller_,&mailbox_,&host_,&producer_,1};if(!parent_.Initialize(parent)||!parent_.PreparedPlan(plans_.parent)){fail(Error::Parent);return false;}
 a_save_user_owner::Report u{};owner_->Snapshot(u);a_save_upstream_gate::Report g{};gate_->Snapshot(g);plans_.ownerSlots=u.hooks;plans_.gateSlots=g.hooks;
 AcquireSRWLockExclusive(&lock_);r_.prepared=1;ReleaseSRWLockExclusive(&lock_);out=plans_;return true;}
bool Runtime::ArmOwner()noexcept {if(!r_.prepared||r_.ownerArmed||r_.sourcesArmed||InterlockedCompareExchange(&stopped_,0,0)||!identity()||!rawInline()){fail(Error::Order);return false;}
 if(!owner_->Arm()){fail(Error::Owner);return false;}a_reward_save_owner::Config reward{};reward.binding=c_.planning;reward.sample=planningSample;reward.context=this;
 if(!a_reward_save_owner::Bind(*owner_,reward)){fail(Error::Reward);Stop();return false;}
 AcquireSRWLockExclusive(&lock_);r_.ownerArmed=1;ReleaseSRWLockExclusive(&lock_);return true;}
bool Runtime::ArmPublishedSources()noexcept {if(!r_.ownerArmed||r_.sourcesArmed||InterlockedCompareExchange(&stopped_,0,0)||!identity()){fail(Error::Order);return false;}
 if(!gate_->Arm()){fail(Error::Gate);Stop();return false;}if(!parent_.Arm()){fail(Error::Parent);Stop();return false;}
 AcquireSRWLockExclusive(&lock_);r_.sourcesArmed=1;ReleaseSRWLockExclusive(&lock_);return true;}
bool Runtime::permit(void*v,const checkpoint_fresh_save::Request&q,const unsigned char*binding)noexcept {auto&s=*static_cast<Runtime*>(v);Report report{};s.Snapshot(report);
 return report.readyForControlledRequest&&s.identity()&&binding&&nonzero(binding,32)&&q.generation==1&&q.period==s.c_.planning.period&&q.cut==0&&q.room_epoch==s.c_.nativeRoomEpoch&&!memcmp(q.room_id,s.c_.roomId,32)&&
 q.year==s.c_.year&&q.month==s.c_.month&&q.day==s.c_.day&&q.force==s.c_.force&&q.ruler==s.c_.ruler;}
void Runtime::executionStop(void*v)noexcept {static_cast<a_save_dispatch_mailbox::Adapter*>(v)->Stop();}
bool Runtime::ConfigureTransport(a_save_dispatch_ipc::Config&out)noexcept {Report report{};Snapshot(report);if(!report.readyForControlledRequest)return false;
 out.owner=owner_;out.room_epoch=c_.nativeRoomEpoch;memcpy(out.room_id,c_.roomId,32);out.permit=permit;out.permitContext=this;
 out.submit=a_save_dispatch_mailbox::Adapter::SubmitPort;out.copy=a_save_dispatch_mailbox::Adapter::CopyPort;out.executionContext=&execution_;out.executionStop=executionStop;return true;}
void Runtime::Stop()noexcept {InterlockedExchange(&stopped_,1);mailbox_.Stop();parent_.Stop();if(owner_)owner_->Stop();
 // Preserve Gate while a committed Save drains; never unlock producer here.
 AcquireSRWLockExclusive(&lock_);r_.stopped=1;ReleaseSRWLockExclusive(&lock_);}
void Runtime::Snapshot(Report&out)noexcept {AcquireSRWLockShared(&lock_);out=r_;ReleaseSRWLockShared(&lock_);
 if(owner_){owner_->Snapshot(out.owner);a_reward_save_owner::Snapshot(*owner_,out.reward);}if(gate_)gate_->Snapshot(out.gate);parent_.Snapshot(out.parent);mailbox_.Snapshot(out.mailbox);
 out.readyForControlledRequest=out.sourcesArmed&&!InterlockedCompareExchange(&stopped_,0,0)&&out.error==Error::None&&out.parent.hostInitialized&&!out.parent.stopped&&out.parent.error==a_save_parent_adapter::Error::None&&
 !out.owner.stopped&&out.owner.error==a_save_user_owner::Error::None&&!out.gate.stopped&&out.gate.error==a_save_upstream_gate::Error::None&&!out.mailbox.stopped&&out.reward.bound&&out.reward.readyFence&&!out.reward.queued&&!out.reward.active&&!out.reward.submitted&&!out.reward.completed;}
}
