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
#include <bcrypt.h>
#include <tlhelp32.h>
#include <set>
#pragma comment(lib,"bcrypt.lib")

// Native Save/army span recorder. Retains the reviewed debugger cleanup loop
// from checkpoint_title_join_live.cpp; frozen predecessors remain unchanged.
// No Frida trampoline, code patch, vtable publication, game call or gameplay input.
struct Registers { DWORD64 dr0, dr1, dr2, dr3, dr6, dr7; };
struct TracedThread { HANDLE handle; Registers original; Registers armed{};unsigned epoch=0;bool armedKnown=false; };
static volatile LONG stopRequested = 0;
static BOOL WINAPI signalHandler(DWORD) { InterlockedExchange(&stopRequested, 1); return TRUE; }
static void check(BOOL success, const char* message) {
    if (!success) throw std::runtime_error(std::string(message)+" error="+std::to_string(GetLastError()));
}
static CONTEXT context(HANDLE thread, DWORD flags) {
    CONTEXT c{}; c.ContextFlags = flags; check(GetThreadContext(thread,&c),"GetThreadContext"); return c;
}
static Registers registersOf(const CONTEXT& c) { return {c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}; }
// Intel DR7 bit10 reads as 1 in hardware but Windows stored CONTEXT may retain 0.
// Compare every other bit; do not mistake the required-one bit for foreign layout.
static bool ownedTrap(const CONTEXT& c,const Registers& armed) {
    const auto reason=c.Dr6&0xF;
    return c.Dr0==armed.dr0&&c.Dr1==armed.dr1&&c.Dr2==armed.dr2&&c.Dr3==armed.dr3&&(c.Dr7&~DWORD64(0x400))==(armed.dr7&~DWORD64(0x400))&&!(c.Dr6&0xE000)&&
        ((reason==1&&c.Rip==armed.dr0)||(reason==2&&c.Rip==armed.dr1)||(reason==4&&c.Rip==armed.dr2)||(reason==8&&c.Rip==armed.dr3));
}
#include "reward_menu_observation_debug_status.inc"
static uint64_t restoredThreads=0;
static DWORD restorationFailedThread=0;
static void restore(HANDLE thread, const Registers& saved) {
    CONTEXT c{}; c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
    c.Dr0=saved.dr0; c.Dr1=saved.dr1; c.Dr2=saved.dr2; c.Dr3=saved.dr3; c.Dr6=saved.dr6; c.Dr7=saved.dr7;
    restorationFailedThread=GetThreadId(thread);
    check(SetThreadContext(thread,&c),"Restore debug registers");
    auto verify=context(thread,CONTEXT_DEBUG_REGISTERS);auto actual=registersOf(verify);
    if(memcmp(&actual,&saved,sizeof saved))throw std::runtime_error("Debug register restore readback mismatch");
    ++restoredThreads;restorationFailedThread=0;
}
static void readExact(HANDLE process, uint64_t address, void* output, size_t bytes) {
    SIZE_T count=0;
    check(ReadProcessMemory(process,reinterpret_cast<void*>(address),output,bytes,&count),"ReadProcessMemory");
    if(count!=bytes) throw std::runtime_error("Partial process read");
}


template<class T> static T rd(HANDLE p,uint64_t a) { T v{};readExact(p,a,&v,sizeof(v));return v; }
static uint64_t sequence=0,stageSamples=0,fixtureSamples=0;
static bool fixtureMode=false;
#include "a_save_observation_payload.inc"
#include "a_save_observation_binding.inc"

