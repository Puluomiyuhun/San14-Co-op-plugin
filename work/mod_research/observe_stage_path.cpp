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
#include <set>

// Derived observation-only stage logger. SAN14_REPLAY is a separate development
// build which substitutes a recorded command at that existing native call only.
// Neither build patches game code, allocates remote code or creates a game call.
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
static void dateFields(FILE* log,HANDLE p,uint64_t world) {
    unsigned char date[8]; readExact(p,world+0x34,date,8);
    uint32_t inputs[4];readExact(p,world+0x450,inputs,16);
    std::fprintf(log,"\"date\":[%u,%u,%u],\"player\":%u,\"world_inputs\":[%u,%u,%u,%u]",
        unsigned(date[0]|date[1]<<8),date[2],date[3],date[6],inputs[0],inputs[1],inputs[2],inputs[3]);
}

static void pathState(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c) {
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    uint64_t filter=rd<uint64_t>(p,base+0x201EC70);
    std::fprintf(log,",\"subday\":%u,\"rbp\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"eax\":%u,\"tick_ms\":%llu,\"pending_94\":%u,\"effect_pending_98\":%u,\"effect_count\":%llu,\"pair_count\":%llu,\"special_filter\":%u,\"world_165c\":%u",
        rd<uint8_t>(p,world+0x38),c.Rbp,c.Rsi,c.Rdi,uint32_t(c.Rax),GetTickCount64(),
        rd<uint32_t>(p,base+0x1A24D84),rd<uint32_t>(p,base+0x1A38AB8),rd<uint64_t>(p,base+0x1A38A58),
        rd<uint64_t>(p,base+0x1A38900),filter?rd<uint32_t>(p,filter):0,rd<uint8_t>(p,world+0x165C));
}
static void onePair(FILE* log,HANDLE p,uint64_t node) {
    uint64_t side=rd<uint64_t>(p,node);
    if(!side)throw std::runtime_error("Null pair first side");
    unsigned char a[24],b[24];readExact(p,side,a,sizeof(a));readExact(p,node+8,b,sizeof(b));
    std::fprintf(log,"{\"a\":\"");hexBytes(log,a,sizeof(a));std::fprintf(log,"\",\"b\":\"");hexBytes(log,b,sizeof(b));std::fprintf(log,"\"}");
}
static void allPairs(FILE* log,HANDLE p,uint64_t base) {
    uint64_t count=rd<uint64_t>(p,base+0x1A38900),node=rd<uint64_t>(p,base+0x1A388E0),last=0,visited=0;
    if(count>2048)throw std::runtime_error("Unexpected pair count");
    std::fprintf(log,",\"pairs\":[");
    while(node) {
        if(visited>=count || rd<uint64_t>(p,node+0x38)!=last)throw std::runtime_error("Pair links/count mismatch");
        if(visited)std::fprintf(log,",");onePair(log,p,node);visited++;last=node;node=rd<uint64_t>(p,node+0x30);
    }
    if(visited!=count)throw std::runtime_error("Pair count mismatch");std::fprintf(log,"]");
}
static void inputLists(FILE* log,HANDLE p,uint64_t base,uint64_t root) {
    const uint64_t first=rd<uint64_t>(p,root+0x7DF60);
    std::fprintf(log,",\"input_lists\":[");
    const unsigned offsets[]={0x58,0x68,0x88,0x98,0x138};
    for(unsigned li=0;li<5;li++) {
        unsigned off=offsets[li];bool ann=off==0x138;
        uint64_t pool=base+(ann?0x1FC9760:0x201D3A0),vt=rd<uint64_t>(p,root+off);
        unsigned expected=ann?0x12AA618:off==0x88?0x123F3C8:off==0x98?0x123F3D8:0x123E200;
        if(vt!=base+expected || !rd<uint64_t>(p,pool+8))throw std::runtime_error("Input list type/pool mismatch");
        uint64_t handle=rd<uint64_t>(p,root+off+8),count=0,node=0,tail=0;
        if(handle) {
            unsigned slot=rd<uint32_t>(p,handle),cap=rd<uint32_t>(p,pool+0x40);
            if(cap!=(ann?0x40u:0x14000u)||slot>=cap)throw std::runtime_error("Input list handle mismatch");
            count=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x28)+slot*8);
            node=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x10)+slot*8);
            tail=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x18)+slot*8);
        }
        if(count>(ann?128u:501u))throw std::runtime_error("Input list count outside bound");
        std::fprintf(log,"%s{\"root_offset\":%u,\"count\":%llu,\"entries\":[",li?",":"",off,count);
        uint64_t visited=0,previous=0;std::set<uint64_t> seen;
        while(node) {
            if(visited>=count||!seen.insert(node).second||rd<uint64_t>(p,node+(ann?0x38:0x10))!=previous)throw std::runtime_error("Input list links invalid");
            if(visited)std::fprintf(log,",");
            if(ann) {
                unsigned char raw[48];readExact(p,node,raw,sizeof(raw));std::fprintf(log,"{\"raw_00_30\":\"");hexBytes(log,raw,sizeof(raw));std::fprintf(log,"\",\"army_members\":[");
                for(unsigned k=0;k<3;k++) {
                    uint64_t object;std::memcpy(&object,raw+k*8,8);long long id=-1;
                    if(object>=first&&object<first+501*0x200&&(object-first)%0x200==0)id=(object-first)/0x200;
                    std::fprintf(log,"%s%lld",k?",":"",id);
                }
                std::fprintf(log,"]}");
            } else {
                uint64_t object=rd<uint64_t>(p,node);unsigned id;
                if(off==0x58||off==0x68) {
                    if(object<first||object>=first+501*0x200||(object-first)%0x200||rd<uint64_t>(p,object)!=base+0x123E288)throw std::runtime_error("Invalid army list element");
                    id=unsigned((object-first)/0x200);
                } else id=rd<uint16_t>(p,object+0x10);
                std::fprintf(log,"%u",id);
            }
            visited++;previous=node;node=rd<uint64_t>(p,node+(ann?0x30:8));
        }
        if(visited!=count||previous!=tail)throw std::runtime_error("Input list tail/count mismatch");std::fprintf(log,"]}");
    }
    std::fprintf(log,"]");
}
static void forceInputs(FILE* log,HANDLE p,uint64_t root) {
    std::fprintf(log,",\"forces\":[");
    for(unsigned i=0;i<52;i++) {
        uint64_t f=rd<uint64_t>(p,root+0xDCA0+i*8);unsigned char rel[52];readExact(p,f+0xEA,rel,sizeof(rel));
        std::fprintf(log,"%s{\"id\":%u,\"field_12\":%u,\"field_194\":%u,\"relations\":\"",i?",":"",i,rd<uint8_t>(p,f+0x12),rd<uint8_t>(p,f+0x194));hexBytes(log,rel,sizeof(rel));std::fprintf(log,"\"}");
    }
    std::fprintf(log,"]");
}
static void stageSample(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    const uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,c.Rbx)!=base+0x12CC770 || rd<uint64_t>(p,world)!=base+0x12AA638)
        throw std::runtime_error("Stage/world vtable mismatch");
    uint32_t stage=rd<uint32_t>(p,c.Rbx+0x484);
    if(stage>30) throw std::runtime_error("Invalid progress stage");
    uint64_t armies[501];readExact(p,root+0x7DF60,armies,sizeof(armies));
    for(unsigned i=0;i<501;i++) if(armies[i]!=armies[0]+i*0x200) throw std::runtime_error("Army table layout changed");
    std::vector<unsigned char> rows(501*0x200);readExact(p,armies[0],rows.data(),rows.size());
    std::fprintf(log,"{\"event\":\"stage\",\"seq\":%llu,\"thread\":%lu,\"stage\":%u,",++sequence,tid,stage);
    dateFields(log,p,world);
    pathState(log,p,base,c);
    std::fprintf(log,",\"frame_start_ms\":%u,\"budget_elapsed_ms\":%u",rd<uint32_t>(p,c.Rsp+0x30),uint32_t(c.Rax));
    if(stage==12) { inputLists(log,p,base,root);forceInputs(log,p,root);allPairs(log,p,base); }
    std::fprintf(log,",\"global_rng\":%u,\"armies\":[",rd<uint32_t>(p,base+0x18EB8B0));
    bool comma=false;
    for(unsigned i=1;i<501;i++) {
        const auto row=rows.data()+i*0x200;
        if(!row[0x10] || !(row[0x12]|row[0x13])) continue;
        if(rd<uint64_t>(p,armies[i])!=base+0x123E288) throw std::runtime_error("Army vtable mismatch");
        std::fprintf(log,"%s[%u,\"",comma?",":"",i);hexBytes(log,row+0x10,0x58);std::fprintf(log,"\"]");comma=true;
    }
    std::fprintf(log,"],\"cities\":[");
    for(unsigned i=0;i<52;i++) {
        uint64_t city=rd<uint64_t>(p,root+0xDAA8+i*8);
        unsigned char row[0x58];readExact(p,city+0x10,row,sizeof(row));
        std::fprintf(log,"%s[%u,\"",i?",":"",i);hexBytes(log,row,sizeof(row));std::fprintf(log,"\"]");
    }
    std::fprintf(log,"]}\n");std::fflush(log);stageSamples++;started=true;
}

