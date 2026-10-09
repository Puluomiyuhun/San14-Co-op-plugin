// Explicit successor: release the published target lease only after actual sealed restore.
#include "b_warm_retire_session.h"
#include "b_warm_refresh_owner.h"
#include <cstring>
#include <cwchar>
// Same Session ABI and single-bank lifetime as checkpoint_forward_native_session.
// Only admission sealing and completed User-AFTER six-slot restoration are new.
namespace b_warm_retire {
namespace ns=checkpoint_forward_native_session;namespace pr=checkpoint_forward_planning_observer_v2;
static SRWLOCK gate=SRWLOCK_INIT;
static ns::Session* session=nullptr;
static pr::Observer* planning=nullptr;
static Report report{};
static volatile LONG sealed=0;
bool Bind(ns::Session&s,pr::Observer&p) noexcept {
    AcquireSRWLockExclusive(&gate);bool ok=false;
    __try {if(!session&&p.config.session==&s&&InterlockedCompareExchange(&p.initialized,0,0)==2){session=&s;planning=&p;report.bound=1;ok=true;}}
    __finally {ReleaseSRWLockExclusive(&gate);}return ok;
}
bool Sealed(const ns::Session*s) noexcept {return s==session&&InterlockedCompareExchange(&sealed,0,0)==1;}
void Snapshot(Report&r) noexcept {AcquireSRWLockShared(&gate);r=report;ReleaseSRWLockShared(&gate);}
static bool enter(ns::Session&s,volatile LONG&active) noexcept {
    AcquireSRWLockExclusive(&gate);const bool ok=!Sealed(&s);if(ok)InterlockedIncrement(&active);ReleaseSRWLockExclusive(&gate);return ok;
}
// Only called from the actual paired physical User AFTER's own final cleanup.
// At this point original User and every observer AFTER have returned; the bridge
// itself is still on stack. Old pointers may arrive later and are transparent.
static bool eligible(ns::Session&s,const CheckpointPushFrame*f,const ns::Report&r) noexcept {
    if(session!=&s||!planning||!f||f->slot||f->thread_id!=GetCurrentThreadId())return false;
    ++report.eligibleChecks;pr::Report p{};pr::Snapshot(*planning,p);
    if(!p.planningBoundaryObserved||p.error||p.inFlight||p.before!=1||p.after!=1||!p.nativeReturned||
       !p.receiptBound||!p.formalPlanningStack||!p.identityMatched||!p.requestCleared||!p.uiObjectsPresent||
       p.userCall!=f->call_id||p.thread!=f->thread_id||p.observedUser!=f->args[0]||p.attempt!=r.attempt||
       p.sessionHadError||p.sessionStopRequested||!p.epoch)return false;
    report.completionSeen=1;report.refusalStage=1;
    const auto&b=r.bytes;const auto&l=r.lifecycle;const auto&i=r.identity;
    if(r.error||r.exceptionCode||r.stopRequested||!r.armed||!r.casPublished||!r.requestSettled||r.requestInFlight||
       !r.request.casApplied||!r.request.intentDurable||!r.request.read.matched||r.dispatchUnpaired||
       r.activeDispatch!=1||r.activeWorker||r.activeRead||b.error||b.activeWorker||b.activeRead||b.workerAbnormal||b.readAbnormal||
       !b.observedWorkerAndBytes||!b.bytesMatched||!b.workerFinally||!b.readFinally||
       l.error||l.inFlight||!l.receiptReady||!l.joinReturned||!l.exactPop||!l.completionFrozen||
       i.error||i.active||i.abnormal||!i.receiptReady||!i.nativeReturned||!i.finallyCalls||
       b.token!=r.attempt||l.token!=r.attempt||i.token!=r.attempt||
       l.load!=i.historicalLoad||l.title!=i.title||l.completedCall!=i.completionCall||
       p.completedLoadCall!=l.completedCall||p.identityWorkerCall!=i.workerCall||
       b.workerCall!=l.frozenBytes.workerCall||b.readCall!=l.frozenBytes.readCall)return false;
    report.refusalStage=2;
    for(unsigned j=0;j<4;++j)if(r.dispatchStats[j].abnormal_exits||r.dispatchStats[j].active!=(j==0?1u:0u))return false;
    if(r.workerStats.active||r.readStats.active||r.workerStats.abnormal_exits||r.readStats.abnormal_exits||r.workerStats.cleanup_faults||r.readStats.cleanup_faults)return false;
    report.refusalStage=3;
    if(!r.hooks.initialized||r.hooks.count!=6||r.hooks.exceptionCode)return false;
    for(const auto&e:r.hooks.entries)if(!e.known||!e.published||e.dirty||e.error||e.restored)return false;
    report.refusalStage=0;report.attempt=r.attempt;report.userCall=f->call_id;report.thread=f->thread_id;report.identityCall=i.workerCall;report.loadCall=l.completedCall;return true;
}
}

