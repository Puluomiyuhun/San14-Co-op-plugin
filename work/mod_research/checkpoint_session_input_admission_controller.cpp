#include "checkpoint_session_input_admission_controller.h"
#include <cstring>
namespace checkpoint_session_input_admission {
namespace { Controller* volatile controller=nullptr; }
bool Controller::Initialize(const Config& c) noexcept {
    if(initialized_||!c.session||!c.attempt||!c.original||!c.expected_prefetch_return||!c.queue||
       bool(c.next_before)!=bool(c.next_after)||c.original==&CheckpointSessionInputAdmissionOriginal)return false;
    if(pending_.Bind(c.pending)!=pd::Error::None)return false;
    config_=c;thread_=GetCurrentThreadId();
    if(InterlockedCompareExchangePointer(reinterpret_cast<void*volatile*>(&controller),this,nullptr))return false;
    initialized_=true;return true;
}
void Controller::trace(Event e) noexcept {if(config_.trace)config_.trace(config_.trace_context,e);}
void Controller::fail(Error e) noexcept {InterlockedExchange(&blocked_,1);if(GetCurrentThreadId()==thread_&&report_.error==Error::None)report_.error=e;}
bool Controller::Snapshot(Report& out)const noexcept {
    if(!initialized_||GetCurrentThreadId()!=thread_)return false;
    out=report_;out.active=active_;out.blocked=blocked_!=0;return true;
}
bool Controller::pair(const CheckpointPushFrame& f)const noexcept {
    return active_&&f.call_id==frame_.call_id&&f.thread_id==frame_.thread_id&&f.slot==frame_.slot&&
        f.caller_entry_rsp==frame_.caller_entry_rsp&&!std::memcmp(f.args,frame_.args,sizeof f.args);
}
void Controller::Before(const CheckpointPushFrame* f,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(s.config_.next_before)s.config_.next_before(f,s.config_.next_context);
    if(!f||GetCurrentThreadId()!=s.thread_){s.fail(Error::Pair);return;}
    if(s.finished_||f->args[0]!=s.config_.pending.states[4])return;
    if(s.active_){++s.report_.reentry;s.fail(Error::Reentrant);return;}
    s.frame_=*f;s.active_=true;s.trace(Event::Before);
    s.report_.before=s.pending_.ObserveBefore(s.config_.pending.binding,*f);
    if(s.report_.before.error!=pd::Error::None)s.fail(Error::Pending);
}
void Controller::RunOriginal(NativeCall& call) {
    call.original=config_.original;
    if(GetCurrentThreadId()!=thread_){fail(Error::Pair);CheckpointSessionInputAdmissionCallOriginal(&call);return;}
    ++report_.original_calls;
    if(running_){++report_.reentry;fail(Error::Reentrant);CheckpointSessionInputAdmissionCallOriginal(&call);return;}
    if(finished_||call.args[0]!=config_.pending.states[4]){CheckpointSessionInputAdmissionCallOriginal(&call);return;}
    if(!active_||std::memcmp(call.args,frame_.args,sizeof call.args)){fail(Error::Pair);CheckpointSessionInputAdmissionCallOriginal(&call);return;}
    pf::Config c{};c.pending=&pending_;c.binding=config_.pending.binding;c.call_id=frame_.call_id;
    c.user=reinterpret_cast<void*>(call.args[0]);c.expected_call_return=config_.expected_prefetch_return;
    pf::Scope scope(c);running_=true;++report_.scope_started;trace(Event::OriginalEnter);
    try {CheckpointSessionInputAdmissionCallOriginal(&call);report_.prefetch=scope.GetReport();trace(Event::OriginalReturned);}
    catch(...) {report_.prefetch=scope.GetReport();running_=false;++report_.scope_finished;++report_.original_abnormal;fail(Error::Abnormal);trace(Event::OriginalAbnormal);throw;}
    running_=false;++report_.scope_finished;
}
void Controller::close(std::uint64_t call) noexcept {
    report_.close=pending_.CloseAfter(config_.pending.binding,call);
    if(report_.close==pd::Error::None){active_=false;++report_.closed;trace(Event::Close);}
    else fail(Error::Pending);
}
void Controller::After(const CheckpointPushFrame* f,void* p) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(s.config_.next_after)s.config_.next_after(f,s.config_.next_context);
    if(!f||GetCurrentThreadId()!=s.thread_){s.fail(Error::Pair);return;}
    if(s.finished_||f->args[0]!=s.config_.pending.states[4])return;
    if(!s.pair(*f)){s.fail(Error::Pair);return;}
    ++s.report_.after_calls;s.trace(Event::After);
    s.report_.native_rax=f->result_rax;std::memcpy(s.report_.native_xmm0,f->result_xmm0,16);
    s.report_.after=s.pending_.ObserveAfter(s.config_.pending.binding,*f);
    ns::Report session{};s.config_.session->Snapshot(session);
    if(session.stopRequested||session.error)s.fail(Error::Stopped);
    if(s.report_.prefetch.status!=pf::Status::Observed)s.fail(Error::Prefetch);
    if(!s.report_.after.pending_admission_candidate||s.report_.after.error!=pd::Error::None)s.fail(Error::Pending);
    if(s.blocked_)s.close(f->call_id); // Session may suppress userAfter on Stop/error.
}
void Controller::UserAfter(void* p,ns::Session& owner,const CheckpointPushFrame* f) noexcept {
    auto& s=*static_cast<Controller*>(p);
    if(!f||GetCurrentThreadId()!=s.thread_||&owner!=s.config_.session){s.fail(Error::Pair);return;}
    if(s.blocked_||s.finished_||!s.pair(*f))return;
    ns::Report session{};owner.Snapshot(session);
    if(session.stopRequested||session.error){s.fail(Error::Stopped);s.close(f->call_id);return;}
    pd::Ticket ticket{};s.report_.begin=s.pending_.BeginAuthorizedLoadPush(s.config_.pending.binding,f->call_id,ticket);
    if(s.report_.begin!=pd::Error::None){s.fail(Error::Pending);s.close(f->call_id);return;}
    s.trace(Event::Authorize);
    try {
        ++s.report_.queue_calls;const auto menu=s.config_.queue(s.config_.queue_context);
        ++s.report_.queue_returned;s.trace(Event::QueueReturned);
        s.report_.commit=s.pending_.CommitAuthorizedLoadPush(ticket,menu);
        if(s.report_.commit!=pd::Error::None)s.fail(Error::Commit);
        else {
            ++s.report_.commit_succeeded;s.trace(Event::Commit);
            // Stop/error after an uncertain queue must never start a request.
            owner.Snapshot(session);
            if(session.stopRequested||session.error)s.fail(Error::Stopped);
            else {
                ns::QueueReceipt receipt{};receipt.attempt=s.config_.attempt;receipt.userCall=f->call_id;
                receipt.thread=f->thread_id;receipt.user=std::uintptr_t(f->args[0]);
                receipt.menu=reinterpret_cast<std::uintptr_t>(menu.data);receipt.nativeQueueReturned=true;
                if(owner.BindQueuedMenu(receipt)){++s.report_.menu_bound;s.finished_=true;s.trace(Event::Bind);}
                else s.fail(Error::Bind);
            }
        }
    }catch(...){s.fail(Error::Queue);}
    s.close(f->call_id);
}
void RunConfigured(NativeCall* call) {
    // Entry is never published until Initialize succeeds. This is deliberately
    // not an installer; no fallback address can be safely invented here.
    auto* c=controller;if(!c||!call)RaiseException(0xE014AD01,EXCEPTION_NONCONTINUABLE,0,nullptr);
    c->RunOriginal(*call);
}
}
extern "C" void CheckpointSessionInputAdmissionRun(checkpoint_session_input_admission::NativeCall* call){checkpoint_session_input_admission::RunConfigured(call);}
