#include "b_warm_two_bank_owner.h"
#include <cstdio>
#include <cstring>
#include <string>
extern "C" {
void** GuestSessionSlots=nullptr;void* SharedGameBase=nullptr;
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
static void* bodies[2][6]{};static unsigned late[6]{},armed[2]{};
static b_warm_profile::Description desc[2]{};
static b_warm_two_bank::Handover handover;
static void need(bool yes,const char*why){if(!yes){printf("FAIL %s\n",why);fflush(stdout);ExitProcess(93);}}
static void report(unsigned i,checkpoint_complete_live_owner::Report&r){auto f=reinterpret_cast<Fn>(GetProcAddress(banks[i],"GetCheckpointCompleteLiveOwnerReport"));need(f&&!f(&r),"owner report");}
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
extern "C" void HostBankArmed(){
    ++armed[activeBank];need(armed[activeBank]==1,"one arm per bank");
    for(unsigned i=0;i<6;++i){auto p=i<4?desc[activeBank].bank.dispatchBridge[i]:i==4?desc[activeBank].bank.workerBridge:desc[activeBank].bank.readBridge;need(GuestSessionSlots[i]==reinterpret_cast<void*>(p),"same host slots contain active bank");}
    if(!activeBank){need(!handover.AuthorizeSecond(banks[1]),"second refuses while first armed");return;}
    checkpoint_complete_live_owner::Report before[2]{},after[2]{};for(unsigned i=0;i<2;++i)report(i,before[i]);
    auto dead=VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_NOACCESS);need(dead!=nullptr,"inaccessible late arguments");probing=true;
    for(unsigned i=0;i<6;++i){auto p=i<4?desc[0].bank.dispatchBridge[i]:i==4?desc[0].bank.workerBridge:desc[0].bank.readBridge;reinterpret_cast<Call>(p)(uintptr_t(dead),uintptr_t(dead),uintptr_t(dead),uintptr_t(dead));need(late[i]==1,"late first entry calls stable native original once");}
    probing=false;for(unsigned i=0;i<2;++i)report(i,after[i]);
    for(unsigned b=0;b<2;++b){need(!memcmp(before[b].bytesReceipt,after[b].bytesReceipt,sizeof before[b].bytesReceipt)&&!memcmp(before[b].lifecycleReceipt,after[b].lifecycleReceipt,sizeof before[b].lifecycleReceipt)&&!memcmp(before[b].identityReceipt,after[b].identityReceipt,sizeof before[b].identityReceipt),"bank business receipts unchanged by old physical entries");}
    need(!memcmp(before[1].bridges,after[1].bridges,sizeof before[1].bridges),"second bank bridges never receive late first calls");
    printf("LATE_FIRST_DURING_SECOND six=6 no_new_bank_callbacks=1\n");
}
int wmain(int argc,wchar_t**argv){
    if(argc!=4)return 2;SharedGameBase=VirtualAlloc(nullptr,0x2200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);GuestSessionSlots=static_cast<void**>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(SharedGameBase&&GuestSessionSlots,"one image and one slot page");
    void* originals[]={reinterpret_cast<void*>(&GuestSessionUserOriginal),reinterpret_cast<void*>(&GuestSessionMenuOriginal),reinterpret_cast<void*>(&GuestSessionGameOriginal),reinterpret_cast<void*>(&GuestSessionUpdateOriginal),reinterpret_cast<void*>(&GuestSessionWorkerOriginal),reinterpret_cast<void*>(&GuestSessionReadOriginal)};
    memcpy(GuestSessionSlots,originals,sizeof originals);DWORD old=0;need(VirtualProtect(GuestSessionSlots,4096,PAGE_READONLY,&old)!=0,"host slot page readonly");
    const char*names[]={"BankUserBody","BankMenuBody","BankGameBody","BankUpdateBody","BankWorkerBody","BankReadBody"};
    for(unsigned i=0;i<2;++i){banks[i]=LoadLibraryExW(argv[i+1],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(banks[i]!=nullptr,"load bank");auto fn=reinterpret_cast<Fn>(GetProcAddress(banks[i],"DescribeBWarmProfileOwner"));need(fn&&!fn(&desc[i])&&desc[i].bank.module==uintptr_t(banks[i]),"real distinct module description");for(unsigned j=0;j<6;++j){bodies[i][j]=reinterpret_cast<void*>(GetProcAddress(banks[i],names[j]));need(bodies[i][j]!=nullptr,"native business export");}}
    need(banks[0]!=banks[1]&&desc[0].bank.dispatchBridge[0]!=desc[1].bank.dispatchBridge[0],"two retained independent physical banks");void** addresses[6]{};for(unsigned i=0;i<6;++i)addresses[i]=GuestSessionSlots+i;need(handover.Bind(banks[0],addresses,originals),"host coordinator bind immutable originals");need(!handover.AuthorizeSecond(banks[1]),"second refuses before any completion");
    const auto base=SharedGameBase;const auto slots=GuestSessionSlots;
    for(unsigned i=0;i<2;++i){if(i){auto stoppedPath=std::wstring(argv[3])+L"\\stopped.dll";auto stopped=LoadLibraryExW(stoppedPath.c_str(),nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(stopped!=nullptr,"load independently stopped candidate");auto stop=reinterpret_cast<Fn>(GetProcAddress(stopped,"StopCheckpointCompleteLiveOwner"));need(stop&&!stop(nullptr)&&!handover.AuthorizeSecond(stopped),"stopped unconfigured bank cannot consume handover");need(handover.AuthorizeSecond(banks[1]),"actual first complete seal restore authorizes second");}
      activeBank=i;SetEnvironmentVariableW(L"B_WARM_PROFILE_VARIANT",i?L"1":L"0");std::wstring dir=std::wstring(argv[3])+L"\\bank"+std::to_wstring(i+1);std::wstring file=dir+L"\\svdexccSC03.s14",request=dir+L".request",identity=dir+L".identity",out=dir+L".report";
      wchar_t*args[]={argv[0],const_cast<wchar_t*>(L"success-new"),file.data(),request.data(),identity.data(),out.data()};auto run=reinterpret_cast<int(*)(int,wchar_t**)>(GetProcAddress(banks[i],"RunBank"));need(run&&!run(6,args),"actual bank chain succeeded");need(SharedGameBase==base&&GuestSessionSlots==slots&&handover.Completed(banks[i]),"same image same six slots fully restored");
      printf("BANK %u completed=1 sealed=1 restored=1 slot_page=%p base=%p module=%p\n",i+1,slots,base,banks[i]);
    }
    need(!handover.AuthorizeSecond(banks[1]),"handover permission cannot repeat");
    printf("{\"passed\":true,\"same_process\":true,\"same_six_slots\":true,\"completed_banks\":2,\"late_first_during_second\":6,\"native_business_double\":true,\"game_access\":false}\n");
    // Both DLLs and old protected objects remain resident until normal process exit.
    return 0;
}
