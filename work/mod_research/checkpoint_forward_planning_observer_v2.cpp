#include "checkpoint_forward_planning_observer_v2.h"
#include <cstring>
namespace checkpoint_forward_planning_observer_v2 {
namespace ns=checkpoint_forward_native_session;namespace by=checkpoint_cc_load_observer;
#define PR_LOCK(o,code) do{AcquireSRWLockExclusive(&(o).lock);__try{code;}__finally{ReleaseSRWLockExclusive(&(o).lock);}}while(0)
static LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>static T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static bool fail(Observer&o,Error e,const char*field,DWORD exception=0){InterlockedCompareExchange(&o.error,LONG(e),0);PR_LOCK(o,o.report.failedField=field;if(exception)o.report.exceptionCode=exception);return false;}
static bool ssoEmpty(uintptr_t p){auto n=at<std::uint64_t>(p+16),cap=at<std::uint64_t>(p+24);if(n||cap>32768||(cap<16&&cap!=15))return false;auto data=cap>=16?at<uintptr_t>(p):p;return data>=0x10000&&!at<char>(data);}
static uintptr_t caller(const Config&c){
#ifdef CHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE
    return c.fixtureCaller;
#else
    return c.base+0x50B785;
#endif
}
static bool snapshotSource(Observer&o,ns::Report&r){
#ifdef CHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE
    if(o.config.syntheticReceipt)r=*o.config.syntheticReceipt;else
#endif
    o.config.session->Snapshot(r);
    const auto&i=r.identity;const auto&l=r.lifecycle;const auto&b=r.bytes;
    return r.initialized&&r.attempt==o.config.attempt&&r.casPublished&&r.request.casApplied&&r.request.intentDurable&&r.request.read.matched&&
        i.receiptReady&&!i.error&&i.token==r.attempt&&i.root&&i.world&&i.title&&i.historicalLoad&&i.workerCall&&i.target.force&&i.target.person&&
        l.receiptReady&&!l.error&&l.token==r.attempt&&l.load==i.historicalLoad&&l.title==i.title&&l.completedCall==i.completionCall&&
        b.observedWorkerAndBytes&&!b.error&&b.token==r.attempt&&b.load==l.load&&b.title==l.title&&b.workerCall==l.frozenBytes.workerCall&&b.readCall==l.frozenBytes.readCall&&
        b.returned==by::TargetSize&&b.nativeResult==1&&!memcmp(b.sha256,by::TargetSha256,32);
}
static bool validate(Observer&o,Point p){return o.config.validate(o.config.context,p,o.config.attempt,o.config.epoch);}
static bool inspect(Observer&o,const CheckpointPushFrame*f,const ns::Report&r,Sample&s){
    const auto b=o.config.base,m=b+0x19E7310,self=uintptr_t(f->args[0]);
    if(at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30)!=0)return fail(o,Error::Stack,"formal_count_or_pending_transition");
    s.stack=at<uintptr_t>(m+0x20);if(!s.stack||at<uintptr_t>(m+0x48)!=self)return fail(o,Error::Stack,"current_user");
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    for(unsigned i=0;i<5;++i){s.states[i]=at<uintptr_t>(s.stack+i*8);if(!s.states[i])return fail(o,Error::Stack,"null_state_address_in_formal_stack");}
    if(s.states[0]!=o.config.persistentRootState||s.states[1]!=o.config.persistentMotorState||s.states[4]!=self)return fail(o,Error::Stack,"root_motor_user_binding");
    const uintptr_t vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    for(unsigned i=0;i<5;++i){auto state=s.states[i];if(memcmp(reinterpret_cast<void*>(state+0x70),names[i],strlen(names[i])+1)||(i&&at<uintptr_t>(state)!=b+vt[i])||at<DWORD>(state+0x68))return fail(o,Error::Stack,"formal_state_type_or_disabled");if(i!=4&&at<uintptr_t>(state+0x50))return fail(o,Error::Worker,"noncurrent_state_worker");}
    if(at<DWORD>(self+0x470)!=2||at<DWORD>(self+0x6C)!=3)return fail(o,Error::Interface,"user_phase");
    s.worker=at<uintptr_t>(self+0x50);if(!s.worker||at<DWORD>(s.worker+0x78)||at<DWORD>(s.worker+0x58)||at<DWORD>(s.worker+0x5C))return fail(o,Error::Worker,"user_worker_state");
    auto callable=at<uintptr_t>(s.worker+0x50),handle=at<uintptr_t>(s.worker+8);if(!callable||!handle||at<uintptr_t>(callable)!=b+0x12F2440||at<uintptr_t>(b+0x12F2440+0x10)!=b+0x50B730||at<DWORD>(handle+0x10)!=f->thread_id)return fail(o,Error::Worker,"native_dispatch_binding");
    auto iterator=at<uintptr_t>(callable+8);if(!iterator||at<uintptr_t>(iterator)!=s.stack+32)return fail(o,Error::Worker,"native_formal_iterator");
    for(unsigned i=1;i<4;++i)if(at<std::uint64_t>(callable+8+i*8)!=f->args[i])return fail(o,Error::Worker,"native_dispatch_arguments");
    s.root=at<uintptr_t>(b+0x1FCA1E0);if(s.root!=r.identity.root||at<uintptr_t>(s.root)!=b+0x12AA6B0)return fail(o,Error::World,"root_binding");
    s.world=at<uintptr_t>(s.root+0x85130);if(s.world!=r.identity.world||at<uintptr_t>(s.world)!=b+0x12AA638)return fail(o,Error::World,"world_binding");
    if(at<WORD>(s.world+0x34)!=203||at<BYTE>(s.world+0x36)!=8||at<BYTE>(s.world+0x37)!=11||at<BYTE>(s.world+0x38)||at<DWORD>(s.world+0x40)!=1||at<BYTE>(s.world+0x3A)!=2||at<BYTE>(s.world+0x165D)!=1||(at<DWORD>(s.world+0x16A8)&0x100))return fail(o,Error::World,"date_local_player_or_mode");
    s.force=at<uintptr_t>(s.root+0xDCA0+2*8);s.ruler=at<uintptr_t>(s.root+0x148+952*8);s.district=at<uintptr_t>(s.root+0xDE40+2*8);
    if(s.force!=r.identity.target.force||s.ruler!=r.identity.target.person||!s.district||at<uintptr_t>(s.force)!=b+0x129FE58||at<WORD>(s.force+0x10)!=952||at<uintptr_t>(s.ruler)!=b+0x12A00D0||at<WORD>(s.ruler+0x10)!=952||at<BYTE>(s.ruler+0x118)!=2||at<uintptr_t>(s.district)!=b+0x129FEC8||at<BYTE>(s.district+0x10)!=2||!at<BYTE>(s.district+0x11)||at<WORD>(s.district+0x12)!=952)return fail(o,Error::Identity,"rebuilt_force_ruler_district");
    s.cache=at<uintptr_t>(b+0x2025318);
    if(!s.cache||at<LONG>(s.cache+0x3EC)!=-1||at<DWORD>(s.cache+0x3F0)||at<LONG>(b+0x201ECD0)!=-1||at<DWORD>(b+0x201ECD4)||at<DWORD>(b+0x201ECD8)||!ssoEmpty(b+0x201ECE0)||at<DWORD>(b+0x201ED00)||at<LONG>(b+0x201ED10)!=-1||!ssoEmpty(b+0x201ED18)||!ssoEmpty(b+0x201ED38))return fail(o,Error::Pending,"native_load_or_save_request");
    auto game=s.states[2];s.toolbar=at<uintptr_t>(self+0x478);s.panel=at<uintptr_t>(self+0x618);auto gamePanel=at<uintptr_t>(game+0x480);
    if(!s.toolbar||!s.panel||!gamePanel||at<LONG>(s.toolbar+0x88)!=-1||at<DWORD>(game+0x474)||at<DWORD>(game+0x478)||at<DWORD>(game+0x47C)||at<DWORD>(gamePanel+0x1B0)||at<uintptr_t>(self+0x4A8)||at<uintptr_t>(self+0x4B0)||at<uintptr_t>(self+0x4B8))return fail(o,Error::Interface,"ui_or_game_request");
    auto special=at<uintptr_t>(b+0x201EC70);if((special&&at<DWORD>(special))||at<DWORD>(b+0x1A38EC8+0x28)||at<DWORD>(b+0x19E7510+0x13C)!=1)return fail(o,Error::Interface,"modal_pause_or_cursor");
    s.uiForceContext=at<DWORD>(b+0x1FCA518); // multi-writer UI context, diagnostic only
    if(at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30)||at<uintptr_t>(m+0x20)!=s.stack||at<uintptr_t>(s.stack+32)!=self||at<uintptr_t>(self+0x50)!=s.worker||at<uintptr_t>(b+0x1FCA1E0)!=s.root||at<uintptr_t>(s.root+0x85130)!=s.world||at<BYTE>(s.world+0x3A)!=2||at<LONG>(s.cache+0x3EC)!=-1)return fail(o,Error::Changed,"boundary_changed_during_read");
    return true;
}
bool Initialize(Observer&o,const Config&c) noexcept {
    if(InterlockedCompareExchange(&o.initialized,1,0))return false;
    bool source=c.session!=nullptr;
#ifdef CHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE
    source=source||c.syntheticReceipt!=nullptr;
#endif
    if(!source||!c.base||!c.attempt||!c.epoch||!c.persistentRootState||!c.persistentMotorState||!c.validate)return fail(o,Error::Config,"config");
    o.config=c;o.report.attempt=c.attempt;o.report.epoch=c.epoch;InterlockedExchange(&o.initialized,2);return true;
}
void Before(const CheckpointPushFrame*f,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        if(get(o.initialized)!=2||get(o.completed)||get(o.error))return;
        ns::Report r{};if(!snapshotSource(o,r)){
            if(!r.identity.receiptReady||!r.lifecycle.receiptReady||!r.bytes.observedWorkerAndBytes){PR_LOCK(o,++o.report.ignored;++o.report.waitingForReceipt);return;}
            fail(o,Error::Receipt,"upstream_receipt_binding");return;
        }
        // A destroyed Load/Title allocation may legitimately become a current
        // Game/User. Only the current formal stack, types, dispatcher and world
        // receipt prove this object's role; address equality alone proves none.
        const auto self=uintptr_t(f->args[0]);
        if(!self||at<uintptr_t>(self)!=o.config.base+0x12CC4A8){PR_LOCK(o,++o.report.ignored);return;}
        if(f->slot!=0||f->thread_id!=GetCurrentThreadId()||at<uintptr_t>(f->caller_entry_rsp)!=caller(o.config)){fail(o,Error::Caller,"user_dispatch_caller");return;}
        if(InterlockedCompareExchange(&o.claimed,1,0)){fail(o,Error::Overlap,"one_owned_user_call");return;}
        memcpy(o.frame.args,f->args,sizeof o.frame.args);o.frame.call_id=f->call_id;o.frame.thread_id=f->thread_id;o.frame.slot=f->slot;o.frame.caller_entry_rsp=f->caller_entry_rsp;InterlockedExchange(&o.inFlight,1);
        PR_LOCK(o,++o.report.before;o.report.userCall=f->call_id;o.report.thread=f->thread_id;o.report.observedUser=self;o.report.historicalLoad=r.identity.historicalLoad;o.report.historicalTitle=r.identity.title;o.report.identityWorkerCall=r.identity.workerCall;o.report.completedLoadCall=r.lifecycle.completedCall;o.report.receiptBound=1;o.report.previousUserAddressReused=self==o.config.previousUser;o.report.sessionHadError=r.error!=0;o.report.sessionStopRequested=r.stopRequested);
        if(!validate(o,Point::Before)){fail(o,Error::Epoch,"epoch_before");return;}
        Sample s{};if(!inspect(o,f,r,s))return;
        PR_LOCK(o,o.report.beforeSample=s;o.report.formalPlanningStack=1;o.report.identityMatched=1;o.report.requestCleared=1;o.report.uiObjectsPresent=1);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,"before_read_fault",GetExceptionCode());}
}
void After(const CheckpointPushFrame*f,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    if(!get(o.inFlight)||f->call_id!=o.frame.call_id||f->thread_id!=o.frame.thread_id||f->slot!=o.frame.slot||f->caller_entry_rsp!=o.frame.caller_entry_rsp||memcmp(f->args,o.frame.args,sizeof f->args))return;
    __try {__try {
        if(f->thread_id!=GetCurrentThreadId()){fail(o,Error::Pair,"after_current_thread");return;}
        PR_LOCK(o,++o.report.after;o.report.nativeReturned=1;o.report.nativeRax=f->result_rax;memcpy(o.report.nativeXmm0,f->result_xmm0,16));
        if(get(o.error))return;
        ns::Report r{};if(!snapshotSource(o,r)||r.identity.workerCall!=o.report.identityWorkerCall||r.lifecycle.completedCall!=o.report.completedLoadCall||r.identity.historicalLoad!=o.report.historicalLoad||r.identity.title!=o.report.historicalTitle){fail(o,Error::Receipt,"receipt_changed");return;}
        if(!validate(o,Point::After)){fail(o,Error::Epoch,"epoch_after");return;}
        Sample s{};if(!inspect(o,f,r,s))return;
        const auto&old=o.report.beforeSample;
        if(memcmp(old.states,s.states,sizeof s.states)||old.stack!=s.stack||old.root!=s.root||old.world!=s.world||old.force!=s.force||old.ruler!=s.ruler||old.district!=s.district||old.cache!=s.cache||old.worker!=s.worker||old.toolbar!=s.toolbar||old.panel!=s.panel){fail(o,Error::Changed,"native_boundary_objects_changed");return;}
        PR_LOCK(o,o.report.afterSample=s;o.report.uiForceContextMatches=s.uiForceContext==2;o.report.planningBoundaryObserved=1);
        InterlockedExchange(&o.completed,1);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,"after_read_fault",GetExceptionCode());}}
    __finally {InterlockedExchange(&o.inFlight,0);}
}
void Snapshot(Observer&o,Report&out) noexcept {AcquireSRWLockShared(&o.lock);out=o.report;ReleaseSRWLockShared(&o.lock);out.error=get(o.error);out.inFlight=get(o.inFlight);out.planningBoundaryObserved=out.planningBoundaryObserved&&!out.error&&!out.inFlight&&out.before==1&&out.after==1&&out.nativeReturned;}
}
