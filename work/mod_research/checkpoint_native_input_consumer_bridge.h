#pragma once
#include "checkpoint_native_input_core.h"

#include <cstdint>
#include <thread>

namespace checkpoint_native_input_consumer {
using checkpoint_native_input::Binding;
using checkpoint_native_input::Buffers;
using checkpoint_native_input::Publication;

// Verified specifically for 3A2920 and its EAX-testing callers. Do not replace
// this with bool: an AL-only return can leave a nonzero upper EAX at the caller.
using MouseQuery = std::uint32_t (*)(const void* mouse_cache, std::uint32_t button);
enum class Mode { ForwardUntouched, NeutralizeThenForward };
enum class Status {
    Ok, NotBound, AlreadyBound, InvalidTarget, WrongThread, StaleBinding,
    UnexpectedCache, InvalidMode, ReentrantCall, PublicationRejected, OriginalException,
};
const char* StatusName(Status status) noexcept;

struct Request {
    Binding binding;
    std::uint64_t publication_cycle = 0;
    Mode mode = Mode::NeutralizeThenForward;
};
struct Report {
    Status status = Status::NotBound;
    checkpoint_native_input::Status core_status = checkpoint_native_input::Status::NotBound;
    Publication publication{};
    const void* forwarded_cache = nullptr;
    std::uint32_t forwarded_button = 0;
    std::uint32_t original_return = 0;
    bool original_started = false;
    bool original_completed = false;
    bool exception_rethrown = false;
    bool native_hook_installed = false;
    bool complete_native_input_hold = false;
};

class MouseQueryBridge final {
public:
    MouseQueryBridge() = default;
    MouseQueryBridge(const MouseQueryBridge&) = delete;
    MouseQueryBridge& operator=(const MouseQueryBridge&) = delete;

    // The caller supplies an owned, lifetime-stable target with the verified
    // signature. No address discovery, detour installation, or pointer patching.
    Status Bind(const Binding& binding, Buffers buffers, MouseQuery target) noexcept;

    // Failure before the target returns 0 with an explicit report and invokes no
    // original consumer. On success, exact original arguments, uint32 return,
    // and C++ exception identity are preserved after the optional cache write.
    // SEH and arbitrary native unwind metadata are outside this fixture proof.
    std::uint32_t Invoke(const Request& request, const void* mouse_cache,
                         std::uint32_t button, Report& report);

private:
    checkpoint_native_input::Adapter adapter_;
    Binding binding_{};
    const void* mouse_cache_ = nullptr;
    MouseQuery target_ = nullptr;
    std::thread::id owner_thread_{};
    bool bound_ = false;
    bool inside_original_ = false;
};

// Caller-controlled route for an exact two-register Windows x64 entry point.
// A future hook must establish a valid same-thread route and verified owner
// boundary first. This entry is NOT safe to install as a global detour as-is:
// absent routes fail closed to 0 and cannot automatically find an original.
class ScopedRoute final {
public:
    ScopedRoute(MouseQueryBridge& bridge, Request request) noexcept;
    ~ScopedRoute();
    ScopedRoute(const ScopedRoute&) = delete;
    ScopedRoute& operator=(const ScopedRoute&) = delete;
    const Report& report() const noexcept { return report_; }

private:
    friend std::uint32_t InvokeRoutedMouseQuery(const void*, std::uint32_t);
    MouseQueryBridge& bridge_;
    Request request_;
    Report report_{};
    ScopedRoute* previous_;
};
std::uint64_t UnroutedCallCountForThisThread() noexcept;
std::uint32_t InvokeRoutedMouseQuery(const void* mouse_cache, std::uint32_t button);
} // namespace checkpoint_native_input_consumer

// Exactly the audited RCX/EDX -> EAX machine ABI. C++ linkage is intentional:
// MSVC /EHsc can assume extern-C calls do not throw and omit route unwinding.
// Its lifetime/routing must be owned by the caller. No global hook is installed.
std::uint32_t CheckpointNativeMouseQueryBridge(
    const void* mouse_cache, std::uint32_t button);
