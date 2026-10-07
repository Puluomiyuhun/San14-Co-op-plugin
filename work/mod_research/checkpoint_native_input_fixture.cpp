#include "checkpoint_native_input_core.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

using namespace checkpoint_native_input;
namespace {
void Require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class T, std::size_t N> void Put(std::array<std::uint8_t, N>& data,
                                         std::size_t offset, T value) {
    Require(offset + sizeof(value) <= N, "fixture write bounds");
    std::memcpy(data.data() + offset, &value, sizeof(value));
}
template<class T, std::size_t N> T Get(const std::array<std::uint8_t, N>& data,
                                     std::size_t offset) {
    T value{};
    Require(offset + sizeof(value) <= N, "fixture read bounds");
    std::memcpy(&value, data.data() + offset, sizeof(value));
    return value;
}
bool ZeroRange(const std::uint8_t* data, std::size_t begin, std::size_t end) {
    return std::all_of(data + begin, data + end, [](auto value) { return value == 0; });
}
Binding NewBinding() {
    Binding binding;
    binding.attempt[0] = 0xa1;
    binding.attachment[0] = 0xb2;
    binding.owner_generation = 7;
    return binding;
}
struct Fixture {
    std::array<std::uint8_t, kNormalSize + 16> normal;
    std::array<std::uint8_t, kMouseSize + 16> mouse;
    std::array<std::uint8_t, kRawKeyboardSize + 16> raw;
    Binding binding = NewBinding();
    Adapter adapter;

