#include "b_reload_bootstrap.h"
#include <cstdio>
// The DLL explicitly populates bounded ranges in this owned MEM_IMAGE section.
// No real executable/runtime profile is modified or loaded by this host.
#pragma bss_seg(".fixture")
extern "C" __declspec(dllexport) unsigned char BReloadBootstrapOwnedSpace[0x2400000];
unsigned char BReloadBootstrapOwnedSpace[0x2400000];
#pragma bss_seg()
int wmain(){
 const auto module=GetModuleHandleW(L"owned bootstrap.dll");using Read=DWORD(WINAPI*)(void*);const auto read=module?reinterpret_cast<Read>(GetProcAddress(module,"BReloadBootstrapReadReport")):nullptr;
 b_reload_bootstrap::Report r{};const bool ok=read&&read(&r)==0&&r.error==b_reload_bootstrap::Error::None&&r.initialized&&r.planPrepared&&r.callWritten&&r.armed&&r.primaryStillHeld&&r.activation.published&&r.activation.initialized&&!r.activation.threads&&!r.lifecycle.entered&&!r.uncertain;
 printf("{\"owned_main_started\":true,\"actual_initialized_and_armed\":%s,\"native_pool_not_started\":true,\"artificial_owned_image\":true}\n",ok?"true":"false");fflush(stdout);return ok?0:91;
}
