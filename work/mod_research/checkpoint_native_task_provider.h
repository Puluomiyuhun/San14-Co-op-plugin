#pragma once
#include "checkpoint_task_attribution_core.h"
#include "checkpoint_dynamic_native_session.h"
#include "checkpoint_persistent_planning_observer.h"

// Resident read-only native-source adapter. No installer, game call, request,
// current-generation fallback, scheduler fence or production publication.
namespace checkpoint_native_task_provider {
namespace ta=checkpoint_task_attribution;
enum class Error:unsigned {None,Config,Capacity,Window,Memory,Source,Formal,Thread,Order,Native,Attribution,Receipt};
// Values are the ACTUAL instruction context supplied by a separately installed
// port. rip is never described as a call return address. This data core cannot
// authenticate that a caller really intercepted native execution at rip.
struct Capture {uintptr_t rip=0,rcx=0,rdx=0,rbx=0,rdi=0,rsp=0;DWORD thread=0;};
struct Config {
    uintptr_t base=0;ta::Generation generation{};
    checkpoint_dynamic_file_profile::Profile file{};
    checkpoint_dynamic_native_session::Session* session=nullptr;
    checkpoint_persistent_planning::Observer* planning=nullptr;
};
struct Role {
    uintptr_t control=0,threadObject=0,callable=0,method=0,payload=0;
    DWORD workerThread=0,startThread=0,joinThread=0;
    std::uint64_t creation=0,start=0,invoke=0,payloadEntry=0,returned=0,done=0,joined=0;
};
struct Report {
    std::uint64_t generation=0,attempt=0,epoch=0,events=0,creations=0,rejected=0,ignored=0;
    uintptr_t load=0,title=0,closure=0;Role roles[3]{};
    Error error=Error::None;DWORD exception=0;
    unsigned registered=0,windowOpen=0,loadBound=0,titleCallback=0,threeJoins=0,planning=0,closed=0;
    unsigned taskCapacity=256,retainedTasks=0;
    bool sourceHooksInstalled=false,productionPublication=false,schedulerFence=false,fullWorld=false;
};
class Provider final {
public:
    // Exactly two resident banks. Neither tasks nor completed banks are reset
    // or recycled. This bounded candidate supports two observations, not an
    // unlimited in-process multiplayer session.
    bool Register(const Config&) noexcept;
    bool OpenWindow(std::uint64_t generation) noexcept;
    bool Observe(const Capture&) noexcept;
    // Called only by an exception-preserving runner FINALLY when no normal
    // 834D9B return happened. It releases this thread's attribution scope.
    bool Abnormal() noexcept;
    bool CloseCompletedWindow(std::uint64_t generation) noexcept;
    bool Snapshot(std::uint64_t generation,Report&) noexcept;
    std::uint64_t UnknownEvents() noexcept {return InterlockedCompareExchange64(&unknown_,0,0);}
    checkpoint_persistent_route::Generation ProxyGeneration(std::uint64_t proxyId) noexcept;
private:
    struct Record {ta::Ticket ticket;ta::Execution execution;ta::Creation creation{};Provider* owner=nullptr;unsigned bank=0;
        bool entered=false,returned=false,done=false,complete=false,abnormal=false;Record* previous=nullptr;};
    struct Bank {Config config{};ta::Core core;ta::Adapter adapter;Report report{};Record records[256];
        unsigned count=0;bool selected=false;DWORD selectionThread=0;uintptr_t selectionState=0,selectionSlot=0;};
    SRWLOCK lock_=SRWLOCK_INIT;Bank banks_[2];unsigned count_=0,current_=2;
    std::uint64_t serial_=0,sequence_=0;
    volatile LONG64 unknown_=0;
    static thread_local Record* active_;
    bool body(const Capture&);
    bool reject(Bank*,Error,DWORD exception=0) noexcept;
    bool formal(Bank&,bool requireLoad);
    bool stateFormal(Bank&,uintptr_t,uintptr_t,ta::Kind&);
    Record* record(Bank&,const ta::Creation&);
    Record* matching(uintptr_t worker,DWORD thread,bool enteredOnly);
    static void Before(const CheckpointLoadWorkerFrame*,void*);
    static void After(const CheckpointLoadWorkerFrame*,void*);
    static void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
};
}
