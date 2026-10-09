// Explicit owned host successor: actual factory bindings, same six noncontiguous slots.
#include "b_warm_two_bank_owner.h"
#include "b_warm_coordinator_native.h"
#include <cstdio>
#include <cstring>
#include <string>
extern "C" {
void** GuestSessionSlots=nullptr;void* SharedGameBase=nullptr;
alignas(16) uintptr_t HostStorageVtable[16]{},HostStorage[2]{};std::uint64_t BindingFixtureGeneration=1;static std::int32_t HostCurrentSize=0;
bool HostExists(void*,const char*name){return !strcmp(name,"svdexccSC03.s14");}
std::int32_t HostFileSize(void*,const char*){return HostCurrentSize;}
__declspec(dllexport) DWORD WINAPI HostSetResidentSize(void*p){HostCurrentSize=static_cast<std::int32_t>(reinterpret_cast<uintptr_t>(p));return 0;}
std::uint64_t GuestSessionParent=0,GuestSessionReadRax=0,GuestSessionWorkerRax=0;
unsigned char GuestSessionReadXmm[16]{},GuestSessionWorkerXmm[16]{};
unsigned char GuestSessionPattern[32]={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16};
uintptr_t HwbpFixtureUser=0;
struct HardwareFixtureSnapshot{std::uint64_t gpr[16]{},rflags=0,reserved=0;std::uint8_t xmm[256]{};DWORD mxcsr=0,reserved2[3]{};};
HardwareFixtureSnapshot HwbpFixtureBefore{},HwbpFixtureAfter{};
alignas(16) unsigned char HwbpFixtureSeed[256]{};std::int32_t HwbpFixtureFetched=-999;
std::uint64_t GuestSessionUserOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionMenuOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionGameOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionUpdateOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionWorkerOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t GuestSessionReadOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
}
using Call=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
using Body=void(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
using Fn=DWORD(WINAPI*)(void*);
static HMODULE banks[2]{};static unsigned activeBank=0;static bool probing=false;
static void* bodies[2][6]{};static unsigned late[6]{};
static b_warm_profile::Description desc[2]{};
struct TypedHandover {
 HMODULE first=nullptr,second=nullptr;
 static void header(b_warm_coordinator::Header&h,unsigned size,unsigned operation){h.size=size;h.operation=operation;memset(h.nonce,0x6c,sizeof h.nonce);}
 bool Bind(HMODULE bank,void**const(&slots)[6],void*const(&originals)[6]){b_warm_coordinator::Description d{};if(DescribeBWarmCoordinator(&d)||d.magic!=b_warm_coordinator::Magic||d.prepareSize!=sizeof(b_warm_coordinator::Prepare))return false;
  b_warm_coordinator::Prepare p{};header(p.header,sizeof p,1);p.pid=GetCurrentProcessId();FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return false;p.birth=(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;p.first=uintptr_t(bank);for(unsigned i=0;i<6;++i){p.slots[i]=uintptr_t(slots[i]);p.originals[i]=uintptr_t(originals[i]);}if(PrepareBWarmCoordinator(&p))return false;first=bank;return true;}
 bool AuthorizeSecond(HMODULE bank){b_warm_coordinator::Authorize p{};header(p.header,sizeof p,2);p.second=uintptr_t(bank);if(AuthorizeBWarmCoordinator(&p))return false;second=bank;return true;}
 bool Completed(HMODULE bank){b_warm_coordinator::Observe p{};header(p.header,sizeof p,3);if(ObserveBWarmCoordinator(&p))return false;return bank==first?p.firstCompleted!=0:bank==second&&p.secondCompleted!=0;}
} handover;
static void need(bool yes,const char*why){if(!yes){printf("FAIL %s\n",why);fflush(stdout);ExitProcess(93);}}
static std::uint64_t body(unsigned i,std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    if(probing){++late[i];return 77;}
    need(activeBank<2&&bodies[activeBank][i],"native business route configured");
    if(i==5)return reinterpret_cast<Call>(bodies[activeBank][i])(a,b,c,d);
    reinterpret_cast<Body>(bodies[activeBank][i])(a,b,c,d);return 0;
}
extern "C" void GuestSessionUserBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){body(0,a,b,c,d);}
extern "C" void GuestSessionMenuBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){body(1,a,b,c,d);}
extern "C" void GuestSessionGameBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){body(2,a,b,c,d);}
extern "C" void GuestSessionUpdateBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){body(3,a,b,c,d);}
extern "C" void GuestSessionWorkerBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){body(4,a,b,c,d);}
extern "C" std::uint64_t GuestSessionReadBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return body(5,a,b,c,d);}
extern "C" void HostBankArmed(){for(unsigned i=0;i<6;++i){auto p=i<4?desc[0].bank.dispatchBridge[i]:i==4?desc[0].bank.workerBridge:desc[0].bank.readBridge;need(*reinterpret_cast<void**>(GuestSessionSlots[i])==reinterpret_cast<void*>(p),"remote installed six slots");}}
extern "C" __declspec(dllexport) DWORD WINAPI HostSelectResidentBank(void* raw){
 banks[0]=static_cast<HMODULE>(raw);auto fn=reinterpret_cast<Fn>(GetProcAddress(banks[0],"DescribeBWarmProfileOwner"));if(!fn||fn(&desc[0]))return 1;
 const char*names[]={"BankUserBody","BankMenuBody","BankGameBody","BankUpdateBody","BankWorkerBody","BankReadBody"};for(unsigned i=0;i<6;++i){bodies[0][i]=reinterpret_cast<void*>(GetProcAddress(banks[0],names[i]));if(!bodies[0][i])return 2;}return 0;
}
int wmain(){
 SharedGameBase=VirtualAlloc(nullptr,0x2200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);GuestSessionSlots=static_cast<void**>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(SharedGameBase&&GuestSessionSlots,"owned environment");
 void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
 constexpr uintptr_t rv[]={0x12cc4d0,0x12db4e8,0x12cc9e0,0x12dbd90,0x138e8d0};HostStorage[0]=uintptr_t(HostStorageVtable);HostStorageVtable[13]=uintptr_t(&HostExists);HostStorageVtable[15]=uintptr_t(&HostFileSize);
 for(unsigned i=0;i<6;++i){GuestSessionSlots[i]=reinterpret_cast<void*>(i<5?uintptr_t(SharedGameBase)+rv[i]:uintptr_t(HostStorageVtable+1));*reinterpret_cast<void**>(GuestSessionSlots[i])=originals[i];}
 printf("OWNED_READY %lu %lu\n",GetCurrentProcessId(),GetCurrentThreadId());fflush(stdout);
 for(;;){int ch=getchar();if(ch=='x'||ch==EOF)break;if(ch!='r')continue;auto fn=reinterpret_cast<Fn>(GetProcAddress(banks[0],"RunResidentOwnedFrames"));need(fn!=nullptr,"frames export");HostBankArmed();need(!fn(nullptr),"owned natural main thread frames");printf("OWNED_FRAMES_DONE\n");fflush(stdout);}
 return 0;
}
