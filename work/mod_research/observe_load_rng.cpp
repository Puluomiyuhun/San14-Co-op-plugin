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

// Observation-only combat gate logger. No game code/data writes or game calls. RNG writers are observed before the native store.
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
static void hexBytes(FILE* f,const unsigned char* data,size_t size) {
    static const char digits[]="0123456789abcdef";
    for(size_t i=0;i<size;i++) { std::fputc(digits[data[i]>>4],f);std::fputc(digits[data[i]&15],f); }
}

template<class T> static bool maybe(HANDLE p,uint64_t a,T& v) {
    SIZE_T n=0;return ReadProcessMemory(p,reinterpret_cast<void*>(a),&v,sizeof(v),&n)&&n==sizeof(v);
}
static void location(FILE* f,HANDLE p,uint64_t base) {
    uint64_t root=0,world=0,vt=0;unsigned char date[8]{};
    bool ok=maybe(p,base+0x1FCA1E0,root)&&root && maybe(p,root+0x85130,world)&&world &&
        maybe(p,world,vt)&&vt==base+0x12AA638&&maybe(p,world+0x34,date);
    if(ok) std::fprintf(f,"\"date\":[%u,%u,%u],\"subday\":%u,\"player\":%u,",unsigned(date[0]|date[1]<<8),date[2],date[3],date[4],date[6]);
    else std::fprintf(f,"\"date\":null,");
    std::fprintf(f,"\"states\":[");
    uint64_t count=0,array=0;bool comma=false;
    if(maybe(p,base+0x19E7310+0x10,count)&&count<=64 && maybe(p,base+0x19E7310+0x20,array)) {
        for(uint64_t i=0;i<count;i++) {
            uint64_t state=0;char name[96]{};
            if(!maybe(p,array+i*8,state)||!state||!maybe(p,state+0x70,name))break;
            name[95]=0;bool valid=true;
            for(unsigned j=0;name[j];j++) if(!((name[j]>='a'&&name[j]<='z')||(name[j]>='A'&&name[j]<='Z')||(name[j]>='0'&&name[j]<='9')||name[j]=='_'))valid=false;
            if(!valid)break;
            std::fprintf(f,"%s\"%s\"",comma?",":"",name);comma=true;
        }
    }
    std::fprintf(f,"]");
}
static void contextDetails(FILE* f,HANDLE p,uint64_t base,const CONTEXT& c) {
    std::fprintf(f,",\"registers\":{\"rip\":%llu,\"rsp\":%llu,\"rbp\":%llu,\"rbx\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"r12\":%llu,\"r13\":%llu,\"r14\":%llu,\"r15\":%llu}",
        c.Rip,c.Rsp,c.Rbp,c.Rbx,c.Rsi,c.Rdi,c.R12,c.R13,c.R14,c.R15);
    unsigned char data[4096]{};size_t size=sizeof(data);SIZE_T count=0;
    while(size>=64 && !(ReadProcessMemory(p,reinterpret_cast<void*>(c.Rsp),data,size,&count)&&count==size))size/=2;
    std::fprintf(f,",\"stack_hex\":\"");if(size>=64)hexBytes(f,data,size);std::fprintf(f,"\"");
    uint64_t vt=0,col=0;uint32_t desc=0;
    if(maybe(p,c.Rbx,vt)&&vt>=base&&vt<base+0x2238000&&maybe(p,vt-8,col)&&col>=base&&col<base+0x2238000&&maybe(p,col+12,desc)&&desc<0x2237000) {
        char name[128]{};
        if(maybe(p,base+desc+16,name)) {
            name[127]=0;bool valid=true;
            for(unsigned i=0;name[i];i++)if(name[i]<32||name[i]>126||name[i]=='"'||name[i]=='\\')valid=false;
            if(valid)std::fprintf(f,",\"rbx_type\":\"%s\"",name);
        }
    }
    // Raw offsets are diagnostic only, not certified script identity fields.
    uint32_t mode=0,offset=0;uint64_t code=0;
    if(maybe(p,c.Rbx+0x1270,mode)&&maybe(p,c.Rbx+0x1274,offset)&&maybe(p,c.Rbx+0x58,code))
        std::fprintf(f,",\"rbx_diagnostic\":{\"field_1270\":%u,\"field_1274\":%u,\"field_58\":%llu}",mode,offset,code);
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    bool seed=c.Rip==base+0x3AA3E0;
    uint64_t caller=rd<uint64_t>(p,c.Rsp);
    uint32_t next=uint32_t(seed||c.Rip==base+0x3AA43B?c.Rcx:c.Rax);
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"tick_ms\":%llu,\"thread\":%lu,\"writer_rva\":%llu,\"caller_rva\":%llu,\"before\":%u,\"after\":%u,\"ecx\":%u,",
        seed?"rng_set":"rng_update",++sequence,GetTickCount64(),tid,c.Rip-base,
        caller>=base&&caller<base+0x2238000?caller-base:0,rd<uint32_t>(p,base+0x18EB8B0),next,uint32_t(c.Rcx));
    location(log,p,base);contextDetails(log,p,base,c);std::fprintf(log,"}\n");std::fflush(log);
    stageSamples++;started=true;return sequence>=2000;
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
        if(_wcsicmp(leaf,L"SAN14PK_SC.exe") && _wcsicmp(leaf,L"submit_probe_fixture.exe"))
            throw std::runtime_error("Only SAN14PK_SC.exe or the dedicated test fixture is allowed");
        BOOL otherDebugger=FALSE;
        check(CheckRemoteDebuggerPresent(process,&otherDebugger),"Check debugger");
        if(otherDebugger) throw std::runtime_error("Another debugger is already attached");
        fixtureMode=(!_wcsicmp(leaf,L"submit_probe_fixture.exe"));
        if(!fixtureMode && rva!=0x3AA3E0) throw std::runtime_error("Unexpected native observer entry");
        uint16_t mz=0; readExact(process,base,&mz,sizeof(mz));
        if(mz!=0x5a4d) throw std::runtime_error("Expected module base");
        uint8_t code[16]; readExact(process,target,code,sizeof(code));
        check(DebugActiveProcess(pid),"DebugActiveProcess"); attached=true;
        check(DebugSetProcessKillOnExit(FALSE),"Disable debuggee termination");
        const ULONGLONG deadline=GetTickCount64()+timeout*1000ULL;
        std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"target_rva\":%llu}\n",pid,rva); std::fflush(log);
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
                    threads.emplace(event.dwThreadId,TracedThread{th,saved});
                    if(!stopping) {
                        c.Dr0=target; c.Dr6=0;
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
                        if(!fixtureMode) { c.Dr1=base+0x3AA3D5;c.Dr2=base+0x3AA43B;c.Dr3=base+0x3AA805;c.Dr7|=0x54; }
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
                        std::fprintf(log,"{\"event\":\"armed\",\"threads\":%zu}\n",threads.size()); std::fflush(log);
                    }
                } else if(codeValue==EXCEPTION_SINGLE_STEP) {
                    auto it=threads.find(event.dwThreadId);
                    if(it!=threads.end()) {
                        auto c=context(it->second.handle,CONTEXT_FULL|CONTEXT_DEBUG_REGISTERS);
                        bool ours=(c.Rip==target && (c.Dr6&1)) ||
                            (!fixtureMode && (((c.Dr6&2) && c.Rip==base+0x3AA3D5) ||
                            ((c.Dr6&4) && c.Rip==base+0x3AA43B) || ((c.Dr6&8) && c.Rip==base+0x3AA805)));
                        if(ours) {
                            bool wasStarted=started;
                            stopping=observe(log,process,base,c,event.dwThreadId) || stopping;
                            hit=stageSamples>0 || fixtureSamples>0;
                            status=DBG_CONTINUE;
                            c.Dr6=0;c.EFlags|=0x10000; // resume this instruction once, preserving all ordinary registers
                            if(started) c.Dr7|=0x40;
                            check(SetThreadContext(it->second.handle,&c),"Resume observed instruction");
                            if(!wasStarted && started) {
                                for(auto& [otherId,other]:threads) if(otherId!=event.dwThreadId) {
                                    auto otherContext=context(other.handle,CONTEXT_DEBUG_REGISTERS);
                                    otherContext.Dr7|=0x40;
                                    check(SetThreadContext(other.handle,&otherContext),"Arm planning return observation");
                                }
                            }
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
