#include "b_reload_bootstrap.h"
#include <cstdio>
#ifdef B_RELOAD_BOOTSTRAP_OWNED_PREPARE
#include "b_reload_lifecycle_profile.h"
#include "b_reload_root_worker_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <cstring>
// Explicit owned PE construction only. Never present in production DLL.
static DWORD WINAPI ownedExtraThread(void*p){return WaitForSingleObject(static_cast<HANDLE>(p),10000)==WAIT_OBJECT_0?0:1;}
static bool prepareOwned(uintptr_t b){
 struct Span{uintptr_t rva;const unsigned char*p;size_t n;};const Span s[]={
 {0x1447B6,b_reload_lifecycle_profile::InitCall,sizeof b_reload_lifecycle_profile::InitCall},
 {0x509580,b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes},
 {0x834D10,b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes},
 {0x50B730,b_reload_root_worker_profile::ThunkBytes,sizeof b_reload_root_worker_profile::ThunkBytes},
 {0x50B690,b_reload_root_worker_profile::YieldBytes,sizeof b_reload_root_worker_profile::YieldBytes},
 {0x83A930,checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes}};
 for(const auto&x:s){DWORD old=0,unused=0;if(!VirtualProtect(reinterpret_cast<void*>(b+x.rva),x.n,PAGE_READWRITE,&old))return false;memcpy(reinterpret_cast<void*>(b+x.rva),x.p,x.n);if(!VirtualProtect(reinterpret_cast<void*>(b+x.rva),x.n,PAGE_EXECUTE_READ,&unused)||!FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(b+x.rva),x.n))return false;}
 const auto pool=b+0x1A24DA0;MEMORY_BASIC_INFORMATION poolMemory{};VirtualQuery(reinterpret_cast<void*>(pool),&poolMemory,sizeof poolMemory);printf("OWNED pool_protection=%lx first=%llx second=%llx\n",poolMemory.Protect,*reinterpret_cast<const uintptr_t*>(pool+0x10),*reinterpret_cast<const uintptr_t*>(pool+0x90));
 DWORD poolOld=0;if(!VirtualProtect(reinterpret_cast<void*>(pool),0x210,PAGE_READWRITE,&poolOld))return false;
 const auto slot=b+0x123C0D8;DWORD old=0,unused=0;if(!VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READWRITE,&old))return false;*reinterpret_cast<uintptr_t*>(slot)=uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection"));
 char mode[64]{};GetEnvironmentVariableA("B_RELOAD_BOOTSTRAP_OWNED_MODE",mode,sizeof mode);
 if(!strcmp(mode,"iat"))*reinterpret_cast<uintptr_t*>(slot)=uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"GetTickCount64"));
 if(!VirtualProtect(reinterpret_cast<void*>(slot),8,PAGE_READONLY,&unused))return false;
 if(!strcmp(mode,"pool"))*reinterpret_cast<uintptr_t*>(b+0x1A24DA0+0x10)=1;
 if(!strcmp(mode,"bytes")){if(!VirtualProtect(reinterpret_cast<void*>(b+0x509580),1,PAGE_READWRITE,&old))return false;*reinterpret_cast<BYTE*>(b+0x509580)^=1;if(!VirtualProtect(reinterpret_cast<void*>(b+0x509580),1,PAGE_EXECUTE_READ,&unused))return false;}
 return true;
}
#endif
static checkpoint_native_task_provider::Provider provider;
extern "C" __declspec(dllexport) DWORD WINAPI BReloadLifecycleBootstrap(void*p){
 bool ok=false;
#ifdef B_RELOAD_BOOTSTRAP_OWNED_PREPARE
 bool duplicateRefused=false;char ownedMode[64]{};GetEnvironmentVariableA("B_RELOAD_BOOTSTRAP_OWNED_MODE",ownedMode,sizeof ownedMode);HANDLE extraStop=nullptr,extraThread=nullptr;
#endif
 __try{if(!p)return 1;const auto i=*static_cast<const BReloadLifecycleBootstrapInfo*>(p);
#ifdef B_RELOAD_BOOTSTRAP_OWNED_PREPARE
 if(i.imageBase!=uintptr_t(GetModuleHandleW(nullptr))||!prepareOwned(i.imageBase))return 2;
 if(!strcmp(ownedMode,"threads")){extraStop=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!extraStop)return 6;extraThread=CreateThread(nullptr,0,ownedExtraThread,extraStop,0,nullptr);if(!extraThread){CloseHandle(extraStop);return 7;}}
#endif
 ok=b_reload_bootstrap::InitializeAndArm(i,provider);
#ifdef B_RELOAD_BOOTSTRAP_OWNED_PREPARE
 if(ok&&!strcmp(ownedMode,"repeat"))duplicateRefused=!b_reload_bootstrap::InitializeAndArm(i,provider);
#endif
 }__except(EXCEPTION_EXECUTE_HANDLER){return 3;}
#ifdef B_RELOAD_BOOTSTRAP_OWNED_PREPARE
 if(extraThread){SetEvent(extraStop);if(WaitForSingleObject(extraThread,10000)!=WAIT_OBJECT_0)return 8;CloseHandle(extraThread);CloseHandle(extraStop);}
 printf("{\"owned_bootstrap_probe\":true,\"repeat_requested\":%s,\"duplicate_refused\":%s}\n",!strcmp(ownedMode,"repeat")?"true":"false",duplicateRefused?"true":"false");
#endif
 b_reload_bootstrap::Report r{};b_reload_bootstrap::Snapshot(r);
 printf("{\"bootstrap_actual_lifecycle\":true,\"ok\":%s,\"error\":%u,\"attempts\":%u,\"primary_held\":%u,\"threads_checked\":%u,\"sources_ready\":%u,\"initialized\":%u,\"plan_prepared\":%u,\"call_written\":%u,\"protection_restored\":%u,\"armed\":%u,\"primary_still_held\":%u,\"uncertain\":%u,\"iat_published\":%u,\"lifecycle_error\":%u,\"activation_error\":%u,\"workers_started\":false,\"full_world\":false,\"room_ready\":false}\n",ok?"true":"false",unsigned(r.error),r.attempts,r.primaryHeld,r.threadSetVerified,r.sourcesReady,r.initialized,r.planPrepared,r.callWritten,r.protectionRestored,r.armed,r.primaryStillHeld,r.uncertain,r.activation.published,unsigned(r.lifecycle.error),unsigned(r.activation.error));fflush(stdout);
 return ok?BReloadLifecycleBootstrapSuccess:4;
}
extern "C" __declspec(dllexport) DWORD WINAPI BReloadBootstrapReadReport(void*p){if(!p)return 1;__try{b_reload_bootstrap::Snapshot(*static_cast<b_reload_bootstrap::Report*>(p));return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 2;}}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
