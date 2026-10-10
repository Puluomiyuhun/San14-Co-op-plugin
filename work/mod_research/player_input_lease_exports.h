#pragma once
#include <windows.h>
#include <cstdint>
namespace player_input_lease_wire {
constexpr std::uint64_t Magic=0x31455341454C4950ull;
enum class Op:std::uint32_t {Initialize=1,Request,Acquire,Complete,Snapshot,Unknown};
#pragma pack(push,1)
struct Header {std::uint64_t magic;std::uint32_t version,size,op,result;};
struct Binding {unsigned char room[16],attachment[16],epoch[16];std::uint64_t period;std::uint32_t seat;};
struct Config {Header header;unsigned char nonce[32];std::uint32_t pid;std::uint64_t birth,base,window;Binding binding;};
struct Request {Header header;unsigned char nonce[32];Binding binding;std::uint32_t phase,localReady;std::uint64_t revision;};
struct Lease {Header header;unsigned char nonce[32];Binding binding;std::uint64_t revision,sequence,lease;};
struct Snapshot {Header header;unsigned char nonce[32];std::uint32_t pid;std::uint64_t birth,window;std::uint32_t windowThread;Binding binding;
 std::uint32_t phase,localReady,error,initialized,installed,pending,acknowledged,held,uncertain,destroyed;
 std::uint64_t revision,acknowledgedRevision,active,finally,leaseId,leaseSequence,leaseRevision,leasesIssued,leasesCompleted,suppressed,auditedForwarded,lifecycleForwarded,uncoveredForwarded,unclassifiedForwarded,publicationWrites;
 std::uint32_t remoteMessagesAllowed,remoteExecutionPolicyOpen,localCommandPolicyOpen,allInputHeld,osQueueDrained,nativeReceiptVerified,controlMessage;};
#pragma pack(pop)
static_assert(sizeof(Header)==24&&sizeof(Binding)==60&&sizeof(Config)==144&&sizeof(Request)==132&&sizeof(Lease)==140&&sizeof(Snapshot)==328);
}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputInitialize(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputRequest(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputAcquire(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputComplete(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputUnknown(void*)noexcept;
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputSnapshot(void*)noexcept;
