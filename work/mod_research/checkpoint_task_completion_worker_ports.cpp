#include "checkpoint_task_completion_worker_ports.h"
#include "checkpoint_task_native_ports_profile.h"
#include "checkpoint_task_completion_profile.h"
#include <cstring>
#include <new>
namespace checkpoint_task_completion_worker_ports {
namespace {
using checkpoint_task_native_ports::RunnerBytes;
using checkpoint_task_native_ports::LoadPrefixBytes;
static uintptr_t point(unsigned role,unsigned i){const uintptr_t p[]={0x834D98,role==0?0x508B40u:role==1?0x4DA390u:0x466600u,0x834D9B,0x834DB4};return p[i];}
struct Debug {DWORD64 v[6]{};};
struct Job {HANDLE target=nullptr;bool restore=false,attempted=false,changed=false,completed=false;uintptr_t base=0;unsigned role=0;Debug original{},observed{};Error error=Error::None;DWORD os=0;};
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
#ifndef CHECKPOINT_TASK_COMPLETION_FIXTURE
    if(m.Type!=MEM_IMAGE)return false;
#endif
    return m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY;
}
bool code(uintptr_t b,unsigned role) noexcept {__try{const auto*prefix=role==0?LoadPrefixBytes:role==1?checkpoint_task_completion::Title520PrefixBytes:checkpoint_task_completion::Title590PrefixBytes;const size_t size=role==0?sizeof LoadPrefixBytes:role==1?sizeof checkpoint_task_completion::Title520PrefixBytes:sizeof checkpoint_task_completion::Title590PrefixBytes;
    return b&&role<3&&b<UINTPTR_MAX-0x2200000&&page(b+0x834D10,sizeof RunnerBytes)&&page(b+point(role,1),size)&&!memcmp(reinterpret_cast<void*>(b+0x834D10),RunnerBytes,sizeof RunnerBytes)&&!memcmp(reinterpret_cast<void*>(b+point(role,1)),prefix,size);
}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
DWORD WINAPI jobMain(void*p){auto&j=*static_cast<Job*>(p);const auto prior=SuspendThread(j.target);if(prior==DWORD(-1)){j.error=Error::Suspend;j.os=GetLastError();j.completed=true;return 0;}
    if(prior)j.error=Error::Suspend;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}
    if(j.error==Error::None){j.observed=read(c);
        if(!j.restore){j.original=j.observed;if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xFFFF00FFull)||(c.Dr6&0xE00Full))j.error=Error::Occupied;
            else {c.Dr0=j.base+point(j.role,0);c.Dr1=j.base+point(j.role,1);c.Dr2=j.base+point(j.role,2);c.Dr3=j.base+point(j.role,3);c.Dr7|=0x55;}}
        else {const auto&d=j.original;
            if(c.Dr0!=j.base+point(j.role,0)||c.Dr1!=j.base+point(j.role,1)||c.Dr2!=j.base+point(j.role,2)||c.Dr3!=j.base+point(j.role,3)||(c.Dr7&~0x400ull)!=((d.v[5]|0x55)&~0x400ull))j.error=Error::Conflict;
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
    unsigned i=0;for(;i<4;++i)if(c.Rip==s->config.base+point(s->config.role,i))break;if(i==4)return EXCEPTION_CONTINUE_SEARCH;
    const auto d=read(c);for(unsigned n=0;n<4;++n)if(d.v[n]!=s->config.base+point(s->config.role,n))return EXCEPTION_CONTINUE_SEARCH;
    if((c.Dr7&~0x400ull)!=((s->arm.original.v[5]|0x55)&~0x400ull)||(c.Dr6&0xE00Full)!=(DWORD64(1)<<i))return EXCEPTION_CONTINUE_SEARCH;
    claimed=s;const DWORD flags=c.EFlags;c.EFlags|=0x10000;c.Dr6&=~(DWORD64(1)<<i);
    if(InterlockedCompareExchange(&s->inHandler,1,0)){fail(*s,Error::Order);return EXCEPTION_CONTINUE_EXECUTION;}
    try {
        bool dispatch=false;{Lock l(s->lock);auto&x=s->report.samples[i];
            if(s->report.captured!=i||x.rip){if(s->report.error==Error::None)s->report.error=Error::Order;}
            else {x.rip=c.Rip;x.thread=GetCurrentThreadId();x.rawFlags=flags;x.mxcsr=c.MxCsr;
                const std::uint64_t registers[]={c.Rax,c.Rcx,c.Rdx,c.Rbx,c.Rsp,c.Rbp,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15};
                memcpy(x.gpr,registers,sizeof registers);memcpy(x.xmm,&c.Xmm0,sizeof x.xmm);++s->report.captured;
                const bool bound=i==1?c.Rcx==s->report.callable:c.Rbx==s->report.control&&c.Rdi==s->report.threadObject&&(i!=0||c.Rcx==s->report.callable);
                if(!bound&&s->report.error==Error::None)s->report.error=Error::Binding;
                if(get(s->stopped)&&s->report.error==Error::None)s->report.error=Error::Stopped;
                dispatch=bound&&s->report.error==Error::None&&!get(s->stopped);}}
        if(dispatch){checkpoint_native_task_provider::Capture actual{c.Rip,c.Rcx,c.Rdx,c.Rbx,c.Rdi,c.Rsp,GetCurrentThreadId()};
            const bool ok=s->config.provider->Observe(actual);{Lock l(s->lock);auto&x=s->report.samples[i];x.delivered=true;x.accepted=ok;if(!ok&&s->report.error==Error::None)s->report.error=Error::Provider;}
            if(ok&&i==0)s->activeScope=true;if(ok&&i==2)s->activeScope=false;}
    }catch(...){InterlockedExchange(&s->inHandler,0);throw;}
    InterlockedExchange(&s->inHandler,0);return EXCEPTION_CONTINUE_EXECUTION;
}
LONG CALLBACK handler(EXCEPTION_POINTERS*ep){State*claimed=nullptr;__try{return body(ep,claimed);}__except(EXCEPTION_EXECUTE_HANDLER){if(!claimed)return EXCEPTION_CONTINUE_SEARCH;
    {AcquireSRWLockExclusive(&claimed->lock);claimed->report.error=Error::Exception;claimed->report.exceptionCode=GetExceptionCode();ReleaseSRWLockExclusive(&claimed->lock);}InterlockedExchange(&claimed->inHandler,0);return EXCEPTION_CONTINUE_EXECUTION;}}
}
bool Initialize(Context&out,const Config&c) noexcept {
    if(InterlockedCompareExchangePointer(&out.opaque,reserved,nullptr))return false;
    if(!c.provider||c.role>2||!c.generation||c.helperDeadlineMs<1||c.helperDeadlineMs>10000||!code(c.base,c.role))return false;
    checkpoint_native_task_provider::Report binding{};if(!c.provider->Snapshot(c.generation,binding)||!binding.registered||!binding.loadBound||!binding.roles[c.role].start||binding.roles[c.role].joined)return false;
    auto*s=new(std::nothrow)State;if(!s)return false;s->owner=&out;s->config=c;s->report.generation=c.generation;s->report.role=c.role;s->report.control=binding.roles[c.role].control;s->report.callable=binding.roles[c.role].callable;s->report.threadObject=binding.roles[c.role].threadObject;
    AcquireSRWLockExclusive(&registryLock);bool ok=false;
    if(contexts<64&&!runtimeFailed){if(!veh){HMODULE module=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&Initialize),&module))runtimeFailed=true;
            else {veh=AddVectoredExceptionHandler(1,handler);if(!veh)runtimeFailed=true;}}
        if(veh&&!runtimeFailed){s->report.modulePinned=true;s->next=registry;registry=s;++contexts;InterlockedExchangePointer(&out.opaque,s);ok=true;}}
    ReleaseSRWLockExclusive(&registryLock);if(!ok)delete s;return ok;
}
bool Begin(Context&h) noexcept {auto*s=find(h);if(!s||InterlockedCompareExchange(&s->used,1,0))return false;
    if(current||IsDebuggerPresent()){fail(*s,current?Error::Occupied:Error::Debugger);return false;}if(get(s->stopped)){fail(*s,Error::Stopped);return false;}
    checkpoint_native_task_provider::Report r{};if(!s->config.provider->Snapshot(s->config.generation,r)||r.roles[s->config.role].workerThread!=GetCurrentThreadId()||r.roles[s->config.role].control!=s->report.control||r.roles[s->config.role].callable!=s->report.callable||r.roles[s->config.role].invoke||!code(s->config.base,s->config.role)){fail(*s,Error::Binding);return false;}
    InterlockedExchange(&s->ownerThread,LONG(GetCurrentThreadId()));{Lock l(s->lock);s->report.thread=GetCurrentThreadId();}
    if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&s->target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)){fail(*s,Error::Helper,GetLastError());return false;}
    current=s;s->arm.target=s->target;s->arm.base=s->config.base;s->arm.role=s->config.role;const bool ok=job(*s,s->arm);s->needsRestore=s->arm.attempted;
    {Lock l(s->lock);memcpy(s->report.originalDr,s->arm.original.v,sizeof s->report.originalDr);s->report.entered=ok;}
    if(!ok)Finish(h);return ok;
}
void Finish(Context&h) noexcept {auto*s=find(h);if(!s)return;if(DWORD(get(s->ownerThread))!=GetCurrentThreadId()){fail(*s,Error::Thread);return;}
    {Lock l(s->lock);if(s->report.finished)return;}
    bool restored=!s->needsRestore;if(s->needsRestore){s->restore.target=s->target;s->restore.base=s->config.base;s->restore.role=s->config.role;s->restore.restore=true;s->restore.original=s->arm.original;restored=job(*s,s->restore);}
    if(s->activeScope){const bool abandoned=s->config.provider->Abnormal();s->activeScope=false;Lock l(s->lock);s->report.providerScopeAbandoned=abandoned?1:2;}
    bool clean=false;{Lock l(s->lock);s->report.finished=1;s->report.restored=restored;s->report.uncertain|=!restored;
        memcpy(s->report.restoredDr,s->needsRestore?s->restore.observed.v:s->arm.observed.v,sizeof s->report.restoredDr);s->report.codeUnchanged=code(s->config.base,s->config.role);
        if(s->report.entered&&s->report.captured!=4&&s->report.error==Error::None)s->report.error=Error::Missing;clean=restored&&!s->report.uncertain;}
    if(clean){if(current==s)current=nullptr;CloseHandle(s->target);s->target=nullptr;}
}
void Stop(Context&h) noexcept {auto*s=find(h);if(s){InterlockedExchange(&s->stopped,1);Lock l(s->lock);s->report.stopped=1;}}
bool Snapshot(const Context&h,Report&r) noexcept {auto*s=find(h);if(!s)return false;Lock l(s->lock);r=s->report;return true;}
}
