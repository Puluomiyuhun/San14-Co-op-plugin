#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <thread>

// This module only touches explicitly supplied, locally owned buffers. It does
// not find devices/windows/processes, install hooks, poll input, or stop updates.
// A successful publication is NOT evidence that the game's input is held.
namespace checkpoint_native_input {

inline constexpr std::size_t kNormalSize = 0x78;
inline constexpr std::size_t kMouseSize = 0x68;
inline constexpr std::size_t kRawKeyboardSize = 0x258;
inline constexpr std::size_t kRawEventCapacity = 0x7e;

struct MutableSpan {
    std::uint8_t* data = nullptr;
    std::size_t size = 0;
};
struct ConstSpan {
    const std::uint8_t* data = nullptr;
    std::size_t size = 0;
};
struct Buffers {
    MutableSpan normal;
    MutableSpan mouse;
    ConstSpan raw_keyboard_source;
};
using Identity = std::array<std::uint8_t, 16>;
struct Binding {
    Identity attempt{};
    Identity attachment{};
    std::uint64_t owner_generation = 0;
};

enum class Status {
    Ok,
    NotBound,
    AlreadyBound,
    InvalidIdentity,
    WrongThread,
    StaleBinding,
    InvalidSpan,
    OverlappingSpans,
    InvalidLayout,
    RawPointerMismatch,
    InvalidCycle,
    StalePublication,
    InvalidQuery,
    InvalidQueue,
    QueueOverlapsBoundMemory,
};
const char* StatusName(Status status) noexcept;

// The first seven bits use the seven names of NeutralInputGate's channel list.
enum Channel : std::uint32_t {
    NormalCache = 1u << 0,
    RawKeyboard = 1u << 1,
    SpecialRepeat = 1u << 2,
    Mouse = 1u << 3,
    ControllerDI = 1u << 4,
    ControllerAlternate = 1u << 5,
    PostedMessages = 1u << 6,
};
inline constexpr std::uint32_t kAllChannels = (1u << 7) - 1;

// These are always missing in this offline subset, even after successful writes.
enum Missing : std::uint64_t {
    NativeConsumerHook = 1ull << 0,
    RawKeyboardBypasses = 1ull << 1,
    RawKeyboardAccessorHook = 1ull << 2,
    RawMouseAndCursorBypasses = 1ull << 3,
    RealProviderDrain = 1ull << 4,
    ControllerDIProvider = 1ull << 5,
    AlternateControllerProvider = 1ull << 6,
    WndProcAndRealQueueIntegration = 1ull << 7,
    UnclassifiedBusinessMessages = 1ull << 8,
    PhysicalReleaseEvidence = 1ull << 9,
    NativeOwnerThreadFence = 1ull << 10,
    PendingBusinessBoundary = 1ull << 11,
    LaterNeutralCycleAndGrant = 1ull << 12,
    EnginePumpAndWorkerProgress = 1ull << 13,
};
inline constexpr std::uint64_t kAlwaysMissing = (1ull << 14) - 1;

struct Publication {
    Status status = Status::NotBound;
    std::uint64_t cycle = 0;
    // These fields describe bytes in the supplied buffers, not hook coverage.
    std::uint32_t neutralized_cache_mask = 0;
    std::uint32_t neutral_shadow_mask = 0;
    std::uint32_t complete_native_channel_mask = 0;
    std::uint32_t missing_native_channel_mask = kAllChannels;
    std::uint64_t missing_mask = kAlwaysMissing;
    bool keyboard_source_contained_input = false;
    bool full_input_hold = false;
    bool physical_release_proven = false;
    bool release_eligible = false;
};

// A plain value snapshot, deliberately not a fake polymorphic device object.
// Do not replace normal+0 or any provider/vtable pointer with this address.
struct RawKeyboardShadow {
    std::uint32_t modifiers = 0;
    std::uint32_t event_count = 0;
    std::array<std::uint16_t, kRawEventCapacity> events{};
    std::array<std::uint8_t, 2> repeat_policy{};
    std::uint16_t last_key = 0;
    std::array<std::uint8_t, 256> keys{};
};
struct QueryResult {
    Status status = Status::NotBound;
    bool pressed = false;
};

struct Message {
    std::uintptr_t window = 0;
    std::uint32_t id = 0;
    std::uintptr_t wparam = 0;
    std::intptr_t lparam = 0;
};
enum class MessageClass {
    AuditedGameplayInput,
    Lifecycle,
    UncoveredInput,
    Unclassified,
    OtherWindow,
};
struct MessageDecision {
    MessageClass classification = MessageClass::Unclassified;
    bool discard = false;
};
// Exact known handlers only. Unknown standard/custom inputs pass and remain
// missing; this is not a general Windows message or input suppression policy.
MessageDecision ClassifyMessage(const Message& message,
                               std::uintptr_t bound_window,
                               bool suppress_audited_inputs) noexcept;

struct QueueResult {
    Status status = Status::NotBound;
    std::size_t kept = 0;
    std::size_t discarded = 0;
    std::size_t uncovered_input = 0;
    std::size_t unclassified = 0;
    std::uint64_t missing_mask = kAlwaysMissing;
    bool actual_os_queue_drained = false;
    bool full_input_hold = false;
};

class Adapter final {
public:
    Adapter() = default;
    Adapter(const Adapter&) = delete;
    Adapter& operator=(const Adapter&) = delete;
    Adapter(Adapter&&) = delete;
    Adapter& operator=(Adapter&&) = delete;

    // Bind once on the same thread that will publish/consume. The host owns all
    // buffer lifetimes and guarantees exclusive access; this is no cross-thread
    // fence. No rebind/handoff exists: a new adapter requires a verified fence.
    Status Bind(const Binding& binding, Buffers buffers) noexcept;

    // Strictly increasing cycle. Validate ALL spans/layout/identity/thread first,
    // stage every modified byte, then commit with no further fallible work.
    // Invoke only after native conversion and before targeted input consumers.
    Publication PublishNeutral(const Binding& binding, std::uint64_t cycle) noexcept;

    // Explicit facade for consumers a future hook has individually identified.
    // These never read physical devices and never claim to cover unhooked paths.
    QueryResult QueryRawModifier(const Binding& binding, std::uint64_t cycle,
                                 std::uint32_t modifier_mask) const noexcept;
    QueryResult QueryRawKey(const Binding& binding, std::uint64_t cycle,
                            std::uint32_t key_index) const noexcept;
    Status CopyRawShadow(const Binding& binding, std::uint64_t cycle,
                         RawKeyboardShadow& destination) const noexcept;

    // Compact the caller's owned batch only, preserving retained order and all
    // lifecycle/engine/custom messages. No PeekMessage/PostMessage/DispatchMessage
    // calls or real WndProc replacement are made. count is not modified on failure.
    QueueResult FilterOwnedQueue(const Binding& binding, std::uint64_t cycle,
                                 std::uintptr_t bound_window, Message* messages,
                                 std::size_t& count, std::size_t capacity) const noexcept;

private:
    Status ValidateBinding(const Binding& binding) const noexcept;
    Status ValidateBuffers(Buffers buffers) const noexcept;
    Status ValidatePublication(const Binding& binding, std::uint64_t cycle) const noexcept;

    bool bound_ = false;
    Binding binding_{};
    Buffers buffers_{};
    std::thread::id owner_thread_{};
    std::uint64_t published_cycle_ = 0;
    RawKeyboardShadow shadow_{};
};

} // namespace checkpoint_native_input
