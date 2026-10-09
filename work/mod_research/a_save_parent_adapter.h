#pragma once
#include "a_save_dispatch_host.h"
#include "b_reload_parent_bridge.h"
// Role-A-only source binding. Uses the frozen two-slot parent ABI bank; NEVER
// combine with B parent source in the same module or stack two source owners.
// Creates a plan, not an installer. No remote/native scheduler invocation API.
namespace a_save_parent_adapter {
bool CurrentBoundary(uintptr_t base)noexcept; // Only adapter-owned control call, never scheduler body.
enum class Error:unsigned {None,Config,Source,Bridge,Publish,Thread,Order,Initialize,Host,Abnormal,Stopped};
struct Config {planning_input_interlock::Config planning{};planning_input_interlock::Controller*controller=nullptr;
 a_save_dispatch_mailbox::Mailbox*mailbox=nullptr;a_save_dispatch_host::Host*host=nullptr;SRWLOCK*producer=nullptr;std::uint64_t readyRevision=1;};
struct Plan {uintptr_t site=0,relay=0;unsigned char before[5]{},after[5]{};};
struct Report {Error error=Error::None;DWORD hostThread=0;unsigned initialized=0,armed=0,hostInitialized=0,stopped=0;
 std::uint64_t before=0,after=0,finally=0,active=0,abnormal=0,hostBefore=0,hostAfter=0,lastCall=0;
 bool installsSources=false,allWritersProven=false,productionPermit=false;};
class Adapter final {
public:
 bool Initialize(const Config&)noexcept;bool PreparedPlan(Plan&)noexcept;bool Arm()noexcept;
 void Stop()noexcept;void Snapshot(Report&)noexcept;
private:
 Config c_{};Plan p_{};Report r_{};SRWLOCK lock_=SRWLOCK_INIT;volatile LONG once_=0,armed_=0,stopped_=0;
 bool sources(bool raw)noexcept;bool prepare()noexcept;bool initializeHost()noexcept;
 void fail(Error)noexcept;static void before(const CheckpointLoadWorkerFrame*,void*)noexcept;
 static void after(const CheckpointLoadWorkerFrame*,void*)noexcept;
 static void finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*)noexcept;
};
}
