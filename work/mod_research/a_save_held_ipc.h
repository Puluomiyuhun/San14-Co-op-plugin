#pragma once
#include "a_save_user_owner.h"
#include "checkpoint_fresh_save_packet.h"

// Explicit successor to frozen a_save_ipc. Same wire ABI, different local backend.
// Local retained-owner transport. No process discovery, game installation,
// addresses, directories, input unlock, game advance or Ready command.
namespace a_save_held_ipc {
constexpr std::uint32_t Magic=0x31465341;
constexpr std::uint16_t Version=1;
enum class Op:std::uint16_t {Snapshot=1,Submit=2,Copy=3,Stop=4};
enum class Status:std::uint32_t {Ok,BadRequest,Unauthorized,Binding,Sequence,Consumed,OperationFailed,NotReady,Stopped};
#pragma pack(push,1)
struct WireSave {
 std::uint64_t generation,room_epoch,period,cut;unsigned char room_id[32];
 std::uint16_t year,ruler;std::uint8_t month,day,force,reserved;char filename[16];
};
struct Request {std::uint32_t magic;std::uint16_t version,opcode;std::uint64_t sequence;unsigned char secret[32],binding[32];WireSave save;};
struct Header {std::uint32_t magic;std::uint16_t version,opcode;std::uint64_t sequence;std::uint32_t status,payload_size;unsigned char binding[32];};
struct Snapshot {
 std::uint32_t owner_error,initialized,armed,stopped,save_status,save_error,completed_requests,binds,queues,user_subset_held;
 std::uint64_t generation,active_scopes;std::uint32_t capabilities;
};
#pragma pack(pop)
static_assert(sizeof(WireSave)==88&&sizeof(Request)==168&&sizeof(Header)==56&&sizeof(Snapshot)==60);
struct Config {
 a_save_user_owner::Owner*owner=nullptr;const wchar_t*pipeName=nullptr;
 DWORD clientPid=0,idleTimeoutMs=30000;
 unsigned char secret[32]{},room_id[32]{};std::uint64_t room_epoch=0;
 // Required production admission port. This must validate local owner/world
 // lifetime and real write exclusion; a peer's boolean is not that evidence.
 // It must not reenter this Server or change the owner's native sources.
 bool(*permit)(void*,const checkpoint_fresh_save::Request&,const unsigned char binding[32])noexcept=nullptr;
 void*permitContext=nullptr;
 // Trusted host execution ports, required together. The wire peer never supplies
 // these addresses. A production host must marshal them onto its native owner
 // thread and preserve the pause through actual completion. No automatic retry.
 bool(*submit)(void*,const checkpoint_fresh_save::Request&,const unsigned char binding[32])noexcept=nullptr;
 bool(*copy)(void*,std::uint64_t,checkpoint_fresh_save::Artifact&)noexcept=nullptr;
 void*executionContext=nullptr;
};
struct Diagnostics {bool opened=false,running=false,closed=false,stopped=false;DWORD osError=0;std::uint64_t requests=0,submits=0,copies=0,lastSequence=0;};
class Server final {
public:
 Server()=default;~Server();Server(const Server&)=delete;Server&operator=(const Server&)=delete;
 bool Open(const Config&)noexcept;
 // Exactly one authenticated connection. Loss ends admission permanently;
 // committed saves keep their Owner callbacks. Caller joins Run before delete.
 bool Run(HANDLE shutdown)noexcept;
 void Inspect(Diagnostics&)noexcept;
private:
 struct Record {WireSave request{};unsigned char binding[32]{};};
 Config c_{};wchar_t name_[180]{};Record records_[2]{};unsigned count_=0;
 HANDLE pipe_=INVALID_HANDLE_VALUE,event_=nullptr,client_=nullptr;
 volatile LONG opened_=0,run_=0;SRWLOCK lock_=SRWLOCK_INIT;Diagnostics d_{};
 std::uint64_t sequence_=0;bool terminal_=false;ULONGLONG terminalUntil_=0;
 bool io(bool,void*,DWORD,HANDLE)noexcept;
 bool complete(OVERLAPPED&,DWORD&,HANDLE,ULONGLONG)noexcept;
 bool connected(HANDLE)noexcept;bool clientAlive()noexcept;bool available(HANDLE)noexcept;
 void stop(DWORD error=0)noexcept;Snapshot snapshot()noexcept;
 Status process(const Request&,std::vector<unsigned char>&,Snapshot&,HANDLE)noexcept;
};
}
