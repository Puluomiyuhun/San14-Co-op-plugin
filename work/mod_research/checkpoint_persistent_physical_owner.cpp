#include "checkpoint_persistent_physical_owner.h"
namespace checkpoint_persistent_physical_owner {
namespace {
void bootstrapBefore(const CheckpointLoadWorkerFrame*,void*) {}
void bootstrapAfter(const CheckpointLoadWorkerFrame*,void*) {}
void bootstrapFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) {}
void* entry(unsigned i) noexcept {
    void* p[]={reinterpret_cast<void*>(&CheckpointPersistentBridge0),reinterpret_cast<void*>(&CheckpointPersistentBridge1),reinterpret_cast<void*>(&CheckpointPersistentBridge2),reinterpret_cast<void*>(&CheckpointPersistentBridge3),reinterpret_cast<void*>(&CheckpointPersistentBridge4),reinterpret_cast<void*>(&CheckpointPersistentBridge5)};return i<6?p[i]:nullptr;
}
bool bridge(void* p) noexcept {for(unsigned i=0;i<6;++i)if(p==entry(i))return true;return false;}
bool residentCode(void* p) noexcept {
    MEMORY_BASIC_INFORMATION m{};HMODULE module=nullptr;
    if(!p||VirtualQuery(p,&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||m.Type!=MEM_IMAGE||
       (m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_READWRITE&&m.Protect!=PAGE_EXECUTE_WRITECOPY&&m.Protect!=PAGE_EXECUTE))return false;
    return GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(p),&module)!=FALSE;
}
[[maybe_unused]] bool generation(const checkpoint_persistent_route::Generation& g) noexcept {
    return g.id&&g.context&&g.before&&g.after&&g.finally&&
        residentCode(reinterpret_cast<void*>(g.before))&&residentCode(reinterpret_cast<void*>(g.after))&&residentCode(reinterpret_cast<void*>(g.finally));
}
}
bool Owner::fail(Error e,DWORD x) noexcept {if(report_.error==Error::None)report_.error=e;if(x)report_.exception=x;InterlockedExchange(&stopped_,1);return false;}
bool Owner::guard(Point p,unsigned i) noexcept {
    __try{return config_.validate&&config_.validate(config_.context,p,i);}
    __except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Owner::Install(const Config& supplied) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    bool ok=false;AcquireSRWLockExclusive(&lock_);
    __try {__try {
        config_=supplied;
        if(!config_.validate||!config_.context){fail(Error::Config);__leave;}
        HMODULE module=nullptr;
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&CheckpointPersistentBridgeConfigure),&module)){fail(Error::Pin);__leave;}
        report_.pinned=1;
        for(unsigned i=0;i<6;++i){
            const auto& b=config_.hooks[i];auto target=i||!config_.userForward?b.original:config_.userForward;
            if(!b.slot||b.hook!=entry(i)||bridge(b.original)||bridge(target)||!residentCode(b.original)||!residentCode(target)){fail(Error::Config);__leave;}
            for(unsigned j=0;j<i;++j)if(config_.hooks[j].slot==b.slot){fail(Error::Config);__leave;}
            CheckpointPersistentBridgeStats s{};if(!CheckpointPersistentBridgeSnapshot(i,&s)||s.configured){fail(Error::ExistingBridge);__leave;}
            report_.original[i]=uintptr_t(b.original);report_.forward[i]=uintptr_t(target);
        }
        if(!guard(Point::BeforeConfigure,0)){fail(Error::Guard);__leave;}
        checkpoint_persistent_route::Config route{};route.initial={1,bootstrapBefore,bootstrapAfter,bootstrapFinally,this};
#ifdef CHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE
        route.allowOfflineTransitions=true;
#endif
        if(!router_.Initialize(route)||!adapter_.Initialize(router_)){fail(Error::Router);__leave;}
        if(!hooks_.Initialize(config_.hooks,6)){fail(Error::HookSet);__leave;}
        report_.initialized=1;
        // Configure every forwarding target before publishing the first slot.
        // A failed attempt is terminal; permanent bridge configs are not reset.
        for(unsigned i=0;i<6;++i){auto c=adapter_.Configuration(reinterpret_cast<void*>(report_.forward[i]));if(!CheckpointPersistentBridgeConfigure(i,&c)){fail(Error::Configure);__leave;}++report_.configured;}
        for(unsigned i=0;i<6;++i){
            if(InterlockedCompareExchange(&stopped_,0,0)||!guard(Point::BeforePublish,i)){fail(Error::Guard);__leave;}
            ++report_.publicationAttempts;
            if(!hooks_.Publish(i)){report_.publicationUncertain=true;fail(Error::Publish);__leave;}
            ++report_.published;report_.hooksRetained=true;
            if(!guard(Point::AfterPublish,i)){fail(Error::Guard);__leave;}
        }
        if(!verifyLocked())__leave;
        report_.installed=1;ok=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());}}
    __finally{ReleaseSRWLockExclusive(&lock_);}
    // No owner-wide restore/unload on failure. The frozen Set::Publish may roll
    // back its CURRENT failed slot, including a briefly published entry. Hence
    // all bridge configurations/context remain resident even when the successful
    // publication count is zero. Earlier successful slots remain installed.
    return ok;
}
bool Owner::verifyLocked() noexcept {
    __try {
        checkpoint_load_hook_set::Report h{};hooks_.Snapshot(h);
        if(!h.initialized||h.count!=6)return fail(Error::Drift);
        for(unsigned i=0;i<6;++i){const auto& e=h.entries[i];MEMORY_BASIC_INFORMATION m{};
            if(!e.published||e.dirty||e.restored||*config_.hooks[i].slot!=entry(i)||
                VirtualQuery(const_cast<void**>(config_.hooks[i].slot),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||m.Protect!=e.protection)return fail(Error::Drift);
        }
        if(!guard(Point::Verify,0))return fail(Error::Guard);
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Owner::Verify() noexcept {
    bool ok=false;AcquireSRWLockExclusive(&lock_);
    __try{ok=report_.installed&&report_.error==Error::None&&verifyLocked();}__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Owner::PublishForOfflineExercise(std::uint64_t expected,const checkpoint_persistent_route::Generation& g) noexcept {
    bool ok=false;AcquireSRWLockExclusive(&lock_);
    __try {
#ifdef CHECKPOINT_PERSISTENT_PHYSICAL_OWNER_FIXTURE
        checkpoint_persistent_route::Report r{};router_.Snapshot(r);
        if(report_.installed&&report_.error==Error::None&&!InterlockedCompareExchange(&stopped_,0,0)&&
           generation(g)&&!r.active&&verifyLocked())ok=router_.PublishForOfflineExercise(expected,g);
#else
        (void)expected;(void)g;
#endif
        if(!ok)++report_.rejectedTransitions;
    }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Owner::Stop() noexcept {InterlockedExchange(&stopped_,1);}
void Owner::Snapshot(Report& out) noexcept {
    AcquireSRWLockShared(&lock_);
    __try{out=report_;out.stopped=InterlockedCompareExchange(&stopped_,0,0)!=0;hooks_.Snapshot(out.hooks);router_.Snapshot(out.route);out.routeFaults=adapter_.Faults();for(unsigned i=0;i<6;++i)CheckpointPersistentBridgeSnapshot(i,&out.bridges[i]);}
    __finally{ReleaseSRWLockShared(&lock_);}
}
}
