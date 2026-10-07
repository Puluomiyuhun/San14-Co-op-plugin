#pragma once
#include "checkpoint_load_worker_bridge.h"
// A single immutable physical owner. The pre-call selector can suppress global UI
// only; a suppressed scope never gets a native AFTER or a claimable Before.
struct ASaveInputBridgeConfig : CheckpointLoadWorkerBridgeConfig {
 bool(*select)(CheckpointLoadWorkerFrame*,void*) noexcept=nullptr;
};
extern "C" {
int ASaveInputBridgeConfigure(unsigned,const ASaveInputBridgeConfig*) noexcept;
int ASaveInputBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t ASaveInputBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t ASaveInputBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int ASaveInputClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int ASaveInputCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
