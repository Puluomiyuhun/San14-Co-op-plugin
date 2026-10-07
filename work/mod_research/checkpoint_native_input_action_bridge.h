#pragma once
#include "checkpoint_native_input_core.h"
#include <cstdint>
#include <thread>

namespace checkpoint_native_input_action {
using checkpoint_native_input::Binding;
using checkpoint_native_input::ConstSpan;
using checkpoint_native_input::MutableSpan;
inline constexpr std::size_t kActionRva=0x3A2DC0, kSingletonRva=0x292220;
inline constexpr std::size_t kNormalRva=0x1FCA0A0, kMouseRva=0x19E1D30;
inline constexpr std::size_t kMapPointerRva=0x1FD1678, kActiveRva=0x1905654;
inline constexpr std::size_t kTlsIndexRva=0x203ABC0, kInitGuardRva=0x1FCA118;
enum class Mode { ForwardUntouched, NeutralizeAuditedAction };
enum class Status { Ok, NotBound, AlreadyBound, InvalidSpan, Overlap, CodeMismatch,
    WrongThread, StaleBinding, WrongSource, InvalidLayout, UninitializedSingleton,
    WrongTls, InvalidAction, UnknownMapping, InvalidMode, Reentrant, PublicationRejected,
    SourceChanged, OriginalInFlight, OriginalException, UnexpectedOriginalResult };
const char* StatusName(Status) noexcept;
struct Config {
    Binding binding{};
    // These are in-process, lifetime-pinned views supplied by an owning host.
    // No discovery, foreign read, device query, or automatic hook installation.
    MutableSpan image;
    checkpoint_native_input::Buffers buffers;
    ConstSpan mapping;          // 0x100-byte action bindings object
    ConstSpan tls_slots;        // exact current GS:[58] array, owner-proved extent
    ConstSpan tls_data;         // exact module slot pointer, at least +10 DWORD
    std::uint32_t tls_index=0;  // independently bound to this module
};
struct Request { Binding binding{};std::uint64_t publication_cycle=0;Mode mode=Mode::ForwardUntouched; };
struct Report {
    Status status=Status::NotBound;
    checkpoint_native_input::Status core_status=checkpoint_native_input::Status::NotBound;
    checkpoint_native_input::Publication publication{};
    std::uint32_t action=0, codes[2]{}, active_gate=0, original_value=0, delivered_value=0;
    std::int32_t initialized_epoch=0, thread_epoch=0;
    bool original_started=false,original_completed=false,source_bundle_unchanged=false;
    bool used_neutral_shadow=false,exception_rethrown=false;
    bool native_hook_installed=false,complete_native_input_hold=false,physical_release_proven=false;
};
class Bridge final {
public:
    Bridge()=default;Bridge(const Bridge&)=delete;Bridge& operator=(const Bridge&)=delete;
    Status Bind(const Config&) noexcept;
    // Full original action and singleton getter run, but ONLY after the getter
    // is proven to take its already initialized TLS fast path. Original native
    // code cannot be supplied as an arbitrary function pointer. Neutral mode
    // delivers the same core publication's shadow result after normal return.
    // Failure returns zero with non-Ok report. A report is not a native lock.
    std::uint32_t Invoke(const Request&,std::uint32_t action,Report&);
private:
    Status Sources(const Config&,std::uint32_t action,bool check_action,Report&) const noexcept;
    checkpoint_native_input::Adapter adapter_;
    Config config_{};std::thread::id owner_{};bool bound_=false,inside_=false;
};
class ScopedRoute final {
public:
    ScopedRoute(Bridge&,Request) noexcept;~ScopedRoute();
    ScopedRoute(const ScopedRoute&)=delete;ScopedRoute& operator=(const ScopedRoute&)=delete;
    const Report& report()const noexcept{return report_;}
private:
    friend std::uint32_t ActionQuery(std::uint32_t);
    Bridge& bridge_;Request request_;Report report_{};ScopedRoute* previous_;
};
// Windows x64 ECX -> EAX. Explicit routes only, NOT a global detour: absence
// returns zero and increments a diagnostic counter. /EHsc is not a SEH proof.
std::uint32_t ActionQuery(std::uint32_t action);
std::uint64_t UnroutedCallCountForThisThread() noexcept;
}
