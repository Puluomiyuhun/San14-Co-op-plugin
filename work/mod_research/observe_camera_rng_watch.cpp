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

// Observation-only camera/tactics trace plus AFTER-write RNG watch. No game code/data writes/calls. Debugger changes scheduling.
struct Registers { DWORD64 dr0, dr1, dr2, dr3, dr6, dr7; };
struct TracedThread { HANDLE handle; Registers original; };
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
static uint64_t sequence=0, stageSamples=0, casualtySamples=0, moveSamples=0, fixtureSamples=0;
static bool started=false, fixtureMode=false;
static uint64_t rngAddress=0;
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
static void tacticRecord(FILE* log,HANDLE p,uint64_t ptr) {
    unsigned char data[0x40];readExact(p,ptr,data,sizeof(data));
    std::fprintf(log,",\"tactic_record\":{\"actor_type\":%u,\"actor_id\":%u,\"raw_hex\":\"",rd<uint32_t>(p,ptr+8),rd<uint32_t>(p,ptr+12));
    hexBytes(log,data,sizeof(data));std::fprintf(log,"\"}");
}
static bool pastTurn(HANDLE p,uint64_t base) {
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    return rd<uint16_t>(p,world+0x34)!=203 || rd<uint8_t>(p,world+0x36)!=8 || rd<uint8_t>(p,world+0x37)>=21;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode){
        auto value=rd<uint32_t>(p,rngAddress);
        std::fprintf(log,"{\"event\":\"fixture_write\",\"thread\":%lu,\"previous_observed\":%u,\"observed_after\":%u}\n",tid,previousObservedRng,value);
        previousObservedRng=value;std::fflush(log);return ++fixtureSamples==7;
    }
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    bool entry=c.Rip==base+0x15B070,decision=c.Rip==base+0x15B12F,rng=(c.Dr6&4)!=0,gate=c.Rip==base+0x3F9344;
    if((int(entry)+int(decision)+int(rng)+int(gate))!=1)throw std::runtime_error("Unexpected route marker");
    if(entry&&c.Rcx!=base+0x1A38A20)throw std::runtime_error("Tactics effect manager mismatch");
    if(gate&&rd<uint64_t>(p,c.Rbx)!=base+0x12CC770)throw std::runtime_error("Progress type mismatch");
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"tick_ms\":%llu,",entry?"tactic_dispatch":decision?"tactic_camera_decision":rng?"rng_write":"combat_gate",++sequence,tid,GetTickCount64());
    routeContext(log,p,base,world);
    if(entry||decision){tacticRecord(log,p,entry?c.Rdx:c.Rbx);if(decision)std::fprintf(log,",\"scene_eligible\":%u",uint32_t(c.Rax));}
    if(rng){
        uint64_t caller=rd<uint64_t>(p,c.Rsp);
        std::fprintf(log,",\"previous_observed\":%u,\"observed_after\":%u,\"ecx_at_stop\":%u,\"caller_rva\":%llu,\"registers\":{\"rip\":%llu,\"rsp\":%llu,\"rbp\":%llu,\"rbx\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"r12\":%llu,\"r13\":%llu,\"r14\":%llu,\"r15\":%llu}",
            previousObservedRng,rd<uint32_t>(p,rngAddress),uint32_t(c.Rcx),caller>=base&&caller<base+0x2238000?caller-base:0,
            c.Rip,c.Rsp,c.Rbp,c.Rbx,c.Rsi,c.Rdi,c.R12,c.R13,c.R14,c.R15);
        std::fprintf(log,",\"rip_after_rva\":%llu",c.Rip>=base&&c.Rip<base+0x2238000?c.Rip-base:0);
        previousObservedRng=rd<uint32_t>(p,rngAddress);
        std::fprintf(log,",\"stack_hex\":\"");
        unsigned char stack[2048];SIZE_T n=0;size_t len=sizeof(stack);
        while(len>=64&&!(ReadProcessMemory(p,reinterpret_cast<void*>(c.Rsp),stack,len,&n)&&n==len))len/=2;
        if(len>=64)hexBytes(log,stack,len);std::fprintf(log,"\"");
    }
    if(gate){
        std::fprintf(log,",\"rbp_gate\":%llu,\"rsi_substep\":%llu,\"armies\":[",c.Rbp,c.Rsi);
        uint64_t pointers[501];readExact(p,root+0x7DF60,pointers,sizeof(pointers));
        for(unsigned i=0;i<501;i++)if(pointers[i]!=pointers[0]+i*0x200)throw std::runtime_error("Army table mismatch");
        std::vector<unsigned char> data(501*0x200);readExact(p,pointers[0],data.data(),data.size());bool comma=false;
        for(unsigned i=1;i<501;i++){
            auto row=data.data()+i*0x200;if(!row[0x10]||!(row[0x12]|row[0x13]))continue;
            uint64_t vt;std::memcpy(&vt,row,8);if(vt!=base+0x123E288)throw std::runtime_error("Army type mismatch");
            std::fprintf(log,"%s[%u,\"",comma?",":"",i);hexBytes(log,row+0x10,0x58);std::fprintf(log,"\"]");comma=true;
        }
        std::fprintf(log,"]");
    }
    std::fprintf(log,"}\n");std::fflush(log);stageSamples++;started=true;
    return sequence>=5000||pastTurn(p,base);
}

