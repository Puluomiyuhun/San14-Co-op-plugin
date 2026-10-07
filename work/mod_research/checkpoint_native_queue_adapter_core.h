#pragma once
#include "checkpoint_bound_input_pending_adapter.h"
namespace checkpoint_native_queue_adapter {
namespace pd=checkpoint_bound_input_pending;
using Native=void(*)(void*,const char*,void*,void*);
enum class Stage:unsigned {New,Initialized,Authorized,Calling,Returned,Resolved,Rejected,Uncertain};
enum class Error:unsigned {None,Config,AlreadyInitialized,Identity,Profile,Memory,Controller,Ticket,Frame,Thread,Consumed,Stopped,Pending,Header,NativeException,NativeResult,Alias,Resolver,ExternalGuard};
enum class Point:unsigned {Initialize,Authorize,BeforeNative,AfterNative,Resolve};
struct Config {
    pd::Config pending{};
    const void* controller_identity=nullptr;
    std::uintptr_t cache=0;
    // Performs the integrator's fresh build/attachment/cache-ownership guard.
    // This is NOT private-ticket authentication, a scheduler lock or world proof.
    bool(*validate_external)(void*,Point) noexcept=nullptr;
    void* external_context=nullptr;
#ifdef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
    Native fixture_native=nullptr;
    std::uintptr_t fixture_user_caller=0;
#endif
};
struct Report {
    Stage stage=Stage::New;Error error=Error::None;
    DWORD exception=0,thread=0;
    std::uint64_t call_id=0,ticket_serial=0;
    std::uintptr_t controller=0,user=0,menu=0,queue=0;
    std::uint64_t queue_count=0,queue_capacity=0;
    unsigned authorized=0,native_calls=0,native_returned=0,native_result_verified=0,resolver_calls=0;
    bool stopped=false,may_have_queued=false,queue_capability_consumed=false;
    bool private_ticket_authenticated_by_adapter=false,world_ready=false;
};
class Adapter final {
public:
    bool Initialize(const Config&) noexcept;
    bool Authorize(const pd::Ticket&,const CheckpointPushFrame&,const void* controller) noexcept;
    pd::Span Queue(); // Native exceptions propagate; capability remains consumed.
    pd::Span Resolve(std::uintptr_t address,std::size_t bytes) noexcept;
    void Stop() noexcept; // Caller must invoke on aborted authorization/attempt retirement.
    bool Snapshot(Report&)const noexcept;
    static bool AuthorizeCallback(void*,const pd::Ticket&,const CheckpointPushFrame&,const void*) noexcept;
    static pd::Span QueueCallback(void*);
    static pd::Span ResolveCallback(void*,std::uintptr_t,std::size_t) noexcept;
private:
    bool external(Point) noexcept;
    bool profile()const noexcept;
    bool planning() noexcept;
    bool planningBody();
    bool returned() noexcept;
    bool returnedBody();
    void fail(Error,DWORD=0) noexcept;
    Config config_{};Report report_{};CheckpointPushFrame frame_{};pd::Ticket ticket_{};
    mutable SRWLOCK lock_=SRWLOCK_INIT;
    mutable volatile LONG initialized_=0,authorization_=0,queue_once_=0,resolver_once_=0,stopped_=0;
    std::uintptr_t old_queue_=0;std::uint64_t old_capacity_=0;
};
}
