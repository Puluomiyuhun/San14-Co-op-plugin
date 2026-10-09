#pragma once
#include <windows.h>
#include "player_input_policy.h"
#include "a_reward_save_owner.h"
// Explicit successor to planning_input_resident's physical WndProc path.
// No discovery/bootstrap. A trusted sole publisher calls Initialize on the HWND
// thread. Do not install alongside either predecessor window boundary.
namespace player_input_owner {
namespace policy=player_input_policy;
enum class Error:unsigned {None,Config,Thread,Identity,Source,Publish,Post,Destroyed,Exception};
struct Config {uintptr_t base=0;HWND window=nullptr;DWORD ownerThread=0;policy::Binding binding{};
 a_save_user_owner::Owner*rewardOwner=nullptr;checkpoint_planning_hold::Binding rewardBinding{};};
struct Report {
 Error error=Error::None;DWORD process=0,windowThread=0,ownerThread=0;UINT controlMessage=0;unsigned callbackSlot=0;
 std::uint64_t revision=0,acknowledgedRevision=0,ticket=0,active=0,finally=0,publicationWrites=0;
 std::uint64_t suppressed=0,auditedForwarded=0,lifecycleForwarded=0,uncoveredForwarded=0,unclassifiedForwarded=0,ignoredControl=0;
 policy::State state{};bool initialized=false,installed=false,pending=false,acknowledged=false,held=true,uncertain=false,destroyed=false;
 bool publicationConflict=false,foreignSourceMayHaveBeenReplaced=false;
 bool localCommandPolicyOpen=false,remoteMessagesAllowed=false,remoteExecutionPolicyOpen=false;
 bool allInputHeld=false,gameReportWhitelistVerified=false,physicalReleaseProven=false,osQueueDrained=false,saveAuthorized=false,roomReady=false;
};
class Owner final {
public:
 Owner();~Owner()=delete;Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 bool Initialize(const Config&)noexcept;
 // On the configured serialized local lane, not a TLS callback. Return means
 // queued. Release occurs only on actual matching HWND delivery. Closing takes
 // effect immediately, but is not reported acknowledged before delivery/FINALLY.
 bool Request(const policy::Binding&,policy::State,std::uint64_t revision,bool&duplicate)noexcept;
 // Additional policy veto around the existing trusted native Submit. It never
 // substitutes for native authority, argument validation, sequencing or receipt.
 bool SubmitRemoteReward(const policy::Binding&,std::uint64_t revision,std::uint64_t sequence,
                         const checkpoint_reward_owned_replay::Command&)noexcept;
 void Snapshot(Report&)noexcept;
private:struct Impl;Impl*p_;
};
}
