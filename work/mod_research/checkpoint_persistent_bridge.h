#pragma once
#include "checkpoint_load_worker_bridge.h"
// Six immutable physical entries: User/Menu/Game/Load/Callable/FileRead.
// All entries have paired FINALLY on normal and SEH/C++ exits. Same restricted
// four-integer Win64 ABI as the proven worker bridge; NOT an installer.
// Frame.slot is the physical 0..5 slot. Old worker observers expecting 0/1 and
// CheckpointLoadWorkerClaim TLS MUST be explicitly adapted before integration.
// A configured BEFORE/AFTER requires FINALLY; invalid config publishes nothing.
using CheckpointPersistentBridgeConfig=CheckpointLoadWorkerBridgeConfig;
using CheckpointPersistentBridgeStats=CheckpointLoadWorkerBridgeStats;
constexpr unsigned CheckpointPersistentBridgeSlots=6;
extern "C" {
int CheckpointPersistentBridgeConfigure(unsigned,const CheckpointPersistentBridgeConfig*) noexcept;
int CheckpointPersistentBridgeSnapshot(unsigned,CheckpointPersistentBridgeStats*) noexcept;
std::uint64_t CheckpointPersistentBridge0(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointPersistentBridge1(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointPersistentBridge2(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointPersistentBridge3(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointPersistentBridge4(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
std::uint64_t CheckpointPersistentBridge5(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
int CheckpointPersistentClaim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept;
int CheckpointPersistentCurrentOwner(CheckpointLoadWorkerOwner*) noexcept;
}
// Module/config/context/originals stay alive until process exit. No reset,
// reconfigure, unload, hook publication, scheduler fence or load authorization.
