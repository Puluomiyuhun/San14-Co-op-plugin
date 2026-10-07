#include "b_reload_title_source.h"
#include "checkpoint_task_completion_profile.h"
#include <cstring>
#include <new>

namespace b_reload_title_source {
namespace {
constexpr uintptr_t Slot=0x12DAAF0+0x28,Update=0x4AA7B0,Join=0x4F7050;
volatile LONG processOwner=0;
struct State {
    Config config{};
    Report report{};
    checkpoint_load_hook_set::Set hooks;
    SRWLOCK lock=SRWLOCK_INIT;
};
void fail(State& s,Error e) {if(s.report.error==Error::None)s.report.error=e;}
bool range(uintptr_t p,size_t n,uintptr_t image,bool code) {
    if(!p||!n||p>UINTPTR_MAX-n)return false;
    const auto end=p+n;
    while(p<end) {
        MEMORY_BASIC_INFORMATION m{};
        if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT)return false;
#ifndef B_RELOAD_TITLE_SOURCE_FIXTURE
        if(m.Type!=MEM_IMAGE||uintptr_t(m.AllocationBase)!=image)return false;
#else
        (void)image;
#endif
        if(code) {
            if(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY)return false;
        } else if(m.Protect!=PAGE_READONLY&&m.Protect!=PAGE_WRITECOPY)return false;
        const auto next=uintptr_t(m.BaseAddress)+m.RegionSize;
        if(next<=p)return false;
        p=next;
    }
    return true;
}
bool source(uintptr_t b,uintptr_t expected) noexcept {
    __try {
        return b&&b<UINTPTR_MAX-0x2200000&&
            range(b+Slot,8,b,false)&&range(b+Update,sizeof checkpoint_task_completion::TitleUpdateBytes,b,true)&&
            range(b+Join,sizeof checkpoint_task_completion::LoadJoinBytes,b,true)&&
            *reinterpret_cast<const uintptr_t*>(b+Slot)==expected&&
            !memcmp(reinterpret_cast<void*>(b+Update),checkpoint_task_completion::TitleUpdateBytes,sizeof checkpoint_task_completion::TitleUpdateBytes)&&
            !memcmp(reinterpret_cast<void*>(b+Join),checkpoint_task_completion::LoadJoinBytes,sizeof checkpoint_task_completion::LoadJoinBytes);
    } __except(EXCEPTION_EXECUTE_HANDLER) {return false;}
}
bool completionReady(const Config& c) {
    checkpoint_task_completion::Report r{};
    return c.firstGeneration&&c.firstGeneration->Snapshot(r)&&r.generation&&
        r.error==checkpoint_task_completion::Error::None&&!r.stopped&&!r.active;
}
bool bridgeReady(State& s) {
    CheckpointLoadWorkerBridgeStats r{};
    const bool ready=CheckpointLoadWorkerBridgeSnapshot(1,&r)&&r.configured&&r.module_pinned&&!r.cleanup_faults;
    s.report.modulePinned=r.module_pinned&&s.report.ownerModulePinned;
    return ready;
}
}
bool Owner::Initialize(const Config& c) noexcept {
    if(state_||!c.firstGeneration||!completionReady(c)||!source(c.base,c.base+Update))return false;
    auto* s=new(std::nothrow)State;
    if(!s)return false;
    s->config=c;s->report.base=c.base;s->report.slot=c.base+Slot;s->report.original=c.base+Update;
    s->report.replacement=uintptr_t(checkpoint_task_completion::Adapter::TitleEntry());
    if(InterlockedCompareExchange(&processOwner,1,0)){delete s;return false;}
    // The global once claim is never reset after any partial configuration.
    state_=s;
    HMODULE ownModule=nullptr;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
        reinterpret_cast<LPCWSTR>(&source),&ownModule)){fail(*s,Error::Bridge);return false;}
    s->report.ownerModulePinned=1;
    if(!checkpoint_task_completion::Adapter::ConfigureTitle(c.base)){fail(*s,Error::Bridge);return false;}
    s->report.bridgeConfigured=1;
    if(!bridgeReady(*s)){fail(*s,Error::Bridge);return false;}
    const checkpoint_load_hook_set::Binding binding{
        reinterpret_cast<void* volatile*>(s->report.slot),
        reinterpret_cast<void*>(s->report.original),reinterpret_cast<void*>(s->report.replacement)};
    if(!s->hooks.Initialize(&binding,1)){fail(*s,Error::Hooks);return false;}
    s->hooks.Snapshot(s->report.hooks);
    s->report.initialized=1;
    return true;
}
bool Owner::Publish() noexcept {
    auto* s=static_cast<State*>(state_);if(!s)return false;
    bool ok=false;AcquireSRWLockExclusive(&s->lock);
    __try {__try {
        if(s->report.stopped){fail(*s,Error::Stopped);__leave;}
        if(!s->report.initialized||s->report.error!=Error::None||s->report.publishAttempted)__leave;
        s->report.publishAttempted=1;
        if(!completionReady(s->config)){fail(*s,Error::Completion);__leave;}
        if(!source(s->config.base,s->report.original)){fail(*s,Error::Source);__leave;}
        if(!bridgeReady(*s)){fail(*s,Error::Bridge);__leave;}
        if(!s->hooks.Publish(0)){fail(*s,Error::Publication);__leave;}
        s->hooks.Snapshot(s->report.hooks);
        s->report.published=s->report.hooks.entries[0].published;
        if(!source(s->config.base,s->report.replacement)){fail(*s,Error::Verification);__leave;}
        s->report.verified=1;ok=true;
    } __except(EXCEPTION_EXECUTE_HANDLER) {s->report.exception=GetExceptionCode();fail(*s,Error::Exception);}}
    __finally {s->hooks.Snapshot(s->report.hooks);s->report.published=s->report.hooks.entries[0].published;ReleaseSRWLockExclusive(&s->lock);}
    return ok;
}
bool Owner::Verify() noexcept {
    auto* s=static_cast<State*>(state_);if(!s)return false;
    AcquireSRWLockExclusive(&s->lock);++s->report.verifyCalls;
    const bool ok=s->report.published&&s->report.error==Error::None&&bridgeReady(*s)&&source(s->config.base,s->report.replacement);
    s->report.verified=ok;if(!ok)fail(*s,Error::Verification);
    s->hooks.Snapshot(s->report.hooks);ReleaseSRWLockExclusive(&s->lock);return ok;
}
void Owner::Stop() noexcept {auto* s=static_cast<State*>(state_);if(!s)return;AcquireSRWLockExclusive(&s->lock);s->report.stopped=1;ReleaseSRWLockExclusive(&s->lock);}
bool Owner::Snapshot(Report& r) noexcept {auto* s=static_cast<State*>(state_);if(!s)return false;AcquireSRWLockShared(&s->lock);r=s->report;ReleaseSRWLockShared(&s->lock);return true;}
}
