#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cwchar>
#include <map>
#include <string>
#include <stdexcept>
#include <share.h>
#include <cstring>
#include <vector>

// Observation only: native RNG entry, per-thread return, and global state writes.
// No game code/data writes, no DLL injection. Debugger changes scheduling.
struct Registers { DWORD64 dr0, dr1, dr2, dr3, dr6, dr7; };
struct PendingCall { uint64_t id=0,rsp=0,caller=0; uint32_t before=0; int32_t argument=0; bool range=false; };
struct TracedThread { HANDLE handle; Registers original; PendingCall pending; };
static volatile LONG stopRequested = 0;
static BOOL WINAPI signalHandler(DWORD) { InterlockedExchange(&stopRequested, 1); return TRUE; }
static void check(BOOL success, const char* message) {
    if (!success) throw std::runtime_error(std::string(message)+" error="+std::to_string(GetLastError()));
}
static CONTEXT context(HANDLE thread, DWORD flags) {
    CONTEXT c{}; c.ContextFlags = flags; check(GetThreadContext(thread,&c),"GetThreadContext"); return c;
}
static Registers registersOf(const CONTEXT& c) { return {c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}; }
static void restore(HANDLE thread, const Registers& saved) {
    CONTEXT c{}; c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    c.Dr0=saved.dr0; c.Dr1=saved.dr1; c.Dr2=saved.dr2; c.Dr3=saved.dr3; c.Dr6=saved.dr6; c.Dr7=saved.dr7;
    check(SetThreadContext(thread,&c),"Restore debug registers");
}
static void readExact(HANDLE process, uint64_t address, void* output, size_t bytes) {
    SIZE_T count=0;
    check(ReadProcessMemory(process,reinterpret_cast<void*>(address),output,bytes,&count),"ReadProcessMemory");
    if(count!=bytes) throw std::runtime_error("Partial process read");
}


template<class T> static T rd(HANDLE p,uint64_t a) { T v{};readExact(p,a,&v,sizeof(v));return v; }
static uint64_t sequence=0, stageSamples=0, fixtureSamples=0, callCount=0, returnCount=0, abandonedCalls=0;
static bool started=false, fixtureMode=false;
static uint64_t rngAddress=0, rangeAddress=0, percentageAddress=0;
static uint32_t previousObservedRng=0;
static void rngBaseline(FILE* log,HANDLE p) {
    previousObservedRng=rd<uint32_t>(p,rngAddress);
    std::fprintf(log,"{\"event\":\"rng_watch_baseline\",\"value\":%u}\n",previousObservedRng);
}
static void hexBytes(FILE* f,const unsigned char* data,size_t size) {
    static const char digits[]="0123456789abcdef";
    for(size_t i=0;i<size;i++) { std::fputc(digits[data[i]>>4],f);std::fputc(digits[data[i]&15],f); }
}
static void dateFields(FILE* log,HANDLE p,uint64_t world) {
    unsigned char date[8]; readExact(p,world+0x34,date,8);
    uint32_t inputs[4];readExact(p,world+0x450,inputs,16);
    std::fprintf(log,"\"date\":[%u,%u,%u],\"player\":%u,\"world_inputs\":[%u,%u,%u,%u]",
        unsigned(date[0]|date[1]<<8),date[2],date[3],date[6],inputs[0],inputs[1],inputs[2],inputs[3]);
}


