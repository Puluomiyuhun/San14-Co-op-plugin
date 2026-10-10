#pragma once
#include "a_save_local_binding.h"
#include "a_reward_save_owner.h"
#include "planning_input_interlock_gate.h"
#include <cstddef>
// Diagnostic only. No UI, command, Ready, save or load permission is issued.
namespace a_menu_parent_observation {
namespace pending=checkpoint_native_input_pending;
// Busy is only Inspector's early toolbar/selection decision, NOT proof that
// later checks passed or a live submenu is supported. Seven-stack capture is
// Unknown; six-stack without those early decisions is normally Blocked.
enum class State:std::uint32_t {Unknown,QuietObserved,BusyObserved,Blocked};
enum class Reason:std::uint32_t {None,Boundary,Identity,Sample,Bind,Inspector,Owner,Retired,Exception};
#pragma pack(push,8)
struct Binding {
 std::uint32_t pid=0,reserved=0;
 std::uint64_t birth=0,base=0,root=0,world=0,user=0,generation=0,period=0,epoch=0;
 unsigned char attempt[16]{},attachment[16]{},inputDigest[32]{};
};
struct Record {
 std::uint32_t size=sizeof(Record),version=1;
 // Odd while publishing; stable even values identify completed observations.
 alignas(8) volatile LONG64 sequence=0;
 Binding binding{};
 std::uint64_t tick=0,parentCall=0,current=0,stackCount=0,queueCount=0,selection[3]{};
 std::uint32_t thread=0,state=0,reason=0,exceptionCode=0,inspectorError=0,decision=0;
 std::int32_t menuCommand=-1;
 std::uint32_t userPhase=0,gameTransition=0,loadQueued=0,advance=0,panelAdvance=0;
 std::uint32_t ownerError=0,ownerStopped=0,gateError=0,gateStopped=0;
 std::uint64_t ownerActive=0,gateActive=0,rewardSequence=0,rewardCompleted=0,rewardActive=0;
 std::uint32_t readyFence=0,gateRequested=0,rewardQueued=0,runtimeStopped=0,runtimeError=0,planningState=0,repeatState=0;
 std::uint32_t uiPermission=0,rewardPermission=0,fullInputHold=0;
};
#pragma pack(pop)
struct Input {
 Binding binding{};
 bool identity=false,stopped=false,retired=false;
 unsigned runtimeError=0,planningState=0,repeatState=0;
 a_save_user_owner::Owner*owner=nullptr;a_save_upstream_gate::Owner*gate=nullptr;
 bool(*sample)(void*,pending::Config&)noexcept=nullptr;void*context=nullptr;
};
void Observe(const Input&)noexcept;
void Snapshot(Record&)noexcept;
// Returns only a fresh same-binding finite Quiet/Busy observation. Neither is a
// permit or a promise of current health: later original callbacks may Stop.
bool Read(const Binding&,std::uint64_t afterSequence,std::uint64_t now,std::uint64_t maxAge,Record&)noexcept;
}
extern "C" __declspec(dllexport) a_menu_parent_observation::Record AMenuParentObservation;
