#pragma once
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include "checkpoint_native_input_core.h"
#include "checkpoint_load_dispatch_bridge.h"

namespace checkpoint_native_input_pending {
using Binding = checkpoint_native_input::Binding;
using Span = checkpoint_native_input::ConstSpan;

struct Config {
    Binding binding{};
    std::uintptr_t profile_base = 0;
    Span user, toolbar, game, panel, manager, stack, queue, load_cache;
    std::uintptr_t states[5]{}; // Root/Motor/Game/Strategy/User attachment identities
};
enum class Decision {
    Invalid, QuiescentObserved, PlayerMenuPending, AdvancePending,
    StateTransition, SelectionPending, UnownedStateQueue, UnownedLoadMenu,
    AuthorizedLoadQueued, AuthorizedLoadActive,
};
enum class Error {
    None, NotBound, AlreadyBound, Identity, WrongThread, Span, Alias, Pointer,
    Layout, Reentrant, CallPair, StaleCall, WrongStage, NoCleanPrefetch,
    NoAuthorization, TicketMismatch, AuthorizationUsed,
};
enum class Stage { None, BeforeUserUpdate, BeforeMenuFetch, AfterUserUpdate, Standalone };
struct Report {
    Decision decision = Decision::Invalid;
    Error error = Error::NotBound;
    Stage stage = Stage::None;
    std::uint64_t call_id = 0;
    std::int32_t menu_command = -1;
    std::uint32_t user_phase = 0, game_transition = 0, load_queued = 0, advance = 0, panel_advance = 0;
    std::uint64_t stack_count = 0, queue_count = 0;
    bool read_only = true;
    bool pending_admission_candidate = false; // only a clean observed prefetch
    bool native_hook_installed = false;
    bool all_pending_sources_covered = false;
    bool full_input_hold = false;
};
struct Ticket {
    Binding binding{};
    std::uint64_t serial = 0, call_id = 0;
};

// This inspector never writes native spans, clears requests, installs hooks or
// stops the original update. It keeps private pairing/authorization state only.
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4324) // Exact bridge frame intentionally has 16-byte alignment.
#endif
class Adapter final {
public:
    Adapter() = default;
    Adapter(const Adapter&) = delete;
    Adapter& operator=(const Adapter&) = delete;
    Error Bind(const Config&) noexcept;
    Report ObserveBefore(const Binding&, const CheckpointPushFrame&) noexcept;
    Report ObserveBeforeFetch(const Binding&, std::uint64_t call_id, const void* saved_rsi) noexcept;
    Report ObserveAfter(const Binding&, const CheckpointPushFrame&) noexcept;
    Error CloseAfter(const Binding&, std::uint64_t call_id) noexcept;
    Report InspectCurrent(const Binding&) noexcept;

    // Only callable inside this same paired AFTER scope, after clean BEFORE,
    // prefetch, and AFTER observations. The caller performs its already
    // authorized native queue operation; this adapter only checks its result.
    Error BeginAuthorizedLoadPush(const Binding&, std::uint64_t call_id, Ticket&) noexcept;
    Error CommitAuthorizedLoadPush(const Ticket&, Span exact_created_menu) noexcept;

private:
    Error ValidateBinding(const Binding&) const noexcept;
    Report Inspect(Stage, std::uint64_t call_id) noexcept;
    bool Matches(const CheckpointPushFrame&) const noexcept;
    Error ValidateMenu(Span) const noexcept;
    Config config_{};
    DWORD owner_thread_ = 0;
    bool bound_ = false, active_ = false, after_ = false;
    bool before_clean_ = false, prefetch_clean_ = false, after_clean_ = false, prefetch_seen_ = false;
    CheckpointPushFrame frame_{};
    std::uint64_t last_call_ = 0, serial_ = 0;
    Ticket ticket_{};
    bool ticket_open_ = false, authorized_ = false, authorization_started_ = false;
    bool authorized_active_observed_ = false, authorization_retired_ = false;
    Span authorized_menu_{};
};
#ifdef _MSC_VER
#pragma warning(pop)
#endif
const char* DecisionName(Decision) noexcept;
const char* ErrorName(Error) noexcept;
} // namespace checkpoint_native_input_pending