int wmain(int argc,wchar_t** argv) {
    const int expectedArgc=
        10;
    if(argc!=expectedArgc) { std::fwprintf(stderr,L"Usage: probe pid base rva timeout_seconds log.jsonl [expected.bin recorded.bin]\n"); return 2; }
    DWORD pid=wcstoul(argv[1],nullptr,0);
    uint64_t base=_wcstoui64(argv[2],nullptr,0), rva=_wcstoui64(argv[3],nullptr,0), target=base+rva;
    unsigned timeout=wcstoul(argv[4],nullptr,0);
    std::wstring stopPath=std::wstring(argv[5])+L".stop";
    if(!pid || timeout<1 || timeout>3600 || !base || rva>0x3000000) return 2;
    const uint64_t birth=_wcstoui64(argv[6],nullptr,0);
    selectedUser=_wcstoui64(argv[7],nullptr,0);selectedStack=_wcstoui64(argv[8],nullptr,0);
    if(!setExpectedName(argv[9]))return 2;
    observationPid=pid;observationBirth=birth;observationBase=base;
    FILE* log=_wfsopen(argv[5],L"wx",_SH_DENYNO); if(!log) return 2;
    HANDLE process=nullptr, debugProcess=nullptr; bool attached=false, eventPending=false, initialBreak=true, stopping=false, hit=false;
    DEBUG_EVENT event{}; std::map<DWORD,TracedThread> threads;
    SetConsoleCtrlHandler(signalHandler,TRUE);
    int result=1;DWORD pendingStatus=DBG_EXCEPTION_NOT_HANDLED;unsigned debugEvents=0;
    std::set<DWORD> systemBreakThreads;bool cleanupBreakIssued=false,cleanupBreakConsumed=false,normalCleanup=false;
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
#ifdef A_SAVE_OBSERVATION_FIXTURE
        fixtureMode=(!_wcsicmp(leaf,L"submit_probe_fixture.exe"));
#else
        if(_wcsicmp(leaf,L"SAN14PK_SC.exe"))throw std::runtime_error("Production recorder refuses fixture/other process");
#endif
        validateBinding(process,path,base,birth,rva);
        emitBinding(log);
        uint16_t mz=0; readExact(process,base,&mz,sizeof(mz));
        if(mz!=0x5a4d) throw std::runtime_error("Expected module base");
        uint8_t code[16]; readExact(process,target,code,sizeof(code));
        bindSystemBreakpoints(process,pid);
        check(DebugActiveProcess(pid),"DebugActiveProcess"); attached=true;
        check(DebugSetProcessKillOnExit(FALSE),"Disable debuggee termination");
        ULONGLONG deadline=GetTickCount64()+20000ULL; // Attach bootstrap only; actual window starts at armed.
        std::fprintf(log,"{\"event\":\"attached\",\"pid\":%lu,\"target_rva\":%llu}\n",pid,rva); std::fflush(log);
        while(true) {
            if(!stopping && (stopRequested || GetTickCount64()>=deadline || GetFileAttributesW(stopPath.c_str())!=INVALID_FILE_ATTRIBUTES)) {
                stopping=true;
                if(!initialBreak){check(DebugBreakProcess(debugProcess),"Request cleanup breakpoint");cleanupBreakIssued=true;}
            }
            if(!WaitForDebugEvent(&event,250)) {
                if(GetLastError()==ERROR_SEM_TIMEOUT) continue;
                check(FALSE,"WaitForDebugEvent");
            }
            eventPending=true;
            DWORD status=DBG_CONTINUE;pendingStatus=DBG_EXCEPTION_NOT_HANDLED;
            if(++debugEvents>20000&&!stopping){stopping=true;stopReason="debug_event_limit";if(!initialBreak){check(DebugBreakProcess(debugProcess),"Request event-limit cleanup breakpoint");cleanupBreakIssued=true;}}
            if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT || event.dwDebugEventCode==CREATE_THREAD_DEBUG_EVENT) {
                if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT) {
                    debugProcess=event.u.CreateProcessInfo.hProcess;
                    if(uint64_t(event.u.CreateProcessInfo.lpBaseOfImage)!=base)throw std::runtime_error("CREATE_PROCESS image base mismatch");
                }
                if(event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT && event.u.CreateProcessInfo.hFile) CloseHandle(event.u.CreateProcessInfo.hFile);
                if(event.dwDebugEventCode==CREATE_THREAD_DEBUG_EVENT&&uint64_t(event.u.CreateThread.lpStartAddress)==systemBreakin)systemBreakThreads.insert(event.dwThreadId);
                HANDLE eventThread=event.dwDebugEventCode==CREATE_PROCESS_DEBUG_EVENT?event.u.CreateProcessInfo.hThread:event.u.CreateThread.hThread;
                if(eventThread)CloseHandle(eventThread);
                HANDLE th=OpenThread(THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|THREAD_QUERY_INFORMATION,FALSE,event.dwThreadId);
                check(th!=nullptr,"OpenThread");
                try {
                    auto c=context(th,CONTEXT_DEBUG_REGISTERS);
                    if(c.Dr7&0xff) throw std::runtime_error("Existing hardware breakpoint; not replacing it");
                    if(!debugStatusVacant(c))throw std::runtime_error("Existing unowned debug status; not clearing it");
                    auto saved=registersOf(c);
                    threads.emplace(event.dwThreadId,TracedThread{th,saved});
                    if(!stopping) {
                        armPoints(c,base,target,event.dwThreadId);
                        check(SetThreadContext(th,&c),"Arm execution breakpoint");
                        threads.at(event.dwThreadId).armed=registersOf(c);threads.at(event.dwThreadId).epoch=pointEpoch;threads.at(event.dwThreadId).armedKnown=true;
                    }
                } catch(...) { if(!threads.count(event.dwThreadId)) CloseHandle(th); throw; }
            } else if(event.dwDebugEventCode==EXIT_THREAD_DEBUG_EVENT) {
                systemBreakThreads.erase(event.dwThreadId);
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
                const bool systemBreak=codeValue==EXCEPTION_BREAKPOINT&&(initialBreak||cleanupBreakIssued)&&
                    uint64_t(event.u.Exception.ExceptionRecord.ExceptionAddress)==systemBreakpoint&&systemBreakThreads.count(event.dwThreadId);
                if(systemBreak) {
                    if(cleanupBreakIssued)cleanupBreakConsumed=true;
                    initialBreak=false; status=DBG_CONTINUE;
                    if(!stopping) {
                        deadline=GetTickCount64()+timeout*1000ULL;
                        std::fprintf(log,"{\"event\":\"armed\",\"threads\":%zu}\n",threads.size()); std::fflush(log);
                    }
                } else if(codeValue==EXCEPTION_SINGLE_STEP) {
                    auto it=threads.find(event.dwThreadId);
                    if(it!=threads.end()) {
                        auto c=context(it->second.handle,CONTEXT_FULL|CONTEXT_DEBUG_REGISTERS);
                        const bool ours=it->second.armedKnown&&ownedTrap(c,it->second.armed);
                        if(!ours)std::fprintf(log,"{\"event\":\"unowned_debug_status\",\"dr0\":%llu,\"expected_dr0\":%llu,\"dr6\":%llu,\"dr7\":%llu,\"expected_dr7\":%llu,\"known\":%s}\n",c.Dr0,it->second.armed.dr0,c.Dr6,c.Dr7,it->second.armed.dr7,it->second.armedKnown?"true":"false");
                        if(ours) {
                            pendingStatus=DBG_CONTINUE; // Our HW exception remains handled if sampling throws.
                            auto oldEpoch=pointEpoch;
                            if(it->second.epoch!=pointEpoch)std::fprintf(log,"{\"event\":\"owned_old_layout_consumed\",\"thread\":%lu,\"armed_epoch\":%u,\"current_epoch\":%u}\n",event.dwThreadId,it->second.epoch,pointEpoch);
                            stopping=observe(log,process,base,c,event.dwThreadId) || stopping;
                            hit=stageSamples>0 || fixtureSamples>0;
                            status=DBG_CONTINUE;
                            c.Dr6=0;c.EFlags|=0x10000; // resume this instruction once, preserving all ordinary registers
                            if(!stopping)armPoints(c,base,target,event.dwThreadId);
                            check(SetThreadContext(it->second.handle,&c),"Resume observed instruction");
                            it->second.armed=registersOf(c);it->second.epoch=pointEpoch;
                            if(!stopping&&oldEpoch!=pointEpoch) {
                                for(auto& [otherId,other]:threads) if(otherId!=event.dwThreadId) {
                                    auto otherContext=context(other.handle,CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS);
                                    if(other.armedKnown&&ownedTrap(otherContext,other.armed)){
                                        std::fprintf(log,"{\"event\":\"pending_owned_layout_retained\",\"thread\":%lu,\"armed_epoch\":%u}\n",otherId,other.epoch);
#ifdef A_SAVE_OBSERVATION_FIXTURE
                                        if(fixtureMode&&selectedUser&&fixtureSamples>=64){
                                            stopping=true;stopReason="fixture_pending_owned_cleanup";
                                            if(selectedStack==1)throw std::runtime_error("Fixture sampling failure with pending owned event");
                                        }
#endif
                                        continue; // Its queued event must consume the old DR6/RIP/layout.
                                    }
                                    if(stopping)continue;
                                    otherContext.ContextFlags=CONTEXT_DEBUG_REGISTERS;
                                    armPoints(otherContext,base,target,otherId);
                                    check(SetThreadContext(other.handle,&otherContext),"Rearm load boundary observation");
                                    other.armed=registersOf(otherContext);other.epoch=pointEpoch;other.armedKnown=true;
                                }
                            }
                        }
                    }
                }
                pendingStatus=status;
                if(status==DBG_EXCEPTION_NOT_HANDLED)std::fprintf(log,"{\"event\":\"forwarded_exception\",\"code\":%lu,\"thread\":%lu,\"first_chance\":%lu,\"address\":%llu}\n",codeValue,event.dwThreadId,event.u.Exception.dwFirstChance,uint64_t(event.u.Exception.ExceptionRecord.ExceptionAddress));
                // A requested remote break must be consumed before detach; otherwise
                // its new thread could reach INT3 after the debugger has departed.
                if(stopping && status==DBG_CONTINUE&&(!cleanupBreakIssued||systemBreak)) {
                    std::fprintf(log,"{\"event\":\"summary\",\"reason\":\"%s\",\"chain_complete\":%s,\"selected_records\":%llu,\"filtered_hits\":%llu,\"debug_events\":%u,\"lost_events\":0}\n",stopReason,chainComplete?"true":"false",sequence,filteredHits,debugEvents);
                    normalCleanup=true;
                    result=(fixtureMode?hit:chainComplete)?0:4; break;
                }
            }
            check(ContinueDebugEvent(event.dwProcessId,event.dwThreadId,status),"Continue event"); eventPending=false;
        }
    } catch(const std::exception& error) {
        std::fprintf(log,"{\"event\":\"error\",\"message\":\"%s\"}\n",error.what());
        std::fprintf(stderr,"%s\n",error.what());
    }
    if(attached) {
        // On uncertainty retain the debugger (and any held event/suspensions).
        // Never detach leaving an unverified owned execution breakpoint behind.
        struct PendingOwned {uint64_t rip=0,dr6=0;Registers armed{};unsigned epoch=0;};
        std::map<DWORD,PendingOwned> pendingOwned;
        std::set<DWORD> suspendedByUs,statusWarned;bool warned=false;
        for(;;) {
            bool restored=true;
            for(auto& [tid,thread]:threads) {
                DWORD exitCode=0;
                if(GetExitCodeThread(thread.handle,&exitCode)&&exitCode!=STILL_ACTIVE){suspendedByUs.erase(tid);pendingOwned.erase(tid);continue;}
                try {
                    if(!eventPending&&!suspendedByUs.count(tid)) {
                        check(SuspendThread(thread.handle)!=DWORD(-1),"Suspend cleanup thread");suspendedByUs.insert(tid);
                    }
                    // Freeze pending ownership before clearing any debug registers.
                    // Never treat the currently delivered event as still queued.
                    if(!(eventPending&&tid==event.dwThreadId)&&!pendingOwned.count(tid)&&thread.armedKnown){
                        const auto beforeRestore=context(thread.handle,CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS);
                        if(ownedTrap(beforeRestore,thread.armed)){
                            pendingOwned.emplace(tid,PendingOwned{beforeRestore.Rip,beforeRestore.Dr6,thread.armed,thread.epoch});
                            std::fprintf(log,"{\"event\":\"cleanup_pending_owned_frozen\",\"thread\":%lu,\"rip\":%llu,\"dr6\":%llu,\"epoch\":%u}\n",tid,beforeRestore.Rip,beforeRestore.Dr6,thread.epoch);
                        }
                    }
                    const auto restoreContext=context(thread.handle,CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS);
                    const auto current=registersOf(restoreContext);
                    const auto sameLayout=[](const Registers&a,const Registers&b){return a.dr0==b.dr0&&a.dr1==b.dr1&&a.dr2==b.dr2&&a.dr3==b.dr3&&(a.dr7&~DWORD64(0x400))==(b.dr7&~DWORD64(0x400));};
                    if(thread.armedKnown&&!sameLayout(current,thread.armed)&&!sameLayout(current,thread.original))throw std::runtime_error("Foreign debug layout changed; retained for attention");
                    const bool deliveredOwned=thread.armedKnown&&eventPending&&tid==event.dwThreadId&&
                        event.dwDebugEventCode==EXCEPTION_DEBUG_EVENT&&pendingStatus==DBG_CONTINUE&&
                        event.u.Exception.ExceptionRecord.ExceptionCode==EXCEPTION_SINGLE_STEP&&
                        uint64_t(event.u.Exception.ExceptionRecord.ExceptionAddress)==restoreContext.Rip;
                    const auto frozen=pendingOwned.find(tid);
                    if(!mayRestoreDebugStatus(restoreContext,thread.original,thread.armed,deliveredOwned,
                        frozen==pendingOwned.end()?0:frozen->second.rip,
                        frozen==pendingOwned.end()?0:frozen->second.dr6,
                        frozen==pendingOwned.end()?nullptr:&frozen->second.armed)){
                        if(statusWarned.insert(tid).second){
                            std::fprintf(log,"{\"event\":\"cleanup_foreign_debug_status_retained\",\"thread\":%lu,\"dr6\":%llu,\"original_dr6\":%llu,\"rip\":%llu}\n",tid,current.dr6,thread.original.dr6,restoreContext.Rip);std::fflush(log);
                        }
                        throw std::runtime_error("Unowned DR6 event status; retained for attention");
                    }
                    restore(thread.handle,thread.original);
                } catch(...) {restored=false;restorationFailedThread=tid;}
            }
            if(restored) {
                for(auto it=suspendedByUs.begin();it!=suspendedByUs.end();) {
                    const auto th=threads.find(*it);
                    if(th==threads.end()||ResumeThread(th->second.handle)!=DWORD(-1))it=suspendedByUs.erase(it);
                    else {restored=false;restorationFailedThread=*it;++it;}
                }
            }
            if(restored)break;
            if(!warned){std::fprintf(log,"{\"event\":\"restoration_uncertain_debugger_retained\",\"failed_thread\":%lu,\"manual_attention_required\":true}\n",restorationFailedThread);std::fflush(log);warned=true;}
            Sleep(250);
        }
        bool continued=true;
        if(eventPending){continued=ContinueDebugEvent(event.dwProcessId,event.dwThreadId,pendingStatus)!=FALSE;if(continued)eventPending=false;}
        while(!continued){
            std::fprintf(log,"{\"event\":\"continue_failed_debugger_retained\",\"os_error\":%lu}\n",GetLastError());std::fflush(log);
            Sleep(250);continued=ContinueDebugEvent(event.dwProcessId,event.dwThreadId,pendingStatus)!=FALSE;
        }
        // Drain an already requested debugger break before detaching even on
        // an error path. Restored game threads have no observer DR slots now.
        while(!pendingOwned.empty()||initialBreak||(cleanupBreakIssued&&!cleanupBreakConsumed)) {
            DEBUG_EVENT pending{};
            if(!WaitForDebugEvent(&pending,250)){if(GetLastError()==ERROR_SEM_TIMEOUT)continue;Sleep(250);continue;}
            DWORD forward=DBG_CONTINUE;
            if(pending.dwDebugEventCode==CREATE_THREAD_DEBUG_EVENT){
                if(uint64_t(pending.u.CreateThread.lpStartAddress)==systemBreakin)systemBreakThreads.insert(pending.dwThreadId);
                if(pending.u.CreateThread.hThread)CloseHandle(pending.u.CreateThread.hThread);
            }else if(pending.dwDebugEventCode==LOAD_DLL_DEBUG_EVENT){if(pending.u.LoadDll.hFile)CloseHandle(pending.u.LoadDll.hFile);}
            else if(pending.dwDebugEventCode==EXIT_THREAD_DEBUG_EVENT){pendingOwned.erase(pending.dwThreadId);}
            else if(pending.dwDebugEventCode==EXCEPTION_DEBUG_EVENT){
                const bool owned=pending.u.Exception.ExceptionRecord.ExceptionCode==EXCEPTION_BREAKPOINT&&
                    uint64_t(pending.u.Exception.ExceptionRecord.ExceptionAddress)==systemBreakpoint&&systemBreakThreads.count(pending.dwThreadId);
                const auto queued=pendingOwned.find(pending.dwThreadId);
                const bool ownedHardware=pending.u.Exception.ExceptionRecord.ExceptionCode==EXCEPTION_SINGLE_STEP&&
                    queued!=pendingOwned.end()&&uint64_t(pending.u.Exception.ExceptionRecord.ExceptionAddress)==queued->second.rip;
                forward=(owned||ownedHardware)?DBG_CONTINUE:DBG_EXCEPTION_NOT_HANDLED;
                if(ownedHardware){
                    std::fprintf(log,"{\"event\":\"cleanup_owned_exception_drained\",\"thread\":%lu,\"rip\":%llu,\"captured_dr6\":%llu,\"epoch\":%u}\n",pending.dwThreadId,queued->second.rip,queued->second.dr6,queued->second.epoch);
                    pendingOwned.erase(queued);
                }
                if(owned){initialBreak=false;if(cleanupBreakIssued)cleanupBreakConsumed=true;}
                if(!owned&&!ownedHardware)std::fprintf(log,"{\"event\":\"cleanup_foreign_exception_forwarded\",\"code\":%lu,\"thread\":%lu}\n",pending.u.Exception.ExceptionRecord.ExceptionCode,pending.dwThreadId);
            }else if(pending.dwDebugEventCode==EXIT_PROCESS_DEBUG_EVENT){
                std::fprintf(log,"{\"event\":\"cleanup_process_exit\",\"code\":%lu}\n",pending.u.ExitProcess.dwExitCode);
                cleanupBreakConsumed=true;initialBreak=false;pendingOwned.clear();attached=false;normalCleanup=false;result=3;
            }
            while(!ContinueDebugEvent(pending.dwProcessId,pending.dwThreadId,forward))Sleep(250);
        }
        BOOL detached=!attached||DebugActiveProcessStop(pid);
        while(!detached){Sleep(250);detached=DebugActiveProcessStop(pid);}
        std::fprintf(log,"{\"event\":\"restore_detail\",\"verified_threads\":%llu,\"failed_thread\":%lu}\n",restoredThreads,restorationFailedThread);
        if(normalCleanup){
            std::fprintf(log,"{\"event\":\"restore_verified\",\"threads\":%llu,\"all_six_debug_registers\":true,\"owned_queue_drained\":true}\n",restoredThreads);
            std::fprintf(log,"{\"event\":\"detached\",\"captured\":%s,\"registers_restored\":true,\"owned_queue_drained\":true}\n",hit?"true":"false");
        }else std::fprintf(log,"{\"event\":\"error_cleanup\",\"registers_restored\":true,\"continued\":true,\"owned_queue_drained\":true,\"detached\":%s}\n",detached?"true":"false");
        std::fflush(log);
    }
    for(auto& [tid,thread]:threads) CloseHandle(thread.handle);
    if(debugProcess)CloseHandle(debugProcess);
    if(process) CloseHandle(process);
    std::fclose(log); return result;
}
