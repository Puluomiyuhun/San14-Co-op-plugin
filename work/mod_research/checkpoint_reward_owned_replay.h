#pragma once
#include "checkpoint_planning_hold_adapter.h"
namespace checkpoint_reward_owned_replay {
namespace ph=checkpoint_planning_hold;
constexpr unsigned MaxOfficers=16;
using Ctor=ph::RewardArgs*(*)(ph::RewardArgs*);
using Append=std::uintptr_t(*)(std::uintptr_t,std::uint32_t,std::uint8_t);
using Dtor=void(*)(ph::RewardArgs*);
using Predicate=int(*)(std::uintptr_t);
struct Config {
    ph::Binding binding{};
    std::uintptr_t base=0,root=0,world=0,user=0;
    std::uint8_t authorized_force=0;std::uint16_t authorized_ruler=0; // Trusted room assignment, never command-supplied authority.
    Ctor ctor=nullptr;Append append=nullptr;Dtor dtor=nullptr;Predicate predicate=nullptr;
    // Trusted owner must keep image/world and native callable lifetimes pinned.
    // Revalidate actual attachment/planning ownership; no local mutex here is
    // claimed to fence unrelated game/UI threads or grant a remote command.
    bool(*validate_attachment)(void*,const ph::Binding&)=nullptr;void*context=nullptr;
};
struct Command {
    std::array<unsigned char,32> nonce{};
    std::uint16_t year=0,ruler=0,funding_city=0;
    std::uint8_t month=0,day=0,viewer_force=0,command_force=0,charged_district=0;
    unsigned count=0;std::uint32_t officers[MaxOfficers]{};
    std::uint64_t expires_at_tick=0;
};
enum class State:unsigned {New,Prepared,Executing,Consumed,Cancelled,Fault};
enum class Error:unsigned {None,Config,Profile,Binding,Command,Expired,WrongThread,Pool,Permissions,Eligibility,SnapshotChanged,Cancelled,Replay,NativeException,Cleanup};
struct Report {
    State state=State::New;Error error=Error::None;
    unsigned ctor_calls=0,append_calls=0,dtor_calls=0,capture_calls=0,execute_calls=0;
    unsigned slot=0xFFFFFFFF;int native_result=0;
    std::uint64_t before_nodes=0,after_nodes=0,before_handles=0,after_handles=0;
    std::array<unsigned char,32> command_sha256{},semantic_sha256{};
    bool native_returned=false,args_released=false,owned_slot_cleared=false,cancel_requested=false;
    bool world_thread_fence_proven=false,game_hook_installed=false,full_input_hold=false;
};
class Owner final {
public:
    Owner();~Owner();Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
    bool Initialize(const Config&)noexcept;
    bool Prepare(const Command&)noexcept;
    // Held throughout frozen PlanningHoldAuthorizeReward + ReplayReward. The
    // native pooled list is freed only after replay returns/exception unwinds.
    int Execute(ph::Context*,std::uint64_t replay_sequence);
    void Cancel()noexcept; // Cross-thread revocation, never frees native objects.
    bool Close()noexcept;  // Owner-thread cleanup; refuses while Execute active.
    Report Snapshot()const noexcept; // Owner thread or after host joins it.
    ph::RewardArgs* ArgsForOwnedFixture()noexcept;
    static bool Capture(void*,ph::Kind,const void*,int,ph::SemanticReceipt&);
private:struct Impl;Impl*p_=nullptr;
};
}
#ifdef CHECKPOINT_REWARD_OWNED_EXPORTS
#define REWARD_OWNED_API extern "C" __declspec(dllexport)
#else
#define REWARD_OWNED_API extern "C" __declspec(dllimport)
#endif
REWARD_OWNED_API checkpoint_reward_owned_replay::Owner* RewardOwnedCreate(const checkpoint_reward_owned_replay::Config*)noexcept;
// Only after all external callbacks/scopes have ceased AND Close succeeds.
REWARD_OWNED_API bool RewardOwnedDestroy(checkpoint_reward_owned_replay::Owner*)noexcept;
REWARD_OWNED_API bool RewardOwnedPrepare(checkpoint_reward_owned_replay::Owner*,const checkpoint_reward_owned_replay::Command*)noexcept;
REWARD_OWNED_API int RewardOwnedExecute(checkpoint_reward_owned_replay::Owner*,checkpoint_planning_hold::Context*,std::uint64_t);
REWARD_OWNED_API void RewardOwnedCancel(checkpoint_reward_owned_replay::Owner*)noexcept;
REWARD_OWNED_API bool RewardOwnedSnapshot(checkpoint_reward_owned_replay::Owner*,checkpoint_reward_owned_replay::Report*)noexcept;
REWARD_OWNED_API bool RewardOwnedCapture(void*,checkpoint_planning_hold::Kind,const void*,int,checkpoint_planning_hold::SemanticReceipt&);
REWARD_OWNED_API checkpoint_planning_hold::RewardArgs* RewardOwnedFixtureArgs(checkpoint_reward_owned_replay::Owner*)noexcept;
