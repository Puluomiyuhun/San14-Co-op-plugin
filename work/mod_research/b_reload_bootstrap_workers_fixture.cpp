#include "b_reload_bootstrap_workers.h"
#include <cstdio>
#pragma bss_seg(".fixture")
extern "C" __declspec(dllexport) unsigned char BReloadBootstrapWorkersSpace[0x2400000];
unsigned char BReloadBootstrapWorkersSpace[0x2400000];
#pragma bss_seg()
int wmain(){auto m=GetModuleHandleW(L"owned workers.dll");using Run=DWORD(WINAPI*)(void*);auto run=m?reinterpret_cast<Run>(GetProcAddress(m,"BReloadWorkersOwnedRun")):nullptr;
printf("{\"owned_main_started\":true}\n");fflush(stdout);return run?int(run(nullptr)):91;}
