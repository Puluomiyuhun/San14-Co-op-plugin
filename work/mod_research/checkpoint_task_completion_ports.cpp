#include "checkpoint_task_completion_ports.h"
#include "checkpoint_task_completion_profile.h"
#include <cstring>
#include <new>
namespace checkpoint_task_completion {
namespace {
constexpr uintptr_t points[]={0x4F7079,0x4AAF64,0x4AAF89};
struct Debug {DWORD64 v[6]{};};
struct Job {HANDLE target=nullptr;uintptr_t base=0;bool title=false,restore=false,attempted=false,completed=false;Debug original{},observed{};Error error=Error::None;DWORD os=0;};
struct State;
struct Scope {State* state=nullptr;unsigned index=0;HANDLE target=nullptr;Job arm{},restore{};bool needsRestore=false;};
struct State {Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG stopped=0,busy=0;Scope scopes[64]{};};
thread_local Scope* current=nullptr;SRWLOCK globalLock=SRWLOCK_INIT;State* retained[2]{};unsigned retainedCount=0;PVOID veh=nullptr;uintptr_t titleBase=0;
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
void fail(State&s,Error e,DWORD os=0){AcquireSRWLockExclusive(&s.lock);if(s.report.error==Error::None)s.report.error=e;if(current&&current->state==&s){auto&r=s.report.scopes[current->index];if(r.error==Error::None)r.error=e;r.osError=os;}ReleaseSRWLockExclusive(&s.lock);}
bool code(uintptr_t b) noexcept {__try {if(!b||b>UINTPTR_MAX-0x2200000)return false;
    for(unsigned i=0;i<2;++i){const auto p=b+(i?0x4AA7B0:0x4F7050);const auto n=i?sizeof TitleUpdateBytes:sizeof LoadJoinBytes;MEMORY_BASIC_INFORMATION m{};
        if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.BaseAddress)+m.RegionSize<p+n||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef CHECKPOINT_TASK_COMPLETION_FIXTURE
        if(m.Type!=MEM_IMAGE)return false;
#endif
        if(memcmp(reinterpret_cast<void*>(p),i?TitleUpdateBytes:LoadJoinBytes,n))return false;
    }return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
Debug read(const CONTEXT&c){return{{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}};}
void write(CONTEXT&c,const Debug&v){c.Dr0=v.v[0];c.Dr1=v.v[1];c.Dr2=v.v[2];c.Dr3=v.v[3];c.Dr6=v.v[4];c.Dr7=v.v[5];}
Debug armed(const Job&j){Debug d=j.original;d.v[0]=j.base+points[j.title?1:0];d.v[1]=j.title?j.base+points[2]:0;d.v[2]=d.v[3]=0;d.v[5]|=j.title?5:1;return d;}
bool sameLayout(const Debug&a,const Debug&b){return a.v[0]==b.v[0]&&a.v[1]==b.v[1]&&a.v[2]==b.v[2]&&a.v[3]==b.v[3]&&(a.v[5]&~0x400ull)==(b.v[5]&~0x400ull);}
DWORD WINAPI helper(void*p){auto&j=*static_cast<Job*>(p);const auto prior=SuspendThread(j.target);if(prior==DWORD(-1)){j.error=Error::Helper;j.os=GetLastError();j.completed=true;return 0;}
    if(prior)j.error=Error::Helper;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}
    if(j.error==Error::None){j.observed=read(c);if(!j.restore){j.original=j.observed;if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xFFFF00FFull)||(c.Dr6&0xE00Full))j.error=Error::Occupied;else write(c,armed(j));}
        else if(!sameLayout(j.observed,armed(j)))j.error=Error::Restore;else write(c,j.original);
        if(j.error==Error::None){j.attempted=true;if(!SetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}else {CONTEXT v{};v.ContextFlags=CONTEXT_DEBUG_REGISTERS;
            if(!GetThreadContext(j.target,&v)){j.error=Error::Context;j.os=GetLastError();}else {j.observed=read(v);auto expected=read(c);if(memcmp(expected.v,j.observed.v,sizeof expected.v))j.error=Error::Context;}}}}
    if(ResumeThread(j.target)==DWORD(-1)){j.error=Error::Restore;j.os=GetLastError();}j.completed=true;return 0;}
