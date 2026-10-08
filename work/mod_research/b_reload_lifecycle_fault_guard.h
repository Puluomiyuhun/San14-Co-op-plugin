#pragma once
#include "checkpoint_persistent_authorized_controller.h"
#include "checkpoint_native_task_provider.h"
#include "b_reload_root_activation.h"
// Trusted local host gate, not a native scheduler fence or game installer.
// One successfully bound retained gate per attempted transition; no retry after
// RegisterAndOpen consumes an attempt. Invalid Initialize/wrong-thread calls do
// not consume it. Trusted caller must supply the actual registered source objects.
// Report snapshots are not an atomic scheduler lock; externally serialize workers.
namespace b_reload_lifecycle_fault_guard {
namespace tp=checkpoint_native_task_provider;namespace ad=checkpoint_persistent_authorized;namespace ns=checkpoint_dynamic_native_session;
enum class Error:unsigned {None,Config,Thread,Input,Session,Root,Incomplete,Next,Register,Open};
struct Report {Error error=Error::None;DWORD thread=0;std::uint64_t previous=0,next=0;unsigned attempts=0,registerCalls=0,openCalls=0,abnormalTasks=0;bool initialized=false,finished=false,registered=false,opened=false,uncertain=false;ad::Error inputError=ad::Error::None;tp::Error providerError=tp::Error::None;LONG sessionError=0;bool schedulerFence=false,roomReady=false,fullWorld=false;};
class Gate final {
public:Gate()=default;~Gate()=delete;
 bool Initialize(tp::Provider&,std::uint64_t,ns::Session&,ad::Controller&)noexcept;
 bool RegisterAndOpen(const tp::Config&)noexcept;
 void Snapshot(Report&)noexcept;
private:SRWLOCK lock_=SRWLOCK_INIT;Report r_{};tp::Provider*p_=nullptr;ns::Session*s_=nullptr;ad::Controller*a_=nullptr;
};
}
