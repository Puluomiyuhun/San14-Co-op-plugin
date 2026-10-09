"""Own generated composition only; frozen queue and registration stay unchanged."""
from pathlib import Path
import importlib.util
P=Path(__file__).resolve().parent
def module(name,file):
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def once(s,a,b):
 if s.count(a)!=1:raise RuntimeError('one exact anchor required: '+a[:100])
 return s.replace(a,b,1)
def fixture_sources():
 old=module('cold_bootstrap_queue_transform','b_reload_bootstrap_queue_transform.py')
 cpp,asm,machine,ports,layout,unwind=old.fixture_sources()
 cpp=cpp.replace('#include "b_reload_bootstrap_queue.h"','#include "b_reload_cold_bootstrap.h"').replace('#include "b_reload_bootstrap_queue_owned.inc"','#include "b_reload_cold_bootstrap_owned.inc"')
 cpp=cpp.replace('b_reload_bootstrap_queue::','b_reload_cold_bootstrap::').replace('b_reload_bootstrap::','b_reload_cold_bootstrap::')
 ports=ports.replace('b_reload_bootstrap_queue::','b_reload_cold_bootstrap::').replace('b_reload_bootstrap::','b_reload_cold_bootstrap::')
 ports=once(ports,'static auto& provider=runtime.Provider();','static auto& provider=runtime.Provider();\nstatic SRWLOCK coldProducerLock=SRWLOCK_INIT;static volatile LONG coldTaskStarts=0;')
 ports=once(ports,'static void lifecycleCtor(','''static DWORD WINAPI coldUnifiedEntry(void*p){return p==&activatedQueue.task?activatedEntry(nullptr):lifecycleEntry(p);}
static void lifecycleCtor(''')
 ports=once(ports,'i?lifecycleEntry:activatedEntry,i?&t:nullptr','coldUnifiedEntry,&t')
 ports=once(ports,'boundRequire(ResumeThread(h)!=DWORD(-1)&&WaitForSingleObject(lifecycleInitial[i],10000)==WAIT_OBJECT_0,"constructor double waits for actual native initial wait");','boundRequire(ResumeThread(h)!=DWORD(-1),"resume cold thread without initial wait");if(i==3)Sleep(30);')
 ports=once(ports,'static void lifecyclePrepare(){if(lifecyclePrepared)return;lifecyclePrepared=true;', '''static HANDLE coldManagerHeld=nullptr;
static DWORD WINAPI coldDelayManager(void*){auto*cs=reinterpret_cast<CRITICAL_SECTION*>(at<uintptr_t>(base+0x2025F50)+0x90);EnterCriticalSection(cs);SetEvent(coldManagerHeld);Sleep(200);LeaveCriticalSection(cs);return 0;}
static void lifecyclePrepare(){if(lifecyclePrepared)return;lifecyclePrepared=true;
 coldManagerHeld=CreateEventW(nullptr,TRUE,FALSE,nullptr);auto delay=CreateThread(nullptr,0,coldDelayManager,nullptr,0,nullptr);boundRequire(delay&&WaitForSingleObject(coldManagerHeld,3000)==WAIT_OBJECT_0,"owned manager blocks four native entries");''')
 ports=once(ports,'boundRequire(lifecycleConstructed==4,"same primary image created four workers once");}', '''boundRequire(lifecycleConstructed==4,"same primary image created four workers once");
 boundRequire(WaitForSingleObject(delay,3000)==WAIT_OBJECT_0,"owned manager holder exits");CloseHandle(delay);CloseHandle(coldManagerHeld);coldManagerHeld=nullptr;
 const auto&cold=b_reload_cold_registration::Snapshot();boundRequire(cold.error==b_reload_cold_registration::Error::None&&cold.oldCalls==1&&cold.registered==1&&cold.provider==uintptr_t(&provider)&&cold.base==base&&cold.wait.pending&&cold.wait.initialWaitVerified==4&&cold.wait.suspends==cold.wait.resumes&&!cold.wait.uncertain,"actual cold coordination and original Register once before queue");
 // Explicit owned engine-service transition AFTER production cold registration.
 // Queue fixture needs its preexisting completion bookkeeping; no production
 // source check is weakened and the activation Leave bridge remains installed.
 DWORD old=0;boundRequire(VirtualProtect(reinterpret_cast<void*>(base+0x123C1D8),8,PAGE_READWRITE,&old)!=FALSE,"owned Set service writable");put<uintptr_t>(base+0x123C1D8,uintptr_t(&activatedSet));DWORD unused=0;boundRequire(VirtualProtect(reinterpret_cast<void*>(base+0x123C1D8),8,old,&unused)!=FALSE,"owned Set service protection restored");
}''')
 return cpp,asm,machine,ports,layout,unwind
