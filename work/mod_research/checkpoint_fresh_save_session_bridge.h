#pragma once
#include "checkpoint_load_worker_bridge.h"
// Dedicated immutable two-slot bank; same audited integer ABI, exact native
// call and FINALLY semantics. No suppression/skip entry exists.
extern "C" {
int CheckpointFreshSaveSessionBridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int CheckpointFreshSaveSessionBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t CheckpointFreshSaveSessionBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointFreshSaveSessionBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int CheckpointFreshSaveSessionClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int CheckpointFreshSaveSessionCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
