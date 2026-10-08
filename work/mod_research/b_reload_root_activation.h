#pragma once
#include "checkpoint_native_task_provider_bound.h"
#include "b_reload_root_worker_ports.h"
namespace b_reload_root_activation {
using Binding=checkpoint_native_task_provider_bound::Binding;
enum class Error:unsigned {None,Config,Source,Capacity,Binding,Thread,Wait,Event,Publish,Stopped,Bridge,Ports,Exception,Conflict};
struct Config {uintptr_t base=0;checkpoint_native_task_provider::Provider* provider=nullptr;DWORD helperDeadlineMs=1000;};
struct Task {Binding binding{};uintptr_t worker=0,callable=0,object=0,state=0;DWORD thread=0;unsigned selected=0,finished=0,abnormal=0;b_reload_root_worker_ports::Report ports{};};
struct Report {Error error=Error::None;DWORD osError=0;uintptr_t iatSlot=0,original=0,replacement=0;unsigned initialized=0,published=0,threads=0,taskCount=0,gateEntries=0,gateFinishes=0,unrelated=0,initialWaitVerified=0,outerBefore=0,outerFinally=0,uncertain=0;Task tasks[64]{};bool gameAccess=false,productionInstaller=false,fullWorld=false,roomReady=false;};
bool Initialize(const Config&) noexcept;
bool PublishIat() noexcept;
// Only called by the actual parent-source successor after its bound 50B598
// creation was accepted. Resume is not a new creation and must bypass this API.
bool OnCreation(checkpoint_native_task_provider::Provider&,const Binding&,const checkpoint_native_task_provider::Capture&) noexcept;
void Stop() noexcept;
bool Snapshot(Report&) noexcept;
}
