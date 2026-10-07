"""Derive a new provider; never edits the frozen predecessor."""
from pathlib import Path
P=Path(__file__).resolve().parent
def main():
    s=(P/'checkpoint_native_input_hwbp.cpp').read_text().replace('checkpoint_native_input_hwbp.h','checkpoint_persistent_input_hwbp.h').replace('namespace checkpoint_native_input_hwbp','namespace checkpoint_persistent_input_hwbp').replace('CHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE','CHECKPOINT_PERSISTENT_INPUT_HWBP_FIXTURE')
    s=s.replace('Config config{};HardwareReceipt report{};SRWLOCK lock=SRWLOCK_INIT;', 'Config config{};HardwareReceipt report{};SRWLOCK lock=SRWLOCK_INIT;\n    Context* owner_context=nullptr;State* registry_next=nullptr;')
    s=s.replace('bool ready=false,route=false,needs_restore=false;','volatile LONG ready=0;bool route=false,needs_restore=false;')
    s=s.replace('State* volatile installed=nullptr;','''SRWLOCK runtimeLock=SRWLOCK_INIT,registryLock=SRWLOCK_INIT;
LONG runtimeState=0;RuntimeReport runtimeReport{};
PVOID permanentHandler=nullptr;
State* registry=nullptr;
volatile LONG64 allocatedContexts=0;
// This sentinel consumes a failed/in-progress Context without exposing a State.
void* const reservedContext=reinterpret_cast<void*>(1);
State* stateOf(const Context& h) noexcept {
    auto* opaque=InterlockedCompareExchangePointer(&const_cast<Context&>(h).opaque,nullptr,nullptr);
    if(!opaque||opaque==reservedContext)return nullptr;
    State* found=nullptr;AcquireSRWLockShared(&registryLock);
    for(auto* s=registry;s;s=s->registry_next)if(s==opaque&&s->owner_context==&h){found=s;break;}
    ReleaseSRWLockShared(&registryLock);return found;
}''')
    start=s.index('bool Initialize(Context&out,const Config&c)noexcept{')
    end=s.index('bool Begin(Context&h,Observe observer',start)
    s=s[:start]+'''bool Initialize(Context&out,const Config&c)noexcept{
    if(InterlockedCompareExchangePointer(&out.opaque,reservedContext,nullptr))return false;
    if(!identity(c.binding)||!c.site_rip||c.helper_deadline_ms<1||c.helper_deadline_ms>10000||!bytes(c.site_rip))return false;
    State*s=new(std::nothrow)State;if(!s)return false;
    s->config=c;s->report.binding=c.binding;s->report.site_rip=c.site_rip;s->owner_context=&out;
    AcquireSRWLockExclusive(&registryLock);s->registry_next=registry;registry=s;ReleaseSRWLockExclusive(&registryLock);
    InterlockedIncrement64(&allocatedContexts);InterlockedExchangePointer(&out.opaque,s);
    // Permanent process runtime. Failure is terminal: a later Context cannot
    // retry registration or create a second VEH. No per-State ownership here.
    AcquireSRWLockExclusive(&runtimeLock);
    if(runtimeState==0){
        runtimeState=1;++runtimeReport.initializeAttempts;HMODULE module=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
            reinterpret_cast<LPCWSTR>(&Initialize),&module)){
            runtimeReport.osError=GetLastError();runtimeState=-1;
        }else {
            runtimeReport.modulePinned=1;permanentHandler=AddVectoredExceptionHandler(1,handler);
            if(!permanentHandler){runtimeReport.osError=GetLastError();runtimeState=-1;}
            else {++runtimeReport.handlerRegistrations;runtimeReport.ready=1;runtimeState=2;}
        }
        if(runtimeState==-1)runtimeReport.failed=1;
    }
    const bool ready=runtimeState==2;const DWORD error=runtimeReport.osError;
    {Lock l(s->lock);s->report.module_pinned=runtimeReport.modulePinned;}
    ReleaseSRWLockExclusive(&runtimeLock);
    if(!ready){fail(*s,Error::Handle,error);return false;}
    InterlockedExchange(&s->ready,1);return true;
}
void SnapshotRuntime(RuntimeReport& out) noexcept {
    AcquireSRWLockShared(&runtimeLock);out=runtimeReport;ReleaseSRWLockShared(&runtimeLock);
    out.allocatedContexts=InterlockedCompareExchange64(&allocatedContexts,0,0);
}
''' +s[end:]
    s=s.replace('auto*s=static_cast<State*>(h.opaque);if(!s||!s->ready)return false;','auto*s=stateOf(h);if(!s||get(s->ready)!=1)return false;')
    s=s.replace('auto*s=static_cast<State*>(h.opaque);','auto*s=stateOf(h);')
    s=s.replace('Finish(h);','checkpoint_persistent_input_hwbp::Finish(h);')
    s=s.replace('return Begin(*static_cast<Context*>(h),','return checkpoint_persistent_input_hwbp::Begin(*static_cast<Context*>(h),')
    s=s.replace('{Finish(*static_cast<Context*>(h));','{checkpoint_persistent_input_hwbp::Finish(*static_cast<Context*>(h));')
    s=s.replace('return Snapshot(*static_cast<Context*>(h),','return checkpoint_persistent_input_hwbp::Snapshot(*static_cast<Context*>(h),')
    s=s.replace('if(restored){route=nullptr;if(s->target){CloseHandle(s->target);s->target=nullptr;}}','''bool cleanRestoration=false;
    {Lock l(s->lock);cleanRestoration=restored&&!s->report.restore_uncertain;}
    // Even if a timed-out helper eventually restored DRs, an uncertain receipt
    // remains a same-thread tombstone. Never silently admit the next generation.
    if(cleanRestoration){if(route==s)route=nullptr;if(s->target){CloseHandle(s->target);s->target=nullptr;}}''')
    (P/'checkpoint_persistent_input_hwbp.cpp').write_text(s)
if __name__=='__main__':main()
