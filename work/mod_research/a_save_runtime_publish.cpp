// A-only external publisher. No remote execution while the attach event is held.
#include "a_save_runtime_exports.h"
#include <tlhelp32.h>
#include <psapi.h>
#include <bcrypt.h>
#include <cstdio>
#include <cstring>
#include <vector>
#include <string>
#include <fstream>
#include <array>
#pragma comment(lib,"bcrypt.lib")
#pragma comment(lib,"psapi.lib")
namespace w=a_save_runtime_wire;using A=std::uint64_t;
namespace {
struct Outcome{const char*status="REJECTED_PREFLIGHT";bool attached=false,detached=false,uncertain=false;unsigned written_mask=0,rolled_mask=0,threads_checked=0;DWORD error=0;};
void report(const Outcome&o){printf("{\"status\":\"%s\",\"attached\":%s,\"detached\":%s,\"uncertain\":%s,\"written_mask\":%u,\"rolled_mask\":%u,\"threads_checked\":%u,\"error\":%lu}\n",o.status,o.attached?"true":"false",o.detached?"true":"false",o.uncertain?"true":"false",o.written_mask,o.rolled_mask,o.threads_checked,o.error);fflush(stdout);}
[[noreturn]]void retain(Outcome&o){o.status="RECOVERY_REQUIRED_EVENT_RETAINED";o.uncertain=true;report(o);for(;;)Sleep(250);}
bool read(HANDLE h,A a,void*p,SIZE_T n){SIZE_T z=0;return ReadProcessMemory(h,reinterpret_cast<void*>(a),p,n,&z)&&z==n;}
bool same(HANDLE h,A a,const void*p,SIZE_T n){unsigned char b[32]{};return n<=sizeof b&&read(h,a,b,n)&&!memcmp(b,p,n);}
bool region(HANDLE h,A a,SIZE_T n,A allocation,DWORD type,DWORD protect){MEMORY_BASIC_INFORMATION m{};return a&&a+n>a&&VirtualQueryEx(h,reinterpret_cast<void*>(a),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==type&&m.Protect==protect&&A(m.AllocationBase)==allocation&&a+n<=A(m.BaseAddress)+m.RegionSize;}
template<class T>bool file(const wchar_t*name,T&out){HANDLE h=CreateFileW(name,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(h==INVALID_HANDLE_VALUE)return false;LARGE_INTEGER n{};DWORD z=0;const bool ok=GetFileSizeEx(h,&n)&&n.QuadPart==sizeof out&&ReadFile(h,&out,sizeof out,&z,nullptr)&&z==sizeof out;CloseHandle(h);return ok;}
std::wstring hash(const wchar_t*path){HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(h==INVALID_HANDLE_VALUE)return {};BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE ctx=nullptr;DWORD n=0,z=0;std::wstring result;
 bool ok=BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0&&BCryptGetProperty(alg,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&n),4,&z,0)>=0;std::vector<unsigned char>buf(n);unsigned char bytes[65536],digest[32]{};
 if(ok)ok=BCryptCreateHash(alg,&ctx,buf.data(),n,nullptr,0,0)>=0;while(ok){if(!ReadFile(h,bytes,sizeof bytes,&z,nullptr)){ok=false;break;}if(!z)break;ok=BCryptHashData(ctx,bytes,z,0)>=0;}if(ok)ok=BCryptFinishHash(ctx,digest,32,0)>=0;
 if(ok)for(auto b:digest){wchar_t v[3]{};swprintf_s(v,L"%02x",b);result+=v;}if(ctx)BCryptDestroyHash(ctx);if(alg)BCryptCloseAlgorithmProvider(alg,0);CloseHandle(h);return result;}
bool number(const wchar_t*s,A&v){wchar_t*end=nullptr;errno=0;v=_wcstoui64(s,&end,0);return *s&&*s!=L'-'&&!*end&&!errno;}
bool identity(HANDLE h,DWORD pid,A born,A base){FILETIME a{},x{},y{},z{};HMODULE first=nullptr;DWORD n=0;return GetProcessId(h)==pid&&GetProcessTimes(h,&a,&x,&y,&z)&&((A(a.dwHighDateTime)<<32)|a.dwLowDateTime)==born&&EnumProcessModulesEx(h,&first,sizeof first,&n,LIST_MODULES_64BIT)&&A(first)==base&&WaitForSingleObject(h,0)==WAIT_TIMEOUT;}
bool mapped(HANDLE h,A base,HANDLE fileHandle){wchar_t actual[32768]{},expected[32768]{};auto n=GetMappedFileNameW(h,reinterpret_cast<void*>(base),actual,32768);auto m=GetFinalPathNameByHandleW(fileHandle,expected,32768,FILE_NAME_NORMALIZED|VOLUME_NAME_NT);return n&&n<32768&&m&&m<32768&&!_wcsicmp(actual,expected);}
bool fileIdentity(HANDLE a,HANDLE b){BY_HANDLE_FILE_INFORMATION x{},y{};return GetFileInformationByHandle(a,&x)&&GetFileInformationByHandle(b,&y)&&x.dwVolumeSerialNumber==y.dwVolumeSerialNumber&&x.nFileIndexHigh==y.nFileIndexHigh&&x.nFileIndexLow==y.nFileIndexLow;}
struct Item{A at=0;unsigned size=0;DWORD protection=0;unsigned char prior[8]{},desired[8]{};};
bool envelope(const w::Header&h,size_t size,w::Op op){return h.magic==w::Magic&&h.version==w::Version&&h.size==size&&h.operation==unsigned(op)&&h.result==unsigned(w::Result::Ok);}
bool counters(HANDLE h,const w::Plans&p,const w::Snapshot&s,bool idle){
 for(unsigned i=0;i<7;++i){const auto&v=s.counters[i];if((v.startedAddress&7)||(v.activeAddress&7)||v.startedAddress==v.activeAddress||v.startedAddress!=p.counters[i].startedAddress||v.activeAddress!=p.counters[i].activeAddress||!region(h,v.startedAddress,8,p.module,MEM_IMAGE,PAGE_READWRITE)||!region(h,v.activeAddress,8,p.module,MEM_IMAGE,PAGE_READWRITE))return false;
  A started=0,active=1;if(!read(h,v.startedAddress,&started,8)||!read(h,v.activeAddress,&active,8)||(idle&&active))return false;
  for(unsigned j=0;j<i;++j)if(v.startedAddress==s.counters[j].startedAddress||v.activeAddress==s.counters[j].activeAddress||v.startedAddress==s.counters[j].activeAddress||v.activeAddress==s.counters[j].startedAddress)return false;
 }return true;
}
bool stopped(HANDLE h,const w::Plans&p,const w::Snapshot&s){
 if(!s.stopped||!s.ownerStopped||!s.mailboxStopped||s.saveLane||s.saveActive||s.ownerActive||s.gateActive||s.parentActive||s.parentBefore!=s.parentAfter||s.parentAfter!=s.parentFinally)return false;
 if(s.saveStatus!=0&&s.saveStatus!=5&&s.saveStatus!=8)return false;
 if(s.saveStatus==5&&(!s.workerJoined||!s.originalReturned||!s.fileVerified||s.saveError))return false;
 if(s.saveStatus==8&&(s.binds||s.queues))return false;
 if(!region(h,s.hostCacheAddress,sizeof(w::HostCache),p.module,MEM_IMAGE,PAGE_READWRITE))return false;
 w::HostCache a{},b{};if(!read(h,s.hostCacheAddress,&a,sizeof a)||!read(h,s.hostCacheAddress,&b,sizeof b)||memcmp(&a,&b,sizeof a)||(a.sequence&1)||a.lease||a.frame||(s.hostInitialized&&!a.valid))return false;
 return true;
}
bool plan(HANDLE h,const w::Plans&p,const w::Snapshot&s,bool install,bool restore,std::array<Item,7>&items,bool held=false){
 const A sites[]={0x3F8606,0x3F9B16,0x13DC09},slots[]={0x12CC4D0,0x12DC620,0x12CC9E0,0x1297D10},originals[]={0x3F9B00,0x4AA650,0x3F8140,0x1AC3C0};
 const unsigned char raw[3][5]={{0xe8,0x15,0x22,0,0},{0xe8,0x05,0x5f,0xd6,0xff},{0xe8,0xd2,0xc3,0x3c,0}};
 if(!envelope(p.header,sizeof p,w::Op::Plans)||!envelope(s.header,sizeof s,w::Op::Snapshot)||memcmp(p.nonce,s.nonce,32)||!s.prepared)return false;bool nonce=false;for(auto v:p.nonce)nonce|=v!=0;if(!nonce)return false;
 if(install&&(s.stopped||s.error||s.ownerError||!s.ownerArmed||s.sourcesArmed||s.hostInitialized||s.saveLane||s.saveGeneration))return false;
 if(!counters(h,p,s,held&&(install||restore))||(restore&&!stopped(h,p,s)))return false;
 for(unsigned i=0;i<3;++i){const auto&v=p.inlines[i];auto&it=items[i];if(v.address!=p.base+sites[i]||v.size!=5||v.protection!=PAGE_EXECUTE_READ||memcmp(v.before,raw[i],5)||v.before[5]||v.before[6]||v.after[5]||v.after[6]||v.after[0]!=0xe8||!region(h,v.address,5,p.base,MEM_IMAGE,v.protection))return false;
  std::int32_t rel=0;memcpy(&rel,v.after+1,4);const auto target=A(std::int64_t(v.address+5)+rel),expected=v.relay+(i==1?32:0);if(target!=expected||!region(h,target,14,v.relay,MEM_PRIVATE,PAGE_EXECUTE_READ))return false;
  unsigned char relay[14]{};A destination=0;const unsigned char jmp[]={0xff,0x25,0,0,0,0};if(!read(h,target,relay,14)||memcmp(relay,jmp,6))return false;memcpy(&destination,relay+6,8);if(!region(h,destination,1,p.module,MEM_IMAGE,PAGE_EXECUTE_READ))return false;
  it.at=v.address;it.size=5;it.protection=v.protection;if(!read(h,it.at,it.prior,5))return false;const bool before=!memcmp(it.prior,v.before,5),after=!memcmp(it.prior,v.after,5);if((install&&!before)||(!before&&!after))return false;memcpy(it.desired,restore?v.before:v.after,5);
 }
 for(unsigned i=0;i<4;++i){const auto&v=p.slots[i];auto&it=items[3+i];if(v.address!=p.base+slots[i]||v.original!=p.base+originals[i]||(v.protection!=PAGE_READONLY&&v.protection!=PAGE_READWRITE&&v.protection!=PAGE_WRITECOPY)||!region(h,v.address,8,p.base,MEM_IMAGE,v.protection)||!region(h,v.hook,1,p.module,MEM_IMAGE,PAGE_EXECUTE_READ))return false;
  it.at=v.address;it.size=8;it.protection=v.protection;A value=0;if(!read(h,it.at,&value,8)||(value!=v.original&&value!=v.hook)||(install&&value!=(i<2?v.hook:v.original)))return false;memcpy(it.prior,&value,8);const auto to=restore?v.original:value;memcpy(it.desired,&to,8);
 }return true;
}
bool contexts(DWORD pid,const w::Plans&p,A moduleSize,unsigned&count){HANDLE list=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(list==INVALID_HANDLE_VALUE)return false;THREADENTRY32 e{};e.dwSize=sizeof e;bool ok=Thread32First(list,&e)!=0;count=0;
 while(ok){if(e.th32OwnerProcessID==pid){HANDLE t=OpenThread(THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,e.th32ThreadID);CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL;ok=t&&GetProcessIdOfThread(t)==pid&&GetThreadContext(t,&c);if(t)CloseHandle(t);if(!ok)break;++count;if(c.Rip>=p.module&&c.Rip<p.module+moduleSize){ok=false;break;}for(const auto&v:p.inlines)if((c.Rip>=v.address&&c.Rip<v.address+v.size)||(c.Rip>=v.relay&&c.Rip<v.relay+64))ok=false;if(!ok)break;}
  if(!Thread32Next(list,&e)){ok=GetLastError()==ERROR_NO_MORE_FILES;break;}}
 CloseHandle(list);return ok&&count;
}
bool replace(HANDLE h,const Item&v,const unsigned char*bytes){DWORD old=0;if(!VirtualProtectEx(h,reinterpret_cast<void*>(v.at),v.size,v.size==5?PAGE_EXECUTE_READWRITE:PAGE_READWRITE,&old))return false;SIZE_T z=0;bool ok=WriteProcessMemory(h,reinterpret_cast<void*>(v.at),bytes,v.size,&z)&&z==v.size&&FlushInstructionCache(h,reinterpret_cast<void*>(v.at),v.size);DWORD ignored=0;bool protectedAgain=VirtualProtectEx(h,reinterpret_cast<void*>(v.at),v.size,v.protection,&ignored)!=0;MEMORY_BASIC_INFORMATION m{};return ok&&protectedAgain&&VirtualQueryEx(h,reinterpret_cast<void*>(v.at),&m,sizeof m)==sizeof m&&m.Protect==v.protection&&same(h,v.at,bytes,v.size);}
void detach(DWORD pid,Outcome&o){if(!DebugActiveProcessStop(pid)){o.error=GetLastError();retain(o);}o.detached=true;}
}
int wmain(int argc,wchar_t**argv){Outcome o{};if(argc!=10){report(o);return 2;}const std::wstring op=argv[1];bool install=op==L"install",restore=op==L"restore",inspect=op==L"inspect";int failAt=-1;
#ifdef A_SAVE_RUNTIME_PUBLISH_FIXTURE
 if(op==L"rollback-1"){install=true;failAt=1;}
#endif
 A pid64=0,born=0,base=0,module=0;if((!install&&!restore&&!inspect)||!number(argv[2],pid64)||!pid64||pid64>MAXDWORD||pid64==GetCurrentProcessId()||!number(argv[3],born)||!number(argv[4],base)||!number(argv[5],module)){report(o);return 2;}DWORD pid=DWORD(pid64);w::Plans p{};w::Snapshot s{};
 if(!file(argv[8],p)||!file(argv[9],s)||p.pid!=pid||p.birth!=born||p.base!=base||p.module!=module||hash(argv[6])!=argv[7]){report(o);return 2;}
 HANDLE h=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ|PROCESS_VM_WRITE|PROCESS_VM_OPERATION|SYNCHRONIZE,FALSE,pid);if(!h){o.error=GetLastError();report(o);return 2;}BOOL debug=TRUE;wchar_t exe[32768]{};DWORD len=32768;
 if(!identity(h,pid,born,base)||!QueryFullProcessImageNameW(h,0,exe,&len)||!CheckRemoteDebuggerPresent(h,&debug)||debug){report(o);return 2;}
#ifndef A_SAVE_RUNTIME_PUBLISH_FIXTURE
 if(hash(exe)!=L"42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025"){report(o);return 2;}
#endif
 HANDLE exeFile=CreateFileW(exe,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr),dllFile=CreateFileW(argv[6],GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(exeFile==INVALID_HANDLE_VALUE||dllFile==INVALID_HANDLE_VALUE||!mapped(h,base,exeFile)||!mapped(h,module,dllFile)){report(o);return 2;}
 IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};if(!read(h,module,&dos,sizeof dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<0||dos.e_lfanew>0x1000||!read(h,module+dos.e_lfanew,&nt,sizeof nt)||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64){report(o);return 2;}
 std::array<Item,7> items{};if(!plan(h,p,s,install,restore,items)){report(o);return 2;}if(inspect){o.status="PASS_READ_ONLY";report(o);return 0;}
 if(!DebugActiveProcess(pid)){o.error=GetLastError();report(o);return 2;}o.attached=true;if(!DebugSetProcessKillOnExit(FALSE)){o.error=GetLastError();detach(pid,o);report(o);return 3;}
 DEBUG_EVENT event{};if(!WaitForDebugEvent(&event,5000)){o.error=GetLastError();detach(pid,o);report(o);return 3;}
 const bool held=event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT&&event.dwProcessId==pid&&event.u.CreateProcessInfo.lpStartAddress==nullptr&&A(event.u.CreateProcessInfo.lpBaseOfImage)==base&&fileIdentity(event.u.CreateProcessInfo.hFile,exeFile)&&GetProcessId(event.u.CreateProcessInfo.hProcess)==pid;
 if(!held){if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT&&event.u.CreateProcessInfo.hFile)CloseHandle(event.u.CreateProcessInfo.hFile);if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT&&event.u.LoadDll.hFile)CloseHandle(event.u.LoadDll.hFile);if(!ContinueDebugEvent(event.dwProcessId,event.dwThreadId,event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT?DBG_EXCEPTION_NOT_HANDLED:DBG_CONTINUE))retain(o);detach(pid,o);o.status="REJECTED_HELD_NO_WRITES";report(o);return 3;}
 bool good=identity(h,pid,born,base)&&mapped(h,base,exeFile)&&mapped(h,module,dllFile)&&plan(h,p,s,install,restore,items,true)&&contexts(pid,p,nt.OptionalHeader.SizeOfImage,o.threads_checked);
 if(!good){CloseHandle(event.u.CreateProcessInfo.hFile);o.status="REJECTED_HELD_NO_WRITES";detach(pid,o);report(o);return 3;}
 const unsigned count=install?3:7;for(unsigned i=0;i<count;++i){if(!memcmp(items[i].prior,items[i].desired,items[i].size))continue;o.written_mask|=1u<<i;if(!replace(h,items[i],items[i].desired)||int(i)==failAt){good=false;break;}}
 for(unsigned i=0;good&&i<count;++i)good=same(h,items[i].at,items[i].desired,items[i].size);
 if(!good){for(int i=6;i>=0;--i)if(o.written_mask&(1u<<i)){auto&v=items[unsigned(i)];if(same(h,v.at,v.prior,v.size)&&replace(h,v,v.prior))o.rolled_mask|=1u<<i;else if(same(h,v.at,v.desired,v.size)&&replace(h,v,v.prior))o.rolled_mask|=1u<<i;else o.uncertain=true;}if(o.uncertain){CloseHandle(event.u.CreateProcessInfo.hFile);retain(o);}o.status="CLEAN_ROLLBACK";}else o.status=install?"INSTALLED":"RESTORED";
 CloseHandle(event.u.CreateProcessInfo.hFile);detach(pid,o);report(o);CloseHandle(dllFile);CloseHandle(exeFile);CloseHandle(h);return good?0:4;
}
