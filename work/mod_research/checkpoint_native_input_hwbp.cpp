#include "checkpoint_native_input_hwbp.h"
#include <cstring>
#include <new>
namespace checkpoint_native_input_hwbp {
namespace {
constexpr unsigned char block[]={0x48,0x8b,0x86,0x78,0x04,0,0,0x41,0x83,0xce,0xff,0x48,0x85,0xc0,0x74,0x11,0x44,0x8b,0xb0,0x88,0,0,0,0xc7,0x80,0x88,0,0,0,0xff,0xff,0xff,0xff};
struct DebugState {DWORD64 d[6]{};};
struct Job {
    HANDLE target=nullptr;
    bool restore=false,attempted=false,changed=false,completed=false;
    std::uintptr_t site=0;
    DebugState saved{},observed{};
    Error error=Error::None;DWORD os_error=0;
};
struct State {
    Config config{};HardwareReceipt report{};SRWLOCK lock=SRWLOCK_INIT;
    volatile LONG once=0,stop=0,owner=0,observing=0;
    Observe observer=nullptr;void* observer_context=nullptr;
    HANDLE target=nullptr;Job arm{},restore{};
    bool ready=false,route=false,needs_restore=false;
};
State* volatile installed=nullptr;
thread_local State* route=nullptr;
#ifdef CHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE
volatile LONG fixtureDelay=0;
#endif
LONG get(volatile LONG& v)noexcept{return InterlockedCompareExchange(&v,0,0);}
struct Lock{SRWLOCK* p;explicit Lock(SRWLOCK&v):p(&v){AcquireSRWLockExclusive(p);}~Lock(){ReleaseSRWLockExclusive(p);}};
void fail(State&s,Error e,DWORD os=0)noexcept{Lock l(s.lock);if(s.report.error==Error::None)s.report.error=e;if(os)s.report.os_error=os;}
bool same(const Binding&a,const Binding&b)noexcept{return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
bool identity(const Binding&b)noexcept{unsigned a=0,c=0;for(auto v:b.attempt)a|=v;for(auto v:b.attachment)c|=v;return a&&c&&b.owner_generation;}
DebugState read(const CONTEXT& c)noexcept{return{{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}};}
void write(CONTEXT&c,const DebugState&s)noexcept{c.Dr0=s.d[0];c.Dr1=s.d[1];c.Dr2=s.d[2];c.Dr3=s.d[3];c.Dr6=s.d[4];c.Dr7=s.d[5];}
bool sameDebug(const DebugState&a,const DebugState&b)noexcept{return !std::memcmp(a.d,b.d,sizeof a.d);}
bool bytes(std::uintptr_t p)noexcept{
    __try {MEMORY_BASIC_INFORMATION m{};return VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==MEM_IMAGE&&
        (m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY)&&p+sizeof block>=p&&p+sizeof block<=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize&&
        !std::memcmp(reinterpret_cast<void*>(p),block,sizeof block);}
    __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
// Helper owns no allocator/report lock while the calling thread is suspended.
// It only changes this one thread's debug registers, never code or other threads.
DWORD WINAPI jobMain(void* p){
    auto&j=*static_cast<Job*>(p);
#ifdef CHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE
    const auto delay=InterlockedExchange(&fixtureDelay,0);if(delay>0)Sleep(DWORD(delay));
#endif
    DWORD previous=SuspendThread(j.target);
    if(previous==DWORD(-1)){j.error=Error::Suspend;j.os_error=GetLastError();j.completed=true;return 0;}
    if(previous!=0)j.error=Error::Suspend;
    CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::Context;j.os_error=GetLastError();}
    if(j.error==Error::None){
        j.observed=read(c);
        if(!j.restore){
            j.saved=j.observed;
            if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xffff00ffull))j.error=Error::Occupied;
            else {c.Dr0=j.site;c.Dr7|=1;}
        }else {
            // RF/DR6 may change when our breakpoint fired. Other slots/controls
            // must still be exactly ours; never overwrite a foreign owner.
            const auto&o=j.saved;
            // CPU execution normalizes DR7's architecturally fixed-one bit 10;
            // it is not another debug owner's control. All enable/type/length
            // and remaining reserved bits still require exact equality.
            if(c.Dr0!=j.site||c.Dr1!=o.d[1]||c.Dr2!=o.d[2]||c.Dr3!=o.d[3]||(c.Dr7&~0x400ull)!=((o.d[5]|1)&~0x400ull))j.error=Error::RestoreConflict;
            else write(c,o);
        }
        if(j.error==Error::None){
            j.attempted=true;
            if(!SetThreadContext(j.target,&c)){j.error=j.restore?Error::Restore:Error::Publish;j.os_error=GetLastError();}
            else {
                j.changed=true;CONTEXT verify{};verify.ContextFlags=CONTEXT_DEBUG_REGISTERS;
                if(!GetThreadContext(j.target,&verify)){j.error=Error::Context;j.os_error=GetLastError();}
                else {j.observed=read(verify);if(!sameDebug(j.observed,read(c)))j.error=j.restore?Error::Restore:Error::Publish;}
            }
        }
    }
    if(ResumeThread(j.target)==DWORD(-1)){j.error=Error::Resume;j.os_error=GetLastError();}
    j.completed=true;return 0;
}
bool runJob(State&s,Job&j)noexcept{
    HANDLE h=CreateThread(nullptr,0,jobMain,&j,0,nullptr);
    if(!h){fail(s,Error::Helper,GetLastError());return false;}
    const auto wait=WaitForSingleObject(h,s.config.helper_deadline_ms);
    if(wait!=WAIT_OBJECT_0){
        {Lock l(s.lock);s.report.helper_deadline_exceeded=1;s.report.restore_uncertain=1;}
        fail(s,Error::Deadline,wait==WAIT_FAILED?GetLastError():0);
        // Retain module/State/job and join before the caller can leave this
        // native scope. The refusal deadline is NOT a hard cleanup deadline.
        // No TerminateThread, no dropping a late arm/restore operation.
        if(WaitForSingleObject(h,INFINITE)!=WAIT_OBJECT_0)return false;
    }
    CloseHandle(h);
    if(j.error!=Error::None)fail(s,j.error,j.os_error);
    return wait==WAIT_OBJECT_0&&j.completed&&j.error==Error::None;
}
LONG handlerBody(EXCEPTION_POINTERS* ep,State*& claimed){
    auto*s=route;
    if(!s||!ep||!ep->ExceptionRecord||!ep->ContextRecord||ep->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
    auto&c=*ep->ContextRecord;
    if(DWORD(get(s->owner))!=GetCurrentThreadId()||c.Rip!=s->config.site_rip||reinterpret_cast<std::uintptr_t>(ep->ExceptionRecord->ExceptionAddress)!=c.Rip||
       c.Dr0!=s->config.site_rip||(c.Dr7&0xf0003)!=1||!(c.Dr6&1)||(c.Dr6&0xe00e))return EXCEPTION_CONTINUE_SEARCH;
    claimed=s;
    // We consume only our own execute breakpoint. RF permits the unchanged
    // native instruction to execute; it clears automatically after execution.
    const auto rawFlags=c.EFlags;
    c.EFlags|=0x10000;c.Dr6&=~1ull;
    if(!s->route)return EXCEPTION_CONTINUE_EXECUTION;
    if(InterlockedCompareExchange(&s->observing,1,0)){fail(*s,Error::Repeated);return EXCEPTION_CONTINUE_EXECUTION;}
    try {
        bool accept=false;
        {Lock l(s->lock);
            if(s->report.captured){if(s->report.error==Error::None)s->report.error=Error::Repeated;}
            else {
                s->report.captured=1;s->report.capture_kind=CaptureKind::HardwareExecuteContext;
                const std::uint64_t regs[]={c.Rax,c.Rcx,c.Rdx,c.Rbx,c.Rsp,c.Rbp,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15};
                std::memcpy(s->report.gpr,regs,sizeof regs);s->report.rflags=rawFlags;
                std::memcpy(s->report.xmm,&c.Xmm0,sizeof s->report.xmm);s->report.mxcsr=c.MxCsr;
                if(c.Rsi!=s->report.user){if(s->report.error==Error::None)s->report.error=Error::WrongUser;}
                else if(c.Rsp&15){if(s->report.error==Error::None)s->report.error=Error::WrongStack;}
                else if(get(s->stop)){if(s->report.error==Error::None)s->report.error=Error::Stopped;}
                else accept=s->report.error==Error::None;
            }
        }
        if(accept){
            const auto r=s->observer(s->observer_context,s->config.binding,s->report.call_id,reinterpret_cast<void*>(c.Rsi));
            Lock l(s->lock);s->report.pending=r;++s->report.observer_calls;
        }
    }catch(...){InterlockedExchange(&s->observing,0);throw;}
    InterlockedExchange(&s->observing,0);
    return EXCEPTION_CONTINUE_EXECUTION;
}
LONG CALLBACK handler(EXCEPTION_POINTERS* ep){
    State*claimed=nullptr;
    __try{return handlerBody(ep,claimed);}
    __except(EXCEPTION_EXECUTE_HANDLER){
        auto*s=claimed;if(!s)return EXCEPTION_CONTINUE_SEARCH;
        AcquireSRWLockExclusive(&s->lock);s->report.error=Error::Observer;s->report.exception_code=GetExceptionCode();ReleaseSRWLockExclusive(&s->lock);
        InterlockedExchange(&s->observing,0);return EXCEPTION_CONTINUE_EXECUTION;
    }
}
}
bool Initialize(Context&out,const Config&c)noexcept{
    if(out.opaque||!identity(c.binding)||!c.site_rip||c.helper_deadline_ms<1||c.helper_deadline_ms>10000||!bytes(c.site_rip))return false;
    State*s=new(std::nothrow)State;if(!s)return false;s->config=c;s->report.binding=c.binding;s->report.site_rip=c.site_rip;
    if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(&installed),s,nullptr)){delete s;return false;}
    out.opaque=s;HMODULE module=nullptr;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&Initialize),&module)){fail(*s,Error::Handle,GetLastError());return false;}
    s->report.module_pinned=1;
    if(!AddVectoredExceptionHandler(1,handler)){fail(*s,Error::Handle,GetLastError());return false;}
    s->ready=true;
    return true;
}
bool Begin(Context&h,Observe observer,void* observer_context,const Binding&b,std::uint64_t call,const void*user)noexcept{
    auto*s=static_cast<State*>(h.opaque);if(!s||!s->ready)return false;
    if(InterlockedCompareExchange(&s->once,1,0)){fail(*s,Error::AlreadyUsed);return false;}
    if(!observer||!call||!user||!same(s->config.binding,b)){fail(*s,Error::Binding);return false;}
    if(route){fail(*s,Error::AlreadyUsed);return false;}
    if(IsDebuggerPresent()){fail(*s,Error::Debugger);return false;}
    if(get(s->stop)){fail(*s,Error::Stopped);return false;}
    if(!bytes(s->config.site_rip)){fail(*s,Error::Site);return false;}
    InterlockedExchange(&s->owner,LONG(GetCurrentThreadId()));
    {Lock l(s->lock);s->report.thread=GetCurrentThreadId();s->report.call_id=call;s->report.user=reinterpret_cast<std::uintptr_t>(user);}
    s->observer=observer;s->observer_context=observer_context;
    if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&s->target,THREAD_SUSPEND_RESUME|THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|SYNCHRONIZE,FALSE,0)){fail(*s,Error::Handle,GetLastError());return false;}
    s->route=true;route=s;s->arm.target=s->target;s->arm.site=s->config.site_rip;
    const bool ok=runJob(*s,s->arm);s->needs_restore=s->arm.attempted;
    {Lock l(s->lock);std::memcpy(s->report.original_dr,s->arm.saved.d,sizeof s->report.original_dr);s->report.entered=ok?1:0;}
    if(!ok){Finish(h);return false;}return true;
}
void Finish(Context&h)noexcept{
    auto*s=static_cast<State*>(h.opaque);if(!s)return;
    if(DWORD(get(s->owner))!=GetCurrentThreadId()){fail(*s,Error::WrongThread);return;}
    {Lock l(s->lock);if(s->report.finished)return;}
    bool restored=!s->needs_restore;
    if(s->needs_restore){s->restore.target=s->target;s->restore.site=s->config.site_rip;s->restore.restore=true;s->restore.saved=s->arm.saved;restored=runJob(*s,s->restore);}
    s->route=false;s->observer=nullptr;s->observer_context=nullptr;
    if(restored){route=nullptr;if(s->target){CloseHandle(s->target);s->target=nullptr;}}
    {Lock l(s->lock);
        s->report.restored=restored?1:0;s->report.finished=1;s->report.restore_uncertain|=!restored;
        std::memcpy(s->report.restored_dr,s->needs_restore?s->restore.observed.d:s->arm.observed.d,sizeof s->report.restored_dr);
        s->report.original_code_unchanged=bytes(s->config.site_rip);
        if(s->report.entered&&!s->report.captured&&s->report.error==Error::None)s->report.error=Error::MissingCapture;
    }
}
void Stop(Context&h)noexcept{auto*s=static_cast<State*>(h.opaque);if(s){InterlockedExchange(&s->stop,1);fail(*s,Error::Stopped);}}
bool Snapshot(const Context&h,HardwareReceipt&out)noexcept{auto*s=static_cast<State*>(h.opaque);if(!s)return false;Lock l(s->lock);out=s->report;return true;}
namespace {
bool begin(void*h,Observe o,void*p,const Binding&b,std::uint64_t c,const void*u)noexcept{return Begin(*static_cast<Context*>(h),o,p,b,c,u);}
void finish(void*h)noexcept{Finish(*static_cast<Context*>(h));}
bool snapshot(void*h,HardwareReceipt&r)noexcept{return Snapshot(*static_cast<Context*>(h),r);}
}
Provider MakeProvider(Context&c)noexcept{return{&c,begin,finish,snapshot};}
#ifdef CHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE
void FixtureHelperDelay(DWORD ms)noexcept{InterlockedExchange(&fixtureDelay,LONG(ms));}
#endif
}
