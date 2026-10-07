// Passive hardware-breakpoint observer. Never writes game code, data or vtables.
// Debug-event/cleanup lifecycle derives from reviewed observe_auto_reload.cpp.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cwchar>
#include <map>
#include <string>
#include <stdexcept>
#include <cstring>
#include <vector>
#include <io.h>
#include <fcntl.h>
#include <share.h>
#include "save_return_observer_profile.h"
#include "auto_reload_cleanup.inc"
struct Registers {DWORD64 dr0,dr1,dr2,dr3,dr6,dr7;};
struct Call {unsigned stage=0;uint64_t id=0,rsp=0,returnAddress=0,rax=0,args[4]{};};
struct Thread {HANDLE handle=nullptr;Registers original{};Call calls[4]{};};
static volatile LONG stopRequested=0;
static BOOL WINAPI signalHandler(DWORD){InterlockedExchange(&stopRequested,1);return TRUE;}
static void need(bool b,const char* m){if(!b)throw std::runtime_error(m);}
static void check(BOOL b,const char* m){if(!b)throw std::runtime_error(std::string(m)+" error="+std::to_string(GetLastError()));}
static CONTEXT context(HANDLE h,DWORD flags){CONTEXT c{};c.ContextFlags=flags;check(GetThreadContext(h,&c),"GetThreadContext");return c;}
static Registers registersOf(const CONTEXT& c){return{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7};}
static void restore(HANDLE h,const Registers& s){CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;c.Dr0=s.dr0;c.Dr1=s.dr1;c.Dr2=s.dr2;c.Dr3=s.dr3;c.Dr6=s.dr6;c.Dr7=s.dr7;check(SetThreadContext(h,&c),"RestoreDR");}
template<class T>static bool maybe(HANDLE h,uint64_t a,T& v){SIZE_T n=0;return ReadProcessMemory(h,reinterpret_cast<void*>(a),&v,sizeof v,&n)&&n==sizeof v;}
template<class T>static T rd(HANDLE h,uint64_t a){T v{};need(maybe(h,a,v),"ReadProcessMemory failed");return v;}
static bool bytes(HANDLE h,uint64_t a,void* p,size_t z){SIZE_T n=0;return ReadProcessMemory(h,reinterpret_cast<void*>(a),p,z,&n)&&n==z;}
static void hex(FILE* f,const unsigned char* p,size_t n){for(size_t i=0;i<n;i++)std::fprintf(f,"%02x",p[i]);}
static uint64_t seq=0,callId=0,pairs=0;static unsigned seen=0;static bool incomplete=false,fixture=false;
static uint64_t pinnedUser=0,pinnedGame=0,pinnedWorld=0;static unsigned char pinnedDate[8]{};
static unsigned active(const std::map<DWORD,Thread>& threads){unsigned n=0;for(auto& t:threads)for(auto& c:t.second.calls)if(c.stage)++n;return n;}
static void arm(CONTEXT& c,const Thread& t,uint64_t base){
 uint64_t a[4];for(unsigned i=0;i<4;i++)a[i]=t.calls[i].stage==2?t.calls[i].returnAddress:base+(t.calls[i].stage==1?sroPoints[i].ret:sroPoints[i].entry);
 c.Dr0=a[0];c.Dr1=a[1];c.Dr2=a[2];c.Dr3=a[3];c.Dr6=0;c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x55;
}
static void raw(FILE* f,HANDLE p,const char* name,uint64_t address,size_t size){
 unsigned char data[512]{};need(size<=sizeof data,"snapshot size");std::fprintf(f,",\"%s\":",name);
 if(address&&bytes(p,address,data,size)){std::fputc('"',f);hex(f,data,size);std::fputc('"',f);}else std::fputs("null",f);
}
static bool snapshot(FILE* f,HANDLE p,uint64_t b,bool strict){
 bool good=true;uint64_t count=0,array=0,n=0,cap=0,queue=0;unsigned char date[8]{};
 good=maybe(p,b+0x19E7310+0x10,count)&&count>=5&&count<=8&&maybe(p,b+0x19E7310+0x20,array)&&array;
 std::fprintf(f,",\"stack\":[");
 uint64_t user=0,game=0;
 if(good)for(uint64_t i=0;i<count;i++){
  uint64_t s=0,vt=0;char name[40]{};bool ok=maybe(p,array+i*8,s)&&s&&maybe(p,s,vt)&&maybe(p,s+0x70,name);name[39]=0;
  if(ok)for(char* q=name;*q;q++)if(!((*q>='a'&&*q<='z')||(*q>='A'&&*q<='Z')||(*q>='0'&&*q<='9')||*q=='_'))ok=false;
  if(!ok){good=false;break;}
  bool allowed=!strcmp(name,"CRootState")||!strcmp(name,"CMotorGameState")||!strcmp(name,"CGameState")||!strcmp(name,"CStrategyState")||!strcmp(name,"CUserStrategyState")||!strcmp(name,"CConfigDlgState")||!strcmp(name,"CSaveLoadState");
  if(!allowed)good=false;
  if(i==4){user=s;if(strcmp(name,"CUserStrategyState")||vt!=b+0x12CC4A8)good=false;}
  if(i==2)game=s;
  std::fprintf(f,"%s{\"ptr\":\"0x%llx\",\"vt\":\"0x%llx\",\"name\":\"%s\"}",i?",":"",s,vt,name);
 }
 std::fputs("]",f);
 if(user!=pinnedUser||game!=pinnedGame)good=false;
 good=maybe(p,pinnedWorld+0x34,date)&&!memcmp(date,pinnedDate,8)&&good;
 std::fprintf(f,",\"date_raw\":\"");hex(f,date,8);std::fputs("\"",f);
 uint32_t phase=0,adv=0;uint64_t toolbar=0,panel=0,cache=0;
 good=maybe(p,pinnedUser+0x470,phase)&&phase==2&&maybe(p,pinnedGame+0x47c,adv)&&adv==0&&good;
 maybe(p,pinnedUser+0x478,toolbar);maybe(p,pinnedGame+0x480,panel);maybe(p,b+0x2025318,cache);
 std::fprintf(f,",\"phase\":%u,\"advance_game\":%u,\"user\":\"0x%llx\"",phase,adv,pinnedUser);
 raw(f,p,pinnedUser?"user470_494":"missing",pinnedUser+0x470,0x28);
 raw(f,p,"selections",pinnedUser+0x4a8,24);raw(f,p,"selection_transforms",pinnedUser+0x500,0x118);
 raw(f,p,"toolbar_pending",toolbar?toolbar+0x88:0,4);raw(f,p,"panel_advance",panel?panel+0x1b0:0,4);
 raw(f,p,"control_pause",b+0x1A38EC8+0x28,4);raw(f,p,"cursor_enabled",b+0x19E7510+0x13c,4);
 raw(f,p,"coordinator_flags",b+0x19E7690,4);raw(f,p,"callback2b0",b+0x19E7690+0x2b0,64);raw(f,p,"callback330",b+0x19E7690+0x330,64);
 raw(f,p,"world20a8",pinnedWorld+0x20a8,4);raw(f,p,"global_rng",b+0x18EB8B0,4);
 raw(f,p,"cache_mode",cache?cache+8:0,4);raw(f,p,"cache_pending_flags",cache?cache+0x3ec:0,8);
 raw(f,p,"request_globals",b+0x201ED10,72);
 bool queueOk=maybe(p,b+0x19E7310+0x30,n)&&maybe(p,b+0x19E7310+0x38,cap)&&maybe(p,b+0x19E7310+0x40,queue)&&n<=8&&n<=cap&&(!n||queue);
 std::fprintf(f,",\"pending_count\":%llu,\"pending_capacity\":%llu",n,cap);raw(f,p,"pending_records",queue,size_t(n<=8?n*16:0));
 std::fprintf(f,",\"snapshot_valid\":%s,\"atomic_debug_event\":%s",good&&queueOk?"true":"false",strict?"true":"false");
 return good&&queueOk;
}
static void record(FILE* f,HANDLE p,uint64_t b,DWORD tid,const CONTEXT& c,unsigned point,const Call& call,const char* kind){
 std::fprintf(f,"{\"event\":\"callback\",\"sequence\":%llu,\"tick\":%llu,\"thread\":%lu,\"call_id\":%llu,\"callback\":\"%s\",\"boundary\":\"%s\",\"rip\":\"0x%llx\",\"rsp\":\"0x%llx\",\"entry_rsp\":\"0x%llx\",\"return_address\":\"0x%llx\",\"rax\":\"0x%llx\",\"rcx\":\"0x%llx\",\"rdx\":\"0x%llx\",\"r8\":\"0x%llx\",\"r9\":\"0x%llx\",\"entry_args\":[\"0x%llx\",\"0x%llx\",\"0x%llx\",\"0x%llx\"],\"eflags\":%lu",++seq,GetTickCount64(),tid,call.id,sroPoints[point].name,kind,c.Rip,c.Rsp,call.rsp,call.returnAddress,c.Rax,c.Rcx,c.Rdx,c.R8,c.R9,call.args[0],call.args[1],call.args[2],call.args[3],c.EFlags);
 std::fputs(",\"xmm0_5\":\"",f);hex(f,reinterpret_cast<const unsigned char*>(&c.Xmm0),6*16);std::fputs("\"",f);
 bool ok=snapshot(f,p,b,true);std::fputs("}\n",f);std::fflush(f);need(ok,"callback_snapshot_guard");
}
static void observe(FILE* f,HANDLE p,uint64_t b,DWORD tid,Thread& t,CONTEXT& c){
 unsigned bits=unsigned(c.Dr6&15);need(bits&&!(bits&(bits-1)),"multiple_breakpoint_bits");unsigned i=0;while(!(bits&(1u<<i)))++i;
 auto& call=t.calls[i];uint64_t wanted=call.stage==2?call.returnAddress:b+(call.stage==1?sroPoints[i].ret:sroPoints[i].entry);
 need(c.Rip==wanted,"unexpected_breakpoint_rip");need(seq<512,"record_limit");
 if(call.stage==0){
  for(auto& other:t.calls)need(other.stage==0,"nested_callback_incomplete");
  need(c.Rcx==pinnedUser,"unexpected_user_identity");need((c.Rsp&15)==8,"entry_stack_alignment");
  call.id=++callId;call.rsp=c.Rsp;call.returnAddress=rd<uint64_t>(p,c.Rsp);call.args[0]=c.Rcx;call.args[1]=c.Rdx;call.args[2]=c.R8;call.args[3]=c.R9;
  need(call.returnAddress>=b+0x1000&&call.returnAddress<b+0x1200000,"return_address_outside_verified_module");
  record(f,p,b,tid,c,i,call,"entry");call.stage=1;
 }else if(call.stage==1){
  need(c.Rsp==call.rsp,"ret_stack_mismatch_reentry_or_unwind");need(rd<uint64_t>(p,c.Rsp)==call.returnAddress,"return_address_changed");
  call.rax=c.Rax;record(f,p,b,tid,c,i,call,"native_ret");call.stage=2;
 }else{
  need(c.Rsp==call.rsp+8,"caller_return_stack_mismatch");need(c.Rax==call.rax,"rax_changed_across_ret");
  record(f,p,b,tid,c,i,call,"returned");seen|=1u<<i;++pairs;call=Call{};
 }
}
static void preflight(HANDLE p,uint64_t b){
 need(rd<uint16_t>(p,b)==0x5A4D,"module_mz");
 for(unsigned i=0;i<4;i++){
  auto& point=sroPoints[i];std::vector<unsigned char> found(point.size);need(bytes(p,b+point.entry,found.data(),found.size()),"callback_code_read");
  if(!fixture)need(!memcmp(found.data(),point.bytes,found.size()),"callback_code_mismatch");
  else need(rd<unsigned char>(p,b+point.ret)==0xC3,"fixture_ret");
  need(rd<uint64_t>(p,b+0x12CC4A8+point.slot)==b+point.entry,"callback_vtable_mismatch");
 }
 need(rd<uint64_t>(p,b+0x19E7310+0x10)==5,"initial_stack_count");auto array=rd<uint64_t>(p,b+0x19E7310+0x20);
 pinnedUser=rd<uint64_t>(p,array+32);pinnedGame=rd<uint64_t>(p,array+16);
 auto root=rd<uint64_t>(p,b+0x1FCA1E0);pinnedWorld=rd<uint64_t>(p,root+0x85130);
 need(rd<uint64_t>(p,pinnedWorld)==b+0x12AA638,"world_vtable");need(bytes(p,pinnedWorld+0x34,pinnedDate,8),"world_date");
 need(pinnedDate[0]==203&&pinnedDate[1]==0&&pinnedDate[2]==8&&pinnedDate[3]==11&&pinnedDate[6]==12,"expected34_date_player");
 need(rd<uint32_t>(p,pinnedUser+0x470)==2,"idle_phase");need(rd<uint64_t>(p,b+0x19E7310+0x30)==0,"initial_pending_queue");
 auto special=rd<uint64_t>(p,b+0x201EC70);need(!special||rd<uint32_t>(p,special)==0,"special_context_active");
 for(auto offset:{0x4a8,0x4b0,0x4b8})need(rd<uint64_t>(p,pinnedUser+offset)==0,"initial_selection_not_empty");
}
static bool idle(HANDLE p,uint64_t b){
 uint64_t count=0,n=0,ui=0,panel=0;uint32_t pause=1,cursor=0,advance=1;int32_t menu=0;
 return maybe(p,b+0x19E7310+0x10,count)&&count==5&&maybe(p,b+0x19E7310+0x30,n)&&n==0&&
  maybe(p,pinnedUser+0x478,ui)&&ui&&maybe(p,ui+0x88,menu)&&menu==-1&&
  maybe(p,pinnedGame+0x480,panel)&&panel&&maybe(p,panel+0x1b0,advance)&&advance==0&&
  maybe(p,b+0x1A38EC8+0x28,pause)&&pause==0&&maybe(p,b+0x19E7510+0x13c,cursor)&&cursor==1;
}
int wmain(int argc,wchar_t** argv){
 if(argc!=6){std::fputs("usage: save_return_observer pid base seconds new-log.jsonl --observe|--fixture\n",stderr);return 2;}
 fixture=!wcscmp(argv[5],L"--fixture");if(!fixture&&wcscmp(argv[5],L"--observe"))return 2;
 DWORD pid=wcstoul(argv[1],nullptr,0);uint64_t b=_wcstoui64(argv[2],nullptr,0);unsigned seconds=wcstoul(argv[3],nullptr,0);
 if(!pid||!b||seconds<1||seconds>600)return 2;
 int fd=-1;if(_wsopen_s(&fd,argv[4],_O_WRONLY|_O_CREAT|_O_EXCL|_O_TEXT,_SH_DENYNO,_S_IREAD|_S_IWRITE))return 2;
 FILE* log=_fdopen(fd,"w");if(!log){_close(fd);return 2;}
 std::wstring stop=std::wstring(argv[4])+L".stop";HANDLE process=nullptr,debugProcess=nullptr;bool attached=false,pending=false,initial=true,stopping=false;DEBUG_EVENT event{};std::map<DWORD,Thread> threads;int result=1;DWORD continuation=DBG_CONTINUE;
 SetConsoleCtrlHandler(signalHandler,TRUE);
 try{
  process=OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,FALSE,pid);check(process!=nullptr,"OpenProcess");
  wchar_t path[32768];DWORD length=32768;check(QueryFullProcessImageNameW(process,0,path,&length),"ProcessPath");const wchar_t* leaf=wcsrchr(path,L'\\');leaf=leaf?leaf+1:path;
  need(!_wcsicmp(leaf,fixture?L"save_return_observer_fixture.exe":L"SAN14PK_SC.exe"),"unexpected_process");
  BOOL other=FALSE;check(CheckRemoteDebuggerPresent(process,&other),"CheckDebugger");need(!other,"another_debugger");preflight(process,b);
  check(DebugActiveProcess(pid),"DebugActiveProcess");attached=true;check(DebugSetProcessKillOnExit(FALSE),"DisableKill");
  uint64_t deadline=GetTickCount64()+seconds*1000ULL,lastSample=0;
  std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"fixture\":%s}\n",pid,fixture?"true":"false");std::fflush(log);
  for(;;){
   if(!stopping&&(stopRequested||GetTickCount64()>=deadline||GetFileAttributesW(stop.c_str())!=INVALID_FILE_ATTRIBUTES)){stopping=true;if(!initial)check(DebugBreakProcess(debugProcess),"CleanupBreak");}
   if(!WaitForDebugEvent(&event,100)){
    if(GetLastError()!=ERROR_SEM_TIMEOUT)check(FALSE,"WaitForDebugEvent");
    if(!stopping&&!initial&&GetTickCount64()-lastSample>=500){lastSample=GetTickCount64();std::fprintf(log,"{\"event\":\"coarse_sample\",\"tick\":%llu",lastSample);bool sampled=snapshot(log,process,b,false);std::fputs("}\n",log);std::fflush(log);if(!sampled){incomplete=true;stopping=true;check(DebugBreakProcess(debugProcess),"InvalidSampleCleanup");}}continue;
   }
   pending=true;continuation=DBG_CONTINUE;
   if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT||event.dwDebugEventCode==CREATE_THREAD_DEBUG_EVENT){
    if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT){debugProcess=event.u.CreateProcessInfo.hProcess;if(event.u.CreateProcessInfo.hFile)CloseHandle(event.u.CreateProcessInfo.hFile);}
    HANDLE h=OpenThread(THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|THREAD_QUERY_INFORMATION,FALSE,event.dwThreadId);check(h!=nullptr,"OpenThread");
    try{auto c=context(h,CONTEXT_DEBUG_REGISTERS);need(!(c.Dr7&0xff),"existing_hardware_breakpoint");Thread t;t.handle=h;t.original=registersOf(c);threads.emplace(event.dwThreadId,t);if(!stopping){arm(c,t,b);check(SetThreadContext(h,&c),"ArmDR");}}catch(...){if(!threads.count(event.dwThreadId))CloseHandle(h);throw;}
   }else if(event.dwDebugEventCode==EXIT_THREAD_DEBUG_EVENT){auto it=threads.find(event.dwThreadId);if(it!=threads.end()){for(auto& c:it->second.calls)if(c.stage){incomplete=true;std::fprintf(log,"{\"event\":\"thread_exit_pending_call\",\"thread\":%lu,\"call_id\":%llu,\"stage\":%u}\n",event.dwThreadId,c.id,c.stage);}CloseHandle(it->second.handle);threads.erase(it);}}
   else if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT){if(event.u.LoadDll.hFile)CloseHandle(event.u.LoadDll.hFile);}
   else if(event.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT){attached=false;incomplete=true;result=3;std::fputs("{\"event\":\"process_exit\",\"complete\":false}\n",log);check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,DBG_CONTINUE),"ContinueExit");pending=false;break;}
   else if(event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT){
    continuation=DBG_EXCEPTION_NOT_HANDLED;auto code=event.u.Exception.ExceptionRecord.ExceptionCode;
    if(code==EXCEPTION_BREAKPOINT&&(initial||stopping)){initial=false;continuation=DBG_CONTINUE;if(!stopping){std::fprintf(log,"{\"event\":\"armed\",\"threads\":%zu}\n",threads.size());std::fflush(log);}}
    else if(code==EXCEPTION_SINGLE_STEP){auto it=threads.find(event.dwThreadId);if(it!=threads.end()){auto c=context(it->second.handle,CONTEXT_FULL|CONTEXT_DEBUG_REGISTERS);if(c.Dr6&15){
     continuation=DBG_CONTINUE;
     try{observe(log,process,b,event.dwThreadId,it->second,c);}catch(...){c.Dr6=0;c.EFlags|=0x10000;check(SetThreadContext(it->second.handle,&c),"ResumeErrorInstruction");throw;}
     c.Dr6=0;c.EFlags|=0x10000;arm(c,it->second,b);check(SetThreadContext(it->second.handle,&c),"ResumeObservedInstruction");
    }}}
    else {incomplete=true;std::fprintf(log,"{\"event\":\"other_exception\",\"code\":%lu,\"first_chance\":%lu}\n",code,event.u.Exception.dwFirstChance);}
    if(stopping&&continuation==DBG_CONTINUE){
     unsigned open=active(threads);if(open)incomplete=true;std::fputs("{\"event\":\"final_snapshot\"",log);bool stable=snapshot(log,process,b,true);std::fputs("}\n",log);
     for(auto& t:threads)restore(t.second.handle,t.second.original);
     check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,continuation),"ContinueCleanup");pending=false;check(DebugActiveProcessStop(pid),"Detach");attached=false;
     bool complete=!incomplete&&stable&&idle(process,b)&&seen==15&&pairs>=4;std::fprintf(log,"{\"event\":\"detached\",\"complete\":%s,\"pairs\":%llu,\"open_calls\":%u,\"registers_restored\":true,\"no_code_data_writes\":true,\"completion_scope\":\"paired_callback_coverage_and_idle_only_not_world_equivalence\"}\n",complete?"true":"false",pairs,open);result=complete?0:4;break;
    }
   }
   check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,continuation),"ContinueEvent");pending=false;
  }
 }catch(const std::exception& e){incomplete=true;std::fprintf(log,"{\"event\":\"incomplete_error\",\"message\":\"%s\",\"pairs\":%llu}\n",e.what(),pairs);std::fprintf(stderr,"%s\n",e.what());}
 if(attached){bool restored=true;for(auto& t:threads){auto outcome=cleanupThread(t.second.handle,pending,[&]{restore(t.second.handle,t.second.original);});if((!outcome.registersRestored&&!outcome.threadExited)||outcome.resumeFailed)restored=false;}
  if(pending)ContinueDebugEvent(event.dwProcessId,event.dwThreadId,continuation);BOOL detached=DebugActiveProcessStop(pid);std::fprintf(log,"{\"event\":\"error_cleanup\",\"complete\":false,\"registers_restored\":%s,\"detached\":%s}\n",restored?"true":"false",detached?"true":"false");}
 for(auto& t:threads)CloseHandle(t.second.handle);if(debugProcess)CloseHandle(debugProcess);if(process)CloseHandle(process);std::fclose(log);return result;
}
