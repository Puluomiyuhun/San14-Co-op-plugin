#include "checkpoint_persistent_route_core.h"
namespace checkpoint_persistent_route {
bool Router::Initialize(const Config& c) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    if(!c.initial.id){InterlockedExchange(&once_,-1);return false;}
    HMODULE module=nullptr;
    static const unsigned residentAnchor=0x52544531;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
        reinterpret_cast<LPCWSTR>(&residentAnchor),&module)){
        InterlockedExchange(&once_,-1);return false;
    }
    generations_[0]=c.initial;count_=1;offline_=c.allowOfflineTransitions;pinned_=true;
    InterlockedExchange(&once_,2);return true;
}
bool Router::Acquire(Lease& l,const Lease* parent) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;
    AcquireSRWLockExclusive(&lock_);
    bool valid=!l.used_ && (!parent||(parent->router_==this&&parent->thread_==GetCurrentThreadId()&&parent->active_));
    if(valid){
        l.router_=this;l.selected_=parent?parent->selected_:&generations_[count_-1];
        l.thread_=GetCurrentThreadId();l.ticket_=++entered_;l.active_=l.used_=true;++active_;
    }else ++rejected_;
    ReleaseSRWLockExclusive(&lock_);return valid;
}
bool Router::Release(Lease& l) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;
    AcquireSRWLockExclusive(&lock_);
    bool valid=l.router_==this&&l.thread_==GetCurrentThreadId()&&l.active_&&l.ticket_&&active_;
    if(valid){l.active_=false;--active_;++released_;}else ++rejected_;
    ReleaseSRWLockExclusive(&lock_);return valid;
}
bool Router::PublishForOfflineExercise(std::uint64_t expected,const Generation& g) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;
    AcquireSRWLockExclusive(&lock_);
    bool valid=offline_&&count_<32&&generations_[count_-1].id==expected&&g.id>expected;
    if(valid){generations_[count_++]=g;++transitions_;}else ++rejected_;
    ReleaseSRWLockExclusive(&lock_);return valid;
}
void Router::Snapshot(Report& r) noexcept {
    r={};if(InterlockedCompareExchange(&once_,0,0)!=2)return;
    AcquireSRWLockShared(&lock_);
    r.current=generations_[count_-1].id;r.entered=entered_;r.released=released_;
    r.active=active_;r.rejected=rejected_;r.transitions=transitions_;r.generations=count_;
    r.initialized=1;r.pinned=pinned_?1:0;
    ReleaseSRWLockShared(&lock_);
}
}
