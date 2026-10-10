#pragma once
#include <windows.h>
#include <cstdint>
#include "player_input_policy.h"
namespace player_input_rebind {
namespace policy=player_input_policy;
enum class Error:unsigned {None,Config,Thread,Identity,Source,Publish,Post,Destroyed,Exception,Lease};
struct Config {uintptr_t base=0;HWND window=nullptr;policy::Binding binding{};};
struct Lease {std::uint64_t id=0,sequence=0,revision=0;};
struct Report {
 Error error=Error::None;DWORD process=0,windowThread=0,ownerThread=0;UINT controlMessage=0;unsigned callbackSlot=0;
 std::uint64_t revision=0,acknowledgedRevision=0,ticket=0,active=0,finally=0,publicationWrites=0;
 std::uint64_t suppressed=0,auditedForwarded=0,lifecycleForwarded=0,uncoveredForwarded=0,unclassifiedForwarded=0,ignoredControl=0;
 policy::Binding binding{};policy::State state{};bool initialized=false,installed=false,pending=false,acknowledged=false,held=true,uncertain=false,destroyed=false;
 bool publicationConflict=false,foreignSourceMayHaveBeenReplaced=false;
 bool localCommandPolicyOpen=false,remoteMessagesAllowed=false,remoteExecutionPolicyOpen=false;
 bool allInputHeld=false,gameReportWhitelistVerified=false,physicalReleaseProven=false,osQueueDrained=false,saveAuthorized=false,roomReady=false;
 Lease lease{};std::uint64_t leasesIssued=0,leasesCompleted=0;
};
class Owner final {
public:
 Owner();~Owner()=delete;Owner(const Owner&)=delete;Owner&operator=(const Owner&)=delete;
 bool Initialize(const Config&)noexcept; // actual HWND thread only
 bool Request(const policy::Binding&,policy::State,std::uint64_t,bool&)noexcept;
 bool Rebind(const policy::Binding& oldBinding,const policy::Binding& nextBinding,std::uint64_t revision)noexcept;
 bool Acquire(const policy::Binding&,std::uint64_t revision,std::uint64_t sequence,Lease&)noexcept;
 bool Complete(const policy::Binding&,const Lease&)noexcept;
 bool Unknown(const policy::Binding&,const Lease&)noexcept;
 void Snapshot(Report&)noexcept;
private:struct Impl;Impl*p_;
};
}
