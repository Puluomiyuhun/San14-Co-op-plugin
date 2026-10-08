#pragma once
#include "b_reload_bootstrap.h"
// One retained DLL owner; this API does not create or replace its Provider.
namespace b_reload_bootstrap_workers {
bool InitializeAndArm(const BReloadLifecycleBootstrapInfo&) noexcept;
void Snapshot(b_reload_bootstrap::Report&,b_reload_lifecycle::Report&,b_reload_root_activation::Report&) noexcept;
}
