#pragma once
#include "checkpoint_load_worker_bridge.h"
extern "C" {
int BReloadTitle520BridgeConfigure(unsigned,const CheckpointLoadWorkerBridgeConfig*) noexcept;
int BReloadTitle520BridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t BReloadTitle520Bridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t BReloadTitle520Bridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int BReloadTitle520Claim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int BReloadTitle520CurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
