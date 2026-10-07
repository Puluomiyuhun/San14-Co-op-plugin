#pragma once
#include "checkpoint_guest_native_session.h"
#include "checkpoint_native_input_prefetch_bridge.h"

// Caller-owned single-attachment, single-attempt composition. This is not a
// game installer or complete input hold. The separately installed mid-function
// observer must really run inside original; its absence denies admission.
namespace checkpoint_session_input_admission {
namespace ns=checkpoint_guest_native_session;
namespace pd=checkpoint_native_input_pending;
namespace pf=checkpoint_native_input_prefetch;
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
    std::uintptr_t expected_prefetch_return=0;
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
    pf::Report prefetch{};
    pd::Error begin=pd::Error::None,commit=pd::Error::None,close=pd::Error::None;
    unsigned original_calls=0,original_abnormal=0,after_calls=0,queue_calls=0,queue_returned=0;
    unsigned commit_succeeded=0,menu_bound=0,closed=0,reentry=0,scope_started=0,scope_finished=0;
    std::uint64_t native_rax=0;std::uint8_t native_xmm0[16]{};
    bool active=false,blocked=false,full_input_hold=false,game_hook_installed=false;
};
class Controller final {
public:
    bool Initialize(const Config&) noexcept;
    bool Snapshot(Report&)const noexcept; // Owner thread only.
    static void Before(const CheckpointPushFrame*,void*) noexcept;
    static void After(const CheckpointPushFrame*,void*) noexcept;
    static void UserAfter(void*,ns::Session&,const CheckpointPushFrame*) noexcept;
    // Invoked only by the ABI-preserving entry wrapper below. Owns Scope over
    // the entire native original, including exceptional unwind.
    void RunOriginal(NativeCall&);
private:
    void trace(Event) noexcept;
    void fail(Error) noexcept;
    void close(std::uint64_t) noexcept;
    bool pair(const CheckpointPushFrame&)const noexcept;
    Config config_{};pd::Adapter pending_{};Report report_{};CheckpointPushFrame frame_{};
    DWORD thread_=0;bool initialized_=false,active_=false,running_=false,finished_=false;
    volatile LONG blocked_=0;
};
#ifdef _MSC_VER
#pragma warning(pop)
#endif
}
// One immutable pinned controller per module. Caller must keep it and originals
// alive. Four integer arguments only; full RAX and XMM0 result preserved.
extern "C" std::uint64_t CheckpointSessionInputAdmissionOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CheckpointSessionInputAdmissionCallOriginal(checkpoint_session_input_admission::NativeCall*);
extern "C" void CheckpointSessionInputAdmissionRun(checkpoint_session_input_admission::NativeCall*);
