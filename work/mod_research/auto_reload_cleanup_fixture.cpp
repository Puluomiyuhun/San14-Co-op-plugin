// Real Windows thread/handle API checks for the same observer cleanup helper.
// Own process only; no SAN14 access, no fake SuspendThread implementation.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <stdexcept>
#include "auto_reload_cleanup.inc"
static void need(bool b,const char* why){if(!b)throw std::runtime_error(why);}
static DWORD WINAPI waitForStop(void* value){WaitForSingleObject(static_cast<HANDLE>(value),INFINITE);return 17;}
int main(){
    try{
        HANDLE event=CreateEventW(nullptr,TRUE,FALSE,nullptr);need(event!=nullptr,"event");
        DWORD tid=0;HANDLE thread=CreateThread(nullptr,0,waitForStop,event,0,&tid);need(thread!=nullptr,"thread");
        HANDLE queryOnly=OpenThread(THREAD_QUERY_INFORMATION,FALSE,tid);need(queryOnly!=nullptr,"query-only handle");
        unsigned restoredCalls=0;
        auto restore=[&]{CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;need(GetThreadContext(thread,&c)!=FALSE,"get context");need(SetThreadContext(thread,&c)!=FALSE,"restore context");++restoredCalls;};
        auto running=cleanupThread(thread,false,restore);
        need(running.registersRestored&&!running.suspendFailed&&!running.resumeFailed&&restoredCalls==1,"running thread restoration");
        auto denied=cleanupThread(queryOnly,false,restore);
        need(!denied.registersRestored&&denied.suspendFailed&&!denied.threadExited&&restoredCalls==1,"live suspend failure must not claim restoration");
        auto invalid=cleanupThread(INVALID_HANDLE_VALUE,false,restore);
        need(!invalid.registersRestored&&invalid.suspendFailed&&!invalid.threadExited&&restoredCalls==1,"invalid handle must not claim restoration");
        auto throws=cleanupThread(thread,false,[]{throw std::runtime_error("restore failed");});
        need(!throws.registersRestored&&!throws.suspendFailed&&!throws.resumeFailed,"restore failure resumes thread");
        // Test debug-event path with a genuinely suspended thread owned here.
        need(SuspendThread(thread)!=DWORD(-1),"manual suspension");
        auto pending=cleanupThread(thread,true,restore);
        need(pending.registersRestored&&!pending.suspendFailed&&restoredCalls==2,"debug event path");
        need(ResumeThread(thread)==1,"pending path must not change suspend count");
        need(SetEvent(event)!=FALSE,"stop thread");need(WaitForSingleObject(thread,2000)==WAIT_OBJECT_0,"thread exits after restoration");
        // Query-only guarantees SuspendThread fails; GetExitCodeThread proves exit.
        auto exited=cleanupThread(queryOnly,false,restore);
        need(!exited.registersRestored&&exited.threadExited&&exited.suspendFailed&&restoredCalls==2,"exited thread distinguished from live failure");
        CloseHandle(queryOnly);CloseHandle(thread);CloseHandle(event);
        std::puts("{\"result\":\"PASS\",\"cases\":6,\"real_windows_threads\":true,\"scope\":\"Shared cleanup helper against owned threads: running, denied live suspension, invalid handle, restore exception, pending event, confirmed exit.\",\"game_process_access\":false}");
        return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
