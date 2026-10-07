#pragma once
#include "checkpoint_guest_native_session.h"

// Windows byte-pipe transport for an already initialized, process-lifetime
// Session. No game discovery/attachment, raw-address command, path command,
// renderer claim, native menu action or hook restoration command is exposed.
namespace checkpoint_session_ipc {
inline constexpr std::uint32_t Magic=0x31495043;
inline constexpr std::uint16_t Version=1;
enum class Opcode:std::uint16_t {Snapshot=1,ArmOnce=2,StopKeepObserving=3};
enum class Status:std::uint32_t {Ok=0,BadRequest=1,Unauthorized=2,Binding=3,Sequence=4,Consumed=5,OperationFailed=6};
#pragma pack(push,1)
struct Request {std::uint32_t magic;std::uint16_t version,opcode;std::uint64_t sequence;unsigned char secret[32],attempt[16],intent[16];};
struct Response {std::uint32_t magic;std::uint16_t version,opcode;std::uint64_t sequence;unsigned char attempt[16];std::uint32_t status,state,error,exceptionCode,armed,menuBound,requestInFlight,casPublished,mayHavePublished,stopRequested,hooksRestored,bytesReady,lifecycleReady,identityReady,activeCallbacks,capabilities;};
#pragma pack(pop)
static_assert(sizeof(Request)==80);static_assert(sizeof(Response)==96);
struct Config {
    checkpoint_guest_native_session::Session* session=nullptr;
    const wchar_t* pipeName=nullptr;
    DWORD expectedClientPid=0,idleTimeoutMs=5000;
    std::uint64_t nativeAttempt=0;
    unsigned char secret[32]{},attempt[16]{},expectedIntent[16]{};
};
struct Diagnostics {
    bool opened=false,running=false,closed=false,armConsumed=false;
    DWORD lastWin32Error=0;
    std::uint64_t lastSequence=0,connections=0,requests=0,rejected=0,losses=0;
    // Deliberately never includes pipe name, secret, attempt, intent or paths.
};
class Server {
public:
    Server()=default;Server(const Server&)=delete;Server&operator=(const Server&)=delete;
    ~Server();
    bool Open(const Config&) noexcept;
    // One server thread only. shutdownEvent is an externally owned event/timer;
    // it must stay valid throughout Run. Loss/deadline/EOF invokes Session.Stop,
    // permanently consumes arm, then accepts reconnect snapshot/stop only.
    bool Run(HANDLE shutdownEvent) noexcept;
    void SnapshotDiagnostics(Diagnostics&) noexcept;
private:
    SRWLOCK lock_=SRWLOCK_INIT;Config config_{};Diagnostics diagnostics_{};
    wchar_t pipeName_[240]{};
    HANDLE pipe_=INVALID_HANDLE_VALUE,client_=nullptr,ioEvent_=nullptr;
    volatile LONG opened_=0,running_=0;bool consumed_=false;
    std::uint64_t lastSequence_=0;
    enum class Io {Ok,Loss,Shutdown};
    Io connect(HANDLE) noexcept;
    Io transfer(bool,void*,DWORD,HANDLE) noexcept;
    Io complete(OVERLAPPED&,DWORD&,HANDLE,ULONGLONG) noexcept;
    void stopForLoss(DWORD) noexcept;
    bool clientAllowed() noexcept;
    void process(const Request&,Response&) noexcept;
    void fill(Response&,Status) noexcept;
};
}
