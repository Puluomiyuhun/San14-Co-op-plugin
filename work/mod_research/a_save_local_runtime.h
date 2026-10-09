#pragma once
#include "a_save_local_binding.h"
#include "a_save_parent_adapter.h"
#include "a_save_dispatch_ipc.h"
// Current-process, controlled no-new-orders Save prototype. No discovery,
// publisher, launcher, injected arbitrary function pointers or reward replay.
namespace a_save_local_runtime {
namespace sb=checkpoint_live_storage_binding;namespace ph=checkpoint_planning_hold;
enum class Error:unsigned {None,Used,Config,Identity,Sampler,Owner,Gate,Parent,Order,Reward,Stopped};
struct Config {
 DWORD pid=0;std::uint64_t birth=0;uintptr_t base=0;
 unsigned char roomId[32]{};std::uint64_t nativeRoomEpoch=0;
 a_save_local_binding::Config source{};sb::Config storage{};ph::Binding planning{};
 std::uint16_t year=0,ruler=0;std::uint8_t month=0,day=0,force=0;
 wchar_t saveDirectory[512]{},intentDirectory[512]{};
};
struct Plans {a_save_upstream_gate::Plan gate{};a_save_parent_adapter::Plan parent{};
 checkpoint_load_hook_set::Report ownerSlots{},gateSlots{};};
struct Report {Error error=Error::None;unsigned prepared=0,ownerArmed=0,sourcesArmed=0,stopped=0;
 bool readyForControlledRequest=false,allWritersProven=false,productionPermit=false,rewardReplayEnabled=false;
 a_save_user_owner::Report owner{};a_save_upstream_gate::Report gate{};
 a_save_parent_adapter::Report parent{};a_save_dispatch_mailbox::Report mailbox{};a_reward_save_owner::Report reward{};};
class Runtime final {
public:
 Runtime()=default;~Runtime()=delete;Runtime(const Runtime&)=delete;Runtime&operator=(const Runtime&)=delete;
 // Immutable local data. storage callbacks/owned read bridges must be null;
 // this runtime supplies its own exact current-process attachment validator.
 bool Prepare(const Config&,Plans&)noexcept;
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
 void Stop()noexcept;void Snapshot(Report&)noexcept;
private:
 Config c_{};Plans plans_{};Report r_{};SRWLOCK lock_=SRWLOCK_INIT,producer_=SRWLOCK_INIT;
 volatile LONG once_=0,stopped_=0;bool copied_=false;
 a_save_local_binding::Sampler sampler_;a_save_user_owner::Owner*owner_=nullptr;a_save_upstream_gate::Owner*gate_=nullptr;
 planning_input_interlock::Controller controller_;a_save_dispatch_mailbox::Mailbox mailbox_;
 a_save_dispatch_mailbox::Adapter execution_{&mailbox_,5000};a_save_dispatch_host::Host host_;a_save_parent_adapter::Adapter parent_;
 bool identity()const noexcept;void fail(Error)noexcept;bool rawInline()const noexcept;
 static bool storageOwner(void*,const sb::Attachment&,sb::Point)noexcept;
 static bool planningSample(void*,uintptr_t,unsigned,a_reward_save_owner::Source&);
 static bool permit(void*,const checkpoint_fresh_save::Request&,const unsigned char[32])noexcept;
 static void executionStop(void*)noexcept;
};
}
