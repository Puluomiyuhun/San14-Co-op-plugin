#include "b_reload_bootstrap_workers.h"
#include <cstdio>
#ifdef B_RELOAD_BOOTSTRAP_WORKERS_OWNED
#include "b_reload_bootstrap_workers_fixture.inc"
#endif
extern "C" __declspec(dllexport) DWORD WINAPI BReloadLifecycleBootstrap(void*p){
 if(!p)return 1;bool ok=false;__try {const auto i=*static_cast<BReloadLifecycleBootstrapInfo*>(p);
#ifdef B_RELOAD_BOOTSTRAP_WORKERS_OWNED
 if(i.imageBase!=uintptr_t(GetModuleHandleW(nullptr))||!ownedPrepare(i.imageBase)){printf("OWNED preparation refused\n");fflush(stdout);return 2;}
#endif
 ok=b_reload_bootstrap_workers::InitializeAndArm(i);
 }__except(EXCEPTION_EXECUTE_HANDLER){printf("OWNED bootstrap exception=%lx\n",GetExceptionCode());fflush(stdout);return 3;}
 b_reload_bootstrap::Report b{};b_reload_lifecycle::Report l{};b_reload_root_activation::Report a{};b_reload_bootstrap_workers::Snapshot(b,l,a);
 printf("{\"actual_bootstrap\":true,\"ok\":%s,\"attempts\":%u,\"armed\":%u,\"workers\":%u,\"error\":%u}\n",ok?"true":"false",b.attempts,b.armed,a.threads,unsigned(b.error));fflush(stdout);return ok?BReloadLifecycleBootstrapSuccess:4;
}
#ifdef B_RELOAD_BOOTSTRAP_WORKERS_OWNED
extern "C" __declspec(dllexport) DWORD WINAPI BReloadWorkersOwnedRun(void*){return ownedRun();}
#endif
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