bool run(Scope&q,Job&j){auto&s=*q.state;HANDLE h=CreateThread(nullptr,0,helper,&j,0,nullptr);if(!h){fail(s,Error::Helper,GetLastError());return false;}const auto waited=WaitForSingleObject(h,s.config.helperDeadlineMs);
    if(waited!=WAIT_OBJECT_0){fail(s,Error::Deadline);AcquireSRWLockExclusive(&s.lock);s.report.scopes[q.index].uncertain=1;ReleaseSRWLockExclusive(&s.lock);if(WaitForSingleObject(h,INFINITE)!=WAIT_OBJECT_0)return false;}
    CloseHandle(h);if(j.error!=Error::None)fail(s,j.error,j.os);return waited==WAIT_OBJECT_0&&j.completed&&j.error==Error::None;}
bool candidate(State&s,uintptr_t owner,uintptr_t rsp,DWORD thread,bool title) noexcept {__try {
    checkpoint_native_task_provider::Report p{};if(thread!=GetCurrentThreadId()||!s.config.provider->Snapshot(s.config.generation,p)||!p.registered||!p.windowOpen||p.closed||p.error!=checkpoint_native_task_provider::Error::None||!p.loadBound)return false;
    uintptr_t caller=s.config.base+0x50B785;
#ifdef CHECKPOINT_TASK_COMPLETION_FIXTURE
    const auto fixture=title?s.config.fixtureTitleCaller:s.config.fixtureLoadCaller;if(fixture)caller=fixture;
#endif
    if(at<uintptr_t>(rsp)!=caller||owner!=(title?p.title:p.load))return false;
    const auto b=s.config.base,m=b+0x19E7310,n=at<std::uint64_t>(m+0x10),stack=at<uintptr_t>(m+0x20);
    if(at<uintptr_t>(m+0x48)!=owner||at<uintptr_t>(owner)!=b+(title?0x12DAAF0:0x12DBD68))return false;
    const auto phase=at<DWORD>(owner+0x470);
    if(title)return p.titleCallback&&p.roles[1].start&&!p.roles[2].joined&&(phase==15||phase==16)&&(n==3||n==4)&&at<uintptr_t>(stack+16)==owner;
    return p.roles[0].start&&!p.roles[0].joined&&phase==2&&n==4&&at<uintptr_t>(stack+24)==owner;
}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void capture(Scope&q,CONTEXT&c,unsigned role,DWORD flags){auto&s=*q.state;Sample sample{};sample.call=s.report.scopes[q.index].call;sample.rip=c.Rip;sample.thread=GetCurrentThreadId();sample.rawFlags=flags;sample.mxcsr=c.MxCsr;sample.role=role;
    const std::uint64_t regs[]={c.Rax,c.Rcx,c.Rdx,c.Rbx,c.Rsp,c.Rbp,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15};memcpy(sample.gpr,regs,sizeof regs);memcpy(sample.xmm,&c.Xmm0,sizeof sample.xmm);
    AcquireSRWLockShared(&s.lock);const bool eligible=s.report.error==Error::None&&s.report.scopes[q.index].error==Error::None&&!s.report.scopes[q.index].uncertain;ReleaseSRWLockShared(&s.lock);
    if(!eligible)return; // a completed helper after its deadline is not admission
    checkpoint_native_task_provider::Report p{};if(get(s.stopped)||!s.config.provider->Snapshot(s.config.generation,p)||p.error!=checkpoint_native_task_provider::Error::None||!p.roles[role].start||!p.roles[role].returned||!p.roles[role].done||p.roles[role].joined){fail(s,get(s.stopped)?Error::Stopped:Error::Order);return;}
    sample.creation=p.roles[role].creation;const checkpoint_native_task_provider::Capture actual{c.Rip,c.Rcx,c.Rdx,c.Rbx,c.Rdi,c.Rsp,GetCurrentThreadId()};sample.accepted=s.config.provider->Observe(actual);
    AcquireSRWLockExclusive(&s.lock);s.report.joins[role]=sample;s.report.accepted[role]+=sample.accepted;++s.report.scopes[q.index].hits;if(!sample.accepted){if(s.report.error==Error::None)s.report.error=Error::Provider;s.report.scopes[q.index].error=Error::Provider;}ReleaseSRWLockExclusive(&s.lock);
}
LONG body(EXCEPTION_POINTERS*ep,Scope*&claimed){auto*q=current;if(!q||!ep||!ep->ExceptionRecord||!ep->ContextRecord||ep->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
    auto&c=*ep->ContextRecord;auto&s=*q->state;const bool title=q->arm.title;unsigned slot=0,role=title?1:0;if(c.Rip!=s.config.base+points[role]){if(!title||c.Rip!=s.config.base+points[2])return EXCEPTION_CONTINUE_SEARCH;slot=1;role=2;}
    if(uintptr_t(ep->ExceptionRecord->ExceptionAddress)!=c.Rip||GetCurrentThreadId()!=s.report.scopes[q->index].thread||!sameLayout(read(c),armed(q->arm))||(c.Dr6&0xE00Full)!=(DWORD64(1)<<slot))return EXCEPTION_CONTINUE_SEARCH;
    claimed=q;const auto flags=c.EFlags;c.EFlags|=0x10000;c.Dr6&=~(DWORD64(1)<<slot);capture(*q,c,role,flags);return EXCEPTION_CONTINUE_EXECUTION;
}
LONG CALLBACK handler(EXCEPTION_POINTERS*ep){Scope*claimed=nullptr;__try{return body(ep,claimed);}__except(EXCEPTION_EXECUTE_HANDLER){if(!claimed)return EXCEPTION_CONTINUE_SEARCH;fail(*claimed->state,Error::Exception,GetExceptionCode());return EXCEPTION_CONTINUE_EXECUTION;}}
void begin(State&s,std::uint64_t call,uintptr_t owner,bool title){if(current||IsDebuggerPresent()||get(s.stopped)||!code(s.config.base)){fail(s,Error::Binding);return;}if(InterlockedCompareExchange(&s.busy,1,0)){fail(s,Error::Occupied);return;}
    AcquireSRWLockExclusive(&s.lock);if(s.report.scopeCount>=64){if(s.report.error==Error::None)s.report.error=Error::Capacity;ReleaseSRWLockExclusive(&s.lock);InterlockedExchange(&s.busy,0);return;}
    const auto i=s.report.scopeCount++;auto&q=s.scopes[i];q.state=&s;q.index=i;auto&r=s.report.scopes[i];r.call=call;r.owner=owner;r.title=title;r.thread=GetCurrentThreadId();s.report.active=1;ReleaseSRWLockExclusive(&s.lock);current=&q;
    if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&q.target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)){fail(s,Error::Helper,GetLastError());return;}
    q.arm.target=q.target;q.arm.base=s.config.base;q.arm.title=title;const bool ok=run(q,q.arm);q.needsRestore=q.arm.attempted;
    AcquireSRWLockExclusive(&s.lock);r.armed=ok;memcpy(r.originalDr,q.arm.original.v,sizeof r.originalDr);ReleaseSRWLockExclusive(&s.lock);
}
void finish(Scope&q,const CheckpointLoadWorkerExit&x){auto&s=*q.state;bool ok=!q.needsRestore;if(q.needsRestore){q.restore.target=q.target;q.restore.base=s.config.base;q.restore.title=q.arm.title;q.restore.restore=true;q.restore.original=q.arm.original;ok=run(q,q.restore);}
    AcquireSRWLockExclusive(&s.lock);auto&r=s.report.scopes[q.index];r.finally=1;r.abnormal=x.abnormal;r.restored=ok;r.uncertain|=!ok;memcpy(r.restoredDr,q.needsRestore?q.restore.observed.v:q.arm.observed.v,sizeof r.restoredDr);++s.report.completedScopes;s.report.active=0;const bool clear=ok&&!r.uncertain;ReleaseSRWLockExclusive(&s.lock);
    if(clear){current=nullptr;if(q.target){CloseHandle(q.target);q.target=nullptr;}InterlockedExchange(&s.busy,0);} // otherwise retained TLS tombstone rejects future capture
}
void titleBefore(const CheckpointLoadWorkerFrame*f,void*){if(!f)return;State*selected=nullptr;AcquireSRWLockShared(&globalLock);for(unsigned i=0;i<retainedCount;++i)if(candidate(*retained[i],f->args[0],f->caller_entry_rsp,f->thread_id,true)){if(selected){fail(*selected,Error::Binding);selected=nullptr;break;}selected=retained[i];}ReleaseSRWLockShared(&globalLock);if(selected)begin(*selected,f->call_id,f->args[0],true);}
void titleAfter(const CheckpointLoadWorkerFrame*f,void*){auto*q=current;if(!f||!q||!q->arm.title||q->state->report.scopes[q->index].call!=f->call_id)return;AcquireSRWLockExclusive(&q->state->lock);q->state->report.scopes[q->index].after=1;ReleaseSRWLockExclusive(&q->state->lock);}
void titleFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*){auto*q=current;if(f&&x&&q&&q->arm.title&&q->state->report.scopes[q->index].call==f->call_id)finish(*q,*x);}
}
bool Adapter::Initialize(const Config&c) noexcept {if(state_||!c.base||!c.generation||!c.provider||!c.nextBefore||!c.nextAfter||!c.nextFinally||c.helperDeadlineMs<1||c.helperDeadlineMs>10000||!code(c.base))return false;
    checkpoint_native_task_provider::Report source{};if(!c.provider->Snapshot(c.generation,source)||!source.registered||source.closed)return false;
    auto*s=new(std::nothrow)State;if(!s)return false;s->config=c;s->report.generation=c.generation;AcquireSRWLockExclusive(&globalLock);bool ok=retainedCount<2;
    if(titleBase&&titleBase!=c.base)ok=false;
    for(unsigned i=0;i<retainedCount;++i)if(retained[i]->config.generation==c.generation||retained[i]->config.base!=c.base)ok=false;
    if(ok&&!veh){HMODULE module=nullptr;if(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&handler),&module))veh=AddVectoredExceptionHandler(1,handler);}
    if(ok&&veh){retained[retainedCount++]=s;state_=s;}else ok=false;ReleaseSRWLockExclusive(&globalLock);if(!ok)delete s;return ok;}
