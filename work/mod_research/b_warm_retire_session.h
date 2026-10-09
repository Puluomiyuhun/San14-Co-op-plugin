#pragma once
#include "checkpoint_forward_planning_observer_v2.h"
// Explicit successor to the immutable six physical warm bridges. One bank per
// resident DLL; Bind is setup only, never completion authorization. No reset.
namespace b_warm_retire {
struct Report {
    unsigned version=1,size=sizeof(Report),bound=0,sealed=0,restored=0,restoreFailed=0;
    unsigned eligibleChecks=0,completionSeen=0,refusalStage=0; std::uint64_t attempt=0,userCall=0,identityCall=0,loadCall=0;
    DWORD thread=0;
};
bool Bind(checkpoint_forward_native_session::Session&,checkpoint_forward_planning_observer_v2::Observer&) noexcept;
bool Sealed(const checkpoint_forward_native_session::Session*) noexcept;
void Snapshot(Report&) noexcept;
}

extern "C" __declspec(dllexport) DWORD WINAPI GetBWarmRetireReport(void*);
