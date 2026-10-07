#include "human_rules_debug_publish_shared.h"
#include <cstdio>
#include <cstring>
extern "C" void OwnedBreak();
extern "C" void Busy();
extern "C" int Site0(),Site1(),Site2(),Site3(),Site4(),Site5();
extern "C" {__declspec(dllexport) Manifest PublishManifest{};volatile LONG Running=1;}
volatile LONG64 counter=0;
#define HOOK(N) extern "C" __declspec(noinline) int Hook##N(){return 100+N;}
HOOK(0) HOOK(1) HOOK(2) HOOK(3) HOOK(4) HOOK(5)
DWORD WINAPI Worker(void*) {while(InterlockedCompareExchange(&Running,1,1))InterlockedIncrement64(&counter);return 0;}
DWORD WINAPI BusyWorker(void*){Busy();return 0;}
int main(int argc,char**argv){
 const char* mode=argc>1?argv[1]:"routes";
 int(*sites[])()={Site0,Site1,Site2,Site3,Site4,Site5};
 int(*hooks[])()={Hook0,Hook1,Hook2,Hook3,Hook4,Hook5};
 PublishManifest.magic=Magic;PublishManifest.owned_break=reinterpret_cast<std::uint64_t>(OwnedBreak);
 for(unsigned i=0;i<6;i++){PublishManifest.sites[i]=reinterpret_cast<std::uint64_t>(sites[i]);PublishManifest.hooks[i]=reinterpret_cast<std::uint64_t>(hooks[i]);}
 PublishManifest.counter=reinterpret_cast<std::uint64_t>(&counter);PublishManifest.running=reinterpret_cast<std::uint64_t>(&Running);PublishManifest.busy=reinterpret_cast<std::uint64_t>(Busy);
 HANDLE workers[3];for(unsigned i=0;i<3;i++)workers[i]=CreateThread(nullptr,0,Worker,nullptr,0,nullptr);
 HANDLE busy=nullptr;
 if(!strcmp(mode,"rip-in-range")){busy=CreateThread(nullptr,0,BusyWorker,nullptr,0,nullptr);PublishManifest.sites[0]=PublishManifest.busy;}
 DWORD driftOld=0;
 if(!strcmp(mode,"preimage-drift")||!strcmp(mode,"protection-drift")){
  VirtualProtect(reinterpret_cast<void*>(Site0),14,PAGE_EXECUTE_READWRITE,&driftOld);
  if(!strcmp(mode,"preimage-drift")){*reinterpret_cast<unsigned char*>(Site0)=0x91;DWORD ignored=0;VirtualProtect(reinterpret_cast<void*>(Site0),14,driftOld,&ignored);FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(Site0),14);}
 }
 Sleep(30);OwnedBreak();
 if(driftOld){DWORD ignored=0;VirtualProtect(reinterpret_cast<void*>(Site0),14,PAGE_EXECUTE_READWRITE,&ignored);*reinterpret_cast<unsigned char*>(Site0)=0x90;VirtualProtect(reinterpret_cast<void*>(Site0),14,driftOld,&ignored);FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(Site0),14);}
 if(!strcmp(mode,"target-exception"))RaiseException(0xE0421234,EXCEPTION_NONCONTINUABLE,0,nullptr);
 bool installed=!strcmp(mode,"routes");
 for(unsigned i=0;i<6;i++)if(sites[i]()!=(installed?100:0)+static_cast<int>(i))return 31;
 OwnedBreak(); // Restore event, or second observation after rejected/rolled-back publication.
 for(unsigned i=0;i<6;i++)if(sites[i]()!=static_cast<int>(i))return 32;
 InterlockedExchange(&Running,0);WaitForMultipleObjects(3,workers,TRUE,5000);
 for(HANDLE h:workers)CloseHandle(h);if(busy){WaitForSingleObject(busy,5000);CloseHandle(busy);}
 return 0;
}