    Fixture() {
        normal.fill(0xa5);
        mouse.fill(0xb6);
        raw.fill(0xc7);
        Put<std::uintptr_t>(normal, 0, reinterpret_cast<std::uintptr_t>(raw.data()));
        Put<std::uint32_t>(normal, 8, 0);
        Put<std::uint32_t>(normal, 12, 1);
        Put<std::uint32_t>(mouse, 0, 1);
        Put<std::uint32_t>(mouse, 4, 0);
        Put<std::uint32_t>(raw, 0x54, 2);
    }
    Buffers buffers() {
        return {{normal.data(), normal.size()}, {mouse.data(), mouse.size()},
                {raw.data(), raw.size()}};
    }
    void Bind() { Require(adapter.Bind(binding, buffers()) == Status::Ok, "bind fixture"); }
    Publication Publish(std::uint64_t cycle = 1) {
        auto result = adapter.PublishNeutral(binding, cycle);
        Require(result.status == Status::Ok, "publish fixture");
        return result;
    }
};

void NormalAndUnknownBytes() {
    Fixture fixture;
    const auto before = fixture.normal;
    const auto mouse_before = fixture.mouse;
    const auto raw_before = fixture.raw;
    fixture.Bind();
    const auto publication = fixture.Publish();
    Require(publication.neutralized_cache_mask == (NormalCache | SpecialRepeat | Mouse),
            "exact local byte publication mask");
    for (std::size_t index = 0; index < fixture.normal.size(); ++index) {
        const bool cleared = (index >= 0x14 && index < 0x21) ||
                             (index >= 0x24 && index < 0x65) ||
                             (index >= 0x68 && index < 0x78);
        Require(fixture.normal[index] == (cleared ? 0 : before[index]),
                "normal exact ranges/unknown/pointer/indices/tail preserved");
    }
    Require(fixture.raw == raw_before, "original raw device remains unchanged");
    Require(fixture.mouse != mouse_before, "mouse also really mutated");
    // Minimal mirror of 3A2900's tested byte then current button mask query.
    const auto current = Get<std::uint32_t>(fixture.normal, 8);
    const bool action = fixture.normal[0x20] != 0 &&
        (Get<std::uint32_t>(fixture.normal, 0x14 + 4 * current) & 1) != 0;
    Require(!action, "normal consumer does not see stale button");
}

void SpecialRepeatsDoNotSurvive() {
    Fixture fixture;
    for (std::size_t index = 0; index < 4; ++index)
        Put<std::uint32_t>(fixture.normal, 0x68 + 4 * index, 45u + static_cast<unsigned>(index));
    fixture.Bind();
    fixture.Publish();
    for (std::size_t index = 0; index < 4; ++index)
        Require(Get<std::uint32_t>(fixture.normal, 0x68 + 4 * index) == 0,
                "special repeat counts neutralized beyond native 3A2700 flush");
}

void RawFacadePreservesHeldSource() {
    Fixture fixture;
    Put<std::uint32_t>(fixture.raw, 0x50, 0x22);
    fixture.raw[0x158 + 0x1e] = 1;
    fixture.raw[0x154] = 3;
    fixture.raw[0x155] = 4;
    const auto before = fixture.raw;
    const auto pointer = Get<std::uintptr_t>(fixture.normal, 0);
    fixture.Bind();
    Require(fixture.Publish().keyboard_source_contained_input,
            "source records nonneutral, never pretend physical release");
    const auto modifier = fixture.adapter.QueryRawModifier(fixture.binding, 1, 0x22);
    const auto key = fixture.adapter.QueryRawKey(fixture.binding, 1, 0x1e);
    Require(modifier.status == Status::Ok && !modifier.pressed, "modifier facade neutral");
    Require(key.status == Status::Ok && !key.pressed, "key facade neutral");
    RawKeyboardShadow shadow;
    Require(fixture.adapter.CopyRawShadow(fixture.binding, 1, shadow) == Status::Ok,
            "copy value shadow");
    Require(shadow.modifiers == 0 && shadow.event_count == 0 && shadow.last_key == 0 &&
            std::all_of(shadow.keys.begin(), shadow.keys.end(), [](auto b) { return b == 0; }) &&
            std::all_of(shadow.events.begin(), shadow.events.end(), [](auto b) { return b == 0; }),
            "shadow controls neutral");
    Require(shadow.repeat_policy[0] == 3 && shadow.repeat_policy[1] == 4,
            "source repeat policies preserved in value view");
    Require(fixture.raw == before && Get<std::uintptr_t>(fixture.normal, 0) == pointer,
            "no device object or pointer replacement");
    Require(fixture.adapter.QueryRawKey(fixture.binding, 1, 256).status == Status::InvalidQuery &&
            fixture.adapter.QueryRawModifier(fixture.binding, 1, 0x100).status == Status::InvalidQuery,
            "invalid facade requests fail closed with error");
}

void MouseExactRanges() {
    Fixture fixture;
    const auto before = fixture.mouse;
    fixture.Bind();
    fixture.Publish();
    for (std::size_t index = 0; index < fixture.mouse.size(); ++index) {
        const bool clear = (index >= 0x08 && index < 0x33) ||
                           (index >= 0x44 && index < 0x50) ||
                           (index >= 0x54 && index < 0x64);
        const bool no_drag = index >= 0x50 && index < 0x54;
        const auto expected = clear ? 0 : (no_drag ? 255 : before[index]);
        Require(fixture.mouse[index] == expected,
                "mouse exact buttons/repeat/delta/wheel/drag, preserve coords/active/padding/tail");
    }
    Require(Get<std::int32_t>(fixture.mouse, 0x50) == -1, "native neutral drag index");
    for (std::size_t index = 0; index < 3; ++index) {
        const auto slot = 3 * (Get<std::uint32_t>(fixture.mouse, 0) + 1) + index;
        Require(Get<std::uint32_t>(fixture.mouse, slot * 4) != 1,
                "3A2920-style button consumer sees no click");
    }
}

void EntirePreflightBeforeAnyWrite() {
    Fixture fixture;
    const auto normal_before = fixture.normal;
    const auto mouse_before = fixture.mouse;
    const auto raw_before = fixture.raw;
    auto buffers = fixture.buffers();
    buffers.mouse.size = kMouseSize - 1;
    Require(fixture.adapter.Bind(fixture.binding, buffers) == Status::InvalidSpan,
            "short later span rejected");
    buffers = fixture.buffers();
    buffers.mouse = {fixture.normal.data() + 8, kMouseSize};
    Require(fixture.adapter.Bind(fixture.binding, buffers) == Status::OverlappingSpans,
            "overlap rejected before layout read");
    buffers = fixture.buffers();
    buffers.raw_keyboard_source.size = std::numeric_limits<std::size_t>::max();
    Require(fixture.adapter.Bind(fixture.binding, buffers) == Status::InvalidSpan,
            "pointer range overflow rejected");
    Require(fixture.normal == normal_before && fixture.mouse == mouse_before &&
            fixture.raw == raw_before, "failed bind performs no caller buffer writes");
    fixture.Bind();
    Put<std::uint32_t>(fixture.mouse, 0, 2);
    const auto invalid_mouse = fixture.mouse;
    Require(fixture.adapter.PublishNeutral(fixture.binding, 1).status == Status::InvalidLayout,
            "later layout invalid at publication time");
    Require(fixture.normal == normal_before && fixture.mouse == invalid_mouse &&
            fixture.raw == raw_before, "no earlier normal mutation when mouse preflight fails");
    Put<std::uint32_t>(fixture.mouse, 0, 1);
    Put<std::uint32_t>(fixture.raw, 0x54, 127);
    Require(fixture.adapter.PublishNeutral(fixture.binding, 1).status == Status::InvalidLayout,
            "oversize raw event count rejected before writes");
    Require(fixture.normal == normal_before && fixture.mouse == mouse_before,
            "no earlier writes on final raw preflight failure");
}

void ThreadIdentityAndCycles() {
    Fixture fixture;
    auto invalid = fixture.binding;
    invalid.attempt.fill(0);
    Require(fixture.adapter.Bind(invalid, fixture.buffers()) == Status::InvalidIdentity,
            "nonempty attempt identity required");
    fixture.Bind();
    Require(fixture.adapter.Bind(fixture.binding, fixture.buffers()) == Status::AlreadyBound,
            "no silent attachment/thread rebind");
    auto stale = fixture.binding;
    ++stale.owner_generation;
    const auto before = fixture.normal;
    Require(fixture.adapter.PublishNeutral(stale, 1).status == Status::StaleBinding,
            "stale generation rejected");
    stale = fixture.binding;
    ++stale.attachment[0];
    Require(fixture.adapter.PublishNeutral(stale, 1).status == Status::StaleBinding,
            "foreign attachment rejected");
    Status foreign = Status::Ok;
    std::thread worker([&] { foreign = fixture.adapter.PublishNeutral(fixture.binding, 1).status; });
    worker.join();
    Require(foreign == Status::WrongThread, "foreign fixture thread refused");
    Require(fixture.normal == before, "identity/thread failures write nothing");
    Require(fixture.adapter.PublishNeutral(fixture.binding, 0).status == Status::InvalidCycle,
            "zero cycle rejected");
    fixture.Publish(2);
    fixture.normal[0x14] = 9;
    const auto after = fixture.normal;
    Require(fixture.adapter.PublishNeutral(fixture.binding, 2).status == Status::InvalidCycle &&
            fixture.adapter.PublishNeutral(fixture.binding, 1).status == Status::InvalidCycle &&
            fixture.normal == after, "replayed/regressed cycles cannot republish evidence");
}

void ForeignPointerNotReplaced() {
    Fixture fixture;
    fixture.Bind();
    Put<std::uintptr_t>(fixture.normal, 0, 0x1234567812345678ull);
    const auto before = fixture.normal;
    const auto mouse_before = fixture.mouse;
    Require(fixture.adapter.PublishNeutral(fixture.binding, 1).status == Status::RawPointerMismatch,
            "device identity drift rejected without following foreign pointer");
    Require(fixture.normal == before && fixture.mouse == mouse_before,
            "foreign pointer not overwritten and no partial mutation");
}

void FreshCyclesAreNotPhysicalRelease() {
    Fixture fixture;
    fixture.Bind();
    const auto first = fixture.Publish(12);
    fixture.normal[0x14] = 1; // owned simulation of the next native conversion
    fixture.normal[0x68] = 2;
    fixture.mouse[0x0c] = 1;
    fixture.raw[0x158 + 0x20] = 1; // held source survives between incremental polls
    const auto raw_before = fixture.raw;
    const auto second = fixture.Publish(13);
    Require(fixture.raw == raw_before && second.keyboard_source_contained_input,
            "new neutral output cycle cannot fabricate source release");
    Require(fixture.normal[0x14] == 0 && fixture.normal[0x68] == 0 && fixture.mouse[0x0c] == 0,
            "repopulated consumer data actually neutralized in later cycle");
    Require(fixture.adapter.QueryRawKey(fixture.binding, 12, 0x20).status == Status::StalePublication,
            "old query publication no longer current");
    Require(!first.release_eligible && !second.release_eligible &&
            !second.physical_release_proven && !second.full_input_hold,
            "multiple neutralized outputs do not release gate");
}

void MessageClassificationIsNarrow() {
    constexpr std::uintptr_t window = 0x4455;
    for (auto key : {0x08u, 0x0du, 0x1bu})
        for (auto id : {0x100u, 0x101u})
            Require(ClassifyMessage({window, id, key, 0}, window, true).discard,
                    "audited repost keys filtered before handler");
    for (auto id : {0x200u, 0x201u, 0x202u, 0x204u, 0x205u, 0x2a3u})
        Require(ClassifyMessage({window, id, 0, 0}, window, true).discard,
                "audited mouse messages filtered");
    for (auto id : {0x5u, 0x6u, 0x7u, 0x8u, 0xfu, 0x10u, 0x1cu, 0x113u, 0x215u, 0x2e0u}) {
        const auto decision = ClassifyMessage({window, id, 0, 0}, window, true);
        Require(!decision.discard && decision.classification == MessageClass::Lifecycle,
                "lifecycle and engine timer always delivered");
    }
    for (auto id : {0xffu, 0x102u, 0x104u, 0x111u, 0x112u, 0x203u, 0x20au, 0x319u}) {
        const auto decision = ClassifyMessage({window, id, 0, 0}, window, true);
        Require(!decision.discard && decision.classification == MessageClass::UncoveredInput,
                "unknown input remains explicit uncovered, not swallowed");
    }
    Require(!ClassifyMessage({window, 0x100, 0x41, 0}, window, true).discard,
            "unaudited A key isn't silently claimed covered");
    Require(!ClassifyMessage({window, 0x8001, 0, 0}, window, true).discard &&
            !ClassifyMessage({window, 0x401, 0, 0}, window, true).discard,
            "custom engine messages always delivered");
    Require(!ClassifyMessage({window + 1, 0x201, 0, 0}, window, true).discard &&
            !ClassifyMessage({window, 0x201, 0, 0}, window, false).discard,
            "other windows and inactive filter preserve input");
}

void QueueRepostsAndFailures() {
    Fixture fixture;
    fixture.Bind();
    fixture.Publish();
    constexpr std::uintptr_t window = 0x4455;
    std::array<Message, 10> queue{{
        {window, 0x100, 0x0d, 1}, // original Enter
        {window, 0x201, 0, 2},   // already-posted mouse event
        {window, 0x000f, 0, 3}, // paint
        {window, 0x8001, 0, 4}, // engine notification, unknown identity
        {window, 0x20a, 0, 5},  // unaudited wheel message stays
        {window, 0x0010, 0, 6}, // close
        {window + 1, 0x201, 0, 7},
        {window, 0x101, 0x0d, 8},
        {window, 0x202, 0, 9},
        {0xdead, 0xbeef, 0xcafe, 42}, // beyond valid count canary
    }};
    const auto original = queue;
    std::size_t count = 9;
    auto result = fixture.adapter.FilterOwnedQueue(fixture.binding, 1, window,
                                                   queue.data(), count, queue.size());
    Require(result.status == Status::Ok && count == 5 && result.discarded == 4 &&
            result.uncovered_input == 1 && result.unclassified == 1,
            "owned queue reports partial coverage and removes both sides of repost");
    for (std::size_t index = 0; index < 5; ++index)
        Require(queue[index].lparam == static_cast<std::intptr_t>(index + 3),
                "retained message order unchanged");
    Require(queue[9].window == original[9].window && queue[9].id == original[9].id &&
            queue[9].lparam == original[9].lparam, "capacity tail canary preserved");
    Require(!result.actual_os_queue_drained && !result.full_input_hold,
            "owned batch never promoted to actual OS queue coverage");
    for (std::size_t index = 5; index < 9; ++index)
        Require(queue[index].window == 0 && queue[index].id == 0, "removed tail cleared");
    const auto kept = queue;
    const auto good_count = count;
    result = fixture.adapter.FilterOwnedQueue(fixture.binding, 1, 0, queue.data(), count, queue.size());
    Require(result.status == Status::InvalidQueue && count == good_count &&
            std::memcmp(queue.data(), kept.data(), sizeof queue) == 0,
            "invalid window causes no queue writes");
    count = 11;
    result = fixture.adapter.FilterOwnedQueue(fixture.binding, 1, window, queue.data(), count, queue.size());
    Require(result.status == Status::InvalidQueue && count == 11,
            "bad count rejected without walking queue");
    count = 1;
    result = fixture.adapter.FilterOwnedQueue(fixture.binding, 1, window,
        reinterpret_cast<Message*>(fixture.normal.data()), count, 1);
    Require(result.status == Status::QueueOverlapsBoundMemory && count == 1,
            "queue can't corrupt bound native cache");
    count = 0;
    result = fixture.adapter.FilterOwnedQueue(fixture.binding, 1, window, nullptr, count, 0);
    Require(result.status == Status::Ok && count == 0, "empty owned queue is safe");
}

void CoverageCannotUpgradeToGlobalHold() {
    Fixture fixture;
    auto unbound = fixture.adapter.PublishNeutral(fixture.binding, 1);
    Require(unbound.status == Status::NotBound && unbound.neutralized_cache_mask == 0 &&
            unbound.missing_mask == kAlwaysMissing, "failure carries no publication evidence");
    fixture.Bind();
    const auto publication = fixture.Publish();
    Require(publication.complete_native_channel_mask == 0 &&
            publication.missing_native_channel_mask == kAllChannels &&
            publication.missing_mask == kAlwaysMissing,
            "all native channels require actual consumer/drain/fence integration");
    for (auto missing : {RealProviderDrain, ControllerDIProvider, AlternateControllerProvider,
                         PhysicalReleaseEvidence, NativeOwnerThreadFence, PendingBusinessBoundary,
                         LaterNeutralCycleAndGrant, EnginePumpAndWorkerProgress})
        Require((publication.missing_mask & missing) != 0, "critical blockers cannot disappear");
    Require(publication.neutral_shadow_mask == RawKeyboard &&
            !publication.full_input_hold && !publication.release_eligible,
            "partial native writes remain distinct from full hold and later gate grant");
}
} // namespace

