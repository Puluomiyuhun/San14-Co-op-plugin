// Queue-aware successor observes 509FE0 -> Load.Finalize -> Title520.
#include "b_reload_queue_finalize_ports.h"
#include "b_reload_title520_profile.h"
#include "checkpoint_task_native_start_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include "checkpoint_task_native_ports_profile.h"
#include <cstring>
#include <new>
namespace b_reload_queue_finalize_ports {
namespace {
constexpr uintptr_t points[]={0x4CC690,0x834B60};
struct Debug {DWORD64 v[6]{};};
struct Job {HANDLE target=nullptr;uintptr_t base=0;bool title=false,restore=false,attempted=false,completed=false;Debug original{},observed{};Error error=Error::None;DWORD os=0;};
struct State;
struct Scope {State* state=nullptr;unsigned index=0;HANDLE target=nullptr;Job arm{},restore{};bool needsRestore=false;std::uint64_t parentCall=0;uintptr_t load=0,closure=0,title=0;};
struct State {Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG stopped=0,busy=0;Scope scopes[4]{};};
thread_local Scope* current=nullptr;SRWLOCK globalLock=SRWLOCK_INIT;State* retained[2]{};unsigned retainedCount=0;PVOID veh=nullptr;uintptr_t sourceBase=0;
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
void fail(State&s,Error e,DWORD os=0){AcquireSRWLockExclusive(&s.lock);if(s.report.error==Error::None)s.report.error=e;if(current&&current->state==&s){auto&r=s.report.scopes[current->index];if(r.error==Error::None)r.error=e;r.osError=os;}ReleaseSRWLockExclusive(&s.lock);}
bool code(uintptr_t b) noexcept {__try {if(!b||b>UINTPTR_MAX-0x2200000)return false;
 struct Span{uintptr_t rva;size_t size;const unsigned char*bytes;};
 const Span spans[]={
 {0x497110,sizeof b_reload_title520_profile::FinalizeBytes,b_reload_title520_profile::FinalizeBytes},
 {0x4FAC30,sizeof b_reload_title520_profile::ThunkBytes,b_reload_title520_profile::ThunkBytes},
 {0x4CC690,sizeof b_reload_title520_profile::CallbackBytes,b_reload_title520_profile::CallbackBytes},
 {0x4BEE50,sizeof b_reload_title520_profile::StartBytes,b_reload_title520_profile::StartBytes},
 {0x834B60,sizeof checkpoint_task_native_start::StartBytes,checkpoint_task_native_start::StartBytes},
 {0x83A930,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes,checkpoint_task_native_activation_v2::ThreadEntryBytes},
 {0x834D10,sizeof checkpoint_task_native_ports::RunnerBytes,checkpoint_task_native_ports::RunnerBytes}};
 for(const auto& span:spans){const auto p=b+span.rva;MEMORY_BASIC_INFORMATION m{};
 if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.BaseAddress)+m.RegionSize<p+span.size||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef CHECKPOINT_TASK_COMPLETION_FIXTURE
 if(m.Type!=MEM_IMAGE||uintptr_t(m.AllocationBase)!=b)return false;
#endif
 if(memcmp(reinterpret_cast<void*>(p),span.bytes,span.size))return false;}return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
Debug read(const CONTEXT&c){return{{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}};}
void write(CONTEXT&c,const Debug&v){c.Dr0=v.v[0];c.Dr1=v.v[1];c.Dr2=v.v[2];c.Dr3=v.v[3];c.Dr6=v.v[4];c.Dr7=v.v[5];}
Debug armed(const Job&j){Debug d=j.original;d.v[0]=j.base+points[0];d.v[1]=j.base+points[1];d.v[2]=0;d.v[3]=0;d.v[5]|=5;return d;}
bool sameLayout(const Debug&a,const Debug&b){return a.v[0]==b.v[0]&&a.v[1]==b.v[1]&&a.v[2]==b.v[2]&&a.v[3]==b.v[3]&&(a.v[5]&~0x400ull)==(b.v[5]&~0x400ull);}
DWORD WINAPI helper(void*p){auto&j=*static_cast<Job*>(p);const auto prior=SuspendThread(j.target);if(prior==DWORD(-1)){j.error=Error::Helper;j.os=GetLastError();j.completed=true;return 0;}
    if(prior)j.error=Error::Helper;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}
    if(j.error==Error::None){j.observed=read(c);if(!j.restore){j.original=j.observed;if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xFFFF00FFull)||(c.Dr6&0xE00Full))j.error=Error::Occupied;else write(c,armed(j));}
        else if(!sameLayout(j.observed,armed(j))||((j.observed.v[4]^j.original.v[4])&0xE00Full))j.error=Error::Restore;else write(c,j.original);
        if(j.error==Error::None){j.attempted=true;if(!SetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}else {CONTEXT v{};v.ContextFlags=CONTEXT_DEBUG_REGISTERS;
            if(!GetThreadContext(j.target,&v)){j.error=Error::Context;j.os=GetLastError();}else {j.observed=read(v);auto expected=read(c);if(memcmp(expected.v,j.observed.v,sizeof expected.v))j.error=Error::Context;}}}}
    if(ResumeThread(j.target)==DWORD(-1)){j.error=Error::Restore;j.os=GetLastError();}j.completed=true;return 0;}
