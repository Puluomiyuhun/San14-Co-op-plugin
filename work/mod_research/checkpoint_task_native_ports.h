#pragma once
#include "checkpoint_native_task_provider.h"
// Actual per-current-thread execute breakpoints. Initial scope is the embedded
// Load runner only. No discovery, foreign-thread installer or native driver.
namespace checkpoint_task_native_ports {
enum class Error:unsigned {None,Config,Occupied,Debugger,Thread,Helper,Suspend,Context,Publish,Resume,Deadline,Conflict,Restore,Order,Binding,Provider,Exception,Stopped,Missing};
struct Config {checkpoint_native_task_provider::Provider* provider=nullptr;uintptr_t base=0;std::uint64_t generation=0;DWORD helperDeadlineMs=1000;};
struct Sample {uintptr_t rip=0;DWORD thread=0,rawFlags=0;std::uint64_t gpr[16]{};unsigned char xmm[256]{};DWORD mxcsr=0;bool delivered=false,accepted=false;};
struct Report {
    Error error=Error::None;DWORD osError=0,exceptionCode=0,thread=0;
    std::uint64_t generation=0;uintptr_t control=0,callable=0,threadObject=0;
    unsigned entered=0,captured=0,finished=0,restored=0,uncertain=0,deadlineExceeded=0,stopped=0,providerScopeAbandoned=0;
    std::uint64_t originalDr[6]{},restoredDr[6]{};Sample samples[4]{};
    bool codeUnchanged=false,modulePinned=false,gameInstaller=false,productionPublication=false,globalFence=false;
};
// Context identity/address and all backing state are retained until process
// exit. One use only; module/VEH stay pinned. Maximum 64 process contexts.
struct Context {void* volatile opaque=nullptr;};
bool Initialize(Context&,const Config&) noexcept;
bool Begin(Context&) noexcept;
void Finish(Context&) noexcept;
void Stop(Context&) noexcept;
bool Snapshot(const Context&,Report&) noexcept;
}
