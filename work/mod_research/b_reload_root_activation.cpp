#include "b_reload_root_activation.h"
#include "b_reload_root_activation_bridge.h"
#include "b_reload_root_worker_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <cstring>
namespace b_reload_root_activation {
namespace {
using QueryEvent=LONG(NTAPI*)(HANDLE,unsigned,void*,ULONG,ULONG*);
struct EventBasic {LONG type,state;};
struct Worker {uintptr_t object=0,control=0;DWORD thread=0;volatile LONG published=0,running=0,retired=0;std::uint64_t outerCall=0;};
struct Pending {Task data{};b_reload_root_worker_ports::Context ports{};};
struct State {Config c{};Report r{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0,stopped=0,publishClaim=0;Worker workers[8]{};Pending pending[64]{};QueryEvent query=nullptr;};
State global;
thread_local Worker* owner=nullptr;
thread_local Pending* active=nullptr;
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
void fail(Error e,DWORD os=0){AcquireSRWLockExclusive(&global.lock);if(global.r.error==Error::None)global.r.error=e;if(os)global.r.osError=os;ReleaseSRWLockExclusive(&global.lock);}
bool executable(uintptr_t p,size_t n,bool image=true) noexcept {MEMORY_BASIC_INFORMATION m{};return p&&p<=UINTPTR_MAX-n&&VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&(!image||m.Type==MEM_IMAGE)&&(m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY)&&p+n<=uintptr_t(m.BaseAddress)+m.RegionSize;}
bool bytes() noexcept {__try {const auto b=global.c.base;
#ifdef B_RELOAD_ROOT_ACTIVATION_FIXTURE
 const bool image=false;
#else
 const bool image=true;
#endif
 return executable(b+0x834D10,sizeof b_reload_root_worker_profile::RunnerBytes,image)&&executable(b+0x83A930,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes,image)&&
 !memcmp(reinterpret_cast<void*>(b+0x834D10),b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes)&&!memcmp(reinterpret_cast<void*>(b+0x83A930),checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool healthy(){AcquireSRWLockShared(&global.lock);const bool ok=global.r.error==Error::None;ReleaseSRWLockShared(&global.lock);return ok;}
bool iatIdentity() noexcept {__try {MEMORY_BASIC_INFORMATION m{};const auto slot=global.c.base+0x123C0D8;
 if((slot&7)||VirtualQuery(reinterpret_cast<void*>(slot),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||slot+8>uintptr_t(m.BaseAddress)+m.RegionSize)return false;
#ifdef B_RELOAD_ROOT_ACTIVATION_FIXTURE
 // The fixture alone owns a private archived image and a dedicated PE IAT double.
 if(m.Type!=MEM_PRIVATE)return false;
#else
 if(m.Type!=MEM_IMAGE||uintptr_t(m.AllocationBase)!=global.c.base||m.Protect!=PAGE_READONLY)return false;
 const auto expected=uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection"));
 if(!expected||global.r.original!=expected)return false;
#endif
 return at<uintptr_t>(slot)==global.r.original&&executable(global.r.original,1);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool clear(HANDLE event){EventBasic e{};ULONG n=0;return global.query&&global.query(event,0,&e,sizeof e,&n)>=0&&n==sizeof e&&e.type==1&&!e.state;}
bool initialWait(HANDLE h,Worker&w) noexcept {__try {CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL|CONTEXT_INTEGER;if(!GetThreadContext(h,&c))return false;
 for(unsigned i=0;i<40&&c.Rip;++i){if(c.Rip==global.c.base+0x83A9D7)return c.Rbx==w.object+0x38&&c.Rsi==w.object&&c.Rdi==w.control;
  const auto sp=c.Rsp;DWORD64 b=0;auto*f=RtlLookupFunctionEntry(c.Rip,&b,nullptr);if(f){PVOID data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,b,c.Rip,f,&c,&data,&frame,nullptr);}else{c.Rip=at<uintptr_t>(c.Rsp);c.Rsp+=8;}if(c.Rsp<=sp||c.Rsp-sp>0x100000)return false;
 }return false;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool publishWorker(Worker&w) noexcept {HANDLE thread=nullptr,event=nullptr;bool suspended=false,ok=false;Error error=Error::None;
 __try {__try {
  if(get(global.stopped)||!bytes()||w.thread==GetCurrentThreadId()){error=Error::Stopped;__leave;}
  const auto th=reinterpret_cast<HANDLE>(at<uintptr_t>(w.object+0x18)),ev=reinterpret_cast<HANDLE>(at<uintptr_t>(w.object+0x20));
  if(!DuplicateHandle(GetCurrentProcess(),th,GetCurrentProcess(),&thread,THREAD_GET_CONTEXT|THREAD_SUSPEND_RESUME|THREAD_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,0)||GetThreadId(thread)!=w.thread||GetProcessIdOfThread(thread)!=GetCurrentProcessId()||!DuplicateHandle(GetCurrentProcess(),ev,GetCurrentProcess(),&event,0,FALSE,DUPLICATE_SAME_ACCESS)){error=Error::Thread;__leave;}
  const auto prior=SuspendThread(thread);if(prior==DWORD(-1)){error=Error::Thread;__leave;}suspended=true;if(prior){error=Error::Thread;__leave;}
  if(at<uintptr_t>(w.object+0x30)!=w.control||at<uintptr_t>(w.control)!=w.object||at<uintptr_t>(w.object+0x38)!=global.c.base+0x834D10||at<DWORD>(w.control+0x50)!=1||at<DWORD>(w.control+0x54)){error=Error::Binding;__leave;}
  if(!initialWait(thread,w)){error=Error::Wait;__leave;}if(!clear(event)){error=Error::Event;__leave;}
  if(get(global.stopped)){error=Error::Stopped;__leave;}
  if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(w.object+0x38),reinterpret_cast<void*>(&BReloadRootActivationBridge1),reinterpret_cast<void*>(global.c.base+0x834D10))!=reinterpret_cast<void*>(global.c.base+0x834D10)){error=Error::Publish;__leave;}
  InterlockedExchange(&w.published,1);ok=true;AcquireSRWLockExclusive(&global.lock);++global.r.initialWaitVerified;ReleaseSRWLockExclusive(&global.lock);
 }__finally {if(suspended&&ResumeThread(thread)==DWORD(-1)){error=Error::Thread;ok=false;AcquireSRWLockExclusive(&global.lock);global.r.uncertain=1;ReleaseSRWLockExclusive(&global.lock);}if(thread)CloseHandle(thread);if(event)CloseHandle(event);}}
 __except(EXCEPTION_EXECUTE_HANDLER){error=Error::Exception;ok=false;}
 if(error!=Error::None)fail(error,GetLastError());return ok;
}
// Walk the actual current-thread OS CONTEXT through reviewed PE unwind frames.
// No synthesized RIP, register substitutions, return-stack rewrite or CET bypass.
bool nativeCaller(const CheckpointLoadWorkerFrame&f,CONTEXT&c) noexcept {__try {RtlCaptureContext(&c);const auto wanted=at<uintptr_t>(f.caller_entry_rsp);
 for(unsigned i=0;i<40&&c.Rip;++i){if(c.Rip==wanted&&c.Rsp==f.caller_entry_rsp+8)return true;const auto sp=c.Rsp;DWORD64 b=0;auto*entry=RtlLookupFunctionEntry(c.Rip,&b,nullptr);if(entry){PVOID data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,b,c.Rip,entry,&c,&data,&frame,nullptr);}else {c.Rip=at<uintptr_t>(c.Rsp);c.Rsp+=8;}if(c.Rsp<=sp||c.Rsp-sp>0x100000)return false;}return false;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void finishTask(bool abnormal){auto*t=active;if(!t)return;b_reload_root_worker_ports::Finish(t->ports);b_reload_root_worker_ports::Report p{};b_reload_root_worker_ports::Snapshot(t->ports,p);
 AcquireSRWLockExclusive(&global.lock);t->data.ports=p;if(p.uncertain||!p.restored)global.r.uncertain=1;t->data.finished=1;t->data.abnormal=abnormal;global.r.tasks[t-global.pending]=t->data;++global.r.gateFinishes;ReleaseSRWLockExclusive(&global.lock);
 if(p.uncertain||!p.restored||(!abnormal&&p.error!=b_reload_root_worker_ports::Error::None))fail(Error::Ports);active=nullptr;
}
void outerBefore(const CheckpointLoadWorkerFrame*f,void*) {if(!f||owner){fail(Error::Bridge);return;}Worker*chosen=nullptr;
 __try {if(at<uintptr_t>(f->caller_entry_rsp)!=global.c.base+0x83A9DF){fail(Error::Source);return;}
 AcquireSRWLockExclusive(&global.lock);for(unsigned i=0;i<global.r.threads;++i){auto&w=global.workers[i];if(w.object==f->args[0]&&w.control==f->args[1]&&w.thread==GetCurrentThreadId()&&get(w.published)&&!get(w.retired)&&!get(w.running)){chosen=&w;break;}}if(chosen){chosen->outerCall=f->call_id;InterlockedExchange(&chosen->running,1);++global.r.outerBefore;}ReleaseSRWLockExclusive(&global.lock);
 if(!chosen||!BReloadRootActivationClaim(f,std::uint64_t(chosen-global.workers)+1)){fail(Error::Binding);return;}owner=chosen;
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception,GetExceptionCode());}}
void outerFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*) {if(!f||!x||!owner)return;if(owner->outerCall!=f->call_id||f->thread_id!=GetCurrentThreadId()){fail(Error::Binding);return;}finishTask(x->abnormal!=0);AcquireSRWLockExclusive(&global.lock);++global.r.outerFinally;InterlockedExchange(&owner->retired,1);InterlockedExchange(&owner->running,0);ReleaseSRWLockExclusive(&global.lock);owner=nullptr;}
void gateAfter(const CheckpointLoadWorkerFrame*f,void*) {if(!f)return;__try {
 const auto caller=at<uintptr_t>(f->caller_entry_rsp);if(caller!=global.c.base+0x834D88&&caller!=global.c.base+0x834DC8){AcquireSRWLockExclusive(&global.lock);++global.r.unrelated;ReleaseSRWLockExclusive(&global.lock);return;}
 if(!owner)return;CheckpointLoadWorkerOwner proof{};CONTEXT c{};if(!BReloadRootActivationCurrentOwner(&proof)||proof.token!=std::uint64_t(owner-global.workers)+1||proof.thread_id!=GetCurrentThreadId()||proof.call_id!=owner->outerCall||!nativeCaller(*f,c)||c.Rbx!=owner->control||c.Rdi!=owner->object){fail(Error::Source);return;}
 if(caller==global.c.base+0x834DC8){finishTask(false);return;}
 if(active){fail(Error::Conflict);return;}if(!healthy())return;if(get(global.stopped)){fail(Error::Stopped);return;}
 const auto callable=at<uintptr_t>(owner->control+0x48);Pending*chosen=nullptr;AcquireSRWLockExclusive(&global.lock);
 for(unsigned i=0;i<global.r.taskCount;++i){auto&t=global.pending[i];if(!t.data.selected&&!t.data.finished&&t.data.worker+8==owner->control&&t.data.callable==callable&&t.data.object==owner->object&&t.data.thread==GetCurrentThreadId()){if(chosen){chosen=nullptr;break;}chosen=&t;}}
 if(chosen){chosen->data.selected=1;++global.r.gateEntries;}ReleaseSRWLockExclusive(&global.lock);if(!chosen){fail(Error::Binding);return;}
 auto&t=*chosen;const b_reload_root_worker_ports::Config cfg{global.c.provider,global.c.base,t.data.binding,t.data.worker,t.data.callable,t.data.object,t.data.thread,global.c.helperDeadlineMs};
 if(!b_reload_root_worker_ports::Initialize(t.ports,cfg)||!b_reload_root_worker_ports::Begin(t.ports)){
 b_reload_root_worker_ports::Report p{};b_reload_root_worker_ports::Snapshot(t.ports,p);
 AcquireSRWLockExclusive(&global.lock);t.data.ports=p;global.r.tasks[chosen-global.pending]=t.data;if(p.uncertain)global.r.uncertain=1;ReleaseSRWLockExclusive(&global.lock);fail(Error::Ports);return;}active=&t;
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception,GetExceptionCode());}}
}
bool Initialize(const Config&c) noexcept {if(InterlockedCompareExchange(&global.once,1,0)||!c.base||c.base>UINTPTR_MAX-0x2300000||!c.provider||c.helperDeadlineMs<1||c.helperDeadlineMs>10000)return false;global.c=c;
 __try {if(!bytes())return false;global.r.iatSlot=c.base+0x123C0D8;global.r.original=at<uintptr_t>(global.r.iatSlot);global.r.replacement=uintptr_t(&BReloadRootActivationBridge0);if(!iatIdentity()){fail(Error::Source);return false;}
 global.query=reinterpret_cast<QueryEvent>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryEvent"));if(!global.query)return false;
 CheckpointLoadWorkerBridgeConfig gate{};gate.original=reinterpret_cast<void*>(global.r.original);gate.after=gateAfter;if(!BReloadRootActivationBridgeConfigure(0,&gate))return false;
 CheckpointLoadWorkerBridgeConfig outer{};outer.original=reinterpret_cast<void*>(c.base+0x834D10);outer.before=outerBefore;outer.finally=outerFinally;if(!BReloadRootActivationBridgeConfigure(1,&outer))return false;global.r.initialized=1;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception,GetExceptionCode());return false;}}
bool PublishIat() noexcept {if(!global.r.initialized||get(global.stopped)||InterlockedCompareExchange(&global.publishClaim,1,0))return false;DWORD old=0;bool changed=false;
 __try {if(!healthy()||!bytes()||!iatIdentity()){fail(Error::Source);return false;}if(!VirtualProtect(reinterpret_cast<void*>(global.r.iatSlot),8,PAGE_READWRITE,&old))return false;
 __try {changed=InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(global.r.iatSlot),reinterpret_cast<void*>(global.r.replacement),reinterpret_cast<void*>(global.r.original))==reinterpret_cast<void*>(global.r.original);}
 __finally {DWORD unused=0;if(!VirtualProtect(reinterpret_cast<void*>(global.r.iatSlot),8,old,&unused)){global.r.uncertain=1;fail(Error::Publish);}}
 if(changed)global.r.published=1;else fail(Error::Publish);return changed&&!global.r.uncertain;
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception,GetExceptionCode());return false;}}
bool OnCreation(checkpoint_native_task_provider::Provider&p,const Binding&binding,const checkpoint_native_task_provider::Capture&c) noexcept {if(!global.r.initialized)return true;
 if(!healthy())return false;
 if(&p!=global.c.provider||!global.r.published||get(global.stopped)||c.thread!=GetCurrentThreadId()||c.rip!=global.c.base+0x50B598){fail(Error::Binding);return false;}
 __try {checkpoint_native_task_provider::Report b{};if(!p.Snapshot(binding.generation,b)||!b.windowOpen||b.closed||b.error!=checkpoint_native_task_provider::Error::None||b.attempt!=binding.attempt||b.epoch!=binding.epoch){fail(Error::Binding);return false;}
 const auto worker=c.rdi,object=at<uintptr_t>(worker+8),callable=at<uintptr_t>(worker+0x50),state=at<uintptr_t>(at<uintptr_t>(c.rsp+0x40));const auto thread=at<DWORD>(object+0x10);
 if(!worker||!object||!callable||!thread||thread==GetCurrentThreadId()||at<uintptr_t>(state+0x50)!=worker||at<uintptr_t>(callable)!=global.c.base+0x12F2440||at<uintptr_t>(global.c.base+0x12F2440+0x10)!=global.c.base+0x50B730){fail(Error::Binding);return false;}
 Worker*w=nullptr;bool fresh=false;AcquireSRWLockExclusive(&global.lock);
 if(global.r.taskCount>=64){ReleaseSRWLockExclusive(&global.lock);fail(Error::Capacity);return false;}
 for(unsigned i=0;i<global.r.threads;++i)if(global.workers[i].object==object&&global.workers[i].control==worker+8&&global.workers[i].thread==thread){w=&global.workers[i];break;}
 if(!w&&global.r.threads<8){w=&global.workers[global.r.threads++];w->object=object;w->control=worker+8;w->thread=thread;fresh=true;}
 if(!w){ReleaseSRWLockExclusive(&global.lock);fail(Error::Capacity);return false;}
 for(unsigned i=0;i<global.r.taskCount;++i){const auto&t=global.pending[i].data;if(!t.selected&&!t.finished&&(t.worker==worker||t.callable==callable)){ReleaseSRWLockExclusive(&global.lock);fail(Error::Conflict);return false;}}
 auto&t=global.pending[global.r.taskCount];t.data.binding=binding;t.data.worker=worker;t.data.callable=callable;t.data.object=object;t.data.state=state;t.data.thread=thread;global.r.tasks[global.r.taskCount]=t.data;++global.r.taskCount;ReleaseSRWLockExclusive(&global.lock);
 if(fresh)return publishWorker(*w);
 if(!get(w->published)||!get(w->running)||get(w->retired)||at<uintptr_t>(object+0x38)!=uintptr_t(&BReloadRootActivationBridge1)){fail(Error::Binding);return false;}return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception,GetExceptionCode());return false;}}
void Stop() noexcept {InterlockedExchange(&global.stopped,1);}
bool Snapshot(Report&r) noexcept {AcquireSRWLockShared(&global.lock);r=global.r;ReleaseSRWLockShared(&global.lock);return r.initialized!=0;}
}
