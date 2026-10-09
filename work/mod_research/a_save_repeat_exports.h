#pragma once
#include "a_save_runtime_exports.h"
// Additive ABI: frozen operations 1..8 and their layouts remain unchanged.
namespace a_save_repeat_wire {
namespace w=a_save_runtime_wire;
constexpr auto NextOp=static_cast<w::Op>(9),SnapshotOp=static_cast<w::Op>(10);
#pragma pack(push,1)
struct NextData {
 std::uint64_t previousGeneration;unsigned char previousSha256[32];
 std::uint64_t generation,period,epoch;unsigned char inputDigest[32];
 std::uint16_t year;std::uint8_t month,day;
};
struct Next {w::Header header;unsigned char nonce[32];NextData request;};
struct Snapshot {
 w::Header header;unsigned char nonce[32];
 std::uint32_t state,error,hostThread,requested,stopped;
 std::uint64_t activeGeneration,retiredSerial,retiredCount;
 NextData request;
 std::uint32_t previousArtifactMatched,nativeDateMatched,bLoadedProven,simulationEnabled;
 std::uint32_t lease,frame,drainPending;
};
#pragma pack(pop)
static_assert(sizeof(NextData)==100&&sizeof(Next)==152&&sizeof(Snapshot)==224);
}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRequestNext(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRepeatSnapshot(void*) noexcept;
