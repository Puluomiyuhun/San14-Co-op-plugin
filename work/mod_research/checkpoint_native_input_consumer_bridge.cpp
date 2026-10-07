#include "checkpoint_native_input_consumer_bridge.h"

namespace checkpoint_native_input_consumer {
namespace {
thread_local ScopedRoute* active_route = nullptr;
thread_local std::uint64_t unrouted_calls = 0;
bool SameBinding(const Binding& a, const Binding& b) noexcept {
    return a.attempt == b.attempt && a.attachment == b.attachment &&
           a.owner_generation == b.owner_generation;
}
struct OriginalGuard {
    bool& flag;
    explicit OriginalGuard(bool& value) noexcept : flag(value) { flag = true; }
    ~OriginalGuard() { flag = false; }
};
} // namespace

const char* StatusName(Status status) noexcept {
    switch (status) {
#define BRIDGE_STATUS(name) case Status::name: return #name;
        BRIDGE_STATUS(Ok)
        BRIDGE_STATUS(NotBound)
        BRIDGE_STATUS(AlreadyBound)
        BRIDGE_STATUS(InvalidTarget)
        BRIDGE_STATUS(WrongThread)
        BRIDGE_STATUS(StaleBinding)
        BRIDGE_STATUS(UnexpectedCache)
        BRIDGE_STATUS(InvalidMode)
        BRIDGE_STATUS(ReentrantCall)
        BRIDGE_STATUS(PublicationRejected)
        BRIDGE_STATUS(OriginalException)
#undef BRIDGE_STATUS
    }
    return "UnknownStatus";
}

Status MouseQueryBridge::Bind(const Binding& binding, Buffers buffers, MouseQuery target) noexcept {
    if (bound_) return Status::AlreadyBound;
    if (!target || target == &CheckpointNativeMouseQueryBridge || target == &InvokeRoutedMouseQuery)
        return Status::InvalidTarget;
    const auto status = adapter_.Bind(binding, buffers);
    if (status != checkpoint_native_input::Status::Ok) return Status::PublicationRejected;
    binding_ = binding;
    mouse_cache_ = buffers.mouse.data;
    target_ = target;
    owner_thread_ = std::this_thread::get_id();
    bound_ = true;
    return Status::Ok;
}

std::uint32_t MouseQueryBridge::Invoke(const Request& request, const void* mouse_cache,
                                      std::uint32_t button, Report& report) {
    report = Report{};
    if (!bound_) { report.status = Status::NotBound; return 0; }
    if (std::this_thread::get_id() != owner_thread_) {
        report.status = Status::WrongThread;
        return 0;
    }
    if (!SameBinding(binding_, request.binding)) {
        report.status = Status::StaleBinding;
        return 0;
    }
    if (mouse_cache != mouse_cache_) {
        report.status = Status::UnexpectedCache;
        return 0;
    }
    if (request.mode != Mode::NeutralizeThenForward && request.mode != Mode::ForwardUntouched) {
        report.status = Status::InvalidMode;
        return 0;
    }
    if (inside_original_) { report.status = Status::ReentrantCall; return 0; }
    if (request.mode == Mode::NeutralizeThenForward) {
        report.publication = adapter_.PublishNeutral(request.binding, request.publication_cycle);
        report.core_status = report.publication.status;
        if (report.core_status != checkpoint_native_input::Status::Ok) {
            report.status = Status::PublicationRejected;
            return 0;
        }
    }
    // The target sees exactly the incoming RCX/EDX. The neutralization itself is
    // complete before this call. There is no pump/update/worker suppression.
    OriginalGuard guard(inside_original_);
    report.forwarded_cache = mouse_cache;
    report.forwarded_button = button;
    report.original_started = true;
    try {
        const auto value = target_(mouse_cache, button);
        report.original_return = value;
        report.original_completed = true;
        report.status = Status::Ok;
        return value;
    } catch (...) {
        report.exception_rethrown = true;
        report.status = Status::OriginalException;
        throw;
    }
}

ScopedRoute::ScopedRoute(MouseQueryBridge& bridge, Request request) noexcept
    : bridge_(bridge), request_(request), previous_(active_route) {
    active_route = this;
}
ScopedRoute::~ScopedRoute() { active_route = previous_; }

std::uint64_t UnroutedCallCountForThisThread() noexcept { return unrouted_calls; }

std::uint32_t InvokeRoutedMouseQuery(const void* mouse_cache, std::uint32_t button) {
    if (!active_route) { ++unrouted_calls; return 0; }
    return active_route->bridge_.Invoke(active_route->request_, mouse_cache, button, active_route->report_);
}
} // namespace checkpoint_native_input_consumer

std::uint32_t CheckpointNativeMouseQueryBridge(
    const void* mouse_cache, std::uint32_t button) {
    return checkpoint_native_input_consumer::InvokeRoutedMouseQuery(mouse_cache, button);
}
