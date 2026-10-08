#pragma once
#include "checkpoint_native_task_provider.h"
#include "b_reload_parent_bridge.h"

// Retained source successor. The scheduler queue phase owns no debug slots;
// four native parent sources are enabled only AFTER its internal F570 call.
// Does not install code, call the scheduler, hold all input, or release Ready.
namespace b_reload_parent_source {
enum class Error:unsigned {None,Config,Source,Bridge,Stopped,Order,Occupied,Helper,Context,Restore,Capacity,Provider,Exception,Deadline};
struct Config {uintptr_t base=0;checkpoint_native_task_provider::Provider* provider=nullptr;DWORD helperDeadlineMs=1000;};
struct Patch {uintptr_t address=0;unsigned char before[5]{},after[5]{};};
struct Plan {Patch patches[2]{};uintptr_t relay=0;};
struct Sample {uintptr_t rip=0,rsp=0,rdi=0,state=0;DWORD thread=0;unsigned point=0,accepted=0,skipped=0;};
struct Report {
 Error error=Error::None;DWORD osError=0;unsigned initialized=0,armed=0,stopped=0;
 unsigned scopes=0,active=0,phaseStarted=0,finally=0,abnormal=0,restored=0,uncertain=0;
 unsigned hits[4]{},accepted[4]{},yieldedSkipped=0,unknownSkipped=0;
 Sample last[4]{};std::uint64_t originalDr[6]{},restoredDr[6]{};
 bool installer=false,finalizeCompatible=false,rootWorkerSources=false,fullWorld=false,roomReady=false;
};
struct QueueOwner {uintptr_t base=0,manager=0;DWORD thread=0;std::uint64_t call=0;};
class Owner final {
public:
 Owner();~Owner()=delete;Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 bool Initialize(const Config&) noexcept;
 // Only a trusted installer may publish this exact plan after real drainage.
 // Arm merely checks already-installed bytes; no "all threads stopped" flag.
 bool PreparedPlan(Plan&) noexcept;
 bool Arm() noexcept;
 void Stop() noexcept;
 void Snapshot(Report&) noexcept;
 // Authenticated outer bridge, exact caller, queue phase and this OS thread.
 // Not yet sufficient by itself to authorize a Load.Finalize callback.
 static bool CurrentQueueOwner(QueueOwner&) noexcept;
private:struct Impl;Impl* p_;
};
}
