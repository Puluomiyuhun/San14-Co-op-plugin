"""Create new successor sources; frozen originals remain read-only."""
from pathlib import Path
P=Path(__file__).resolve().parent
def main():
    s=(P/'checkpoint_authorized_forward_admission_controller.cpp').read_text()
    s=s.replace('checkpoint_authorized_forward_admission_controller.h','checkpoint_persistent_authorized_controller.h').replace('namespace checkpoint_authorized_forward_admission','namespace checkpoint_persistent_authorized').replace('checkpoint_authorized_forward_admission::','checkpoint_persistent_authorized::')
    s=s.replace('CheckpointAuthorizedForwardAdmission','CheckpointPersistentAuthorized')
    s=s.replace('Controller* volatile controller=nullptr;','''Original fixedOriginal=nullptr;
volatile LONG forwardOnce=0;
volatile LONG64 unownedForwards=0;
struct RouteScope {Controller* controller=nullptr;const CheckpointPushFrame* logical=nullptr;CheckpointPushFrame frame{};unsigned stage=0;bool valid=false,runSeen=false,running=false;};
thread_local RouteScope scopes[64]{};
thread_local unsigned routeDepth=0,routeOverflow=0;
bool mapping(const CheckpointPushFrame* f,std::uint64_t generation,unsigned stage) noexcept {
    checkpoint_persistent_logical_adapter::Mapping m{};
    return f&&checkpoint_persistent_logical_adapter::CurrentMapping(&m)&&m.generation==generation&&m.physicalSlot==0&&
        m.logicalSlot==0&&m.logicalFrame==f&&m.stage==stage&&m.call==f->call_id&&m.thread==GetCurrentThreadId()&&
        f->thread_id==GetCurrentThreadId()&&f->slot==0;
}
bool sameFrame(const CheckpointPushFrame& a,const CheckpointPushFrame& b) noexcept {
    return a.slot==b.slot&&a.call_id==b.call_id&&a.thread_id==b.thread_id&&a.caller_entry_rsp==b.caller_entry_rsp&&
        !std::memcmp(a.args,b.args,sizeof a.args);
}
RouteScope* scope(Controller* c,const CheckpointPushFrame* f) noexcept {
    if(!routeDepth||routeOverflow)return nullptr;
    auto& r=scopes[routeDepth-1];return r.controller==c&&r.logical==f&&sameFrame(r.frame,*f)?&r:nullptr;
}''')
    s=s.replace('if(!c.session||!c.attempt||','if(!c.session.context||!c.session.status||!c.session.bind_menu||!c.generation||c.pending.binding.owner_generation!=c.generation||!c.revoke_queue||get(forwardOnce)!=2||c.original!=fixedOriginal||!c.attempt||')
    s=s.replace('#ifndef CHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE','#ifndef CHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE')
    s=s.replace('if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(&controller),this,nullptr))return false;','')
    s=s.replace('InterlockedExchange(&blocked_,1);ReportLock l(report_lock_);','InterlockedExchange(&blocked_,1);if(config_.revoke_queue)config_.revoke_queue(config_.revoke_queue_context);ReportLock l(report_lock_);')
    s=s.replace('out.stopped=get(stopped_)!=0;out.finished=get(finished_)!=0;return true;','out.stopped=get(stopped_)!=0;out.finished=get(finished_)!=0;out.generation=config_.generation;out.offline_activation=get(offline_)!=0;return true;')
    s=s.replace('void Controller::Stop() noexcept {InterlockedExchange(&stopped_,1);}','void Controller::Stop() noexcept {InterlockedExchange(&stopped_,1);if(config_.revoke_queue)config_.revoke_queue(config_.revoke_queue_context);}')
    s=s.replace('ns::Report session{};config_.session->Snapshot(session);\n    return session.stopRequested||session.error;','SessionStatus session{};\n    return !get(offline_)||!config_.session.status(config_.session.context,session)||!session.admissionReady||session.stopped||session.error;')
    s=s.replace('void Controller::UserAfter(void* p,ns::Session& owner,const CheckpointPushFrame* f) noexcept {\n    auto& s=*static_cast<Controller*>(p);','void Controller::SubmitUserAfter(const CheckpointPushFrame* f) noexcept {\n    auto& s=*this;\n    auto* routed=scope(this,f);\n    if(!routed||!routed->valid||routed->stage!=3||!routed->runSeen||routed->running||!mapping(f,config_.generation,3)){fail(Error::Pair);return;}')
    s=s.replace('if(!f||&owner!=s.config_.session||!s.pair(*f))','if(!f||!s.pair(*f))')
    s=s.replace('ns::QueueReceipt receipt{}','QueueReceipt receipt{}').replace('owner.BindQueuedMenu(receipt)','s.config_.session.bind_menu(s.config_.session.context,receipt)')
    start=s.index('void RunConfigured(NativeCall* call) {')
    s=s[:start]+r'''
bool ConfigureForwardOriginal(Original original) noexcept {
    if(InterlockedCompareExchange(&forwardOnce,1,0))return false;
    Original excluded[]={&CheckpointPersistentAuthorizedOriginal,&CheckpointPersistentBridge0,&CheckpointPersistentBridge1,
        &CheckpointPersistentBridge2,&CheckpointPersistentBridge3,&CheckpointPersistentBridge4,&CheckpointPersistentBridge5,
        reinterpret_cast<Original>(&CheckpointPersistentAuthorizedCallOriginal),reinterpret_cast<Original>(&CheckpointPersistentAuthorizedRun)};
    if(!original){InterlockedExchange(&forwardOnce,-1);return false;}
    for(auto entry:excluded)if(original==entry){InterlockedExchange(&forwardOnce,-1);return false;}
    HMODULE module=nullptr;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
       reinterpret_cast<LPCWSTR>(&ConfigureForwardOriginal),&module)){InterlockedExchange(&forwardOnce,-1);return false;}
    fixedOriginal=original;InterlockedExchange(&forwardOnce,2);return true;
}
void SnapshotForward(ForwardReport& out) noexcept {
    out={};out.configured=get(forwardOnce)==2;out.pinned=out.configured;
    out.unowned_forwards=InterlockedCompareExchange64(&unownedForwards,0,0);
}
bool Controller::ActivateForOfflineExercise() noexcept {
#ifndef CHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE
    return false;
#else
    if(get(initialized_)!=2||get(stopped_)||get(blocked_)||get(active_))return false;
    return InterlockedCompareExchange(&offline_,1,0)==0;
#endif
}
void Controller::RoutedBefore(const CheckpointPushFrame* f,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(routeOverflow||routeDepth==64){++routeOverflow;s.fail(Error::Reentrant);return;}
    auto& r=scopes[routeDepth++];r={};r.controller=&s;r.logical=f;r.stage=1;
    if(f)r.frame=*f;
    r.valid=get(s.initialized_)==2&&mapping(f,s.config_.generation,1);
    {ReportLock l(s.report_lock_);++s.report_.route_started;++s.report_.route_active;}
    if(!r.valid){{ReportLock l(s.report_lock_);++s.report_.route_faults;}s.fail(Error::Pair);r.stage=2;return;}
    try {Before(f,p);}
    catch(...){s.fail(Error::Abnormal);}
    r.stage=2;
}
void Controller::RoutedAfter(const CheckpointPushFrame* f,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);auto* r=scope(&s,f);
    if(!r){ReportLock l(s.report_lock_);++s.report_.ignored_after;return;}
    r->stage=3;
    if(!r->valid||!r->runSeen||r->running||!mapping(f,s.config_.generation,3)){
        {ReportLock l(s.report_lock_);++s.report_.route_faults;}s.fail(Error::Pair);return;
    }
    try {After(f,p);}
    catch(...){s.fail(Error::Abnormal);}
}
void Controller::RoutedFinally(const CheckpointPushFrame* f,const CheckpointLoadWorkerExit* exit,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(routeOverflow){--routeOverflow;return;}
    auto* r=scope(&s,f);if(!r){ReportLock l(s.report_lock_);++s.report_.ignored_finally;return;}
    r->stage=5;
    try {
        if(!exit||!mapping(f,s.config_.generation,5)){{ReportLock l(s.report_lock_);++s.report_.route_faults;}s.fail(Error::Pair);}
        if(exit&&exit->abnormal){{ReportLock l(s.report_lock_);++s.report_.route_abnormal;}s.fail(Error::Abnormal);}
        if(s.pair(*f)){
            // The original and its provider have unwound. A missing/aborted
            // AFTER/Submit is terminal; do not fabricate a successful Close.
            {ReportLock l(s.report_lock_);++s.report_.abandoned_after;}
            s.fail(Error::Abnormal);InterlockedExchange(&s.active_,0);
        }
        if(s.config_.next_finally)s.config_.next_finally(f,exit,s.config_.next_context);
    }catch(...){{ReportLock l(s.report_lock_);++s.report_.route_faults;}s.fail(Error::Abnormal);}
    {ReportLock l(s.report_lock_);++s.report_.route_finished;--s.report_.route_active;}
    *r={};--routeDepth;
}
void RunSelected(NativeCall* call) {
    if(!call||get(forwardOnce)!=2)RaiseException(0xE014AD02,EXCEPTION_NONCONTINUABLE,0,nullptr);
    RouteScope* r=routeDepth&&!routeOverflow?&scopes[routeDepth-1]:nullptr;
    const bool valid=r&&r->valid&&r->stage==2&&!r->runSeen&&!r->running&&
        mapping(r->logical,r->controller->config_.generation,2)&&!std::memcmp(call->args,r->frame.args,sizeof call->args);
    if(!valid){
        if(r){ {ReportLock l(r->controller->report_lock_);++r->controller->report_.route_faults;}r->controller->fail(Error::Pair);}
        call->original=fixedOriginal;InterlockedIncrement64(&unownedForwards);CheckpointPersistentAuthorizedCallOriginal(call);return;
    }
    r->runSeen=true;r->running=true;
    {ReportLock l(r->controller->report_lock_);++r->controller->report_.route_original;}
    try {r->controller->RunOriginal(*call);}
    catch(...){r->running=false;throw;}
    r->running=false;
}
}
extern "C" void CheckpointPersistentAuthorizedRun(checkpoint_persistent_authorized::NativeCall* call){checkpoint_persistent_authorized::RunSelected(call);}
'''
    (P/'checkpoint_persistent_authorized_controller.cpp').write_text(s)
    asm=(P/'checkpoint_authorized_forward_admission_bridge.asm').read_text().replace('CheckpointAuthorizedForwardAdmission','CheckpointPersistentAuthorized')
    (P/'checkpoint_persistent_authorized_bridge.asm').write_text(asm)
if __name__=='__main__':main()
