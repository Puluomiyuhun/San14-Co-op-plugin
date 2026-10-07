#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include "checkpoint_load_worker_bridge.h"

// Offline building block. Not an installer, native scheduler fence, ownership
// transfer proof, admission authority, or permission to publish another load.
// The router, every context and callback must remain resident until exit.
namespace checkpoint_persistent_route {
struct Generation {
    std::uint64_t id=0;
    CheckpointLoadWorkerObserver before=nullptr,after=nullptr;
    CheckpointLoadWorkerFinally finally=nullptr;
    void* context=nullptr;
};
struct Config { Generation initial{}; bool allowOfflineTransitions=false; };
struct Report {
    std::uint64_t current=0,entered=0,released=0,active=0,rejected=0,transitions=0;
    unsigned generations=0,initialized=0,pinned=0;
    bool nativeSchedulerFence=false,productionAdmission=false;
};
class Router;
// Caller creates/acquires a fresh Lease on one thread only. Concurrent first
// Acquire calls using the same Lease (including across routers) are prohibited.
// After Acquire returns, an external reference must be published with normal
// thread synchronization. Router/thread identity stays immutable thereafter;
// foreign Release/parent requests reject before reading mutable active state.
// Selected() is for the acquiring thread, not an asynchronous diagnostic API.
class Lease {
public:
    Lease() noexcept=default;
    Lease(const Lease&)=delete; Lease& operator=(const Lease&)=delete;
    const Generation* Selected() const noexcept {return active_?selected_:nullptr;}
private:
    friend class Router;
    Router* router_=nullptr; const Generation* selected_=nullptr;
    DWORD thread_=0; std::uint64_t ticket_=0; bool active_=false,used_=false;
};
class Router {
public:
    Router() noexcept=default;
    Router(const Router&)=delete; Router& operator=(const Router&)=delete;
    bool Initialize(const Config&) noexcept;
    // Root entries select the current generation atomically with acquiring their
    // lease. Nested calls may inherit an active same-thread ancestor. A delayed
    // old native task entering as a new root WILL select the new generation.
    bool Acquire(Lease&,const Lease* ancestor=nullptr) noexcept;
    bool Release(Lease&) noexcept;
    // Data-core exercise only. Default closed. Does not inspect native work
    // queues or certify that old work cannot enter after this transition.
    bool PublishForOfflineExercise(std::uint64_t expected,const Generation&) noexcept;
    void Snapshot(Report&) noexcept;
private:
    SRWLOCK lock_=SRWLOCK_INIT;
    volatile LONG once_=0;
    Generation generations_[32]{};
    unsigned count_=0; bool offline_=false,pinned_=false;
    std::uint64_t entered_=0,released_=0,active_=0,rejected_=0,transitions_=0;
};
}
