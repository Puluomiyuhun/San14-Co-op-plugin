#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>

#include "checkpoint_native_input_consumer_bridge.h"
#include "checkpoint_native_input_consumer_archived.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace core = checkpoint_native_input;
namespace consumer = checkpoint_native_input_consumer;
namespace {
void Require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
template<class T> void Put(std::uint8_t* bytes, std::size_t at, T value) {
    std::memcpy(bytes + at, &value, sizeof value);
}
template<class T> T Get(const void* bytes, std::size_t at) {
    T value;
    std::memcpy(&value, static_cast<const std::uint8_t*>(bytes) + at, sizeof value);
    return value;
}

// Only self-owned memory. The archived leaf contains no call/RIP references and
// was independently bounded/hashed by the companion archive audit.
class OwnedLeaf {
public:
    OwnedLeaf() {
        page_ = VirtualAlloc(nullptr, 4096, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
        Require(page_ != nullptr, "allocate self-owned leaf page");
        std::memcpy(page_, consumer::kArchivedMouseQuery.data(), consumer::kArchivedMouseQuery.size());
        DWORD old = 0;
        if (!VirtualProtect(page_, 4096, PAGE_EXECUTE_READ, &old)) {
            VirtualFree(page_, 0, MEM_RELEASE);
            page_ = nullptr;
            throw std::runtime_error("protect self-owned leaf page");
        }
        Require(FlushInstructionCache(GetCurrentProcess(), page_, consumer::kArchivedMouseQuery.size()) != 0,
                "flush only own process instruction cache");
    }
    ~OwnedLeaf() { if (page_) VirtualFree(page_, 0, MEM_RELEASE); }
    consumer::MouseQuery entry() const { return reinterpret_cast<consumer::MouseQuery>(page_); }
private:
    void* page_ = nullptr;
};

struct Probe {
    consumer::MouseQuery archived = nullptr;
    consumer::MouseQueryBridge* bridge = nullptr;
    core::Binding binding{};
    const void* seen_cache = nullptr;
    std::uint32_t seen_button = 0;
    unsigned calls = 0;
    std::uint32_t constant_return = 0;
    const void* thrown_address = nullptr;
    bool throw_now = false;
    bool recurse = false;
    bool inspect_neutral = false;
    bool saw_neutral = false;
    consumer::Status nested_status = consumer::Status::NotBound;
};
thread_local Probe* probe = nullptr;

struct OriginalFailure : std::runtime_error {
    const void* token;
    std::uint32_t code = 0xA41234u;
    explicit OriginalFailure(const void* owner) : std::runtime_error("owned exception"), token(owner) {}
};

std::uint32_t ObservedTarget(const void* cache, std::uint32_t button) {
    Require(probe != nullptr, "fixture probe bound");
    probe->seen_cache = cache;
    probe->seen_button = button;
    ++probe->calls;
    if (probe->inspect_neutral) {
        const auto* bytes = static_cast<const std::uint8_t*>(cache);
        probe->saw_neutral = std::all_of(bytes + 0x08, bytes + 0x33, [](auto value) { return value == 0; }) &&
            Get<std::int32_t>(cache, 0x50) == -1;
        Require(probe->saw_neutral, "target observed neutral state before its read");
    }
    if (probe->recurse) {
        probe->recurse = false;
        consumer::ScopedRoute nested(*probe->bridge,
            {probe->binding, 900, consumer::Mode::NeutralizeThenForward});
        Require(CheckpointNativeMouseQueryBridge(cache, button) == 0, "nested target refused");
        probe->nested_status = nested.report().status;
    }
    if (probe->throw_now) {
        try { throw OriginalFailure(probe); }
        catch (const OriginalFailure& error) { probe->thrown_address = &error; throw; }
    }
    if (probe->archived) return probe->archived(cache, button);
    return probe->constant_return;
}

struct Fixture {
    std::array<std::uint8_t, core::kNormalSize + 16> normal{};
    std::array<std::uint8_t, core::kMouseSize + 16> mouse{};
    std::array<std::uint8_t, core::kRawKeyboardSize + 16> raw{};
    core::Binding binding{};
    consumer::MouseQueryBridge bridge;
    Probe own_probe;

