#pragma once
#include "a_save_runtime_exports.h"
// Addresses belong to the actual frozen bridge Slot banks, not copied counters.
bool ASaveRuntimeUserCounters(a_save_runtime_wire::Counter*)noexcept;
bool ASaveRuntimeGateCounters(a_save_runtime_wire::Counter*)noexcept;
bool ASaveRuntimeParentCounters(a_save_runtime_wire::Counter*)noexcept;
std::uintptr_t ASaveRuntimePublishHostCacheAddress()noexcept;
bool ASaveRuntimePublishEvidence(a_save_runtime_wire::Counter out[7],std::uint32_t*valid,
 std::uint32_t*lease,std::uint32_t*frame,std::uint32_t*state,std::uint64_t*sequence)noexcept;
