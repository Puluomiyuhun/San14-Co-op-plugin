#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include "checkpoint_push_bridge.h"

extern "C" {
std::uint64_t CheckpointPushFixtureArgs[2][4]{};
std::uint64_t CheckpointPushFixtureModulo[2]{};
std::uint64_t CheckpointPushFixtureNativeCalls[2]{};
alignas(16) unsigned char CheckpointPushFixtureNvPattern[10][16]{};
alignas(16) unsigned char CheckpointPushFixtureReturnPattern[2][16]{};
void CheckpointPushFixtureBefore(const CheckpointPushFrame*, void*) noexcept;
void CheckpointPushFixtureAfter(const CheckpointPushFrame*, void*) noexcept;
void CheckpointPushFixtureOriginal0();
void CheckpointPushFixtureOriginal1();
void CheckpointPushBridgeCallOriginal(void*, CheckpointPushFrame*);
void CheckpointPushBridgeInvoke(unsigned, CheckpointPushFrame*);
}

struct alignas(16) Capture {
    std::uint64_t rax, pad;
    unsigned char xmm0[16];
    std::uint64_t rsp_before, rsp_after;
    std::uint64_t nonvolatile[8];
    unsigned char xmm_nonvolatile[10][16];
};
static_assert(sizeof(Capture) == 0x110);
extern "C" void CheckpointPushFixtureRun(CheckpointPushEntry, Capture*);

static int failures = 0, checks = 0;
static unsigned mode = 0;
static unsigned before[2]{}, after[2]{};
static CheckpointPushFrame observed_before[2]{}, observed_after[2]{};
static const std::uint64_t arguments[4] = {
    0x1020304050607080ull, 0x90a0b0c0d0e0f001ull, 0xf123456789abcdefull, 0xfedcba9876543210ull};
static const std::uint64_t nonvolatile[8] = {
    0x1111111122222222ull, 0x2222222233333333ull, 0x3333333344444444ull, 0x4444444455555555ull,
    0x5555555566666666ull, 0x6666666677777777ull, 0x7777777788888888ull, 0x8888888899999999ull};
static bool seh_seen = false, cpp_seen = false;
static constexpr DWORD fixture_exception_code = 0xE0421414;
static void check(const char* label, bool condition) {
    ++checks;
    if (!condition) { ++failures; std::printf("FAIL %s\n", label); }
}

extern "C" void CheckpointPushFixtureBeforeRecord(const CheckpointPushFrame* f, void* context) noexcept {
    if (f->slot > 1) { ++failures; return; }
    ++before[f->slot]; observed_before[f->slot] = *f;
    if (context != &before[f->slot]) ++failures;
}
extern "C" void CheckpointPushFixtureAfterRecord(const CheckpointPushFrame* f, void* context) noexcept {
    if (f->slot > 1) { ++failures; return; }
    ++after[f->slot]; observed_after[f->slot] = *f;
    if (context != &before[f->slot]) ++failures;
}
extern "C" __declspec(noinline) void CheckpointPushFixtureMaybeThrow(unsigned slot) {
    if (slot == 1 && mode == 1) {
        const ULONG_PTR args[] = {0x1122334455667788ull, 0xfedcba9876543210ull};
        RaiseException(fixture_exception_code, 0, 2, args);
    }
    if (slot == 1 && mode == 2) throw std::runtime_error("native-fixture-exception");
}
static int exception_filter(EXCEPTION_POINTERS* ex) {
    auto* r = ex->ExceptionRecord;
    if (r->ExceptionCode != fixture_exception_code) return EXCEPTION_CONTINUE_SEARCH;
    seh_seen = r->NumberParameters == 2 && r->ExceptionInformation[0] == 0x1122334455667788ull
        && r->ExceptionInformation[1] == 0xfedcba9876543210ull;
    return EXCEPTION_EXECUTE_HANDLER;
}
static std::uint64_t catch_seh(std::uint64_t a, std::uint64_t b, std::uint64_t c, std::uint64_t d) {
    __try { return CheckpointPushBridge1(a,b,c,d); }
    __except(exception_filter(GetExceptionInformation())) { return 0xAABBCCDDEEFF0001ull; }
}
static std::uint64_t catch_cpp(std::uint64_t a, std::uint64_t b, std::uint64_t c, std::uint64_t d) {
    try { return CheckpointPushBridge1(a,b,c,d); }
    catch (const std::runtime_error& e) {
        cpp_seen = std::strcmp(e.what(), "native-fixture-exception") == 0;
        return 0xAABBCCDDEEFF0002ull;
    }
}
static bool has_unwind(void* entry) {
    DWORD64 base = 0;
    return RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(entry), &base, nullptr) != nullptr;
}
static void capture_checks(const Capture& c) {
    check("caller RSP exact", c.rsp_before == c.rsp_after);
    check("caller RSP aligned for call", (c.rsp_before & 15) == 0);
    check("all 8 nonvolatile GPRs", std::memcmp(c.nonvolatile, nonvolatile, sizeof nonvolatile) == 0);
    check("all XMM6..XMM15", std::memcmp(c.xmm_nonvolatile, CheckpointPushFixtureNvPattern,
                                          sizeof CheckpointPushFixtureNvPattern) == 0);
}

