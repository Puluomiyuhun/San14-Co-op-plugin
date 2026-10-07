#pragma once
#include "checkpoint_native_input_hwbp.h"
// ABI-compatible provider successor. One permanent VEH, immutable per-Context
// state, and per-thread active routing. No retry/reset/unload or game installer.
namespace checkpoint_persistent_input_hwbp {
using Binding=checkpoint_native_input_hwbp::Binding;
using PendingReport=checkpoint_native_input_hwbp::PendingReport;
using CaptureKind=checkpoint_native_input_hwbp::CaptureKind;
using Error=checkpoint_native_input_hwbp::Error;
using Observe=checkpoint_native_input_hwbp::Observe;
using Config=checkpoint_native_input_hwbp::Config;
using HardwareReceipt=checkpoint_native_input_hwbp::HardwareReceipt;
using Context=checkpoint_native_input_hwbp::Context;
using Provider=checkpoint_native_input_hwbp::Provider;
struct RuntimeReport {
    unsigned initializeAttempts=0,handlerRegistrations=0,modulePinned=0,ready=0,failed=0;
    DWORD osError=0;
    std::uint64_t allocatedContexts=0;
    bool nativeSchedulerFence=false,productionAdmission=false;
};
// Context must be zero-initialized, address-stable and retained until exit.
// Even invalid initialization consumes that Context; create a fresh one instead.
// Copying a Context's opaque pointer does not create a valid second handle.
bool Initialize(Context&,const Config&) noexcept;
bool Begin(Context&,Observe,void*,const Binding&,std::uint64_t,const void*) noexcept;
void Finish(Context&) noexcept;
void Stop(Context&) noexcept;
bool Snapshot(const Context&,HardwareReceipt&) noexcept;
Provider MakeProvider(Context&) noexcept;
void SnapshotRuntime(RuntimeReport&) noexcept;
#ifdef CHECKPOINT_PERSISTENT_INPUT_HWBP_FIXTURE
void FixtureHelperDelay(DWORD) noexcept;
#endif
}