    explicit Fixture(consumer::MouseQuery target = &ObservedTarget) {
        normal.fill(0xa5); mouse.fill(0xb6); raw.fill(0xc7);
        binding.attempt[0] = 1;
        binding.attachment[0] = 2;
        binding.owner_generation = 3;
        Put<std::uintptr_t>(normal.data(), 0, reinterpret_cast<std::uintptr_t>(raw.data()));
        Put<std::uint32_t>(normal.data(), 8, 0);
        Put<std::uint32_t>(normal.data(), 12, 1);
        Put<std::uint32_t>(mouse.data(), 0, 0);
        Put<std::uint32_t>(mouse.data(), 4, 1);
        Put<std::uint32_t>(mouse.data(), 0x10, 1); // current right-button pressed
        Put<std::uint32_t>(raw.data(), 0x54, 2);
        own_probe.bridge = &bridge;
        own_probe.binding = binding;
        probe = &own_probe;
        Require(bridge.Bind(binding, buffers(), target) == consumer::Status::Ok, "bind fixture bridge");
    }
    ~Fixture() { probe = nullptr; }
    core::Buffers buffers() {
        return {{normal.data(), normal.size()}, {mouse.data(), mouse.size()}, {raw.data(), raw.size()}};
    }
    consumer::Request request(std::uint64_t cycle = 1,
                              consumer::Mode mode = consumer::Mode::NeutralizeThenForward) const {
        return {binding, cycle, mode};
    }
};

void ExactArchivedLeafAbi() {
    OwnedLeaf leaf;
    Fixture fixture(leaf.entry());
    const auto unchanged = fixture.mouse;
    consumer::ScopedRoute route(fixture.bridge, fixture.request(0, consumer::Mode::ForwardUntouched));
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 1,
            "archived query executes through actual bridge returning full EAX=1");
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 0xffffffffu) == 0,
            "archived unsigned index rejection returns full EAX=0");
    Require(fixture.mouse == unchanged, "forward mode leaves input bytes untouched");
    Require(route.report().original_completed && !route.report().complete_native_input_hold,
            "target ran, no global hold claim");
}

void PublishBeforeActualArchivedConsumer() {
    OwnedLeaf leaf;
    Fixture fixture;
    fixture.own_probe.archived = leaf.entry();
    fixture.own_probe.inspect_neutral = true;
    const auto raw_before = fixture.raw;
    const auto normal_pointer = Get<std::uintptr_t>(fixture.normal.data(), 0);
    Require(leaf.entry()(fixture.mouse.data(), 1) == 1, "starting actual leaf sees pressed button");
    consumer::ScopedRoute route(fixture.bridge, fixture.request());
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 0,
            "same archived leaf sees neutral state through bridge");
    Require(fixture.own_probe.saw_neutral && fixture.own_probe.calls == 1,
            "publication completed before exactly one original call");
    Require(route.report().publication.neutralized_cache_mask ==
            (core::NormalCache | core::SpecialRepeat | core::Mouse), "core performed real cache writes");
    Require(fixture.raw == raw_before && Get<std::uintptr_t>(fixture.normal.data(), 0) == normal_pointer,
            "original raw provider source/pointer unchanged");
}

void ExactArgumentsAndFullReturn() {
    Fixture fixture;
    fixture.own_probe.constant_return = 0xA5F01234u;
    consumer::ScopedRoute route(fixture.bridge, fixture.request(1, consumer::Mode::ForwardUntouched));
    const auto value = CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 0xF1234567u);
    Require(value == 0xA5F01234u && fixture.own_probe.seen_button == 0xF1234567u &&
            fixture.own_probe.seen_cache == fixture.mouse.data(),
            "full uint32 arguments and return preserved without bool conversion");
    Require(route.report().original_return == value && route.report().original_completed,
            "report records original full return");
}

void ExceptionIdentityAndRouteUnwind() {
    Fixture fixture;
    fixture.own_probe.throw_now = true;
    {
        consumer::ScopedRoute route(fixture.bridge, fixture.request());
        bool caught = false;
        try { CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1); }
        catch (const OriginalFailure& error) {
            caught = true;
            Require(&error == fixture.own_probe.thrown_address && error.token == &fixture.own_probe &&
                    error.code == 0xA41234u && std::string(error.what()) == "owned exception",
                    "same original C++ exception rethrown through exact two-register ABI entry");
        }
        Require(caught && route.report().exception_rethrown &&
                route.report().status == consumer::Status::OriginalException &&
                !route.report().original_completed, "exception state explicit, never fake success");
    }
    fixture.own_probe.throw_now = false;
    fixture.own_probe.constant_return = 7;
    consumer::ScopedRoute route(fixture.bridge, fixture.request(2));
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 7,
            "reentrancy guard/route survive exception and allow next original");
}

