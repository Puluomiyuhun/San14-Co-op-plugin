#include "checkpoint_persistent_logical_adapter.h"
#include <cstring>
namespace checkpoint_persistent_logical_adapter {
namespace {
struct Entry {
    Adapter* adapter=nullptr;
    const CheckpointLoadWorkerFrame* physical=nullptr;
    CheckpointLoadWorkerFrame initial{},worker{},expected{};
    CheckpointPushFrame dispatch{};
    std::uint64_t generation=0,claimedToken=0;
    unsigned stage=0,logicalWorkerDepth=0,nativeOwnerDepth=0;
};
thread_local Entry entries[64]{};
thread_local unsigned depth=0,overflow=0;
std::uint64_t read64(volatile LONG64* p) noexcept{return InterlockedCompareExchange64(p,0,0);}
bool sameIdentity(const CheckpointLoadWorkerFrame& a,const CheckpointLoadWorkerFrame& b) noexcept {
    return a.slot==b.slot&&a.thread_id==b.thread_id&&a.call_id==b.call_id&&a.caller_entry_rsp==b.caller_entry_rsp&&
        a.reserved_28==b.reserved_28&&a.reserved_58==b.reserved_58&&!memcmp(a.args,b.args,sizeof a.args);
}
Entry* match(Adapter* a,const CheckpointLoadWorkerFrame* f) noexcept {
    if(!depth||entries[depth-1].adapter!=a||entries[depth-1].physical!=f)return nullptr;
    return &entries[depth-1];
}
const void* logical(const Entry& e) noexcept {return e.initial.slot<4?static_cast<const void*>(&e.dispatch):static_cast<const void*>(&e.worker);}
bool unchanged(const Entry& e) noexcept{return !memcmp(logical(e),&e.expected,sizeof e.expected);}
void copy(Entry& e,const CheckpointLoadWorkerFrame* f) noexcept {
    e.expected=*f;if(f->slot>=4)e.expected.slot-=4;
    if(f->slot<4)memcpy(&e.dispatch,&e.expected,sizeof e.dispatch);else e.worker=e.expected;
}
static_assert(sizeof(CheckpointPushFrame)==sizeof(CheckpointLoadWorkerFrame));
static_assert(offsetof(CheckpointPushFrame,slot)==offsetof(CheckpointLoadWorkerFrame,slot));
static_assert(offsetof(CheckpointPushFrame,call_id)==offsetof(CheckpointLoadWorkerFrame,call_id));
}
bool Adapter::Initialize(const Config& c) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    bool valid=c.generation!=0;
    for(unsigned i=0;i<4;i++)if((c.dispatchBefore[i]||c.dispatchAfter[i])&&!c.dispatchFinally[i])valid=false;
    for(unsigned i=0;i<2;i++)if((c.workerBefore[i]||c.workerAfter[i])&&!c.workerFinally[i])valid=false;
    if(!valid){InterlockedExchange(&once_,-1);return false;}
    static const unsigned anchor=0x4C4F4731;HMODULE module=nullptr;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
       reinterpret_cast<LPCWSTR>(&anchor),&module)){InterlockedExchange(&once_,-1);return false;}
    config_=c;pinned_=true;InterlockedExchange(&once_,2);return true;
}
checkpoint_persistent_route::Generation Adapter::RouteGeneration() noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return {};
    return {config_.generation,Before,After,Finally,this};
}
void Adapter::Snapshot(Report& r) noexcept {
    r={};if(InterlockedCompareExchange(&once_,0,0)!=2)return;
    r.generation=config_.generation;r.before=read64(&before_);r.after=read64(&after_);r.finally=read64(&finally_);
    r.active=read64(&active_);r.faults=read64(&faults_);r.claims=read64(&claims_);r.rejectedClaims=read64(&rejectedClaims_);
    r.initialized=1;r.pinned=pinned_?1:0;
}
void Adapter::Before(const CheckpointLoadWorkerFrame* f,void* p){
    auto* a=static_cast<Adapter*>(p);if(!a)return;
    if(InterlockedCompareExchange(&a->once_,0,0)!=2){InterlockedIncrement64(&a->faults_);return;}
    if(overflow||depth==64){++overflow;InterlockedIncrement64(&a->faults_);return;}
    if(!f||f->slot>=6||f->thread_id!=GetCurrentThreadId()||!f->call_id){InterlockedIncrement64(&a->faults_);return;}
    unsigned workerDepth=0;for(unsigned i=0;i<depth;i++)if(entries[i].initial.slot>=4)++workerDepth;
    auto& e=entries[depth++];e={};e.adapter=a;e.physical=f;e.initial=*f;e.generation=a->config_.generation;
    e.logicalWorkerDepth=workerDepth+(f->slot>=4?1u:0u);e.stage=static_cast<unsigned>(CheckpointLoadWorkerStage::Before);copy(e,f);
    InterlockedIncrement64(&a->before_);InterlockedIncrement64(&a->active_);
    if(f->slot<4){auto cb=a->config_.dispatchBefore[f->slot];if(cb)cb(&e.dispatch,a->config_.dispatchContexts[f->slot]);}
    else {auto cb=a->config_.workerBefore[f->slot-4];if(cb)cb(&e.worker,a->config_.workerContexts[f->slot-4]);}
    if(!unchanged(e))InterlockedIncrement64(&a->faults_);
    e.stage=static_cast<unsigned>(CheckpointLoadWorkerStage::Native);
}
void Adapter::After(const CheckpointLoadWorkerFrame* f,void* p){
    auto* a=static_cast<Adapter*>(p);if(!a||overflow)return;
    auto* e=match(a,f);
    if(!e||e->stage!=static_cast<unsigned>(CheckpointLoadWorkerStage::Native)||!sameIdentity(*f,e->initial)){
        InterlockedIncrement64(&a->faults_);return;
    }
    if(!unchanged(*e))InterlockedIncrement64(&a->faults_);
    copy(*e,f);e->stage=static_cast<unsigned>(CheckpointLoadWorkerStage::After);InterlockedIncrement64(&a->after_);
    if(f->slot<4){auto cb=a->config_.dispatchAfter[f->slot];if(cb)cb(&e->dispatch,a->config_.dispatchContexts[f->slot]);}
    else {auto cb=a->config_.workerAfter[f->slot-4];if(cb)cb(&e->worker,a->config_.workerContexts[f->slot-4]);}
    if(!unchanged(*e))InterlockedIncrement64(&a->faults_);
    e->stage=static_cast<unsigned>(CheckpointLoadWorkerStage::Done);
}
void Adapter::Finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){
    auto* a=static_cast<Adapter*>(p);if(!a)return;
    if(overflow){--overflow;return;}
    auto* e=match(a,f);if(!e){InterlockedIncrement64(&a->faults_);return;}
    __try {
        InterlockedIncrement64(&a->finally_);
        if(!x||!sameIdentity(*f,e->initial)){InterlockedIncrement64(&a->faults_);__leave;}
        if(!unchanged(*e))InterlockedIncrement64(&a->faults_);
        copy(*e,f);e->stage=static_cast<unsigned>(CheckpointLoadWorkerStage::Finally);
        auto exit=*x;if(f->slot>=4)exit.depth=e->logicalWorkerDepth;
        if(f->slot<4){auto cb=a->config_.dispatchFinally[f->slot];if(cb)cb(&e->dispatch,&exit,a->config_.dispatchContexts[f->slot]);}
        else {auto cb=a->config_.workerFinally[f->slot-4];if(cb)cb(&e->worker,&exit,a->config_.workerContexts[f->slot-4]);}
        if(!unchanged(*e))InterlockedIncrement64(&a->faults_);
    }__finally {
        e->adapter=nullptr;e->physical=nullptr;--depth;InterlockedDecrement64(&a->active_);
    }
}
bool Claim(const CheckpointLoadWorkerFrame* f,std::uint64_t token) noexcept {
    if(!depth||overflow)return false;auto& e=entries[depth-1];auto* a=e.adapter;
    bool valid=e.initial.slot>=4&&e.stage==static_cast<unsigned>(CheckpointLoadWorkerStage::Before)&&
        f==&e.worker&&token&&!e.claimedToken&&e.initial.thread_id==GetCurrentThreadId()&&unchanged(e)&&sameIdentity(*e.physical,e.initial);
    if(valid)valid=CheckpointPersistentClaim(e.physical,token)==1;
    if(valid){
        CheckpointLoadWorkerOwner owner{};
        valid=CheckpointPersistentCurrentOwner(&owner)==1&&owner.token==token&&owner.call_id==e.initial.call_id&&
            owner.slot==e.initial.slot&&owner.thread_id==e.initial.thread_id;
        if(valid){e.claimedToken=token;e.nativeOwnerDepth=owner.owner_depth;InterlockedIncrement64(&a->claims_);}
        else InterlockedIncrement64(&a->faults_); // Native claim exists; never retry or undo it.
    }
    if(!valid)InterlockedIncrement64(&a->rejectedClaims_);return valid;
}
bool CurrentOwner(CheckpointLoadWorkerOwner* out) noexcept {
    if(!out)return false;*out={};if(!depth||overflow)return false;
    auto& current=entries[depth-1];CheckpointLoadWorkerOwner native{};
    if(!CheckpointPersistentCurrentOwner(&native)||native.thread_id!=GetCurrentThreadId())return false;
    for(unsigned i=depth;i;i--){auto& e=entries[i-1];
        if(e.initial.slot==native.slot&&e.initial.call_id==native.call_id&&e.initial.thread_id==native.thread_id){
            if(e.adapter!=current.adapter||e.generation!=current.generation||e.initial.slot<4||
               !e.claimedToken||e.claimedToken!=native.token||e.nativeOwnerDepth!=native.owner_depth||
               !sameIdentity(*e.physical,e.initial))return false;
            *out=native;out->slot-=4;out->owner_depth=e.logicalWorkerDepth;out->current_depth=current.logicalWorkerDepth;return true;
        }
    }
    return false;
}
bool CurrentMapping(Mapping* out) noexcept {
    if(!out)return false;*out={};if(!depth||overflow)return false;const auto& e=entries[depth-1];
    *out={e.generation,e.initial.call_id,e.initial.slot,e.initial.slot<4?e.initial.slot:e.initial.slot-4,
          e.initial.thread_id,e.stage,e.logicalWorkerDepth,e.physical,logical(e)};return true;
}
}
