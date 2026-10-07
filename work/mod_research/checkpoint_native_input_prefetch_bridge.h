#pragma once
#include "checkpoint_native_input_pending_adapter.h"
#include <cstddef>

namespace checkpoint_native_input_prefetch {
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable:4324) // Intentional 16-byte CPU frame alignment inside reports/scopes.
#endif
enum Register:unsigned {Rax,Rcx,Rdx,Rbx,Rsp,Rbp,Rsi,Rdi,R8,R9,R10,R11,R12,R13,R14,R15};
struct alignas(16) Frame {
    std::uint64_t gpr[16]{};
    std::uint64_t rflags=0,return_address=0;
    std::uint8_t xmm[16][16]{};
    std::uint32_t mxcsr=0;
    std::uint32_t reserved[3]{};
};
static_assert(sizeof(Frame)==0x1a0);
static_assert(offsetof(Frame,rflags)==0x80&&offsetof(Frame,xmm)==0x90&&offsetof(Frame,mxcsr)==0x190);
enum class Status {NotObserved,Observed,NoRoute,WrongThread,Reentrant,WrongSite,WrongStack,WrongUser,ObserverFault,PendingRejected};
struct Report {
    Status status=Status::NotObserved;
    DWORD exception_code=0;
    checkpoint_native_input_pending::Report pending{};
    Frame captured{};
    bool installed_in_game=false,global_hold_proven=false;
};
using Probe = void(*)(void*); // Optional diagnostic/fault injection in OWNED fixtures only.
struct Config {
    checkpoint_native_input_pending::Adapter* pending=nullptr;
    checkpoint_native_input::Binding binding{};
    std::uint64_t call_id=0;
    const void* user=nullptr;
    std::uintptr_t expected_call_return=0;
    Probe before_observation=nullptr;
    void* probe_context=nullptr;
};
class Scope final {
public:
    explicit Scope(const Config&) noexcept;
    ~Scope();
    Scope(const Scope&)=delete;Scope&operator=(const Scope&)=delete;
    const Report& GetReport()const noexcept{return report_;}
private:
    friend void Observe(const Frame*);
    friend void ObservationFault(DWORD) noexcept;
    Config config_{};Report report_{};Scope*previous_=nullptr;
    DWORD thread_=0;bool observing_=false;
};
void Observe(const Frame*);
void ObservationFault(DWORD) noexcept;
#ifdef _MSC_VER
#pragma warning(pop)
#endif
}

// Mid-function no-argument call entry. It captures the live register context;
// do not call as a C++ function-entry replacement or copy its raw code bytes.
extern "C" void CheckpointPrefetchMidBridge();
extern "C" void CheckpointPrefetchObserve(const checkpoint_native_input_prefetch::Frame*) noexcept;
extern "C" unsigned char CheckpointPrefetchMidBody,CheckpointPrefetchReplayLoad;
