// Only compiled into the owned test DLL. No runtime archive reconstruction in production.
#include "b_reload_lifecycle_profile.h"
#include "b_reload_root_worker_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <cstring>
static uintptr_t ownedBase=0;
static unsigned ownedFailures=0,ownedConstructed=0;
static volatile LONG ownedBodies=0;
static unsigned char ownedManager[0x200]{},ownedCounter[0x100]{};
struct OwnedWorker {uintptr_t control=0;unsigned char object[0x300]{},callable[0x80]{},state[0x100]{},vtable[0x80]{};uintptr_t slot=0,chain=0;HANDLE ready=nullptr,done=nullptr,initial=nullptr,thread=nullptr;DWORD tid=0;};
static OwnedWorker ownedWorkers[4];
static void require(bool x,const char*m){if(!x){++ownedFailures;printf("FAIL %s os=%lu\n",m,GetLastError());fflush(stdout);ExitProcess(94);}}
template<class T>static void put(uintptr_t a,T v){*reinterpret_cast<T*>(a)=v;}
template<class T>static T at(uintptr_t a){return *reinterpret_cast<T*>(a);}
static bool span(uintptr_t r,const void*p,size_t n,DWORD protection){DWORD old=0,unused=0;auto a=ownedBase+r;MEMORY_BASIC_INFORMATION m{};if(!VirtualQuery(reinterpret_cast<void*>(a),&m,sizeof m)||m.Type!=MEM_IMAGE||uintptr_t(m.AllocationBase)!=ownedBase)return false;
if(!VirtualProtect(reinterpret_cast<void*>(a),n,PAGE_READWRITE,&old))return false;memcpy(reinterpret_cast<void*>(a),p,n);return VirtualProtect(reinterpret_cast<void*>(a),n,protection,&unused)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(a),n);}
static bool jump(uintptr_t r,uintptr_t target){unsigned char b[14]={0xff,0x25,0,0,0,0};memcpy(b+6,&target,8);return span(r,b,sizeof b,PAGE_EXECUTE_READ);}
static void cookie(uintptr_t value){if(value!=at<uintptr_t>(ownedBase+0x1923f90))RaiseException(0xE014BA01,EXCEPTION_NONCONTINUABLE,0,nullptr);}
static void threadExit(unsigned){} // Owned thread-entry CRT service; outer thread wrapper returns normally.
static DWORD ownedWait(HANDLE h,DWORD ms){for(auto&w:ownedWorkers)if(w.ready==h&&w.tid==GetCurrentThreadId())SetEvent(w.initial);return WaitForSingleObject(h,ms);}
static DWORD WINAPI ownedEntry(void*p){auto&w=*static_cast<OwnedWorker*>(p);return reinterpret_cast<DWORD(*)(void*)>(ownedBase+0x83A930)(w.object);}
static uintptr_t status(){return 0;}
static uintptr_t business(uintptr_t self,uintptr_t a,uintptr_t b,uintptr_t c){require(self==uintptr_t(ownedWorkers[0].state)&&a==11&&b==22&&c==33,"actual archived thunk business args");InterlockedIncrement(&ownedBodies);return 17;}
static void constructor(uintptr_t control,uintptr_t callable,uintptr_t name,uintptr_t flags){const auto i=ownedConstructed++;require(i<4&&control==ownedBase+0x1A24DA0+0x10+uintptr_t(i)*0x80&&!callable&&name&&!flags,"four exact constructor sites");if(i>=4)RaiseException(0xE014BA02,EXCEPTION_NONCONTINUABLE,0,nullptr);auto&w=ownedWorkers[i];w.control=control;
 w.ready=CreateEventW(nullptr,FALSE,FALSE,nullptr);w.done=CreateEventW(nullptr,TRUE,TRUE,nullptr);w.initial=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(w.object+0x110));
 put<uintptr_t>(control,uintptr_t(w.object));put<uintptr_t>(control+8,uintptr_t(w.object)+0x100);put<uintptr_t>(control+0x48,uintptr_t(w.callable));put<DWORD>(control+0x50,1);put<uintptr_t>(control+0x60,uintptr_t(w.done));put<DWORD>(control+0x68,1);
 put<uintptr_t>(uintptr_t(w.object)+0x20,uintptr_t(w.ready));put<uintptr_t>(uintptr_t(w.object)+0x30,control);put<uintptr_t>(uintptr_t(w.object)+0x38,ownedBase+0x834D10);put<DWORD>(uintptr_t(w.object)+8,2);
 w.thread=CreateThread(nullptr,0,ownedEntry,&w,CREATE_SUSPENDED,&w.tid);require(w.thread!=nullptr,"create own worker");put<DWORD>(uintptr_t(w.object)+0x10,w.tid);put<uintptr_t>(uintptr_t(w.object)+0x18,uintptr_t(w.thread));
 require(ResumeThread(w.thread)==1&&WaitForSingleObject(w.initial,3000)==WAIT_OBJECT_0,"constructor waits for actual initial native wait");
}
static bool ownedPrepare(uintptr_t b){ownedBase=b;printf("PREP begin\n");fflush(stdout);
 // Verify every occupied range is within the exported owned section, not PE/CRT/unwind.
 auto start=uintptr_t(GetProcAddress(GetModuleHandleW(nullptr),"BReloadBootstrapWorkersSpace"));if(!start||start>b+0x144000||start+0x2400000<b+0x2301000)return false;
 printf("PREP range\n");fflush(stdout);
 struct Span{uintptr_t r;const unsigned char*p;size_t n;};const Span s[]={{0x1447B6,b_reload_lifecycle_profile::InitCall,sizeof b_reload_lifecycle_profile::InitCall},{0x509580,b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes},{0x834D10,b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes},{0x50B730,b_reload_root_worker_profile::ThunkBytes,sizeof b_reload_root_worker_profile::ThunkBytes},{0x50B690,b_reload_root_worker_profile::YieldBytes,sizeof b_reload_root_worker_profile::YieldBytes},{0x83A930,checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes}};
 for(const auto&x:s)if(!span(x.r,x.p,x.n,PAGE_EXECUTE_READ))return false;
 const unsigned char head[]={0x48,0x83,0xec,0x28},tail[]={0x48,0x83,0xc4,0x28,0xc3};if(!span(0x1447B2,head,4,PAGE_EXECUTE_READ)||!span(0x1447BB,tail,5,PAGE_EXECUTE_READ))return false;
 printf("PREP bytes\n");fflush(stdout);
 const unsigned char initUnwind[]={1,0x14,8,0,0x14,0xd2,0x10,0x70,0x0f,0x64,0x13,0,0x0b,0x54,0x12,0,0x07,0x34,0x11,0},caller[]={1,4,1,0,4,0x42,0,0},runner[]={1,10,4,0,10,0x32,6,0x70,5,0x34,6,0},thread[]={1,12,4,0,12,0x72,8,0x70,7,0x60,6,0x30},thunk[]={1,0x14,8,0,0x14,0x32,0x10,0x70,0x0f,0x64,8,0,0x0a,0x54,7,0,5,0x34,6,0};
 if(!span(0x2300000,caller,sizeof caller,PAGE_READONLY)||!span(0x2300040,initUnwind,sizeof initUnwind,PAGE_READONLY)||!span(0x2300080,thunk,sizeof thunk,PAGE_READONLY)||!span(0x23000c0,runner,sizeof runner,PAGE_READONLY)||!span(0x2300100,thread,sizeof thread,PAGE_READONLY))return false;
 static RUNTIME_FUNCTION functions[]={{0x1447B2,0x1447C0,0x2300000},{0x509580,0x509639,0x2300040},{0x50B730,0x50B79A,0x2300080},{0x834D10,0x834E75,0x23000c0},{0x83A930,0x83AA2D,0x2300100}};
 printf("PREP unwind\n");fflush(stdout);
 // The host has these exact entries in its static PE exception directory.
 for(const auto&f:functions){DWORD64 image=0;auto*found=RtlLookupFunctionEntry(b+f.BeginAddress,&image,nullptr);if(!found||image!=b||memcmp(found,&f,sizeof f)){printf("LOOKUP expected=%lx actual=%lx image_match=%d\n",f.BeginAddress,found?found->BeginAddress:0,image==b);fflush(stdout);return false;}}
 printf("PREP lookup\n");fflush(stdout);
 if(!jump(0x833CB0,uintptr_t(&constructor))||!jump(0xef9f20,uintptr_t(&cookie))||!jump(0xf31158,uintptr_t(&threadExit)))return false;
 DWORD old=0;if(!VirtualProtect(reinterpret_cast<void*>(b+0x1A24DA0),0x210,PAGE_READWRITE,&old)||!VirtualProtect(reinterpret_cast<void*>(b+0x2025200),0x1000,PAGE_READWRITE,&old))return false;
 printf("PREP data\n");fflush(stdout);
 InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90));InitializeCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(ownedCounter+0x10));
 put<uintptr_t>(b+0x2025F50,uintptr_t(ownedManager));put<uintptr_t>(b+0x2025268,uintptr_t(ownedCounter));
 const uintptr_t enter=uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"EnterCriticalSection")),leave=uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection")),set=uintptr_t(&SetEvent),wait=uintptr_t(&ownedWait);
 if(!enter||!leave||!span(0x123C328,&enter,8,PAGE_READONLY)||!span(0x123C0D8,&leave,8,PAGE_READONLY)||!span(0x123C1D8,&set,8,PAGE_READONLY)||!span(0x123C1E0,&wait,8,PAGE_READONLY))return false;
 printf("PREP IAT\n");fflush(stdout);
 auto&w=ownedWorkers[0];w.slot=uintptr_t(w.state);w.chain=uintptr_t(&w.slot);put<uintptr_t>(uintptr_t(w.callable),uintptr_t(w.vtable));put<uintptr_t>(uintptr_t(w.vtable)+0x10,b+0x50B730);put<uintptr_t>(uintptr_t(w.vtable)+0x28,uintptr_t(&business));put<uintptr_t>(uintptr_t(w.vtable)+0x30,uintptr_t(&status));put<uintptr_t>(uintptr_t(w.state),uintptr_t(w.vtable));put<uintptr_t>(uintptr_t(w.callable)+8,uintptr_t(&w.chain));put<uintptr_t>(uintptr_t(w.callable)+16,11);put<uintptr_t>(uintptr_t(w.callable)+24,22);put<uintptr_t>(uintptr_t(w.callable)+32,33);
 // Demand-zero MEM_IMAGE pages initially report WRITECOPY until materialized.
 // Establish the artificial empty pool before Bootstrap, then recheck exact RW.
 for(unsigned i=0;i<4;++i)*reinterpret_cast<volatile uintptr_t*>(b+0x1A24DA0+0x10+i*0x80)=0;
 for(unsigned i=0;i<4;++i){MEMORY_BASIC_INFORMATION m{};const auto p=b+0x1A24DA0+0x10+i*0x80;if(!VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)||m.Type!=MEM_IMAGE||m.Protect!=PAGE_READWRITE||at<uintptr_t>(p))return false;}

 return true;
}
static DWORD ownedRun(){b_reload_bootstrap::Report initial{};b_reload_lifecycle::Report l{};b_reload_root_activation::Report a{};b_reload_bootstrap_workers::Snapshot(initial,l,a);
 require(initial.attempts==1&&initial.armed&&!initial.uncertain&&!a.threads,"single actual armed bootstrap before main");unsigned char call[5]{};memcpy(call,reinterpret_cast<void*>(ownedBase+0x1447B6),5);const auto iat=at<uintptr_t>(ownedBase+0x123C0D8);
 reinterpret_cast<void(*)(uintptr_t)>(ownedBase+0x1447B2)(ownedBase+0x1A24DA0);
 b_reload_bootstrap::Report b{};b_reload_bootstrap_workers::Snapshot(b,l,a);require(ownedConstructed==4&&a.threads==4&&a.initialWaitVerified==4&&l.entered==1&&l.returned==1&&l.finally==1&&l.error==b_reload_lifecycle::Error::None,"actual bootstrap to cold worker registration");
 auto&w=ownedWorkers[0];ResetEvent(w.initial);ResetEvent(w.done);SetEvent(w.ready);require(WaitForSingleObject(w.done,3000)==WAIT_OBJECT_0&&WaitForSingleObject(w.initial,3000)==WAIT_OBJECT_0,"ordinary native task completes and returns to wait");
 b_reload_bootstrap_workers::Snapshot(b,l,a);require(ownedBodies==1&&l.unownedTasks==1&&!a.taskCount&&!a.gateEntries&&!a.gateFinishes,"one unregistered task transparent without Provider ticket");
 for(auto&x:ownedWorkers){put<DWORD>(x.control+0x54,1);SetEvent(x.ready);}for(auto&x:ownedWorkers)require(WaitForSingleObject(x.thread,3000)==WAIT_OBJECT_0,"all four workers exit normally");
 b_reload_bootstrap_workers::Snapshot(b,l,a);require(a.error==b_reload_root_activation::Error::None&&!a.uncertain&&a.outerBefore==4&&a.outerFinally==4&&l.entered==1&&l.returned==1&&l.finally==1&&l.coldPools==1&&l.unownedTasks==1,"single lifecycle and four real outer FINALLY");
 require(b.attempts==1&&b.armed&&!memcmp(call,reinterpret_cast<void*>(ownedBase+0x1447B6),5)&&iat==at<uintptr_t>(ownedBase+0x123C0D8)&&ownedBase==uintptr_t(GetModuleHandleW(nullptr)),"same main PE and published call/IAT unchanged");
 require(!memcmp(reinterpret_cast<void*>(ownedBase+0x509580),b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes)&&!memcmp(reinterpret_cast<void*>(ownedBase+0x834D10),b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes)&&!memcmp(reinterpret_cast<void*>(ownedBase+0x83A930),checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes)&&!memcmp(reinterpret_cast<void*>(ownedBase+0x50B730),b_reload_root_worker_profile::ThunkBytes,sizeof b_reload_root_worker_profile::ThunkBytes),"archived sources unchanged after normal shutdown");
 require(at<uintptr_t>(ownedBase+0x123C328)==uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"EnterCriticalSection")),"real Enter IAT unchanged");
 for(auto&x:ownedWorkers){DWORD exit=99;require(GetExitCodeThread(x.thread,&exit)&&!exit,"actual worker returns zero");auto*cs=reinterpret_cast<CRITICAL_SECTION*>(x.object+0x110);require(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"worker completion critical section balanced");LeaveCriticalSection(cs);DeleteCriticalSection(cs);CloseHandle(x.thread);CloseHandle(x.initial);CloseHandle(x.done);CloseHandle(x.ready);}
 for(auto*cs:{reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90),reinterpret_cast<CRITICAL_SECTION*>(ownedCounter+0x10)}){require(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"global critical section balanced");LeaveCriticalSection(cs);DeleteCriticalSection(cs);}
 require(at<DWORD>(ownedBase+0x2025270)==0,"task counter returned to zero");
 printf("{\"workers_composed\":true,\"passed\":%s,\"failures\":%u,\"cold_workers\":%u,\"ordinary_bodies\":%ld,\"unowned_tasks\":%u,\"outer_finally\":%u,\"activation_error\":%u,\"lifecycle_error\":%u,\"actual_system_critical_sections\":true,\"same_main_pe\":true,\"same_provider\":true,\"game_access\":false}\n",ownedFailures?"false":"true",ownedFailures,a.initialWaitVerified,ownedBodies,l.unownedTasks,a.outerFinally,unsigned(a.error),unsigned(l.error));fflush(stdout);return ownedFailures?1:0;
}
