// Explicit owned host successor: actual factory bindings, same six noncontiguous slots.
#include "b_warm_two_bank_owner.h"
#include "b_warm_coordinator_native.h"
#include "b_warm_refresh_owner.h"
#include <filesystem>
#include <vector>
#include <cstdio>
#include <cstring>
#include <string>
extern "C" {
void** GuestSessionSlots=nullptr;void* SharedGameBase=nullptr;
alignas(16) uintptr_t HostStorageVtable[16]{},HostStorage[2]{};std::uint64_t BindingFixtureGeneration=1;static std::vector<unsigned char> HostNativeCache;static std::filesystem::path HostNativeDirectory,HostNativeTarget;static unsigned HostWrites=0;
bool HostExists(void*,const char*name){return !strcmp(name,"svdexccSC03.s14");}
std::int32_t HostFileSize(void*,const char*){return static_cast<std::int32_t>(HostNativeCache.size());}
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
struct TypedHandover {
 HMODULE first=nullptr,second=nullptr;
 static void header(b_warm_coordinator::Header&h,unsigned size,unsigned operation){h.size=size;h.operation=operation;memset(h.nonce,0x6c,sizeof h.nonce);}
 bool Bind(HMODULE bank,void**const(&slots)[6],void*const(&originals)[6]){b_warm_coordinator::Description d{};if(DescribeBWarmCoordinator(&d)||d.magic!=b_warm_coordinator::Magic||d.prepareSize!=sizeof(b_warm_coordinator::Prepare))return false;
  b_warm_coordinator::Prepare p{};header(p.header,sizeof p,1);p.pid=GetCurrentProcessId();FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return false;p.birth=(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;p.first=uintptr_t(bank);for(unsigned i=0;i<6;++i){p.slots[i]=uintptr_t(slots[i]);p.originals[i]=uintptr_t(originals[i]);}if(PrepareBWarmCoordinator(&p))return false;first=bank;return true;}
 bool AuthorizeSecond(HMODULE bank){b_warm_coordinator::Authorize p{};header(p.header,sizeof p,2);p.second=uintptr_t(bank);if(AuthorizeBWarmCoordinator(&p))return false;second=bank;return true;}
 bool Completed(HMODULE bank){b_warm_coordinator::Observe p{};header(p.header,sizeof p,3);if(ObserveBWarmCoordinator(&p))return false;return bank==first?p.firstCompleted!=0:bank==second&&p.secondCompleted!=0;}
} handover;
static void need(bool yes,const char*why){if(!yes){printf("FAIL %s\n",why);fflush(stdout);ExitProcess(93);}}

static bool HostPut(const std::filesystem::path&p,const std::vector<unsigned char>&bytes){
 HANDLE h=CreateFileW(p.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return false;DWORD wrote=0;bool ok=WriteFile(h,bytes.data(),static_cast<DWORD>(bytes.size()),&wrote,nullptr)&&wrote==bytes.size()&&FlushFileBuffers(h);if(!CloseHandle(h))ok=false;return ok;
}
extern "C" bool __fastcall HostFileWrite(void*self,const char*name,const void*bytes,std::int32_t size){
 if(self!=HostStorage||strcmp(name,"svdexccSC03.s14")||!bytes||size<=0)return false;
 ++HostWrites;HANDLE h=CreateFileW(HostNativeTarget.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return false;
 DWORD wrote=0;bool ok=WriteFile(h,bytes,static_cast<DWORD>(size),&wrote,nullptr)&&wrote==static_cast<DWORD>(size)&&SetEndOfFile(h)&&FlushFileBuffers(h);if(!CloseHandle(h))ok=false;
 if(ok){const auto*p=static_cast<const unsigned char*>(bytes);HostNativeCache.assign(p,p+size);}return ok;
}
static bool HostIdentity(const wchar_t*path,b_warm_storage_refresh::Identity&out){
 HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);if(h==INVALID_HANDLE_VALUE)return false;BY_HANDLE_FILE_INFORMATION i{};bool ok=GetFileInformationByHandle(h,&i)!=FALSE;if(!CloseHandle(h))ok=false;if(ok)out={i.dwVolumeSerialNumber,i.nFileIndexHigh,i.nFileIndexLow,i.ftLastWriteTime};return ok;
}
static bool HostPath(wchar_t(&to)[512],const std::filesystem::path&p){const auto text=p.wstring();if(text.size()>=512)return false;std::wmemcpy(to,text.c_str(),text.size()+1);return true;}
extern "C" bool HostRefreshConfig(b_warm_refresh::Config*out){
 if(!out||HostNativeCache.empty())return false;
 auto&c=*out;c.previousSize=static_cast<std::uint32_t>(HostNativeCache.size());
 if(!native_storage_read::Sha256(HostNativeCache.data(),HostNativeCache.size(),c.previousSha256)||!HostIdentity(c.warm.owner.localPath,c.sourceIdentity)||!HostIdentity(HostNativeTarget.c_str(),c.previousTargetIdentity))return false;
 const auto backup=HostNativeDirectory/(L"backup-"+std::to_wstring(activeBank+1)+L".s14");
 if(!HostPut(backup,HostNativeCache)||!HostPath(c.targetPath,HostNativeTarget)||!HostPath(c.backupPath,backup)||!HostPath(c.refreshIntent,HostNativeDirectory/(L"refresh-"+std::to_wstring(activeBank+1)+L".intent")))return false;
 c.write.address=uintptr_t(&HostFileWrite);c.write.moduleIndex=1;memcpy(c.write.first32,reinterpret_cast<void*>(&HostFileWrite),32);return true;
}
extern "C" bool HostProbeLease(bool expectedHeld){
 HANDLE h=CreateFileW(HostNativeTarget.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);const DWORD error=GetLastError();if(h!=INVALID_HANDLE_VALUE){CloseHandle(h);return !expectedHeld;}return expectedHeld&&error==ERROR_SHARING_VIOLATION;
}

static void report(unsigned i,checkpoint_complete_live_owner::Report&r){auto f=reinterpret_cast<Fn>(GetProcAddress(banks[i],"GetCheckpointCompleteLiveOwnerReport"));need(f&&!f(&r),"owner report");}
static std::uint64_t body(unsigned i,std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    if(probing){++late[i];return 77;}
    need(activeBank<2&&bodies[activeBank][i],"native business route configured");
    if(i==5){need(a==uintptr_t(HostStorage)&&!strcmp(reinterpret_cast<const char*>(b),"svdexccSC03.s14")&&c&&d<=HostNativeCache.size(),"native cache read ABI");memcpy(reinterpret_cast<void*>(c),HostNativeCache.data(),static_cast<size_t>(d));return d;}
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
    for(unsigned i=0;i<6;++i){auto p=i<4?desc[activeBank].bank.dispatchBridge[i]:i==4?desc[activeBank].bank.workerBridge:desc[activeBank].bank.readBridge;need(*reinterpret_cast<void**>(GuestSessionSlots[i])==reinterpret_cast<void*>(p),"same host slots contain active bank");}
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
    constexpr uintptr_t slotsRva[]={0x12cc4d0,0x12db4e8,0x12cc9e0,0x12dbd90,0x138e8d0};
    HostNativeDirectory=std::filesystem::path(argv[3])/L"native";std::filesystem::create_directories(HostNativeDirectory);HostNativeTarget=HostNativeDirectory/L"svdexccSC03.s14";HostNativeCache.assign(701,0x17);need(HostPut(HostNativeTarget,HostNativeCache),"initial native target");
    HostStorageVtable[0]=uintptr_t(&HostFileWrite);HostStorage[0]=uintptr_t(HostStorageVtable);HostStorageVtable[13]=uintptr_t(&HostExists);HostStorageVtable[15]=uintptr_t(&HostFileSize);
    for(unsigned i=0;i<6;++i){GuestSessionSlots[i]=reinterpret_cast<void*>(i<5?uintptr_t(SharedGameBase)+slotsRva[i]:uintptr_t(HostStorageVtable+1));*reinterpret_cast<void**>(GuestSessionSlots[i])=originals[i];}
    const char*names[]={"BankUserBody","BankMenuBody","BankGameBody","BankUpdateBody","BankWorkerBody","BankReadBody"};
    for(unsigned i=0;i<2;++i){banks[i]=LoadLibraryExW(argv[i+1],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(banks[i]!=nullptr,"load bank");auto fn=reinterpret_cast<Fn>(GetProcAddress(banks[i],"DescribeBWarmProfileOwner"));need(fn&&!fn(&desc[i])&&desc[i].bank.module==uintptr_t(banks[i]),"real distinct module description");for(unsigned j=0;j<6;++j){bodies[i][j]=reinterpret_cast<void*>(GetProcAddress(banks[i],names[j]));need(bodies[i][j]!=nullptr,"native business export");}}
    need(banks[0]!=banks[1]&&desc[0].bank.dispatchBridge[0]!=desc[1].bank.dispatchBridge[0],"two retained independent physical banks");void** addresses[6]{};for(unsigned i=0;i<6;++i)addresses[i]=reinterpret_cast<void**>(GuestSessionSlots[i]);need(handover.Bind(banks[0],addresses,originals),"host coordinator bind immutable originals");need(!handover.AuthorizeSecond(banks[1]),"second refuses before any completion");
    const auto base=SharedGameBase;const auto slots=GuestSessionSlots;
    const bool firstFail=GetEnvironmentVariableW(L"B_WARM_PAIR_FIRST_FAIL",nullptr,0)!=0;
    for(unsigned i=0;i<2;++i){if(i){auto stoppedPath=std::wstring(argv[3])+L"\\stopped.dll";auto stopped=LoadLibraryExW(stoppedPath.c_str(),nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);need(stopped!=nullptr,"load independently stopped candidate");auto stop=reinterpret_cast<Fn>(GetProcAddress(stopped,"StopCheckpointCompleteLiveOwner"));need(stop&&!stop(nullptr)&&!handover.AuthorizeSecond(stopped),"stopped unconfigured bank cannot consume handover");need(handover.AuthorizeSecond(banks[1]),"actual first complete seal restore authorizes second");}
      activeBank=i;SetEnvironmentVariableW(L"B_WARM_PROFILE_VARIANT",i?L"1":L"0");std::wstring dir=std::wstring(argv[3])+L"\\bank"+std::to_wstring(i+1);std::wstring file=dir+L"\\svdexccSC03.s14",request=dir+L".request",identity=dir+L".identity",out=dir+L".report";
      // Native cache changes only through the actual refresh FileWrite port.
      wchar_t*args[]={argv[0],const_cast<wchar_t*>(firstFail?L"guard-drift":L"success-new"),file.data(),request.data(),identity.data(),out.data()};auto run=reinterpret_cast<int(*)(int,wchar_t**)>(GetProcAddress(banks[i],"RunBank"));need(run&&!run(6,args),"actual bank factory chain succeeded");if(firstFail){need(i==0&&!handover.Completed(banks[0])&&!handover.AuthorizeSecond(banks[1]),"actual first source failure cannot hand over");checkpoint_complete_live_owner::Report untouched{};report(1,untouched);need(!untouched.value[unsigned(checkpoint_complete_live_owner::Value::InstallCalls)]&&!armed[1],"second never installed after first failed");printf("FIRST_FAILED_NO_HANDOVER actual_guard_drift=1 second_install=0\n");return 0;}need(SharedGameBase==base&&GuestSessionSlots==slots&&handover.Completed(banks[i]),"actual full factory guard chain restored same six addresses");
      printf("BANK %u completed=1 sealed=1 restored=1 slot_page=%p base=%p module=%p\n",i+1,slots,base,banks[i]);
    }
    need(!handover.AuthorizeSecond(banks[1]),"handover permission cannot repeat");need(HostWrites==2&&HostProbeLease(false),"two native writes and final target lease released");
    printf("{\"passed\":true,\"same_process\":true,\"same_six_slots\":true,\"completed_banks\":2,\"late_first_during_second\":6,\"native_business_double\":true,\"game_access\":false}\n");
    // Both DLLs and old protected objects remain resident until normal process exit.
    return 0;
}
