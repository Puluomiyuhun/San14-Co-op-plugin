// Title +590 role successor. Frozen Load-only router remains unchanged.
#include "b_reload_title590_router.h"
#include "checkpoint_task_native_ports_profile.h"
#include "checkpoint_task_native_activation_v2_profile.h"
#include <cstring>
namespace b_reload_title590_router {
namespace p=checkpoint_task_completion_worker_ports;
namespace {
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
bool code(uintptr_t b) noexcept {__try {MEMORY_BASIC_INFORMATION m{};
    if(!b||b>UINTPTR_MAX-0x2200000||VirtualQuery(reinterpret_cast<void*>(b+0x834D10),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
       uintptr_t(m.BaseAddress)+m.RegionSize<b+0x834D10+sizeof checkpoint_task_native_ports::RunnerBytes||
       (m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef CHECKPOINT_TASK_NATIVE_ACTIVATION_FIXTURE
    if(m.Type!=MEM_IMAGE)return false;
#endif
    if(memcmp(reinterpret_cast<void*>(b+0x834D10),checkpoint_task_native_ports::RunnerBytes,sizeof checkpoint_task_native_ports::RunnerBytes))return false;
    if(VirtualQuery(reinterpret_cast<void*>(b+0x83A930),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
       uintptr_t(m.BaseAddress)+m.RegionSize<b+0x83A930+sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes||
       (m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef CHECKPOINT_TASK_NATIVE_ACTIVATION_FIXTURE
    if(m.Type!=MEM_IMAGE)return false;
#endif
    return !memcmp(reinterpret_cast<void*>(b+0x83A930),checkpoint_task_native_activation_v2::ThreadEntryBytes,sizeof checkpoint_task_native_activation_v2::ThreadEntryBytes);
}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool nativeBinding(const CheckpointLoadWorkerFrame&f,uintptr_t base,const checkpoint_native_task_provider::Role&r,uintptr_t&caller) noexcept {
    __try {caller=*reinterpret_cast<const uintptr_t*>(f.caller_entry_rsp);
        return caller==base+0x83A9DF&&f.thread_id==GetCurrentThreadId()&&f.args[0]==r.threadObject&&f.args[1]==r.control&&
          *reinterpret_cast<const uintptr_t*>(r.threadObject+0x30)==r.control&&
          *reinterpret_cast<const uintptr_t*>(r.threadObject+0x38)==uintptr_t(Router::Entry())&&
          *reinterpret_cast<const DWORD*>(r.threadObject+0x10)==GetCurrentThreadId()&&
          *reinterpret_cast<const uintptr_t*>(r.control)==r.threadObject&&
          *reinterpret_cast<const uintptr_t*>(r.control+0x48)==r.callable;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
}
thread_local Router::Binding* Router::active_=nullptr;
void* Router::Entry() noexcept {return reinterpret_cast<void*>(&BReloadTitleBridge0);}
bool Router::Initialize(uintptr_t base,DWORD deadline) noexcept {
    if(!code(base)||deadline<1||deadline>10000)return false;
    AcquireSRWLockExclusive(&lock_);bool ok=false;
    if(!ready_&&!base_){base_=base;deadline_=deadline;CheckpointLoadWorkerBridgeConfig c{};
        c.original=reinterpret_cast<void*>(base+0x834D10);c.before=Before;c.after=After;c.finally=Finally;c.context=this;
        ready_=BReloadTitleBridgeConfigure(0,&c)!=0;ok=ready_;}
    ReleaseSRWLockExclusive(&lock_);return ok;
}
bool Router::Register(checkpoint_native_task_provider::Provider&provider,std::uint64_t generation) noexcept {
    checkpoint_native_task_provider::Report r{};if(!generation||!provider.Snapshot(generation,r)||!r.registered||r.closed)return false;
    AcquireSRWLockExclusive(&lock_);bool ok=ready_&&count_<2;
    for(unsigned i=0;i<count_;++i)if(bindings_[i].generation==generation)ok=false;
    if(ok){auto&b=bindings_[count_++];b.provider=&provider;b.generation=generation;b.report.generation=generation;}
    ReleaseSRWLockExclusive(&lock_);return ok;
}
bool Router::ValidateRegistration(const checkpoint_native_task_provider::Provider&provider,uintptr_t base,std::uint64_t generation) noexcept {
    AcquireSRWLockShared(&lock_);bool ok=false;
    if(ready_&&base_==base)for(unsigned i=0;i<count_;++i){auto&b=bindings_[i];if(b.generation==generation&&b.provider==&provider&&!get(b.stopped)&&!get(b.used)&&b.report.error==Error::None&&!b.report.selected){ok=true;break;}}
    ReleaseSRWLockShared(&lock_);return ok;
}
void Router::Stop(std::uint64_t generation) noexcept {
    AcquireSRWLockExclusive(&lock_);for(unsigned i=0;i<count_;++i)if(bindings_[i].generation==generation){auto&b=bindings_[i];InterlockedExchange(&b.stopped,1);b.report.stopped=1;
        // Do not rewrite a completed hardware receipt. In-flight Stop retains
        // the original call/finally and merely refuses subsequent delivery.
        if(b.report.initialized&&!b.report.finally)p::Stop(b.ports);}
    ReleaseSRWLockExclusive(&lock_);
}
bool Router::Snapshot(std::uint64_t generation,Report&out) noexcept {AcquireSRWLockShared(&lock_);bool ok=false;for(unsigned i=0;i<count_;++i)if(bindings_[i].generation==generation){out=bindings_[i].report;ok=true;break;}ReleaseSRWLockShared(&lock_);return ok;}
void Router::SnapshotStatistics(Statistics&out) noexcept {AcquireSRWLockShared(&lock_);out.before=before_;out.unknownForwarded=unknown_;out.refused=refused_;ReleaseSRWLockShared(&lock_);BReloadTitleBridgeSnapshot(0,&out.bridge);}
void Router::Before(const CheckpointLoadWorkerFrame*f,void*c) noexcept {if(f&&c)static_cast<Router*>(c)->before(*f);}
void Router::before(const CheckpointLoadWorkerFrame&f) noexcept {
    Binding*selected=nullptr;checkpoint_native_task_provider::Report source{};
    AcquireSRWLockExclusive(&lock_);++before_;
    for(unsigned i=0;i<count_;++i){checkpoint_native_task_provider::Report r{};auto&b=bindings_[i];
        if(b.provider->Snapshot(b.generation,r)&&r.registered&&r.loadBound&&r.roles[2].start&&!r.roles[2].joined&&
            r.roles[2].threadObject==f.args[0]&&r.roles[2].control==f.args[1]&&r.roles[2].workerThread==f.thread_id){
            if(selected){selected=nullptr;++refused_;ReleaseSRWLockExclusive(&lock_);return;}selected=&b;source=r;}}
    if(!selected){++unknown_;ReleaseSRWLockExclusive(&lock_);return;}
    auto&b=*selected;auto&r=b.report;
    if(active_||InterlockedCompareExchange(&b.used,1,0)){if(r.error==Error::None)r.error=Error::Reentry;++refused_;ReleaseSRWLockExclusive(&lock_);return;}
    r.selected=1;r.creation=source.roles[2].creation;r.callId=f.call_id;r.control=f.args[1];r.threadObject=f.args[0];r.thread=GetCurrentThreadId();
    r.beforeNative=source.roles[2].invoke==0;r.stopped=get(b.stopped)!=0;
    if(r.stopped)r.error=Error::Stopped;
    else if(source.error!=checkpoint_native_task_provider::Error::None||!source.windowOpen||!r.creation||!r.beforeNative)r.error=Error::Source;
    else if(!nativeBinding(f,base_,source.roles[2],r.caller))r.error=Error::NativeBinding;
    active_=&b;
    const bool eligible=r.error==Error::None;ReleaseSRWLockExclusive(&lock_);
    if(!eligible)return;
    const bool initialized=p::Initialize(b.ports,{b.provider,base_,b.generation,deadline_,2});
    AcquireSRWLockExclusive(&lock_);r.initialized=initialized;r.beginAttempted=initialized;if(!initialized)r.error=Error::Initialize;ReleaseSRWLockExclusive(&lock_);
    if(!initialized)return;
    if(get(b.stopped))p::Stop(b.ports);
    const bool armed=p::Begin(b.ports);
    AcquireSRWLockExclusive(&lock_);r.armed=armed;if(!armed)r.error=Error::Begin;ReleaseSRWLockExclusive(&lock_);
}
void Router::After(const CheckpointLoadWorkerFrame*f,void*c) noexcept {auto*b=active_;if(!f||!c||!b||b->report.callId!=f->call_id)return;auto&o=*static_cast<Router*>(c);
    AcquireSRWLockExclusive(&o.lock_);b->report.after=1;b->report.resultRax=f->result_rax;memcpy(b->report.resultXmm0,f->result_xmm0,16);ReleaseSRWLockExclusive(&o.lock_);}
void Router::Finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*c) noexcept {auto*b=active_;if(!f||!x||!c||!b||b->report.callId!=f->call_id)return;auto&o=*static_cast<Router*>(c);
    // No exception interception of original. Frozen bridge invokes FINALLY on
    // SEH/C++ unwind and preserves the original exception and normal RAX/XMM0.
    if(b->report.armed)p::Finish(b->ports);
    p::Report receipt{};if(b->report.initialized)p::Snapshot(b->ports,receipt);
    AcquireSRWLockExclusive(&o.lock_);b->report.ports=receipt;b->report.finally=1;b->report.abnormal=x->abnormal;
    if(b->report.armed&&(!receipt.finished||!receipt.restored||receipt.uncertain)&&b->report.error==Error::None)b->report.error=Error::Finish;
    ReleaseSRWLockExclusive(&o.lock_);active_=nullptr;
}
}
