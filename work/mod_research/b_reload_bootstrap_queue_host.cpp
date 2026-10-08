#include <Windows.h>
#pragma bss_seg(".fixture")
extern "C" __declspec(dllexport) unsigned char BReloadBootstrapQueueSpace[0x2400000];
unsigned char BReloadBootstrapQueueSpace[0x2400000];
#pragma bss_seg()
// No CRT: the whole occupied owned fixture range starts below RVA F000.
extern "C" void HostEntry(){
 auto m=GetModuleHandleW(L"owned queue.dll");using Run=DWORD(WINAPI*)(void*);
 auto run=m?reinterpret_cast<Run>(GetProcAddress(m,"BReloadQueueOwnedRun")):nullptr;
 ExitProcess(run?run(nullptr):91);
}
