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

// Default build observes one native call. SAN14_REPLAY is a separate development
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
#ifdef SAN14_REPLAY
static void readCommandFile(const wchar_t* path,uint32_t (&words)[26]) {
    FILE* file=nullptr; if(_wfopen_s(&file,path,L"rb") || !file) throw std::runtime_error("Cannot open command file");
    size_t n=fread(words,1,sizeof(words),file); int trailing=fgetc(file); fclose(file);
    if(n!=sizeof(words) || trailing!=EOF) throw std::runtime_error("Command file must be exactly 104 bytes");
}
template<class T> static T value(HANDLE p,uint64_t address) { T v{}; readExact(p,address,&v,sizeof(v)); return v; }
static void guardGameReplay(HANDLE process,uint64_t base,uint64_t caller,const uint32_t* words) {
    if(caller-base!=0x7149D9 || words[0]!=666 || words[2]!=1300 || words[14]!=5 || words[15]!=20)
        throw std::runtime_error("Pilot only permits the captured Zhang Lu 1300 / Chang'an command");
    uint64_t root=value<uint64_t>(process,base+0x1FCA1E0);
    uint64_t world=value<uint64_t>(process,root+0x85130);
    if(value<uint16_t>(process,world+0x34)!=203 || value<uint8_t>(process,world+0x36)!=8 ||
       value<uint8_t>(process,world+0x37)!=11 || value<uint8_t>(process,world+0x3A)!=12)
        throw std::runtime_error("Pilot date/player mismatch");
    uint64_t city=value<uint64_t>(process,root+0xDAA8+19*8);
    uint64_t person=value<uint64_t>(process,root+0x148+666*8);
    uint8_t districtId=value<uint8_t>(process,person+0x118);
    if(districtId==0 || districtId>51) throw std::runtime_error("Invalid actor district");
    uint64_t district=value<uint64_t>(process,root+0xDE40+districtId*8);
    if(value<uint16_t>(process,city+0x10)!=19 || value<uint16_t>(process,person+0x10)!=666 ||
       value<uint8_t>(process,district+0x10)!=12 || value<uint8_t>(process,district+0x14)!=18 ||
       value<uint8_t>(process,city+0x30)!=districtId ||
       value<uint16_t>(process,person+0x11A)!=value<uint16_t>(process,city+0x4E) ||
       value<uint32_t>(process,city+0x3C)!=15204)
        throw std::runtime_error("Pilot ownership/resources mismatch");
    for(unsigned i=1;i<=500;i++) {
        uint64_t unit=value<uint64_t>(process,root+0x7DF60+i*8);
        if(value<uint8_t>(process,unit+0x10) && value<uint16_t>(process,unit+0x12)==666)
            throw std::runtime_error("Zhang Lu already has an army unit");
    }
}
#endif

int wmain(int argc,wchar_t** argv) {
    const int expectedArgc=
#ifdef SAN14_REPLAY
        8;
#else
        6;
#endif
    if(argc!=expectedArgc) { std::fwprintf(stderr,L"Usage: probe pid base rva timeout_seconds log.jsonl [expected.bin recorded.bin]\n"); return 2; }
    DWORD pid=wcstoul(argv[1],nullptr,0);
    uint64_t base=_wcstoui64(argv[2],nullptr,0), rva=_wcstoui64(argv[3],nullptr,0), target=base+rva;
    unsigned timeout=wcstoul(argv[4],nullptr,0);
    if(!pid || timeout<1 || timeout>900 || !base || rva>0x3000000) return 2;
    FILE* log=_wfsopen(argv[5],L"w",_SH_DENYNO); if(!log) return 2;
    HANDLE process=nullptr, debugProcess=nullptr; bool attached=false, eventPending=false, initialBreak=true, stopping=false, hit=false;
    DEBUG_EVENT event{}; std::map<DWORD,TracedThread> threads;
    SetConsoleCtrlHandler(signalHandler,TRUE);
    int result=1;
    try {
        DWORD access=PROCESS_QUERY_INFORMATION|PROCESS_VM_READ;
#ifdef SAN14_REPLAY
        access|=PROCESS_VM_WRITE|PROCESS_VM_OPERATION;
        uint32_t expected[26]{}, replacement[26]{};
        readCommandFile(argv[6],expected); readCommandFile(argv[7],replacement);
        if(expected[0]!=666 || expected[2]!=1000 || replacement[2]!=1300)
            throw std::runtime_error("Pilot requires a 1000-to-1300 troop-count substitution");
        for(int i=0;i<26;i++) if(i!=2 && expected[i]!=replacement[i])
            throw std::runtime_error("Pilot permits no other parameter differences");
#endif
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
        uint16_t mz=0; readExact(process,base,&mz,sizeof(mz));
        if(mz!=0x5a4d) throw std::runtime_error("Expected module base");
        uint8_t code[16]; readExact(process,target,code,sizeof(code));
        check(DebugActiveProcess(pid),"DebugActiveProcess"); attached=true;
        check(DebugSetProcessKillOnExit(FALSE),"Disable debuggee termination");
        const ULONGLONG deadline=GetTickCount64()+timeout*1000ULL;
        std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"target_rva\":%llu}\n",pid,rva); std::fflush(log);
        while(true) {
            if(!stopping && (stopRequested || GetTickCount64()>=deadline)) {
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
                        c.Dr7=(c.Dr7&~(DWORD64(0xf)<<16))|1;
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
                        if(c.Rip==target && (c.Dr6&1)) {
                            uint32_t words[26]; uint64_t caller=0;
                            readExact(process,c.Rcx,words,sizeof(words)); readExact(process,c.Rsp,&caller,8);
#ifdef SAN14_REPLAY
                            if(c.Rdx!=1 || memcmp(words,expected,sizeof(words)))
                                throw std::runtime_error("Live command does not match the checked expected command");
                            if(!_wcsicmp(leaf,L"SAN14PK_SC.exe")) guardGameReplay(process,base,caller,replacement);
                            SIZE_T written=0;
                            BOOL ok=WriteProcessMemory(process,reinterpret_cast<void*>(c.Rcx),replacement,sizeof(replacement),&written);
                            uint32_t verify[26]{};
                            SIZE_T read=0;
                            BOOL readOk=ReadProcessMemory(process,reinterpret_cast<void*>(c.Rcx),verify,sizeof(verify),&read);
                            if(!ok || written!=sizeof(replacement) || !readOk || read!=sizeof(verify) || memcmp(verify,replacement,sizeof(verify))) {
                                SIZE_T restored=0;
                                check(WriteProcessMemory(process,reinterpret_cast<void*>(c.Rcx),words,sizeof(words),&restored),"Restore original command after failed substitution");
                                if(restored!=sizeof(words)) throw std::runtime_error("Partial original-command restore");
                                throw std::runtime_error("Command substitution failed; original command restored");
                            }
                            std::fprintf(log,"{\"event\":\"recorded_command_substituted\",\"original_soldiers\":1000,\"recorded_soldiers\":1300,\"bytes\":104}\n");
                            memcpy(words,replacement,sizeof(words));
#endif
                            std::fprintf(log,"{\"event\":\"submit_entry\",\"thread_id\":%lu,\"argument_pointer\":%llu,\"flags\":%llu,\"caller_rva\":%llu,\"words\":[",event.dwThreadId,c.Rcx,c.Rdx,caller-base);
                            for(int i=0;i<26;i++) std::fprintf(log,"%s%u",i?",":"",words[i]);
                            std::fprintf(log,"]}\n"); std::fflush(log);
                            hit=true; stopping=true; status=DBG_CONTINUE;
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
