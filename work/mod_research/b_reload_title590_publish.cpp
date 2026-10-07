// Fixed Title +590 publication; same native wait proof as frozen Load start.
#include "b_reload_title590_publish.h"
#include <new>
namespace b_reload_title590_publish {
namespace {
using QueryEvent=LONG(NTAPI*)(HANDLE,unsigned,void*,ULONG,ULONG*);
struct EventBasic {LONG type,state;};
struct State {Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG used=0,stopped=0,publication=0;QueryEvent query=nullptr;};
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
void fail(State&s,Error e,DWORD os=0){AcquireSRWLockExclusive(&s.lock);if(s.report.error==Error::None)s.report.error=e;if(os)s.report.osError=os;ReleaseSRWLockExclusive(&s.lock);}
bool page(uintptr_t p,size_t n,bool code){MEMORY_BASIC_INFORMATION m{};if(p>UINTPTR_MAX-n||VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||p+n>uintptr_t(m.BaseAddress)+m.RegionSize)return false;
    if(code){
#ifndef CHECKPOINT_TASK_NATIVE_START_FIXTURE
        if(m.Type!=MEM_IMAGE)return false;
#endif
        return m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY;}
    return m.Protect==PAGE_READWRITE||m.Protect==PAGE_WRITECOPY;
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
        checkpoint_native_task_provider::Report p{};if(!s.config.provider->Snapshot(s.config.generation,p)||p.error!=checkpoint_native_task_provider::Error::None||!p.roles[2].start||p.roles[2].invoke){r.error=Error::Source;__leave;}
        const auto&w=p.roles[2];r.creation=w.creation;r.control=w.control;r.object=w.threadObject;r.workerThread=w.workerThread;r.slot=w.threadObject+0x38;r.original=s.config.base+0x834D10;r.replacement=uintptr_t(b_reload_title590_router::Router::Entry());
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

}
bool Publisher::Initialize(const Config&c) noexcept {
 if(state_||!c.base||!c.generation||!c.provider||!c.activation||!c.activation->ValidateRegistration(*c.provider,c.base,c.generation))return false;
 auto*s=new(std::nothrow)State;if(!s)return false;s->config=c;s->report.generation=c.generation;s->report.publishOptIn=c.publishRunner;
 s->query=reinterpret_cast<QueryEvent>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryEvent"));if(!s->query){delete s;return false;}
 HMODULE module=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&publish),&module)){delete s;return false;}
 state_=s;return true;
}
bool Publisher::OnStart(const checkpoint_native_task_provider::Capture& c) noexcept {
 auto*s=static_cast<State*>(state_);if(!s||InterlockedCompareExchange(&s->used,1,0))return false;
 bool valid=false;
 __try {checkpoint_native_task_provider::Report p{};valid=c.rip==s->config.base+0x834B60&&c.thread==GetCurrentThreadId()&&at<uintptr_t>(c.rsp)==s->config.base+0x4BEF2B&&s->config.provider->Snapshot(s->config.generation,p)&&p.title&&c.rcx==p.title+0x590&&p.roles[2].start&&p.roles[2].startThread==c.thread;}
 __except(EXCEPTION_EXECUTE_HANDLER){valid=false;}
 if(!valid){fail(*s,Error::Source);return false;}
 AcquireSRWLockExclusive(&s->lock);s->report.parentThread=c.thread;s->report.captured=1;s->report.samples[0]={c.rip,c.rcx,c.rdx,c.rbx,c.rdi,c.rsp,c.thread,0,1};ReleaseSRWLockExclusive(&s->lock);
 publish(*s);Report r{};Snapshot(r);return r.error==Error::None&&(!s->config.publishRunner||r.published);
}
void Publisher::Stop() noexcept {auto*s=static_cast<State*>(state_);if(!s)return;InterlockedCompareExchange(&s->publication,2,0);InterlockedExchange(&s->stopped,1);s->config.activation->Stop(s->config.generation);AcquireSRWLockExclusive(&s->lock);s->report.stopped=1;ReleaseSRWLockExclusive(&s->lock);}
bool Publisher::Snapshot(Report&r) noexcept {auto*s=static_cast<State*>(state_);if(!s)return false;AcquireSRWLockShared(&s->lock);r=s->report;ReleaseSRWLockShared(&s->lock);return true;}
}
