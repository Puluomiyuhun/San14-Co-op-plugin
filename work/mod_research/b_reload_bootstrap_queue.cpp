#include "b_reload_bootstrap_queue.h"
namespace b_reload_bootstrap_queue {
bool Runtime::InitializeAndArm(const BReloadLifecycleBootstrapInfo&i) noexcept {if(bootAttempted_)return false;bootAttempted_=true;image_=i.imageBase;bootArmed_=b_reload_bootstrap::InitializeAndArm(i,provider_);return bootArmed_;}
bool Runtime::OpenFirst(const checkpoint_native_task_provider::Config&c) noexcept {
 b_reload_bootstrap::Report b{};b_reload_lifecycle::Report l{};b_reload_root_activation::Report a{};
 b_reload_bootstrap::Snapshot(b);b_reload_lifecycle::Snapshot(l);b_reload_root_activation::Snapshot(a);
 if(!bootArmed_||b.image!=image_||c.base!=image_||!a.published||firstAttempted_||!b.armed||b.uncertain||l.error!=b_reload_lifecycle::Error::None||l.abnormal||l.entered!=1||l.returned!=1||l.finally!=1||l.coldPools!=1||a.threads!=4||a.initialWaitVerified!=4||a.error!=b_reload_root_activation::Error::None||a.uncertain)return false;
 host_=GetCurrentThreadId();firstAttempted_=true;firstOpened_=provider_.Register(c)&&provider_.OpenWindow(c.generation.callbacks.id);return firstOpened_;
}
bool Runtime::BindCompleted(std::uint64_t g,checkpoint_dynamic_native_session::Session&s,checkpoint_persistent_authorized::Controller&c) noexcept {
 if(!firstOpened_||bound_||GetCurrentThreadId()!=host_)return false;
 bound_=next_->Initialize(provider_,g,s,c);return bound_;
}
bool Runtime::OpenNext(const checkpoint_native_task_provider::Config&c) noexcept {return bootArmed_&&c.base==image_&&bound_&&GetCurrentThreadId()==host_&&next_->RegisterAndOpen(c);}
void Runtime::Snapshot(b_reload_bootstrap::Report&b,b_reload_lifecycle::Report&l,b_reload_root_activation::Report&a,b_reload_lifecycle_fault_guard::Report&g) noexcept {
 b_reload_bootstrap::Snapshot(b);b_reload_lifecycle::Snapshot(l);b_reload_root_activation::Snapshot(a);next_->Snapshot(g);
}
}