namespace checkpoint_forward_native_session {
namespace rq=checkpoint_load_request_commit;namespace by=checkpoint_cc_load_observer;namespace lc=checkpoint_cc_load_lifecycle;namespace ti=checkpoint_title_identity_adapter;namespace bd=checkpoint_load_input_boundary;
#define SESSION_LOCK(code) do{AcquireSRWLockExclusive(&lock_);__try{code;}__finally{ReleaseSRWLockExclusive(&lock_);}}while(0)
template<class T>static T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
static bool same(const CheckpointPushFrame&a,const CheckpointPushFrame&b){return a.call_id==b.call_id&&a.thread_id==b.thread_id&&a.slot==b.slot&&a.caller_entry_rsp==b.caller_entry_rsp&&!memcmp(a.args,b.args,sizeof a.args);}
template<size_t N>static bool pathCopy(wchar_t(&out)[N],const wchar_t*in){if(!in||!*in)return false;for(size_t i=0;i<N;++i){out[i]=in[i];if(!out[i])return true;}return false;}
static void* entries(unsigned i){void*const p[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};return i<6?p[i]:nullptr;}
void Session::fail(Error e,DWORD exception) noexcept {InterlockedCompareExchange(&error_,LONG(e),0);if(exception)SESSION_LOCK(report_.exceptionCode=exception);}
bool Session::validate(Point p) noexcept {__try{return config_.validate&&config_.validate(config_.context,p);}__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());return false;}}
bool Session::Initialize(const Config&c) noexcept {
    if(InterlockedCompareExchange(&initialized_,1,0))return false;
    __try {
        auto b=c.request.boundary.base;auto token=c.request.boundary.attempt;
        if(!b||!token||c.request.boundary.menu||!c.validate||!c.userAfter||!c.request.validate||
           bool(c.userObservationBefore)!=bool(c.userObservationAfter)||
           c.bytes.base!=b||c.bytes.attemptToken!=token||c.lifecycle.base!=b||c.lifecycle.attemptToken!=token||c.identity.base!=b||c.identity.attemptToken!=token||
           !c.bytes.validateAttachment||!c.lifecycle.validateAttachment||!c.identity.validateAttachment||memcmp(c.request.ownerBinding,c.identity.ownerBinding,32)||
           !pathCopy(localPath_,c.request.localPath)||!pathCopy(requestIntent_,c.request.intentPath)||!pathCopy(identityIntent_,c.identity.intentPath)||!wcscmp(requestIntent_,identityIntent_)){
            fail(Error::Config);return false;
        }
        for(unsigned i=0;i<6;++i)if(c.hooks[i].hook!=entries(i)||!c.hooks[i].original||!c.hooks[i].slot){fail(Error::Config);return false;}
#ifndef CHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE
        // Supported native User vtable profile. A wrapper is never an expected
        // pre-existing value, even when configured as a forwarding target.
        if(c.hooks[0].slot!=reinterpret_cast<void*volatile*>(b+0x12CC4A8+0x28)||
           c.hooks[0].original!=reinterpret_cast<void*>(b+0x3F9B00)){fail(Error::Config);return false;}
#endif
        for(unsigned i=0;i<4;++i){
            const auto target=c.dispatchForwardTargets[i]?c.dispatchForwardTargets[i]:c.hooks[i].original;
            for(unsigned j=0;j<6;++j)if(target==entries(j)){fail(Error::Config);return false;}
        }
        if(c.bytes.readMethod!=uintptr_t(c.hooks[5].original)){fail(Error::Config);return false;}
        config_=c;config_.request.localPath=localPath_;config_.request.intentPath=requestIntent_;config_.identity.intentPath=identityIntent_;
        if(!validate(Point::Initialize)||!hooks_.Initialize(c.hooks,6)||!by::Initialize(bytes_,c.bytes)){fail(Error::Initialize);return false;}
        auto l=c.lifecycle;l.bytes=&bytes_;if(!lc::Initialize(lifecycle_,l)){fail(Error::Initialize);return false;}
        auto t=config_.identity;t.lifecycle=&lifecycle_;t.bytes=&bytes_;if(!ti::Initialize(identity_,t)){fail(Error::Initialize);return false;}
        for(unsigned i=0;i<4;++i){CheckpointLoadDispatchBridgeConfig x{};x.original=c.dispatchForwardTargets[i]?c.dispatchForwardTargets[i]:c.hooks[i].original;x.before=DispatchBefore;x.after=DispatchAfter;x.context=this;if(!CheckpointLoadDispatchBridgeConfigure(i,&x)){fail(Error::Initialize);return false;}}
        CheckpointLoadWorkerBridgeConfig w{};w.original=c.hooks[4].original;w.before=WorkerBefore;w.after=WorkerAfter;w.finally=WorkerFinally;w.context=this;
        CheckpointLoadWorkerBridgeConfig r{};r.original=c.hooks[5].original;r.before=ReadBefore;r.after=ReadAfter;r.finally=ReadFinally;r.context=this;
        if(!CheckpointLoadWorkerBridgeConfigure(0,&w)||!CheckpointLoadWorkerBridgeConfigure(1,&r)){fail(Error::Initialize);return false;}
        SESSION_LOCK(report_.attempt=token;report_.initialized=1;
            for(unsigned i=0;i<4;++i){report_.dispatchExpectedOriginal[i]=uintptr_t(c.hooks[i].original);report_.dispatchEffectiveTarget[i]=uintptr_t(c.dispatchForwardTargets[i]?c.dispatchForwardTargets[i]:c.hooks[i].original);report_.dispatchOverride[i]=c.dispatchForwardTargets[i]&&c.dispatchForwardTargets[i]!=c.hooks[i].original?1u:0u;});InterlockedExchange(&initialized_,2);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());return false;}
}
bool Session::ArmHooks() noexcept {
    if(get(initialized_)!=2||get(stop_)||get(error_)||InterlockedCompareExchange(&armed_,1,0))return false;
    if(!validate(Point::Arm)){fail(Error::Arm);return false;}
    // Observation slots precede driving slots. No callback can drive work until
    // all six publications have completed and accepting_ is set.
    const unsigned order[]={3,4,5,1,2,0};
    for(unsigned i:order)if(get(stop_)||!hooks_.Publish(i)){fail(Error::Arm);hooks_.RestoreAll();return false;}
    if(get(stop_)){hooks_.RestoreAll();return false;}
    InterlockedExchange(&accepting_,1);InterlockedExchange(&armed_,2);return true;
}
bool Session::BindQueuedMenu(const QueueReceipt&r) noexcept {
    if(get(initialized_)!=2||!get(accepting_)||get(stop_)||get(error_)||get(userAfterActive_)!=1||r.attempt!=config_.request.boundary.attempt||
       r.userCall!=userAfterCall_||r.thread!=userAfterThread_||r.thread!=GetCurrentThreadId()||r.user!=config_.request.boundary.states[4]||!r.menu||!r.nativeQueueReturned||
       InterlockedCompareExchange(&menuBound_,1,0)){fail(Error::MenuBinding);return false;}
    __try {
        const auto b=config_.request.boundary.base,m=b+0x19E7310,stack=at<uintptr_t>(m+0x20),queue=at<uintptr_t>(m+0x40);
        if(!stack||!queue||at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30)!=1||at<DWORD>(queue)!=0||at<uintptr_t>(queue+8)!=r.menu||
           at<uintptr_t>(r.menu)!=b+0x12DB4C0||memcmp(reinterpret_cast<void*>(r.menu+0x70),"CSaveLoadState",15)||at<DWORD>(r.user+0x470)!=2){fail(Error::MenuBinding);return false;}
        for(unsigned i=0;i<5;++i)if(at<uintptr_t>(stack+i*8)!=config_.request.boundary.states[i]){fail(Error::MenuBinding);return false;}
        if(!validate(Point::BindMenu)||get(stop_)){fail(Error::MenuBinding);return false;}
        auto c=config_.request;c.boundary.menu=r.menu;c.validate=requestGuard;c.context=this;
        if(!request_.Initialize(c)){fail(Error::MenuBinding);return false;}
        SESSION_LOCK(report_.menu=r.menu;report_.menuBound=1);InterlockedExchange(&menuBound_,2);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());return false;}
}
bool Session::makeCall(const CheckpointPushFrame*f,bd::Stage stage,uintptr_t worker,bd::Call&out,uintptr_t&fixtureReturn) noexcept {
    __try {
        if(f->thread_id!=GetCurrentThreadId()||f->slot>3)return false;
        out=bd::Call{};out.stage=stage;memcpy(out.args,f->args,sizeof out.args);out.callId=out.pairedCallId=f->call_id;out.thread=out.pairedThread=f->thread_id;
        out.callerEntryRsp=f->caller_entry_rsp;out.pairedWorker=worker;out.originalReturned=stage==bd::Stage::MenuAfter;
#ifdef CHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE
        if(at<uintptr_t>(f->caller_entry_rsp)!=config_.fixtureDispatchCaller[f->slot])return false;
        fixtureReturn=config_.request.boundary.base+0x50B785;out.callerEntryRsp=uintptr_t(&fixtureReturn);
#else
        (void)fixtureReturn;
#endif
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());return false;}
}
bool Session::requestGuard(void*ctx,rq::Point p) noexcept {
    auto&s=*static_cast<Session*>(ctx);
    __try {
        if(get(s.stop_)||get(s.error_)||!get(s.accepting_)||get(s.armed_)!=2)return false;
        auto point=p==rq::Point::AfterCas?Point::AfterRequest:Point::BeforeRequest;
        return s.validate(point)&&s.config_.request.validate(s.config_.request.context,p)&&!get(s.stop_)&&!get(s.error_)&&get(s.accepting_);
    }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Memory,GetExceptionCode());return false;}
}
void Session::captureRequest() noexcept {
    const auto&r=request_.GetReport();SESSION_LOCK(report_.request=r);
    if(r.casApplied)InterlockedExchange(&published_,1);
    if(r.casApplied||(r.casAttempts&&r.state!=rq::State::NotApplied))InterlockedExchange(&mayPublished_,1);
}
void Session::Stop() noexcept {AcquireSRWLockExclusive(&b_warm_retire::gate);InterlockedExchange(&stop_,1);ReleaseSRWLockExclusive(&b_warm_retire::gate);}
bool Session::RestoreBeforeCommit() noexcept {
    Stop();InterlockedExchange(&accepting_,0);
    if(get(mayPublished_)||get(requestActive_)||get(activeDispatch_)||get(activeWorker_)||get(activeRead_))return false;
    if(!validate(Point::RestoreBeforeCommit))return false;
    const bool ok=hooks_.RestoreAll();if(ok)InterlockedExchange(&restored_,1);else fail(Error::Restore);return ok;
}
void Session::DispatchBefore(const CheckpointPushFrame*f,void*ctx) noexcept {
    auto&s=*static_cast<Session*>(ctx);if(!b_warm_retire::enter(s,s.activeDispatch_))return;
    __try {
        if(f->slot>3||get(s.initialized_)!=2)return;
        AcquireSRWLockExclusive(&s.lock_);
        __try {++s.report_.dispatchBefore[f->slot];}__finally{ReleaseSRWLockExclusive(&s.lock_);}
        if(!get(s.accepting_)&&!get(s.mayPublished_))return;
        bool accepted=false;uintptr_t worker=0;
        if(f->slot==0){
            // Observation follows the shared User vtable, not the address of the
            // previous User. Do not dereference unknown/new self here; the
            // observer authenticates its rebuilt stack and lifetime receipt.
            if(!s.config_.userObservationBefore&&f->args[0]!=s.config_.request.boundary.states[4])return;
        }else if(f->slot==1||f->slot==2){if(f->slot==1&&get(s.menuBound_)!=2)return;const auto expected=f->slot==1?s.report_.menu:s.config_.request.boundary.states[2];if(!expected||f->args[0]!=expected)return;worker=at<uintptr_t>(expected+0x50);}
        AcquireSRWLockExclusive(&s.lock_);
        __try {auto&r=s.dispatch_[f->slot];if(!r.accepted){r.frame=*f;r.worker=worker;r.accepted=true;accepted=true;}}
        __finally{ReleaseSRWLockExclusive(&s.lock_);}
        if(!accepted){s.fail(Error::DispatchPair);return;}
        if(f->slot==0&&s.config_.userObservationBefore)s.config_.userObservationBefore(f,s.config_.userObservationContext);
        if(f->slot==3){if(get(s.mayPublished_))lc::UpdateBefore(f,&s.lifecycle_);return;}
        if(f->slot!=2||get(s.stop_)||get(s.error_)||get(s.menuBound_)!=2||get(s.menuOnce_)!=2||InterlockedCompareExchange(&s.gameOnce_,1,0))return;
        InterlockedExchange(&s.requestActive_,1);
        __try {
            bd::Call call{};uintptr_t translatedReturn=0;
            if(!s.makeCall(f,bd::Stage::GameBefore,worker,call,translatedReturn)){s.fail(Error::Request);return;}
            const bool ok=s.request_.CommitGameBefore(call);s.captureRequest();
            if(!ok)s.fail(Error::Request);
        }__finally {InterlockedExchange(&s.requestSettled_,1);InterlockedExchange(&s.requestActive_,0);}
    }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Memory,GetExceptionCode());}
}
void Session::DispatchAfter(const CheckpointPushFrame*f,void*ctx) noexcept {
    auto&s=*static_cast<Session*>(ctx);if(b_warm_retire::Sealed(&s))return;
    __try {__try {
        if(f->slot>3||get(s.initialized_)!=2)return;
        DispatchRecord record{};bool paired=false;
        AcquireSRWLockExclusive(&s.lock_);
        __try {++s.report_.dispatchAfter[f->slot];auto&r=s.dispatch_[f->slot];if(r.accepted&&same(r.frame,*f)){record=r;r.accepted=false;paired=true;}else if(r.accepted)++s.report_.dispatchUnpaired;}
        __finally{ReleaseSRWLockExclusive(&s.lock_);}
        if(!paired)return;
        if(f->slot==3){if(get(s.mayPublished_))lc::UpdateAfter(f,&s.lifecycle_);return;}
        if(f->slot==0){
            if(s.config_.userObservationAfter)s.config_.userObservationAfter(f,s.config_.userObservationContext);
            if(f->args[0]!=s.config_.request.boundary.states[4])return;
            if(get(s.stop_)||get(s.error_)||!get(s.accepting_)||InterlockedCompareExchange(&s.userOnce_,1,0))return;
            s.userAfterCall_=f->call_id;s.userAfterThread_=f->thread_id;InterlockedExchange(&s.userAfterActive_,1);
            AcquireSRWLockExclusive(&s.lock_);++s.report_.userControllerCalls;ReleaseSRWLockExclusive(&s.lock_);
            __try {s.config_.userAfter(s.config_.context,s,f);}__finally {InterlockedExchange(&s.userAfterActive_,0);}
            return;
        }
        if(f->slot!=1||get(s.stop_)||get(s.error_)||get(s.menuBound_)!=2||InterlockedCompareExchange(&s.menuOnce_,1,0))return;
        bd::Call call{};uintptr_t translatedReturn=0;
        if(!s.makeCall(f,bd::Stage::MenuAfter,record.worker,call,translatedReturn)){s.fail(Error::Request);return;}
        const bool ok=s.request_.ObserveMenuAfter(call);s.captureRequest();if(!ok)s.fail(Error::Request);else InterlockedExchange(&s.menuOnce_,2);
    }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Memory,GetExceptionCode());}}
    __finally{
        AcquireSRWLockExclusive(&b_warm_retire::gate);
        __try {
            bool retire=false;
            if(f&&f->slot==0&&b_warm_retire::session==&s){Report completed{};s.Snapshot(completed);retire=b_warm_retire::eligible(s,f,completed);}
            InterlockedDecrement(&s.activeDispatch_);
            if(retire){
                InterlockedExchange(&s.accepting_,0);InterlockedExchange(&b_warm_retire::sealed,1);b_warm_retire::report.sealed=1;
                // The actual HookSet preserves each native original/protection
                // and refuses a foreign pointer. Failure never unseals the bank.
                const bool restored=s.hooks_.RestoreAll();
                b_warm_retire::report.restored=restored?1u:0u;b_warm_retire::report.restoreFailed=restored?0u:1u;
                if(restored){
                    InterlockedExchange(&s.restored_,1);
                    if(!b_warm_refresh::ReleaseAfterRetirement())s.fail(Error::Restore);
                }
            }
        }__finally {ReleaseSRWLockExclusive(&b_warm_retire::gate);}
    }
}
void Session::WorkerBefore(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {auto&s=*static_cast<Session*>(ctx);if(!b_warm_retire::enter(s,s.activeWorker_))return;if(get(s.mayPublished_)){by::WorkerBefore(f,&s.bytes_);ti::Before(f,&s.identity_);}}
void Session::WorkerAfter(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {auto&s=*static_cast<Session*>(ctx);if(b_warm_retire::Sealed(&s))return;if(get(s.mayPublished_)){by::WorkerAfter(f,&s.bytes_);ti::After(f,&s.identity_);}}
void Session::WorkerFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*ctx) noexcept {auto&s=*static_cast<Session*>(ctx);if(b_warm_retire::Sealed(&s))return;__try {if(get(s.mayPublished_)){by::WorkerFinally(f,e,&s.bytes_);ti::Finally(f,e,&s.identity_);}}__finally{InterlockedDecrement(&s.activeWorker_);}}
void Session::ReadBefore(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {auto&s=*static_cast<Session*>(ctx);if(!b_warm_retire::enter(s,s.activeRead_))return;if(get(s.mayPublished_))by::ReadBefore(f,&s.bytes_);}
void Session::ReadAfter(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {auto&s=*static_cast<Session*>(ctx);if(b_warm_retire::Sealed(&s))return;if(get(s.mayPublished_))by::ReadAfter(f,&s.bytes_);}
void Session::ReadFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*ctx) noexcept {auto&s=*static_cast<Session*>(ctx);if(b_warm_retire::Sealed(&s))return;__try {if(get(s.mayPublished_))by::ReadFinally(f,e,&s.bytes_);}__finally{InterlockedDecrement(&s.activeRead_);}}
void Session::Snapshot(Report&out) noexcept {
    AcquireSRWLockShared(&lock_);out=report_;ReleaseSRWLockShared(&lock_);
    out.error=get(error_);out.armed=get(armed_)==2;out.requestInFlight=get(requestActive_);out.requestSettled=get(requestSettled_);out.casPublished=get(published_);out.mayHavePublished=get(mayPublished_);out.stopRequested=get(stop_);out.restoreRequested=!get(accepting_)&&get(stop_);out.hooksRestored=get(restored_);
    out.activeDispatch=get(activeDispatch_);out.activeWorker=get(activeWorker_);out.activeRead=get(activeRead_);
    by::Snapshot(bytes_,out.bytes);lc::Snapshot(lifecycle_,out.lifecycle);ti::Snapshot(identity_,out.identity);hooks_.Snapshot(out.hooks);
    bool abnormal=false;for(unsigned i=0;i<4;++i){CheckpointLoadDispatchBridgeSnapshot(i,&out.dispatchStats[i]);abnormal|=out.dispatchStats[i].abnormal_exits!=0;}
    CheckpointLoadWorkerBridgeSnapshot(0,&out.workerStats);CheckpointLoadWorkerBridgeSnapshot(1,&out.readStats);
    abnormal|=out.workerStats.abnormal_exits||out.readStats.abnormal_exits||out.workerStats.cleanup_faults||out.readStats.cleanup_faults;
    if(out.hooksRestored)out.state=State::HooksRestored;
    else if(out.stopRequested)out.state=out.mayHavePublished||out.requestInFlight?State::RetainingObservation:State::StoppedBeforeRequest;
    else if(out.error||abnormal||out.bytes.error||out.lifecycle.error||out.identity.error)out.state=out.mayHavePublished?State::Uncertain:State::Rejected;
    else if(out.identity.receiptReady)out.state=State::IdentityReceipt;
    else if(out.lifecycle.receiptReady)out.state=State::LoadReceipt;
    else if(out.casPublished)out.state=State::ObservingLoad;
    else if(out.requestInFlight)out.state=State::RequestInFlight;
    else if(out.request.menuObserved)out.state=State::MenuReady;
    else if(out.menuBound)out.state=State::MenuQueued;
    else if(out.armed)out.state=State::Armed;
    else if(out.initialized)out.state=State::Initialized;
    else out.state=State::New;
}
}

extern "C" DWORD WINAPI GetBWarmRetireReport(void*p){
    __try {if(!p)return 1;b_warm_retire::Snapshot(*static_cast<b_warm_retire::Report*>(p));return 0;}
    __except(EXCEPTION_EXECUTE_HANDLER){return 2;}
}
