#include "checkpoint_bound_forward_admission_controller.h"
#include <cstring>
#include <new>
namespace checkpoint_bound_forward_admission {
namespace {
Controller* volatile controller=nullptr;
LONG get(volatile LONG& value)noexcept{return InterlockedCompareExchange(&value,0,0);}
struct ReportLock {SRWLOCK* p;explicit ReportLock(SRWLOCK& l):p(&l){AcquireSRWLockExclusive(p);}~ReportLock(){ReleaseSRWLockExclusive(p);}};
}
bool Controller::Initialize(const Config& c) noexcept {
    if(InterlockedCompareExchange(&initialized_,1,0))return false;
    if(!c.session||!c.attempt||!c.original||!c.expected_prefetch_site||!c.queue||!c.prefetch_provider.context||!c.prefetch_provider.begin||!c.prefetch_provider.finish||!c.prefetch_provider.snapshot||
       !c.pending.states[4]||bool(c.next_before)!=bool(c.next_after)||c.original==&CheckpointBoundForwardAdmissionOriginal)return false;
#ifndef CHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE
    // Production wrapper must lead to this profile's exact native User entry,
    // never back to any dispatch bridge or another wrapper.
    if(c.original!=reinterpret_cast<Original>(c.pending.profile_base+0x3F9B00)||c.expected_prefetch_site!=c.pending.profile_base+0x3F9DAF)return false;
#endif
    // No native spans inspected and no pending adapter bound to the installer.
    // Full existing Span/Binding validation runs on actual BEFORE below.
    config_=c;{ReportLock l(report_lock_);report_.initialized_thread=GetCurrentThreadId();}
    if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(&controller),this,nullptr))return false;
    InterlockedExchange(&initialized_,2);return true;
}
void Controller::trace(Event e) noexcept {if(config_.trace)config_.trace(config_.trace_context,e);}
void Controller::fail(Error e) noexcept {
    InterlockedExchange(&blocked_,1);ReportLock l(report_lock_);
    if(report_.error==Error::None)report_.error=e;
}
bool Controller::Snapshot(Report& out)const noexcept {
    if(get(initialized_)!=2)return false;
    ReportLock l(report_lock_);out=report_;out.active=get(active_)!=0;out.blocked=get(blocked_)!=0;
    out.stopped=get(stopped_)!=0;out.finished=get(finished_)!=0;return true;
}
void Controller::Stop() noexcept {InterlockedExchange(&stopped_,1);}
bool Controller::stopped()const noexcept {
    if(get(stopped_))return true;
    ns::Report session{};config_.session->Snapshot(session);
    return session.stopRequested||session.error;
}
bool Controller::irrelevant(std::uint64_t user)const noexcept {
    return get(finished_)||user!=config_.pending.states[4];
}
bool Controller::pair(const CheckpointPushFrame& f)const noexcept {
    // Metadata is locked even for stale/foreign negative callbacks.
    ReportLock l(report_lock_);
    return get(active_)==2&&DWORD(get(owner_thread_))==GetCurrentThreadId()&&
        f.thread_id==GetCurrentThreadId()&&f.call_id==frame_.call_id&&f.thread_id==frame_.thread_id&&f.slot==frame_.slot&&
        f.caller_entry_rsp==frame_.caller_entry_rsp&&!std::memcmp(f.args,frame_.args,sizeof f.args);
}
void Controller::Before(const CheckpointPushFrame* f,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(s.config_.next_before)s.config_.next_before(f,s.config_.next_context);
    if(get(s.initialized_)!=2)return;
    if(f&&(s.irrelevant(f->args[0])||s.stopped()||get(s.blocked_))){ReportLock l(s.report_lock_);++s.report_.ignored_before;return;}
    if(!f||!f->call_id||!f->caller_entry_rsp||f->slot!=0||f->thread_id!=GetCurrentThreadId()){s.fail(Error::Pair);return;}
    if(InterlockedCompareExchange(&s.active_,1,0)){ {ReportLock l(s.report_lock_);++s.report_.reentry;}s.fail(Error::Reentrant);return;}
    bool stale=false;
    {ReportLock l(s.report_lock_);stale=f->call_id<=s.last_call_;if(!stale){s.last_call_=f->call_id;s.frame_=*f;InterlockedExchange(&s.owner_thread_,LONG(f->thread_id));}}
    if(stale){s.fail(Error::Pair);InterlockedExchange(&s.active_,0);return;}
    // active_ protects lifetime: no reset while original/AFTER owns this call.
    s.pending_.~Adapter();new(&s.pending_)pd::Adapter;
    const auto bound=s.pending_.Bind(s.config_.pending);
    pd::Report before{};
    if(bound==pd::Error::None)before=s.pending_.ObserveBefore(s.config_.pending.binding,*f);else before.error=bound;
    {ReportLock l(s.report_lock_);s.report_.before=before;s.report_.call_thread=f->thread_id;++s.report_.callback_bindings;}
    InterlockedExchange(&s.active_,2);s.trace(Event::Before);
    if(before.error!=pd::Error::None)s.fail(Error::Pending);
}
void Controller::RunOriginal(NativeCall& call) {
    call.original=config_.original;
    {ReportLock l(report_lock_);++report_.original_calls;}
    // A configured bridge may run before Session starts accepting callbacks.
    // Without a real admission BEFORE there is no ticket/provider/queue path.
    // Forward once; do not poison the later first accepted callback.
    if(irrelevant(call.args[0])||get(active_)==0){
        {ReportLock l(report_lock_);++report_.ignored_original;}CheckpointBoundForwardAdmissionCallOriginal(&call);return;
    }
    bool belongs=false;
    {ReportLock l(report_lock_);belongs=get(active_)==2&&DWORD(get(owner_thread_))==GetCurrentThreadId()&&!std::memcmp(call.args,frame_.args,sizeof call.args);}
    if(!belongs){
        fail(Error::Pair);CheckpointBoundForwardAdmissionCallOriginal(&call);return;
    }
    if(InterlockedCompareExchange(&running_,1,0)){
        {ReportLock l(report_lock_);++report_.reentry;}fail(Error::Reentrant);CheckpointBoundForwardAdmissionCallOriginal(&call);return;
    }
    {ReportLock l(report_lock_);++report_.scope_started;}trace(Event::OriginalEnter);
    // Provider begins only after real BEFORE bound this callback's adapter.
    // Finish is required even if Begin fails or the original unwinds.
    const auto& provider=config_.prefetch_provider;
    const bool began=provider.begin(provider.context,ObservePrefetch,this,config_.pending.binding,frame_.call_id,reinterpret_cast<void*>(call.args[0]));
    {ReportLock l(report_lock_);report_.provider_begin=began;}
    try {
        CheckpointBoundForwardAdmissionCallOriginal(&call);
        finish_provider();trace(Event::OriginalReturned);
    }catch(...) {
        finish_provider();
        {ReportLock l(report_lock_);++report_.scope_finished;++report_.original_abnormal;}
        InterlockedExchange(&running_,0);fail(Error::Abnormal);trace(Event::OriginalAbnormal);throw;
    }
    InterlockedExchange(&running_,0);{ReportLock l(report_lock_);++report_.scope_finished;}

}
hw::PendingReport Controller::ObservePrefetch(void* context,const hw::Binding& binding,std::uint64_t call,const void* user) noexcept {
    auto& s=*static_cast<Controller*>(context);
    bool owned=false;
    {ReportLock l(s.report_lock_);owned=get(s.active_)==2&&get(s.running_)==1&&DWORD(get(s.owner_thread_))==GetCurrentThreadId()&&
        call==s.frame_.call_id&&reinterpret_cast<std::uintptr_t>(user)==s.frame_.args[0];}
    if(!owned){hw::PendingReport denied{};denied.error=pd::Error::CallPair;return denied;}
    return s.pending_.ObserveBeforeFetch(binding,call,user);
}
void Controller::finish_provider() noexcept {
    const auto& provider=config_.prefetch_provider;provider.finish(provider.context);
    hw::HardwareReceipt receipt{};const bool read=provider.snapshot(provider.context,receipt);
    ReportLock l(report_lock_);report_.prefetch=receipt;report_.provider_snapshot=read;
}
bool Controller::hardware_valid()const noexcept {
    ReportLock l(report_lock_);const auto& r=report_.prefetch;const auto& b=config_.pending.binding;
    return report_.provider_begin&&report_.provider_snapshot&&r.capture_kind==hw::CaptureKind::HardwareExecuteContext&&
        r.error==hw::Error::None&&r.entered==1&&r.captured==1&&r.finished==1&&r.restored==1&&!r.restore_uncertain&&
        r.module_pinned==1&&r.original_code_unchanged&&r.observer_calls==1&&
        r.site_rip==config_.expected_prefetch_site&&r.thread==frame_.thread_id&&r.thread==GetCurrentThreadId()&&
        r.call_id==frame_.call_id&&r.user==frame_.args[0]&&r.gpr[6]==frame_.args[0]&&
        r.binding.attempt==b.attempt&&r.binding.attachment==b.attachment&&r.binding.owner_generation==b.owner_generation&&
        r.pending.error==pd::Error::None&&r.pending.stage==pd::Stage::BeforeMenuFetch&&r.pending.call_id==frame_.call_id&&
        r.pending.pending_admission_candidate;
}
void Controller::close(std::uint64_t call) noexcept {
    const auto result=pending_.CloseAfter(config_.pending.binding,call);
    {ReportLock l(report_lock_);report_.close=result;if(result==pd::Error::None)++report_.closed;}
    if(result==pd::Error::None){trace(Event::Close);InterlockedExchange(&active_,0);}else fail(Error::Pending);
}
void Controller::After(const CheckpointPushFrame* f,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(s.config_.next_after)s.config_.next_after(f,s.config_.next_context);
    if(get(s.initialized_)!=2)return;
    // Completed/new User frames and Stop-late callbacks must not be compared
    // against the retired call's owner. Existing in-flight old call still pairs.
    if(f&&(s.irrelevant(f->args[0])||(get(s.active_)==0&&(s.stopped()||get(s.blocked_))))){ReportLock l(s.report_lock_);++s.report_.ignored_after;return;}
    if(!f||!s.pair(*f)){s.fail(Error::Pair);return;}
    {ReportLock l(s.report_lock_);++s.report_.after_calls;s.report_.native_rax=f->result_rax;std::memcpy(s.report_.native_xmm0,f->result_xmm0,16);}
    s.trace(Event::After);const auto after=s.pending_.ObserveAfter(s.config_.pending.binding,*f);
    {ReportLock l(s.report_lock_);s.report_.after=after;}
    if(s.stopped())s.fail(Error::Stopped);
    if(!s.hardware_valid())s.fail(Error::Prefetch);
    if(!after.pending_admission_candidate||after.error!=pd::Error::None)s.fail(Error::Pending);
    if(get(s.blocked_))s.close(f->call_id);
}
void Controller::UserAfter(void* p,ns::Session& owner,const CheckpointPushFrame* f) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(get(s.finished_)||get(s.blocked_))return;
    if(!f||&owner!=s.config_.session||!s.pair(*f)){s.fail(Error::Pair);return;}
    if(s.stopped()){s.fail(Error::Stopped);s.close(f->call_id);return;}
    pd::Ticket ticket{};const auto begin=s.pending_.BeginAuthorizedLoadPush(s.config_.pending.binding,f->call_id,ticket);
    {ReportLock l(s.report_lock_);s.report_.begin=begin;}
    if(begin!=pd::Error::None){s.fail(Error::Pending);s.close(f->call_id);return;}
    if(InterlockedCompareExchange(&s.queue_once_,1,0)){s.fail(Error::Queue);s.close(f->call_id);return;}
    s.trace(Event::Authorize);
    // Stop is a request, not a fence. If it arrives inside native queue the
    // returned queue is retained; no cancellation, retry or fabricated success.
    if(s.stopped()||get(s.blocked_)){if(s.stopped())s.fail(Error::Stopped);s.close(f->call_id);return;}
    try {
        {ReportLock l(s.report_lock_);++s.report_.queue_calls;}
        const auto menu=s.config_.queue(s.config_.queue_context);
        {ReportLock l(s.report_lock_);++s.report_.queue_returned;}s.trace(Event::QueueReturned);
        const auto commit=s.pending_.CommitAuthorizedLoadPush(ticket,menu);
        {ReportLock l(s.report_lock_);s.report_.commit=commit;}
        if(commit!=pd::Error::None)s.fail(Error::Commit);
        else {
            {ReportLock l(s.report_lock_);++s.report_.commit_succeeded;}s.trace(Event::Commit);
            if(s.stopped())s.fail(Error::Stopped);
            else if(get(s.blocked_)){} // A reentrant/foreign error during queue remains terminal.
            else {
                ns::QueueReceipt receipt{};receipt.attempt=s.config_.attempt;receipt.userCall=f->call_id;
                receipt.thread=f->thread_id;receipt.user=std::uintptr_t(f->args[0]);
                receipt.menu=reinterpret_cast<std::uintptr_t>(menu.data);receipt.nativeQueueReturned=true;
                if(owner.BindQueuedMenu(receipt)){
                    {ReportLock l(s.report_lock_);++s.report_.menu_bound;}InterlockedExchange(&s.finished_,1);s.trace(Event::Bind);
                }else s.fail(Error::Bind);
            }
        }
    }catch(...){s.fail(Error::Queue);}
    s.close(f->call_id);
}
void RunConfigured(NativeCall* call) {
    auto* c=controller;if(!c||!call)RaiseException(0xE014AD01,EXCEPTION_NONCONTINUABLE,0,nullptr);
    c->RunOriginal(*call);
}
}
extern "C" void CheckpointBoundForwardAdmissionRun(checkpoint_bound_forward_admission::NativeCall* call){checkpoint_bound_forward_admission::RunConfigured(call);}