int main(int argc, char** argv) {
    struct Case { const char* id; void (*run)(); };
    const std::array<Case, 11> cases{{
        {"normal_exact_write_ranges_and_canaries", NormalAndUnknownBytes},
        {"special_repeat_beyond_native_flush", SpecialRepeatsDoNotSurvive},
        {"raw_value_facade_preserves_incremental_source", RawFacadePreservesHeldSource},
        {"mouse_exact_neutral_ranges_and_coordinates", MouseExactRanges},
        {"all_spans_preflight_before_any_write", EntirePreflightBeforeAnyWrite},
        {"binding_thread_generation_and_cycle_fences", ThreadIdentityAndCycles},
        {"foreign_raw_pointer_refused_not_replaced", ForeignPointerNotReplaced},
        {"later_neutral_output_is_not_physical_release", FreshCyclesAreNotPhysicalRelease},
        {"narrow_message_filter_preserves_lifecycle", MessageClassificationIsNarrow},
        {"owned_queue_reposts_order_and_failure_atomicity", QueueRepostsAndFailures},
        {"partial_success_never_claims_global_hold", CoverageCannotUpgradeToGlobalHold},
    }};
    std::vector<std::string> passed;
    std::vector<std::string> failed;
    for (const auto& test : cases) {
        try {
            test.run();
            passed.emplace_back(test.id);
            std::cout << "PASS " << test.id << '\n';
        } catch (const std::exception& error) {
            failed.emplace_back(test.id);
            std::cerr << "FAIL " << test.id << ": " << error.what() << '\n';
        }
    }
    if (argc == 2) {
        std::ofstream report(argv[1], std::ios::binary | std::ios::trunc);
        if (!report) { std::cerr << "cannot open fixture report\n"; return 2; }
        report << "{\n  \"schema\": \"checkpoint-native-input-fixture/v1\",\n"
               << "  \"scope\": \"owned-buffers-and-owned-message-arrays-only\",\n"
               << "  \"real_game_accessed\": false,\n"
               << "  \"physical_input_read\": false,\n"
               << "  \"native_hooks_installed\": false,\n"
               << "  \"full_native_input_hold_proven\": false,\n"
               << "  \"missing_mask\": " << kAlwaysMissing << ",\n"
               << "  \"cases\": [\n";
        for (std::size_t index = 0; index < cases.size(); ++index) {
            const bool ok = std::find(passed.begin(), passed.end(), cases[index].id) != passed.end();
            report << "    {\"id\": \"" << cases[index].id << "\", \"passed\": "
                   << (ok ? "true" : "false") << "}" << (index + 1 < cases.size() ? "," : "") << '\n';
        }
        report << "  ],\n  \"passed\": " << passed.size() << ",\n  \"failed\": " << failed.size() << "\n}\n";
    }
    std::cout << passed.size() << "/" << cases.size() << " owned fixtures passed\n";
    return failed.empty() ? 0 : 1;
}
