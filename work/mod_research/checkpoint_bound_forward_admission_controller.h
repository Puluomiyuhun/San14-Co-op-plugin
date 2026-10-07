#pragma once
#include "checkpoint_forward_native_session.h"
#include "checkpoint_bound_input_pending_adapter.h"
#include "checkpoint_native_input_hwbp.h"

// Caller-owned single-attachment, single-attempt composition. No creation-thread affinity.
// Each admission adapter is bound inside the actual callback, and no state is
// transferred to another thread within an in-flight call. Original always runs. This is not a
// game installer or complete input hold. A hardware-context provider must
// capture the exact native site inside original and prove DR restoration.
namespace checkpoint_bound_forward_admission {
namespace ns=checkpoint_forward_native_session;
namespace pd=checkpoint_bound_input_pending;
namespace hw=checkpoint_native_input_hwbp;
using Original=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
struct alignas(16) NativeCall {
    std::uint64_t args[4]{};
    std::uint64_t result_rax=0;
    Original original=nullptr;
    std::uint8_t result_xmm0[16]{};
};
static_assert(sizeof(NativeCall)==0x40&&offsetof(NativeCall,result_xmm0)==0x30);
enum class Event {Before,OriginalEnter,OriginalReturned,OriginalAbnormal,After,Authorize,QueueReturned,Commit,Bind,Close};
enum class Error {None,Config,Binding,Pair,Reentrant,Pending,Prefetch,Stopped,Queue,Commit,Bind,Abnormal};
struct Config {
    ns::Session* session=nullptr;
    pd::Config pending{};
    std::uint64_t attempt=0;
    Original original=nullptr;
    std::uintptr_t expected_prefetch_site=0;
    hw::Provider prefetch_provider{};
    // Performs the caller's already authorized native queue action and returns
    // the exact created menu's locally owned span. May throw: uncertain results
    // are terminal and are never retried or relabeled as successful.
    pd::Span (*queue)(void*)=nullptr;
    void* queue_context=nullptr;
    void(*next_before)(const CheckpointPushFrame*,void*) noexcept=nullptr;
    void(*next_after)(const CheckpointPushFrame*,void*) noexcept=nullptr;
    void* next_context=nullptr;
    void(*trace)(void*,Event) noexcept=nullptr;
    void* trace_context=nullptr;
};
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4324)
#endif
struct Report {
    Error error=Error::None;
    pd::Report before{},after{};
    hw::HardwareReceipt prefetch{};
    bool provider_begin=false,provider_snapshot=false;
    pd::Error begin=pd::Error::None,commit=pd::Error::None,close=pd::Error::None;
    unsigned original_calls=0,original_abnormal=0,after_calls=0,queue_calls=0,queue_returned=0;
    unsigned commit_succeeded=0,menu_bound=0,closed=0,reentry=0,scope_started=0,scope_finished=0;
    std::uint64_t native_rax=0;std::uint8_t native_xmm0[16]{};
    bool active=false,blocked=false,full_input_hold=false,game_hook_installed=false;
    DWORD initialized_thread=0,call_thread=0;
    unsigned ignored_before=0,ignored_original=0,ignored_after=0,callback_bindings=0;
    bool stopped=false,finished=false;
};
class Controller final {
public:
    bool Initialize(const Config&) noexcept;
    bool Snapshot(Report&)const noexcept; // Any thread: diagnostic copy only.
    void Stop() noexcept; // Closes new admission; never interrupts original or clears in-flight pairing.
    static void Before(const CheckpointPushFrame*,void*) noexcept;
    static void After(const CheckpointPushFrame*,void*) noexcept;
    static void UserAfter(void*,ns::Session&,const CheckpointPushFrame*) noexcept;
    // Invoked only by the ABI-preserving entry wrapper below. Owns Scope over
    // the entire native original, including exceptional unwind.
    void RunOriginal(NativeCall&);
private:
    static hw::PendingReport ObservePrefetch(void*,const hw::Binding&,std::uint64_t,const void*) noexcept;
    bool hardware_valid()const noexcept;
    void finish_provider() noexcept;
    void trace(Event) noexcept;
    void fail(Error) noexcept;
    void close(std::uint64_t) noexcept;
    bool pair(const CheckpointPushFrame&)const noexcept;
    Config config_{};pd::Adapter pending_{};Report report_{};CheckpointPushFrame frame_{};
    bool irrelevant(std::uint64_t)const noexcept;
    bool stopped()const noexcept;
    mutable SRWLOCK report_lock_=SRWLOCK_INIT;
    mutable volatile LONG initialized_=0,active_=0,running_=0,finished_=0,blocked_=0,stopped_=0,owner_thread_=0,queue_once_=0;
    std::uint64_t last_call_=0;
};
#ifdef _MSC_VER
#pragma warning(pop)
#endif
}
// One immutable pinned controller per module. Caller must keep it and originals
// alive. Four integer arguments only; full RAX and XMM0 result preserved.
extern "C" std::uint64_t CheckpointBoundForwardAdmissionOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CheckpointBoundForwardAdmissionCallOriginal(checkpoint_bound_forward_admission::NativeCall*);
extern "C" void CheckpointBoundForwardAdmissionRun(checkpoint_bound_forward_admission::NativeCall*);