static void cameraState(FILE* log,HANDLE p,uint64_t base) {
    uint64_t camera=base+0x19E7690;
    if(rd<uint64_t>(p,camera+0x50)!=base+0x123E520)throw std::runtime_error("Camera controller type mismatch");
    unsigned char raw[0x290];readExact(p,camera,raw,sizeof(raw));
    uint64_t linked=rd<uint64_t>(p,camera+0x280);
    std::fprintf(log,",\"camera\":{\"level\":%d,\"fraction\":%d,\"mode_288\":%u,\"linked_present\":%s,\"singleton_hex\":\"",
        rd<int32_t>(p,camera+0x230),rd<int32_t>(p,camera+0x234),rd<uint32_t>(p,camera+0x288),linked?"true":"false");
    hexBytes(log,raw,sizeof(raw));std::fprintf(log,"\",\"linked_hex\":");
    if(linked){unsigned char data[0xb0];readExact(p,linked,data,sizeof(data));std::fprintf(log,"\"");hexBytes(log,data,sizeof(data));std::fprintf(log,"\"");}
    else std::fprintf(log,"null");std::fprintf(log,"}");
}
static void routeContext(FILE* log,HANDLE p,uint64_t base,uint64_t world) {
    dateFields(log,p,world);
    std::fprintf(log,",\"subday\":%u,\"global_rng\":%u,\"worker_90\":%u,\"pending_94\":%u,\"effect_pending_98\":%u,\"effect_count\":%llu",
        rd<uint8_t>(p,world+0x38),rd<uint32_t>(p,base+0x18EB8B0),rd<uint32_t>(p,base+0x1A24D80),
        rd<uint32_t>(p,base+0x1A24D84),rd<uint32_t>(p,base+0x1A38AB8),rd<uint64_t>(p,base+0x1A38A58));
    cameraState(log,p,base);
    uint64_t manager=base+0x19E7310,count=rd<uint64_t>(p,manager+0x10),list=rd<uint64_t>(p,manager+0x20);
    if(count>64 || (count&&!list))throw std::runtime_error("State stack bound");
    int stage=-1;std::fprintf(log,",\"states\":[");
    for(uint64_t i=0;i<count;i++){
        uint64_t state=rd<uint64_t>(p,list+i*8);char name[96];readExact(p,state+0x70,name,sizeof(name));name[95]=0;
        for(unsigned j=0;name[j];j++)if(!((name[j]>='A'&&name[j]<='Z')||(name[j]>='a'&&name[j]<='z')||(name[j]>='0'&&name[j]<='9')||name[j]=='_'))throw std::runtime_error("State name invalid");
        std::fprintf(log,"%s\"%s\"",i?",":"",name);
        if(rd<uint64_t>(p,state)==base+0x12CC770)stage=rd<int32_t>(p,state+0x484);
    }
    std::fprintf(log,"],\"stage\":%d",stage);
}

