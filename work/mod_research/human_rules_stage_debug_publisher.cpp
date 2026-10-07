#include "human_rules_passthrough_stage.h"
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
#pragma comment(lib,"advapi32.lib")
namespace {
using A=std::uint64_t;
using human_rules_stage::Descriptor;
using human_rules_stage::Site;
bool read(HANDLE h,A a,void*b,SIZE_T n){SIZE_T done=0;return ReadProcessMemory(h,reinterpret_cast<void*>(a),b,n,&done)&&done==n;}
bool write(HANDLE h,A a,const void*b,SIZE_T n){SIZE_T done=0;return WriteProcessMemory(h,reinterpret_cast<void*>(a),b,n,&done)&&done==n;}
bool same(HANDLE h,A a,const void*b,SIZE_T n){std::vector<unsigned char>v(n);return read(h,a,v.data(),n)&&!memcmp(v.data(),b,n);}
bool region(HANDLE h,A a,SIZE_T n,A allocation,DWORD type,DWORD protection){MEMORY_BASIC_INFORMATION m{};return a+n>a&&VirtualQueryEx(h,reinterpret_cast<void*>(a),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==type&&m.Protect==protection&&reinterpret_cast<A>(m.AllocationBase)==allocation&&a+n<=reinterpret_cast<A>(m.BaseAddress)+m.RegionSize;}
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
bool contexts(DWORD pid,const Descriptor&d,unsigned&count){
 HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(snapshot==INVALID_HANDLE_VALUE)return false;
 THREADENTRY32 entry{};entry.dwSize=sizeof entry;bool ok=!!Thread32First(snapshot,&entry);count=0;
 while(ok){if(entry.th32OwnerProcessID==pid){HANDLE thread=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,entry.th32ThreadID);CONTEXT c{};c.ContextFlags=CONTEXT_ALL;
  if(!thread||GetProcessIdOfThread(thread)!=pid||!GetThreadContext(thread,&c)){if(thread)CloseHandle(thread);ok=false;break;}CloseHandle(thread);++count;
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
 if(!directory.VirtualAddress||directory.Size%sizeof(RUNTIME_FUNCTION)||directory.Size>4096*sizeof(RUNTIME_FUNCTION)||A(directory.VirtualAddress)+directory.Size>nt.OptionalHeader.SizeOfImage)return false;
 std::vector<RUNTIME_FUNCTION> entries(directory.Size/sizeof(RUNTIME_FUNCTION));if(!read(h,image+directory.VirtualAddress,entries.data(),directory.Size))return false;
 for(const auto&w:human_rules_hook::Unwinds){bool found=false;for(const auto&e:entries)if(e.BeginAddress==w.start&&e.EndAddress==w.end&&e.UnwindData==w.rva)found=true;if(!found||!same(h,image+w.rva,w.bytes,w.size))return false;}return true;
}
void jump(unsigned char*out,A to){out[0]=0xff;out[1]=0x25;memset(out+2,0,4);memcpy(out+6,&to,8);}
bool siteBytes(HANDLE h,const Site&s,bool patched){return same(h,s.address,patched?s.replacement:s.expected,s.patch_size)&&same(h,s.address+s.patch_size,s.expected+s.patch_size,s.profile_size-s.patch_size);}
bool validate(HANDLE h,const Descriptor&d,DWORD pid,A born,A image,A stage,const std::array<A,5>&exports,bool patched){
 if(d.magic!=human_rules_stage::Magic||d.version!=1||d.size!=sizeof d||d.pid!=pid||d.birth!=born||d.fixture!=1||d.image!=image||d.module!=stage||d.preparation_state!=human_rules_stage::Prepared||d.site_count!=6||d.policy_enabled||d.reserved||!d.allocation)return false;
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
int main(int argc,char**argv){
 if(argc!=10)return 2;std::array<std::string,4> paths={argv[1],argv[3],argv[5],argv[7]};std::string mode=argv[9];std::array<HANDLE,4> files{};
 for(unsigned i=0;i<4;i++){files[i]=CreateFileA(paths[i].c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(files[i]==INVALID_HANDLE_VALUE||fileHash(paths[i].c_str())!=argv[2+i*2])return 3;}
 HMODULE targetLocal=LoadLibraryExA(paths[0].c_str(),nullptr,DONT_RESOLVE_DLL_REFERENCES),stageLocal=LoadLibraryExA(paths[1].c_str(),nullptr,DONT_RESOLVE_DLL_REFERENCES);if(!targetLocal||!stageLocal)return 4;
 A pointerRva=exportRva(targetLocal,"HumanRulesStageDescriptorPointer"),breakRva=exportRva(targetLocal,"HumanRulesStageDebugBreak"),descriptorRva=exportRva(stageLocal,"HumanRulesStageDescriptor");if(!pointerRva||!breakRva||!descriptorRva)return 5;
 std::array<A,5> exports={exportRva(stageLocal,"HumanRulesStageForce"),exportRva(stageLocal,"HumanRulesStageDistrict"),exportRva(stageLocal,"HumanRulesStageArmy"),exportRva(stageLocal,"HumanRulesStageGroup"),exportRva(stageLocal,"HumanRulesStageIncome")};for(auto r:exports)if(!r)return 6;
 std::string command='"'+paths[0]+'"'+" "+mode;for(unsigned i=1;i<4;i++)command+=" \""+paths[i]+"\"";std::vector<char> mutableCommand(command.begin(),command.end());mutableCommand.push_back(0);
 STARTUPINFOA startup{};startup.cb=sizeof startup;PROCESS_INFORMATION process{};
 if(!CreateProcessA(paths[0].c_str(),mutableCommand.data(),nullptr,nullptr,FALSE,DEBUG_ONLY_THIS_PROCESS|CREATE_NO_WINDOW,nullptr,nullptr,&startup,&process))return 7;
 DebugSetProcessKillOnExit(TRUE);FILETIME t[4]{};if(!GetProcessTimes(process.hProcess,&t[0],&t[1],&t[2],&t[3]))return 8;A born=(A(t[0].dwHighDateTime)<<32)|t[0].dwLowDateTime;
 A target=0,stage=0,image=0;Descriptor saved{};unsigned owned=0,threads=0,firstThreads=0,restoreThreads=0,written=0,rolled=0;bool installed=false,restored=false,uncertain=false,rejected=false,finished=false,startupBreak=false,validated=false;DWORD exitCode=0;ULONGLONG deadline=GetTickCount64()+20000;
 while(!finished&&GetTickCount64()<deadline){
  DEBUG_EVENT event{};if(!WaitForDebugEvent(&event,200)){if(GetLastError()==ERROR_SEM_TIMEOUT)continue;break;}DWORD next=DBG_CONTINUE;bool terminate=event.dwProcessId!=process.dwProcessId;
  if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT){if(!fileId(event.u.CreateProcessInfo.hFile,files[0]))terminate=true;target=reinterpret_cast<A>(event.u.CreateProcessInfo.lpBaseOfImage);if(event.u.CreateProcessInfo.hFile)CloseHandle(event.u.CreateProcessInfo.hFile);}
  else if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT){auto&e=event.u.LoadDll;if(e.hFile){if(fileId(e.hFile,files[1]))stage=reinterpret_cast<A>(e.lpBaseOfDll);if(fileId(e.hFile,files[2]))image=reinterpret_cast<A>(e.lpBaseOfDll);CloseHandle(e.hFile);}}
  else if(event.dwDebugEventCode==UNLOAD_DLL_DEBUG_EVENT){A at=reinterpret_cast<A>(event.u.UnloadDll.lpBaseOfDll);if(at==stage||at==image){stage=image=0;if(installed&&!restored)terminate=true;}}
  else if(event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT){auto&e=event.u.Exception;
   bool ours=target&&e.dwFirstChance&&e.ExceptionRecord.ExceptionCode==EXCEPTION_BREAKPOINT&&event.dwThreadId==process.dwThreadId&&reinterpret_cast<A>(e.ExceptionRecord.ExceptionAddress)==target+breakRva;
   if(ours){++owned;CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL;A pointer=0;unsigned char int3=0;Descriptor current{};
    bool valid=identity(process.hProcess,process.dwProcessId,born,paths[0])&&stage&&image&&read(process.hProcess,target+pointerRva,&pointer,8)&&pointer==stage+descriptorRva&&read(process.hProcess,target+breakRva,&int3,1)&&int3==0xcc&&GetThreadContext(process.hThread,&c)&&c.Rip==target+breakRva+1&&copiedDescriptor(process.hProcess,pointer,current)&&validate(process.hProcess,current,process.dwProcessId,born,image,stage,exports,installed&&!restored)&&contexts(process.dwProcessId,current,threads);
    if(owned==2)valid=valid&&!memcmp(&current,&saved,sizeof current);
    if(valid){validated=true;if(owned==1)firstThreads=threads;else if(owned==2)restoreThreads=threads;}
    if(!valid||owned>2){rejected=true;terminate=true;}
    else if(owned==1){memcpy(&saved,&current,sizeof saved);bool ok=true;int fail=mode.rfind("rollback-",0)==0?atoi(mode.c_str()+9):-1;
     for(unsigned i=0;i<6;i++){written|=1u<<i;if(!replace(process.hProcess,saved.sites[i],true)||static_cast<int>(i)==fail){ok=false;break;}}
     if(ok)ok=validate(process.hProcess,saved,process.dwProcessId,born,image,stage,exports,true);
     if(ok)installed=true;else{for(int i=5;i>=0;i--)if(written&(1u<<i)){if(siteBytes(process.hProcess,saved.sites[i],true)&&replace(process.hProcess,saved.sites[i],false))rolled|=1u<<i;else uncertain=true;}if(!validate(process.hProcess,saved,process.dwProcessId,born,image,stage,exports,false))uncertain=true;if(uncertain)terminate=true;}
    }else if(installed){bool ok=true;for(int i=5;i>=0;i--)if(!replace(process.hProcess,saved.sites[i],false)){ok=false;break;}restored=ok&&validate(process.hProcess,saved,process.dwProcessId,born,image,stage,exports,false);if(!restored){uncertain=true;terminate=true;}}
   }else if(e.ExceptionRecord.ExceptionCode==EXCEPTION_BREAKPOINT&&!startupBreak&&!owned){startupBreak=true;}
   else next=DBG_EXCEPTION_NOT_HANDLED;
  }else if(event.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT){exitCode=event.u.ExitProcess.dwExitCode;finished=true;}
  if(terminate)TerminateProcess(process.hProcess,91);
  if(!ContinueDebugEvent(event.dwProcessId,event.dwThreadId,next))break;
 }
 if(!finished){TerminateProcess(process.hProcess,92);WaitForSingleObject(process.hProcess,5000);}
 bool pass=finished&&exitCode==0&&owned==2&&!rejected&&!uncertain;
 if(mode.rfind("rollback-",0)==0)pass=pass&&written&&written==rolled&&!installed;else pass=pass&&installed&&restored;
 printf("{\"case\":\"%s\",\"passed\":%s,\"owned_events\":%u,\"threads_checked\":%u,\"first_event_threads_checked\":%u,\"restore_event_threads_checked\":%u,\"written_mask\":%u,\"rolled_mask\":%u,\"installed\":%s,\"restored\":%s,\"uncertain\":%s,\"rejected\":%s,\"child_exit\":%lu,\"six_actual_profiles_validated\":%s,\"source_MEM_IMAGE_verified\":%s,\"game_access\":false}\n",mode.c_str(),pass?"true":"false",owned,threads,firstThreads,restoreThreads,written,rolled,installed?"true":"false",restored?"true":"false",uncertain?"true":"false",rejected?"true":"false",exitCode,validated?"true":"false",validated?"true":"false");
 CloseHandle(process.hThread);CloseHandle(process.hProcess);FreeLibrary(stageLocal);FreeLibrary(targetLocal);for(HANDLE f:files)CloseHandle(f);return pass?0:20;
}
