#pragma once
#include "checkpoint_persistent_route_core.h"
namespace checkpoint_persistent_route {
// Configure these three callbacks on the frozen worker bridge once. That bridge
// guarantees FINALLY on normal/abnormal exit. The dispatch bridge has no such
// callback and CANNOT use this adapter. No hook installation is performed here.
class WorkerAdapter {
public:
    bool Initialize(Router&) noexcept;
    static void Before(const CheckpointLoadWorkerFrame*,void*);
    static void After(const CheckpointLoadWorkerFrame*,void*);
    static void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
    std::uint64_t Faults() noexcept;
    Router* Route() const noexcept{return router_;}
    void Fault() noexcept {InterlockedIncrement64(&faults_);}
private:
    volatile LONG once_=0; Router* router_=nullptr; volatile LONG64 faults_=0;
};
}
