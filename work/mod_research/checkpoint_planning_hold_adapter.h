#pragma once
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include "checkpoint_native_input_pending_adapter.h"
#include "checkpoint_native_input_consumer_bridge.h"
#include <array>
#include <cstdint>

// No installer, process lookup, native thread suspension, or network parser.
// One immutable round/attachment; only the supplied owner-thread entry family.
namespace checkpoint_planning_hold {
namespace ni=checkpoint_native_input;
namespace pd=checkpoint_native_input_pending;
struct Binding {ni::Binding native{};std::uint64_t period=0,epoch=0;std::array<unsigned char,32> room_input_digest{};};
struct RewardArgs {std::uintptr_t vtable=0,handle=0,funding=0;};
static_assert(sizeof(RewardArgs)==24);
using RewardOriginal=int(*)(RewardArgs*); // 1D6DA0: RCX -> EAX
using SortieOriginal=void*(*)(std::uint32_t*,int); // 1D1940: RCX, EDX -> RAX
enum class Kind:unsigned {Reward,Sortie};
enum class Phase:unsigned {Unbound,Open,HoldPending,Held,DrainPending,ReleasePending,FailStop};
enum class Operation:unsigned {Hold,Drain,Release};
enum class Status:unsigned {Ok,Config,Binding,WrongThread,StaleAction,State,Busy,Held,Stopped,Pending,MissingReplayTicket,ReplayBinding,Reentrant,NativeFailure,NativeException};
struct SemanticReceipt {std::array<unsigned char,32> digest{};std::uint64_t ownership_token=0,payload_epoch=0;};
struct Config {
    Binding binding{};pd::Config pending{};ni::Buffers buffers{};
    RewardOriginal reward=nullptr;SortieOriginal sortie=nullptr;
    checkpoint_native_input_consumer::MouseQuery mouse=nullptr;
    // Mandatory for remote replay. Trusted host must walk/deep-hash indirect
    // command content and validate owned lifetimes/world authority. The host
    // must retain EXCLUSIVE ownership through the entire native invocation;
    // digest rechecking alone is not a cross-thread mutation/lifetime fence.
    // The entry
    // shell alone is insufficient. Pure callback: never reenter this adapter.
    // No real-game provider is installed by this module; nullptr denies replay.
    bool(*capture_owned_command)(void*,Kind,const void*,int,SemanticReceipt&)=nullptr;
    void* replay_source_context=nullptr;
    // Owning host has audited exact function signatures and pinned lifetimes.
    // These pointers never become permission to install any hook.
};
struct Report {
    Status status=Status::Config;Phase phase=Phase::Unbound;
    std::uint64_t action_generation=0,revision=0,boundary_call=0,neutral_cycle=0;
    std::uint64_t local_entered=0,local_rejected=0,remote_entered=0,remote_rejected=0;
    std::uint64_t local_inflight=0,replay_inflight=0,last_replay_sequence=0,open_replay_tickets=0;
    std::uint64_t cancellations=0,exceptions=0,native_returns=0;
    bool covered_local_gate_closed=false,covered_local_drained=false,covered_replays_drained=false;
    bool paired_planning_boundary=false,covered_operation_completed=false;
    bool input_held=false,full_input_hold=false,physical_release_proven=false,room_ack_eligible=false;
    bool installed_in_game=false,game_threads_paused=false;
};
struct ReplayTicket;class Context;
// Explicit TLS routes are single invocation. Nested native commands do not
// inherit replay privilege. Never publish these entries as global detours.
int RewardEntry(RewardArgs*);
void* SortieEntry(std::uint32_t*,int);
std::uint32_t MouseEntry(const void*,std::uint32_t);

class Context final {
public:
    // Host must keep Context, source buffers, original/provider code and every
    // reachable command object alive throughout callbacks/TLS scopes/tickets.
    // Disconnect revokes admission; it is NOT a destruction/unload barrier.
    // Production integration should retain these contexts until process exit.
    Context();~Context();Context(const Context&)=delete;Context&operator=(const Context&)=delete;
    bool Initialize(const Config&) noexcept;
    // Thread-safe control request. Release closes/revokes prior drain authority
    // before its later owner-thread boundary reopens covered local admission.
    Status Request(const Binding&,Operation,std::uint64_t action_generation) noexcept;
    void Disconnect() noexcept;
    bool Snapshot(Report&) noexcept;
    bool BoundTo(const Binding&)const noexcept;
    bool InspectOwnedUserSkipCandidate(std::uintptr_t) noexcept;
    void Before(const CheckpointPushFrame&) noexcept;
    void BeforeMenuFetch(std::uint64_t call,const void* saved_rsi) noexcept;
    void After(const CheckpointPushFrame&) noexcept;
    void OriginalAbnormal() noexcept;
    int LocalReward(RewardArgs*);
    void* LocalSortie(std::uint32_t*,int);
    std::uint32_t Mouse(const void*,std::uint32_t);
    // Only the already authenticated local replay scheduler may issue tickets.
    // Ticket address/private state, exact args snapshot, binding and ordinal
    // are required; no packet boolean or inherited TLS mode grants a bypass.
    const ReplayTicket* AuthorizeReward(const Binding&,std::uint64_t sequence,RewardArgs*) noexcept;
    const ReplayTicket* AuthorizeSortie(const Binding&,std::uint64_t sequence,std::uint32_t*,int) noexcept;
    int ReplayReward(const ReplayTicket*,RewardArgs*);
    void* ReplaySortie(const ReplayTicket*,std::uint32_t*,int);
private:
    struct Impl;Impl* p_=nullptr;
    friend int RewardEntry(RewardArgs*);friend void* SortieEntry(std::uint32_t*,int);
    friend std::uint32_t MouseEntry(const void*,std::uint32_t);
    std::uint64_t Invoke(Kind,void*,int,const ReplayTicket*);
};
}

