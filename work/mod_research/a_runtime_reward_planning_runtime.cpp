#include "a_runtime_reward_planning_runtime.h"
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
bool Runtime::inputSample(void*v,checkpoint_native_input_pending::Config&out)noexcept{auto&s=*static_cast<Runtime*>(v);return InterlockedCompareExchange(&s.sourceIndex_,0,0)?s.nextSampler_.Capture(out):s.sampler_.Capture(out);}
bool Runtime::identity()const noexcept {return identity(periods_[InterlockedCompareExchange(const_cast<volatile LONG*>(&activePeriod_),0,0)]);}
bool Runtime::identity(const Period&period)const noexcept {if(!copied_||GetCurrentProcessId()!=c_.pid||birth()!=c_.birth
#ifndef A_SAVE_REPEAT_FIXTURE
 ||uintptr_t(GetModuleHandleW(nullptr))!=c_.base
#endif
)return false;
 __try {if(at<uintptr_t>(c_.base+0x1FCA1E0)!=c_.source.root||at<uintptr_t>(c_.source.root+0x85130)!=c_.source.world||at<uintptr_t>(c_.base+0x2025318)!=c_.source.cache)return false;
 const auto w=c_.source.world;const auto force=at<uintptr_t>(c_.source.root+0xDCA0+c_.force*8);
 return at<std::uint16_t>(w+0x34)==period.year&&at<std::uint8_t>(w+0x36)==period.month&&at<std::uint8_t>(w+0x37)==period.day&&at<std::uint8_t>(w+0x3A)==c_.force&&force&&at<std::uint16_t>(force+0x10)==c_.ruler;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void Runtime::fail(Error e)noexcept {AcquireSRWLockExclusive(&lock_);if(r_.error==Error::None)r_.error=e;ReleaseSRWLockExclusive(&lock_);}
bool Runtime::storageOwner(void*v,const sb::Attachment&a,sb::Point)noexcept {auto&s=*static_cast<Runtime*>(v);const auto&b=s.c_.storage.attachment;
 // Do not consult Owner/Gate/Driver or take their locks from this callback.
 return s.identity()&&a.pid==b.pid&&a.birth==b.birth&&a.base==b.base&&a.attempt==b.attempt&&a.generation==b.generation&&!memcmp(a.id,b.id,32)&&!memcmp(a.gameSha256,b.gameSha256,32);}
bool Runtime::planningSample(void*v,uintptr_t user,unsigned actor,a_reward_save_owner::Source&out){auto&period=*static_cast<Period*>(v);auto&s=*period.self;out={};
 if(!s.identity(period)||user!=s.sources_[InterlockedCompareExchange(&s.sourceIndex_,0,0)].states[4])return false;
 if(InterlockedCompareExchange(&s.rewardCapture_,0,0))return s.rewardSources_[unsigned(&period-s.periods_)].Capture(user,actor,out);
 if(actor!=s.c_.force)return false;
 checkpoint_native_input_pending::Config pending{};if(!inputSample(&s,pending))return false;
 out.admission.binding=period.binding;out.admission.pending=pending;out.admission.reward=reinterpret_cast<ph::RewardOriginal>(s.c_.base+0x1D6DA0);
 out.reward.binding=period.binding;out.reward.base=s.c_.base;out.reward.root=s.c_.source.root;out.reward.world=s.c_.source.world;out.reward.user=user;
 out.reward.authorized_force=s.c_.force;out.reward.authorized_ruler=s.c_.ruler;
 // Deliberately leave replay ctor/append/dtor/predicate/capture/buffers empty.
 // This supplies only lifecycle::fresh's read-only identity/pending contract.
 // Actual reward callback switches to the fixed replay source above.
 return true;}
bool Runtime::rawInline()const noexcept {__try {for(const auto&p:plans_.gate.patches)if(!p.size||p.size>sizeof p.before||memcmp(reinterpret_cast<void*>(p.address),p.before,p.size))return false;
 return plans_.parent.site&&!memcmp(reinterpret_cast<void*>(plans_.parent.site),plans_.parent.before,5);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool Runtime::Prepare(const Config&c,Plans&out)noexcept {out={};if(InterlockedCompareExchange(&once_,1,0)){fail(Error::Used);return false;}
 if(!c.pid||!c.birth||!c.base||!c.nativeRoomEpoch||!nonzero(c.roomId,32)||!c.year||c.month<1||c.month>12||(c.day!=1&&c.day!=11&&c.day!=21)||!c.force||c.force>=51||c.ruler>=1000||
 !terminated(c.saveDirectory,512)||!terminated(c.intentDirectory,512)||c.source.base!=c.base||!nativeBinding(c.planning.native,c.source.binding)||!c.planning.period||!c.planning.epoch||!nonzero(c.planning.room_input_digest.data(),32)||
 c.storage.attachment.pid!=c.pid||c.storage.attachment.birth!=c.birth||c.storage.attachment.base!=c.base||c.storage.checkOwner||c.storage.checkOwnedReadBridge||c.storage.owner||c.storage.ownedReadBridge.address){fail(Error::Config);return false;}
 c_=c;sources_[0]=c.source;for(unsigned i=0;i<5;++i)stateVtables_[i]=at<uintptr_t>(c.source.states[i]);periods_[0]={this,c.planning,c.year,c.month,c.day};copied_=true;if(!identity()){fail(Error::Identity);return false;}
 if(!sampler_.Initialize(c.source)){fail(Error::Sampler);return false;}checkpoint_native_input_pending::Config pending{};
 if(!sampler_.Capture(pending)){fail(Error::Sampler);return false;}checkpoint_native_input_pending::Adapter inspector;
 if(inspector.Bind(pending)!=checkpoint_native_input_pending::Error::None){fail(Error::Sampler);return false;}
 try {owner_=new a_save_user_owner::Owner;gate_=new a_save_upstream_gate::Owner;}catch(...){fail(Error::Owner);return false;}
 a_save_user_owner::Config owner{};owner.base=c.base;owner.room_epoch=c.nativeRoomEpoch;memcpy(owner.room_id,c.roomId,32);wcscpy_s(owner.save_directory,c.saveDirectory);wcscpy_s(owner.intent_directory,c.intentDirectory);
 owner.storage=c.storage;owner.storage.owner=this;owner.storage.checkOwner=storageOwner;owner.sample_input=inputSample;owner.input_context=this;owner.input_binding=c.source.binding;
 #ifdef A_SAVE_REPEAT_FIXTURE
 owner.binder=c.fixtureBinder;owner.queue=c.fixtureQueue;owner.caller=c.fixtureUserCaller;
#endif
 if(!owner_->Initialize(owner)){fail(Error::Owner);return false;}
 a_save_upstream_gate::Config gate{};gate.base=c.base;gate.root=c.source.root;gate.world=c.source.world;gate.saveOwner=owner_;gate.binding=c.source.binding;gate.sample=inputSample;gate.context=this;
 #ifdef A_SAVE_REPEAT_FIXTURE
 gate.fixtureGameCaller=c.fixtureGameCaller;gate.fixtureUiCaller=c.fixtureUiCaller;
#endif
 if(!gate_->Initialize(gate)||!gate_->PreparedPlan(plans_.gate)){fail(Error::Gate);return false;}
 planning_input_interlock::Config planning{};planning.owner=owner_;planning.gate=gate_;planning.binding=c.planning;planning.base=c.base;planning.root=c.source.root;planning.world=c.source.world;
 a_save_parent_adapter::Config parent{planning,&controller_,&mailbox_,&host_,&producer_,1};if(!parent_.Initialize(parent)||!parent_.PreparedPlan(plans_.parent)){fail(Error::Parent);return false;}
 if(!a_save_repeat_parent::Bind(parent_,this,repeatBefore,repeatAfter,repeatCancel)){fail(Error::Parent);return false;}
 a_save_user_owner::Report u{};owner_->Snapshot(u);a_save_upstream_gate::Report g{};gate_->Snapshot(g);plans_.ownerSlots=u.hooks;plans_.gateSlots=g.hooks;
 AcquireSRWLockExclusive(&lock_);r_.prepared=1;ReleaseSRWLockExclusive(&lock_);out=plans_;return true;}
bool Runtime::ArmOwner()noexcept {if(!r_.prepared||r_.ownerArmed||r_.sourcesArmed||InterlockedCompareExchange(&stopped_,0,0)||!identity()||!rawInline()){fail(Error::Order);return false;}
 if(!owner_->Arm()){fail(Error::Owner);return false;}a_reward_save_owner::Config reward{};reward.binding=c_.planning;reward.sample=planningSample;reward.context=&periods_[0];
 if(!a_reward_save_owner::Bind(*owner_,reward)){fail(Error::Reward);Stop();return false;}
 AcquireSRWLockExclusive(&lock_);r_.ownerArmed=1;ReleaseSRWLockExclusive(&lock_);return true;}
bool Runtime::ArmPublishedSources()noexcept {if(!r_.ownerArmed||r_.sourcesArmed||InterlockedCompareExchange(&stopped_,0,0)||!identity()){fail(Error::Order);return false;}
 if(!gate_->Arm()){fail(Error::Gate);Stop();return false;}if(!parent_.Arm()){fail(Error::Parent);Stop();return false;}
 AcquireSRWLockExclusive(&lock_);r_.sourcesArmed=1;ReleaseSRWLockExclusive(&lock_);return true;}
bool Runtime::permit(void*v,const checkpoint_fresh_save::Request&q,const unsigned char*binding)noexcept {auto&s=*static_cast<Runtime*>(v);Report report{};s.Snapshot(report);
 const auto index=InterlockedCompareExchange(&s.activePeriod_,0,0);const auto&period=s.periods_[index];
 return report.readyForControlledRequest&&s.identity(period)&&binding&&nonzero(binding,32)&&q.generation==std::uint64_t(index+1)&&q.period==period.binding.period&&q.cut==report.reward.completed&&q.room_epoch==s.c_.nativeRoomEpoch&&!memcmp(q.room_id,s.c_.roomId,32)&&
 q.year==period.year&&q.month==period.month&&q.day==period.day&&q.force==s.c_.force&&q.ruler==s.c_.ruler;}
void Runtime::executionStop(void*v)noexcept {static_cast<a_save_dispatch_mailbox::Adapter*>(v)->Stop();}
bool Runtime::ConfigureTransport(a_save_dispatch_ipc::Config&out)noexcept {Report report{};Snapshot(report);if(!report.readyForControlledRequest)return false;
 out.owner=owner_;out.room_epoch=c_.nativeRoomEpoch;memcpy(out.room_id,c_.roomId,32);out.permit=permit;out.permitContext=this;
 out.submit=a_save_dispatch_mailbox::Adapter::SubmitPort;out.copy=a_save_dispatch_mailbox::Adapter::CopyPort;out.executionContext=&execution_;out.executionStop=executionStop;return true;}
void Runtime::Stop()noexcept {InterlockedExchange(&stopped_,1);AcquireSRWLockExclusive(&lock_);if(reward_.state==RewardState::Queued||reward_.state==RewardState::Executing){reward_.state=RewardState::Failed;reward_.error=RewardError::Stopped;reward_.uncertain=rewardFrame_;}ReleaseSRWLockExclusive(&lock_);mailbox_.Stop();parent_.Stop();if(owner_)owner_->Stop();
 // Preserve Gate while a committed Save drains; never unlock producer here.
 AcquireSRWLockExclusive(&lock_);r_.stopped=1;repeat_.stopped=1;planning_.stopped=true;if(planning_.state==PlanningState::Queued){planning_.state=PlanningState::Failed;planning_.error=PlanningError::Stopped;}planning_.opened=false;ReleaseSRWLockExclusive(&lock_);}
void Runtime::Snapshot(Report&out)noexcept {AcquireSRWLockShared(&lock_);out=r_;const bool repeatReady=planning_.state!=PlanningState::Queued&&planning_.state!=PlanningState::Opened&&(repeat_.state==RepeatState::Idle||repeat_.state==RepeatState::ReadySecond)&&reward_.state!=RewardState::Queued&&reward_.state!=RewardState::Executing&&reward_.state!=RewardState::Failed;ReleaseSRWLockShared(&lock_);
 if(owner_){owner_->Snapshot(out.owner);a_reward_save_owner::Snapshot(*owner_,out.reward);}if(gate_)gate_->Snapshot(out.gate);parent_.Snapshot(out.parent);mailbox_.Snapshot(out.mailbox);
 out.readyForControlledRequest=repeatReady&&out.sourcesArmed&&!InterlockedCompareExchange(&stopped_,0,0)&&out.error==Error::None&&out.parent.hostInitialized&&!out.parent.stopped&&out.parent.error==a_save_parent_adapter::Error::None&&
 !out.owner.stopped&&out.owner.error==a_save_user_owner::Error::None&&!out.gate.stopped&&out.gate.error==a_save_upstream_gate::Error::None&&!out.mailbox.stopped&&out.reward.bound&&out.reward.readyFence&&!out.reward.queued&&!out.reward.active&&out.reward.submitted==out.reward.completed&&!out.reward.uncertain;
 AcquireSRWLockShared(&lock_);out.rewardReplayEnabled=reward_.configured;ReleaseSRWLockShared(&lock_);}
bool Runtime::RequestNext(const Next&n)noexcept {
 if(n.previousGeneration!=1||n.generation!=2||n.period!=c_.planning.period+1||n.epoch<=c_.planning.epoch||!nonzero(n.previousSha256,32)||!nonzero(n.inputDigest,32)||!memcmp(n.inputDigest,c_.planning.room_input_digest.data(),32))return false;
 auto y=c_.year;auto m=c_.month;auto d=c_.day;if(d==21){d=1;if(m==12){m=1;if(y==65535)return false;++y;}else ++m;}else d=static_cast<unsigned char>(d+10);
 if(n.year!=y||n.month!=m||n.day!=d)return false;
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {if(!r_.sourcesArmed||reward_.state==RewardState::Queued||reward_.state==RewardState::Executing||reward_.state==RewardState::Failed||planning_.state==PlanningState::Queued||planning_.state==PlanningState::Failed||repeat_.requested||InterlockedCompareExchange(&stopped_,0,0)||r_.error!=Error::None)__leave;
  if(planning_.opened){planning_.opened=false;planning_.state=PlanningState::Retired;}repeat_.request=n;repeat_.requested=1;repeat_.state=RepeatState::Queued;periods_[1]={this,c_.planning,n.year,n.month,n.day};periods_[1].binding.period=n.period;periods_[1].binding.epoch=n.epoch;memcpy(periods_[1].binding.room_input_digest.data(),n.inputDigest,32);ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Runtime::RepeatSnapshot(RepeatReport&out)noexcept {AcquireSRWLockShared(&lock_);out=repeat_;ReleaseSRWLockShared(&lock_);}
bool Runtime::repeatBefore(void*v)noexcept{return static_cast<Runtime*>(v)->onRepeatBefore();}
bool Runtime::repeatAfter(void*v)noexcept{return static_cast<Runtime*>(v)->onRepeatAfter();}
bool Runtime::repeatCancel(void*v)noexcept{return static_cast<Runtime*>(v)->onRepeatCancel();}
bool Runtime::repeatFail(RepeatError e)noexcept {
 if(repeat_.error==RepeatError::None)repeat_.error=e;repeat_.state=RepeatState::Failed;repeat_.stopped=1;InterlockedExchange(&stopped_,1);r_.stopped=1;if(r_.error==Error::None)r_.error=Error::Order;mailbox_.Stop();if(owner_)owner_->Stop();return false;
}
bool Runtime::onRepeatBefore()noexcept {
 if(!planningBefore())return false;
 if(!rewardBefore())return false;
 if(!a_save_parent_adapter::CurrentBoundary(c_.base))return false;AcquireSRWLockExclusive(&lock_);bool ok=true;checkpoint_fresh_save::Artifact*previous=nullptr;
 __try {__try {
  if(!repeat_.requested||repeat_.state==RepeatState::ReadySecond||repeat_.state==RepeatState::Failed||InterlockedCompareExchange(&stopped_,0,0))__leave;
  a_save_dispatch_host::Report h{};mailbox_.Snapshot(r_.mailbox);
  if(!host_.Snapshot(h)||h.thread!=GetCurrentThreadId()||h.frame||h.lease||h.state!=a_save_dispatch_host::State::Complete){ok=repeatFail(RepeatError::Boundary);__leave;}
  repeat_.hostThread=h.thread;
  if(repeat_.state==RepeatState::Queued){
   if(r_.mailbox.stopped||r_.mailbox.count!=1||r_.mailbox.records[0].state!=a_save_dispatch_mailbox::State::Delivered||r_.mailbox.records[0].message.request.generation!=1){ok=repeatFail(RepeatError::Delivery);__leave;}
   previous=new(std::nothrow)checkpoint_fresh_save::Artifact;if(!previous){ok=repeatFail(RepeatError::Delivery);__leave;}
   if(!owner_->CopyArtifact(1,*previous)||previous->report.status!=checkpoint_fresh_save::Status::Complete||!previous->report.file_bytes_verified||memcmp(previous->sha256,repeat_.request.previousSha256,32)){ok=repeatFail(RepeatError::Delivery);__leave;}
   repeat_.previousArtifactMatched=true;
   if(!TryAcquireSRWLockExclusive(&producer_))__leave;repeatLease_=true;repeat_.lease=repeat_.frame=repeat_.drainPending=true;
   planning_input_interlock::Report observed{};controller_.Snapshot(observed);repeatRevision_=observed.revision;
   if(!identity(periods_[0])||!controller_.BeginObservation(repeatRevision_)){ReleaseSRWLockExclusive(&producer_);repeatLease_=false;repeat_.lease=repeat_.frame=repeat_.drainPending=false;ok=repeatFail(RepeatError::Observation);__leave;}
   repeat_.state=RepeatState::Observing;
  }else if(repeat_.state==RepeatState::RetiredWaitingDate){
   // No date writer or simulation call: remain retired until the actual world is next.
   if(!stableIdentity()){ok=repeatFail(RepeatError::Boundary);__leave;}
   ++runningFrames_;
   const auto w=c_.source.world;const unsigned now=(unsigned(at<std::uint16_t>(w+0x34))*12+at<std::uint8_t>(w+0x36))*32+at<std::uint8_t>(w+0x37);
   const unsigned old=(unsigned(c_.year)*12+c_.month)*32+c_.day,nextDate=(unsigned(periods_[1].year)*12+periods_[1].month)*32+periods_[1].day;
   if(now<old||now>nextDate){ok=repeatFail(RepeatError::Date);__leave;}
   if(!identity(periods_[1]))__leave;
   if(!returnSource())__leave;
   if(reward_.configured&&!rewardSource(1)){ok=repeatFail(RepeatError::Rebind);__leave;}
   a_reward_save_owner::Config next{};next.binding=periods_[1].binding;next.sample=planningSample;next.context=&periods_[1];
   if(!planning_period_owner::Rebind(*owner_,*gate_,next,retired_.serial)){ok=repeatFail(RepeatError::Rebind);__leave;}
   planning_input_interlock::Config pc{};pc.owner=owner_;pc.gate=gate_;pc.binding=periods_[1].binding;pc.base=c_.base;pc.root=c_.source.root;pc.world=c_.source.world;
   if(!secondController_.Initialize(pc)){ok=repeatFail(RepeatError::Controller);__leave;}
   if(!host_.BindPeriod(secondController_)){ok=repeatFail(RepeatError::Host);__leave;}
   if(!a_native_turn::Transition(*gate_,{a_native_turn::Action::End,retired_.serial,nullptr})){ok=repeatFail(RepeatError::Host);__leave;}
   repeat_.drainPending=false;InterlockedExchange(&activePeriod_,1);repeat_.activeGeneration=2;repeat_.nativeDateMatched=true;repeat_.state=RepeatState::ReadySecond;
  }
 }__except(EXCEPTION_EXECUTE_HANDLER){ok=repeatFail(RepeatError::Boundary);}}
 __finally{delete previous;ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Runtime::onRepeatAfter()noexcept {
 if(!rewardAfter())return false;
 if(!a_save_parent_adapter::CurrentBoundary(c_.base))return false;AcquireSRWLockExclusive(&lock_);bool ok=true;
 __try {__try {
  if(!repeatLease_)__leave;
  const bool observed=controller_.EndObservation(repeatRevision_);
  if(InterlockedCompareExchange(&stopped_,0,0)||!observed){ok=repeatFail(RepeatError::Observation);__leave;}
  if(!planning_period_owner::Retire(*owner_,*gate_,controller_,periods_[0].binding,retired_)){ok=repeatFail(RepeatError::Retire);__leave;}
  repeat_.retiredSerial=retired_.serial;repeat_.retiredCount=1;repeat_.state=RepeatState::RetiredWaitingDate;
  if(!a_native_turn::Transition(*gate_,{a_native_turn::Action::Begin,retired_.serial,nullptr})){ok=repeatFail(RepeatError::Host);__leave;}
  repeat_.drainPending=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){ok=repeatFail(RepeatError::Boundary);}}
 __finally{if(repeatLease_){ReleaseSRWLockExclusive(&producer_);repeatLease_=false;repeat_.lease=repeat_.frame=false;repeat_.drainPending=a_native_turn::Running();}ReleaseSRWLockExclusive(&lock_);}return ok;
}

bool Runtime::onRepeatCancel()noexcept {
 if(!a_save_parent_adapter::CurrentBoundary(c_.base))return false;AcquireSRWLockExclusive(&lock_);
 __try {if(rewardFrame_){rewardFail(RewardError::Boundary);rewardFrame_=false;}if(repeatLease_){controller_.EndObservation(repeatRevision_);repeatFail(RepeatError::Boundary);}else if(a_native_turn::Running())repeatFail(RepeatError::Boundary);}
 __finally{if(repeatLease_){ReleaseSRWLockExclusive(&producer_);repeatLease_=false;repeat_.lease=repeat_.frame=false;repeat_.drainPending=a_native_turn::Running();}ReleaseSRWLockExclusive(&lock_);}return false;
}

}

namespace a_save_local_runtime {
namespace {
bool rewardBinding(const ph::Binding&a,const ph::Binding&b)noexcept{return nativeBinding(a.native,b.native)&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
}
bool Runtime::rewardSource(unsigned i)noexcept {
 a_runtime_reward_source::Config s{};const auto&p=periods_[i];s.base=c_.base;s.root=c_.source.root;s.world=c_.source.world;s.user=sources_[i].states[4];s.binding=p.binding;
 s.year=p.year;s.month=p.month;s.day=p.day;s.viewer=c_.force;memcpy(s.actors,rewardConfig_.actors,sizeof s.actors);s.sample_input=inputSample;s.input_context=this;return rewardSources_[i].Initialize(s);
}
bool Runtime::ConfigureReward(const RewardConfig&c)noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {if(reward_.configured||reward_.state!=RewardState::Disabled||!r_.prepared||InterlockedCompareExchange(&stopped_,0,0)||repeat_.requested||!rewardBinding(c.binding,periods_[0].binding))__leave;
  if(c.actors[0].force==c.actors[1].force)__leave;bool viewer=false;
  for(const auto&a:c.actors){if(!a.force||a.force>=51||!a.ruler||a.ruler>=6000||!a.district||a.district>=52)__leave;if(a.force==c_.force&&a.ruler==c_.ruler)viewer=true;}
  if(!viewer)__leave;rewardConfig_=c;reward_.state=RewardState::Failed;reward_.error=RewardError::Config;
  if(!rewardSource(0))__leave;reward_.binding=c.binding;reward_.configured=true;reward_.state=RewardState::Idle;reward_.error=RewardError::None;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Runtime::SubmitReward(const ph::Binding&binding,std::uint64_t sequence,const a_reward_save_owner::rw::Command&command)noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {const auto index=InterlockedCompareExchange(&activePeriod_,0,0);const auto&p=periods_[index];
  if(!reward_.configured||(reward_.state!=RewardState::Idle&&reward_.state!=RewardState::Complete)||!r_.sourcesArmed||r_.error!=Error::None||InterlockedCompareExchange(&stopped_,0,0)||
   (repeat_.state!=RepeatState::Idle&&repeat_.state!=RepeatState::ReadySecond)||!rewardBinding(binding,p.binding)||!identity(p))__leave;
  a_save_parent_adapter::Report parent{};parent_.Snapshot(parent);if(!parent.hostInitialized||parent.stopped||parent.error!=a_save_parent_adapter::Error::None)__leave;
  a_reward_save_owner::Report actual{};a_reward_save_owner::Snapshot(*owner_,actual);a_save_user_owner::Report own{};owner_->Snapshot(own);
  a_save_dispatch_mailbox::Report mail{};mailbox_.Snapshot(mail);
  if(actual.error!=a_reward_save_owner::Error::None||actual.queued||actual.active||actual.uncertain||!actual.readyFence||actual.submitted!=actual.completed||sequence!=actual.submitted+1||!sequence||own.save_lane||own.stopped||mail.stopped||(mail.count!=unsigned(index)&&!(index==0&&planning_.opened&&planning_.state==PlanningState::Opened&&mail.count==1)))__leave;
  for(unsigned i=0;i<mail.count;++i)if(mail.records[i].state!=a_save_dispatch_mailbox::State::Delivered)__leave;
  const a_runtime_reward_source::Actor*actor=nullptr;for(const auto&a:rewardConfig_.actors)if(a.force==command.command_force)actor=&a;
  const auto now=GetTickCount64();if(!actor||actor->ruler!=command.ruler||actor->district!=command.charged_district||command.viewer_force!=c_.force||command.year!=p.year||command.month!=p.month||command.day!=p.day||
   !nonzero(command.nonce.data(),32)||!command.count||command.count>16||command.expires_at_tick<=now||command.expires_at_tick-now>60000)__leave;
  for(unsigned i=0;i<16;++i){if(i<command.count){if(command.officers[i]>=6000)__leave;for(unsigned j=0;j<i;++j)if(command.officers[j]==command.officers[i])__leave;}else if(command.officers[i])__leave;}
  rewardCommand_=command;reward_.sequence=sequence;reward_.binding=binding;reward_.readyResealed=false;reward_.state=RewardState::Queued;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Runtime::RewardSnapshot(RewardReport&out)noexcept {AcquireSRWLockShared(&lock_);out=reward_;out.stopped=InterlockedCompareExchange(&stopped_,0,0)!=0;if(owner_)a_reward_save_owner::Snapshot(*owner_,out.owner);ReleaseSRWLockShared(&lock_);}
bool Runtime::rewardFail(RewardError e)noexcept {if(reward_.error==RewardError::None)reward_.error=e;reward_.state=RewardState::Failed;reward_.uncertain=rewardFrame_;reward_.readyResealed=false;InterlockedExchange(&stopped_,1);r_.stopped=1;r_.error=Error::Reward;mailbox_.Stop();if(owner_)owner_->Stop();return false;}
bool Runtime::rewardBefore()noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=true;
 __try {__try {if(reward_.state!=RewardState::Queued)__leave;
  a_save_dispatch_host::Report h{};if(!a_save_parent_adapter::CurrentBoundary(c_.base)||!host_.Snapshot(h)||h.thread!=GetCurrentThreadId()||h.frame||h.lease||(h.state!=a_save_dispatch_host::State::Idle&&!(h.state==a_save_dispatch_host::State::Complete&&planning_.opened&&planning_.state==PlanningState::Opened&&planningReceipt(planning_.request)))||InterlockedCompareExchange(&stopped_,0,0)){ok=rewardFail(RewardError::Boundary);__leave;}
  auto&controller=InterlockedCompareExchange(&activePeriod_,0,0)?secondController_:controller_;planning_input_interlock::Report c{};controller.Snapshot(c);bool duplicate=false;
  if(!c.initialized||c.error!=planning_input_interlock::Error::None||!c.requested||c.observing||c.uncertain||!controller.Request(false,c.revision+1,duplicate)){ok=rewardFail(RewardError::Open);__leave;}
  a_reward_save_owner::Report before{};a_reward_save_owner::Snapshot(*owner_,before);rewardBeforeFinally_=before.finally;rewardBeforeAbnormal_=before.abnormal;
  reward_.thread=GetCurrentThreadId();rewardFrame_=true;reward_.state=RewardState::Executing;InterlockedExchange(&rewardCapture_,1);
  if(!a_reward_save_owner::Submit(*owner_,reward_.binding,reward_.sequence,rewardCommand_)){ok=rewardFail(RewardError::Submit);__leave;}
 }__except(EXCEPTION_EXECUTE_HANDLER){ok=rewardFail(RewardError::Boundary);}}
 __finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Runtime::rewardAfter()noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=true;
 __try {__try {if(!rewardFrame_)__leave;
  a_reward_save_owner::Report a{};a_reward_save_owner::Snapshot(*owner_,a);a_save_dispatch_host::Report h{};a_save_user_owner::Report own{};owner_->Snapshot(own);
  if(!a_save_parent_adapter::CurrentBoundary(c_.base)||GetCurrentThreadId()!=reward_.thread||!host_.Snapshot(h)||h.frame||h.lease||InterlockedCompareExchange(&stopped_,0,0)||
   a.error!=a_reward_save_owner::Error::None||a.submitted!=reward_.sequence||a.completed!=reward_.sequence||a.queued||a.active||a.uncertain||a.finally!=rewardBeforeFinally_+1||a.abnormal!=rewardBeforeAbnormal_||a.created!=a.destroyed||own.active_scopes||own.save_lane||
   a.reward.state!=a_reward_save_owner::rw::State::Consumed||a.reward.error!=a_reward_save_owner::rw::Error::None||!a.reward.native_returned||!a.reward.args_released||!a.reward.owned_slot_cleared){ok=rewardFail(RewardError::Native);__leave;}
  InterlockedExchange(&rewardCapture_,0);auto&controller=InterlockedCompareExchange(&activePeriod_,0,0)?secondController_:controller_;planning_input_interlock::Report c{};controller.Snapshot(c);bool duplicate=false;
  if(!controller.Request(true,c.revision+1,duplicate)){ok=rewardFail(RewardError::Reseal);__leave;}
  a_reward_save_owner::Snapshot(*owner_,a);if(!a.readyFence){ok=rewardFail(RewardError::Reseal);__leave;}
  reward_.state=RewardState::Complete;reward_.readyResealed=true;rewardFrame_=false;
 }__except(EXCEPTION_EXECUTE_HANDLER){ok=rewardFail(RewardError::Boundary);}}
 __finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Runtime::stableIdentity()const noexcept {
 if(GetCurrentProcessId()!=c_.pid||birth()!=c_.birth)return false;
 __try {const auto w=c_.source.world,root=c_.source.root;
 if(at<uintptr_t>(c_.base+0x1FCA1E0)!=root||at<uintptr_t>(root+0x85130)!=w||at<uintptr_t>(c_.base+0x2025318)!=c_.source.cache||at<std::uint8_t>(w+0x3A)!=c_.force)return false;
 const auto force=at<uintptr_t>(root+0xDCA0+c_.force*8);return force&&at<std::uint16_t>(force+0x10)==c_.ruler;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Runtime::returnSource()noexcept {
 if(returnedSource_)return true;
 __try {
  const auto m=c_.base+0x19E7310;
  if(at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30)||at<uintptr_t>(m+0x48))return false;
  const auto stack=at<uintptr_t>(m+0x20);if(!stack)return false;
  auto candidate=c_.source;static const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
  for(unsigned i=0;i<5;++i){auto state=at<uintptr_t>(stack+i*8);if(state<0x10000||state>UINTPTR_MAX-0x700||at<uintptr_t>(state)!=stateVtables_[i]||memcmp(reinterpret_cast<const void*>(state+0x70),names[i],strlen(names[i])+1)||at<uintptr_t>(state+0x50))return false;candidate.states[i]=state;}
  if(at<unsigned>(candidate.states[4]+0x470)!=2)return false;
  a_save_local_binding::Sampler trial;if(!trial.Initialize(candidate))return false;checkpoint_native_input_pending::Config pending{};
  if(!trial.Capture(pending))return false;checkpoint_native_input_pending::Adapter inspector;
  if(inspector.Bind(pending)!=checkpoint_native_input_pending::Error::None)return false;
  auto view=inspector.InspectCurrent(candidate.binding);if(view.error!=checkpoint_native_input_pending::Error::None||view.decision!=checkpoint_native_input_pending::Decision::QuiescentObserved)return false;
  a_save_early_guard::Guard reports;a_save_early_guard::Config guard{};guard.base=c_.base;guard.root=c_.source.root;guard.world=c_.source.world;guard.user=candidate.states[4];guard.binding=candidate.binding;
  if(!reports.Initialize(guard)||reports.Observe(candidate.binding).decision!=a_save_early_guard::Decision::QuietReportsObserved)return false;
  // Stage an immutable second sampler. Old source/guard allocations stay retained.
  sources_[1]=candidate;if(!nextSampler_.Initialize(candidate))return repeatFail(RepeatError::Rebind);
  InterlockedExchange(&sourceIndex_,1);
  if(!a_native_turn::Transition(*gate_,{a_native_turn::Action::Refresh,retired_.serial,&pending}))return repeatFail(RepeatError::Rebind);
  returnedSource_=true;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return repeatFail(RepeatError::Boundary);}
}
}

namespace a_save_local_runtime {
bool Runtime::planningReceipt(const PlanningRequest&q)noexcept {
 if(!owner_||q.generation!=1||!rewardBinding(q.binding,periods_[0].binding)||!identity(periods_[0]))return false;
 a_save_dispatch_mailbox::Report m{};mailbox_.Snapshot(m);if(m.stopped||m.count!=1||m.records[0].state!=a_save_dispatch_mailbox::State::Delivered)return false;
 const auto&r=m.records[0].message.request;
 if(r.generation!=1||r.period!=q.binding.period||r.room_epoch!=c_.nativeRoomEpoch||memcmp(r.room_id,c_.roomId,32)||r.year!=c_.year||r.month!=c_.month||r.day!=c_.day||r.force!=c_.force||r.ruler!=c_.ruler)return false;
 auto*a=new(std::nothrow)checkpoint_fresh_save::Artifact;if(!a)return false;
 const bool copied=owner_->CopyArtifact(1,*a);const auto&s=a->report;
 bool ok=copied&&!a->bytes.empty()&&!memcmp(&a->request,&r,sizeof r)&&!memcmp(a->sha256,q.artifactSha256,32)&&s.generation==1&&s.status==checkpoint_fresh_save::Status::Complete&&!s.error&&!s.active&&!s.abnormal&&s.file_bytes_verified&&s.worker_joined&&s.finalizer_returned&&s.original_returned&&s.return_matched;
 delete a;return ok;
}
bool Runtime::OpenPlanning(const PlanningRequest&q)noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {
  if(planning_.state!=PlanningState::Closed||!reward_.configured||!r_.sourcesArmed||r_.error!=Error::None||InterlockedCompareExchange(&stopped_,0,0)||InterlockedCompareExchange(&activePeriod_,0,0)||repeat_.requested||
   (reward_.state!=RewardState::Idle&&reward_.state!=RewardState::Complete)||!nonzero(q.artifactSha256,32)||!planningReceipt(q))__leave;
  a_reward_save_owner::Report a{};a_reward_save_owner::Snapshot(*owner_,a);if(!a.readyFence||a.queued||a.active||a.uncertain||a.error!=a_reward_save_owner::Error::None||a.submitted!=a.completed)__leave;
  planning_.request=q;planning_.state=PlanningState::Queued;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Runtime::PlanningSnapshot(PlanningReport&out)noexcept {AcquireSRWLockShared(&lock_);out=planning_;out.stopped=InterlockedCompareExchange(&stopped_,0,0)!=0;ReleaseSRWLockShared(&lock_);}
bool Runtime::planningBefore()noexcept {
 AcquireSRWLockExclusive(&lock_);bool ok=true;
 __try {__try {
  if(planning_.state!=PlanningState::Queued)__leave;
  a_save_dispatch_host::Report h{};a_save_user_owner::Report own{};owner_->Snapshot(own);planning_input_interlock::Report c{};controller_.Snapshot(c);
  if(InterlockedCompareExchange(&stopped_,0,0)||!a_save_parent_adapter::CurrentBoundary(c_.base)||!host_.Snapshot(h)||h.thread!=GetCurrentThreadId()||h.frame||h.lease||h.state!=a_save_dispatch_host::State::Complete||own.active_scopes||own.save_lane||own.stopped||own.error!=a_save_user_owner::Error::None||
   !c.initialized||c.thread!=h.thread||c.error!=planning_input_interlock::Error::None||!c.requested||c.observing||c.uncertain||!planningReceipt(planning_.request)){
   planning_.state=PlanningState::Failed;planning_.error=PlanningError::Boundary;planning_.stopped=true;ok=rewardFail(RewardError::Boundary);__leave;}
  planning_.hostThread=h.thread;planning_.opened=planning_.receiptMatched=true;planning_.state=PlanningState::Opened;
 }__except(EXCEPTION_EXECUTE_HANDLER){planning_.state=PlanningState::Failed;planning_.error=PlanningError::Boundary;planning_.stopped=true;ok=rewardFail(RewardError::Boundary);}}
 __finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
}
