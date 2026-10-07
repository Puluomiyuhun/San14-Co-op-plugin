#include "checkpoint_planning_hold_user_dry.h"
namespace checkpoint_planning_hold_user_dry {
bool Adapter::Initialize(const Config&c)noexcept{
    if(initialized_||!c.hold||!c.original)return false;
#ifndef CHECKPOINT_PLANNING_HOLD_OWNED_DRY
    if(c.request_owned_dry_skip)return false;
#endif
    config_=c;owner_=GetCurrentThreadId();initialized_=true;return true;
}
std::uint64_t Adapter::Invoke(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    if(!initialized_)return 0;
    ++report_.entries;report_.native_body_returned_last=false;
    const bool eligible=GetCurrentThreadId()==owner_&&!inside_;
    if(!eligible){++report_.forwarded;return config_.original(a,b,c,d);}
    inside_=true;
    try{
#ifdef CHECKPOINT_PLANNING_HOLD_OWNED_DRY
        if(config_.request_owned_dry_skip&&PlanningHoldUserSkipCandidate(config_.hold,std::uintptr_t(a))){
            // The original User body is intentionally NOT reported as returned.
            // Parent dispatcher/worker cleanup belongs outside this function.
            ++report_.skipped;
            if(config_.owned_replay_pump){++report_.replay_pumps;config_.owned_replay_pump(config_.context);}
            inside_=false;return 0; // Opaque dry substitute, not a native result.
        }
#endif
        ++report_.forwarded;auto result=config_.original(a,b,c,d);++report_.body_returned;report_.native_body_returned_last=true;inside_=false;return result;
    }catch(...){++report_.abnormal;inside_=false;PlanningHoldAbnormal(config_.hold);throw;}
}
}
