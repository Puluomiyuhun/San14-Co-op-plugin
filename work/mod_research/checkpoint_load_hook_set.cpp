#include "checkpoint_load_hook_set.h"

namespace checkpoint_load_hook_set {
namespace {
bool query(void* volatile* slot,DWORD& protection) {
    const auto p=reinterpret_cast<std::uintptr_t>(slot);MEMORY_BASIC_INFORMATION m{};
    if(p<0x10000||(p&7)||VirtualQuery(const_cast<void**>(slot),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
       p+8>reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize)return false;
    protection=m.Protect;
    return protection==PAGE_READONLY||protection==PAGE_READWRITE||protection==PAGE_WRITECOPY;
}
}
bool Set::Initialize(const Binding* bindings,unsigned count) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    bool ok=false;AcquireSRWLockExclusive(&lock_);
    __try {__try {
        if(!bindings||!count||count>Capacity)__leave;
        for(unsigned i=0;i<count;++i){
            const auto b=bindings[i];DWORD protection=0;
            if(!b.original||!b.hook||b.original==b.hook||!query(b.slot,protection)||*b.slot!=b.original)__leave;
            for(unsigned j=0;j<i;++j)if(bindings[j].slot==b.slot)__leave;
            report_.entries[i].binding=b;report_.entries[i].protection=protection;report_.entries[i].known=true;
        }
        report_.count=count;report_.initialized=true;ok=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();}}
    __finally{ReleaseSRWLockExclusive(&lock_);}
    return ok;
}
bool Set::Publish(unsigned index) noexcept {
    bool ok=false;AcquireSRWLockExclusive(&lock_);
    __try {__try {
        if(!report_.initialized||index>=report_.count)__leave;
        auto&e=report_.entries[index];DWORD observed=0,old=0;
        if(e.published||e.dirty||e.restored||!query(e.binding.slot,observed)||observed!=e.protection||*e.binding.slot!=e.binding.original){e.error=ERROR_INVALID_STATE;__leave;}
        if(!VirtualProtect(const_cast<void**>(e.binding.slot),8,PAGE_READWRITE,&old)){e.error=GetLastError();__leave;}
        e.dirty=true;
        auto previous=InterlockedCompareExchangePointer(e.binding.slot,e.binding.hook,e.binding.original);
        e.published=previous==e.binding.original;
        if(VirtualProtect(const_cast<void**>(e.binding.slot),8,e.protection,&old))e.dirty=false;
        else e.error=GetLastError();
        e.observed=reinterpret_cast<std::uintptr_t>(*e.binding.slot);
        if(!query(e.binding.slot,e.lastProtection))e.error=ERROR_INVALID_ADDRESS;
        ok=e.published&&!e.dirty&&e.observed==reinterpret_cast<std::uintptr_t>(e.binding.hook)&&e.lastProtection==e.protection;
        if(!ok)restoreLocked(index);
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();if(index<report_.count)restoreLocked(index);}}
    __finally{ReleaseSRWLockExclusive(&lock_);}
    return ok;
}
bool Set::restoreLocked(unsigned index) noexcept {
    if(!report_.initialized||index>=report_.count)return false;
    auto&e=report_.entries[index];bool pointer=false,protection=false;DWORD old=0;
    __try {
        if(!e.dirty&&!e.published){
            e.observed=reinterpret_cast<std::uintptr_t>(*e.binding.slot);
            return e.observed==reinterpret_cast<std::uintptr_t>(e.binding.original)&&query(e.binding.slot,e.lastProtection)&&e.lastProtection==e.protection;
        }
        if(VirtualProtect(const_cast<void**>(e.binding.slot),8,PAGE_READWRITE,&old)){
            e.dirty=true;
            auto previous=InterlockedCompareExchangePointer(e.binding.slot,e.binding.original,e.binding.hook);
            e.observed=reinterpret_cast<std::uintptr_t>(*e.binding.slot);
            pointer=(previous==e.binding.original||previous==e.binding.hook)&&e.observed==reinterpret_cast<std::uintptr_t>(e.binding.original);
            if(e.observed!=reinterpret_cast<std::uintptr_t>(e.binding.hook))e.published=false;
        }else e.error=GetLastError();
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();}
    // Restoration of page protection is attempted independently of a failed
    // slot dereference/CAS. Never leave writable protection merely because the
    // pointer half of cleanup faulted.
    __try {
        if(e.dirty){protection=VirtualProtect(const_cast<void**>(e.binding.slot),8,e.protection,&old)!=0;if(protection)e.dirty=false;else e.error=GetLastError();}
        else protection=true;
        protection=protection&&query(e.binding.slot,e.lastProtection)&&e.lastProtection==e.protection;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();protection=false;}
    e.restored=pointer&&protection;
    if(!e.restored&&!e.error)e.error=ERROR_INVALID_STATE;
    return e.restored;
}
bool Set::Restore(unsigned index) noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=false;
    __try{ok=restoreLocked(index);}__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Set::RestoreAll() noexcept {
    AcquireSRWLockExclusive(&lock_);bool ok=report_.initialized;
    __try{for(unsigned i=report_.count;i;--i)if(!restoreLocked(i-1))ok=false;}
    __finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Set::Snapshot(Report&out) noexcept {
    AcquireSRWLockShared(&lock_);out=report_;ReleaseSRWLockShared(&lock_);
}
}
