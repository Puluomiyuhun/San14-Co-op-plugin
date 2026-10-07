#include "checkpoint_persistent_route_worker_adapter.h"
#include <new>
namespace checkpoint_persistent_route {
namespace {
struct Entry {WorkerAdapter* adapter=nullptr;const CheckpointLoadWorkerFrame* frame=nullptr;Lease lease{};bool after=false;};
// Bounded, allocation-free per-thread stack. Overflows keep forwarding native
// originals but provide no generation callbacks and mark the receipt failed.
thread_local Entry entries[64];thread_local unsigned depth=0,overflow=0;
Entry* match(WorkerAdapter* a,const CheckpointLoadWorkerFrame* f) noexcept {
    if(!depth||entries[depth-1].adapter!=a||entries[depth-1].frame!=f)return nullptr;
    return &entries[depth-1];
}
}
bool WorkerAdapter::Initialize(Router& r) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    Report report{};r.Snapshot(report);if(!report.initialized){InterlockedExchange(&once_,-1);return false;}
    router_=&r;InterlockedExchange(&once_,2);return true;
}
std::uint64_t WorkerAdapter::Faults() noexcept{return InterlockedCompareExchange64(&faults_,0,0);}
void WorkerAdapter::Before(const CheckpointLoadWorkerFrame* f,void* p){
    auto* a=static_cast<WorkerAdapter*>(p);
    if(!a||!f||!a->router_)return;
    if(depth==64||overflow){++overflow;a->Fault();return;}
    const Lease* parent=nullptr;
    for(unsigned i=depth;i;i--)if(entries[i-1].adapter->Route()==a->router_){parent=&entries[i-1].lease;break;}
    auto& e=entries[depth++];e.adapter=a;e.frame=f;e.after=false;
    e.lease.~Lease();new(&e.lease) Lease;
    if(!a->router_->Acquire(e.lease,parent)){a->Fault();return;}
    const auto* g=e.lease.Selected();if(g->before)g->before(f,g->context);
}
void WorkerAdapter::After(const CheckpointLoadWorkerFrame* f,void* p){
    auto* a=static_cast<WorkerAdapter*>(p);if(!a)return;
    if(overflow)return;
    auto* e=match(a,f);if(!e||e->after){a->Fault();return;}
    e->after=true;const auto* g=e->lease.Selected();if(g&&g->after)g->after(f,g->context);
}
void WorkerAdapter::Finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){
    auto* a=static_cast<WorkerAdapter*>(p);if(!a)return;
    if(overflow){--overflow;return;}
    auto* e=match(a,f);if(!e){a->Fault();return;}
    const auto* g=e->lease.Selected();
    __try {if(g&&g->finally)g->finally(f,x,g->context);}
    __finally {
        if(g&&!a->router_->Release(e->lease))a->Fault();
        e->adapter=nullptr;e->frame=nullptr;--depth;
    }
}
}
