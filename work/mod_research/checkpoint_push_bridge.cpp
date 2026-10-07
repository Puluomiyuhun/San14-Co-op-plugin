#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "checkpoint_push_bridge.h"

extern "C" void CheckpointPushBridgeCallOriginal(void*, CheckpointPushFrame*);

namespace {
struct Slot {
    volatile LONG state; // 0=unset, 1=configuration in progress, 2=published
    CheckpointPushBridgeConfig config;
    volatile LONG64 started, native_started, native_returned;
    volatile LONG64 before_calls, after_calls, abnormal_exits, active;
    bool pinned;
};
Slot slots[2]{};

std::uint64_t read64(volatile LONG64* value) noexcept {
    return static_cast<std::uint64_t>(InterlockedCompareExchange64(value, 0, 0));
}
[[noreturn]] void unconfigured_entry() noexcept {
    // Calling an unpublished entry is an installer bug. Never guess an original.
    RaiseFailFastException(nullptr, nullptr, 0);
    TerminateProcess(GetCurrentProcess(), 0xE0140001);
    __assume(0);
}
}

extern "C" int CheckpointPushBridgeConfigure(unsigned slot, const CheckpointPushBridgeConfig* config) noexcept {
    if (slot > 1 || !config || config->size != sizeof(*config) || config->version != 1 || !config->original)
        return 0;
    if (config->original == reinterpret_cast<void*>(&CheckpointPushBridge0) ||
        config->original == reinterpret_cast<void*>(&CheckpointPushBridge1) ||
        config->original == reinterpret_cast<void*>(&CheckpointPushBridgeCallOriginal)) return 0;
    Slot& s = slots[slot];
    if (InterlockedCompareExchange(&s.state, 1, 0) != 0) return 0;
    HMODULE module = nullptr;
    if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
        reinterpret_cast<LPCWSTR>(&CheckpointPushBridgeConfigure), &module)) {
        InterlockedExchange(&s.state, 0);
        return 0;
    }
    s.config = *config;
    s.pinned = true;
    InterlockedExchange(&s.state, 2);
    return 1;
}

extern "C" int CheckpointPushBridgeSnapshot(unsigned slot, CheckpointPushBridgeStats* out) noexcept {
    if (slot > 1 || !out) return 0;
    Slot& s = slots[slot];
    LONG state = InterlockedCompareExchange(&s.state, 0, 0);
    *out = {read64(&s.started), read64(&s.native_started), read64(&s.native_returned),
            read64(&s.before_calls), read64(&s.after_calls), read64(&s.abnormal_exits), read64(&s.active),
            state == 2 ? 1u : 0u, state == 2 && s.pinned ? 1u : 0u};
    return 1;
}

extern "C" __declspec(noinline) void CheckpointPushBridgeInvoke(unsigned slot, CheckpointPushFrame* frame) {
    if (slot > 1 || !frame || InterlockedCompareExchange(&slots[slot].state, 0, 0) != 2)
        unconfigured_entry();
    Slot& s = slots[slot];
    const CheckpointPushBridgeConfig& config = s.config;
    frame->slot = slot;
    frame->thread_id = GetCurrentThreadId();
    frame->call_id = static_cast<std::uint64_t>(InterlockedIncrement64(&s.started));
    InterlockedIncrement64(&s.active);
    // No __except surrounds the native call. Its SEH/C++ exception propagates.
    // Observers are nonthrowing by contract. /EHa is required for this TU.
    __try {
        if (config.before) {
            InterlockedIncrement64(&s.before_calls);
            config.before(frame, config.context);
        }
        InterlockedIncrement64(&s.native_started);
        CheckpointPushBridgeCallOriginal(config.original, frame);
        InterlockedIncrement64(&s.native_returned);
        if (config.after) {
            InterlockedIncrement64(&s.after_calls);
            config.after(frame, config.context);
        }
    } __finally {
        if (AbnormalTermination()) InterlockedIncrement64(&s.abnormal_exits);
        InterlockedDecrement64(&s.active);
    }
}
