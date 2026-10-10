// DR6 guard regression in a separate owned process and owned suspended thread.
// No debugger/game attachment; Set/GetThreadContext values are real OS results.
#define wmain menu_recorder_entry_not_run
#include "reward_result_observation.cpp"
#undef wmain
static DWORD WINAPI ownedWait(void*){return 0;}
int wmain(int argc,wchar_t**argv){
    if(argc!=2)return 2;FILE*log=_wfsopen(argv[1],L"wx",_SH_DENYNO);if(!log)return 2;
    HANDLE thread=CreateThread(nullptr,0,ownedWait,nullptr,CREATE_SUSPENDED,nullptr);if(!thread){fclose(log);return 3;}
    unsigned checks=0,roundtrips=0,retained=0;bool passed=false;CONTEXT original{};
    try{
        original=context(thread,CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS);
        need(debugStatusVacant(original),"New owned thread unexpectedly has event status");
        auto armed=registersOf(original);armed.dr0=uint64_t(&ownedWait);armed.dr1=armed.dr0+1;armed.dr2=armed.dr0+2;armed.dr3=armed.dr0+3;armed.dr7=0x55;
        const DWORD64 cases[]={0,1,3,0x2000,0x4000,0x8000,0x4001,0x8003,0xE00F};
        for(auto bits:cases){
            CONTEXT changed{};changed.ContextFlags=CONTEXT_DEBUG_REGISTERS;
            changed.Dr0=armed.dr0;changed.Dr1=armed.dr1;changed.Dr2=armed.dr2;changed.Dr3=armed.dr3;
            changed.Dr7=armed.dr7;changed.Dr6=(original.Dr6&~debugEventMask)|bits;
            check(SetThreadContext(thread,&changed),"Owned DR6 injection");
            const auto actual=context(thread,CONTEXT_CONTROL|CONTEXT_DEBUG_REGISTERS);
            ++roundtrips;if(actual.Dr6&debugEventMask)++retained;
            const bool allowed=mayRestoreDebugStatus(actual,registersOf(original),armed,false);
            need(allowed==debugStatusVacant(actual),"Unexpected actual OS status policy");
            std::fprintf(log,"{\"case\":\"actual_set_get_dr6\",\"requested_event_bits\":%llu,\"readback_dr6\":%llu,\"requested_bits_preserved\":%s,\"restoration_allowed\":%s,\"admission_allowed\":%s}\n",bits,actual.Dr6,(actual.Dr6&debugEventMask)==bits?"true":"false",allowed?"true":"false",debugStatusVacant(actual)?"true":"false");++checks;
            // Windows can clear DR6 when SetThreadContext is used outside an
            // actual debug exception. Never label requested bits as observed.
            auto modeled=actual;modeled.Dr6=(modeled.Dr6&~debugEventMask)|bits;
            need(mayRestoreDebugStatus(modeled,registersOf(original),armed,false)==(bits==0),"Modeled foreign event would be cleared");
            need(debugStatusVacant(modeled)==(bits==0),"Modeled foreign event would be admitted");++checks;
            std::fprintf(log,"{\"case\":\"explicit_context_model\",\"event_bits\":%llu,\"permitted\":%s,\"not_os_event_evidence\":true}\n",bits,bits==0?"true":"false");
        }
        // Exact ownership predicates use explicit CONTEXT values: they are
        // models, unlike the actual OS roundtrips above.
        CONTEXT c{};c.Dr0=armed.dr0;c.Dr1=armed.dr1;c.Dr2=armed.dr2;c.Dr3=armed.dr3;c.Dr7=armed.dr7;c.Dr6=1;c.Rip=armed.dr0;
        const auto saved=registersOf(original);
        need(!mayRestoreDebugStatus(c,saved,armed,false),"Bare matching trap lacks event ownership");++checks;
        need(mayRestoreDebugStatus(c,saved,armed,true),"Delivered owned event rejected");++checks;
        need(mayRestoreDebugStatus(c,saved,armed,false,c.Rip,c.Dr6,&armed),"Exact pending snapshot rejected");++checks;
        need(!mayRestoreDebugStatus(c,saved,armed,false,c.Rip+1,c.Dr6,&armed),"Wrong pending RIP accepted");++checks;
        need(!mayRestoreDebugStatus(c,saved,armed,false,c.Rip,2,&armed),"Wrong pending event bits accepted");++checks;
        c.Dr6=3;need(!mayRestoreDebugStatus(c,saved,armed,true,c.Rip,3,&armed),"Multi-point event claimed");++checks;
        c.Dr6=0x4001;need(!mayRestoreDebugStatus(c,saved,armed,true,c.Rip,c.Dr6,&armed),"Single-step plus own event claimed");++checks;
        c.Dr6=1;c.Dr7^=4;need(!mayRestoreDebugStatus(c,saved,armed,true,c.Rip,c.Dr6,&armed),"Foreign layout claimed");++checks;
        passed=true;
    }catch(const std::exception&e){std::fprintf(log,"{\"error\":\"%s\"}\n",e.what());}
    // The fixture, which introduced these statuses, restores its own thread.
    // The recorder/guard did not clear a rejected event or kill a debuggee.
    if(original.ContextFlags){original.ContextFlags=CONTEXT_DEBUG_REGISTERS;SetThreadContext(thread,&original);}
    ResumeThread(thread);WaitForSingleObject(thread,5000);CloseHandle(thread);fclose(log);
    std::printf("{\"passed\":%s,\"checks\":%u,\"actual_os_status_roundtrips\":%u,\"nonzero_event_bits_retained_by_os\":%u,\"event_ownership_counterexamples_are_context_models\":true,\"game_access\":false,\"debugger_attached\":false}\n",passed?"true":"false",checks,roundtrips,retained);
    return passed?0:1;
}
