// Explicit Bootstrap successor: same validations, one coordinated Prepare.
#include "b_reload_cold_bootstrap.h"
#include "b_reload_lifecycle_profile.h"
#include "b_reload_root_worker_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <tlhelp32.h>
#include <cstring>
namespace b_reload_cold_bootstrap {
namespace {SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0;Report report;
void fail(Error e){if(report.error==Error::None)report.error=e;report.osError=GetLastError();}
bool page(uintptr_t base,uintptr_t p,size_t n,DWORD protection){MEMORY_BASIC_INFORMATION m{};return p<=UINTPTR_MAX-n&&VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==MEM_IMAGE&&uintptr_t(m.AllocationBase)==base&&p+n<=uintptr_t(m.BaseAddress)+m.RegionSize&&m.Protect==protection;}
bool entry(const BReloadLifecycleBootstrapInfo&i){__try {
 if(i.size!=sizeof i||i.version!=1||i.reserved||i.pid!=GetCurrentProcessId()||!i.primaryThread||i.primaryThread==GetCurrentThreadId()||i.imageBase!=uintptr_t(GetModuleHandleW(nullptr))||i.entryByte>255)return false;
 const auto*b=reinterpret_cast<const BYTE*>(i.imageBase);const auto*d=reinterpret_cast<const IMAGE_DOS_HEADER*>(b);if(d->e_magic!=IMAGE_DOS_SIGNATURE||d->e_lfanew<=0||d->e_lfanew>0x100000)return false;const auto*n=reinterpret_cast<const IMAGE_NT_HEADERS64*>(b+d->e_lfanew);
 return n->Signature==IMAGE_NT_SIGNATURE&&n->FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64&&n->OptionalHeader.Magic==IMAGE_NT_OPTIONAL_HDR64_MAGIC&&n->OptionalHeader.SizeOfImage>=0x2300000&&i.entryPoint==i.imageBase+n->OptionalHeader.AddressOfEntryPoint&&page(i.imageBase,i.entryPoint,1,PAGE_EXECUTE_READ)&&*reinterpret_cast<const BYTE*>(i.entryPoint)==i.entryByte;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool threads(DWORD main){HANDLE h=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(h==INVALID_HANDLE_VALUE)return false;THREADENTRY32 e{};e.dwSize=sizeof e;unsigned foundMain=0,foundSelf=0;bool ok=true;for(BOOL more=Thread32First(h,&e);more;more=Thread32Next(h,&e))if(e.th32OwnerProcessID==GetCurrentProcessId()){if(e.th32ThreadID==main)++foundMain;else if(e.th32ThreadID==GetCurrentThreadId())++foundSelf;else ok=false;}const auto finalError=GetLastError();CloseHandle(h);return ok&&finalError==ERROR_NO_MORE_FILES&&foundMain==1&&foundSelf==1;}
bool sources(uintptr_t b){__try {
 struct Span{uintptr_t rva;const unsigned char*p;size_t n;};const Span spans[]={
 {0x1447B6,b_reload_lifecycle_profile::InitCall,sizeof b_reload_lifecycle_profile::InitCall},
 {0x509580,b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes},
 {0x834D10,b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes},
 {0x50B730,b_reload_root_worker_profile::ThunkBytes,sizeof b_reload_root_worker_profile::ThunkBytes},
 {0x50B690,b_reload_root_worker_profile::YieldBytes,sizeof b_reload_root_worker_profile::YieldBytes},
 {0x83A930,checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes}};
 for(const auto&s:spans)if(!page(b,b+s.rva,s.n,PAGE_EXECUTE_READ)||memcmp(reinterpret_cast<const void*>(b+s.rva),s.p,s.n))return false;
 const auto slot=b+0x123C0D8;const auto original=GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection");return original&&page(b,slot,8,PAGE_READONLY)&&*reinterpret_cast<const uintptr_t*>(slot)==uintptr_t(original);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool empty(uintptr_t b){__try{for(unsigned i=0;i<4;++i){const auto p=b+0x1A24DA0+0x10+uintptr_t(i)*0x80;if(!page(b,p,8,PAGE_READWRITE)||*reinterpret_cast<const uintptr_t*>(p))return false;}return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
}
bool InitializeAndArm(const BReloadLifecycleBootstrapInfo&i,checkpoint_native_task_provider::Provider&provider,const b_reload_cold_registration::Policy&policy)noexcept {
 if(InterlockedCompareExchange(&once,1,0))return false;AcquireSRWLockExclusive(&lock);HANDLE primary=nullptr;bool held=false,ok=false;
 __try {__try {
 ++report.attempts;report.image=i.imageBase;report.primary=i.primaryThread;if(!entry(i)){fail(Error::Metadata);__leave;}
 primary=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_LIMITED_INFORMATION|THREAD_SUSPEND_RESUME,FALSE,i.primaryThread);if(!primary||GetProcessIdOfThread(primary)!=GetCurrentProcessId()){fail(Error::Primary);__leave;}
 const auto prior=SuspendThread(primary);if(prior==DWORD(-1)){fail(Error::Primary);__leave;}held=true;if(prior!=1){fail(Error::Primary);__leave;}CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL;if(!GetThreadContext(primary,&c)||c.Rip!=i.entryPoint){fail(Error::Primary);__leave;}report.primaryHeld=1;
 if(!threads(i.primaryThread)){fail(Error::Threads);__leave;}report.threadSetVerified=1;
 if(!sources(i.imageBase)){fail(Error::Source);__leave;}report.sourcesReady=1;if(!empty(i.imageBase)){fail(Error::Pool);__leave;}
 HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&InitializeAndArm),&pinned)){fail(Error::Pin);__leave;}report.modulePinned=1;
 if(!b_reload_cold_registration::Prepare({i.imageBase,&provider,1000},policy)){fail(Error::Initialize);__leave;}report.initialized=1;b_reload_lifecycle::Plan plan{};
 if(!b_reload_lifecycle::PreparedPlan(plan)||plan.address!=i.imageBase+0x1447B6||!plan.relay||memcmp(plan.before,b_reload_lifecycle_profile::InitCall,5)||!sources(i.imageBase)||!empty(i.imageBase)||!threads(i.primaryThread)){fail(Error::Plan);__leave;}report.planPrepared=1;
 DWORD old=0,unused=0;if(!VirtualProtect(reinterpret_cast<void*>(plan.address),5,PAGE_READWRITE,&old)){fail(Error::Publish);__leave;}
 __try {if(old!=PAGE_EXECUTE_READ||memcmp(reinterpret_cast<void*>(plan.address),plan.before,5)){fail(Error::Publish);__leave;}memcpy(reinterpret_cast<void*>(plan.address),plan.after,5);report.callWritten=1;}
 __finally {if(VirtualProtect(reinterpret_cast<void*>(plan.address),5,old,&unused))report.protectionRestored=1;else{report.uncertain=1;fail(Error::Publish);}}
 if(report.error!=Error::None||!report.callWritten||!FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(plan.address),5)){fail(Error::Publish);__leave;}
 if(!b_reload_lifecycle::Arm()){fail(Error::Arm);__leave;}report.armed=1;
 c.ContextFlags=CONTEXT_CONTROL;if(!GetThreadContext(primary,&c)||c.Rip!=i.entryPoint||!entry(i)){fail(Error::Primary);__leave;}ok=true;
 }__finally {if(held){if(ResumeThread(primary)==2)report.primaryStillHeld=1;else{report.uncertain=1;fail(Error::Resume);ok=false;}}if(primary)CloseHandle(primary);b_reload_lifecycle::Snapshot(report.lifecycle);b_reload_root_activation::Snapshot(report.activation);}}
 __except(EXCEPTION_EXECUTE_HANDLER){report.uncertain=report.callWritten;fail(Error::Exception);ok=false;}
 if(!ok&&(report.callWritten||report.activation.published))report.uncertain=1;
 ReleaseSRWLockExclusive(&lock);return ok;
}
void Snapshot(Report&r)noexcept{AcquireSRWLockShared(&lock);r=report;ReleaseSRWLockShared(&lock);}
}
