#pragma once
#include "a_runtime_reward_exports.h"
// Independent B User-only owner. No A Save/Gate/Parent is installed.
namespace b_reward_wire {
namespace a=a_runtime_reward_wire;namespace base=a_save_runtime_wire;
enum class Op:unsigned {Configure=1,Submit,Snapshot,Stop,Restore};
#pragma pack(push,1)
struct Configure {base::Header header;unsigned char nonce[32];a::Context context;
 std::uint64_t base,root,world,cache,states[5];
 std::uint16_t year,ruler;std::uint8_t month,day,viewer,reserved;
 a::Actor actors[2];std::uint64_t storageVtable,readOriginal;};
using Command=base::Command;using Submit=a::Submit;
// The A-compatible prefix keeps readyResealed FALSE: B does not own an A Ready.
// Success requires nativeClean and the actual prefix cleanup evidence. Before
// the next load, Stop+Restore and a fresh drained Snapshot are mandatory.
struct Snapshot {a::Snapshot reward;std::uint32_t armed,admissionClosed,nativeClean,restoreVerified,slotRestored;
 std::uint64_t bridgeStarted,bridgeActive,bridgeFinally,bridgeCleanupFaults;};
#pragma pack(pop)
static_assert(sizeof(Configure)==256&&sizeof(Submit)==280&&sizeof(Snapshot)==400);
}
extern "C" __declspec(dllexport) DWORD WINAPI BRewardConfigure(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI BRewardSubmit(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI BRewardSnapshot(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI BRewardStop(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI BRewardRestore(void*)noexcept;
