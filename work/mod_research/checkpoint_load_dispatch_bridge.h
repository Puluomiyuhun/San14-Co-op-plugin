#pragma once
#include "checkpoint_push_bridge.h"
// Four immutable dispatch slots; the frame/observer ABI remains identical to
// the frozen two-slot bridge. Originals are never suppressed. No installer.
using CheckpointLoadDispatchBridgeConfig=CheckpointPushBridgeConfig;
using CheckpointLoadDispatchBridgeStats=CheckpointPushBridgeStats;
extern "C" {
int CheckpointLoadDispatchBridgeConfigure(unsigned,const CheckpointLoadDispatchBridgeConfig*) noexcept;
int CheckpointLoadDispatchBridgeSnapshot(unsigned,CheckpointLoadDispatchBridgeStats*) noexcept;
std::uint64_t CheckpointLoadDispatchBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointLoadDispatchBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointLoadDispatchBridge2(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointLoadDispatchBridge3(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
}
