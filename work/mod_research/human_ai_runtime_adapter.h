#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "human_ai_runtime_subject.h"
namespace san14_ai_runtime {
using Wrapper=void(*)(void* manager,void* object);
struct HeldCall {Route route;void* manager;void* object;DWORD thread;Subject subject;};
// A Hold handler may block until repair and return to request a FULL re-read.
// Returning never authorizes bypass/native. Exceptions propagate through the
// intercepted call after adapter cleanup. It must not return on a timer alone.
using HoldHandler=void(*)(void*,const HeldCall&);
struct Config {Reader reader{};Address image=0,root=0;std::uint64_t human_mask=0;Wrapper original[4]{};HoldHandler hold=nullptr;void*hold_context=nullptr;};
struct Report {bool configured=false,installed=false;std::uint64_t entered[4]{},native[4]{},bypassed[4]{},held[4]{},active=0,exits=0,abnormal_exits=0;};
// One immutable configuration, never reset/unloaded. Must be configured before
// publishing any detour. original[] must be permanent unwind-safe trampolines;
// the four original code entry addresses themselves are deliberately rejected.
// This configures callable exports only: it never patches game code.
bool Configure(const Config&) noexcept;
void Snapshot(Report&) noexcept;
// Generic explicit thread-blocking fallback for own-process tests or deliberate
// diagnostic use. NOT a native game pause; holding the render thread can freeze
// its UI. No timeout, cancel-as-success or automatic native fallback exists.
class BlockingHold {
public:
 static void Wait(void*,const HeldCall&);
 void RequestRetry() noexcept;
 unsigned Waiting() noexcept;
private:
 SRWLOCK lock_=SRWLOCK_INIT;CONDITION_VARIABLE condition_=CONDITION_VARIABLE_INIT;
 std::uint64_t epoch_=0;unsigned waiting_=0;
};
}
extern "C" __declspec(dllexport) void HumanAiForceEntry(void*,void*);
extern "C" __declspec(dllexport) void HumanAiDistrictEntry(void*,void*);
extern "C" __declspec(dllexport) void HumanAiArmyEntry(void*,void*);
extern "C" __declspec(dllexport) void HumanAiGroupEntry(void*,void*);
extern "C" __declspec(dllexport) bool HumanAiRuntimeConfigure(const san14_ai_runtime::Config*) noexcept;
extern "C" __declspec(dllexport) void HumanAiRuntimeSnapshot(san14_ai_runtime::Report*) noexcept;