bool run(Scope&q,Job&j){auto&s=*q.state;HANDLE h=CreateThread(nullptr,0,helper,&j,0,nullptr);if(!h){fail(s,Error::Helper,GetLastError());return false;}const auto waited=WaitForSingleObject(h,s.config.helperDeadlineMs);
    if(waited!=WAIT_OBJECT_0){fail(s,Error::Deadline);AcquireSRWLockExclusive(&s.lock);s.report.scopes[q.index].uncertain=1;ReleaseSRWLockExclusive(&s.lock);if(WaitForSingleObject(h,INFINITE)!=WAIT_OBJECT_0)return false;}
    CloseHandle(h);if(j.error!=Error::None)fail(s,j.error,j.os);return waited==WAIT_OBJECT_0&&j.completed&&j.error==Error::None;}
bool binding(State&s,const b_reload_queue_parent_source::QueueOwner&q){return q.base==s.config.base&&q.manager==s.config.base+0x19E7310&&q.provider==s.config.provider&&q.thread==GetCurrentThreadId()&&q.binding.generation==s.report.binding.generation&&q.binding.attempt==s.report.binding.attempt&&q.binding.epoch==s.report.binding.epoch;}
bool candidate(State&s,const CheckpointLoadWorkerFrame&f) noexcept {__try {
 b_reload_queue_parent_source::QueueOwner q{};if(!b_reload_queue_parent_source::Owner::CurrentQueueOwner(q)||!binding(s,q)||!f.caller_entry_rsp)return false;
 const auto caller=at<uintptr_t>(f.caller_entry_rsp)-s.config.base;if(caller!=0x50AA56&&caller!=0x50AD45&&caller!=0x50B002&&caller!=0x50B1B8)return false;
 checkpoint_native_task_provider::Report p{};if(f.thread_id!=GetCurrentThreadId()||!s.config.provider->Snapshot(s.config.generation,p)||!p.registered||!p.windowOpen||p.closed||p.error!=checkpoint_native_task_provider::Error::None||!p.loadBound||!p.roles[0].joined||p.titleCallback)return false;
 const auto b=s.config.base,m=b+0x19E7310,stack=at<uintptr_t>(m+0x20);
 return f.args[0]==p.load&&at<uintptr_t>(p.load)==b+0x12DBD68&&!at<uintptr_t>(p.load+0x50)&&at<uintptr_t>(p.load+0x48)==p.closure&&at<uintptr_t>(p.closure)==b+0x12EA4D0&&at<uintptr_t>(p.closure+8)==p.title&&at<uintptr_t>(b+0x12EA4D0+0x10)==b+0x4FAC30&&!at<uintptr_t>(m+0x48)&&at<std::uint64_t>(m+0x10)==4&&stack&&at<uintptr_t>(stack+16)==p.title&&at<uintptr_t>(stack+24)==p.load;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void capture(Scope&q,CONTEXT&c,unsigned role,DWORD flags){auto&s=*q.state;Sample sample{};sample.call=s.report.scopes[q.index].call;sample.rip=c.Rip;sample.thread=GetCurrentThreadId();sample.rawFlags=flags;sample.mxcsr=c.MxCsr;sample.role=role;
 const std::uint64_t regs[]={c.Rax,c.Rcx,c.Rdx,c.Rbx,c.Rsp,c.Rbp,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15};memcpy(sample.gpr,regs,sizeof regs);memcpy(sample.xmm,&c.Xmm0,sizeof sample.xmm);
 AcquireSRWLockShared(&s.lock);const bool eligible=s.report.error==Error::None&&s.report.scopes[q.index].error==Error::None&&!s.report.scopes[q.index].uncertain;ReleaseSRWLockShared(&s.lock);if(!eligible)return;
 if(get(s.stopped)){fail(s,Error::Stopped);return;}
 b_reload_queue_parent_source::QueueOwner parent{};if(!b_reload_queue_parent_source::Owner::CurrentQueueOwner(parent)||!binding(s,parent)||parent.call!=q.parentCall||at<uintptr_t>(s.config.base+0x19E7310+0x48)||at<uintptr_t>(q.load+0x48)!=q.closure||at<uintptr_t>(q.closure+8)!=q.title){fail(s,Error::Binding);return;}
 checkpoint_native_task_provider::Report p{};if(!s.config.provider->Snapshot(s.config.generation,p)||p.error!=checkpoint_native_task_provider::Error::None||!p.roles[0].joined||(role?(!p.titleCallback||p.roles[1].start||c.Rcx!=p.title+0x520):(p.titleCallback||c.Rcx!=p.title||c.Rdx!=p.load))){fail(s,Error::Order);return;}
 const checkpoint_native_task_provider::Capture actual{c.Rip,c.Rcx,c.Rdx,c.Rbx,c.Rdi,c.Rsp,GetCurrentThreadId()};sample.accepted=s.config.provider->Observe(actual);
 AcquireSRWLockExclusive(&s.lock);s.report.samples[role]=sample;(role?s.report.start520:s.report.callback)+=sample.accepted;++s.report.scopes[q.index].hits;ReleaseSRWLockExclusive(&s.lock);
 if(!sample.accepted||(role&&!s.config.title520->OnStart(actual)))fail(s,Error::Provider);
}
LONG body(EXCEPTION_POINTERS*ep,Scope*&claimed){auto*q=current;if(!q||!ep||!ep->ExceptionRecord||!ep->ContextRecord||ep->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
 auto&c=*ep->ContextRecord;auto&s=*q->state;unsigned slot=0;if(c.Rip!=s.config.base+points[0]){if(c.Rip==s.config.base+points[1])slot=1;else return EXCEPTION_CONTINUE_SEARCH;}
 if(uintptr_t(ep->ExceptionRecord->ExceptionAddress)!=c.Rip||GetCurrentThreadId()!=s.report.scopes[q->index].thread||!sameLayout(read(c),armed(q->arm))||(c.Dr6&0xE00Full)!=(DWORD64(1)<<slot))return EXCEPTION_CONTINUE_SEARCH;
 claimed=q;const auto flags=c.EFlags;c.EFlags|=0x10000;c.Dr6&=~(DWORD64(1)<<slot);capture(*q,c,slot,flags);return EXCEPTION_CONTINUE_EXECUTION;
}
LONG CALLBACK handler(EXCEPTION_POINTERS*ep){Scope*claimed=nullptr;__try{return body(ep,claimed);}__except(EXCEPTION_EXECUTE_HANDLER){if(!claimed)return EXCEPTION_CONTINUE_SEARCH;fail(*claimed->state,Error::Exception,GetExceptionCode());return EXCEPTION_CONTINUE_EXECUTION;}}
void begin(State&s,std::uint64_t call,uintptr_t owner,bool title){if(current||IsDebuggerPresent()||get(s.stopped)||!code(s.config.base)){fail(s,Error::Binding);return;}if(InterlockedCompareExchange(&s.busy,1,0)){fail(s,Error::Occupied);return;}
    AcquireSRWLockExclusive(&s.lock);if(s.report.scopeCount>=4){if(s.report.error==Error::None)s.report.error=Error::Capacity;ReleaseSRWLockExclusive(&s.lock);InterlockedExchange(&s.busy,0);return;}
    const auto i=s.report.scopeCount++;auto&q=s.scopes[i];q.state=&s;q.index=i;auto&r=s.report.scopes[i];r.call=call;r.owner=owner;r.title=title;r.thread=GetCurrentThreadId();s.report.active=1;ReleaseSRWLockExclusive(&s.lock);current=&q;
    if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&q.target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)){fail(s,Error::Helper,GetLastError());return;}
    q.arm.target=q.target;q.arm.base=s.config.base;q.arm.title=title;const bool ok=run(q,q.arm);q.needsRestore=q.arm.attempted;
    AcquireSRWLockExclusive(&s.lock);r.armed=ok;memcpy(r.originalDr,q.arm.original.v,sizeof r.originalDr);ReleaseSRWLockExclusive(&s.lock);
}
void finish(Scope&q,const CheckpointLoadWorkerExit&x){auto&s=*q.state;bool ok=!q.needsRestore;if(q.needsRestore){q.restore.target=q.target;q.restore.base=s.config.base;q.restore.title=q.arm.title;q.restore.restore=true;q.restore.original=q.arm.original;ok=run(q,q.restore);}
    AcquireSRWLockExclusive(&s.lock);auto&r=s.report.scopes[q.index];r.finally=1;r.abnormal=x.abnormal;r.restored=ok;r.uncertain|=!ok;memcpy(r.restoredDr,q.needsRestore?q.restore.observed.v:q.arm.observed.v,sizeof r.restoredDr);++s.report.completedScopes;s.report.active=0;const bool clear=ok&&!r.uncertain;ReleaseSRWLockExclusive(&s.lock);
    if(clear){current=nullptr;if(q.target){CloseHandle(q.target);q.target=nullptr;}InterlockedExchange(&s.busy,0);} // otherwise retained TLS tombstone rejects future capture
}
void before(const CheckpointLoadWorkerFrame*f,void*){if(!f)return;State*selected=nullptr;b_reload_queue_parent_source::QueueOwner parent{};const bool owned=b_reload_queue_parent_source::Owner::CurrentQueueOwner(parent);AcquireSRWLockShared(&globalLock);
 for(unsigned i=0;i<retainedCount;++i){auto*s=retained[i];checkpoint_native_task_provider::Report p{};if(!s->config.provider->Snapshot(s->config.generation,p)||!p.loadBound||p.closed||!p.windowOpen)continue;
  if(owned?binding(*s,parent):p.load==f->args[0]){if(selected){fail(*selected,Error::Binding);selected=nullptr;break;}selected=s;}}
 ReleaseSRWLockShared(&globalLock);if(!selected)return;
 if(!owned||!candidate(*selected,*f)){AcquireSRWLockExclusive(&selected->lock);++selected->report.refused;ReleaseSRWLockExclusive(&selected->lock);fail(*selected,Error::Binding);return;}
 checkpoint_native_task_provider::Report p{};if(!selected->config.provider->Snapshot(selected->config.generation,p)){fail(*selected,Error::Binding);return;}
 begin(*selected,f->call_id,f->args[0],false);auto*q=current;if(!q||q->state!=selected)return;q->parentCall=parent.call;q->load=p.load;q->closure=p.closure;q->title=p.title;
 AcquireSRWLockExclusive(&selected->lock);selected->report.parentCall=parent.call;selected->report.caller=at<uintptr_t>(f->caller_entry_rsp);selected->report.currentAtEntry=at<uintptr_t>(selected->config.base+0x19E7310+0x48);selected->report.load=p.load;selected->report.closure=p.closure;selected->report.title=p.title;ReleaseSRWLockExclusive(&selected->lock);
}
void after(const CheckpointLoadWorkerFrame*f,void*){auto*q=current;if(!f||!q||q->state->report.scopes[q->index].call!=f->call_id)return;AcquireSRWLockExclusive(&q->state->lock);q->state->report.scopes[q->index].after=1;ReleaseSRWLockExclusive(&q->state->lock);}
void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*){auto*q=current;if(f&&x&&q&&q->state->report.scopes[q->index].call==f->call_id)finish(*q,*x);}
}
bool Adapter::Initialize(const Config&c) noexcept {if(state_||!c.base||!c.generation||!c.provider||!c.title520||c.helperDeadlineMs<1||c.helperDeadlineMs>10000||!code(c.base))return false;
 checkpoint_native_task_provider::Report source{};if(!c.provider->Snapshot(c.generation,source)||!source.registered||source.closed)return false;
 auto*s=new(std::nothrow)State;if(!s)return false;s->config=c;s->report.generation=c.generation;s->report.binding={c.generation,source.attempt,source.epoch};if(!source.attempt||!source.epoch){delete s;return false;}AcquireSRWLockExclusive(&globalLock);bool ok=retainedCount<2;
 if(sourceBase&&sourceBase!=c.base)ok=false;
 for(unsigned i=0;i<retainedCount;++i)if(retained[i]->config.generation==c.generation||retained[i]->config.base!=c.base)ok=false;
 if(ok&&!veh){HMODULE module=nullptr;if(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&handler),&module))veh=AddVectoredExceptionHandler(1,handler);}
 if(ok&&veh){retained[retainedCount++]=s;state_=s;}else ok=false;ReleaseSRWLockExclusive(&globalLock);if(!ok)delete s;return ok;}