static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    if(c.Rip==base+0x3F9219) {
        stageSample(log,p,base,c,tid);
        auto day=rd<uint8_t>(p,world+0x37),hour=rd<uint8_t>(p,world+0x38);
        return (day>11 || (day==11&&hour>=12)) || stageSamples>600;
    }
    bool entry=c.Rip==base+0x16C640,ready=c.Rip==base+0x16C685;
    if(entry && c.Rcx!=base+0x1A24CF0)throw std::runtime_error("Battle entry context mismatch");
    if(ready && c.Rbx!=base+0x1A24CF0)throw std::runtime_error("Battle return context mismatch");
    if(!entry&&!ready&&(c.R15!=base+0x1A38840||c.Rdi<1||c.Rdi>7))throw std::runtime_error("Battle phase context mismatch");
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"rva\":%llu,",entry?"battle_entry":ready?"pairs_ready":"pair_phase",++sequence,tid,c.Rip-base);
    dateFields(log,p,world);pathState(log,p,base,c);
    if(entry)std::fprintf(log,",\"caller_rva\":%llu",rd<uint64_t>(p,c.Rsp)-base);
    else if(ready) {allPairs(log,p,base);inputLists(log,p,base,root);forceInputs(log,p,root);}
    else {std::fprintf(log,",\"phase\":%llu,\"pair\":",c.Rdi);onePair(log,p,c.Rbx);}
    std::fprintf(log,"}\n");std::fflush(log);
    if(sequence>3000)throw std::runtime_error("Observation bound exceeded");return false;
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
        if(!fixtureMode && rva!=0x3F9219) throw std::runtime_error("Unexpected native observer entry");
        uint16_t mz=0; readExact(process,base,&mz,sizeof(mz));
        if(mz!=0x5a4d) throw std::runtime_error("Expected module base");
        uint8_t code[16]; readExact(process,target,code,sizeof(code));
        check(DebugActiveProcess(pid),"DebugActiveProcess"); attached=true;
        check(DebugSetProcessKillOnExit(FALSE),"Disable debuggee termination");
        const ULONGLONG deadline=GetTickCount64()+timeout*1000ULL;
        LARGE_INTEGER frequency{};check(QueryPerformanceFrequency(&frequency),"QPC frequency");
        std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"target_rva\":%llu,\"qpc_frequency\":%lld}\n",pid,rva,frequency.QuadPart); std::fflush(log);
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
                        if(!fixtureMode) { c.Dr1=base+0x16C640;c.Dr2=base+0x16C685;c.Dr3=base+0x15C0B0;c.Dr7|=0x54; }
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
                            (!fixtureMode && (((c.Dr6&2) && c.Rip==base+0x16C640) ||
                            ((c.Dr6&4) && c.Rip==base+0x16C685) || ((c.Dr6&8) && c.Rip==base+0x15C0B0)));
                        if(ours) {
                            LARGE_INTEGER costStart{},costEnd{};QueryPerformanceCounter(&costStart);
                            stopping=observe(log,process,base,c,event.dwThreadId) || stopping;
                            QueryPerformanceCounter(&costEnd);
                            std::fprintf(log,"{\"event\":\"observer_cost\",\"seq\":%llu,\"qpc_ticks\":%lld}\n",sequence,costEnd.QuadPart-costStart.QuadPart);std::fflush(log);
                            hit=stageSamples>0 || fixtureSamples>0;
                            status=DBG_CONTINUE;
                            c.Dr6=0;c.EFlags|=0x10000; // resume this instruction once, preserving all ordinary registers
                            
                            check(SetThreadContext(it->second.handle,&c),"Resume observed instruction");

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
