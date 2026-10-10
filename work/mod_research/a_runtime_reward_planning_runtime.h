#pragma once
#include "a_runtime_reward_source.h"
#include "a_save_local_binding.h"
#include "a_native_turn_control.h"
#include "a_save_early_guard.h"
#include "a_save_parent_adapter.h"
#include "a_save_repeat_parent.h"
#include "a_save_dispatch_ipc.h"
// Current-process controlled Save plus typed reward planning window.
// No discovery, publisher, launcher, or externally supplied native callbacks.
namespace a_save_local_runtime {
namespace sb=checkpoint_live_storage_binding;namespace ph=checkpoint_planning_hold;
enum class Error:unsigned {None,Used,Config,Identity,Sampler,Owner,Gate,Parent,Order,Reward,Stopped};
struct Config {
 DWORD pid=0;std::uint64_t birth=0;uintptr_t base=0;
 unsigned char roomId[32]{};std::uint64_t nativeRoomEpoch=0;
 a_save_local_binding::Config source{};sb::Config storage{};ph::Binding planning{};
 std::uint16_t year=0,ruler=0;std::uint8_t month=0,day=0,force=0;
 wchar_t saveDirectory[512]{},intentDirectory[512]{};
#ifdef A_SAVE_REPEAT_FIXTURE
 uintptr_t fixtureBinder=0,fixtureQueue=0,fixtureUserCaller=0,fixtureGameCaller=0,fixtureUiCaller=0;
#endif
};
struct Plans {a_save_upstream_gate::Plan gate{};a_save_parent_adapter::Plan parent{};
 checkpoint_load_hook_set::Report ownerSlots{},gateSlots{};};
struct Report {Error error=Error::None;unsigned prepared=0,ownerArmed=0,sourcesArmed=0,stopped=0;
 bool readyForControlledRequest=false,allWritersProven=false,productionPermit=false,rewardReplayEnabled=false;
 a_save_user_owner::Report owner{};a_save_upstream_gate::Report gate{};
 a_save_parent_adapter::Report parent{};a_save_dispatch_mailbox::Report mailbox{};a_reward_save_owner::Report reward{};};
// A copied local experiment request; no B-loaded assertion or native call address.
struct Next {
 std::uint64_t previousGeneration=0;unsigned char previousSha256[32]{};
 std::uint64_t generation=0,period=0,epoch=0;unsigned char inputDigest[32]{};
 std::uint16_t year=0;std::uint8_t month=0,day=0;
};
enum class RepeatState:unsigned {Idle,Queued,Observing,RetiredWaitingDate,ReadySecond,Failed};
enum class RepeatError:unsigned {None,Shape,Delivery,Boundary,Observation,Retire,Date,Rebind,Controller,Host,Stopped};
struct RepeatReport {
 RepeatState state=RepeatState::Idle;RepeatError error=RepeatError::None;
 DWORD hostThread=0;unsigned requested=0,stopped=0;std::uint64_t activeGeneration=1,retiredSerial=0,retiredCount=0;
 Next request{};bool lease=false,frame=false,drainPending=false;bool previousArtifactMatched=false,nativeDateMatched=false,bLoadedProven=false,simulationEnabled=false;
};
enum class RewardState:unsigned {Disabled,Idle,Queued,Executing,Complete,Failed};
enum class RewardError:unsigned {None,Config,Used,Shape,Busy,Binding,Boundary,Open,Submit,Native,Reseal,Stopped};
struct RewardConfig {ph::Binding binding{};a_runtime_reward_source::Actor actors[2]{};};
struct RewardReport {RewardState state=RewardState::Disabled;RewardError error=RewardError::None;
 ph::Binding binding{};std::uint64_t sequence=0;DWORD thread=0;bool configured=false,readyResealed=false,uncertain=false,stopped=false;
 a_reward_save_owner::Report owner{};};
enum class PlanningState:unsigned {Closed,Queued,Opened,Retired,Failed};
enum class PlanningError:unsigned {None,Binding,Receipt,Boundary,Stopped};
struct PlanningRequest {ph::Binding binding{};std::uint64_t generation=0;unsigned char artifactSha256[32]{};};
struct PlanningReport {PlanningRequest request{};PlanningState state=PlanningState::Closed;PlanningError error=PlanningError::None;DWORD hostThread=0;bool opened=false,receiptMatched=false,stopped=false;};
class Runtime final {
public:
 Runtime()=default;~Runtime()=delete;Runtime(const Runtime&)=delete;Runtime&operator=(const Runtime&)=delete;
 // Immutable local data. storage callbacks/owned read bridges must be null;
 // this runtime supplies its own exact current-process attachment validator.
 bool Prepare(const Config&,Plans&)noexcept;
 // Re-admit explicit commands after bootstrap delivery, retaining the original
 // native binding and save history. Actual acceptance occurs at parent BEFORE.
 bool OpenPlanning(const PlanningRequest&)noexcept;
 void PlanningSnapshot(PlanningReport&)noexcept;
 bool ConfigureReward(const RewardConfig&)noexcept;
 bool SubmitReward(const ph::Binding&,std::uint64_t,const a_reward_save_owner::rw::Command&)noexcept;
 void RewardSnapshot(RewardReport&)noexcept;
#ifdef A_SAVE_REPEAT_FIXTURE
 a_save_user_owner::Owner*FixtureOwner()noexcept{return owner_;}
 a_save_upstream_gate::Owner*FixtureGate()noexcept{return gate_;}
 a_save_dispatch_mailbox::Mailbox&FixtureMailbox()noexcept{return mailbox_;}
 SRWLOCK&FixtureProducer()noexcept{return producer_;}
 a_save_dispatch_host::Host&FixtureHost()noexcept{return host_;}
 a_save_parent_adapter::Adapter&FixtureParent()noexcept{return parent_;}
#endif
 // Under the trusted external publication window, BEFORE changing Gate inline
 // bytes: publish Owner Save/User slots, then bind the read-only planning lane.
 bool ArmOwner()noexcept;
 // External publisher now writes Gate 2 inline sites + Parent 1 call. Finish
 // publishes Gate slots and arms Parent LAST. It does not initialize Controller.
 bool ArmPublishedSources()noexcept;
 // Caller supplies only pipe/client/secret/timeout. No server is opened here.
 // Available only after a real authenticated parent initialized Host. Permit
 // is strictly this controlled test identity, NOT a full-writer/input proof.
 bool ConfigureTransport(a_save_dispatch_ipc::Config&)noexcept;
 // Consumes one copied request. Acceptance/retirement occur only at parent TLS.
 bool RequestNext(const Next&)noexcept;void RepeatSnapshot(RepeatReport&)noexcept;
 void Stop()noexcept;void Snapshot(Report&)noexcept;
private:
 PlanningReport planning_{};
 bool planningReceipt(const PlanningRequest&)noexcept;
 bool planningBefore()noexcept;
 a_runtime_reward_source::SourceProvider rewardSources_[2];RewardConfig rewardConfig_{};RewardReport reward_{};
 a_reward_save_owner::rw::Command rewardCommand_{};bool rewardFrame_=false;std::uint64_t rewardBeforeFinally_=0,rewardBeforeAbnormal_=0;volatile LONG rewardCapture_=0;
 bool rewardSource(unsigned)noexcept;bool rewardBefore()noexcept;bool rewardAfter()noexcept;
 bool rewardFail(RewardError)noexcept;
 Config c_{};Plans plans_{};Report r_{};SRWLOCK lock_=SRWLOCK_INIT,producer_=SRWLOCK_INIT;
 volatile LONG once_=0,stopped_=0;bool copied_=false;
 a_save_local_binding::Sampler sampler_,nextSampler_;
 a_save_local_binding::Config sources_[2]{};uintptr_t stateVtables_[5]{};volatile LONG sourceIndex_=0;
 bool returnedSource_=false;std::uint64_t runningFrames_=0;
 static bool inputSample(void*,checkpoint_native_input_pending::Config&)noexcept;
 bool stableIdentity()const noexcept;bool returnSource()noexcept;a_save_user_owner::Owner*owner_=nullptr;a_save_upstream_gate::Owner*gate_=nullptr;
 planning_input_interlock::Controller controller_;a_save_dispatch_mailbox::Mailbox mailbox_;
 a_save_dispatch_mailbox::Adapter execution_{&mailbox_,5000};a_save_dispatch_host::Host host_;a_save_parent_adapter::Adapter parent_;
 struct Period {Runtime*self=nullptr;ph::Binding binding{};std::uint16_t year=0;std::uint8_t month=0,day=0;};
 Period periods_[2]{};volatile LONG activePeriod_=0;RepeatReport repeat_{};bool repeatLease_=false;
 planning_input_interlock::Controller secondController_;planning_period_owner::Receipt retired_{};std::uint64_t repeatRevision_=0;
 static bool repeatBefore(void*)noexcept;static bool repeatAfter(void*)noexcept;static bool repeatCancel(void*)noexcept;
 bool onRepeatBefore()noexcept;bool onRepeatAfter()noexcept;bool onRepeatCancel()noexcept;bool repeatFail(RepeatError)noexcept;
 bool identity(const Period&)const noexcept;bool identity()const noexcept;void fail(Error)noexcept;bool rawInline()const noexcept;
 static bool storageOwner(void*,const sb::Attachment&,sb::Point)noexcept;
 static bool planningSample(void*,uintptr_t,unsigned,a_reward_save_owner::Source&);
 static bool permit(void*,const checkpoint_fresh_save::Request&,const unsigned char[32])noexcept;
 static void executionStop(void*)noexcept;
};
}
