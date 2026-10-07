#pragma once
#include "checkpoint_fresh_save.h"
#include "checkpoint_serialized_storage_gate.h"
#include "checkpoint_load_hook_set.h"
#include "a_save_user_owner_bridge.h"
#include "checkpoint_native_input_pending_adapter.h"

// In-process A-side composition. There is no discovery, remote installer,
// arbitrary native function input, room readiness or input-lock authority.
namespace a_save_user_owner {
enum class Error:LONG {None,Used,Config,RawSlot,Storage,Driver,Bridge,Hooks,Arm,Stopped,Room,Input,Overlap};
struct Config {
 std::uintptr_t base=0;
 wchar_t save_directory[512]{},intent_directory[512]{};
 std::uint64_t room_epoch=0;
 unsigned char room_id[32]{};
 // Retained attachment provider must be read-only, non-reentrant and must not
 // call Owner/Driver methods: Driver can validate it while holding its mutex.
 // The storage generation identifies this retained attachment; each Request
 // has a separate monotonically increasing save generation.
 checkpoint_live_storage_binding::Config storage{};
 // Fresh spans, not an approval callback. Inspected on the actual User thread.
 // Must be read-only, non-reentrant, and must not call Owner methods. Fixed
 // manager/cache addresses and original dispatcher return are checked here.
 checkpoint_native_input_pending::Binding input_binding{};
 bool(*sample_input)(void*,checkpoint_native_input_pending::Config&) noexcept=nullptr;
 void* input_context=nullptr;
#ifdef A_SAVE_USER_OWNER_FIXTURE
 // Test-only native business doubles and dispatcher return label. The two
 // original entry addresses and slot publication still use base + native RVA.
 std::uintptr_t binder=0,queue=0,caller=0;
#endif
};
struct Report {
 Error error=Error::None;
 unsigned initialized=0,armed=0,stopped=0,retained=1;
 checkpoint_fresh_save::Report save{};
 checkpoint_serialized_storage_gate::Report storage{};
 checkpoint_load_hook_set::Report hooks{};
 CheckpointLoadWorkerBridgeStats bridges[2]{};
 std::uint64_t hold_revision=0,held_scopes=0,active_scopes=0;
 bool user_hold_requested=false,user_subset_held=false,save_lane=false;
 bool room_ready=false,full_world=false,all_input_held=false;
};
// Create on the heap and retain until process exit. No teardown is offered:
// Stop prevents admission but forwards originals and observes committed work.
// This deliberate lifetime also covers a prefetched/cached bridge invocation.
class Owner final {
public:
 Owner(); ~Owner()=delete;
 Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 bool Initialize(const Config&) noexcept;
 bool Arm() noexcept;
 bool Submit(const checkpoint_fresh_save::Request&) noexcept;
 // Held User is never run for the sake of saving. Save and hold admission
 // exclude each other. This is only the User subset, not a Ready/input grant.
 bool SetUserHold(bool,std::uint64_t revision) noexcept;
 void Stop() noexcept;
 void Snapshot(Report&) noexcept;
 bool CopyArtifact(std::uint64_t,checkpoint_fresh_save::Artifact&) noexcept;
private:
 struct Impl;Impl*p_;
};
}
