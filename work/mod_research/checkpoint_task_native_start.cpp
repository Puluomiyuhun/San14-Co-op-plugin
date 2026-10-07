#include "checkpoint_task_native_start.h"
#include "checkpoint_task_native_start_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <cstring>
#include <new>
namespace checkpoint_task_native_start {
namespace {
constexpr uintptr_t points[]={0x4DA240,0x834B60};
using QueryEvent=LONG(NTAPI*)(HANDLE,unsigned,void*,ULONG,ULONG*);
struct EventBasic {LONG type,state;};
struct Debug {DWORD64 v[6]{};};
struct Job {HANDLE target=nullptr;uintptr_t base=0;bool restore=false,attempted=false,changed=false,completed=false;Debug original{},observed{};Error error=Error::None;DWORD os=0;};
struct State {Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG used=0,stopped=0,inHandler=0,publication=0;HANDLE parent=nullptr;Job arm{},restore{};bool needsRestore=false;QueryEvent query=nullptr;};
thread_local State* current=nullptr;SRWLOCK globalLock=SRWLOCK_INIT;PVOID handlerToken=nullptr;unsigned retained=0;
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
void fail(State&s,Error e,DWORD os=0){AcquireSRWLockExclusive(&s.lock);if(s.report.error==Error::None)s.report.error=e;if(os)s.report.osError=os;ReleaseSRWLockExclusive(&s.lock);}
Debug read(const CONTEXT&c){return{{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}};}
void write(CONTEXT&c,const Debug&v){c.Dr0=v.v[0];c.Dr1=v.v[1];c.Dr2=v.v[2];c.Dr3=v.v[3];c.Dr6=v.v[4];c.Dr7=v.v[5];}
bool page(uintptr_t p,size_t n,bool code){MEMORY_BASIC_INFORMATION m{};if(p>UINTPTR_MAX-n||VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||p+n>uintptr_t(m.BaseAddress)+m.RegionSize)return false;
    if(code){
#ifndef CHECKPOINT_TASK_NATIVE_START_FIXTURE
        if(m.Type!=MEM_IMAGE)return false;
#endif
        return m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY;}
    return m.Protect==PAGE_READWRITE||m.Protect==PAGE_WRITECOPY;
}
bool code(uintptr_t b) noexcept {__try{return b&&b<UINTPTR_MAX-0x2200000&&page(b+points[0],sizeof BindBytes,true)&&page(b+points[1],sizeof StartBytes,true)&&
    page(b+0x83A930,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes,true)&&
    !memcmp(reinterpret_cast<void*>(b+points[0]),BindBytes,sizeof BindBytes)&&!memcmp(reinterpret_cast<void*>(b+points[1]),StartBytes,sizeof StartBytes)&&
    !memcmp(reinterpret_cast<void*>(b+0x83A930),checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes);
}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
DWORD WINAPI helper(void*p){auto&j=*static_cast<Job*>(p);auto prior=SuspendThread(j.target);if(prior==DWORD(-1)){j.error=Error::Helper;j.os=GetLastError();j.completed=true;return 0;}
    if(prior)j.error=Error::Helper;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::DebugContext;j.os=GetLastError();}
    if(j.error==Error::None){j.observed=read(c);if(!j.restore){j.original=j.observed;
        if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xFFFF00FFull)||(c.Dr6&0xE00Full))j.error=Error::Occupied;
        else {c.Dr0=j.base+points[0];c.Dr1=j.base+points[1];c.Dr7|=5;}}
        else if(c.Dr0!=j.base+points[0]||c.Dr1!=j.base+points[1]||c.Dr2||c.Dr3||(c.Dr7&~0x400ull)!=((j.original.v[5]|5)&~0x400ull))j.error=Error::Restore;
        else write(c,j.original);
        if(j.error==Error::None){j.attempted=true;if(!SetThreadContext(j.target,&c)){j.error=Error::DebugContext;j.os=GetLastError();}else {j.changed=true;CONTEXT v{};v.ContextFlags=CONTEXT_DEBUG_REGISTERS;
            if(!GetThreadContext(j.target,&v)){j.error=Error::DebugContext;j.os=GetLastError();}else {j.observed=read(v);auto expect=read(c);if(memcmp(expect.v,j.observed.v,sizeof expect.v))j.error=Error::DebugContext;}}}}
    if(ResumeThread(j.target)==DWORD(-1)){j.error=Error::Resume;j.os=GetLastError();}j.completed=true;return 0;
}
bool runJob(State&s,Job&j){HANDLE h=CreateThread(nullptr,0,helper,&j,0,nullptr);if(!h){fail(s,Error::Helper,GetLastError());return false;}auto waited=WaitForSingleObject(h,s.config.helperDeadlineMs);
    if(waited!=WAIT_OBJECT_0){fail(s,Error::Deadline);AcquireSRWLockExclusive(&s.lock);s.report.uncertain=1;ReleaseSRWLockExclusive(&s.lock);if(WaitForSingleObject(h,INFINITE)!=WAIT_OBJECT_0)return false;}
    CloseHandle(h);if(j.error!=Error::None)fail(s,j.error,j.os);return waited==WAIT_OBJECT_0&&j.completed&&j.error==Error::None;
}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool sameNative(uintptr_t control,uintptr_t object,const checkpoint_native_task_provider::Role&r,uintptr_t base){return control==r.control&&object==r.threadObject&&
    at<uintptr_t>(control)==object&&at<uintptr_t>(control+0x48)==r.callable&&at<DWORD>(control+0x50)==1&&!at<DWORD>(control+0x54)&&
    at<uintptr_t>(object+0x30)==control&&at<uintptr_t>(object+0x38)==base+0x834D10&&at<DWORD>(object+0x10)==r.workerThread;}