void Adapter::Stop() noexcept {auto*s=static_cast<State*>(state_);if(s){InterlockedExchange(&s->stopped,1);s->config.title520->Stop();AcquireSRWLockExclusive(&s->lock);s->report.stopped=1;ReleaseSRWLockExclusive(&s->lock);}}
bool Adapter::Snapshot(Report&r) noexcept {auto*s=static_cast<State*>(state_);if(!s)return false;AcquireSRWLockShared(&s->lock);r=s->report;ReleaseSRWLockShared(&s->lock);return true;}
bool Adapter::Configure(uintptr_t b) noexcept {if(!code(b))return false;AcquireSRWLockExclusive(&globalLock);bool ok=false,sameBase=true;for(unsigned i=0;i<retainedCount;++i)if(retained[i]->config.base!=b)sameBase=false;if(!sourceBase&&sameBase){CheckpointLoadWorkerBridgeConfig c{};c.original=reinterpret_cast<void*>(b+0x497110);c.before=before;c.after=after;c.finally=finally;if(BReloadTitle520BridgeConfigure(1,&c)){sourceBase=b;ok=true;}}ReleaseSRWLockExclusive(&globalLock);return ok;}
void* Adapter::Entry() noexcept {return reinterpret_cast<void*>(&BReloadTitle520Bridge1);}
}
