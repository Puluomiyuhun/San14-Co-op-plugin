#pragma once
#include <windows.h>
#include <cstdint>
namespace b_reload_cold_wait {
enum class Error:unsigned {None,Config,Reused,Source,Binding,Thread,Event,Context,Warm,TaskStarted,Deadline,Callback,Exception,Resume};
struct Worker {uintptr_t object=0,control=0;DWORD thread=0;uintptr_t threadStart=0;};
// Trusted in-process host only. Every producer must acquire this lock shared
// BEFORE touching a worker/event, and increment taskStarts before dispatch.
// The component cannot discover or exclude producers that bypass this contract.
struct Config {uintptr_t base=0;Worker workers[4]{};SRWLOCK* producerLock=nullptr;volatile LONG* taskStarts=nullptr;DWORD deadlineMs=1000,pollMs=2;};
struct Report {Error error=Error::None;DWORD osError=0;unsigned attempts=0,rounds=0,suspends=0,resumes=0,initialWaitVerified=0,pending=0,callbackCalls=0,uncertain=0;ULONGLONG elapsedMs=0;uintptr_t waitService=0,lastRip[4]{};unsigned warm[4]{};};
using Continuation=bool(*)(void*) noexcept;
class Coordinator final {
 volatile LONG once_=0;Report report_{};
public:
 Coordinator()=default;Coordinator(const Coordinator&)=delete;Coordinator& operator=(const Coordinator&)=delete;
 // One attempt, including failure. All suspension increments are restored before
 // the callback, which runs on this thread under producerLock exclusive.
 // The callback still must perform actual RegisterColdPool/lifecycle validation.
 bool Run(const Config&,Continuation,void*) noexcept;
 const Report& Snapshot() const noexcept {return report_;} // serialized host only
};
}