bool eventClear(State&s,HANDLE event,Report&r){EventBasic info{};ULONG n=0;const LONG status=s.query(event,0,&info,sizeof info,&n);r.eventType=info.type;r.eventState=info.state;
    return status>=0&&n==sizeof info&&info.type==1&&info.state==0;}
bool waiting(State&s,HANDLE worker,uintptr_t object,uintptr_t control,Report&r){CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL|CONTEXT_INTEGER;if(!GetThreadContext(worker,&c))return false;
    for(unsigned i=0;i<32;++i){r.unwindFrames=i;r.waitRip=c.Rip;
        // Exact native continuation before loading/calling [object+38]. The
        // worker remains suspended across this proof, event query and CAS.
        if(c.Rip==s.config.base+0x83A9D7)return c.Rbx==object+0x38&&c.Rsi==object&&c.Rdi==control;
        if(!c.Rip||!c.Rsp||c.Rsp>UINTPTR_MAX-16)return false;const auto previous=c.Rsp;DWORD64 image=0;auto*fn=RtlLookupFunctionEntry(c.Rip,&image,nullptr);
        if(fn){PVOID data=nullptr;DWORD64 establisher=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,image,c.Rip,fn,&c,&data,&establisher,nullptr);}
        else {c.Rip=at<uintptr_t>(c.Rsp);c.Rsp+=8;}
        if(c.Rsp<=previous||c.Rsp-previous>0x100000)return false;
    }return false;
}
void publish(State&s) noexcept {
    Report r{};AcquireSRWLockShared(&s.lock);r=s.report;ReleaseSRWLockShared(&s.lock);HANDLE worker=nullptr,event=nullptr;bool suspended=false;
    __try {__try {
        checkpoint_native_task_provider::Report p{};if(!s.config.provider->Snapshot(s.config.generation,p)||p.error!=checkpoint_native_task_provider::Error::None||!p.roles[0].start||p.roles[0].invoke){r.error=Error::Source;__leave;}
        const auto&w=p.roles[0];r.creation=w.creation;r.control=w.control;r.object=w.threadObject;r.workerThread=w.workerThread;r.slot=w.threadObject+0x38;r.original=s.config.base+0x834D10;r.replacement=uintptr_t(checkpoint_task_native_activation_v2::Router::Entry());
        if(!sameNative(r.control,r.object,w,s.config.base)||(r.slot%8)||!page(r.slot,8,false)||w.workerThread==GetCurrentThreadId()){r.error=Error::Binding;__leave;}
        const auto threadHandle=reinterpret_cast<HANDLE>(at<uintptr_t>(r.object+0x18)),eventHandle=reinterpret_cast<HANDLE>(at<uintptr_t>(r.object+0x20));
        if(!DuplicateHandle(GetCurrentProcess(),threadHandle,GetCurrentProcess(),&worker,THREAD_GET_CONTEXT|THREAD_SUSPEND_RESUME|THREAD_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,0)||GetThreadId(worker)!=w.workerThread||GetProcessIdOfThread(worker)!=GetCurrentProcessId()||
            !DuplicateHandle(GetCurrentProcess(),eventHandle,GetCurrentProcess(),&event,0,FALSE,DUPLICATE_SAME_ACCESS)){r.error=Error::Worker;r.osError=GetLastError();__leave;}
        const auto prior=SuspendThread(worker);if(prior==DWORD(-1)){r.error=Error::Worker;r.osError=GetLastError();__leave;}suspended=true;r.workerSuspended=1;
        if(prior||!sameNative(r.control,r.object,w,s.config.base)){r.error=Error::Worker;__leave;}
        if(!waiting(s,worker,r.object,r.control,r)){r.error=Error::WaitStack;__leave;}r.waitStackVerified=1;
        if(!eventClear(s,event,r)){r.error=Error::Event;__leave;}r.eventUnsignaled=1;
        if(!s.config.publishRunner||get(s.stopped))__leave;
        if(!s.config.activation->ValidateRegistration(*s.config.provider,s.config.base,s.config.generation)||!page(r.replacement,32,true)){r.error=Error::Binding;__leave;}
        if(InterlockedCompareExchange(&s.publication,1,0)!=0){r.error=Error::Stopped;__leave;}r.publicationClaimed=1;
        if(!s.config.activation->ValidateRegistration(*s.config.provider,s.config.base,s.config.generation)){r.error=Error::Binding;__leave;}
        if(InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(r.slot),reinterpret_cast<void*>(r.replacement),reinterpret_cast<void*>(r.original))!=reinterpret_cast<void*>(r.original)){r.error=Error::Pointer;__leave;}
        r.published=1;
        if(at<uintptr_t>(r.slot)!=r.replacement||!eventClear(s,event,r)){
            r.error=Error::Event;if(InterlockedCompareExchangePointer(reinterpret_cast<void* volatile*>(r.slot),reinterpret_cast<void*>(r.original),reinterpret_cast<void*>(r.replacement))==reinterpret_cast<void*>(r.replacement)){r.rolledBack=1;r.published=0;}else r.uncertain=1;
        }
    }__finally {if(suspended){if(ResumeThread(worker)==DWORD(-1)){r.error=Error::Resume;r.osError=GetLastError();r.uncertain=1;}else r.workerResumed=1;}if(worker)CloseHandle(worker);if(event)CloseHandle(event);}}
    __except(EXCEPTION_EXECUTE_HANDLER){r.error=Error::Exception;r.exception=GetExceptionCode();r.uncertain|=r.published;}
    AcquireSRWLockExclusive(&s.lock);const auto old=s.report.error;r.stopped=get(s.stopped)!=0;r.stopAfterClaim=r.stopped&&r.publicationClaimed;s.report=r;if(old!=Error::None)s.report.error=old;ReleaseSRWLockExclusive(&s.lock);
}
LONG body(EXCEPTION_POINTERS*ep,State*&claimed){auto*s=current;if(!s||!ep||!ep->ExceptionRecord||!ep->ContextRecord||ep->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
    auto&c=*ep->ContextRecord;unsigned i=0;for(;i<2;++i)if(c.Rip==s->config.base+points[i])break;if(i==2||uintptr_t(ep->ExceptionRecord->ExceptionAddress)!=c.Rip||GetCurrentThreadId()!=s->report.parentThread)return EXCEPTION_CONTINUE_SEARCH;
    if(c.Dr0!=s->config.base+points[0]||c.Dr1!=s->config.base+points[1]||c.Dr2||c.Dr3||(c.Dr7&~0x400ull)!=((s->arm.original.v[5]|5)&~0x400ull)||(c.Dr6&0xE00Full)!=(DWORD64(1)<<i))return EXCEPTION_CONTINUE_SEARCH;
    claimed=s;const DWORD flags=c.EFlags;c.EFlags|=0x10000;c.Dr6&=~(DWORD64(1)<<i);
    if(InterlockedCompareExchange(&s->inHandler,1,0)){fail(*s,Error::Occupied);return EXCEPTION_CONTINUE_EXECUTION;}
    bool deliver=false;AcquireSRWLockExclusive(&s->lock);if(s->report.captured==i&&!get(s->stopped)&&s->report.error==Error::None){s->report.samples[i]={c.Rip,c.Rcx,c.Rdx,c.Rbx,c.Rdi,c.Rsp,GetCurrentThreadId(),flags,0};++s->report.captured;deliver=true;}else if(s->report.error==Error::None)s->report.error=get(s->stopped)?Error::Stopped:Error::Source;ReleaseSRWLockExclusive(&s->lock);
    if(deliver){const checkpoint_native_task_provider::Capture actual{c.Rip,c.Rcx,c.Rdx,c.Rbx,c.Rdi,c.Rsp,GetCurrentThreadId()};const bool ok=s->config.provider->Observe(actual);
        AcquireSRWLockExclusive(&s->lock);s->report.samples[i].accepted=ok;if(!ok)s->report.error=Error::Source;ReleaseSRWLockExclusive(&s->lock);if(ok&&i==1)publish(*s);}
    InterlockedExchange(&s->inHandler,0);return EXCEPTION_CONTINUE_EXECUTION;
}
LONG CALLBACK handler(EXCEPTION_POINTERS*ep){State*claimed=nullptr;__try{return body(ep,claimed);}__except(EXCEPTION_EXECUTE_HANDLER){if(!claimed)return EXCEPTION_CONTINUE_SEARCH;fail(*claimed,Error::Exception,GetExceptionCode());InterlockedExchange(&claimed->inHandler,0);return EXCEPTION_CONTINUE_EXECUTION;}}
bool candidate(State&s,const CheckpointPushFrame&f) noexcept {__try {checkpoint_native_task_provider::Report p{};checkpoint_dynamic_native_session::Report session{};s.config.sessionOwner->Snapshot(session);
    const auto b=s.config.base,m=b+0x19E7310;
    uintptr_t caller=b+0x50B785;
#ifdef CHECKPOINT_TASK_NATIVE_START_FIXTURE
    if(s.config.fixtureUpdateCaller)caller=s.config.fixtureUpdateCaller;
#endif
    return f.slot==3&&f.thread_id==GetCurrentThreadId()&&at<uintptr_t>(f.caller_entry_rsp)==caller&&s.config.provider->Snapshot(s.config.generation,p)&&p.registered&&p.windowOpen&&!p.loadBound&&p.error==checkpoint_native_task_provider::Error::None&&
        session.attempt==p.attempt&&session.casPublished&&!session.error&&at<uintptr_t>(f.args[0])==b+0x12DBD68&&at<DWORD>(f.args[0]+0x470)==1&&
        at<std::uint64_t>(m+0x10)==4&&at<uintptr_t>(at<uintptr_t>(m+0x20)+24)==f.args[0]&&at<uintptr_t>(m+0x48)==f.args[0];
}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void finish(State&s){if(current!=&s)return;bool ok=!s.needsRestore;if(s.needsRestore){s.restore.target=s.parent;s.restore.base=s.config.base;s.restore.restore=true;s.restore.original=s.arm.original;ok=runJob(s,s.restore);}
    AcquireSRWLockExclusive(&s.lock);s.report.restored=ok;s.report.uncertain|=!ok;memcpy(s.report.restoredDr,s.needsRestore?s.restore.observed.v:s.arm.observed.v,sizeof s.report.restoredDr);const bool clear=ok&&!s.report.uncertain;ReleaseSRWLockExclusive(&s.lock);
    if(clear){current=nullptr;if(s.parent){CloseHandle(s.parent);s.parent=nullptr;}}
}
}
bool Adapter::Initialize(const Config&c) noexcept {
    if(state_||!c.provider||!c.sessionOwner||!c.activation||!c.generation||!c.nextBefore||!c.nextAfter||!c.nextFinally||c.helperDeadlineMs<1||c.helperDeadlineMs>10000||!code(c.base)||!c.activation->ValidateRegistration(*c.provider,c.base,c.generation))return false;
    auto*s=new(std::nothrow)State;if(!s)return false;s->config=c;s->report.generation=c.generation;s->report.publishOptIn=c.publishRunner;
    s->query=reinterpret_cast<QueryEvent>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryEvent"));if(!s->query){delete s;return false;}
    AcquireSRWLockExclusive(&globalLock);bool ok=false;if(retained<2){if(!handlerToken){HMODULE mod=nullptr;if(GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&handler),&mod))handlerToken=AddVectoredExceptionHandler(1,handler);}
        if(handlerToken){++retained;state_=s;ok=true;}}ReleaseSRWLockExclusive(&globalLock);if(!ok)delete s;return ok;
}
void Adapter::Stop() noexcept {auto*s=static_cast<State*>(state_);if(!s)return;InterlockedCompareExchange(&s->publication,2,0);InterlockedExchange(&s->stopped,1);s->config.activation->Stop(s->config.generation);AcquireSRWLockExclusive(&s->lock);s->report.stopped=1;ReleaseSRWLockExclusive(&s->lock);}
bool Adapter::Snapshot(Report&r) noexcept {auto*s=static_cast<State*>(state_);if(!s)return false;AcquireSRWLockShared(&s->lock);r=s->report;ReleaseSRWLockShared(&s->lock);return true;}
void Adapter::Before(const CheckpointPushFrame*f,void*p) noexcept {auto*a=static_cast<Adapter*>(p);auto*s=a?static_cast<State*>(a->state_):nullptr;if(!s||!f)return;s->config.nextBefore(f,s->config.nextContext);
    if(!candidate(*s,*f)||InterlockedCompareExchange(&s->used,1,0))return;
    AcquireSRWLockExclusive(&s->lock);s->report.call=f->call_id;s->report.load=f->args[0];s->report.parentThread=GetCurrentThreadId();ReleaseSRWLockExclusive(&s->lock);
    if(current||IsDebuggerPresent()||get(s->stopped)||!code(s->config.base)){fail(*s,Error::Binding);return;}
    if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&s->parent,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)){fail(*s,Error::Helper,GetLastError());return;}
    current=s;s->arm.target=s->parent;s->arm.base=s->config.base;const bool ok=runJob(*s,s->arm);s->needsRestore=s->arm.attempted;
    AcquireSRWLockExclusive(&s->lock);s->report.armed=ok;memcpy(s->report.originalDr,s->arm.original.v,sizeof s->report.originalDr);ReleaseSRWLockExclusive(&s->lock);if(!ok)finish(*s);
}
void Adapter::After(const CheckpointPushFrame*f,void*p) noexcept {auto*a=static_cast<Adapter*>(p);auto*s=a?static_cast<State*>(a->state_):nullptr;if(s&&f)s->config.nextAfter(f,s->config.nextContext);}
void Adapter::Finally(const CheckpointPushFrame*f,const CheckpointLoadWorkerExit*x,void*p){auto*a=static_cast<Adapter*>(p);auto*s=a?static_cast<State*>(a->state_):nullptr;if(!s||!f||!x)return;
    if(s->report.call==f->call_id&&s->report.parentThread==GetCurrentThreadId()){finish(*s);AcquireSRWLockExclusive(&s->lock);s->report.finally=1;s->report.abnormal=x->abnormal;ReleaseSRWLockExclusive(&s->lock);}
    s->config.nextFinally(f,x,s->config.nextContext);
}
}
