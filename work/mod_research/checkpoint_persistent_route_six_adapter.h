#pragma once
#include "checkpoint_persistent_bridge.h"
#include "checkpoint_persistent_route_worker_adapter.h"
namespace checkpoint_persistent_route {
// Same lease engine, new six-slot bridge ABI/TLS. Does not translate old slot
// indices or old Claim/CurrentOwner calls; existing game observers need adapters.
class SixAdapter {
public:
    bool Initialize(Router& r) noexcept {return engine_.Initialize(r);}
    CheckpointPersistentBridgeConfig Configuration(void* original) noexcept;
    std::uint64_t Faults() noexcept {return engine_.Faults();}
    static bool Claim(const CheckpointLoadWorkerFrame* f,std::uint64_t token) noexcept;
    static bool CurrentOwner(CheckpointLoadWorkerOwner& o) noexcept;
private:
    WorkerAdapter engine_{};
    static void Before(const CheckpointLoadWorkerFrame*,void*);
    static void After(const CheckpointLoadWorkerFrame*,void*);
    static void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
};
}
