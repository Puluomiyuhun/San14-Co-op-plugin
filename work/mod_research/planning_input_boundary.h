#pragma once
#include "planning_input_interlock.h"
// Retained HWND message boundary, never an additional Game/User Owner.
// Initialize on the target window's own thread. Request only on the existing
// Controller's execution thread. Requires a trusted sole WndProc publisher;
// it cannot exclude an unrelated concurrent SetWindowLongPtr writer.
// No discovery, injection or input synthesis.
namespace planning_input_boundary {
enum class Error:unsigned {None,Config,Identity,Thread,Source,Publish,Conflict,Post,Destroyed,Exception};
struct Config {planning_input_interlock::Controller*controller=nullptr;uintptr_t base=0;HWND window=nullptr;};
struct Report {
 Error error=Error::None;DWORD process=0,windowThread=0,ownerThread=0;
 UINT controlMessage=0;unsigned callbackSlot=0;std::uint64_t ticket=0,revision=0,acknowledgedRevision=0,active=0,finally=0;
 std::uint64_t auditedSuppressed=0,auditedForwarded=0,lifecycleForwarded=0,uncoveredForwarded=0,unclassifiedForwarded=0,controlCalls=0,ignoredControl=0;
 bool initialized=false,installed=false,requested=false,acknowledged=false,held=false,uncertain=false,destroyed=false;
 bool auditedSuppressionObserved=false,retired=false,retirementAcknowledged=false;
 // Win32 SetWindowLongPtr has no CAS. A post-write mismatch is uncertain and
 // may ALREADY have replaced an external publisher. No compensating overwrite.
 bool publicationConflict=false,foreignSourceMayHaveBeenReplaced=false;
 // All remain false: Win32 message delivery is not physical release or complete
 // OS queue drainage, and this classifier explicitly leaves messages uncovered.
 bool fullWindowInputHeld=false,allInputHeld=false,physicalReleaseProven=false,osQueueDrained=false,roomReady=false,saveAuthorized=false,nativeGameplayEnabled=false;
};
class Boundary final {
public:
 Boundary();~Boundary()=delete;Boundary(const Boundary&)=delete;Boundary&operator=(const Boundary&)=delete;
 bool Initialize(const Config&)noexcept;
 // Only a matching *observed* local Controller fence can close this boundary.
 // Return means queued, never acknowledged. Identical revisions are idempotent.
 // No native/control callback takes any Controller/Owner/Gate lock.
 bool Request(bool held,std::uint64_t revision,bool&duplicate)noexcept;
 bool Retire(std::uint64_t releasedRevision,bool&duplicate)noexcept;
 void Snapshot(Report&)noexcept;
private:struct Impl;Impl*p_;
};
}
