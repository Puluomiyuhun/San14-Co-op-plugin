#pragma once
#include "checkpoint_load_worker_bridge.h"
// One immutable source bank. Game always forwards; global UI and panel may be
// suppressed. Suppressed scopes receive neither native AFTER nor claimable BEFORE.
// The separate mid-User tail bridge executes a declared body transformation.
struct ASaveActionBridgeConfig : CheckpointLoadWorkerBridgeConfig {
 bool(*select)(CheckpointLoadWorkerFrame*,void*) noexcept=nullptr;
};
extern "C" {
int ASaveActionBridgeConfigure(unsigned,const ASaveActionBridgeConfig*) noexcept;
int ASaveActionBridgeSnapshot(unsigned,CheckpointLoadWorkerBridgeStats*) noexcept;
std::uint64_t ASaveActionBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t ASaveActionBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t ASaveActionBridge2(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int ASaveActionClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int ASaveActionCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
