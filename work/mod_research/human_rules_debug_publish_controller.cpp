#include "human_rules_debug_publish_shared.h"
#include <tlhelp32.h>
#include <wincrypt.h>
#include <array>
#include <vector>
#include <string>
#include <cstdio>
#include <cstring>
#include <algorithm>
#pragma comment(lib,"advapi32.lib")
namespace {
using A=std::uint64_t;
struct Site{A address=0;std::array<unsigned char,14> before{},after{};DWORD protection=0;};
bool read(HANDLE h,A a,void*b,SIZE_T n){SIZE_T done=0;return ReadProcessMemory(h,reinterpret_cast<void*>(a),b,n,&done)&&done==n;}
bool write(HANDLE h,A a,const void*b,SIZE_T n){SIZE_T done=0;return WriteProcessMemory(h,reinterpret_cast<void*>(a),b,n,&done)&&done==n;}
bool executable(DWORD p){return p==PAGE_EXECUTE_READ||p==PAGE_EXECUTE||p==PAGE_EXECUTE_READWRITE||p==PAGE_EXECUTE_WRITECOPY;}
bool imagePage(HANDLE h,A a,A base,DWORD&protection){MEMORY_BASIC_INFORMATION m{};if(!VirtualQueryEx(h,reinterpret_cast<void*>(a),&m,sizeof m)||m.State!=MEM_COMMIT||m.Type!=MEM_IMAGE||reinterpret_cast<A>(m.AllocationBase)!=base||!executable(m.Protect)||a+14>reinterpret_cast<A>(m.BaseAddress)+m.RegionSize)return false;protection=m.Protect;return true;}
std::string fileHash(const char*path){
 HANDLE f=CreateFileA(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(f==INVALID_HANDLE_VALUE)return {};
 HCRYPTPROV provider=0;HCRYPTHASH hash=0;bool ok=CryptAcquireContext(&provider,nullptr,nullptr,PROV_RSA_AES,CRYPT_VERIFYCONTEXT)&&CryptCreateHash(provider,CALG_SHA_256,0,0,&hash);
 unsigned char buffer[65536];DWORD count=0;
 while(ok){if(!ReadFile(f,buffer,sizeof buffer,&count,nullptr)){ok=false;break;}if(!count)break;ok=!!CryptHashData(hash,buffer,count,0);}
 unsigned char digest[32];DWORD n=32;ok=ok&&CryptGetHashParam(hash,HP_HASHVAL,digest,&n,0)&&n==32;
 if(hash)CryptDestroyHash(hash);if(provider)CryptReleaseContext(provider,0);CloseHandle(f);
 std::string out;if(ok)for(auto b:digest){char part[3];sprintf_s(part,"%02x",b);out+=part;}return out;
}
bool identity(HANDLE h,DWORD pid,const FILETIME&born,const std::string&path){FILETIME a,b,c,d;char actual[32768];DWORD n=sizeof actual;return GetProcessId(h)==pid&&GetProcessTimes(h,&a,&b,&c,&d)&&a.dwLowDateTime==born.dwLowDateTime&&a.dwHighDateTime==born.dwHighDateTime&&QueryFullProcessImageNameA(h,0,actual,&n)&&!_stricmp(actual,path.c_str())&&WaitForSingleObject(h,0)==WAIT_TIMEOUT;}
bool contexts(DWORD pid,const std::array<Site,6>&sites,unsigned&count){
 HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(snapshot==INVALID_HANDLE_VALUE)return false;
 THREADENTRY32 entry{};entry.dwSize=sizeof entry;bool ok=!!Thread32First(snapshot,&entry);count=0;
 while(ok){if(entry.th32OwnerProcessID==pid){HANDLE thread=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,entry.th32ThreadID);CONTEXT context{};context.ContextFlags=CONTEXT_ALL;
  if(!thread||GetProcessIdOfThread(thread)!=pid||!GetThreadContext(thread,&context)){if(thread)CloseHandle(thread);ok=false;break;}CloseHandle(thread);++count;
  for(const auto&s:sites)if(context.Rip>=s.address&&context.Rip<s.address+s.before.size()){ok=false;break;}if(!ok)break;}
  if(!Thread32Next(snapshot,&entry)){ok=GetLastError()==ERROR_NO_MORE_FILES;break;}
 }CloseHandle(snapshot);return ok&&count>=4;
}
bool bytesEqual(HANDLE h,const Site&s,bool patched){std::array<unsigned char,14>b{};return read(h,s.address,b.data(),b.size())&&b==(patched?s.after:s.before);}
// No externally supplied "paused" flag: this function is private to the owning
// debugger loop, invoked only while its exact owned event remains uncontinued.
bool replace(HANDLE h,const Site&s,bool patched){
 DWORD previous=0;if(!VirtualProtectEx(h,reinterpret_cast<void*>(s.address),s.before.size(),PAGE_EXECUTE_READWRITE,&previous))return false;
 const auto&b=patched?s.after:s.before;
 bool ok=write(h,s.address,b.data(),b.size())&&FlushInstructionCache(h,reinterpret_cast<void*>(s.address),b.size());
 DWORD temporary=0;bool restored=!!VirtualProtectEx(h,reinterpret_cast<void*>(s.address),b.size(),s.protection,&temporary);
 DWORD protection=0;MEMORY_BASIC_INFORMATION m{};bool query=!!VirtualQueryEx(h,reinterpret_cast<void*>(s.address),&m,sizeof m);if(query)protection=m.Protect;
 return ok&&restored&&query&&protection==s.protection&&bytesEqual(h,s,patched);
}
}
int main(int argc,char**argv){
 if(argc!=4)return 2;std::string path=argv[1],mode=argv[3];
 // Keep the verified backing executable non-writable/non-deletable until exit.
 HANDLE approvedFile=CreateFileA(path.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
 if(approvedFile==INVALID_HANDLE_VALUE||fileHash(path.c_str())!=argv[2])return 3;
 HMODULE local=LoadLibraryExA(path.c_str(),nullptr,DONT_RESOLVE_DLL_REFERENCES);if(!local)return 4;
 auto localBase=reinterpret_cast<A>(local);auto exported=GetProcAddress(local,"PublishManifest");if(!exported)return 5;
 A manifestRva=reinterpret_cast<A>(exported)-localBase;
 auto*dos=reinterpret_cast<IMAGE_DOS_HEADER*>(local);auto*nt=reinterpret_cast<IMAGE_NT_HEADERS64*>(localBase+dos->e_lfanew);DWORD imageSize=nt->OptionalHeader.SizeOfImage;
 if(nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64)return 6;
 STARTUPINFOA startup{};startup.cb=sizeof startup;PROCESS_INFORMATION process{};
 std::string command='"'+path+'"'+" "+mode;std::vector<char> mutableCommand(command.begin(),command.end());mutableCommand.push_back(0);
 if(!CreateProcessA(path.c_str(),mutableCommand.data(),nullptr,nullptr,FALSE,DEBUG_ONLY_THIS_PROCESS|CREATE_NO_WINDOW,nullptr,nullptr,&startup,&process))return 7;
 // Fail-safe scope: only this newly created child is debugged. Debugger death
 // terminates it; no attach, detach, resume-on-uncertain or arbitrary PID API.
 DebugSetProcessKillOnExit(TRUE);
 FILETIME born{},unused1{},unused2{},unused3{};GetProcessTimes(process.hProcess,&born,&unused1,&unused2,&unused3);
 A base=0;unsigned ownedEvents=0,threads=0,written=0,rolled=0;bool installed=false,restored=false,rejected=false,uncertain=false,frozen=false,identityOk=true,startupBreakSeen=false;DWORD exitCode=0;bool finished=false;std::array<Site,6>sites{};
 ULONGLONG deadline=GetTickCount64()+15000;
 while(!finished&&GetTickCount64()<deadline){
  DEBUG_EVENT event{};if(!WaitForDebugEvent(&event,200)){if(GetLastError()==ERROR_SEM_TIMEOUT)continue;identityOk=false;break;}
  DWORD continuation=DBG_CONTINUE;bool terminate=false;
  if(event.dwProcessId!=process.dwProcessId){identityOk=false;terminate=true;}
  if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT){base=reinterpret_cast<A>(event.u.CreateProcessInfo.lpBaseOfImage);if(event.u.CreateProcessInfo.hFile)CloseHandle(event.u.CreateProcessInfo.hFile);}
  else if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT){if(event.u.LoadDll.hFile)CloseHandle(event.u.LoadDll.hFile);}
  else if(event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT){
   auto&e=event.u.Exception;Manifest m{};bool owned=base&&read(process.hProcess,base+manifestRva,&m,sizeof m)&&m.magic==Magic&&event.dwThreadId==process.dwThreadId&&e.ExceptionRecord.ExceptionCode==EXCEPTION_BREAKPOINT&&e.dwFirstChance&&reinterpret_cast<A>(e.ExceptionRecord.ExceptionAddress)==m.owned_break;
   if(owned){++ownedEvents;
    FILETIME expectedBirth=born;if(mode=="identity-reject"&&ownedEvents==1)expectedBirth.dwLowDateTime^=1;
    identityOk=identity(process.hProcess,process.dwProcessId,expectedBirth,path);unsigned char int3=0;
    CONTEXT breaking{};breaking.ContextFlags=CONTEXT_CONTROL;
    identityOk=identityOk&&m.owned_break>=base&&m.owned_break<base+imageSize&&read(process.hProcess,m.owned_break,&int3,1)&&int3==0xcc&&GetThreadContext(process.hThread,&breaking)&&breaking.Rip==m.owned_break+1;
    if(!identityOk){rejected=true;if(mode!="identity-reject")terminate=true;}
    else if(ownedEvents==1){
     bool profile=true;
     for(unsigned i=0;i<6;i++){
      auto&s=sites[i];s.address=m.sites[i];
      if(s.address<base||s.address+14>base+imageSize||m.hooks[i]<base||m.hooks[i]+14>base+imageSize){profile=false;break;}
      memcpy(s.before.data(),reinterpret_cast<void*>(localBase+s.address-base),14);s.after={0xff,0x25,0,0,0,0};memcpy(s.after.data()+6,&m.hooks[i],8);
      DWORD hookProtect=0;MEMORY_BASIC_INFORMATION originalPage{};
      if(!VirtualQuery(reinterpret_cast<void*>(localBase+s.address-base),&originalPage,sizeof originalPage)||!imagePage(process.hProcess,s.address,base,s.protection)||s.protection!=originalPage.Protect||!imagePage(process.hProcess,m.hooks[i],base,hookProtect)||!bytesEqual(process.hProcess,s,false))profile=false;
      for(unsigned j=0;j<i;j++)if(s.address<sites[j].address+14&&sites[j].address<s.address+14)profile=false;
     }
     LONG64 first=0,last=1;frozen=read(process.hProcess,m.counter,&first,8);Sleep(100);frozen=frozen&&read(process.hProcess,m.counter,&last,8)&&first>0&&first==last;
     bool safe=identityOk&&profile&&frozen&&contexts(process.dwProcessId,sites,threads);
     if(!safe){rejected=true;if(mode!="rip-in-range"&&mode!="identity-reject"&&mode!="preimage-drift"&&mode!="protection-drift")terminate=true;}
     else if(mode=="target-exception"){} // Observe normal target exception policy, without patching.
     else {
      bool ok=true;int fail=-1;if(mode.rfind("rollback-",0)==0)fail=atoi(mode.c_str()+9);
      for(unsigned i=0;i<6;i++){written|=1u<<i;if(!replace(process.hProcess,sites[i],true)){ok=false;break;}
       if(static_cast<int>(i)==fail){ok=false;break;}
       if(mode=="uncertain"&&i==2){unsigned char foreign=0xcc;DWORD old=0;VirtualProtectEx(process.hProcess,reinterpret_cast<void*>(sites[i].address),14,PAGE_EXECUTE_READWRITE,&old);write(process.hProcess,sites[i].address,&foreign,1);DWORD ignored=0;VirtualProtectEx(process.hProcess,reinterpret_cast<void*>(sites[i].address),14,old,&ignored);FlushInstructionCache(process.hProcess,reinterpret_cast<void*>(sites[i].address),14);ok=false;break;}
      }
      if(ok)installed=true;
      else {for(int i=5;i>=0;i--)if(written&(1u<<i)){if(bytesEqual(process.hProcess,sites[i],true)&&replace(process.hProcess,sites[i],false)){rolled|=1u<<i;}else uncertain=true;}if(uncertain)terminate=true;}
     }
    }else if(ownedEvents==2&&installed){
     bool ok=contexts(process.dwProcessId,sites,threads);
     for(const auto&s:sites){DWORD p=0;ok=ok&&imagePage(process.hProcess,s.address,base,p)&&p==s.protection&&bytesEqual(process.hProcess,s,true);}
     if(ok)for(int i=5;i>=0;i--)if(!replace(process.hProcess,sites[i],false)){ok=false;break;}
     restored=ok;if(!ok){uncertain=true;terminate=true;}
    }else if(ownedEvents>2){terminate=true;}
   }else if(e.ExceptionRecord.ExceptionCode!=EXCEPTION_BREAKPOINT){continuation=DBG_EXCEPTION_NOT_HANDLED;}
   // The sole non-owned BREAKPOINT accepted below is the OS startup breakpoint,
   // before manifest initialization. Other breakpoint events never authorize writes.
   else if(m.magic==Magic||startupBreakSeen){continuation=DBG_EXCEPTION_NOT_HANDLED;}
   else startupBreakSeen=true;
  }else if(event.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT){exitCode=event.u.ExitProcess.dwExitCode;finished=true;}
  if(terminate)TerminateProcess(process.hProcess,91);
  if(!ContinueDebugEvent(event.dwProcessId,event.dwThreadId,continuation)){identityOk=false;break;}
 }
 if(!finished){TerminateProcess(process.hProcess,92);WaitForSingleObject(process.hProcess,5000);}
 bool passed=finished&&(frozen||mode=="identity-reject");
 if(mode=="routes")passed=passed&&identityOk&&installed&&restored&&ownedEvents==2&&exitCode==0;
 else if(mode=="rip-in-range"||mode=="identity-reject"||mode=="preimage-drift"||mode=="protection-drift")passed=passed&&rejected&&!written&&exitCode==0;
 else if(mode=="uncertain")passed=passed&&uncertain&&!restored&&exitCode==91;
 else if(mode=="target-exception")passed=passed&&!written&&exitCode==0xE0421234;
 else passed=passed&&written&&written==rolled&&!uncertain&&exitCode==0;
 printf("{\"case\":\"%s\",\"passed\":%s,\"all_threads_observed_stopped\":%s,\"threads_checked\":%u,\"owned_events\":%u,\"written_mask\":%u,\"rolled_back_mask\":%u,\"installed\":%s,\"restored\":%s,\"rejected\":%s,\"uncertain\":%s,\"child_exit\":%lu,\"actual_mem_image\":true,\"game_access\":false}\n",mode.c_str(),passed?"true":"false",frozen?"true":"false",threads,ownedEvents,written,rolled,installed?"true":"false",restored?"true":"false",rejected?"true":"false",uncertain?"true":"false",exitCode);
 CloseHandle(process.hThread);CloseHandle(process.hProcess);FreeLibrary(local);CloseHandle(approvedFile);return passed?0:20;
}
