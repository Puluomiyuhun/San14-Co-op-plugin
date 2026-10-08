#include "b_reload_lifecycle_loader.h"
#include <cstdio>
#ifdef B_RELOAD_LIFECYCLE_BOOTSTRAP_DLL
extern "C" __declspec(dllexport) DWORD WINAPI BReloadLifecycleBootstrap(void*p){
 const auto*i=static_cast<const BReloadLifecycleBootstrapInfo*>(p);if(!i||i->size!=sizeof(*i)||i->version!=1||i->pid!=GetCurrentProcessId()||i->imageBase!=uintptr_t(GetModuleHandleW(nullptr))||i->entryByte>255)return 1;
 HANDLE main=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_LIMITED_INFORMATION,FALSE,i->primaryThread);if(!main||GetProcessIdOfThread(main)!=GetCurrentProcessId()){if(main)CloseHandle(main);return 2;}CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL;const bool waiting=GetThreadContext(main,&c)&&c.Rip==i->entryPoint;CloseHandle(main);if(!waiting||*reinterpret_cast<const BYTE*>(i->entryPoint)!=BYTE(i->entryByte))return 3;
 auto*marker=reinterpret_cast<volatile LONG*>(GetProcAddress(GetModuleHandleW(nullptr),"BReloadLifecycleMainMarker"));if(!marker||InterlockedCompareExchange(marker,1,0)!=0)return 4;
 wchar_t reject[2]{};if(GetEnvironmentVariableW(L"B_RELOAD_LOADER_FIXTURE_REJECT",reject,2))return 5;
 return BReloadLifecycleBootstrapSuccess;
}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
#else
extern "C" __declspec(dllexport) volatile LONG BReloadLifecycleMainMarker=0;
int wmain(){const bool ok=InterlockedCompareExchange(&BReloadLifecycleMainMarker,2,1)==1;printf("{\"owned_main_started_after_bootstrap\":%s}\n",ok?"true":"false");return ok?0:91;}
#endif
