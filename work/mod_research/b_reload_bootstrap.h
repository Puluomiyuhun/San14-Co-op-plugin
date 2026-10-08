#pragma once
#include "b_reload_lifecycle_loader.h"
#include "b_reload_lifecycle.h"
namespace b_reload_bootstrap {
enum class Error:unsigned {None,Once,Metadata,Primary,Threads,Source,Pool,Pin,Initialize,Plan,Publish,Arm,Resume,Exception};
struct Report {Error error=Error::None;DWORD osError=0;unsigned attempts=0,primaryHeld=0,threadSetVerified=0,sourcesReady=0,modulePinned=0,initialized=0,planPrepared=0,callWritten=0,protectionRestored=0,armed=0,primaryStillHeld=0,uncertain=0;uintptr_t image=0;DWORD primary=0; b_reload_lifecycle::Report lifecycle{};b_reload_root_activation::Report activation{};bool roomReady=false,fullWorld=false,gameLaunchVerified=false,workersStarted=false;};
// Startup-only trusted loader contract: primary already suspended once at its
// original PE entry, no other process threads besides this export caller. No
// running-thread attach, loader-lock call, reset, unload or retry after attempt.
// Caller retains Provider and DLL. Source bytes must already be available; this
// interface does not unpack, reconstruct, wait for or invent a runtime profile.
bool InitializeAndArm(const BReloadLifecycleBootstrapInfo&,checkpoint_native_task_provider::Provider&)noexcept;
void Snapshot(Report&)noexcept;
}
