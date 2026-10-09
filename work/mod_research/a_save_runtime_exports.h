#pragma once
#include <windows.h>
#include <cstdint>
// Local bootstrap ABI. No entry point is safe to invoke while other target
// threads are debugger-suspended. Every object and code module is retained.
namespace a_save_runtime_wire {
constexpr std::uint32_t Magic=0x31585241,Version=1;
enum class Op:std::uint32_t {Prepare=1,Plans,ArmOwner,ArmPublishedSources,Snapshot,Stop,StartServer,ServerStatus};
enum class Result:std::uint32_t {Ok,BadEnvelope,BadOperation,Busy,Used,NotPrepared,Rejected,Exception,Stopped,Allocation,NotReady};
#pragma pack(push,1)
struct Header {std::uint32_t magic,version,size,operation,result;};
struct NativeBinding {unsigned char attempt[16],attachment[16];std::uint64_t ownerGeneration;};
struct Module {std::uint64_t base;std::uint32_t sizeOfImage,timestamp;wchar_t path[1024];std::uint64_t fileSize;unsigned char fileSha256[32],headerSha256[32];};
struct Endpoint {std::uint64_t address;std::uint32_t moduleIndex;unsigned char first32[32];};
struct Storage {std::uint32_t pid;std::uint64_t birth,attempt,generation,base;unsigned char id[32],gameSha256[32];
 Module modules[3];std::uint32_t moduleCount;Endpoint contextInit,exists,size,read;
 std::uint64_t storage,vtable,counter;std::uint32_t vtableModuleIndex,counterModuleIndex;std::uint64_t cachedGeneration;unsigned char contextCode[0x65];};
struct Prepare {Header header;unsigned char nonce[32];std::uint32_t pid;std::uint64_t birth,base;unsigned char roomId[32];std::uint64_t nativeRoomEpoch;
 NativeBinding native;std::uint64_t root,world,cache,states[5];Storage storage;
 std::uint64_t period,epoch;unsigned char roomInputDigest[32];std::uint16_t year,ruler;std::uint8_t month,day,force,reserved;
 wchar_t saveDirectory[512],intentDirectory[512];};
struct Inline {std::uint64_t address,relay;std::uint32_t size,protection;unsigned char before[7],after[7];};
struct Slot {std::uint64_t address,original,hook;std::uint32_t protection;};
struct Counter {std::uint64_t startedAddress,activeAddress,started,active;};
struct HostCache {std::uint64_t sequence;std::uint32_t valid,lease,frame,state;};
struct Plans {Header header;unsigned char nonce[32];std::uint32_t pid;std::uint64_t birth,base,module;
 Inline inlines[3];Slot slots[4];Counter counters[7];};
struct Command {Header header;unsigned char nonce[32];};
struct StartServer {Header header;unsigned char nonce[32];std::uint32_t clientPid,idleTimeoutMs;unsigned char secret[32];wchar_t pipeName[180];};
struct ServerStatus {Header header;unsigned char nonce[32];std::uint32_t started,threadExited,runSucceeded,opened,running,closed,stopped,osError;std::uint64_t requests,submits,copies,lastSequence;};
struct Snapshot {Header header;unsigned char nonce[32];std::uint32_t error,prepared,ownerArmed,sourcesArmed,stopped,ready;
 std::uint32_t ownerError,ownerStopped,saveLane,saveStatus,saveError,binds,queues,phaseMask,workerJoined,originalReturned,fileVerified;
 std::uint64_t saveGeneration,saveActive,ownerActive,gateActive,parentActive,parentBefore,parentAfter,parentFinally;
 std::uint32_t parentError,hostInitialized,hostThread,mailboxStopped,mailboxCount,mailboxStates[2];
 // Filled by an authenticated parent-thread cache successor, never guessed.
 std::uint32_t hostCacheValid,hostLease,hostFrame,hostState;std::uint64_t hostCacheSequence,hostCacheAddress;
 Counter counters[7];std::uint32_t productionPermit,allWritersProven,restoreReady;};
#pragma pack(pop)
static_assert(sizeof(Header)==20&&sizeof(wchar_t)==2&&sizeof(void*)==8);
}
#define A_SAVE_RUNTIME_EXPORT extern "C" __declspec(dllexport) DWORD WINAPI
A_SAVE_RUNTIME_EXPORT ASaveRuntimePrepare(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimePlans(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeArmOwner(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeArmPublishedSources(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeSnapshot(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeStop(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeStartServer(void*) noexcept;
A_SAVE_RUNTIME_EXPORT ASaveRuntimeServerStatus(void*) noexcept;
