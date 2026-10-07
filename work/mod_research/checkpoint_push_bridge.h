#pragma once
#include <cstddef>
#include <cstdint>

// Win64 INTEGER/pointer RCX,RDX,R8,R9 only, no stack or floating-point args.
// Both fixed entry points preserve original RAX (all 64 bits) and XMM0 (128).
// No hook/installer/game API is provided. Use a normally OS-loaded PE; do not
// copy these functions as raw trampolines. Configure outside DllMain once BEFORE publishing an
// entry point. This module is pinned until process exit; no reset/unload API.
// Original, callbacks and context must stay alive. Observers must not throw,
// alter this frame, or recursively enter either bridge. Original exceptions
// propagate unchanged; normal after is not called on an exceptional exit.

struct alignas(16) CheckpointPushFrame {
    std::uint64_t args[4];              // 00..1f, immutable observations
    std::uint64_t result_rax;           // 20, zero in before callback
    std::uint64_t reserved_28;          // 28
    std::uint8_t result_xmm0[16];       // 30, zero in before callback
    std::uint64_t caller_entry_rsp;     // 40, original bridge entry stack
    std::uint32_t slot;                 // 48
    std::uint32_t thread_id;            // 4c
    std::uint64_t call_id;              // 50, monotonic per slot
    std::uint64_t reserved_58;          // 58
};
static_assert(sizeof(CheckpointPushFrame) == 0x60);
static_assert(offsetof(CheckpointPushFrame, result_rax) == 0x20);
static_assert(offsetof(CheckpointPushFrame, result_xmm0) == 0x30);
static_assert(offsetof(CheckpointPushFrame, caller_entry_rsp) == 0x40);

using CheckpointPushObserver = void (*)(const CheckpointPushFrame*, void*) noexcept;
using CheckpointPushEntry = std::uint64_t (*)(std::uint64_t, std::uint64_t,
                                             std::uint64_t, std::uint64_t);

struct CheckpointPushBridgeConfig {
    std::uint32_t size = sizeof(CheckpointPushBridgeConfig);
    std::uint32_t version = 1;
    void* original = nullptr;
    CheckpointPushObserver before = nullptr;
    CheckpointPushObserver after = nullptr;
    void* context = nullptr;
};

struct CheckpointPushBridgeStats {
    std::uint64_t started, native_started, native_returned;
    std::uint64_t before_calls, after_calls, abnormal_exits, active;
    std::uint32_t configured, module_pinned;
};

extern "C" {
// 1=installed immutable config; 0=invalid/already configured/pin failed.
int CheckpointPushBridgeConfigure(unsigned slot, const CheckpointPushBridgeConfig*) noexcept;
// A diagnostic snapshot, NOT an atomic quiescence/unload guarantee.
int CheckpointPushBridgeSnapshot(unsigned slot, CheckpointPushBridgeStats*) noexcept;
std::uint64_t CheckpointPushBridge0(std::uint64_t, std::uint64_t, std::uint64_t, std::uint64_t);
std::uint64_t CheckpointPushBridge1(std::uint64_t, std::uint64_t, std::uint64_t, std::uint64_t);
}