int wmain(int argc,wchar_t** argv) {
    const int expectedArgc=
        6;
    if(argc!=expectedArgc) { std::fwprintf(stderr,L"Usage: probe pid base rva timeout_seconds log.jsonl [expected.bin recorded.bin]\n"); return 2; }
    DWORD pid=wcstoul(argv[1],nullptr,0);
    uint64_t base=_wcstoui64(argv[2],nullptr,0), rva=_wcstoui64(argv[3],nullptr,0), target=base+rva;
    unsigned timeout=wcstoul(argv[4],nullptr,0);
    std::wstring stopPath=std::wstring(argv[5])+L".stop";
    if(!pid || timeout<1 || timeout>900 || !base || rva>0x3000000) return 2;
    FILE* log=_wfsopen(argv[5],L"w",_SH_DENYNO); if(!log) return 2;
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
        if(_wcsicmp(leaf,L"SAN14PK_SC.exe") && _wcsicmp(leaf,L"pending_watch_fixture.exe"))
            throw std::runtime_error("Only SAN14PK_SC.exe or the dedicated test fixture is allowed");
        BOOL otherDebugger=FALSE;
        check(CheckRemoteDebuggerPresent(process,&otherDebugger),"Check debugger");
        if(otherDebugger) throw std::runtime_error("Another debugger is already attached");
        fixtureMode=(!_wcsicmp(leaf,L"pending_watch_fixture.exe"));
        rngAddress=fixtureMode?target:base+0x18EB8B0;
        if(rngAddress&3)throw std::runtime_error("Unaligned RNG watch");
        if(!fixtureMode && rva!=0x15B070) throw std::runtime_error("Unexpected native observer entry");
        uint16_t mz=0; readExact(process,base,&mz,sizeof(mz));
        if(mz!=0x5a4d) throw std::runtime_error("Expected module base");
        uint8_t code[16]; readExact(process,target,code,sizeof(code));
        check(DebugActiveProcess(pid),"DebugActiveProcess"); attached=true;
        check(DebugSetProcessKillOnExit(FALSE),"Disable debuggee termination");
        const ULONGLONG deadline=GetTickCount64()+timeout*1000ULL;
        std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"target_rva\":%llu}\n",pid,rva); std::fflush(log);
        while(true) {
            if(!stopping && (stopRequested || GetTickCount64()>=deadline || GetFileAttributesW(stopPath.c_str())!=INVALID_FILE_ATTRIBUTES || (!fixtureMode&&started&&pastTurn(process,base)))) {
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
                    threads.emplace(event.dwThreadId,TracedThread{th,saved});
                    if(!stopping) {
                        c.Dr0=fixtureMode?0:target;c.Dr1=fixtureMode?0:base+0x15B12F;
                        c.Dr2=rngAddress;c.Dr3=fixtureMode?0:base+0x3F9344;c.Dr6=0;
                        // L2 enabled, RW2=01/write, LEN2=11/four bytes.
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x0d000010;
                        if(!fixtureMode)c.Dr7|=0x45;
                        check(SetThreadContext(th,&c),"Arm execution breakpoint");
                    }
                } catch(...) { if(!threads.count(event.dwThreadId)) CloseHandle(th); throw; }
            } else if(event.dwDebugEventCode==EXIT_THREAD_DEBUG_EVENT) {
                auto it=threads.find(event.dwThreadId);
                if(it!=threads.end()) { CloseHandle(it->second.handle); threads.erase(it); }
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
                        bool ours=(c.Dr6&4) || (!fixtureMode &&
                            (((c.Dr6&1)&&c.Rip==target)||((c.Dr6&2)&&c.Rip==base+0x15B12F)||((c.Dr6&8)&&c.Rip==base+0x3F9344)));
                        if(ours) {
                            stopping=observe(log,process,base,c,event.dwThreadId) || stopping;
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
                    std::fprintf(log,"{\"event\":\"detached\",\"captured\":%s,\"registers_restored\":true}\n",hit?"true":"false");
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
                if(!eventPending) { if(SuspendThread(thread.handle)==DWORD(-1)) continue; suspended=true; }
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
