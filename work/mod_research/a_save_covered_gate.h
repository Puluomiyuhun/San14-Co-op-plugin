#pragma once
#include <cstdint>
#include <cstddef>
#pragma pack(push,1)
struct ASaveCoveredGateFailure {
 std::uint32_t size,version;
 std::uint64_t stackCount,queueCount,current,top,saveState,saveGeneration,reservedGeneration;
 std::uint32_t saveStatus,saveStopped,saveError,thread;
 // Written last: 1 frame/sourcecaller, 2 source bytes, 3 claim, 4 layout.
 volatile std::uint32_t stage;
};
#pragma pack(pop)
static_assert(offsetof(ASaveCoveredGateFailure,stage)%4==0);
extern "C" __declspec(dllexport) ASaveCoveredGateFailure ASaveCoveredGateFirstFailure;