static void stackRecord(FILE* log,HANDLE p,const CONTEXT& c) {
    std::fprintf(log,",\"registers\":{\"rip\":%llu,\"rsp\":%llu,\"rax\":%llu,\"rcx\":%llu,\"rdx\":%llu,\"rbp\":%llu,\"rbx\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"r8\":%llu,\"r9\":%llu,\"r10\":%llu,\"r11\":%llu,\"r12\":%llu,\"r13\":%llu,\"r14\":%llu,\"r15\":%llu}",
        c.Rip,c.Rsp,c.Rax,c.Rcx,c.Rdx,c.Rbp,c.Rbx,c.Rsi,c.Rdi,c.R8,c.R9,c.R10,c.R11,c.R12,c.R13,c.R14,c.R15);
    unsigned char stack[2048];SIZE_T n=0;size_t len=sizeof(stack);
    while(len>=64&&!(ReadProcessMemory(p,reinterpret_cast<void*>(c.Rsp),stack,len,&n)&&n==len))len/=2;
    std::fprintf(log,",\"stack_hex\":\"");if(len>=64)hexBytes(log,stack,len);std::fprintf(log,"\"");
}
static bool observe(FILE* log,HANDLE p,uint64_t base,CONTEXT& c,DWORD tid,TracedThread& t) {
    const unsigned bits=unsigned(c.Dr6&15);
    if(!bits||(bits&(bits-1)))throw std::runtime_error("Ambiguous hardware marker bits");
    bool entry=bits==1||bits==2,returned=bits==8,write=bits==4;
    auto state=rd<uint32_t>(p,rngAddress);
    if(entry){
        if(t.pending.id)throw std::runtime_error("Nested entry in audited leaf RNG");
        auto caller=rd<uint64_t>(p,c.Rsp);
        MEMORY_BASIC_INFORMATION region{};
        if(!VirtualQueryEx(p,reinterpret_cast<void*>(caller),&region,sizeof(region))||
           region.State!=MEM_COMMIT||!(region.Protect&(PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))
            throw std::runtime_error("Native return address is not executable");
        t.pending={++callCount,c.Rsp,caller,state,int32_t(c.Rcx),bits==1};
        c.Dr3=caller;c.Dr7|=0x40;
    }
    if(returned&&(!t.pending.id||c.Rip!=t.pending.caller||c.Rsp!=t.pending.rsp+8))
        throw std::runtime_error("Native call/return stack mismatch");
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"tick_ms\":%llu,\"call_id\":%llu,\"rip\":%llu,\"rng_snapshot\":%u",
        entry?"rng_entry":returned?"rng_return":"rng_write",++sequence,tid,GetTickCount64(),t.pending.id,c.Rip,state);
    if(!fixtureMode){
        auto root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
        if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
        std::fprintf(log,",");routeContext(log,p,base,world);
    }
    if(entry||returned){
        auto& q=t.pending;
        std::fprintf(log,",\"kind\":\"%s\",\"argument\":%d,\"entry_rng_snapshot\":%u,\"caller\":%llu,\"entry_rsp\":%llu",
            q.range?"range":"percentage",q.argument,q.before,q.caller,q.rsp);
        if(returned){std::fprintf(log,",\"result\":%d,\"return_rsp\":%llu",int32_t(c.Rax),c.Rsp);returnCount++;}
    }
    if(write){
        std::fprintf(log,",\"previous_observed\":%u,\"observed_after\":%u",previousObservedRng,state);
        previousObservedRng=state;
    }
    if(entry||write)stackRecord(log,p,c);
    std::fprintf(log,"}\n");std::fflush(log);
    if(returned){t.pending={};c.Dr3=0;c.Dr7&=~DWORD64(0x40);}
    stageSamples++;started=true;
    return sequence>=12000;
}
static uint64_t unfinished(const std::map<DWORD,TracedThread>& threads){
    uint64_t n=0;for(const auto& row:threads)if(row.second.pending.id)n++;return n;
}
int wmain(int argc,wchar_t** argv) {
    const int expectedArgc=
        8;
    if(argc!=expectedArgc) { std::fwprintf(stderr,L"Usage: probe pid base range_address percentage_address rng_address timeout_seconds log.jsonl\n"); return 2; }
    DWORD pid=wcstoul(argv[1],nullptr,0);
    uint64_t base=_wcstoui64(argv[2],nullptr,0);
    rangeAddress=_wcstoui64(argv[3],nullptr,0);percentageAddress=_wcstoui64(argv[4],nullptr,0);rngAddress=_wcstoui64(argv[5],nullptr,0);
    unsigned timeout=wcstoul(argv[6],nullptr,0);
    std::wstring stopPath=std::wstring(argv[7])+L".stop";
    if(!pid || timeout<1 || timeout>900 || !base || !rangeAddress || !percentageAddress || !rngAddress) return 2;
    FILE* log=_wfsopen(argv[7],L"w",_SH_DENYNO); if(!log) return 2;
    HANDLE process=nullptr, debugProcess=nullptr; bool attached=false, eventPending=false, initialBreak=true, stopping=false, hit=false;
    DEBUG_EVENT event{}; std::map<DWORD,TracedThread> threads;
    SetConsoleCtrlHandler(signalHandler,TRUE);
    int result=1;
    try {
        DWORD access=PROCESS_QUERY_INFORMATION|PROCESS_VM_READ;
        process=OpenProcess(access,FALSE,pid);
        check(process!=nullptr,"OpenProcess read-only");
        wchar_t path[32768]; DWORD length=32768;
        check(QueryFullProcessImageNameW(process,0,path,&length),"Query process image");
        const wchar_t* leaf=wcsrchr(path,L'\\'); leaf=leaf?leaf+1:path;
        if(_wcsicmp(leaf,L"SAN14PK_SC.exe") && _wcsicmp(leaf,L"rng_pair_target_fixture.exe"))
            throw std::runtime_error("Only SAN14PK_SC.exe or the dedicated test fixture is allowed");
        BOOL otherDebugger=FALSE;
        check(CheckRemoteDebuggerPresent(process,&otherDebugger),"Check debugger");
        if(otherDebugger) throw std::runtime_error("Another debugger is already attached");
        fixtureMode=(!_wcsicmp(leaf,L"rng_pair_target_fixture.exe"));
        if(rngAddress&3)throw std::runtime_error("Unaligned RNG watch");
        if(!fixtureMode && (rangeAddress!=base+0x3AA7C0||percentageAddress!=base+0x3AA3F0||rngAddress!=base+0x18EB8B0))
            throw std::runtime_error("Unexpected native observer addresses");
        uint16_t mz=0; readExact(process,base,&mz,sizeof(mz));
        if(mz!=0x5a4d) throw std::runtime_error("Expected module base");
        uint8_t code[16]; readExact(process,rangeAddress,code,sizeof(code));
        check(DebugActiveProcess(pid),"DebugActiveProcess"); attached=true;
        check(DebugSetProcessKillOnExit(FALSE),"Disable debuggee termination");
        const ULONGLONG deadline=GetTickCount64()+timeout*1000ULL;
        std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"base\":%llu,\"range_address\":%llu,\"percentage_address\":%llu,\"rng_address\":%llu}\n",pid,base,rangeAddress,percentageAddress,rngAddress); std::fflush(log);
        while(true) {
            if(!stopping && (stopRequested || GetTickCount64()>=deadline || GetFileAttributesW(stopPath.c_str())!=INVALID_FILE_ATTRIBUTES)) {
                stopping=true;
                if(!initialBreak) check(DebugBreakProcess(debugProcess),"Request cleanup breakpoint");
            }
            if(!WaitForDebugEvent(&event,250)) {
                if(GetLastError()==ERROR_SEM_TIMEOUT) continue;
                check(FALSE,"WaitForDebugEvent");
            }
            eventPending=true;
            DWORD status=DBG_CONTINUE;
            if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT || event.dwDebugEventCode==CREATE_THREAD_DEBUG_EVENT) {
                if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT) debugProcess=event.u.CreateProcessInfo.hProcess;
                if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT && event.u.CreateProcessInfo.hFile) CloseHandle(event.u.CreateProcessInfo.hFile);
                HANDLE th=OpenThread(THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|THREAD_QUERY_INFORMATION,FALSE,event.dwThreadId);
                check(th!=nullptr,"OpenThread");
                try {
                    auto c=context(th,CONTEXT_DEBUG_REGISTERS);
                    if(c.Dr7&0xff) throw std::runtime_error("Existing hardware breakpoint; not replacing it");
                    auto saved=registersOf(c);
                    threads.emplace(event.dwThreadId,TracedThread{th,saved,{}});
                    if(!stopping) {
                        c.Dr0=rangeAddress;c.Dr1=percentageAddress;c.Dr2=rngAddress;c.Dr3=0;c.Dr6=0;
                        // Entry L0/L1; RNG write L2/RW2=01/LEN2=11; L3 armed per pending return.
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x0d000015;
                        check(SetThreadContext(th,&c),"Arm execution breakpoint");
                    }
                } catch(...) { if(!threads.count(event.dwThreadId)) CloseHandle(th); throw; }
            } else if(event.dwDebugEventCode==EXIT_THREAD_DEBUG_EVENT) {
                auto it=threads.find(event.dwThreadId);
                if(it!=threads.end()) {
                    if(it->second.pending.id){
                        abandonedCalls++;
                        std::fprintf(log,"{\"event\":\"thread_exit_with_pending\",\"thread\":%lu,\"call_id\":%llu}\n",event.dwThreadId,it->second.pending.id);
                    }
                    CloseHandle(it->second.handle);threads.erase(it);
                }
            } else if(event.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT) {
                if(event.u.LoadDll.hFile) CloseHandle(event.u.LoadDll.hFile);
            } else if(event.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT) {
                attached=false; result=3;
                std::fprintf(log,"{\"event\":\"process_exit\",\"code\":%lu}\n",event.u.ExitProcess.dwExitCode);
                check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,DBG_CONTINUE),"Continue exit"); eventPending=false; break;
            } else if(event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT) {
                auto codeValue=event.u.Exception.ExceptionRecord.ExceptionCode;
                status=DBG_EXCEPTION_NOT_HANDLED;
                if(codeValue==EXCEPTION_BREAKPOINT && (initialBreak || stopping)) {
                    initialBreak=false; status=DBG_CONTINUE;
                    if(!stopping) {
                        rngBaseline(log,process);
                        std::fprintf(log,"{\"event\":\"armed\",\"threads\":%zu}\n",threads.size()); std::fflush(log);
                    }
                } else if(codeValue==EXCEPTION_SINGLE_STEP) {
                    auto it=threads.find(event.dwThreadId);
                    if(it!=threads.end()) {
                        auto c=context(it->second.handle,CONTEXT_FULL|CONTEXT_DEBUG_REGISTERS);
                        bool ours=(c.Dr6&4)||((c.Dr6&1)&&c.Rip==rangeAddress)||((c.Dr6&2)&&c.Rip==percentageAddress)||
                            ((c.Dr6&8)&&it->second.pending.id&&c.Rip==it->second.pending.caller);
                        if(ours) {
                            stopping=observe(log,process,base,c,event.dwThreadId,it->second) || stopping;
                            hit=stageSamples>0 || fixtureSamples>0;
                            status=DBG_CONTINUE;
                            if(c.Dr6&11)c.EFlags|=0x10000; // RF for execution markers only; data watch already executed.
                            c.Dr6=0;
                            check(SetThreadContext(it->second.handle,&c),"Resume observed thread");
                        }
                    }
                }
                if(stopping && status==DBG_CONTINUE) {
                    for(auto& [tid,thread]:threads) restore(thread.handle,thread.original);
                    check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,status),"Continue cleanup"); eventPending=false;
                    check(DebugActiveProcessStop(pid),"Detach debugger"); attached=false;
                    std::fprintf(log,"{\"event\":\"detached\",\"captured\":%s,\"registers_restored\":true,\"entries\":%llu,\"returns\":%llu,\"unfinished_calls\":%llu,\"abandoned_calls\":%llu}\n",hit?"true":"false",callCount,returnCount,unfinished(threads),abandonedCalls);
                    result=hit?0:4; break;
                }
            }
            check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,status),"Continue event"); eventPending=false;
        }
    } catch(const std::exception& error) {
        std::fprintf(log,"{\"event\":\"error\",\"message\":\"%s\"}\n",error.what());
        std::fprintf(stderr,"%s\n",error.what());
    }
    if(attached) {
        bool restored=true;
        for(auto& [tid,thread]:threads) {
            bool suspended=false;
            try {
                if(!eventPending) { if(SuspendThread(thread.handle)==DWORD(-1)){restored=false;continue;} suspended=true; }
                restore(thread.handle,thread.original);
            } catch(...) { restored=false; }
            if(suspended) ResumeThread(thread.handle);
        }
        if(eventPending) ContinueDebugEvent(event.dwProcessId,event.dwThreadId,DBG_CONTINUE);
        BOOL detached=DebugActiveProcessStop(pid);
        std::fprintf(log,"{\"event\":\"error_cleanup\",\"registers_restored\":%s,\"detached\":%s}\n",restored?"true":"false",detached?"true":"false");
    }
    for(auto& [tid,thread]:threads) CloseHandle(thread.handle);
    if(process) CloseHandle(process);
    std::fclose(log); return result;
}
