#include "checkpoint_serialized_storage_gate.h"

namespace checkpoint_serialized_storage_gate {
namespace {
struct Marker {const Gate*gate;Marker*previous;};
thread_local Marker* current=nullptr;
bool recursive(const Gate*p)noexcept{for(auto*m=current;m;m=m->previous)if(m->gate==p)return true;return false;}
LONG get(volatile LONG&x)noexcept{return InterlockedCompareExchange(&x,0,0);}
}
bool Gate::retire(Error error,State state)noexcept{
    LONG prior=get(state_);
    while(prior!=LONG(State::Stopped)&&prior!=LONG(State::Invalidated)){
        const auto seen=InterlockedCompareExchange(&state_,LONG(state),prior);if(seen==prior)break;prior=seen;
    }
    // No gate report/validation lock held here. Context invalidation is sticky
    // and can reject an in-flight check without waiting for its native owner.
    context_.Invalidate();
    AcquireSRWLockExclusive(&reportLock_);if(report_.error==Error::None)report_.error=error;
    report_.state=State(get(state_));ReleaseSRWLockExclusive(&reportLock_);return false;
}
void Gate::bindingSnapshot()noexcept{
    binding::Report b{};context_.Snapshot(b);
    AcquireSRWLockExclusive(&reportLock_);report_.lastBinding=b;report_.fixtureBuild=b.fixtureBuild!=0;ReleaseSRWLockExclusive(&reportLock_);
}
bool Gate::Open(const binding::Config& config)noexcept{
    AcquireSRWLockExclusive(&reportLock_);++report_.openAttempts;ReleaseSRWLockExclusive(&reportLock_);
    if(recursive(this)){
        AcquireSRWLockExclusive(&reportLock_);++report_.recursionRejected;ReleaseSRWLockExclusive(&reportLock_);
        return retire(Error::Recursion,State::Invalidated);
    }
    if(InterlockedCompareExchange(&once_,1,0))return retire(Error::AlreadyOpened,State::Invalidated);
    if(InterlockedCompareExchange(&state_,LONG(State::Opening),LONG(State::New))!=LONG(State::New))return false;
    Marker mark{this,current};current=&mark;bool ok=false;
    // Opening happens once before callbacks are published. The same lock keeps
    // it disjoint from any validation entrance; no native method is called.
    AcquireSRWLockExclusive(&validationLock_);
    __try{ok=context_.Open(config);}
    __finally{ReleaseSRWLockExclusive(&validationLock_);current=mark.previous;}
    if(!ok){bindingSnapshot();return retire(Error::OpenFailed,State::Invalidated);}
    const auto original=context_.Api();
    if(!original.storage||!original.exists||!original.size||!original.read||!original.validate){bindingSnapshot();return retire(Error::OpenFailed,State::Invalidated);}
    // Publish this immutable copy before Open becomes observable to any thread.
    api_=original;api_.validate=&Validate;api_.validationContext=this;
    const bool published=InterlockedCompareExchange(&state_,LONG(State::Open),LONG(State::Opening))==LONG(State::Opening);
    AcquireSRWLockExclusive(&reportLock_);report_.opened=published?1u:0u;report_.state=State(get(state_));ReleaseSRWLockExclusive(&reportLock_);
    bindingSnapshot();return published;
}
bool Gate::Valid()noexcept{
    AcquireSRWLockExclusive(&reportLock_);++report_.validationAttempts;report_.lastThread=GetCurrentThreadId();ReleaseSRWLockExclusive(&reportLock_);
    // This precedes both state checks and waiting: recursion during Open or
    // through A->B->A is refused instead of deadlocking on our own SRW lock.
    if(recursive(this)){
        AcquireSRWLockExclusive(&reportLock_);++report_.recursionRejected;++report_.validationRejected;ReleaseSRWLockExclusive(&reportLock_);
        return retire(Error::Recursion,State::Invalidated);
    }
    if(get(state_)!=LONG(State::Open)){
        AcquireSRWLockExclusive(&reportLock_);++report_.validationRejected;ReleaseSRWLockExclusive(&reportLock_);return false;
    }
    Marker mark{this,current};current=&mark;
    if(!TryAcquireSRWLockExclusive(&validationLock_)){
        AcquireSRWLockExclusive(&reportLock_);++report_.queued;ReleaseSRWLockExclusive(&reportLock_);
        AcquireSRWLockExclusive(&validationLock_);
    }
    bool ok=false,checked=false;
    __try{
        if(get(state_)==LONG(State::Open)){
            AcquireSRWLockExclusive(&reportLock_);++report_.activeChecks;
            if(report_.activeChecks>report_.maxActiveChecks)report_.maxActiveChecks=report_.activeChecks;
            ReleaseSRWLockExclusive(&reportLock_);
            checked=true;ok=context_.Valid();
            AcquireSRWLockExclusive(&reportLock_);--report_.activeChecks;ReleaseSRWLockExclusive(&reportLock_);
        }
    }__finally{ReleaseSRWLockExclusive(&validationLock_);current=mark.previous;}
    // No locks cross API native method calls; the caller makes those later.
    if(checked&&!ok)retire(Error::ValidationFailed,State::Invalidated);
    ok=ok&&get(state_)==LONG(State::Open);
    AcquireSRWLockExclusive(&reportLock_);if(ok)++report_.validationSucceeded;else ++report_.validationRejected;
    report_.state=State(get(state_));ReleaseSRWLockExclusive(&reportLock_);
    bindingSnapshot();return ok;
}
bool Gate::Validate(void*p)noexcept{return p&&static_cast<Gate*>(p)->Valid();}
native_storage_read::Api Gate::Api()noexcept{return get(state_)==LONG(State::Open)?api_:native_storage_read::Api{};}
void Gate::Invalidate()noexcept{retire(Error::Invalidated,State::Invalidated);}
void Gate::Stop()noexcept{retire(Error::Stopped,State::Stopped);}
void Gate::Snapshot(Report&out)const noexcept{AcquireSRWLockShared(&reportLock_);out=report_;out.state=State(get(const_cast<volatile LONG&>(state_)));ReleaseSRWLockShared(&reportLock_);}
}
