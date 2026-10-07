#pragma once
#include "checkpoint_native_input_consumer_bridge.h"
#include "checkpoint_native_input_keyboard_bridge.h"
#include "checkpoint_native_input_action_bridge.h"
#include <cstdint>
#include <thread>

namespace checkpoint_native_input_router {
using checkpoint_native_input::Binding;
enum class Mode { ForwardUntouched, NeutralizeAdmittedQuery };
enum class Kind : std::uint32_t { Mouse, KeyRelease, KeyPress, KeyRepeat,
    Modifier11, ModifierMasked, Modifier22, Action, Count };
enum class Status { Ok, NotBound, BindAlreadyAttempted, InvalidTarget, BindRejected,
    WrongThread, StaleBinding, InvalidMode, UnknownRoute, InvalidArguments,
    WrongSource, InvalidSourceLayout, StaleCycle, Reentrant, OriginalInFlight, DelegateRejected, OriginalException };
const char* StatusName(Status) noexcept;
struct Config {
    // This one action configuration owns the common binding and source views.
    // There are no separately supplied mouse/keyboard identities to mix up.
    checkpoint_native_input_action::Config source;
    checkpoint_native_input_consumer::MouseQuery mouse_original=nullptr;
    checkpoint_native_input_keyboard::Targets keyboard_originals{};
};
struct BindReport {
    Status status=Status::NotBound;
    checkpoint_native_input_consumer::Status mouse=checkpoint_native_input_consumer::Status::NotBound;
    checkpoint_native_input_keyboard::Status keyboard=checkpoint_native_input_keyboard::Status::NotBound;
    checkpoint_native_input_action::Status action=checkpoint_native_input_action::Status::NotBound;
};
struct Request {
    Binding binding{};
    // One nonzero, strictly increasing request/publication sequence shared by
    // every route, including forwarding. Gaps are allowed; replay is not.
    std::uint64_t cycle=0;
    Mode mode=Mode::ForwardUntouched;
};
struct Call {
    Kind kind=Kind::Count;
    // Exact incoming native cache pointer. Action has no cache argument and
    // must use nullptr; its frozen adapter validates global sources itself.
    const void* observed_cache=nullptr;
    std::uint32_t argument=0,flag=0;
};
struct Report {
    Status status=Status::NotBound;
    Kind kind=Kind::Count;
    std::uint64_t cycle=0,previous_cycle=0,original_return=0,delivered_return=0;
    bool cycle_consumed=false,delegated=false,original_started=false,original_completed=false;
    bool exception_rethrown=false;
    checkpoint_native_input_consumer::Report mouse{};
    checkpoint_native_input_keyboard::Report keyboard{};
    checkpoint_native_input_action::Report action{};
    bool native_hook_installed=false,complete_native_input_hold=false,physical_release_proven=false;
    bool authorize_release=false;
};
class Router final {
public:
    Router()=default;Router(const Router&)=delete;Router& operator=(const Router&)=delete;
    // One-shot, even on failure. Partial sub-bridge binding cannot be reused.
    // Code/buffer lifetimes and same-thread exclusion are host obligations.
    BindReport Bind(const Config&) noexcept;
    // Unified production dispatch, not an observation-only approval facade.
    // Claims cycle before delegating. A delegate failure or original exception
    // keeps it consumed; callers must inspect the child report and not replay.
    std::uint64_t Invoke(const Request&,const Call&,Report&);
private:
    checkpoint_native_input_consumer::MouseQueryBridge mouse_;
    checkpoint_native_input_keyboard::QueryBridge keyboard_;
    checkpoint_native_input_action::Bridge action_;
    Binding binding_{};const void* normal_=nullptr;const void* mouse_cache_=nullptr;
    checkpoint_native_input::Buffers buffers_{};
    std::thread::id owner_{};std::uint64_t last_cycle_=0;
    bool bind_attempted_=false,bound_=false,inside_=false;
};
class ScopedRoute final {
public:
    ScopedRoute(Router&,Request) noexcept;~ScopedRoute();
    ScopedRoute(const ScopedRoute&)=delete;ScopedRoute& operator=(const ScopedRoute&)=delete;
    const Report& report()const noexcept{return report_;}
private:
    friend std::uint64_t Routed(const Call&);
    Router& router_;Request request_;Report report_{};ScopedRoute* previous_;
};
std::uint64_t UnroutedCallCountForThisThread() noexcept;
std::uint64_t Routed(const Call&);
// Exact consumed native parameters; no global hooks are installed. Explicit
// routes last for a single sequence. Missing routes return zero and count it.
std::uint32_t Mouse(const void*,std::uint32_t button);
std::uint64_t KeyRelease(const void*,std::uint32_t key);
std::uint64_t KeyPress(const void*,std::uint32_t key);
std::uint64_t KeyRepeat(const void*,std::uint32_t key,std::uint32_t require_active);
std::uint64_t Modifier11(const void*);
std::uint64_t Modifier22(const void*);
std::uint64_t ModifierMasked(const void*,std::uint32_t mask,std::uint32_t require_all);
std::uint32_t Action(std::uint32_t action);
}
