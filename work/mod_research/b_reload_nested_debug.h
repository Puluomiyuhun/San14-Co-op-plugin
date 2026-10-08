#pragma once
#include <windows.h>
#include <cstdint>
// Internal cooperation contract. Never accepts arbitrary occupied DR layouts.
namespace checkpoint_native_task_provider {class Provider;}
namespace b_reload_nested_debug {
enum class Result {Absent,Granted,Refused};
struct Lease {void* owner=nullptr;std::uint64_t serial=0;DWORD thread=0;};
// Current Root worker only, after entry and before return; requests absolute
// execute addresses in freed slots 0 and 2. Slot 3 always observes Root yield.
Result Acquire(checkpoint_native_task_provider::Provider* provider,uintptr_t base,std::uint64_t generation,uintptr_t slot0,uintptr_t slot2,Lease&) noexcept;
Result AcquireInput(const void* user,std::uint64_t generation,uintptr_t site,Lease&) noexcept;
// Helper-thread validation while the target is suspended. Six registers use
// DR0,DR1,DR2,DR3,DR6,DR7 ordering; pending debug events are never erased.
bool Match(const Lease&,const std::uint64_t dr[6],bool childArmed) noexcept;
// Same original owner thread; only after exact original layout was restored.
bool Release(const Lease&) noexcept;
}
