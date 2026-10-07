"""One-time derivation helper; creates successors, never edits frozen sources."""
from pathlib import Path
P=Path(__file__).resolve().parent
assert not any((P/f'checkpoint_persistent_native_session.{e}').exists() for e in ('h','cpp')), 'One-time derivation only; edit successors directly'
for ext in ('h','cpp'):
 s=(P/f'checkpoint_forward_native_session.{ext}').read_text()
 s=s.replace('checkpoint_forward_native_session','checkpoint_persistent_native_session').replace('CHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE','CHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE')
 if ext=='h':
  s=s.replace('#include "checkpoint_load_dispatch_bridge.h"','#include "checkpoint_load_dispatch_bridge.h"\n#include "checkpoint_persistent_bridge.h"')
  start=s.index('// No discovery,');end=s.index('namespace checkpoint_',start)
  s=s[:start]+'''// Per-generation successor: does not configure, install, restore or unload bridges.
// Logical adapter owns the exact callback scope; retain every Session until exit.
// Current cores retain the validated fixed archive/scenario profile. Production
// activation is closed until native scheduler/admission and dynamic profile bind.
'''+s[end:]
  s=s.replace('bool ArmHooks() noexcept;','bool ActivateForOfflineExercise() noexcept;')
  s=s.replace('static void WorkerBefore(', 'static void DispatchFinally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;\n    static void WorkerBefore(')
  s=s.replace('checkpoint_load_hook_set::Set hooks_{};','// Physical hook ownership deliberately remains outside this generation.')
  s=s.replace('unsigned activeDispatch=0,activeWorker=0,activeRead=0;','unsigned activeDispatch=0,activeWorker=0,activeRead=0;\n    unsigned dispatchFinally[4]{},dispatchAbnormal=0;\n    bool productionAdmission=false,nativeSchedulerFence=false;')
  s=s.replace('// Requests Stop first. Only pre-CAS, after own callbacks have drained. No\n    // post-CAS detach API: final planning/outcome controller remains to integrate.', '// Compatibility refusal: a generation never restores shared physical hooks.')
  s=s.replace('// Expected/restored native slot values remain hooks[i].original. Optional', '// Descriptive native binding only; no publication or restoration here. Optional')
 else:
  s=s.replace('CheckpointLoadDispatchBridge0','CheckpointPersistentBridge0').replace('CheckpointLoadDispatchBridge1','CheckpointPersistentBridge1').replace('CheckpointLoadDispatchBridge2','CheckpointPersistentBridge2').replace('CheckpointLoadDispatchBridge3','CheckpointPersistentBridge3').replace('CheckpointLoadWorkerBridge0','CheckpointPersistentBridge4').replace('CheckpointLoadWorkerBridge1','CheckpointPersistentBridge5')
  s=s.replace('||!hooks_.Initialize(c.hooks,6)','')
  start=s.index('        for(unsigned i=0;i<4;++i){CheckpointLoadDispatchBridgeConfig');end=s.index('        SESSION_LOCK(report_.attempt',start)
  s=s[:start]+s[end:]
  start=s.index('bool Session::ArmHooks()');end=s.index('bool Session::BindQueuedMenu',start)
  s=s[:start]+'''bool Session::ActivateForOfflineExercise() noexcept {
#ifndef CHECKPOINT_PERSISTENT_NATIVE_SESSION_FIXTURE
    // Not a substitute for proving engine queue quiescence and input admission.
    return false;
#else
    if(get(initialized_)!=2||get(stop_)||get(error_)||InterlockedCompareExchange(&armed_,1,0))return false;
    if(!validate(Point::Arm)){fail(Error::Arm);return false;}
    InterlockedExchange(&accepting_,1);InterlockedExchange(&armed_,2);return true;
#endif
}
'''+s[end:]
  start=s.index('bool Session::RestoreBeforeCommit()');end=s.index('void Session::DispatchBefore',start)
  s=s[:start]+'''bool Session::RestoreBeforeCommit() noexcept {
    Stop();InterlockedExchange(&accepting_,0);
    return false; // Physical slots are shared and never owned by this Session.
}
'''+s[end:]
  s=s.replace('    __try {__try {\n        if(f->slot>3','    __try {\n        if(f->slot>3')
  s=s.replace('    }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Memory,GetExceptionCode());}}\n    __finally{InterlockedDecrement(&s.activeDispatch_);}\n}', '''    }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Memory,GetExceptionCode());}
}
void Session::DispatchFinally(const CheckpointPushFrame*f,const CheckpointLoadWorkerExit*e,void*ctx) noexcept {
    auto&s=*static_cast<Session*>(ctx);
    __try {
        if(f->slot>3)return;
        AcquireSRWLockExclusive(&s.lock_);
        __try {
            ++s.report_.dispatchFinally[f->slot];
            auto&r=s.dispatch_[f->slot];
            // Never clear a different overlapping call's record.
            if(r.accepted&&same(r.frame,*f))r.accepted=false;
            if(e->abnormal)++s.report_.dispatchAbnormal;
        }__finally{ReleaseSRWLockExclusive(&s.lock_);}
        if(e->abnormal)s.fail(Error::DispatchPair);
    }__finally{InterlockedDecrement(&s.activeDispatch_);}
}''')
  s=s.replace(';hooks_.Snapshot(out.hooks);',';')
  start=s.index('    bool abnormal=false;');end=s.index('    if(out.hooksRestored)',start)
  s=s[:start]+'''    // Per-generation faults only. Shared bridge counters belong to the owner;
    // a previous generation's abnormal exit cannot contaminate this receipt.
    const bool abnormal=out.dispatchAbnormal!=0;
'''+s[end:]
 (P/f'checkpoint_persistent_native_session.{ext}').write_text(s)
