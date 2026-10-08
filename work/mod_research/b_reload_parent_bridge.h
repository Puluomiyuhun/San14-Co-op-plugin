#pragma once
#include "checkpoint_load_worker_bridge.h"
extern "C" {
int BReloadParentBridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int BReloadParentBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t BReloadParentBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t BReloadParentBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int BReloadParentClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int BReloadParentCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
