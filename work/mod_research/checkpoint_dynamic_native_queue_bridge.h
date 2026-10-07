#pragma once
#include "checkpoint_native_queue_adapter_core.h"
#include "checkpoint_persistent_authorized_controller.h"
namespace checkpoint_dynamic_native_queue {
namespace qa=checkpoint_native_queue_adapter;
namespace ad=checkpoint_persistent_authorized;
namespace pd=checkpoint_bound_input_pending;
struct Options {
    ad::Controller* controller=nullptr;
    bool(*validate_external)(void*,qa::Point) noexcept=nullptr;
    void* external_context=nullptr;
#ifdef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
    qa::Native fixture_native=nullptr;
    uintptr_t fixture_user_caller=0;
#endif
};
struct Report {
    std::uint64_t generation=0;unsigned initialized=0;
    std::uint64_t route_rejections=0;
    qa::Report native{};
    bool production_admission=false,native_scheduler_fence=false;
};
// Per-generation wiring only. Frozen Adapter owns all capability, native queue,
// returned menu/span validation, exception and once-only resolver logic.
class Bridge {
public:
    // Consume once. Fills only pending resolver and authorize/queue/revoke
    // callbacks of a not-yet-initialized Controller Config, from that SAME
    // pending config. Caller retains bridge, controller and contexts until exit.
    bool Initialize(const Options&,ad::Config&) noexcept;
    void Stop() noexcept;
    const qa::Adapter& AdapterForValidation() const noexcept { return adapter_; }
    bool Snapshot(Report&) const noexcept;
    static bool Authorize(void*,const pd::Ticket&,const CheckpointPushFrame&,const void*) noexcept;
    static pd::Span Queue(void*);
    static pd::Span Resolve(void*,uintptr_t,std::size_t) noexcept;
    static void Revoke(void*) noexcept;
private:
    bool route(const CheckpointPushFrame* exact=nullptr,std::uint64_t call=0) noexcept;
    qa::Adapter adapter_{};std::uint64_t generation_=0;ad::Controller* controller_=nullptr;
    mutable volatile LONG once_=0;volatile LONG64 route_rejections_=0;
};
}
