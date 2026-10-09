#pragma once
#include "planning_checkpoint_save.h"
#include "a_save_dispatch_mailbox.h"
// Role A, trusted local coordinator. No native parent hook is installed here.
// The external producer lock is a HOST contract, not a discovered game lock.
// Every relevant producer and its lock order must be proven before game use.
namespace a_save_dispatch_host {
namespace mb=a_save_dispatch_mailbox;
enum class State:unsigned {Idle,Observing,Submitted,Complete,Stopped,Unknown};
struct Config {a_save_user_owner::Owner*owner=nullptr;a_save_upstream_gate::Owner*gate=nullptr;
 planning_input_interlock::Controller*controller=nullptr;mb::Mailbox*mailbox=nullptr;SRWLOCK*producer=nullptr;};
struct Report {State state=State::Idle;DWORD thread=0,lastReleaseThread=0;bool initialized=false,frame=false,lease=false;
 unsigned observations=0,submits=0,copies=0,releases=0;std::uint64_t serial=0;bool actualParentHook=false,allWritersProven=false,productionPermit=false;};
class Host final {
public:
 bool Initialize(const Config&)noexcept;
 bool BindPeriod(planning_input_interlock::Controller&)noexcept;
 // A false return NEVER instructs the caller to skip normal native dispatch.
 // Stopped committed Save callbacks must continue; call BeforeFrame again at
 // later quiet boundaries to drain, retaining Host/Owner/Gate/producer lifetime.
 // Both calls must originate on the established host thread, OUTSIDE all User,
 // Game and Save callbacks. The actual normal frame occurs BETWEEN the calls.
 bool BeforeFrame()noexcept;bool AfterFrame()noexcept;
 // Report is host-thread-only. Cancellation uses Mailbox::Stop on any thread.
 bool Snapshot(Report&)const noexcept;
 // No destructor releases a lease: unresolved native work must retain this
 // Host and all dependencies, then receive a proven host-thread drain boundary.
private:
 Config c_{};Report r_{};mb::Envelope pending_{};planning_checkpoint_save::Evidence evidence_{};
 std::uint64_t revision_=0;bool submitted_=false;
 bool quiet(a_save_user_owner::Report&)noexcept;void release()noexcept;
 bool stoppedBoundary()noexcept;
};
}
