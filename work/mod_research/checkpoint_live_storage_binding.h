#pragma once
#include "native_storage_read_core.h"

// In-process, cached v014 binding only. No ContextInit/Steam calls, discovery,
// hook publication, path fallback or native-load authority. Noncopyable and
// process-lifetime stable after exposing Api(); approved modules are PINned.
namespace checkpoint_live_storage_binding {
enum class Error : LONG { None, AlreadyUsed, Config, Attachment, Owner, Module,
    ModuleFile, ModuleHeader, Page, Code, Token, Generation, Storage, Vtable,
    Method, ReadSlot, HookOwner, Memory, Invalidated, Reentrant };
enum class Point : unsigned { Open, Validate };
struct Attachment {
    DWORD pid=0; std::uint64_t birth=0, attempt=0, generation=0;
    std::uintptr_t base=0; unsigned char id[32]{}, gameSha256[32]{};
};
struct ModuleApproval {
    std::uintptr_t base=0; std::uint32_t sizeOfImage=0, timestamp=0;
    wchar_t path[1024]{}; std::uint64_t fileSize=0;
    unsigned char fileSha256[32]{}, headerSha256[32]{}; // first 4096 mapped bytes
};
struct Endpoint {
    std::uintptr_t address=0; unsigned moduleIndex=0;
    unsigned char first32[32]{};
};
struct Config {
    Attachment attachment{};
    ModuleApproval modules[3]{}; unsigned moduleCount=0;
    Endpoint contextInit{}, exists{}, size{}, read{};
    std::uintptr_t storage=0, vtable=0, counter=0;
    unsigned vtableModuleIndex=0, counterModuleIndex=0;
    std::uint64_t cachedGeneration=0;
    unsigned char contextCode[0x65]{}; // exact fresh captured initialized code
    // Optional additional owned bridge. Never becomes Api.read or the immutable
    // native original. Its module/32-byte prefix is approved like all endpoints.
    Endpoint ownedReadBridge{};
    bool (*checkOwner)(void*,const Attachment&,Point) noexcept=nullptr;
    bool (*checkOwnedReadBridge)(void*,std::uintptr_t slot,
        std::uintptr_t original,std::uintptr_t bridge) noexcept=nullptr;
    void* owner=nullptr;
};
struct Report {
    Error error=Error::None; DWORD exceptionCode=0, osError=0;
    unsigned opened=0, invalidated=0, validationCalls=0, modulesPinned=0;
    unsigned readSlotWasOwnedBridge=0, fixtureBuild=0;
    std::uintptr_t holder=0, storage=0, vtable=0, originalRead=0, counter=0;
    std::uint64_t cachedGeneration=0;
    // Literal capabilities of this adapter, not claims about its caller.
    unsigned contextInitCalls=0, steamCalls=0, hookWrites=0, loadAuthorized=0;
};
class Context {
public:
    Context()=default;
    Context(const Context&)=delete;
    Context& operator=(const Context&)=delete;
    bool Open(const Config&) noexcept;
    bool Valid() noexcept;
    native_storage_read::Api Api() noexcept;
    void Invalidate() noexcept;
    void Snapshot(Report&) const noexcept;
private:
    Config config_{}; native_storage_read::Api api_{};
    mutable SRWLOCK reportLock_=SRWLOCK_INIT; Report report_{};
    volatile LONG once_=0, active_=0, validating_=0;
    bool fail(Error,DWORD exception=0,DWORD os=0) noexcept;
    bool inspect(Point) noexcept;
    bool module(unsigned,bool open) noexcept;
    bool endpoint(const Endpoint&) noexcept;
    static bool Validate(void*) noexcept;
};
}
