#pragma once
#include <cstddef>
#include <cstdint>

// Independent OS-loaded PE bridge, not an installer or raw-code trampoline.
// Win64 RCX/RDX/R8/R9 INTEGER args only; no stack or floating point arguments.
// Preserves original full RAX and XMM0 on normal return. BEFORE/AFTER exceptions
// propagate; FINALLY runs on normal and abnormal exits. Original is called once
// unless BEFORE itself throws. This interface never suppresses a native call.
// Module is pinned; config/original/context lifetime must last until exit.
struct alignas(16) CheckpointLoadWorkerFrame {
    std::uint64_t args[4];
    std::uint64_t result_rax, reserved_28;
    std::uint8_t result_xmm0[16];
    std::uint64_t caller_entry_rsp;
    std::uint32_t slot, thread_id;
    std::uint64_t call_id, reserved_58;
};
static_assert(sizeof(CheckpointLoadWorkerFrame)==0x60);
static_assert(offsetof(CheckpointLoadWorkerFrame,result_rax)==0x20);
static_assert(offsetof(CheckpointLoadWorkerFrame,result_xmm0)==0x30);
static_assert(offsetof(CheckpointLoadWorkerFrame,caller_entry_rsp)==0x40);
enum class CheckpointLoadWorkerStage:std::uint32_t { Before=1, Native=2, After=3, Done=4, Finally=5 };
struct CheckpointLoadWorkerExit {
    std::uint32_t abnormal, stage, claimed, depth;
    std::uint64_t token;
};
struct CheckpointLoadWorkerOwner {
    std::uint64_t token, call_id;
    std::uint32_t slot, thread_id, owner_depth, current_depth;
};
using CheckpointLoadWorkerObserver=void(*)(const CheckpointLoadWorkerFrame*,void*);
using CheckpointLoadWorkerFinally=void(*)(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
using CheckpointLoadWorkerEntry=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
struct CheckpointLoadWorkerBridgeConfig {
    std::uint32_t size=sizeof(CheckpointLoadWorkerBridgeConfig),version=1;
    void* original=nullptr;
    CheckpointLoadWorkerObserver before=nullptr,after=nullptr;
    CheckpointLoadWorkerFinally finally=nullptr;
    void* context=nullptr;
};
struct CheckpointLoadWorkerBridgeStats {
    std::uint64_t started,native_started,native_returned,before_calls,after_calls;
    std::uint64_t finally_calls,abnormal_exits,cleanup_faults,scope_claims,rejected_claims,active;
    std::uint32_t configured,module_pinned;
};
extern "C" {
int CheckpointLoadWorkerBridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int CheckpointLoadWorkerBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t CheckpointLoadWorkerBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointLoadWorkerBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
// Only BEFORE of this exact frame may claim nonzero token; any already owned
// ancestor rejects nested takeover. Native/AFTER/FINALLY cannot claim. Rejection
// does not skip original; caller must mark its own receipt incomplete as needed.
int CheckpointLoadWorkerClaim(const CheckpointLoadWorkerFrame*,std::uint64_t token) noexcept;
// Current thread only. Unclaimed nested read calls inherit the nearest owner.
// No process-wide exclusion, worker identity proof, or lifetime extension.
int CheckpointLoadWorkerCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
// FINALLY observes ownership before the bridge unconditionally restores its
// previous TLS scope. It must not throw. SEH/C++ violations are contained and
// counted cleanup_faults to preserve an in-flight original exception; zero faults
// is mandatory for a successful receipt. Internal TLS cleanup does not depend on
// this callback. No cleanup/unload/reset API is provided.
