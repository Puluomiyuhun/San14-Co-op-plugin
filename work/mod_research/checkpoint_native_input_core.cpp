#include "checkpoint_native_input_core.h"

#include <algorithm>
#include <cstring>
#include <limits>

namespace checkpoint_native_input {
namespace {
static_assert(sizeof(std::uintptr_t) == 8, "Audited layout is x64 only");

struct Range { std::uintptr_t begin; std::uintptr_t end; };
bool MakeRange(const void* pointer, std::size_t size, std::size_t required,
               Range& result) noexcept {
    if (!pointer || size < required) return false;
    const auto begin = reinterpret_cast<std::uintptr_t>(pointer);
    if (size > std::numeric_limits<std::uintptr_t>::max() - begin) return false;
    result = {begin, begin + size};
    return true;
}
bool Overlap(const Range& a, const Range& b) noexcept {
    return a.begin < b.end && b.begin < a.end;
}
template<class T> T Read(const std::uint8_t* bytes, std::size_t offset) noexcept {
    T value{};
    std::memcpy(&value, bytes + offset, sizeof value);
    return value;
}
template<class T> void Write(std::uint8_t* bytes, std::size_t offset, T value) noexcept {
    std::memcpy(bytes + offset, &value, sizeof value);
}
bool HasIdentity(const Identity& identity) noexcept {
    return std::any_of(identity.begin(), identity.end(), [](auto byte) { return byte != 0; });
}
bool SameBinding(const Binding& a, const Binding& b) noexcept {
    return a.attempt == b.attempt && a.attachment == b.attachment &&
           a.owner_generation == b.owner_generation;
}
void Zero(std::uint8_t* buffer, std::size_t begin, std::size_t end) noexcept {
    std::memset(buffer + begin, 0, end - begin);
}
bool IsLifecycle(std::uint32_t message) noexcept {
    switch (message) {
    case 0x0001: // CREATE
    case 0x0002: // DESTROY
    case 0x0003: // MOVE
    case 0x0005: // SIZE
    case 0x0006: // ACTIVATE
    case 0x0007: // SETFOCUS
    case 0x0008: // KILLFOCUS
    case 0x000f: // PAINT
    case 0x0010: // CLOSE
    case 0x0011: // QUERYENDSESSION
    case 0x0012: // QUIT (usually thread message)
    case 0x0014: // ERASEBKGND
    case 0x0016: // ENDSESSION
    case 0x0018: // SHOWWINDOW
    case 0x001c: // ACTIVATEAPP
    case 0x0020: // SETCURSOR: retain engine cursor/lifecycle handling
    case 0x0024: // GETMINMAXINFO
    case 0x0046: // WINDOWPOSCHANGING
    case 0x0047: // WINDOWPOSCHANGED
    case 0x007e: // DISPLAYCHANGE
    case 0x0081: // NCCREATE
    case 0x0082: // NCDESTROY
    case 0x0113: // TIMER: may progress engine work
    case 0x0215: // CAPTURECHANGED
    case 0x0218: // POWERBROADCAST
    case 0x02e0: // DPICHANGED
        return true;
    default:
        return false;
    }
}
bool IsAuditedGameplay(const Message& message) noexcept {
    switch (message.id) {
    case 0x0100: // KEYDOWN: only explicit Enter/Backspace/Esc repost paths
    case 0x0101: // KEYUP
        return message.wparam == 0x0d || message.wparam == 0x08 || message.wparam == 0x1b;
    case 0x0200: // MOUSEMOVE, 3A39D0
    case 0x0201: // LBUTTONDOWN, 510D64 repost
    case 0x0202: // LBUTTONUP, 510D87 repost
    case 0x0204: // RBUTTONDOWN, 510E1A repost
    case 0x0205: // RBUTTONUP, 510E42 repost
    case 0x02a3: // MOUSELEAVE, 3A39D0
        return true;
    default:
        return false;
    }
}
bool IsUncoveredStandardInput(std::uint32_t message) noexcept {
    // Classification only. None of these broad classes are discarded.
    return (message >= 0x0100 && message <= 0x0109) ||
           (message >= 0x0200 && message <= 0x020e) ||
           (message >= 0x0240 && message <= 0x0253) ||
           message == 0x00ff || message == 0x0111 || message == 0x0112 ||
           message == 0x0312 || message == 0x0319;
}
} // namespace

const char* StatusName(Status status) noexcept {
    switch (status) {
#define INPUT_STATUS(name) case Status::name: return #name;
        INPUT_STATUS(Ok)
        INPUT_STATUS(NotBound)
        INPUT_STATUS(AlreadyBound)
        INPUT_STATUS(InvalidIdentity)
        INPUT_STATUS(WrongThread)
        INPUT_STATUS(StaleBinding)
        INPUT_STATUS(InvalidSpan)
        INPUT_STATUS(OverlappingSpans)
        INPUT_STATUS(InvalidLayout)
        INPUT_STATUS(RawPointerMismatch)
        INPUT_STATUS(InvalidCycle)
        INPUT_STATUS(StalePublication)
        INPUT_STATUS(InvalidQuery)
        INPUT_STATUS(InvalidQueue)
        INPUT_STATUS(QueueOverlapsBoundMemory)
#undef INPUT_STATUS
    }
    return "UnknownStatus";
}

Status Adapter::ValidateBuffers(Buffers buffers) const noexcept {
    Range normal{}, mouse{}, raw{}, adapter{};
    if (!MakeRange(buffers.normal.data, buffers.normal.size, kNormalSize, normal) ||
        !MakeRange(buffers.mouse.data, buffers.mouse.size, kMouseSize, mouse) ||
        !MakeRange(buffers.raw_keyboard_source.data, buffers.raw_keyboard_source.size,
                   kRawKeyboardSize, raw) ||
        !MakeRange(this, sizeof(*this), sizeof(*this), adapter)) return Status::InvalidSpan;
    if (Overlap(normal, mouse) || Overlap(normal, raw) || Overlap(mouse, raw) ||
        Overlap(normal, adapter) || Overlap(mouse, adapter) || Overlap(raw, adapter))
        return Status::OverlappingSpans;

    // No device pointer is dereferenced. Require the already bound normal cache
    // to refer to exactly the raw source supplied by its local owner.
    if (Read<std::uintptr_t>(buffers.normal.data, 0) !=
        reinterpret_cast<std::uintptr_t>(buffers.raw_keyboard_source.data))
        return Status::RawPointerMismatch;
    if (Read<std::uint32_t>(buffers.normal.data, 8) > 1 ||
        Read<std::uint32_t>(buffers.normal.data, 0xc) > 1 ||
        Read<std::uint32_t>(buffers.mouse.data, 0) > 1 ||
        Read<std::uint32_t>(buffers.mouse.data, 4) > 1 ||
        Read<std::uint32_t>(buffers.raw_keyboard_source.data, 0x54) > kRawEventCapacity)
        return Status::InvalidLayout;
    return Status::Ok;
}

Status Adapter::Bind(const Binding& binding, Buffers buffers) noexcept {
    if (bound_) return Status::AlreadyBound;
    if (!HasIdentity(binding.attempt) || !HasIdentity(binding.attachment) ||
        !binding.owner_generation) return Status::InvalidIdentity;
    const auto validated = ValidateBuffers(buffers);
    if (validated != Status::Ok) return validated;
    binding_ = binding;
    buffers_ = buffers;
    owner_thread_ = std::this_thread::get_id();
    bound_ = true;
    return Status::Ok;
}

Status Adapter::ValidateBinding(const Binding& binding) const noexcept {
    if (!bound_) return Status::NotBound;
    if (std::this_thread::get_id() != owner_thread_) return Status::WrongThread;
    if (!SameBinding(binding, binding_)) return Status::StaleBinding;
    return Status::Ok;
}

Publication Adapter::PublishNeutral(const Binding& binding, std::uint64_t cycle) noexcept {
    Publication result;
    result.cycle = cycle;
    result.status = ValidateBinding(binding);
    if (result.status != Status::Ok) return result;
    if (!cycle || cycle <= published_cycle_) {
        result.status = Status::InvalidCycle;
        return result;
    }
    result.status = ValidateBuffers(buffers_);
    if (result.status != Status::Ok) return result;

    // Stage all changes before touching caller buffers. This is an all-preflight
    // commit on an exclusively owned thread, not a transaction against racing
    // writers/unmapped memory. The future native fence must prove ownership.
    std::array<std::uint8_t, kNormalSize> normal{};
    std::array<std::uint8_t, kMouseSize> mouse{};
    std::memcpy(normal.data(), buffers_.normal.data, normal.size());
    std::memcpy(mouse.data(), buffers_.mouse.data, mouse.size());
    RawKeyboardShadow next_shadow{};
    const auto* raw = buffers_.raw_keyboard_source.data;
    next_shadow.repeat_policy[0] = raw[0x154];
    next_shadow.repeat_policy[1] = raw[0x155];
    result.keyboard_source_contained_input = Read<std::uint32_t>(raw, 0x50) != 0 ||
        Read<std::uint32_t>(raw, 0x54) != 0 ||
        std::any_of(raw + 0x158, raw + 0x258, [](auto byte) { return byte != 0; });

    // 3A270F..3A274F: preserve device pointer, both indices, +10 and padding.
    Zero(normal.data(), 0x14, 0x21);
    Zero(normal.data(), 0x24, 0x65);
    // 3A391B..3A394A: the four raw-modifier-derived repeat counters.
    Zero(normal.data(), 0x68, 0x78);

    // 3A2780..3A27BB buttons/repeats; 3A335C..3370/3571..35AF motion/activity;
    // 3A3538..3571 drag's native neutral form. Preserve coordinates, indices,
    // +33 padding and +64 active state so rendering/lifecycle can continue.
    Zero(mouse.data(), 0x08, 0x33);
    Zero(mouse.data(), 0x44, 0x50);
    Write<std::int32_t>(mouse.data(), 0x50, -1);
    Zero(mouse.data(), 0x54, 0x64);

    // The raw source and normal+0 pointer stay untouched. GetDeviceData is
    // incremental: clearing its held state could fabricate a later release.
    std::memcpy(buffers_.normal.data, normal.data(), normal.size());
    std::memcpy(buffers_.mouse.data, mouse.data(), mouse.size());
    shadow_ = next_shadow;
    published_cycle_ = cycle;
    result.neutralized_cache_mask = NormalCache | SpecialRepeat | Mouse;
    result.neutral_shadow_mask = RawKeyboard;
    return result;
}

Status Adapter::ValidatePublication(const Binding& binding, std::uint64_t cycle) const noexcept {
    const auto status = ValidateBinding(binding);
    if (status != Status::Ok) return status;
    if (!cycle || cycle != published_cycle_) return Status::StalePublication;
    return Status::Ok;
}

QueryResult Adapter::QueryRawModifier(const Binding& binding, std::uint64_t cycle,
                                      std::uint32_t modifier_mask) const noexcept {
    QueryResult result{ValidatePublication(binding, cycle), false};
    if (result.status != Status::Ok) return result;
    // The four masks 11/22/44/88 are observed in 3A38E0..3923.
    if (!modifier_mask || (modifier_mask & ~0xffu)) {
        result.status = Status::InvalidQuery;
        return result;
    }
    result.pressed = (shadow_.modifiers & modifier_mask) != 0;
    return result;
}

QueryResult Adapter::QueryRawKey(const Binding& binding, std::uint64_t cycle,
                                 std::uint32_t key_index) const noexcept {
    QueryResult result{ValidatePublication(binding, cycle), false};
    if (result.status != Status::Ok) return result;
    if (key_index >= shadow_.keys.size()) {
        result.status = Status::InvalidQuery;
        return result;
    }
    result.pressed = shadow_.keys[key_index] != 0;
    return result;
}

Status Adapter::CopyRawShadow(const Binding& binding, std::uint64_t cycle,
                              RawKeyboardShadow& destination) const noexcept {
    const auto status = ValidatePublication(binding, cycle);
    if (status != Status::Ok) return status;
    // Destination is an ordinary caller-owned value, not a native device object.
    destination = shadow_;
    return Status::Ok;
}

MessageDecision ClassifyMessage(const Message& message, std::uintptr_t bound_window,
                                bool suppress_audited_inputs) noexcept {
    if (!bound_window || message.window != bound_window)
        return {MessageClass::OtherWindow, false};
    if (IsLifecycle(message.id)) return {MessageClass::Lifecycle, false};
    if (IsAuditedGameplay(message))
        return {MessageClass::AuditedGameplayInput, suppress_audited_inputs};
    if (IsUncoveredStandardInput(message.id)) return {MessageClass::UncoveredInput, false};
    return {MessageClass::Unclassified, false};
}

QueueResult Adapter::FilterOwnedQueue(const Binding& binding, std::uint64_t cycle,
                                      std::uintptr_t bound_window, Message* messages,
                                      std::size_t& count, std::size_t capacity) const noexcept {
    QueueResult result;
    result.kept = count;
    result.status = ValidatePublication(binding, cycle);
    if (result.status != Status::Ok) return result;
    if (!bound_window || count > capacity ||
        capacity > std::numeric_limits<std::size_t>::max() / sizeof(Message) ||
        (!messages && capacity != 0)) {
        result.status = Status::InvalidQueue;
        return result;
    }
    if (!capacity) return result;
    Range queue{}, normal{}, mouse{}, raw{}, adapter{};
    if (!MakeRange(messages, capacity * sizeof(Message), sizeof(Message), queue)) {
        result.status = Status::InvalidQueue;
        return result;
    }
    MakeRange(buffers_.normal.data, buffers_.normal.size, kNormalSize, normal);
    MakeRange(buffers_.mouse.data, buffers_.mouse.size, kMouseSize, mouse);
    MakeRange(buffers_.raw_keyboard_source.data, buffers_.raw_keyboard_source.size,
              kRawKeyboardSize, raw);
    MakeRange(this, sizeof(*this), sizeof(*this), adapter);
    if (Overlap(queue, normal) || Overlap(queue, mouse) || Overlap(queue, raw) ||
        Overlap(queue, adapter)) {
        result.status = Status::QueueOverlapsBoundMemory;
        return result;
    }
    // count itself must not alias the message storage that will be compacted.
    Range count_range{};
    MakeRange(&count, sizeof(count), sizeof(count), count_range);
    if (Overlap(queue, count_range) || Overlap(count_range, normal) ||
        Overlap(count_range, mouse) || Overlap(count_range, raw) ||
        Overlap(count_range, adapter)) {
        result.status = Status::QueueOverlapsBoundMemory;
        return result;
    }
    std::size_t write = 0;
    for (std::size_t read = 0; read < count; ++read) {
        const auto decision = ClassifyMessage(messages[read], bound_window, true);
        if (decision.discard) {
            ++result.discarded;
        } else {
            if (decision.classification == MessageClass::UncoveredInput) ++result.uncovered_input;
            if (decision.classification == MessageClass::Unclassified) ++result.unclassified;
            if (write != read) messages[write] = messages[read];
            ++write;
        }
    }
    // Clear removed tails only inside the original valid count, preserving all
    // capacity canaries. A caller must dispatch only the returned count.
    for (std::size_t index = write; index < count; ++index) messages[index] = Message{};
    count = write;
    result.kept = write;
    return result;
}

} // namespace checkpoint_native_input
