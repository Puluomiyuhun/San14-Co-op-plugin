#pragma once
#include "checkpoint_load_worker_bridge.h"
extern "C" {
int BReloadTitleBridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int BReloadTitleBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t BReloadTitleBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t BReloadTitleBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int BReloadTitleClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int BReloadTitleCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
