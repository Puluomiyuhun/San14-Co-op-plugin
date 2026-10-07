#include "human_rules_activation_v2.h"
#include "human_rules_activation_profile.h"
#include "human_rules_activation_publish_v2_inspect.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_profile.h"
#include "human_rules_hook_unwind.h"
#include <tlhelp32.h>
#include <wincrypt.h>
#include <array>
#include <vector>
#include <string>
#include <cstdio>
#include <cstring>
#include <cstddef>
#include <psapi.h>
#include "human_rules_activation_publish_v2_config.h"
#pragma comment(lib,"psapi.lib")
#pragma comment(lib,"advapi32.lib")
namespace {
using A=std::uint64_t;
using human_rules_stage::Descriptor;
using human_rules_stage::Site;
bool read(HANDLE h,A a,void*b,SIZE_T n){SIZE_T done=0;return ReadProcessMemory(h,reinterpret_cast<void*>(a),b,n,&done)&&done==n;}
bool write(HANDLE h,A a,const void*b,SIZE_T n){SIZE_T done=0;return WriteProcessMemory(h,reinterpret_cast<void*>(a),b,n,&done)&&done==n;}
bool same(HANDLE h,A a,const void*b,SIZE_T n){std::vector<unsigned char>v(n);return read(h,a,v.data(),n)&&!memcmp(v.data(),b,n);}
bool region(HANDLE h,A a,SIZE_T n,A allocation,DWORD type,DWORD protection){MEMORY_BASIC_INFORMATION m{};return a+n>a&&VirtualQueryEx(h,reinterpret_cast<void*>(a),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==type&&m.Protect==protection&&reinterpret_cast<A>(m.AllocationBase)==allocation&&a+n<=reinterpret_cast<A>(m.BaseAddress)+m.RegionSize;}
bool counterCheck(HANDLE h,A stage){
 for(const auto&c:ActiveCounters){A value=1;if(!region(h,stage+c.value_rva,8,stage,MEM_IMAGE,PAGE_READWRITE)||!region(h,stage+c.instruction_rva,c.size,stage,MEM_IMAGE,PAGE_EXECUTE_READ)||!same(h,stage+c.instruction_rva,c.bytes,c.size)||!read(h,stage+c.value_rva,&value,8)||value)return false;}return true;
}
bool fileId(HANDLE a,HANDLE b){BY_HANDLE_FILE_INFORMATION x{},y{};return GetFileInformationByHandle(a,&x)&&GetFileInformationByHandle(b,&y)&&x.dwVolumeSerialNumber==y.dwVolumeSerialNumber&&x.nFileIndexHigh==y.nFileIndexHigh&&x.nFileIndexLow==y.nFileIndexLow;}
std::string fileHash(const char*path){
 HANDLE f=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(f==INVALID_HANDLE_VALUE)return {};
 HCRYPTPROV provider=0;HCRYPTHASH hash=0;bool ok=CryptAcquireContext(&provider,nullptr,nullptr,PROV_RSA_AES,CRYPT_VERIFYCONTEXT)&&CryptCreateHash(provider,CALG_SHA_256,0,0,&hash);
 unsigned char buffer[65536];DWORD count=0;
 while(ok){if(!ReadFile(f,buffer,sizeof buffer,&count,nullptr)){ok=false;break;}if(!count)break;ok=!!CryptHashData(hash,buffer,count,0);}
 unsigned char digest[32];DWORD n=32;ok=ok&&CryptGetHashParam(hash,HP_HASHVAL,digest,&n,0)&&n==32;
 if(hash)CryptDestroyHash(hash);if(provider)CryptReleaseContext(provider,0);CloseHandle(f);
 std::string out;if(ok)for(auto b:digest){char part[3];sprintf_s(part,"%02x",b);out+=part;}return out;
}
bool identity(HANDLE h,DWORD pid,A born,const std::string&path){FILETIME a,b,c,d;char actual[32768];DWORD n=sizeof actual;return GetProcessId(h)==pid&&GetProcessTimes(h,&a,&b,&c,&d)&&((A(a.dwHighDateTime)<<32)|a.dwLowDateTime)==born&&QueryFullProcessImageNameA(h,0,actual,&n)&&!_stricmp(actual,path.c_str())&&WaitForSingleObject(h,0)==WAIT_TIMEOUT;}
A exportRva(HMODULE module,const char*name){auto p=GetProcAddress(module,name);return p?reinterpret_cast<A>(p)-reinterpret_cast<A>(module):0;}
bool contexts(DWORD pid,const Descriptor&d,unsigned&count,A stageSize){
 HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(snapshot==INVALID_HANDLE_VALUE)return false;
 THREADENTRY32 entry{};entry.dwSize=sizeof entry;bool ok=!!Thread32First(snapshot,&entry);count=0;
 while(ok){if(entry.th32OwnerProcessID==pid){HANDLE thread=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,entry.th32ThreadID);CONTEXT c{};c.ContextFlags=CONTEXT_ALL;
  if(!thread||GetProcessIdOfThread(thread)!=pid||!GetThreadContext(thread,&c)){if(thread)CloseHandle(thread);ok=false;break;}CloseHandle(thread);++count;
  if((c.Rip>=d.module&&c.Rip<d.module+stageSize)||(c.Rip>=d.allocation&&c.Rip<d.allocation+0x10000)){ok=false;break;}
  for(const auto&s:d.sites)if(c.Rip>=s.address&&c.Rip<s.address+s.patch_size){ok=false;break;}if(!ok)break;}
  if(!Thread32Next(snapshot,&entry)){ok=GetLastError()==ERROR_NO_MORE_FILES;break;}
 }CloseHandle(snapshot);return ok&&count>=1;
}
bool copiedDescriptor(HANDLE h,A address,Descriptor&d){
 LONG before=0,after=0;const A at=address+offsetof(Descriptor,preparation_state);Descriptor again{};
 return read(h,at,&before,sizeof before)&&before==human_rules_stage::Prepared&&read(h,address,&d,sizeof d)&&read(h,address,&again,sizeof again)&&read(h,at,&after,sizeof after)&&after==before&&!memcmp(&d,&again,sizeof d)&&d.preparation_state==before;
}
bool nativeUnwind(HANDLE h,A image){
 IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
 if(!read(h,image,&dos,sizeof dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<0||dos.e_lfanew>0x1000||!read(h,image+dos.e_lfanew,&nt,sizeof nt)||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64)return false;
 const auto&directory=nt.OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXCEPTION];
 if(!directory.VirtualAddress||directory.Size%sizeof(RUNTIME_FUNCTION)||directory.Size>2*1024*1024||A(directory.VirtualAddress)+directory.Size>nt.OptionalHeader.SizeOfImage)return false;
 std::vector<RUNTIME_FUNCTION> entries(directory.Size/sizeof(RUNTIME_FUNCTION));if(!read(h,image+directory.VirtualAddress,entries.data(),directory.Size))return false;
 for(const auto&w:human_rules_hook::Unwinds){bool found=false;for(const auto&e:entries)if(e.BeginAddress==w.start&&e.EndAddress==w.end&&e.UnwindData==w.rva)found=true;if(!found||!same(h,image+w.rva,w.bytes,w.size))return false;}return true;
}
void jump(unsigned char*out,A to){out[0]=0xff;out[1]=0x25;memset(out+2,0,4);memcpy(out+6,&to,8);}
bool siteBytes(HANDLE h,const Site&s,bool patched){return same(h,s.address,patched?s.replacement:s.expected,s.patch_size)&&same(h,s.address+s.patch_size,s.expected+s.patch_size,s.profile_size-s.patch_size);}
bool validate(HANDLE h,const Descriptor&d,DWORD pid,A born,A image,A stage,const std::array<A,5>&exports,bool patched){
 if(d.magic!=human_rules_stage::Magic||d.version!=1||d.size!=sizeof d||d.pid!=pid||d.birth!=born||d.fixture!=ExpectedFixture||d.image!=image||d.module!=stage||d.preparation_state!=human_rules_stage::Prepared||d.site_count!=6||d.policy_enabled!=1||d.reserved||!d.allocation)return false;
 bool nonce=false;for(auto b:d.nonce)nonce=nonce||b!=0;if(!nonce||!nativeUnwind(h,image))return false;
 if(!region(h,d.allocation,0x10000,d.allocation,MEM_PRIVATE,PAGE_EXECUTE_READ))return false;
 for(unsigned i=0;i<6;i++){
  const auto&s=d.sites[i];unsigned char expectedPatch[16]{};A target=0;
  if(s.reserved||s.protection!=PAGE_EXECUTE_READ)return false;
  if(i<4){const auto&p=san14_ai_runtime::HookSites[i];target=stage+exports[i];
   if(s.address!=image+p.original.rva||s.patch_size!=p.instruction_prefix||s.profile_size!=p.original.size||memcmp(s.expected,p.original.bytes,p.original.size)||s.destination!=target||s.original_target!=d.allocation+i*0x100)return false;
   memset(expectedPatch,0x90,s.patch_size);jump(expectedPatch,target);
   unsigned char trampoline[32]{};memcpy(trampoline,p.original.bytes,s.patch_size);trampoline[s.patch_size]=0x49;trampoline[s.patch_size+1]=0xbb;A continuation=s.address+s.patch_size;memcpy(trampoline+s.patch_size+2,&continuation,8);trampoline[s.patch_size+10]=0x41;trampoline[s.patch_size+11]=0xff;trampoline[s.patch_size+12]=0xe3;
   const auto&w=human_rules_hook::Unwinds[i];if(!same(h,s.original_target,trampoline,s.patch_size+13)||!same(h,d.allocation+i*0x100+0x40,w.bytes,w.size))return false;
  }else{const auto&p=san14_economy_runtime::Callsites[i-4];target=stage+exports[4];A relay=d.allocation+0x400+(i-4)*0x20;
   if(s.address!=image+p.call_rva||s.patch_size!=5||s.profile_size!=5||memcmp(s.expected,p.original,5)||s.destination!=relay||s.original_target!=image+0x2110b0)return false;
   auto delta=static_cast<std::int64_t>(relay)-static_cast<std::int64_t>(s.address+5);if(delta<INT32_MIN||delta>INT32_MAX)return false;auto rel=static_cast<std::int32_t>(delta);expectedPatch[0]=0xe8;memcpy(expectedPatch+1,&rel,4);
   unsigned char relayBytes[14];jump(relayBytes,target);if(!same(h,relay,relayBytes,sizeof relayBytes))return false;
  }
  if(memcmp(s.replacement,expectedPatch,s.patch_size)||!region(h,target,1,stage,MEM_IMAGE,PAGE_EXECUTE_READ)||!region(h,s.address,s.profile_size,image,MEM_IMAGE,s.protection)||!siteBytes(h,s,patched))return false;
 }
 for(const auto&a:san14_economy_runtime::NativeAnchors)if(!same(h,image+a.rva,a.bytes,a.size))return false;
 return true;
}
bool replace(HANDLE h,const Site&s,bool patched){
 DWORD previous=0;if(!VirtualProtectEx(h,reinterpret_cast<void*>(s.address),s.patch_size,PAGE_EXECUTE_READWRITE,&previous))return false;
 bool ok=write(h,s.address,patched?s.replacement:s.expected,s.patch_size)&&FlushInstructionCache(h,reinterpret_cast<void*>(s.address),s.patch_size);
 DWORD ignored=0;bool protectedAgain=!!VirtualProtectEx(h,reinterpret_cast<void*>(s.address),s.patch_size,s.protection,&ignored);
 MEMORY_BASIC_INFORMATION m{};bool query=VirtualQueryEx(h,reinterpret_cast<void*>(s.address),&m,sizeof m)==sizeof m;
 return ok&&protectedAgain&&query&&m.Protect==s.protection&&siteBytes(h,s,patched);
}
// replace checks bytes and native protection restoration; the image ownership
// and entire six-profile check are repeated by the caller before resuming.
}
namespace {
bool mappedFile(HANDLE process,A base,HANDLE file){
 char mapped[32768]{},expected[32768]{};DWORD n=GetMappedFileNameA(process,reinterpret_cast<void*>(base),mapped,sizeof mapped);
 DWORD k=GetFinalPathNameByHandleA(file,expected,sizeof expected,FILE_NAME_NORMALIZED|VOLUME_NAME_NT);
 return n&&n<sizeof mapped&&k&&k<sizeof expected&&!_stricmp(mapped,expected);
}
bool number(const char*s,A&out){char*end=nullptr;errno=0;out=_strtoui64(s,&end,0);return s[0]&&s[0]!='-'&&end&&!*end&&!errno;}
bool nonceEqual(const char*text,const unsigned char*nonce){if(strlen(text)!=64)return false;for(unsigned i=0;i<32;i++){char part[3]={text[i*2],text[i*2+1],0};char*end=nullptr;auto v=strtoul(part,&end,16);if(*end||v!=nonce[i])return false;}return true;}
struct Outcome {const char*status="REJECTED_PREFLIGHT";bool attached=false,detached=false,held=false,uncertain=false;unsigned threads=0,mask=0,rolled=0;DWORD error=0;};
void report(const Outcome&o){printf("{\"status\":\"%s\",\"attached\":%s,\"detached\":%s,\"held_create_process_event\":%s,\"uncertain\":%s,\"threads_checked\":%u,\"written_mask\":%u,\"rolled_mask\":%u,\"error\":%lu,\"fixture_build\":%s,\"policy_module_expected\":true}\n",o.status,o.attached?"true":"false",o.detached?"true":"false",o.held?"true":"false",o.uncertain?"true":"false",o.threads,o.mask,o.rolled,o.error,ExpectedFixture?"true":"false");fflush(stdout);}
// Never terminates the target, moves its instruction pointers or writes unknown
// bytes. An unresolved write/detach failure leaves this debugger alive holding
// its owned event; operator can inspect it. Killing this tool is NOT recovery.
void retain(Outcome&o){o.status="RECOVERY_REQUIRED_EVENT_RETAINED";report(o);for(;;)Sleep(250);}
bool detach(DWORD pid,Outcome&o){if(DebugActiveProcessStop(pid)){o.detached=true;return true;}o.error=GetLastError();o.status="DETACH_FAILED";retain(o);}
}
int main(int argc,char**argv){
 // operation PID birth image descriptor stage.dll nonce exact-room-Config.bin
 Outcome o{};if(argc!=9){report(o);return 2;}A pidValue=0,born=0,image=0,descriptorAddress=0;
 std::string operation=argv[1];bool restore=operation=="restore"||operation=="check-installed";bool checkOnly=operation=="check"||operation=="check-installed";int fail=-1;
#ifdef HUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE
 if(operation.size()==10&&operation.rfind("rollback-",0)==0&&operation[9]>='0'&&operation[9]<='5')fail=operation[9]-'0';
#endif
 if((operation!="install"&&!restore&&!checkOnly&&fail<0)||!number(argv[2],pidValue)||!pidValue||pidValue>MAXDWORD||pidValue==GetCurrentProcessId()||!number(argv[3],born)||!number(argv[4],image)||!number(argv[5],descriptorAddress)){report(o);return 3;}
 DWORD pid=static_cast<DWORD>(pidValue);HANDLE process=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION|SYNCHRONIZE,FALSE,pid);
 if(!process){o.error=GetLastError();report(o);return 4;}
 char executable[32768]{};DWORD pathLength=sizeof executable;BOOL debugged=FALSE;
 if(!QueryFullProcessImageNameA(process,0,executable,&pathLength)||!identity(process,pid,born,executable)||!CheckRemoteDebuggerPresent(process,&debugged)||debugged){report(o);CloseHandle(process);return 5;}
 HANDLE exeFile=CreateFileA(executable,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr),stageFile=CreateFileA(argv[6],GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
 if(exeFile==INVALID_HANDLE_VALUE||stageFile==INVALID_HANDLE_VALUE||fileHash(executable)!=ApprovedExeSha||fileHash(argv[6])!=ApprovedStageSha){report(o);return 6;}
 HMODULE mainModule=nullptr;DWORD needed=0;if(!EnumProcessModulesEx(process,&mainModule,sizeof mainModule,&needed,LIST_MODULES_64BIT)||!mainModule){report(o);return 7;}
 A mainBase=reinterpret_cast<A>(mainModule);
 HANDLE imageFile=exeFile;
#ifdef HUMAN_RULES_ACTIVATION_PUBLISH_FIXTURE
 char imagePath[32768]{};if(!GetModuleFileNameExA(process,reinterpret_cast<HMODULE>(image),imagePath,sizeof imagePath)){report(o);return 8;}
 imageFile=CreateFileA(imagePath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
 if(imageFile==INVALID_HANDLE_VALUE||fileHash(imagePath)!=ApprovedImageSha){report(o);return 9;}
#else
 if(image!=mainBase){report(o);return 8;}
#endif
 HMODULE stageLocal=LoadLibraryExA(argv[6],nullptr,DONT_RESOLVE_DLL_REFERENCES);if(!stageLocal){report(o);return 10;}
 A descriptorRva=exportRva(stageLocal,"HumanRulesActivationDescriptor");Descriptor saved{};
 human_rules_activation::Config expectedBinding{};HANDLE bindingFile=CreateFileA(argv[8],GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);LARGE_INTEGER bindingSize{};DWORD bindingRead=0;
 bool bindingLoaded=bindingFile!=INVALID_HANDLE_VALUE&&GetFileSizeEx(bindingFile,&bindingSize)&&bindingSize.QuadPart==sizeof expectedBinding&&ReadFile(bindingFile,&expectedBinding,sizeof expectedBinding,&bindingRead,nullptr)&&bindingRead==sizeof expectedBinding;
 if(bindingFile!=INVALID_HANDLE_VALUE)CloseHandle(bindingFile);
 A stateRva=exportRva(stageLocal,"HumanRulesActivationState"),bindingRva=exportRva(stageLocal,"HumanRulesActivationBinding");
 IMAGE_DOS_HEADER stageDos{};IMAGE_NT_HEADERS64 stageNt{};memcpy(&stageDos,stageLocal,sizeof stageDos);
 if(stageDos.e_magic!=IMAGE_DOS_SIGNATURE||stageDos.e_lfanew<=0||stageDos.e_lfanew>0x1000){report(o);return 10;}memcpy(&stageNt,reinterpret_cast<void*>(reinterpret_cast<A>(stageLocal)+stageDos.e_lfanew),sizeof stageNt);
 if(stageNt.Signature!=IMAGE_NT_SIGNATURE||!stageNt.OptionalHeader.SizeOfImage){report(o);return 10;}const A stageSize=stageNt.OptionalHeader.SizeOfImage;
 std::array<A,5> exports={exportRva(stageLocal,"HumanRulesActivationForce"),exportRva(stageLocal,"HumanRulesActivationDistrict"),exportRva(stageLocal,"HumanRulesActivationArmy"),exportRva(stageLocal,"HumanRulesActivationGroup"),exportRva(stageLocal,"HumanRulesActivationIncome")};
 bool good=bindingLoaded&&stateRva&&bindingRva&&descriptorRva&&copiedDescriptor(process,descriptorAddress,saved)&&descriptorAddress==saved.module+descriptorRva&&nonceEqual(argv[7],saved.nonce)&&mappedFile(process,mainBase,exeFile)&&mappedFile(process,image,imageFile)&&mappedFile(process,saved.module,stageFile);
 for(auto r:exports)good=good&&r!=0;
 good=good&&validate(process,saved,pid,born,image,saved.module,exports,restore);
 ActivationInspection inspection{process,saved.module,stateRva,bindingRva,expectedBinding};
 good=good&&expectedBinding.image==image&&inspection.check(restore)&&counterCheck(process,saved.module);
 if(!good){report(o);return 11;}
 if(checkOnly){o.status="PASS_READ_ONLY_PREFLIGHT";report(o);return 0;}
 if(!DebugActiveProcess(pid)){o.error=GetLastError();report(o);return 12;}o.attached=true;
 // Set immediately after successful attach; do not ever depend on debugger
 // process death as a detach or recovery mechanism.
 if(!DebugSetProcessKillOnExit(FALSE)){o.error=GetLastError();if(!DebugActiveProcessStop(pid)){o.status="KILL_POLICY_FAILED_DETACH_FAILED";retain(o);}o.detached=true;report(o);return 13;}
 DEBUG_EVENT event{};
 if(!WaitForDebugEvent(&event,5000)){o.error=GetLastError();o.status="EVENT_TIMEOUT_NO_WRITES";detach(pid,o);report(o);return 14;}
 // An exclusively acquired initial attach event is the ONLY write permit.
 // Do not continue it to request another breakpoint or execute target code.
 good=event.dwProcessId==pid&&event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT&&event.u.CreateProcessInfo.lpStartAddress==nullptr&&reinterpret_cast<A>(event.u.CreateProcessInfo.lpBaseOfImage)==mainBase&&fileId(event.u.CreateProcessInfo.hFile,exeFile)&&GetProcessId(event.u.CreateProcessInfo.hProcess)==pid;
 if(!good){
  DWORD disposition=event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT?DBG_EXCEPTION_NOT_HANDLED:DBG_CONTINUE;
  if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT&&event.u.CreateProcessInfo.hFile)CloseHandle(event.u.CreateProcessInfo.hFile);
  if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT&&event.u.LoadDll.hFile)CloseHandle(event.u.LoadDll.hFile);
  if(!ContinueDebugEvent(event.dwProcessId,event.dwThreadId,disposition)){o.error=GetLastError();retain(o);}
  o.status="UNEXPECTED_EVENT_NO_WRITES";detach(pid,o);report(o);return 15;
 }
 o.held=true;Descriptor current{};
 good=identity(process,pid,born,executable)&&mappedFile(process,image,imageFile)&&mappedFile(process,saved.module,stageFile)&&copiedDescriptor(process,descriptorAddress,current)&&!memcmp(&saved,&current,sizeof saved)&&validate(process,saved,pid,born,image,saved.module,exports,restore)&&inspection.check(restore)&&counterCheck(process,saved.module)&&contexts(pid,saved,o.threads,stageSize);
 if(!good){o.status="REJECTED_HELD_NO_WRITES";CloseHandle(event.u.CreateProcessInfo.hFile);detach(pid,o);report(o);return 16;}
 bool changed=true;
 for(unsigned i=0;i<6;i++){o.mask|=1u<<i;if(!replace(process,saved.sites[i],!restore)||static_cast<int>(i)==fail){changed=false;break;}}
 if(changed)changed=validate(process,saved,pid,born,image,saved.module,exports,!restore)&&inspection.check(restore)&&counterCheck(process,saved.module);
 if(!changed){
  for(int i=5;i>=0;i--)if(o.mask&(1u<<i)){
   const auto&s=saved.sites[i];
   // If a write never happened, preserve the exact original transaction state.
   if(siteBytes(process,s,restore)&&region(process,s.address,s.profile_size,image,MEM_IMAGE,s.protection)){o.rolled|=1u<<i;continue;}
   if(siteBytes(process,s,!restore)&&replace(process,s,restore))o.rolled|=1u<<i;else o.uncertain=true;
  }
  if(!validate(process,saved,pid,born,image,saved.module,exports,restore))o.uncertain=true;
  o.status=o.uncertain?"UNCERTAIN_NO_DETACH":"CLEAN_ROLLBACK";
  if(o.uncertain){CloseHandle(event.u.CreateProcessInfo.hFile);retain(o);}
 }else o.status=restore?"RESTORED":"INSTALLED_HUMAN_RULES";
 CloseHandle(event.u.CreateProcessInfo.hFile);
 // Direct detach with this initial event pending is deliberately used. It was
 // observed on the supported local Windows build to cancel the attach startup
 // breakpoint, resume all threads and preserve later application exceptions.
 detach(pid,o);report(o);
 FreeLibrary(stageLocal);if(imageFile!=exeFile)CloseHandle(imageFile);CloseHandle(stageFile);CloseHandle(exeFile);CloseHandle(process);
 return changed?0:17;
}