void Adapter::Stop() noexcept {auto*s=static_cast<State*>(state_);if(s){InterlockedExchange(&s->stopped,1);AcquireSRWLockExclusive(&s->lock);s->report.stopped=1;ReleaseSRWLockExclusive(&s->lock);}}
bool Adapter::Snapshot(Report&r) noexcept {auto*s=static_cast<State*>(state_);if(!s)return false;AcquireSRWLockShared(&s->lock);r=s->report;ReleaseSRWLockShared(&s->lock);return true;}
void Adapter::LoadBefore(const CheckpointPushFrame*f,void*p) noexcept {auto*a=static_cast<Adapter*>(p);auto*s=a?static_cast<State*>(a->state_):nullptr;if(!f||!s)return;s->config.nextBefore(f,s->config.nextContext);if(f->slot==3&&candidate(*s,f->args[0],f->caller_entry_rsp,f->thread_id,false))begin(*s,f->call_id,f->args[0],false);}
void Adapter::LoadAfter(const CheckpointPushFrame*f,void*p) noexcept {auto*a=static_cast<Adapter*>(p);auto*s=a?static_cast<State*>(a->state_):nullptr;if(!f||!s)return;auto*q=current;if(q&&q->state==s&&!q->arm.title&&s->report.scopes[q->index].call==f->call_id){AcquireSRWLockExclusive(&s->lock);s->report.scopes[q->index].after=1;ReleaseSRWLockExclusive(&s->lock);}s->config.nextAfter(f,s->config.nextContext);}
void Adapter::LoadFinally(const CheckpointPushFrame*f,const CheckpointLoadWorkerExit*x,void*p){auto*a=static_cast<Adapter*>(p);auto*s=a?static_cast<State*>(a->state_):nullptr;if(!f||!x||!s)return;auto*q=current;if(q&&q->state==s&&!q->arm.title&&s->report.scopes[q->index].call==f->call_id)finish(*q,*x);s->config.nextFinally(f,x,s->config.nextContext);}
bool Adapter::ConfigureTitle(uintptr_t b) noexcept {if(!code(b))return false;AcquireSRWLockExclusive(&globalLock);bool ok=false,sameBase=true;for(unsigned i=0;i<retainedCount;++i)if(retained[i]->config.base!=b)sameBase=false;if(!titleBase&&sameBase){CheckpointLoadWorkerBridgeConfig c{};c.original=reinterpret_cast<void*>(b+0x4AA7B0);c.before=titleBefore;c.after=titleAfter;c.finally=titleFinally;if(CheckpointLoadWorkerBridgeConfigure(1,&c)){titleBase=b;ok=true;}}ReleaseSRWLockExclusive(&globalLock);return ok;}
void* Adapter::TitleEntry() noexcept {return reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1);}
}
