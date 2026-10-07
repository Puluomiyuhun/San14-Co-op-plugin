#pragma once
#include "checkpoint_persistent_route_core.h"
#include "checkpoint_persistent_bridge.h"

// Data/dispatch integration only. Receipts must come from a separately validated
// native creation/entry/join observer. This module cannot authenticate their
// provenance, install those observations, fence the scheduler or publish loads.
namespace checkpoint_task_attribution {
enum class Kind:unsigned {User,Menu,Game,Load,EmbeddedLoad,Title520,Title590};
enum class Outcome:unsigned {Returned,Abnormal};
enum class Error:unsigned {None,Config,Capacity,Generation,Receipt,Duplicate,Ticket,Thread,Scope,Completed,Frame};
struct Generation {
    checkpoint_persistent_route::Generation callbacks{};
    std::uint64_t attempt=0,epoch=0;
    unsigned char attachment[32]{};
};
struct Creation {
    Kind kind=Kind::User;
    std::uint64_t serial=0,selectionSite=0,creationSite=0;
    std::uint64_t state=0,worker=0,callable=0,payload=0,formalSlot=0;
    DWORD parentThread=0,workerThread=0;
};
struct Entry {
    std::uint64_t serial=0,site=0,caller=0,state=0,worker=0,callable=0;
    DWORD thread=0;
};
struct Completion {
    // Embedded joins run in the owning state's updater/finalizer and need not
    // use the thread which created the embedded task. Their actual join site
    // and owner/worker association must be authenticated by the provider.
    std::uint64_t serial=0,site=0,worker=0,callable=0,attached=0;
    DWORD thread=0,done=0,yielded=0;
};
class Core;
class Ticket {
public: Ticket() noexcept=default;Ticket(const Ticket&)=delete;Ticket& operator=(const Ticket&)=delete;
private:friend class Core;Core* core_=nullptr;unsigned index_=0;std::uint64_t serial_=0;
};
class Execution {
public:Execution() noexcept=default;Execution(const Execution&)=delete;Execution& operator=(const Execution&)=delete;
private:friend class Core;Core* core_=nullptr;Execution* previous_=nullptr;unsigned index_=0;
    DWORD thread_=0;bool used_=false,active_=false;
};
struct Selection {
    checkpoint_persistent_route::Generation callbacks{};
    std::uint64_t serial=0,attempt=0,epoch=0,state=0,callable=0;
    Kind kind=Kind::User;
};
struct Report {
    unsigned initialized=0,generations=0,tasks=0,activeExecutions=0;
    std::uint64_t created=0,entered=0,resumed=0,returned=0,abnormal=0,completed=0,rejected=0;
    Error lastError=Error::None;
    bool nativeReceiptProviderInstalled=false,schedulerFence=false,productionPublication=false;
};
class Core final {
public:
    bool Initialize(std::uint64_t imageBase) noexcept;
    // Registers retained callbacks; does NOT make a generation current/publish it.
    bool RegisterGeneration(const Generation&) noexcept;
    bool RecordCreation(std::uint64_t generation,const Creation&,Ticket&) noexcept;
    // Existing task resume binds the same Ticket, never the current generation.
    // Cooperative yield does not unwind the worker's original native stack:
    // its Execution remains live, and resume does not re-enter 50B730.
    bool RecordYield(Ticket&,std::uint64_t site,DWORD workerThread) noexcept;
    bool RecordResume(Ticket&,std::uint64_t site,DWORD parentThread) noexcept;
    bool Enter(Ticket&,const Entry&,Execution&) noexcept;
    bool Leave(Execution&,Outcome) noexcept;
    bool RecordCompletion(Ticket&,const Completion&) noexcept;
    bool Select(Selection&) noexcept;
    void Snapshot(Report&) noexcept;
private:
    struct Task {Creation c{};unsigned generation=0;bool started=false,active=false,yielded=false,resume=false,returned=false,abnormal=false,completed=false;};
    SRWLOCK lock_=SRWLOCK_INIT;volatile LONG once_=0;std::uint64_t base_=0,lastSerial_=0;
    Generation generations_[16]{};Task tasks_[256]{};Report report_{};
    static thread_local Execution* current_;
    bool reject(Error) noexcept;
    Task* task(Ticket&) noexcept;
};
// Can replace SixAdapter::Configuration on the same frozen six physical bridges,
// or be supplied as a proxy Generation to the UNMODIFIED frozen SixAdapter.
// That router may select a new proxy id, but this adapter selects only the task's
// immutable ticket. Thus even late root callbacks cannot be reattributed.
class Adapter final {
public:
    bool Initialize(Core&) noexcept;
    CheckpointPersistentBridgeConfig Configuration(void* original) noexcept;
    checkpoint_persistent_route::Generation ProxyGeneration(std::uint64_t id) noexcept;
    std::uint64_t ForwardedUnknown() noexcept;
    std::uint64_t Faults() noexcept;
private:
    Core* core_=nullptr;volatile LONG once_=0;volatile LONG64 unknown_=0,faults_=0;
    static void Before(const CheckpointLoadWorkerFrame*,void*);
    static void After(const CheckpointLoadWorkerFrame*,void*);
    static void Finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
};
}