void LifecycleWorkersContinueInOwnedHost() {
    OwnedLeaf leaf;
    Fixture fixture(leaf.entry());
    unsigned pump_ticks = 0, root_ticks = 0, load_worker_completions = 0, after_query_ticks = 0;
    for (std::uint64_t cycle = 1; cycle <= 8; ++cycle) {
        ++pump_ticks; // fixture-owned host update; no real window/device
        ++root_ticks;
        Put<std::uint32_t>(fixture.mouse.data(), 0x10, 1); // fixture conversion
        {
            consumer::ScopedRoute route(fixture.bridge, fixture.request(cycle));
            Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 0,
                    "consumer sees neutral on every owned update");
            Require(route.report().original_completed, "query's original target always executes");
        }
        ++load_worker_completions;
        ++after_query_ticks;
    }
    Require(pump_ticks == 8 && root_ticks == 8 && load_worker_completions == 8 && after_query_ticks == 8,
            "bridge never aborts or suppresses surrounding owned host updates");
}

void BadIdentityCacheCycleAndMode() {
    Fixture fixture;
    const auto normal_before = fixture.normal;
    const auto mouse_before = fixture.mouse;
    auto request = fixture.request();
    ++request.binding.attachment[0];
    consumer::Report report;
    Require(fixture.bridge.Invoke(request, fixture.mouse.data(), 1, report) == 0 &&
            report.status == consumer::Status::StaleBinding && !report.original_started,
            "foreign attachment refused");
    request = fixture.request();
    Require(fixture.bridge.Invoke(request, fixture.mouse.data() + 1, 1, report) == 0 &&
            report.status == consumer::Status::UnexpectedCache, "foreign pointer refused before read");
    request.mode = static_cast<consumer::Mode>(77);
    Require(fixture.bridge.Invoke(request, fixture.mouse.data(), 1, report) == 0 &&
            report.status == consumer::Status::InvalidMode, "unknown mode cannot bypass gate");
    Require(fixture.normal == normal_before && fixture.mouse == mouse_before && fixture.own_probe.calls == 0,
            "refusals do not mutate caches or invoke target");
    fixture.bridge.Invoke(fixture.request(2), fixture.mouse.data(), 1, report);
    const auto count = fixture.own_probe.calls;
    Require(fixture.bridge.Invoke(fixture.request(2), fixture.mouse.data(), 1, report) == 0 &&
            report.status == consumer::Status::PublicationRejected &&
            report.core_status == core::Status::InvalidCycle && fixture.own_probe.calls == count,
            "old publication cycle cannot consume unrefreshed evidence");
}

void WrongThreadAndMissingRoute() {
    Fixture fixture;
    consumer::Report foreign;
    std::thread worker([&] {
        fixture.bridge.Invoke(fixture.request(), fixture.mouse.data(), 1, foreign);
        const auto before = consumer::UnroutedCallCountForThisThread();
        Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 0 &&
                consumer::UnroutedCallCountForThisThread() == before + 1,
                "unrouted worker has no inherited TLS routing");
    });
    worker.join();
    Require(foreign.status == consumer::Status::WrongThread && fixture.own_probe.calls == 0,
            "foreign thread never reaches original or mutates native caches");
    const auto before = consumer::UnroutedCallCountForThisThread();
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 0 &&
            consumer::UnroutedCallCountForThisThread() == before + 1, "absent route explicit local refusal");
}

void ReentrantOriginalRefusedAndOuterPreserved() {
    Fixture fixture;
    fixture.own_probe.recurse = true;
    fixture.own_probe.constant_return = 0xA5000001u;
    consumer::ScopedRoute route(fixture.bridge, fixture.request());
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 0xA5000001u,
            "outer result retained across rejected recursive bridge entry");
    Require(fixture.own_probe.nested_status == consumer::Status::ReentrantCall &&
            fixture.own_probe.calls == 1 && route.report().original_completed,
            "nested scope restored outer route and did not duplicate target");
}

