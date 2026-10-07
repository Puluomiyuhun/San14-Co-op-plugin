#include "checkpoint_cc_load_lifecycle.h"
#include <cstring>
namespace checkpoint_cc_load_lifecycle {
namespace bytes=checkpoint_cc_load_observer;
#define LC_LOCK(o,code) do{AcquireSRWLockExclusive(&(o).lock);__try{code;}__finally{ReleaseSRWLockExclusive(&(o).lock);}}while(0)
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
static void fail(Lifecycle&o,Error e,DWORD exception=0){InterlockedCompareExchange(&o.error,LONG(e),0);if(exception)LC_LOCK(o,o.report.exceptionCode=exception);}
static uintptr_t caller(const Config&c){
#ifdef CHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE
    return c.fixtureUpdateCaller;
#else
    return c.base+0x50B785;
#endif
}
static bool sso(uintptr_t p,const char* expected){
    auto n=at<std::uint64_t>(p+16),cap=at<std::uint64_t>(p+24);auto length=std::strlen(expected);
    if(n!=length||n>cap||cap>32768||(cap<16&&cap!=15))return false;
    auto data=cap>=16?at<uintptr_t>(p):p;
    return data>=0x10000&&!memcmp(reinterpret_cast<void*>(data),expected,length+1);
}
static bool attachment(Lifecycle&o,Point p){return !get(o.stopped)&&o.config.validateAttachment(o.config.validationContext,p,o.report.load,o.report.title);}
static bool closureOkay(Lifecycle&o,uintptr_t load,uintptr_t closure,uintptr_t title){
    auto b=o.config.base;
    return at<uintptr_t>(load)==b+0x12DBD68&&!memcmp(reinterpret_cast<void*>(load+0x70),"CLoadState",11)&&
        at<uintptr_t>(load+0x48)==closure&&closure&&at<uintptr_t>(closure)==b+0x12EA4D0&&
        at<uintptr_t>(b+0x12EA4D0+0x10)==b+0x4FAC30&&at<uintptr_t>(closure+8)==title&&title&&at<std::int32_t>(title+0x47C)==63;
}
static bool byteEvidence(Lifecycle&o,bytes::Report&out){
    bytes::Snapshot(*o.config.bytes,out);
    return out.observedWorkerAndBytes&&out.token==o.config.attemptToken&&out.load==o.report.load&&out.title==o.report.title&&
        out.nativeResult==1&&out.bytesMatched&&out.returned==bytes::TargetSize&&!memcmp(out.sha256,bytes::TargetSha256,32);
}
static bool exactPop(uintptr_t manager){auto vector=at<uintptr_t>(manager+0x40);return at<std::uint64_t>(manager+0x30)==1&&vector&&at<DWORD>(vector)==1&&at<uintptr_t>(vector+8)==0;}
static bool requestCleared(uintptr_t b){
    auto cache=at<uintptr_t>(b+0x2025318);
    return at<std::int32_t>(b+0x201ECD0)==-1&&!at<DWORD>(b+0x201ECD4)&&!at<DWORD>(b+0x201ECD8)&&
        sso(b+0x201ECE0,"")&&!at<DWORD>(b+0x201ED00)&&cache&&at<std::int32_t>(cache+0x3EC)==-1;
}
bool Initialize(Lifecycle&o,const Config&c) noexcept {
    if(InterlockedCompareExchange(&o.initialized,1,0))return false;
    if(c.base<0x10000||!c.attemptToken||!c.bytes||!c.validateAttachment){fail(o,Error::Config);return false;}
    if(c.bytes->config.base!=c.base||c.bytes->config.attemptToken!=c.attemptToken||get(c.bytes->initialized)!=2||get(c.bytes->bound)!=0){fail(o,Error::Config);return false;}
    o.config=c;o.report.token=c.attemptToken;InterlockedExchange(&o.initialized,2);return true;
}
void Stop(Lifecycle&o) noexcept {InterlockedExchange(&o.stopped,1);fail(o,Error::Stopped);}
void Snapshot(Lifecycle&o,Report&out) noexcept {
    AcquireSRWLockShared(&o.lock);out=o.report;ReleaseSRWLockShared(&o.lock);
    out.error=get(o.error);out.stopped=get(o.stopped);out.inFlight=get(o.inFlight)?1u:0u;
    out.receiptReady=!out.error&&!out.stopped&&!out.inFlight&&out.bound&&out.workerStarted&&out.joinReturned&&
        out.completionFrozen&&out.requestCleared&&out.exactPop&&out.successFlag==0x7FFFFFFD&&out.nativeResult==1&&out.frozenBytes.observedWorkerAndBytes;
}
void UpdateBefore(const CheckpointPushFrame*f,void*context) noexcept {
    auto&o=*static_cast<Lifecycle*>(context);
    __try {
        if(get(o.initialized)!=2||get(o.stopped)||get(o.completed))return;
        auto self=uintptr_t(f->args[0]);if(!self)return;
        if(get(o.bound)==2&&self!=o.report.load){LC_LOCK(o,++o.report.otherUpdates);return;}
        if(at<uintptr_t>(self)!=o.config.base+0x12DBD68){LC_LOCK(o,++o.report.otherUpdates);return;}
        auto phase=at<DWORD>(self+0x470);
        if(!get(o.bound)&&phase!=1){LC_LOCK(o,++o.report.otherUpdates);return;}
        if(f->thread_id!=GetCurrentThreadId()||at<uintptr_t>(f->caller_entry_rsp)!=caller(o.config)){fail(o,Error::Caller);return;}
        if(InterlockedCompareExchange(&o.inFlight,1,0)){fail(o,Error::Overlap);return;}
        LC_LOCK(o,o.call=f->call_id;o.thread=f->thread_id;o.slot=f->slot;o.rsp=f->caller_entry_rsp;memcpy(o.args,f->args,sizeof o.args);o.beforePhase=phase;
            ++o.report.beforeCalls;o.report.lastCall=f->call_id;o.report.lastThread=f->thread_id;o.report.phaseBefore=phase;o.report.inFlight=1);
        InterlockedExchange(&o.inFlight,2);
        if(!get(o.bound)){
            auto closure=at<uintptr_t>(self+0x48),title=closure?at<uintptr_t>(closure+8):0;
            LC_LOCK(o,o.report.load=self;o.report.title=title;o.report.completionClosure=closure;o.report.worker=self+0x478);
            if(!closureOkay(o,self,closure,title)||at<std::int32_t>(o.config.base+0x201ECD0)!=63||!sso(o.config.base+0x201ECE0,bytes::TargetName)||!attachment(o,Point::Bind)){
                fail(o,Error::Binding);return;
            }
            if(!bytes::BindLoad(*o.config.bytes,self,title)){fail(o,Error::Bytes);return;}
            LC_LOCK(o,o.report.bound=1;o.report.boundCall=f->call_id);InterlockedExchange(&o.bound,2);
        }
        if(phase<1||phase>4||!closureOkay(o,self,o.report.completionClosure,o.report.title)||!attachment(o,Point::Before)){fail(o,Error::Guard);return;}
        if(phase==1&&o.report.workerStarted){fail(o,Error::Phase);return;}
        if(phase>=3&&!o.report.joinReturned){fail(o,Error::Join);return;}
        if(phase==4&&at<std::uint64_t>(o.config.base+0x19E7310+0x30)!=0){fail(o,Error::Completion);return;}
        LC_LOCK(o,o.report.phaseMask|=1u<<phase);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void UpdateAfter(const CheckpointPushFrame*f,void*context) noexcept {
    auto&o=*static_cast<Lifecycle*>(context);
    if(get(o.inFlight)!=2||f->call_id!=o.call||f->thread_id!=o.thread||f->slot!=o.slot||f->caller_entry_rsp!=o.rsp||memcmp(f->args,o.args,sizeof o.args))return;
    __try {
      __try {
        LC_LOCK(o,++o.report.afterCalls;o.report.lastRax=f->result_rax;memcpy(o.report.lastXmm0,f->result_xmm0,16));
        if(get(o.error)||get(o.bound)!=2)return;
        auto self=o.report.load;auto phase=at<DWORD>(self+0x470);
        LC_LOCK(o,o.report.phaseAfter=phase);
        if(!closureOkay(o,self,o.report.completionClosure,o.report.title)||!attachment(o,Point::After)){fail(o,Error::Guard);return;}
        if(o.beforePhase==1){
            auto callable=at<uintptr_t>(self+0x478+0x48);
            if(phase!=2||!callable||at<uintptr_t>(callable)!=o.config.base+0x138E8C0||at<uintptr_t>(callable+8)!=o.config.base+0x508B40){fail(o,Error::Phase);return;}
            LC_LOCK(o,o.report.workerStarted=1);
        }else if(o.beforePhase==2){
            if(phase==2)return;
            bytes::Report evidence{};
            if(phase!=3||!byteEvidence(o,evidence)){fail(o,Error::Bytes);return;}
            auto worker=self+0x478;
            if(at<uintptr_t>(worker)||at<uintptr_t>(worker+8)||at<uintptr_t>(worker+0x60)){fail(o,Error::Join);return;}
            LC_LOCK(o,o.report.joinReturned=1;o.report.joinedCall=f->call_id;o.report.frozenBytes=evidence);
        }else if(o.beforePhase==3){
            if(phase!=3&&phase!=4)fail(o,Error::Phase);
        }else if(o.beforePhase==4){
            bytes::Report evidence{};const DWORD success=at<DWORD>(self+8),result=at<DWORD>(o.config.base+0x201EC08);
            const bool cleared=requestCleared(o.config.base),pop=exactPop(o.config.base+0x19E7310);
            LC_LOCK(o,o.report.successFlag=success;o.report.nativeResult=result;o.report.requestCleared=cleared;o.report.exactPop=pop);
            if(phase!=4||!o.report.joinReturned||!byteEvidence(o,evidence)||success!=0x7FFFFFFD||result!=1||!cleared||!pop){fail(o,Error::Completion);return;}
            LC_LOCK(o,o.report.frozenBytes=evidence;o.report.completionFrozen=1;o.report.completedCall=f->call_id);
            InterlockedExchange(&o.completed,1);
        }else fail(o,Error::Phase);
      }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
    }__finally {LC_LOCK(o,o.report.inFlight=0);InterlockedExchange(&o.inFlight,0);}
}
}
