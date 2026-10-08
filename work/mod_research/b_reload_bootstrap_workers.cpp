#include "b_reload_bootstrap_workers.h"
namespace b_reload_bootstrap_workers {
namespace { struct Runtime {checkpoint_native_task_provider::Provider provider;};Runtime runtime; }
bool InitializeAndArm(const BReloadLifecycleBootstrapInfo&i) noexcept {return b_reload_bootstrap::InitializeAndArm(i,runtime.provider);}
void Snapshot(b_reload_bootstrap::Report&b,b_reload_lifecycle::Report&l,b_reload_root_activation::Report&a) noexcept {
b_reload_bootstrap::Snapshot(b);b_reload_lifecycle::Snapshot(l);b_reload_root_activation::Snapshot(a);
}
}
