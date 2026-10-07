#pragma once
#include "checkpoint_load_worker_bridge.h"
// A single immutable physical owner. The pre-call selector can suppress User
// only; a suppressed scope never gets a native AFTER or a claimable Before.
struct ASaveUserOwnerBridgeConfig : CheckpointLoadWorkerBridgeConfig {
 bool(*select)(CheckpointLoadWorkerFrame*,void*) noexcept=nullptr;
};
extern "C" {
int ASaveUserOwnerBridgeConfigure(unsigned,const ASaveUserOwnerBridgeConfig*) noexcept;
int ASaveUserOwnerBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t ASaveUserOwnerBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t ASaveUserOwnerBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int ASaveUserOwnerClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int ASaveUserOwnerCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
