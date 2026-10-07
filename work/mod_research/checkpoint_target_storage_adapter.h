#pragma once
#include "native_storage_read_core.h"
#include "checkpoint_target_metadata_core.h"

// A caller-scoped binding to the already installed Steam v014 interface.
// This does not create a game serialization fence. The caller must supply the
// actual permitted callback boundary and invalidate it before leaving.
namespace checkpoint_target_storage {
using CheckBoundary = bool(*)(void*) noexcept;
class Context {
public:
    bool Open(uintptr_t base, CheckBoundary check, void* owner) noexcept;
    bool Valid() const noexcept;
    void Invalidate() noexcept { active_=false; }
    const native_storage_read::Api& Api() const noexcept { return api_; }
    checkpoint_target_metadata::Presence Presence(const char* name) noexcept;
    bool SlotName(unsigned slot, char out[16]) noexcept;
    uintptr_t Holder() const noexcept { return holder_; }
    uintptr_t Vtable() const noexcept { return vtable_; }
    unsigned ContextCalls() const noexcept { return contextCalls_; }
    unsigned PresenceCalls() const noexcept { return presenceCalls_; }
    unsigned FormatterCalls() const noexcept { return formatterCalls_; }
private:
    static bool Validate(void*) noexcept;
    uintptr_t base_=0,contextInit_=0,holder_=0,storage_=0,vtable_=0;
    CheckBoundary check_=nullptr;
    void* owner_=nullptr;
    native_storage_read::Api api_{};
    bool attempted_=false,active_=false;
    unsigned contextCalls_=0,presenceCalls_=0,formatterCalls_=0;
};
}
