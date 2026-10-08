#pragma once
#include "checkpoint_load_hook_set.h"
#include "checkpoint_native_input_pending_adapter.h"
#include "a_save_action_gate_bridge.h"
#include "a_save_user_owner.h"

// Successor to a_save_input: Game/global-UI plus direct panel and claimed-save
// User action-tail sources. Never all-input exclusion. The User/Save vtable
// slots remain with a_save_user_owner; the User BODY is explicitly transformed.
namespace a_save_action_gate {
namespace pending=checkpoint_native_input_pending;
enum class Error:unsigned {None,Config,Used,Source,Bridge,Hooks,Input,Scope,Exception};
struct Config {
 uintptr_t base=0,root=0,world=0;
 a_save_user_owner::Owner* saveOwner=nullptr;
 pending::Binding binding{};
 // Read-only/non-reentrant. May not call any Owner method. Samples fresh spans
 // on the real Game execution thread; never an approval/idle boolean.
 bool(*sample)(void*,pending::Config&)noexcept=nullptr;
 void*context=nullptr;
#ifdef A_SAVE_ACTION_FIXTURE
 uintptr_t fixtureGameCaller=0,fixtureUiCaller=0;
#endif
};
struct Report {
 Error error=Error::None;
 unsigned initialized=0,armed=0,stopped=0;
 std::uint64_t revision=0,active=0,gameCalls=0,uiSuppressed=0,uiForwarded=0;
 bool requested=false,coveredGlobalUiHeld=false;
 std::uint64_t panelSuppressed=0,panelForwarded=0,userTailSuppressed=0,userTailForwarded=0;
 bool coveredPanelHeld=false,ownedUserTailTransform=false;
 bool fullInputHold=false,saveAuthorized=false,roomReady=false;
 checkpoint_load_hook_set::Report hooks{};
 CheckpointLoadWorkerBridgeStats bridges[3]{};
};
// Source publication is a separate installer operation. No caller-supplied
// boolean can certify all threads stopped. Prepare only builds a retained RX
// near relay; Arm checks these exact installed bytes and the source image.
struct Patch {uintptr_t address=0;unsigned size=0;unsigned char before[7]{},after[7]{};};
struct Plan {Patch patches[2]{};uintptr_t relay=0;};
class Owner final {
public:
 Owner();~Owner()=delete;Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 bool Initialize(const Config&)noexcept;
 bool PreparedPlan(Plan&)noexcept;
 bool Arm()noexcept;
 bool Hold(const pending::Binding&,bool,std::uint64_t revision)noexcept;
 void Stop()noexcept;
 void Snapshot(Report&)noexcept;
private:struct Impl;Impl*p_;
};
}
