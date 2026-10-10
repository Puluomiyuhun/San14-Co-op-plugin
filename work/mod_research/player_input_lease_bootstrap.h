#pragma once
#include "player_input_lease_exports.h"
namespace player_input_lease_bootstrap {
constexpr std::uint64_t Magic=0x31544F4F424C4950ull;
enum class Op:std::uint32_t {Begin=1,Snapshot=2};
enum class State:std::uint32_t {Dormant,Queued,Executing,Complete,Failed,Unknown};
enum class Error:std::uint32_t {None,Config,Identity,Source,Pin,Hook,Post,Timeout,Initialize,Unhook,Exception};
#pragma pack(push,1)
struct Config {player_input_lease_wire::Header header;player_input_lease_wire::Config input;std::uint32_t windowThread,timeoutMs;};
struct Report {
 player_input_lease_wire::Header header;unsigned char nonce[32];
 std::uint32_t pid;std::uint64_t birth,window;std::uint32_t windowThread;
 std::uint32_t state,error,initializeResult,initializeThread,hookInstalled,hookRemoved,modulePinned,uncertain,attempts,callbackClaims,controlMessage,timeoutMs;
 std::uint64_t startTick,deadlineTick,endTick,module;
 std::uint32_t initializeAttempted,initializeSucceeded,callbackActive,callbackFinally;
};
#pragma pack(pop)
static_assert(sizeof(Config)==176&&sizeof(Report)==176);
}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputBootstrapBegin(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputBootstrapSnapshot(void*)noexcept;
