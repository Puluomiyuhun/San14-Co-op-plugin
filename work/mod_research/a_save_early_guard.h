#pragma once
#include "checkpoint_native_input_pending_adapter.h"

// A read-only, negative admission check for ONE actual early User write path.
// QuietReportsObserved is not a save permit, input lock, or complete world proof.
namespace a_save_early_guard {
using Binding=checkpoint_native_input_pending::Binding;
enum class Decision:unsigned {NotInitialized,Retired,Binding,Source,Unreadable,Identity,Phase,PendingUserReport,PendingReportQueue,QueueShape,Drift,QuietReportsObserved};
struct Config {uintptr_t base=0,root=0,world=0,user=0;Binding binding{};
#ifdef A_SAVE_EARLY_FIXTURE
 void(*betweenSamples)(void*)noexcept=nullptr;void*context=nullptr;
#endif
};
struct Report {
 Decision decision=Decision::NotInitialized;
 unsigned userFlag=0;std::uint64_t queuedReports=0;
 bool sourceChecked=false,twoSamplesEqual=false;
 // Always false, including after QuietReportsObserved.
 bool fullWriteExclusion=false,saveAuthorized=false,roomReady=false;
};
class Guard final {
public:
 Guard()=default;Guard(const Guard&)=delete;Guard&operator=(const Guard&)=delete;
 bool Initialize(const Config&)noexcept;
 Report Observe(const Binding&)noexcept;
 void Retire()noexcept;
private:
 Config c_{};volatile LONG used_=0,initialized_=0,retired_=0;
 bool sources()const noexcept;
};
}