void LaterPreflightFailureDoesNotConsume() {
    Fixture fixture;
    Put<std::uint32_t>(fixture.raw.data(), 0x54, 127);
    const auto normal_before = fixture.normal;
    const auto mouse_before = fixture.mouse;
    consumer::ScopedRoute route(fixture.bridge, fixture.request());
    Require(CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1) == 0 &&
            route.report().status == consumer::Status::PublicationRejected &&
            route.report().core_status == core::Status::InvalidLayout,
            "core's final span/layout validation failure blocks target");
    Require(fixture.normal == normal_before && fixture.mouse == mouse_before &&
            fixture.own_probe.calls == 0, "no partial cache writes or target call");
}

void BoundTargetAndCoverageLimits() {
    Fixture fixture;
    consumer::MouseQueryBridge unbound;
    Require(unbound.Bind(fixture.binding, fixture.buffers(), nullptr) == consumer::Status::InvalidTarget &&
            unbound.Bind(fixture.binding, fixture.buffers(), &CheckpointNativeMouseQueryBridge) == consumer::Status::InvalidTarget,
            "null or direct recursive target rejected");
    consumer::ScopedRoute route(fixture.bridge, fixture.request());
    CheckpointNativeMouseQueryBridge(fixture.mouse.data(), 1);
    Require(route.report().publication.complete_native_channel_mask == 0 &&
            route.report().publication.missing_mask == core::kAlwaysMissing &&
            !route.report().complete_native_input_hold && !route.report().native_hook_installed,
            "one working consumer path cannot upgrade complete native input coverage");
}
} // namespace

int main(int argc, char** argv) {
    struct Case { const char* id; void (*run)(); };
    const std::array<Case, 10> cases{{
        {"actual_archived_leaf_full_eax_abi", ExactArchivedLeafAbi},
        {"publish_before_actual_archived_consumer", PublishBeforeActualArchivedConsumer},
        {"exact_rcx_edx_and_full_uint32_return", ExactArgumentsAndFullReturn},
        {"same_cpp_exception_and_route_unwind", ExceptionIdentityAndRouteUnwind},
        {"owned_host_pump_root_worker_continue", LifecycleWorkersContinueInOwnedHost},
        {"identity_pointer_cycle_mode_refusal", BadIdentityCacheCycleAndMode},
        {"thread_owner_and_absent_tls_route", WrongThreadAndMissingRoute},
        {"reentry_refused_outer_call_retained", ReentrantOriginalRefusedAndOuterPreserved},
        {"all_preflight_before_target", LaterPreflightFailureDoesNotConsume},
        {"invalid_target_and_no_global_hold_claim", BoundTargetAndCoverageLimits},
    }};
    std::vector<std::string> passed;
    std::vector<std::string> failed;
    for (const auto& item : cases) {
        try { item.run(); passed.emplace_back(item.id); std::cout << "PASS " << item.id << '\n'; }
        catch (const std::exception& error) {
            failed.emplace_back(item.id);
            std::cerr << "FAIL " << item.id << ": " << error.what() << '\n';
        }
    }
    if (argc == 2) {
        std::ofstream out(argv[1], std::ios::binary | std::ios::trunc);
        if (!out) return 2;
        out << "{\n  \"schema\": \"checkpoint-native-input-consumer-fixture/v1\",\n"
            << "  \"scope\": \"owned_buffers_owned_rx_archive_leaf_owned_host_callbacks\",\n"
            << "  \"archived_leaf_rva\": \"0x3a2920\",\n"
            << "  \"archived_leaf_executed_through_bridge\": true,\n"
            << "  \"native_game_accessed\": false,\n"
            << "  \"devices_windows_physical_input_accessed\": false,\n"
            << "  \"game_pump_progress_proven\": false,\n"
            << "  \"native_hook_installed\": false,\n"
            << "  \"complete_native_input_hold\": false,\n  \"cases\": [\n";
        for (std::size_t i = 0; i < cases.size(); ++i) {
            const bool ok = std::find(passed.begin(), passed.end(), cases[i].id) != passed.end();
            out << "    {\"id\": \"" << cases[i].id << "\", \"passed\": "
                << (ok ? "true" : "false") << "}" << (i + 1 < cases.size() ? "," : "") << '\n';
        }
        out << "  ],\n  \"passed\": " << passed.size() << ",\n  \"failed\": " << failed.size() << "\n}\n";
    }
    std::cout << passed.size() << '/' << cases.size() << " controlled consumer fixtures passed\n";
    return failed.empty() ? 0 : 1;
}