#ifdef CHECKPOINT_PLANNING_HOLD_EXPORTS
#define PLANNING_HOLD_API extern "C" __declspec(dllexport)
#else
#define PLANNING_HOLD_API extern "C" __declspec(dllimport)
#endif
PLANNING_HOLD_API checkpoint_planning_hold::Context* PlanningHoldCreate(const checkpoint_planning_hold::Config*) noexcept;
// Owned host teardown only, after ALL references/callbacks/TLS scopes/ticket
// consumers/control calls have stopped. No synchronization proof is made here.
PLANNING_HOLD_API void PlanningHoldDestroy(checkpoint_planning_hold::Context*) noexcept;
PLANNING_HOLD_API unsigned PlanningHoldRequest(checkpoint_planning_hold::Context*,const checkpoint_planning_hold::Binding*,unsigned,std::uint64_t) noexcept;
PLANNING_HOLD_API void PlanningHoldDisconnect(checkpoint_planning_hold::Context*) noexcept;
PLANNING_HOLD_API bool PlanningHoldSnapshot(checkpoint_planning_hold::Context*,checkpoint_planning_hold::Report*) noexcept;
PLANNING_HOLD_API void PlanningHoldBefore(checkpoint_planning_hold::Context*,const CheckpointPushFrame*) noexcept;
PLANNING_HOLD_API void PlanningHoldPrefetch(checkpoint_planning_hold::Context*,std::uint64_t,const void*) noexcept;
PLANNING_HOLD_API void PlanningHoldAfter(checkpoint_planning_hold::Context*,const CheckpointPushFrame*) noexcept;
PLANNING_HOLD_API void PlanningHoldAbnormal(checkpoint_planning_hold::Context*) noexcept;
PLANNING_HOLD_API bool PlanningHoldUserSkipCandidate(checkpoint_planning_hold::Context*,std::uintptr_t) noexcept;
PLANNING_HOLD_API int PlanningHoldLocalReward(checkpoint_planning_hold::Context*,checkpoint_planning_hold::RewardArgs*);
PLANNING_HOLD_API void* PlanningHoldLocalSortie(checkpoint_planning_hold::Context*,std::uint32_t*,int);
PLANNING_HOLD_API std::uint32_t PlanningHoldMouse(checkpoint_planning_hold::Context*,const void*,std::uint32_t);
PLANNING_HOLD_API const checkpoint_planning_hold::ReplayTicket* PlanningHoldAuthorizeReward(checkpoint_planning_hold::Context*,const checkpoint_planning_hold::Binding*,std::uint64_t,checkpoint_planning_hold::RewardArgs*) noexcept;
PLANNING_HOLD_API int PlanningHoldReplayReward(checkpoint_planning_hold::Context*,const checkpoint_planning_hold::ReplayTicket*,checkpoint_planning_hold::RewardArgs*);
PLANNING_HOLD_API const checkpoint_planning_hold::ReplayTicket* PlanningHoldAuthorizeSortie(checkpoint_planning_hold::Context*,const checkpoint_planning_hold::Binding*,std::uint64_t,std::uint32_t*,int) noexcept;
PLANNING_HOLD_API void* PlanningHoldReplaySortie(checkpoint_planning_hold::Context*,const checkpoint_planning_hold::ReplayTicket*,std::uint32_t*,int);
