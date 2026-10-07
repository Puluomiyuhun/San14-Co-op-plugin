#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>

// Six fixed pointer slots for User/Menu/Game/Load and worker/FileRead.
// Own module/config/originals must already be pinned. This is not a scheduler
// fence and RestoreAll does not imply previously entered callbacks have drained.
namespace checkpoint_load_hook_set {
constexpr unsigned Capacity=6;
struct Binding {void* volatile* slot=nullptr;void* original=nullptr;void* hook=nullptr;};
struct Entry {
    Binding binding{};DWORD protection=0,lastProtection=0,error=0;
    bool known=false,dirty=false,published=false,restored=false;
    std::uintptr_t observed=0;
};
struct Report {unsigned count=0;bool initialized=false;Entry entries[Capacity]{};DWORD exceptionCode=0;};
class Set {
public:
    bool Initialize(const Binding*,unsigned) noexcept;
    bool Publish(unsigned) noexcept;
    bool Restore(unsigned) noexcept;
    bool RestoreAll() noexcept;
    void Snapshot(Report&) noexcept;
private:
    SRWLOCK lock_=SRWLOCK_INIT;volatile LONG once_=0;
    Report report_{};
    bool restoreLocked(unsigned) noexcept;
};
}
