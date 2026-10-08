#include "b_reload_cold_registration.h"
#include "b_reload_lifecycle_bridge.h"
namespace b_reload_cold_registration {namespace {
struct State {volatile LONG once=0,attempt=0;b_reload_lifecycle::Config config{};Policy policy{};Report report{};b_reload_cold_registration_wait::Coordinator wait;const CheckpointLoadWorkerFrame* frame=nullptr;};State state;
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool original(void*) noexcept {++state.report.oldCalls;const bool ok=b_reload_lifecycle::RegisterColdPool(state.frame);b_reload_root_activation::Snapshot(state.report.activation);unsigned pools=0,unowned=0;b_reload_lifecycle::WorkerStatistics(pools,unowned);state.report.registered=pools;return ok&&pools==1&&!unowned&&state.report.activation.threads==4&&state.report.activation.initialWaitVerified==4&&state.report.activation.error==b_reload_root_activation::Error::None&&!state.report.activation.uncertain;}
}
bool Prepare(const b_reload_lifecycle::Config&c,const Policy&p) noexcept {
 if(InterlockedCompareExchange(&state.once,1,0))return false;
 state.config=c;state.policy=p;state.report.base=c.base;state.report.provider=uintptr_t(c.provider);
 if(!c.provider||!c.base||!p.producerLock||!p.taskStarts||!p.threadStart||p.deadlineMs<1||p.deadlineMs>10000){state.report.error=Error::Config;return false;}
 if(!b_reload_lifecycle::Initialize(c)){state.report.error=Error::Initialize;return false;}state.report.prepared=1;return true;
}
bool Register(const CheckpointLoadWorkerFrame*f) noexcept {
 if(InterlockedCompareExchange(&state.attempt,1,0))return false;state.report.attempts=1;
 __try {CheckpointLoadWorkerOwner owner{};const auto b=state.config.base,pool=b+0x1A24DA0;
  if(!state.report.prepared||!f||!BReloadLifecycleCurrentOwner(&owner)||owner.slot!=0||owner.owner_depth!=1||owner.current_depth!=1||owner.token!=pool||owner.call_id!=f->call_id||owner.thread_id!=GetCurrentThreadId()||f->thread_id!=GetCurrentThreadId()||f->args[0]!=pool||at<uintptr_t>(f->caller_entry_rsp)!=b+0x1447BB){state.report.error=Error::Owner;return false;}
  b_reload_root_activation::Report a{};b_reload_root_activation::Snapshot(a);unsigned pools=0,unowned=0;b_reload_lifecycle::WorkerStatistics(pools,unowned);
  if(!a.initialized||!a.published||a.threads||a.taskCount||a.outerBefore||a.error!=b_reload_root_activation::Error::None||a.uncertain||pools||unowned){state.report.error=Error::Binding;return false;}
  b_reload_cold_registration_wait::Config c{};c.base=b;c.producerLock=state.policy.producerLock;c.taskStarts=state.policy.taskStarts;c.deadlineMs=state.policy.deadlineMs;
  for(unsigned i=0;i<4;++i){const auto control=pool+0x10+uintptr_t(i)*0x80,object=at<uintptr_t>(control);c.workers[i]={object,control,at<DWORD>(object+0x10),state.policy.threadStart};}
  state.frame=f;const bool ok=state.wait.Run(c,original,nullptr);state.frame=nullptr;state.report.wait=state.wait.Snapshot();
  if(!ok)state.report.error=state.report.oldCalls?Error::Registration:Error::Wait;return ok;
 }__except(EXCEPTION_EXECUTE_HANDLER){state.frame=nullptr;state.report.error=Error::Exception;return false;}
}
const Report& Snapshot() noexcept {return state.report;}
}
namespace b_reload_lifecycle {bool CoordinatedRegisterColdPool(const CheckpointLoadWorkerFrame*f) noexcept {return b_reload_cold_registration::Register(f);}}
