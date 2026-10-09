#include "a_save_native_input_scope.h"
#include "b_reload_parent_bridge.h"
#include "a_save_action_gate_bridge.h"
#include "a_save_user_owner_bridge.h"
#include "a_save_parent_adapter.h"
namespace a_save_native_input_scope {
bool Current(const checkpoint_native_input_pending::Config&c,
             checkpoint_native_input_pending::Stage stage,uintptr_t current)noexcept {
 if(stage!=checkpoint_native_input_pending::Stage::Standalone||uintptr_t(c.manager.data)!=c.profile_base+0x19E7310)return false;
 __try {
  CheckpointLoadWorkerOwner owner{};
  if(current==uintptr_t(c.game.data)){
   // Gate verifies exact Game return source and frame BEFORE claiming this
   // scope. A generic current-state pointer alone is never enough.
   return ASaveActionCurrentOwner(&owner)&&owner.slot==0&&owner.token==c.binding.owner_generation&&
          owner.call_id&&owner.thread_id==GetCurrentThreadId()&&owner.owner_depth==1&&owner.current_depth==1;
  }
  if(current||!a_save_parent_adapter::CurrentBoundary(c.profile_base)||!BReloadParentCurrentOwner(&owner)||owner.slot||!owner.call_id||owner.token!=owner.call_id||
     owner.thread_id!=GetCurrentThreadId()||owner.owner_depth!=1||owner.current_depth!=1)return false;
  // Actual parent boundaries observed in the game have current==0 and no
  // retained formal-state tasks. Do not equate a parent return alone with drain.
  for(auto state:c.states)if(!state||*reinterpret_cast<const volatile uintptr_t*>(state+0x50))return false;
  CheckpointLoadWorkerBridgeStats s{};
  for(unsigned i=0;i<2;++i)if(!ASaveUserOwnerBridgeSnapshot(i,&s)||!s.configured||!s.module_pinned||s.active)return false;
  for(unsigned i=0;i<3;++i)if(!ASaveActionBridgeSnapshot(i,&s)||!s.configured||!s.module_pinned||s.active)return false;
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
}
