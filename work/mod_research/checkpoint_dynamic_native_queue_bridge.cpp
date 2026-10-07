#include "checkpoint_dynamic_native_queue_bridge.h"
namespace checkpoint_dynamic_native_queue {
bool Bridge::Initialize(const Options& options,ad::Config& c) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    if(!options.controller||!options.validate_external||!c.generation||c.generation!=c.pending.binding.owner_generation||
       c.authorize_queue||c.queue||c.revoke_queue||c.pending.resolve_created_queue)return false;
    generation_=c.generation;controller_=options.controller;
    qa::Config q{};q.pending=c.pending;q.pending.resolve_created_queue=Resolve;q.pending.queue_resolver_context=this;
    q.controller_identity=controller_;q.cache=reinterpret_cast<uintptr_t>(c.pending.load_cache.data);
    q.validate_external=options.validate_external;q.external_context=options.external_context;
#ifdef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
    q.fixture_native=options.fixture_native;q.fixture_user_caller=options.fixture_user_caller;
#endif
    if(!adapter_.Initialize(q))return false;
    c.pending=q.pending;c.authorize_queue=Authorize;c.authorize_queue_context=this;
    c.queue=Queue;c.queue_context=this;c.revoke_queue=Revoke;c.revoke_queue_context=this;
    InterlockedExchange(&once_,2);return true;
}
bool Bridge::route(const CheckpointPushFrame* exact,std::uint64_t call) noexcept {
    checkpoint_persistent_logical_adapter::Mapping m{};
    const bool valid=InterlockedCompareExchange(&once_,0,0)==2&&
        checkpoint_persistent_logical_adapter::CurrentMapping(&m)&&m.generation==generation_&&m.physicalSlot==0&&m.logicalSlot==0&&
        m.stage==3&&m.thread==GetCurrentThreadId()&&(!exact||m.logicalFrame==exact)&&(!call||m.call==call);
    if(!valid){InterlockedIncrement64(&route_rejections_);adapter_.Stop();}return valid;
}
void Bridge::Stop() noexcept {adapter_.Stop();}
bool Bridge::Snapshot(Report& r)const noexcept {
    r={};if(InterlockedCompareExchange(&once_,0,0)!=2)return false;
    r.generation=generation_;r.initialized=1;
    r.route_rejections=InterlockedCompareExchange64(const_cast<volatile LONG64*>(&route_rejections_),0,0);
    return adapter_.Snapshot(r.native);
}
bool Bridge::Authorize(void* p,const pd::Ticket& ticket,const CheckpointPushFrame& frame,const void* controller) noexcept {
    auto& s=*static_cast<Bridge*>(p);if(!s.route(&frame,frame.call_id))return false;
    // Do not manufacture a boolean capability: the original private ticket,
    // actual frame and controller identity go directly to the frozen adapter.
    return s.adapter_.Authorize(ticket,frame,controller);
}
pd::Span Bridge::Queue(void* p){
    auto& s=*static_cast<Bridge*>(p);qa::Report r{};
    if(!s.adapter_.Snapshot(r)||!s.route(nullptr,r.call_id))return {};
    return s.adapter_.Queue();
}
pd::Span Bridge::Resolve(void* p,uintptr_t address,std::size_t bytes) noexcept {
    auto& s=*static_cast<Bridge*>(p);qa::Report r{};
    if(!s.adapter_.Snapshot(r)||!s.route(nullptr,r.call_id))return {};
    return s.adapter_.Resolve(address,bytes);
}
void Bridge::Revoke(void* p) noexcept {static_cast<Bridge*>(p)->Stop();}
}
