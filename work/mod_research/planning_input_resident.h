#pragma once
#include "planning_period_owner.h"
// Single retained physical WndProc across same-world logical planning periods.
// Requires the same trusted sole publisher/bootstrap as boundary predecessor.
// All public calls except Initialize run serially on Controller's owner thread.
// Initialize runs on the HWND thread. Callback never samples Owner/Controller.
namespace planning_input_resident {
namespace pi=planning_input_interlock;namespace pp=planning_period_owner;
enum class Error:unsigned {None,Config,Identity,Thread,Source,Publish,Conflict,Post,Destroyed,Exception};
struct Config {pi::Controller*controller=nullptr;a_save_user_owner::Owner*owner=nullptr;
 pi::ar::ph::Binding binding{};uintptr_t base=0;HWND window=nullptr;};
struct Report {
 Error error=Error::None;DWORD process=0,windowThread=0,ownerThread=0;UINT controlMessage=0;unsigned callbackSlot=0;
 std::uint64_t ticket=0,revision=0,acknowledgedRevision=0,active=0,finally=0;
 std::uint64_t serial=0,period=0,epoch=0,handoffsAccepted=0,handoffsAcknowledged=0,publicationWrites=0;
 std::uint64_t auditedSuppressed=0,auditedForwarded=0,lifecycleForwarded=0,uncoveredForwarded=0,unclassifiedForwarded=0,controlCalls=0,ignoredControl=0;
 bool initialized=false,installed=false,requested=false,acknowledged=false,held=false,uncertain=false,destroyed=false;
 bool auditedSuppressionObserved=false,residentHold=false,handoffPending=false;
 bool publicationConflict=false,foreignSourceMayHaveBeenReplaced=false;
 bool fullWindowInputHeld=false,allInputHeld=false,physicalReleaseProven=false,osQueueDrained=false,roomReady=false,saveAuthorized=false,nativeGameplayEnabled=false;
};
class Boundary final {
public:
 Boundary();~Boundary()=delete;Boundary(const Boundary&)=delete;Boundary&operator=(const Boundary&)=delete;
 bool Initialize(const Config&)noexcept;
 bool Request(bool held,std::uint64_t revision,bool&duplicate)noexcept;
 // No WndProc restoration, release or reinstall occurs here. False does not
 // release the current physical hold. Same completed/pending handoff idempotent.
 bool Handoff(pi::Controller&next,const pi::ar::ph::Binding&nextBinding,
              std::uint64_t retiredSerial,std::uint64_t revision,bool&duplicate)noexcept;
 void Snapshot(Report&)noexcept;
private:struct Impl;Impl*p_;
};
}
