#pragma once
#include "checkpoint_load_hook_set.h"
#include "checkpoint_native_input_pending_adapter.h"
#include "a_save_input_bridge.h"

// One concrete independent consumer source, NOT all-input exclusion. The User
// and Save vtable slots are never owned/modified by this component.
namespace a_save_input {
namespace pending=checkpoint_native_input_pending;
enum class Error:unsigned {None,Config,Used,Source,Bridge,Hooks,Input,Scope,Exception};
struct Config {
 uintptr_t base=0,root=0,world=0;
 pending::Binding binding{};
 // Read-only/non-reentrant. May not call any Owner method. Samples fresh spans
 // on the real Game execution thread; never an approval/idle boolean.
 bool(*sample)(void*,pending::Config&)noexcept=nullptr;
 void*context=nullptr;
#ifdef A_SAVE_INPUT_FIXTURE
 uintptr_t fixtureGameCaller=0,fixtureUiCaller=0;
#endif
};
struct Report {
 Error error=Error::None;
 unsigned initialized=0,armed=0,stopped=0;
 std::uint64_t revision=0,active=0,gameCalls=0,uiSuppressed=0,uiForwarded=0;
 bool requested=false,coveredGlobalUiHeld=false;
 bool fullInputHold=false,saveAuthorized=false,roomReady=false;
 checkpoint_load_hook_set::Report hooks{};
 CheckpointLoadWorkerBridgeStats bridges[2]{};
};
class Owner final {
public:
 Owner();~Owner()=delete;Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 bool Initialize(const Config&)noexcept;
 bool Arm()noexcept;
 bool Hold(const pending::Binding&,bool,std::uint64_t revision)noexcept;
 void Stop()noexcept;
 void Snapshot(Report&)noexcept;
private:struct Impl;Impl*p_;
};
}
