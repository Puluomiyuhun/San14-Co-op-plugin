#pragma once
#include "checkpoint_bound_input_pending_adapter.h"
#include "checkpoint_native_input_hwbp.h"
#include "checkpoint_persistent_logical_adapter.h"

namespace checkpoint_persistent_authorized {
namespace pd=checkpoint_bound_input_pending;
namespace hw=checkpoint_native_input_hwbp;
using Original=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
struct alignas(16) NativeCall {
    std::uint64_t args[4]{};std::uint64_t result_rax=0;Original original=nullptr;std::uint8_t result_xmm0[16]{};
};
static_assert(sizeof(NativeCall)==0x40&&offsetof(NativeCall,result_xmm0)==0x30);
struct SessionStatus {bool admissionReady=false,stopped=false;LONG error=0;};
struct QueueReceipt {
    std::uint64_t attempt=0,userCall=0;DWORD thread=0;uintptr_t user=0,menu=0;bool nativeQueueReturned=false;
};
struct SessionPort {
    void* context=nullptr;
    bool(*status)(void*,SessionStatus&) noexcept=nullptr;
    bool(*bind_menu)(void*,const QueueReceipt&) noexcept=nullptr;
};
enum class Event {Before,OriginalEnter,OriginalReturned,OriginalAbnormal,After,Authorize,QueueReturned,Commit,Bind,Close};
enum class Error {None,Config,Binding,Pair,Reentrant,Pending,Prefetch,Stopped,Queue,Commit,Bind,Abnormal};
struct Config {
    SessionPort session{};pd::Config pending{};
    // generation is also pending.binding.owner_generation and logical route id.
    std::uint64_t generation=0,attempt=0;Original original=nullptr;
    std::uintptr_t expected_prefetch_site=0;hw::Provider prefetch_provider{};
    bool(*authorize_queue)(void*,const pd::Ticket&,const CheckpointPushFrame&,const void*) noexcept=nullptr;
    void* authorize_queue_context=nullptr;
    pd::Span(*queue)(void*)=nullptr;void* queue_context=nullptr;
    // Revoke must be idempotent and safe from any thread; closes only this
    // generation's queue capability. It never cancels an already queued menu.
    void(*revoke_queue)(void*) noexcept=nullptr;void* revoke_queue_context=nullptr;
    void(*next_before)(const CheckpointPushFrame*,void*) noexcept=nullptr;
    void(*next_after)(const CheckpointPushFrame*,void*) noexcept=nullptr;
    void(*next_finally)(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept=nullptr;
    void* next_context=nullptr;
    void(*trace)(void*,Event) noexcept=nullptr;void* trace_context=nullptr;
};
#pragma warning(push)
#pragma warning(disable:4324)
struct Report {
    Error error=Error::None;pd::Report before{},after{};hw::HardwareReceipt prefetch{};
    bool provider_begin=false,provider_snapshot=false;
    pd::Error begin=pd::Error::None,commit=pd::Error::None,close=pd::Error::None;
    unsigned original_calls=0,original_abnormal=0,after_calls=0,queue_calls=0,queue_returned=0;
    unsigned commit_succeeded=0,menu_bound=0,closed=0,reentry=0,scope_started=0,scope_finished=0;
    unsigned queue_authorize_calls=0,queue_authorized=0;
    std::uint64_t native_rax=0;std::uint8_t native_xmm0[16]{};
    bool active=false,blocked=false,full_input_hold=false,game_hook_installed=false;
    DWORD initialized_thread=0,call_thread=0;
    unsigned ignored_before=0,ignored_original=0,ignored_after=0,callback_bindings=0;
    bool stopped=false,finished=false;
    std::uint64_t generation=0,route_started=0,route_finished=0,route_original=0,route_abnormal=0;
    unsigned route_faults=0,route_active=0,ignored_finally=0,abandoned_after=0;
    bool offline_activation=false,production_admission=false,native_scheduler_fence=false;
};
struct ForwardReport {std::uint64_t unowned_forwards=0;bool configured=false,pinned=false,production_admission=false;};
class Controller final {
public:
    bool Initialize(const Config&) noexcept;
    bool Snapshot(Report&)const noexcept;
    bool ActivateForOfflineExercise() noexcept; // Always false in production object.
    void Stop() noexcept;
    static void RoutedBefore(const CheckpointPushFrame*,void*) noexcept;
    static void RoutedAfter(const CheckpointPushFrame*,void*) noexcept;
    static void RoutedFinally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
    // Invoke from Session.userAfter after RoutedAfter and before RoutedFinally.
    void SubmitUserAfter(const CheckpointPushFrame*) noexcept;
private:
    friend void RunSelected(NativeCall*);
    void RunOriginal(NativeCall&);
    static void Before(const CheckpointPushFrame*,void*) noexcept;
    static void After(const CheckpointPushFrame*,void*) noexcept;
    static hw::PendingReport ObservePrefetch(void*,const hw::Binding&,std::uint64_t,const void*) noexcept;
    bool hardware_valid()const noexcept;void finish_provider() noexcept;void trace(Event) noexcept;
    void fail(Error) noexcept;void close(std::uint64_t) noexcept;bool pair(const CheckpointPushFrame&)const noexcept;
    bool irrelevant(std::uint64_t)const noexcept;bool stopped()const noexcept;
    Config config_{};pd::Adapter pending_{};Report report_{};CheckpointPushFrame frame_{};
    mutable SRWLOCK report_lock_=SRWLOCK_INIT;
    mutable volatile LONG initialized_=0,active_=0,running_=0,finished_=0,blocked_=0,stopped_=0,owner_thread_=0,queue_once_=0;
    mutable volatile LONG offline_=0;std::uint64_t last_call_=0;
};
#pragma warning(pop)
// One immutable original target per physical wrapper; never a global controller.
// Configure outside DllMain before publishing the wrapper. No reset or unload.
bool ConfigureForwardOriginal(Original) noexcept;
void SnapshotForward(ForwardReport&) noexcept;
}
extern "C" std::uint64_t CheckpointPersistentAuthorizedOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CheckpointPersistentAuthorizedCallOriginal(checkpoint_persistent_authorized::NativeCall*);
extern "C" void CheckpointPersistentAuthorizedRun(checkpoint_persistent_authorized::NativeCall*);
