#pragma once
#include "checkpoint_load_worker_bridge.h"
extern "C" {
int BReloadRootActivationBridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int BReloadRootActivationBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t BReloadRootActivationBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t BReloadRootActivationBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int BReloadRootActivationClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int BReloadRootActivationCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
