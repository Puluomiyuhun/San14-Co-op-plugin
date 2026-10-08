#include "b_reload_root_worker_ports.h"
#include "b_reload_root_worker_profile.h"
#include "checkpoint_native_task_provider_worker.h"
#include <cstring>
#include <new>
namespace b_reload_root_worker_ports {
namespace {
using namespace b_reload_root_worker_profile;
static uintptr_t point(unsigned i){const uintptr_t p[]={0x50B730,0x834D9B,0x834DB4,0x50B690};return p[i];}
struct Debug {DWORD64 v[6]{};};
struct Job {HANDLE target=nullptr;bool restore=false,attempted=false,changed=false,completed=false;uintptr_t base=0;Debug original{},observed{};Error error=Error::None;DWORD os=0;};
struct State {Context* owner=nullptr;Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;State* next=nullptr;
    HANDLE target=nullptr;Job arm{},restore{};volatile LONG used=0,stopped=0,inHandler=0,ownerThread=0;bool needsRestore=false,activeScope=false;};
SRWLOCK registryLock=SRWLOCK_INIT;State* registry=nullptr;unsigned contexts=0;PVOID veh=nullptr;bool runtimeFailed=false;
thread_local State* current=nullptr;
void* const reserved=reinterpret_cast<void*>(1);
LONG get(volatile LONG&n){return InterlockedCompareExchange(&n,0,0);}
struct Lock {SRWLOCK* p;explicit Lock(SRWLOCK&l):p(&l){AcquireSRWLockExclusive(p);}~Lock(){ReleaseSRWLockExclusive(p);}};
State* find(const Context&c){auto*p=InterlockedCompareExchangePointer(&const_cast<Context&>(c).opaque,nullptr,nullptr);if(!p||p==reserved)return nullptr;AcquireSRWLockShared(&registryLock);State*r=nullptr;for(auto*s=registry;s;s=s->next)if(s==p&&s->owner==&c){r=s;break;}ReleaseSRWLockShared(&registryLock);return r;}
void fail(State&s,Error e,DWORD os=0){Lock l(s.lock);if(s.report.error==Error::None)s.report.error=e;if(os)s.report.osError=os;}
Debug read(const CONTEXT&c){return{{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}};}
void write(CONTEXT&c,const Debug&d){c.Dr0=d.v[0];c.Dr1=d.v[1];c.Dr2=d.v[2];c.Dr3=d.v[3];c.Dr6=d.v[4];c.Dr7=d.v[5];}
bool eq(const Debug&a,const Debug&b){return !memcmp(a.v,b.v,sizeof a.v);}
bool page(uintptr_t p,size_t n){MEMORY_BASIC_INFORMATION m{};if(p>UINTPTR_MAX-n||VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||p+n>uintptr_t(m.BaseAddress)+m.RegionSize)return false;
#ifndef B_RELOAD_ROOT_WORKER_FIXTURE
    if(m.Type!=MEM_IMAGE)return false;
#endif
    return m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY;
}
bool code(uintptr_t b) noexcept {__try{
 return b&&b<UINTPTR_MAX-0x2200000&&page(b+0x834D10,sizeof RunnerBytes)&&page(b+0x50B730,sizeof ThunkBytes)&&page(b+0x50B690,sizeof YieldBytes)&&
  !memcmp(reinterpret_cast<void*>(b+0x834D10),RunnerBytes,sizeof RunnerBytes)&&!memcmp(reinterpret_cast<void*>(b+0x50B730),ThunkBytes,sizeof ThunkBytes)&&!memcmp(reinterpret_cast<void*>(b+0x50B690),YieldBytes,sizeof YieldBytes);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
template<class T>T rd(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool pointers(const Config& c) noexcept {__try{
 if(!c.worker||c.worker>UINTPTR_MAX-0x80||!c.callable||c.callable>UINTPTR_MAX-0x28||!c.threadObject||c.threadObject>UINTPTR_MAX-0x20)return false;
 const auto state=rd<uintptr_t>(rd<uintptr_t>(rd<uintptr_t>(c.callable+8)));
 return state&&state<=UINTPTR_MAX-0x50&&rd<uintptr_t>(state+0x50)==c.worker&&rd<uintptr_t>(c.worker+8)==c.threadObject&&rd<uintptr_t>(c.worker+0x50)==c.callable&&
  rd<DWORD>(c.threadObject+0x10)==c.workerThread&&!rd<DWORD>(c.worker+0x58)&&!rd<DWORD>(c.worker+0x5c)&&
  rd<uintptr_t>(c.callable)==c.base+0x12F2440&&rd<uintptr_t>(c.base+0x12F2440+0x10)==c.base+0x50B730;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool binding(const Config& c){checkpoint_native_task_provider::Report r{};return c.provider->Snapshot(c.binding.generation,r)&&r.registered&&r.windowOpen&&!r.closed&&r.error==checkpoint_native_task_provider::Error::None&&r.generation==c.binding.generation&&r.attempt==c.binding.attempt&&r.epoch==c.binding.epoch;}
DWORD WINAPI jobMain(void*p){auto&j=*static_cast<Job*>(p);const auto prior=SuspendThread(j.target);if(prior==DWORD(-1)){j.error=Error::Suspend;j.os=GetLastError();j.completed=true;return 0;}
    if(prior)j.error=Error::Suspend;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}
    if(j.error==Error::None){j.observed=read(c);
        if(!j.restore){j.original=j.observed;if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xFFFF00FFull)||(c.Dr6&0xE00Full))j.error=Error::Occupied;
            else {c.Dr0=j.base+point(0);c.Dr1=j.base+point(1);c.Dr2=j.base+point(2);c.Dr3=j.base+point(3);c.Dr7|=0x55;}}
        else {const auto&d=j.original;
            if(c.Dr0!=j.base+point(0)||c.Dr1!=j.base+point(1)||c.Dr2!=j.base+point(2)||c.Dr3!=j.base+point(3)||(c.Dr7&~0x400ull)!=((d.v[5]|0x55)&~0x400ull)||(c.Dr6&0xE00Full)!=(d.v[4]&0xE00Full))j.error=Error::Conflict;
            else write(c,d);}
        if(j.error==Error::None){j.attempted=true;if(!SetThreadContext(j.target,&c)){j.error=j.restore?Error::Restore:Error::Publish;j.os=GetLastError();}
            else {j.changed=true;CONTEXT verify{};verify.ContextFlags=CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(j.target,&verify)){j.error=Error::Context;j.os=GetLastError();}
                else {j.observed=read(verify);if(!eq(j.observed,read(c)))j.error=j.restore?Error::Restore:Error::Publish;}}}}
    if(ResumeThread(j.target)==DWORD(-1)){j.error=Error::Resume;j.os=GetLastError();}j.completed=true;return 0;
}
bool job(State&s,Job&j){HANDLE h=CreateThread(nullptr,0,jobMain,&j,0,nullptr);if(!h){fail(s,Error::Helper,GetLastError());return false;}
    const auto wait=WaitForSingleObject(h,s.config.helperDeadlineMs);if(wait!=WAIT_OBJECT_0){{Lock l(s.lock);s.report.deadlineExceeded=s.report.uncertain=1;}fail(s,Error::Deadline,wait==WAIT_FAILED?GetLastError():0);
        // Deadline is admission refusal, never permission to discard a pending
        // SetThreadContext helper or unload its state. Cleanup may wait forever.
        if(WaitForSingleObject(h,INFINITE)!=WAIT_OBJECT_0)return false;}
    CloseHandle(h);if(j.error!=Error::None)fail(s,j.error,j.os);return wait==WAIT_OBJECT_0&&j.completed&&j.error==Error::None;
}
LONG body(EXCEPTION_POINTERS*ep,State*&claimed){auto*s=current;if(!s||!ep||!ep->ExceptionRecord||!ep->ContextRecord||ep->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
    auto&c=*ep->ContextRecord;if(DWORD(get(s->ownerThread))!=GetCurrentThreadId()||uintptr_t(ep->ExceptionRecord->ExceptionAddress)!=c.Rip)return EXCEPTION_CONTINUE_SEARCH;
    unsigned i=0;for(;i<4;++i)if(c.Rip==s->config.base+point(i))break;if(i==4)return EXCEPTION_CONTINUE_SEARCH;
    const auto d=read(c);for(unsigned n=0;n<4;++n)if(d.v[n]!=s->config.base+point(n))return EXCEPTION_CONTINUE_SEARCH;
    if((c.Dr7&~0x400ull)!=((s->arm.original.v[5]|0x55)&~0x400ull)||(c.Dr6&0xE00Full)!=(DWORD64(1)<<i))return EXCEPTION_CONTINUE_SEARCH;
    claimed=s;const DWORD flags=c.EFlags;c.EFlags|=0x10000;c.Dr6&=~(DWORD64(1)<<i);
    if(InterlockedCompareExchange(&s->inHandler,1,0)){fail(*s,Error::Order);return EXCEPTION_CONTINUE_EXECUTION;}
    try {
        bool dispatch=false;{Lock l(s->lock);auto&x=s->report.samples[i];++s->report.hits[i];
            const bool ordered=i==3?s->report.captured==1:s->report.captured==i&&!x.rip;
            if(!ordered){if(s->report.error==Error::None)s->report.error=Error::Order;}
            else {x={};x.rip=c.Rip;x.thread=GetCurrentThreadId();x.rawFlags=flags;x.mxcsr=c.MxCsr;
                const std::uint64_t registers[]={c.Rax,c.Rcx,c.Rdx,c.Rbx,c.Rsp,c.Rbp,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15};
                memcpy(x.gpr,registers,sizeof registers);memcpy(x.xmm,&c.Xmm0,sizeof x.xmm);if(i==3)++s->report.yields;else ++s->report.captured;
                const bool bound=i==3?c.Rcx==rd<uintptr_t>(rd<uintptr_t>(rd<uintptr_t>(s->config.callable+8))):c.Rbx==s->report.control&&c.Rdi==s->report.threadObject&&(i!=0||c.Rcx==s->report.callable);
                if(!bound&&s->report.error==Error::None)s->report.error=Error::Binding;
                if(get(s->stopped)&&s->report.error==Error::None)s->report.error=Error::Stopped;
                dispatch=bound&&s->report.error==Error::None&&!get(s->stopped);}}
        if(dispatch){checkpoint_native_task_provider::Capture actual{c.Rip,c.Rcx,c.Rdx,c.Rbx,c.Rdi,c.Rsp,GetCurrentThreadId()};
            const bool ok=checkpoint_native_task_provider_worker::ObserveExpected(*s->config.provider,s->config.binding,actual);{Lock l(s->lock);auto&x=s->report.samples[i];x.delivered=true;x.accepted=ok;if(ok)++s->report.accepted[i];else if(s->report.error==Error::None)s->report.error=Error::Provider;}
            if(ok&&i==0)s->activeScope=true;if(ok&&i==1)s->activeScope=false;}
    }catch(...){InterlockedExchange(&s->inHandler,0);throw;}
    InterlockedExchange(&s->inHandler,0);return EXCEPTION_CONTINUE_EXECUTION;
}
LONG CALLBACK handler(EXCEPTION_POINTERS*ep){State*claimed=nullptr;__try{return body(ep,claimed);}__except(EXCEPTION_EXECUTE_HANDLER){if(!claimed)return EXCEPTION_CONTINUE_SEARCH;
    {AcquireSRWLockExclusive(&claimed->lock);if(claimed->report.error==Error::None)claimed->report.error=Error::Exception;claimed->report.exceptionCode=GetExceptionCode();ReleaseSRWLockExclusive(&claimed->lock);}InterlockedExchange(&claimed->inHandler,0);return EXCEPTION_CONTINUE_EXECUTION;}}
}
bool Initialize(Context&out,const Config&c) noexcept {
    if(InterlockedCompareExchangePointer(&out.opaque,reserved,nullptr))return false;
    if(!c.provider||!c.binding.generation||!c.binding.attempt||!c.binding.epoch||!c.workerThread||c.helperDeadlineMs<1||c.helperDeadlineMs>10000||!code(c.base)||!binding(c)||!pointers(c))return false;
    auto*s=new(std::nothrow)State;if(!s)return false;s->owner=&out;s->config=c;s->report.generation=c.binding.generation;s->report.attempt=c.binding.attempt;s->report.epoch=c.binding.epoch;s->report.worker=c.worker;s->report.control=c.worker+8;s->report.callable=c.callable;s->report.threadObject=c.threadObject;
    AcquireSRWLockExclusive(&registryLock);bool ok=false;
    if(contexts<64&&!runtimeFailed){if(!veh){HMODULE module=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&Initialize),&module))runtimeFailed=true;
            else {veh=AddVectoredExceptionHandler(1,handler);if(!veh)runtimeFailed=true;}}
        if(veh&&!runtimeFailed){s->report.modulePinned=true;s->next=registry;registry=s;++contexts;InterlockedExchangePointer(&out.opaque,s);ok=true;}}
    ReleaseSRWLockExclusive(&registryLock);if(!ok)delete s;return ok;
}
bool Begin(Context&h) noexcept {auto*s=find(h);if(!s||InterlockedCompareExchange(&s->used,1,0))return false;
    if(current||IsDebuggerPresent()){fail(*s,current?Error::Occupied:Error::Debugger);return false;}if(get(s->stopped)){fail(*s,Error::Stopped);return false;}
    if(s->config.workerThread!=GetCurrentThreadId()||!binding(s->config)||!pointers(s->config)||!code(s->config.base)){fail(*s,Error::Binding);return false;}
    InterlockedExchange(&s->ownerThread,LONG(GetCurrentThreadId()));{Lock l(s->lock);s->report.thread=GetCurrentThreadId();}
    if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&s->target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)){fail(*s,Error::Helper,GetLastError());return false;}
    current=s;s->arm.target=s->target;s->arm.base=s->config.base;const bool ok=job(*s,s->arm);s->needsRestore=s->arm.attempted;
    {Lock l(s->lock);memcpy(s->report.originalDr,s->arm.original.v,sizeof s->report.originalDr);s->report.entered=ok;}
    if(!ok)Finish(h);return ok;
}
void Finish(Context&h) noexcept {auto*s=find(h);if(!s)return;if(DWORD(get(s->ownerThread))!=GetCurrentThreadId()){fail(*s,Error::Thread);return;}
    {Lock l(s->lock);if(s->report.finished)return;}
    bool restored=!s->needsRestore;if(s->needsRestore){s->restore.target=s->target;s->restore.base=s->config.base;s->restore.restore=true;s->restore.original=s->arm.original;restored=job(*s,s->restore);}
    if(s->activeScope){const bool abandoned=s->config.provider->Abnormal();s->activeScope=false;Lock l(s->lock);s->report.providerScopeAbandoned=abandoned?1:2;}
    bool clean=false;{Lock l(s->lock);s->report.finished=1;s->report.restored=restored;s->report.uncertain|=!restored;
        memcpy(s->report.restoredDr,s->needsRestore?s->restore.observed.v:s->arm.observed.v,sizeof s->report.restoredDr);s->report.codeUnchanged=code(s->config.base);
        if(!s->report.codeUnchanged&&s->report.error==Error::None)s->report.error=Error::Binding;
        if(s->report.entered&&s->report.captured!=3&&s->report.error==Error::None)s->report.error=Error::Missing;clean=restored&&!s->report.uncertain;}
    if(clean){if(current==s)current=nullptr;CloseHandle(s->target);s->target=nullptr;}
}
void Stop(Context&h) noexcept {auto*s=find(h);if(s){InterlockedExchange(&s->stopped,1);Lock l(s->lock);s->report.stopped=1;}}
bool Snapshot(const Context&h,Report&r) noexcept {auto*s=find(h);if(!s)return false;Lock l(s->lock);r=s->report;return true;}
}
