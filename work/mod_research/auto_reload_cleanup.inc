// Shared by the observer and a separate real-thread cleanup fixture.
// Failure to suspend a live/unqueryable thread is never reported as restored.
struct ARCleanupResult {
    bool registersRestored=false,threadExited=false,suspendFailed=false,resumeFailed=false;
};
template<class Restore> static ARCleanupResult cleanupThread(HANDLE thread,bool eventPending,Restore restoreRegisters){
    ARCleanupResult result;
    bool suspended=false;
    if(!eventPending){
        if(SuspendThread(thread)==DWORD(-1)){
            result.suspendFailed=true;
            DWORD exitCode=STILL_ACTIVE;
            result.threadExited=GetExitCodeThread(thread,&exitCode)&&exitCode!=STILL_ACTIVE;
            return result;
        }
        suspended=true;
    }
    try{restoreRegisters();result.registersRestored=true;}catch(...){}
    if(suspended&&ResumeThread(thread)==DWORD(-1))result.resumeFailed=true;
    return result;
}
