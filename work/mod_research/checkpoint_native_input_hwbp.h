#pragma once
#include "checkpoint_native_input_pending_adapter.h"

// One process-local, one-attempt observation. No code patch, native queue, load,
// process discovery, or input suppression. Initialize before publishing callbacks.
namespace checkpoint_native_input_hwbp {
using Binding=checkpoint_native_input::Binding;
using PendingReport=checkpoint_native_input_pending::Report;
enum class CaptureKind:unsigned {None,HardwareExecuteContext};
enum class Error:unsigned {None,Config,AlreadyInitialized,Binding,AlreadyUsed,WrongThread,Debugger,
    Site,Handle,Helper,Deadline,Suspend,Context,Occupied,Publish,RestoreConflict,Restore,Resume,
    WrongUser,WrongStack,Repeated,Observer,MissingCapture,Stopped};
using Observe=PendingReport(*)(void*,const Binding&,std::uint64_t,const void*) noexcept;
struct Config {
    Binding binding{};
    std::uintptr_t site_rip=0; // Exact 3F9DAF-equivalent 33-byte native block.
    DWORD helper_deadline_ms=1000; // Refusal deadline; cancellation/cleanup may wait longer.
};
struct HardwareReceipt {
    CaptureKind capture_kind=CaptureKind::None;
    Error error=Error::None;
    DWORD os_error=0,exception_code=0,thread=0;
    std::uint64_t call_id=0;
    std::uintptr_t site_rip=0,user=0;
    Binding binding{};
    PendingReport pending{};
    unsigned entered=0,captured=0,restored=0,finished=0,module_pinned=0;
    unsigned helper_deadline_exceeded=0,restore_uncertain=0,observer_calls=0;
    // This is the exception's native context, not a fabricated CALL frame.
    std::uint64_t gpr[16]{},rflags=0; // RAX..R15 as below; raw incoming exception EFlags, including RF.
    std::uint8_t xmm[256]{};
    DWORD mxcsr=0;
    std::uint64_t original_dr[6]{},restored_dr[6]{}; // DR0..3,DR6,DR7.
    bool original_code_unchanged=false,queue_authorized=false,full_input_hold=false;
};
struct Context {void* opaque=nullptr;}; // Pinned allocation; no destroy/unload during process lifetime.
bool Initialize(Context&,const Config&) noexcept;
bool Begin(Context&,Observe,void* observer_context,const Binding&,std::uint64_t call_id,const void* user) noexcept;
void Finish(Context&) noexcept; // Same actual thread; always call, also on original exception.
void Stop(Context&) noexcept; // No forced restoration under an active native call.
bool Snapshot(const Context&,HardwareReceipt&) noexcept;
// Controller integration may take this directly as its distinct hardware provider.
struct Provider {
    void* context=nullptr;
    bool(*begin)(void*,Observe,void*,const Binding&,std::uint64_t,const void*) noexcept=nullptr;
    void(*finish)(void*) noexcept=nullptr;
    bool(*snapshot)(void*,HardwareReceipt&) noexcept=nullptr;
};
Provider MakeProvider(Context&) noexcept;
#ifdef CHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE
void FixtureHelperDelay(DWORD) noexcept; // Own executable only; omitted in production object.
#endif
}