int main() {
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    for (unsigned i=0;i<10;++i) for (unsigned j=0;j<16;++j) CheckpointPushFixtureNvPattern[i][j] = (unsigned char)(i*17+j);
    for (unsigned i=0;i<2;++i) for (unsigned j=0;j<16;++j) CheckpointPushFixtureReturnPattern[i][j] = (unsigned char)(0x40+i*31+j);
    for (unsigned s=0;s<2;++s) {
        CheckpointPushBridgeConfig cfg;
        cfg.original = s ? reinterpret_cast<void*>(&CheckpointPushFixtureOriginal1) : reinterpret_cast<void*>(&CheckpointPushFixtureOriginal0);
        cfg.before = CheckpointPushFixtureBefore; cfg.after = CheckpointPushFixtureAfter; cfg.context = &before[s];
        check("configure once", CheckpointPushBridgeConfigure(s, &cfg) == 1);
        check("reject reconfiguration", CheckpointPushBridgeConfigure(s, &cfg) == 0);
    }
    check("entry0 unwind", has_unwind(reinterpret_cast<void*>(&CheckpointPushBridge0)));
    check("entry1 unwind", has_unwind(reinterpret_cast<void*>(&CheckpointPushBridge1)));
    check("call-original unwind", has_unwind(reinterpret_cast<void*>(&CheckpointPushBridgeCallOriginal)));
    check("C++ finally unwind", has_unwind(reinterpret_cast<void*>(&CheckpointPushBridgeInvoke)));
    check("fixture prolog unwind", has_unwind(reinterpret_cast<void*>(&CheckpointPushFixtureRun)));
    for (unsigned s=0;s<2;++s) {
        Capture c{};
        CheckpointPushFixtureRun(s ? CheckpointPushBridge1 : CheckpointPushBridge0, &c);
        capture_checks(c);
        check("RAX all 64 bits", c.rax == 0xfedcba9876543210ull+s);
        check("XMM0 128 bits", std::memcmp(c.xmm0, CheckpointPushFixtureReturnPattern[s], 16) == 0);
        check("four native arguments exact", std::memcmp(CheckpointPushFixtureArgs[s], arguments, sizeof arguments) == 0);
        check("before arguments exact", std::memcmp(observed_before[s].args, arguments, sizeof arguments) == 0);
        check("after arguments exact", std::memcmp(observed_after[s].args, arguments, sizeof arguments) == 0);
        check("native entry stack aligned", CheckpointPushFixtureModulo[s] == 8);
        check("observer bridge-entry stack", (observed_before[s].caller_entry_rsp & 15) == 8);
        check("after sees full native return", observed_after[s].result_rax == c.rax &&
              std::memcmp(observed_after[s].result_xmm0, c.xmm0, 16) == 0);
        check("exactly one original", CheckpointPushFixtureNativeCalls[s] == 1);
        check("one before and one after", before[s] == 1 && after[s] == 1);
    }
    mode = 1;
    Capture seh{}; CheckpointPushFixtureRun(catch_seh, &seh); capture_checks(seh);
    check("native SEH code/parameters propagated", seh_seen && seh.rax == 0xAABBCCDDEEFF0001ull);
    mode = 2;
    Capture cpp{}; CheckpointPushFixtureRun(catch_cpp, &cpp); capture_checks(cpp);
    check("native C++ exception propagated", cpp_seen && cpp.rax == 0xAABBCCDDEEFF0002ull);
    CheckpointPushBridgeStats s0{}, s1{};
    CheckpointPushBridgeSnapshot(0, &s0); CheckpointPushBridgeSnapshot(1, &s1);
    check("slot0 counts independent", s0.started==1 && s0.native_started==1 && s0.native_returned==1 && s0.active==0 && s0.abnormal_exits==0);
    check("slot1 exceptional counts", s1.started==3 && s1.native_started==3 && s1.native_returned==1 && s1.active==0 && s1.abnormal_exits==2);
    check("no after on native exception", s1.before_calls==3 && s1.after_calls==1 && before[1]==3 && after[1]==1);
    check("exactly one original even on throws", CheckpointPushFixtureNativeCalls[1] == 3);
    check("module pinned", s0.module_pinned==1 && s1.module_pinned==1);
    std::printf("{\"schema\":\"san14.checkpoint-push-bridge-fixture.v1\",\"result\":\"%s\",\"checks\":%d,\"failures\":%d,"
        "\"native_gameplay_enabled\":false,\"game_process_access\":false,\"scope\":\"Own EXE only; ABI/unwind, not a game hook\"}\n",
        failures ? "FAIL" : "PASS", checks, failures);
    return failures ? 1 : 0;
}
