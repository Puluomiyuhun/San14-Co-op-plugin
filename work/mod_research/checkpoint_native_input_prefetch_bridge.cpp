#include "checkpoint_native_input_prefetch_bridge.h"
namespace checkpoint_native_input_prefetch {
namespace{thread_local Scope* active=nullptr;}
Scope::Scope(const Config&c)noexcept:config_(c),previous_(active),thread_(GetCurrentThreadId()){active=this;}
Scope::~Scope(){active=previous_;}
void ObservationFault(DWORD code)noexcept{
    if(!active)return;
    active->report_.status=Status::ObserverFault;active->report_.exception_code=code;
    active->report_.pending=checkpoint_native_input_pending::Report{};
    active->observing_=false;
}
void Observe(const Frame*f){
    auto*s=active;if(!s)return;
    if(s->observing_){s->report_.status=Status::Reentrant;return;}
    s->report_=Report{};
    if(s->thread_!=GetCurrentThreadId()){s->report_.status=Status::WrongThread;return;}
    if(!f||!s->config_.pending||!s->config_.call_id||!s->config_.expected_call_return||
       f->return_address!=s->config_.expected_call_return){s->report_.status=Status::WrongSite;return;}
    if((f->gpr[Rsp]&15)!=0){s->report_.status=Status::WrongStack;return;}
    if(f->gpr[Rsi]!=reinterpret_cast<std::uintptr_t>(s->config_.user)){s->report_.status=Status::WrongUser;return;}
    s->report_.captured=*f;s->observing_=true;
    if(s->config_.before_observation)s->config_.before_observation(s->config_.probe_context);
    // Probe reentry/fault must not be followed by a fresh successful receipt.
    if(s->report_.status==Status::Reentrant){s->observing_=false;return;}
    s->report_.pending=s->config_.pending->ObserveBeforeFetch(s->config_.binding,s->config_.call_id,s->config_.user);
    s->report_.status=s->report_.pending.error==checkpoint_native_input_pending::Error::None?Status::Observed:Status::PendingRejected;
    s->observing_=false;
}
}
extern "C" void CheckpointPrefetchObserve(const checkpoint_native_input_prefetch::Frame*f)noexcept{
    // Nothing catches exceptions from the relocated ORIGINAL load in assembly.
    // Only the observer is contained; a fault provides no new admission receipt.
    __try {checkpoint_native_input_prefetch::Observe(f);}
    __except(EXCEPTION_EXECUTE_HANDLER){checkpoint_native_input_prefetch::ObservationFault(GetExceptionCode());}
}
