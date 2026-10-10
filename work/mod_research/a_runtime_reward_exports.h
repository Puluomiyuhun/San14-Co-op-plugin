#pragma once
#include "a_save_runtime_exports.h"
// Additive local ABI: retained Runtime and binding only, no addresses/callbacks.
namespace a_runtime_reward_wire {
namespace base=a_save_runtime_wire;
constexpr base::Op ConfigureOp=static_cast<base::Op>(11),SubmitOp=static_cast<base::Op>(12),SnapshotOp=static_cast<base::Op>(13);
#pragma pack(push,1)
struct Context {std::uint32_t pid;std::uint64_t birth;base::NativeBinding native;std::uint64_t period,epoch;unsigned char inputDigest[32];};
struct Actor {std::uint8_t force,district;std::uint16_t ruler;};
struct Configure {base::Header header;unsigned char nonce[32];Context context;Actor actors[2];};
struct Command {unsigned char nonce[32];std::uint16_t year;std::uint8_t month,day,viewer,actor;std::uint16_t ruler,city;std::uint8_t district,reserved;std::uint32_t count,officers[16];std::uint64_t expiresAtTick;};
struct Submit {base::Header header;unsigned char nonce[32];Context context;std::uint64_t sequence;Command command;};
struct Snapshot {base::Header header;unsigned char nonce[32];Context context;std::uint64_t sequence,submitted,completed;
 std::uint32_t state,error,configured,queued,active,readyResealed,uncertain,stopped,hostThread;
 std::uint32_t ownerError,replayState,replayError,nativeReturned,argsReleased,ownedSlotCleared,ctorCalls,appendCalls,dtorCalls,captureCalls,executeCalls;
 std::uint64_t finallyCalls,abnormalCalls;unsigned char commandSha256[32],semanticSha256[32];
 std::uint32_t fullInputHold,worldFenceProven,nativeGameplayEnabled;};
#pragma pack(pop)
static_assert(sizeof(Context)==100&&sizeof(Configure)==160&&sizeof(Command)==120&&sizeof(Submit)==280&&sizeof(Snapshot)==348);
}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRewardConfigure(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRewardSubmit(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRewardSnapshot(void*) noexcept;
