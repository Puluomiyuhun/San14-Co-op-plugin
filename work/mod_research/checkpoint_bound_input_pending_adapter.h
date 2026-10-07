#pragma once
#include "checkpoint_native_input_pending_adapter.h"
namespace checkpoint_bound_input_pending {
namespace prior=checkpoint_native_input_pending;
using Binding=prior::Binding;using Span=prior::Span;
using Decision=prior::Decision;using Error=prior::Error;using Stage=prior::Stage;
using Report=prior::Report;using Ticket=prior::Ticket;
// Called only after a single authorized native queue operation returned and
// created the formerly-empty vector. Resolver must independently prove readable
// extent/lifetime; it never allocates memory or submits an operation.
using QueueSpanResolver=Span(*)(void*,std::uintptr_t,std::size_t) noexcept;
struct Config:prior::Config {
    std::uint32_t expected_initial_cache_mode=1;
    QueueSpanResolver resolve_created_queue=nullptr;
    void* queue_resolver_context=nullptr;
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
} // namespace checkpoint_bound_input_pending
