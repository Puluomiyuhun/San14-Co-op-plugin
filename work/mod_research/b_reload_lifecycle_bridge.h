#pragma once
#include "checkpoint_load_worker_bridge.h"
extern "C" {
int BReloadLifecycleBridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int BReloadLifecycleBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t BReloadLifecycleBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t BReloadLifecycleBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int BReloadLifecycleClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int BReloadLifecycleCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
