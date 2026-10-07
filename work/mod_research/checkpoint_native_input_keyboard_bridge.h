#pragma once
#include "checkpoint_native_input_core.h"
#include <array>
#include <cstdint>
#include <thread>

namespace checkpoint_native_input_keyboard {
using checkpoint_native_input::Binding;
using checkpoint_native_input::Buffers;
enum class Query : std::uint32_t { Release, Press, Repeat, Modifier11, ModifierMasked, Modifier22, Count };
enum class Mode { ForwardUntouched, NeutralizeAuditedQuery };
enum class Status {
    Ok, NotBound, AlreadyBound, InvalidTarget, WrongThread, StaleBinding,
    UnexpectedCache, InvalidLayout, InvalidMode, InvalidQuery, ReentrantCall,
    PublicationRejected, OriginalException, UnexpectedOriginalResult,
};
const char* StatusName(Status value) noexcept;

// The real leaves return AL. Their upper RAX is semantically unspecified. This
// capture type retains it opaquely; it must not be interpreted as a 64-bit bool.
// RCX/EDX/R8D are the only consumed arguments across the audited family. Unary
// and binary leaves ignore the extra arguments. No provider method is called.
using OriginalQuery = std::uint64_t (*)(const void*, std::uint32_t, std::uint32_t);
using Targets = std::array<OriginalQuery, static_cast<std::size_t>(Query::Count)>;
struct Request {
    Binding binding{};
    // Strictly increasing publication number per neutralized query, not a
    // native engine-frame ID. This bridge owns its separate core adapter.
    std::uint64_t publication_cycle = 0;
    Mode mode = Mode::ForwardUntouched;
};
struct Report {
    Status status = Status::NotBound;
    checkpoint_native_input::Status core_status = checkpoint_native_input::Status::NotBound;
    checkpoint_native_input::Publication publication{};
    Query query = Query::Count;
    const void* original_cache = nullptr;
    std::uint32_t argument = 0, flag = 0;
    std::uint64_t original_rax = 0, delivered_rax = 0;
    bool original_started = false, original_completed = false, exception_rethrown = false;
    bool used_neutral_shadow = false, native_hook_installed = false;
    bool complete_native_input_hold = false, physical_release_proven = false;
};

class QueryBridge final {
public:
    QueryBridge() = default;
    QueryBridge(const QueryBridge&) = delete;
    QueryBridge& operator=(const QueryBridge&) = delete;
    // Caller owns all buffer/code lifetimes and exclusive same-thread access.
    // Targets must be the separately verified pure leaves with this ABI. Null
    // targets are disabled, not discovered. No pointers/vtables are installed.
    Status Bind(const Binding&, Buffers, Targets) noexcept;
    // Neutral mode first publishes the frozen core's caches/shadow. Key leaves
    // then execute normally on the neutral cache. Modifier leaves execute once
    // on the ORIGINAL physical source, then only AL is substituted with the
    // neutral shadow result. Normal+0 and every physical raw byte stay intact.
    // Failure before target: returns zero, report is non-Ok, no original call.
    // C++ exceptions retain identity and unwind; arbitrary SEH is not proven.
    std::uint64_t Invoke(const Request&, Query, const void*, std::uint32_t argument,
                         std::uint32_t flag, Report&);
private:
    checkpoint_native_input::Adapter adapter_;
    Binding binding_{};
    Buffers buffers_{};
    Targets targets_{};
    std::thread::id owner_{};
    bool bound_ = false, inside_ = false;
};

// A route is explicitly established by an owning caller. The wrappers are not
// installable global detours: absent routes return zero with a counter, and no
// automatic original-pointer lookup exists. Never install them globally as-is.
class ScopedRoute final {
public:
    ScopedRoute(QueryBridge&, Request) noexcept;
    ~ScopedRoute();
    ScopedRoute(const ScopedRoute&) = delete;
    ScopedRoute& operator=(const ScopedRoute&) = delete;
    const Report& report() const noexcept { return report_; }
private:
    friend std::uint64_t Routed(Query,const void*,std::uint32_t,std::uint32_t);
    QueryBridge& bridge_;
    Request request_;
    Report report_{};
    ScopedRoute* previous_;
};
std::uint64_t UnroutedCallCountForThisThread() noexcept;
std::uint64_t Routed(Query,const void*,std::uint32_t,std::uint32_t);

// Exact consumed native parameters, returning opaque RAX whose AL is used.
// C++ linkage deliberately preserves /EHsc exception unwinding.
std::uint64_t Release(const void*,std::uint32_t key);
std::uint64_t Press(const void*,std::uint32_t key);
std::uint64_t Repeat(const void*,std::uint32_t key,std::uint32_t require_active);
std::uint64_t Modifier11(const void*);
std::uint64_t Modifier22(const void*);
std::uint64_t ModifierMasked(const void*,std::uint32_t mask,std::uint32_t require_all);
}
