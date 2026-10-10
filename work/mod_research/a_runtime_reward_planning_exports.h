#pragma once
#include "a_runtime_reward_exports.h"
namespace a_runtime_reward_planning_wire {
namespace base=a_save_runtime_wire;
constexpr base::Op OpenOp=static_cast<base::Op>(14),SnapshotOp=static_cast<base::Op>(15);
#pragma pack(push,1)
struct Open {base::Header header;unsigned char nonce[32];a_runtime_reward_wire::Context context;std::uint64_t generation;unsigned char artifactSha256[32];};
struct Snapshot {base::Header header;unsigned char nonce[32];a_runtime_reward_wire::Context context;std::uint64_t generation;unsigned char artifactSha256[32];std::uint32_t state,error,hostThread,opened,receiptMatched,stopped;};
#pragma pack(pop)
static_assert(sizeof(Open)==192&&sizeof(Snapshot)==216);
}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeOpenPlanning(void*)noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimePlanningSnapshot(void*)noexcept;
