// Explicit new-process startup loader only. No attach-by-PID, process discovery,
// running-pool interception, remote return-stack editing, or executable stub.
#include "b_reload_lifecycle_loader.h"
#include <tlhelp32.h>
#include <cstdio>
#include <cwchar>
#include <string>
#include <vector>
struct LifecycleChild {
 PROCESS_INFORMATION pi{};bool debug=false,pending=false,entryStopped=false,entryRestored=false,resumed=false;DEBUG_EVENT event{};
 ~LifecycleChild(){if(pi.hThread)CloseHandle(pi.hThread);if(pi.hProcess)CloseHandle(pi.hProcess);}
 void abort(){if(!pi.hProcess)return;TerminateProcess(pi.hProcess,0xB14CFFFF);if(pending){ContinueDebugEvent(event.dwProcessId,event.dwThreadId,DBG_CONTINUE);pending=false;}if(debug){DebugActiveProcessStop(pi.dwProcessId);debug=false;}WaitForSingleObject(pi.hProcess,3000);}
};
static bool readRemote(HANDLE p,uintptr_t address,void*out,SIZE_T size){SIZE_T got=0;return ReadProcessMemory(p,reinterpret_cast<const void*>(address),out,size,&got)&&got==size;}
static bool writeByte(HANDLE p,uintptr_t address,BYTE value){DWORD old=0,unused=0;SIZE_T got=0;if(!VirtualProtectEx(p,reinterpret_cast<void*>(address),1,PAGE_EXECUTE_READWRITE,&old))return false;const bool wrote=WriteProcessMemory(p,reinterpret_cast<void*>(address),&value,1,&got)&&got==1;const bool restored=VirtualProtectEx(p,reinterpret_cast<void*>(address),1,old,&unused)!=FALSE;return wrote&&restored&&FlushInstructionCache(p,reinterpret_cast<void*>(address),1);}
static bool fullFile(const wchar_t*input,std::wstring&out){const auto n=GetFullPathNameW(input,0,nullptr,nullptr);if(!n)return false;std::vector<wchar_t>b(n);if(!GetFullPathNameW(input,n,b.data(),nullptr))return false;out=b.data();const auto flags=GetFileAttributesW(out.c_str());return flags!=INVALID_FILE_ATTRIBUTES&&!(flags&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT));}
static bool moduleBase(DWORD pid,const std::wstring&path,uintptr_t&base){HANDLE h=CreateToolhelp32Snapshot(TH32CS_SNAPMODULE|TH32CS_SNAPMODULE32,pid);if(h==INVALID_HANDLE_VALUE)return false;MODULEENTRY32W m{};m.dwSize=sizeof m;bool found=false;for(BOOL ok=Module32FirstW(h,&m);ok;ok=Module32NextW(h,&m))if(!_wcsicmp(m.szExePath,path.c_str())){base=uintptr_t(m.modBaseAddr);found=true;break;}CloseHandle(h);return found;}
static bool remoteSystemExport(DWORD pid,const char*name,uintptr_t&out){auto address=GetProcAddress(GetModuleHandleW(L"kernel32.dll"),name);HMODULE actual=nullptr;if(!address||!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(address),&actual))return false;wchar_t path[32768]{};if(!GetModuleFileNameW(actual,path,DWORD(sizeof path/sizeof path[0])))return false;uintptr_t remote=0;if(!moduleBase(pid,path,remote))return false;out=remote+(uintptr_t(address)-uintptr_t(actual));return true;}
static bool bootstrapRva(const std::wstring&dll,uintptr_t&out){HMODULE image=LoadLibraryExW(dll.c_str(),nullptr,DONT_RESOLVE_DLL_REFERENCES);if(!image)return false;bool valid=false;__try{auto*dos=reinterpret_cast<const IMAGE_DOS_HEADER*>(image);auto*nt=reinterpret_cast<const IMAGE_NT_HEADERS64*>(uintptr_t(image)+dos->e_lfanew);auto fn=GetProcAddress(image,"BReloadLifecycleBootstrap");if(dos->e_magic==IMAGE_DOS_SIGNATURE&&nt->Signature==IMAGE_NT_SIGNATURE&&nt->FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64&&fn&&uintptr_t(fn)>=uintptr_t(image)&&uintptr_t(fn)<uintptr_t(image)+nt->OptionalHeader.SizeOfImage){out=uintptr_t(fn)-uintptr_t(image);valid=true;}}__except(EXCEPTION_EXECUTE_HANDLER){}FreeLibrary(image);return valid;}
static bool remoteCall(HANDLE process,uintptr_t fn,void*arg,DWORD&code){HANDLE h=CreateRemoteThread(process,nullptr,0,reinterpret_cast<LPTHREAD_START_ROUTINE>(fn),arg,0,nullptr);if(!h)return false;const auto wait=WaitForSingleObject(h,10000);const bool ok=wait==WAIT_OBJECT_0&&GetExitCodeThread(h,&code);CloseHandle(h);return ok;}
static bool stopAtEntry(LifecycleChild&child,BReloadLifecycleBootstrapInfo&info){const auto deadline=GetTickCount64()+10000;bool originalBreakpoint=false,started=false;BYTE saved=0;
 // Release only CREATE_SUSPENDED: the debugger receives CREATE_PROCESS before
 // the child can execute its PE entry, and all threads stop for each event.
 if(ResumeThread(child.pi.hThread)!=1)return false;started=true;
 while(GetTickCount64()<deadline){DEBUG_EVENT e{};if(!WaitForDebugEvent(&e,100)){if(GetLastError()==ERROR_SEM_TIMEOUT)continue;return false;}child.event=e;child.pending=true;DWORD disposition=DBG_CONTINUE;
#ifdef B_RELOAD_LIFECYCLE_LOADER_DIAGNOSTIC
  fprintf(stderr,"EVENT type=%lu tid=%lu primary=%lu code=%lx address=%p entry=%llx\n",e.dwDebugEventCode,e.dwThreadId,child.pi.dwThreadId,e.dwDebugEventCode==EXCEPTION_DEBUG_EVENT?e.u.Exception.ExceptionRecord.ExceptionCode:0,e.dwDebugEventCode==EXCEPTION_DEBUG_EVENT?e.u.Exception.ExceptionRecord.ExceptionAddress:nullptr,info.entryPoint);
#endif

  if(e.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT){
   const auto base=uintptr_t(e.u.CreateProcessInfo.lpBaseOfImage);IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
   const bool valid=readRemote(child.pi.hProcess,base,&dos,sizeof dos)&&dos.e_magic==IMAGE_DOS_SIGNATURE&&dos.e_lfanew>0&&dos.e_lfanew<0x100000&&readRemote(child.pi.hProcess,base+uintptr_t(dos.e_lfanew),&nt,sizeof nt)&&nt.Signature==IMAGE_NT_SIGNATURE&&nt.FileHeader.Machine==IMAGE_FILE_MACHINE_AMD64&&nt.OptionalHeader.Magic==IMAGE_NT_OPTIONAL_HDR64_MAGIC&&nt.OptionalHeader.AddressOfEntryPoint&&nt.OptionalHeader.AddressOfEntryPoint<nt.OptionalHeader.SizeOfImage;
   if(e.u.CreateProcessInfo.hFile)CloseHandle(e.u.CreateProcessInfo.hFile);if(!valid)return false;
   // Process/thread handles supplied by debug events belong to the active
   // debug session. Keep them valid until detach/exit; the OS uses them there.
   info.imageBase=base;info.entryPoint=base+nt.OptionalHeader.AddressOfEntryPoint;if(!readRemote(child.pi.hProcess,uintptr_t(info.entryPoint),&saved,1)||saved==0xcc||!writeByte(child.pi.hProcess,uintptr_t(info.entryPoint),0xcc))return false;info.entryByte=saved;

  }else if(e.dwDebugEventCode==CREATE_THREAD_DEBUG_EVENT){
   // Keep the debugger-owned thread handle live through DebugActiveProcessStop.
  }else if(e.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT){if(e.u.LoadDll.hFile)CloseHandle(e.u.LoadDll.hFile);
  }else if(e.dwDebugEventCode==EXCEPTION_DEBUG_EVENT){const auto&x=e.u.Exception.ExceptionRecord;
   if(x.ExceptionCode==EXCEPTION_BREAKPOINT&&uintptr_t(x.ExceptionAddress)==info.entryPoint&&e.dwThreadId==child.pi.dwThreadId&&started){CONTEXT c{};c.ContextFlags=CONTEXT_CONTROL;
#ifdef B_RELOAD_LIFECYCLE_LOADER_DIAGNOSTIC
    fprintf(stderr,"ENTRY handles process=%p thread=%p\n",child.pi.hProcess,child.pi.hThread);
#endif
    if(!GetThreadContext(child.pi.hThread,&c)){fprintf(stderr,"entry-get-context %lu\n",GetLastError());return false;}if(c.Rip!=info.entryPoint+1){fprintf(stderr,"entry-rip %llx\n",c.Rip);return false;}if(!writeByte(child.pi.hProcess,uintptr_t(info.entryPoint),saved)){fprintf(stderr,"entry-restore-byte %lu\n",GetLastError());return false;}c.Rip=info.entryPoint;if(!SetThreadContext(child.pi.hThread,&c)){fprintf(stderr,"entry-set-context %lu\n",GetLastError());return false;}if(SuspendThread(child.pi.hThread)!=0){fprintf(stderr,"entry-suspend %lu\n",GetLastError());return false;}
    child.entryStopped=child.entryRestored=true;if(!ContinueDebugEvent(e.dwProcessId,e.dwThreadId,DBG_CONTINUE))return false;child.pending=false;if(!DebugSetProcessKillOnExit(FALSE)){fprintf(stderr,"entry-debug-kill-policy %lu\n",GetLastError());return false;}if(!DebugActiveProcessStop(child.pi.dwProcessId)){fprintf(stderr,"entry-detach %lu\n",GetLastError());return false;}child.debug=false;return true;
   }
   if(x.ExceptionCode==EXCEPTION_BREAKPOINT&&!originalBreakpoint){originalBreakpoint=true;}else disposition=DBG_EXCEPTION_NOT_HANDLED;
  }else if(e.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT)return false;
  if(!ContinueDebugEvent(e.dwProcessId,e.dwThreadId,disposition))return false;child.pending=false;
 }return false;
}
int wmain(int argc,wchar_t**argv){if(argc<3||argc>4||(argc==4&&wcscmp(argv[3],L"--wait-exit"))){fwprintf(stderr,L"Usage: b_reload_lifecycle_loader.exe <explicit-exe> <runtime-dll> [--wait-exit]\n");return 2;}
 std::wstring exe,dll;uintptr_t exported=0;if(!fullFile(argv[1],exe)||!fullFile(argv[2],dll)||!bootstrapRva(dll,exported)){printf("{\"passed\":false,\"stage\":\"input\"}\n");return 2;}
 LifecycleChild child;const auto fail=[&](const char*stage){const auto os=GetLastError();child.abort();printf("{\"passed\":false,\"stage\":\"%s\",\"os_error\":%lu,\"created_child_only\":true}\n",stage,os);return 1;};
 std::wstring command=L"\""+exe+L"\"";std::vector<wchar_t> cmd(command.begin(),command.end());cmd.push_back(0);const auto slash=exe.find_last_of(L"\\/");const auto cwd=exe.substr(0,slash);STARTUPINFOW si{};si.cb=sizeof si;
 if(!CreateProcessW(exe.c_str(),cmd.data(),nullptr,nullptr,FALSE,DEBUG_ONLY_THIS_PROCESS|CREATE_SUSPENDED,nullptr,cwd.c_str(),&si,&child.pi))return fail("create");child.debug=true;
 BReloadLifecycleBootstrapInfo info{};info.pid=child.pi.dwProcessId;info.primaryThread=child.pi.dwThreadId;if(!stopAtEntry(child,info))return fail("entry");
 uintptr_t load=0;if(!remoteSystemExport(child.pi.dwProcessId,"LoadLibraryW",load))return fail("system-export");const auto bytes=(dll.size()+1)*sizeof(wchar_t);void*remotePath=VirtualAllocEx(child.pi.hProcess,nullptr,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);SIZE_T written=0;DWORD code=0;
 if(!remotePath||!WriteProcessMemory(child.pi.hProcess,remotePath,dll.c_str(),bytes,&written)||written!=bytes||!remoteCall(child.pi.hProcess,load,remotePath,code))return fail("load-library");VirtualFreeEx(child.pi.hProcess,remotePath,0,MEM_RELEASE);
 uintptr_t module=0;if(!moduleBase(child.pi.dwProcessId,dll,module))return fail("loaded-module");void*remoteInfo=VirtualAllocEx(child.pi.hProcess,nullptr,sizeof info,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
 if(!remoteInfo||!WriteProcessMemory(child.pi.hProcess,remoteInfo,&info,sizeof info,&written)||written!=sizeof info||!remoteCall(child.pi.hProcess,module+exported,remoteInfo,code)||code!=BReloadLifecycleBootstrapSuccess)return fail("bootstrap");VirtualFreeEx(child.pi.hProcess,remoteInfo,0,MEM_RELEASE);
 CONTEXT current{};current.ContextFlags=CONTEXT_CONTROL;BYTE original=0;if(!GetThreadContext(child.pi.hThread,&current)||current.Rip!=info.entryPoint||!readRemote(child.pi.hProcess,uintptr_t(info.entryPoint),&original,1)||original!=info.entryByte)return fail("entry-recheck");
 if(ResumeThread(child.pi.hThread)!=1)return fail("resume");child.resumed=true;DWORD targetExit=STILL_ACTIVE;if(argc==4){if(WaitForSingleObject(child.pi.hProcess,10000)!=WAIT_OBJECT_0||!GetExitCodeProcess(child.pi.hProcess,&targetExit)||targetExit)return fail("owned-test-exit");}
 printf("{\"passed\":true,\"created_child_only\":true,\"pe_entry_stopped\":true,\"entry_byte_restored\":true,\"bootstrap_before_entry\":true,\"primary_resumed\":true,\"target_exit\":%lu,\"running_process_attach\":false}\n",targetExit);return 0;
}
