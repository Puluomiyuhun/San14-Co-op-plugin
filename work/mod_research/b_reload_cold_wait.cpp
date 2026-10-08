#include "b_reload_cold_wait.h"
#include "b_reload_root_worker_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <cstring>
namespace b_reload_cold_wait { namespace {
using QueryEvent=LONG(NTAPI*)(HANDLE,unsigned,void*,ULONG,ULONG*);
using QueryThread=LONG(NTAPI*)(HANDLE,unsigned,void*,ULONG,ULONG*);
using CompareHandles=BOOL(WINAPI*)(HANDLE,HANDLE);
struct EventBasic {LONG type,state;};
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool executable(uintptr_t p,size_t n,uintptr_t image=0){MEMORY_BASIC_INFORMATION m{};return p&&p<=UINTPTR_MAX-n&&VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==MEM_IMAGE&&(!image||uintptr_t(m.AllocationBase)==image)&&(m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY)&&p+n<=uintptr_t(m.BaseAddress)+m.RegionSize;}
bool source(uintptr_t b){return b==uintptr_t(GetModuleHandleW(nullptr))&&executable(b+0x834D10,sizeof b_reload_root_worker_profile::RunnerBytes,b)&&executable(b+0x83A930,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes,b)&&!memcmp(reinterpret_cast<void*>(b+0x834D10),b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes)&&!memcmp(reinterpret_cast<void*>(b+0x83A930),checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes);}
bool imports(uintptr_t b,uintptr_t wait){
 const uintptr_t slots[]={0x123C328,0x123C0D8,0x123C1D8,0x123C1E0};
 const uintptr_t values[]={uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"EnterCriticalSection")),uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection")),uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"SetEvent")),wait};
 for(unsigned i=0;i<4;++i){MEMORY_BASIC_INFORMATION m{};const auto p=b+slots[i];if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||m.Type!=MEM_IMAGE||uintptr_t(m.AllocationBase)!=b||m.Protect!=PAGE_READONLY||p+8>uintptr_t(m.BaseAddress)+m.RegionSize||!executable(values[i],1)||at<uintptr_t>(p)!=values[i])return false;}
 // Wait is pinned, not behaviorally attested. A production caller must supply a
 // trusted source environment; an executable imported service is not a fence.
 return true;
}
enum class Position {Initial,Pending,Warm,Invalid};
Position position(HANDLE h,const Worker&w,uintptr_t base,uintptr_t&rip){CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL|CONTEXT_INTEGER;if(!GetThreadContext(h,&c))return Position::Invalid;bool entry=false;
 for(unsigned i=0;i<40&&c.Rip;++i){rip=c.Rip;
  if(c.Rip==base+0x83A9D7)return c.Rbx==w.object+0x38&&c.Rsi==w.object&&c.Rdi==w.control?Position::Initial:Position::Invalid;
  if(c.Rip>=base+0x834D10&&c.Rip<base+0x834E75)return Position::Warm;
  if(c.Rip>=base+0x83A930&&c.Rip<base+0x83AA2D){if(c.Rip>base+0x83A9D7)return Position::Warm;entry=true;}
  const auto sp=c.Rsp;DWORD64 image=0;auto*f=RtlLookupFunctionEntry(c.Rip,&image,nullptr);
  if(f){PVOID data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,image,c.Rip,f,&c,&data,&frame,nullptr);}else{c.Rip=at<uintptr_t>(c.Rsp);c.Rsp+=8;}
  if(c.Rsp<=sp||c.Rsp-sp>0x100000)return Position::Invalid;
 }return entry?Position::Pending:Position::Invalid;
}
}
bool Coordinator::Run(const Config&c,Continuation continuation,void*context) noexcept {
 if(InterlockedCompareExchange(&once_,1,0))return false;
 report_.attempts=1;auto fail=[&](Error e){if(report_.error==Error::None){report_.error=e;report_.osError=GetLastError();}};
 if(!c.base||c.base>UINTPTR_MAX-0x2400000||!c.producerLock||!c.taskStarts||!continuation||c.deadlineMs<1||c.deadlineMs>10000||c.pollMs<1||c.pollMs>100){fail(Error::Config);return false;}
 HANDLE threads[4]{},events[4]{},originalThreads[4]{},originalEvents[4]{};bool suspended[4]{},locked=false,ok=false;const auto start=GetTickCount64();
 auto resume=[&](){bool good=true;for(unsigned i=0;i<4;++i)if(suspended[i]){const auto old=ResumeThread(threads[i]);suspended[i]=false;if(old==DWORD(-1)){report_.uncertain=1;fail(Error::Resume);good=false;}else{++report_.resumes;if(old!=1){fail(Error::Thread);good=false;}}}return good;};
 __try {__try {
  // Never block indefinitely waiting for a producer holding the shared lock.
  while(!TryAcquireSRWLockExclusive(c.producerLock)){if(GetTickCount64()-start>=c.deadlineMs){fail(Error::Deadline);__leave;}Sleep(c.pollMs);}locked=true;
  auto qe=reinterpret_cast<QueryEvent>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryEvent"));auto qt=reinterpret_cast<QueryThread>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"NtQueryInformationThread"));
  auto compare=reinterpret_cast<CompareHandles>(GetProcAddress(GetModuleHandleW(L"kernelbase.dll"),"CompareObjectHandles"));
  if(!qe||!qt||!compare||!source(c.base)){fail(Error::Source);__leave;}
  report_.waitService=at<uintptr_t>(c.base+0x123C1E0);
  if(!imports(c.base,report_.waitService)){fail(Error::Source);__leave;}
  for(unsigned i=0;i<4;++i){const auto&w=c.workers[i];if(!w.object||!w.control||!w.thread||w.thread==GetCurrentThreadId()||!executable(w.threadStart,1)){fail(Error::Binding);__leave;}
   for(unsigned j=0;j<i;++j)if(w.object==c.workers[j].object||w.control==c.workers[j].control||w.thread==c.workers[j].thread){fail(Error::Binding);__leave;}
   if(report_.error!=Error::None)__leave;
   originalThreads[i]=reinterpret_cast<HANDLE>(at<uintptr_t>(w.object+0x18));originalEvents[i]=reinterpret_cast<HANDLE>(at<uintptr_t>(w.object+0x20));
   if(!DuplicateHandle(GetCurrentProcess(),originalThreads[i],GetCurrentProcess(),&threads[i],THREAD_GET_CONTEXT|THREAD_SUSPEND_RESUME|THREAD_QUERY_INFORMATION|SYNCHRONIZE,FALSE,0)||GetThreadId(threads[i])!=w.thread||GetProcessIdOfThread(threads[i])!=GetCurrentProcessId()||!DuplicateHandle(GetCurrentProcess(),originalEvents[i],GetCurrentProcess(),&events[i],0,FALSE,DUPLICATE_SAME_ACCESS)){fail(Error::Thread);__leave;}
   uintptr_t actual=0;if(qt(threads[i],9,&actual,sizeof actual,nullptr)<0||actual!=w.threadStart){fail(Error::Source);__leave;}
  }
  if(report_.error!=Error::None)__leave;
  for(;;){++report_.rounds;unsigned initial=0;
   if(!source(c.base)||!imports(c.base,report_.waitService)){fail(Error::Source);break;}
   if(InterlockedCompareExchange(c.taskStarts,0,0)){fail(Error::TaskStarted);break;}
   for(unsigned i=0;i<4;++i){const auto prior=SuspendThread(threads[i]);if(prior==DWORD(-1)){fail(Error::Thread);break;}suspended[i]=true;++report_.suspends;if(prior){fail(Error::Thread);break;}}
   if(report_.error==Error::None)for(unsigned i=0;i<4;++i){const auto&w=c.workers[i];
    if(WaitForSingleObject(threads[i],0)!=WAIT_TIMEOUT||at<uintptr_t>(w.object+0x18)!=uintptr_t(originalThreads[i])||at<uintptr_t>(w.object+0x20)!=uintptr_t(originalEvents[i])||!compare(originalThreads[i],threads[i])||!compare(originalEvents[i],events[i])||at<DWORD>(w.object+0x10)!=w.thread||at<uintptr_t>(w.object+0x30)!=w.control||at<uintptr_t>(w.control)!=w.object||at<uintptr_t>(w.object+0x38)!=c.base+0x834D10||at<DWORD>(w.control+0x50)!=1||at<DWORD>(w.control+0x54)){fail(Error::Binding);break;}
    const auto p=position(threads[i],w,c.base,report_.lastRip[i]);
    if(p==Position::Warm){report_.warm[i]=1;fail(Error::Warm);break;}if(p==Position::Invalid){fail(Error::Context);break;}
    EventBasic eb{};ULONG n=0;if(qe(events[i],0,&eb,sizeof eb,&n)<0||n!=sizeof eb||eb.type!=1||eb.state){fail(Error::Event);break;}
    if(p==Position::Initial)++initial;else ++report_.pending;
   }
   if(!resume()||report_.error!=Error::None)break;
   if(InterlockedCompareExchange(c.taskStarts,0,0)){fail(Error::TaskStarted);break;}
   if(GetTickCount64()-start>=c.deadlineMs){fail(Error::Deadline);break;}
   if(initial==4){report_.initialWaitVerified=initial;++report_.callbackCalls;ok=continuation(context);if(!ok)fail(Error::Callback);break;}
   Sleep(c.pollMs);
  }
 }__finally {if(!resume())ok=false;for(unsigned i=0;i<4;++i){if(events[i])CloseHandle(events[i]);if(threads[i])CloseHandle(threads[i]);}if(locked)ReleaseSRWLockExclusive(c.producerLock);}}
 __except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception);report_.osError=GetExceptionCode();ok=false;}
 report_.elapsedMs=GetTickCount64()-start;return ok&&report_.error==Error::None&&!report_.uncertain;
}
}
