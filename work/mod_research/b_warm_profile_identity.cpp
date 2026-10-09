#include "b_warm_profile.h"
static const b_warm_profile::Profile& wp() noexcept {return b_warm_profile::Get();}
#include "checkpoint_title_identity_adapter.h"
#include <cstring>
#include <cwchar>
namespace checkpoint_title_identity_adapter {
namespace lc=checkpoint_cc_load_lifecycle;namespace by=checkpoint_cc_load_observer;
#define TI_LOCK(o,code) do{AcquireSRWLockExclusive(&(o).lock);__try{code;}__finally{ReleaseSRWLockExclusive(&(o).lock);}}while(0)
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
static void fail(Adapter&o,Error e,DWORD exception=0){InterlockedCompareExchange(&o.error,LONG(e),0);if(exception)TI_LOCK(o,o.report.exceptionCode=exception);}
static bool equal(pair::Pair a,pair::Pair b){return a.force==b.force&&a.person==b.person;}
static uintptr_t expectedCaller(const Config&c){
#ifdef CHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE
    return c.fixtureWorkerCaller;
#else
    return c.base+0x834D9B;
#endif
}
static bool owner(Adapter&o){CheckpointLoadWorkerOwner current{};return CheckpointLoadWorkerCurrentOwner(&current)&&current.token==o.config.attemptToken&&current.call_id==o.call&&current.thread_id==o.thread&&current.slot==o.slot&&GetCurrentThreadId()==o.thread;}
static bool receipt(Adapter&o,lc::Report&r){
    lc::Snapshot(*o.config.lifecycle,r);by::Report b{};by::Snapshot(*o.config.bytes,b);
    return r.receiptReady&&r.token==o.config.attemptToken&&b.observedWorkerAndBytes&&b.token==r.token&&b.load==r.load&&b.title==r.title&&
        b.workerCall==r.frozenBytes.workerCall&&b.readCall==r.frozenBytes.readCall&&b.bytesMatched&&b.nativeResult==1&&
        !memcmp(b.sha256,wp().file.sha256,32)&&r.completedCall>r.joinedCall&&r.joinedCall>r.boundCall;
}
static bool stack(Adapter&o,DWORD&count){
    const auto manager=o.config.base+0x19E7310;auto n=at<std::uint64_t>(manager+0x10),array=at<uintptr_t>(manager+0x20);
    if((n!=3&&n!=4)||!array)return false;
    auto first=at<uintptr_t>(array),second=at<uintptr_t>(array+8),third=at<uintptr_t>(array+16);
    if(!first||!second||third!=o.report.title||memcmp(reinterpret_cast<void*>(first+0x70),"CRootState",11)||memcmp(reinterpret_cast<void*>(second+0x70),"CMotorGameState",16))return false;
    // Historical Load is compared only as an address value. Never read its VT,
    // worker, closure, fields or semantic maps, even when it remains on stack.
    if(n==4&&at<uintptr_t>(array+24)!=o.report.historicalLoad)return false;
    count=DWORD(n);return at<std::uint64_t>(manager+0x10)==n&&at<uintptr_t>(manager+0x20)==array&&at<uintptr_t>(array+16)==third;
}
static bool personForce(uintptr_t b,uintptr_t root,uintptr_t person,WORD id,BYTE districtId,BYTE forceId){
    if(!person||at<uintptr_t>(person)!=b+0x12A00D0||at<WORD>(person+0x10)!=id||at<BYTE>(person+0x118)!=districtId)return false;
    auto district=at<uintptr_t>(root+0xDE40+districtId*8);
    return district&&at<uintptr_t>(district)==b+0x129FEC8&&at<BYTE>(district+0x10)==forceId&&at<BYTE>(district+0x11)!=0&&at<WORD>(district+0x12)==id;
}
static unsigned capturedSource47=0,capturedTarget47=0;
static bool worldRelations(Adapter&o,bool after,bool capture){
    auto b=o.config.base,root=at<uintptr_t>(b+0x1FCA1E0),world=root?at<uintptr_t>(root+0x85130):0,title=o.report.title;
    if(!root||!world||at<uintptr_t>(root)!=b+0x12AA6B0||at<uintptr_t>(world)!=b+0x12AA638||at<uintptr_t>(title)!=b+0x12DAAF0||
       memcmp(reinterpret_cast<void*>(title+0x70),"CTitleState",12)||at<std::int32_t>(title+0x47C)!=63)return false;
    DWORD phase=at<DWORD>(title+0x470),count=0;
    // Actual4BEEC7 stores Title+470=15 after native thread start. Both observed
    // schedules are permitted; the parent may advance13->15 during the worker.
    if((phase!=13&&phase!=15)||!stack(o,count))return false;
    phase=at<DWORD>(title+0x470);
    if((phase!=13&&phase!=15)||(count==3&&phase!=15))return false;
    if(at<WORD>(world+0x34)!=wp().loaded.year||at<BYTE>(world+0x36)!=wp().loaded.month||at<BYTE>(world+0x37)!=wp().loaded.day||at<BYTE>(world+0x38)!=0||at<DWORD>(world+0x40)!=1)return false;
    if(at<BYTE>(world+0x3A)!=(after?wp().target.force:wp().source.force)||at<BYTE>(world+0x165D)!=(after?1:2)||(!after&&at<DWORD>(world+0x20A8)!=1))return false;
    pair::Pair source{at<uintptr_t>(root+0xDCA0+wp().source.force*8),at<uintptr_t>(root+0x148+wp().source.ruler*8)},target{at<uintptr_t>(root+0xDCA0+wp().target.force*8),at<uintptr_t>(root+0x148+wp().target.ruler*8)};
    if(!source.force||!target.force||at<uintptr_t>(source.force)!=b+0x129FE58||at<uintptr_t>(target.force)!=b+0x129FE58||
       at<WORD>(source.force+0x10)!=wp().source.ruler||at<WORD>(target.force+0x10)!=wp().target.ruler||
       !personForce(b,root,source.person,wp().source.ruler,wp().source.district,wp().source.force)||!personForce(b,root,target.person,wp().target.ruler,wp().target.district,wp().target.force))return false;
    // Same opaque-field rule as dynamic identity: capture in actual owned
    // Title BEFORE, then demand stability throughout its commit and return.
    if(source.force==target.force||source.person==target.person)return false;
    const auto source47=at<BYTE>(source.force+0x47),target47=at<BYTE>(target.force+0x47);
    if(capture){capturedSource47=source47;capturedTarget47=target47;}
    else if(source47!=capturedSource47||target47!=capturedTarget47)return false;
    if(capture)TI_LOCK(o,o.report.root=root;o.report.world=world;o.report.source=source;o.report.target=target;o.report.phaseBefore=phase;o.report.stackBefore=count);
    else if(root!=o.report.root||world!=o.report.world||!equal(source,o.report.source)||!equal(target,o.report.target))return false;
    if(after)TI_LOCK(o,o.report.phaseAfter=phase;o.report.stackAfter=count;o.report.worldForceAfter=at<BYTE>(world+0x3A);o.report.worldControlAfter=at<BYTE>(world+0x165D));
    return true;
}
static bool validate(Adapter&o,Point point,bool targetPair){
    if(get(o.stopped)||get(o.error)||!owner(o))return false;
    lc::Report r{};if(!receipt(o,r)||r.title!=o.report.title||r.load!=o.report.historicalLoad||r.completedCall!=o.report.completionCall)return false;
    if(at<uintptr_t>(o.report.title+0x520+0x48)!=o.report.callable||at<uintptr_t>(o.report.callable)!=o.config.base+0x138E8C0||at<uintptr_t>(o.report.callable+8)!=o.config.base+0x4DA390)return false;
    if(!worldRelations(o,false,false)||!equal(at<pair::Pair>(o.report.title+0x4A0),targetPair?o.report.target:o.report.source))return false;
    return o.config.validateAttachment(o.config.validationContext,point,o.report.title,o.report.root,o.report.world)&&!get(o.stopped)&&!get(o.error)&&owner(o);
}
static bool commitGuard(void*context,pair::Point p,const pair::Input&i){
    auto&o=*static_cast<Adapter*>(context);
    if(i.destination!=reinterpret_cast<pair::Pair*>(o.report.title+0x4A0)||!equal(i.source,o.report.source)||!equal(i.target,o.report.target)||i.attempt!=o.config.attemptToken||
       i.callId!=o.call||i.thread!=o.thread||wcscmp(i.intentPath,o.intentPath)||memcmp(i.ownerBinding,o.config.ownerBinding,32))return false;
    auto point=p==pair::Point::Preflight?Point::Preflight:p==pair::Point::BeforeIntent?Point::BeforeIntent:p==pair::Point::BeforeCompareExchange?Point::BeforeCompareExchange:Point::AfterCompareExchange;
    return validate(o,point,p==pair::Point::AfterCompareExchange);
}
bool Initialize(Adapter&o,const Config&c) noexcept {
    if(InterlockedCompareExchange(&o.initialized,1,0))return false;
    __try {
        BYTE ownerByte=0;for(auto x:c.ownerBinding)ownerByte|=x;
        if(!b_warm_profile::Ready()||c.base<0x10000||!c.attemptToken||!c.lifecycle||!c.bytes||!c.intentPath||!ownerByte||!c.validateAttachment||
           c.lifecycle->config.base!=c.base||c.lifecycle->config.attemptToken!=c.attemptToken||c.lifecycle->config.bytes!=c.bytes||get(c.lifecycle->initialized)!=2){fail(o,Error::Config);return false;}
        bool terminated=false;for(unsigned i=0;i<1024;++i){o.intentPath[i]=c.intentPath[i];if(!o.intentPath[i]){terminated=i!=0;break;}}
        if(!terminated){fail(o,Error::Config);return false;}
        o.config=c;o.config.intentPath=o.intentPath;o.report.token=c.attemptToken;InterlockedExchange(&o.initialized,2);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());return false;}
}
void Stop(Adapter&o) noexcept {InterlockedExchange(&o.stopped,1);fail(o,Error::Stopped);}
void Snapshot(Adapter&o,Report&out) noexcept {
    AcquireSRWLockShared(&o.lock);out=o.report;ReleaseSRWLockShared(&o.lock);out.error=get(o.error);out.stopped=get(o.stopped);
    out.receiptReady=!out.error&&!out.stopped&&out.commitReturned&&out.casApplied&&out.intentDurable&&out.postGuard&&out.nativeReturned&&out.identityObserved&&
        out.beforeCalls==1&&out.afterCalls==1&&out.finallyCalls==1&&!out.active&&!out.abnormal;
}
void Before(const CheckpointLoadWorkerFrame*f,void*context) noexcept {
    auto&o=*static_cast<Adapter*>(context);
    __try {
        if(get(o.initialized)!=2)return;
        const auto callable=uintptr_t(f->args[0]);if(!callable)return;
        if(at<uintptr_t>(callable+8)!=o.config.base+0x4DA390){TI_LOCK(o,++o.report.otherWorkers);return;}
        if(get(o.stopped)){fail(o,Error::Stopped);return;}
        lc::Report r{};if(!receipt(o,r)){fail(o,Error::Receipt);return;}
        auto caller=at<uintptr_t>(f->caller_entry_rsp);
        if(f->slot!=0||f->thread_id!=GetCurrentThreadId()||caller!=expectedCaller(o.config)||at<uintptr_t>(callable)!=o.config.base+0x138E8C0||
           at<uintptr_t>(r.title+0x520+0x48)!=callable){fail(o,Error::Worker);return;}
        if(InterlockedCompareExchange(&o.claimed,1,0)){fail(o,Error::Duplicate);return;}
        if(!CheckpointLoadWorkerClaim(f,o.config.attemptToken)){fail(o,Error::Owner);return;}
        TI_LOCK(o,o.call=f->call_id;o.thread=f->thread_id;o.slot=f->slot;o.rsp=f->caller_entry_rsp;memcpy(o.args,f->args,sizeof o.args);
            o.report.title=r.title;o.report.historicalLoad=r.load;o.report.completionCall=r.completedCall;o.report.callable=callable;o.report.workerCall=f->call_id;o.report.thread=f->thread_id;o.report.caller=caller;++o.report.beforeCalls;o.report.active=1);
        InterlockedExchange(&o.claimed,2);
        if(!worldRelations(o,false,true)){fail(o,Error::World);return;}
        if(!validate(o,Point::Before,false)){fail(o,Error::Guard);return;}
        pair::Input input{};input.destination=reinterpret_cast<pair::Pair*>(r.title+0x4A0);input.source=o.report.source;input.target=o.report.target;
        input.attempt=o.config.attemptToken;input.callId=o.call;input.thread=o.thread;input.intentPath=o.intentPath;memcpy(input.ownerBinding,o.config.ownerBinding,32);
        pair::Access access{&o,commitGuard};bool committed=o.committer.Commit(input,access);const auto&c=o.committer.GetReport();
        TI_LOCK(o,o.report.commitState=unsigned(c.state);o.report.commitCalls=c.invocations;o.report.casAttempts=c.casAttempts;o.report.casApplied=c.casApplied;
            o.report.intentCreated=c.intentCreated;o.report.intentDurable=c.intentDurable;o.report.postGuard=c.postGuard;o.report.commitReturned=committed;
            o.report.commitException=c.exceptionCode;o.report.commitOsError=c.osError;o.report.observedPair=c.observed;strncpy_s(o.report.commitStage,c.stage,_TRUNCATE));
        if(!committed)fail(o,Error::Commit);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
static bool same(Adapter&o,const CheckpointLoadWorkerFrame*f){return get(o.claimed)==2&&o.call==f->call_id&&o.thread==f->thread_id&&o.slot==f->slot&&o.rsp==f->caller_entry_rsp&&!memcmp(o.args,f->args,sizeof o.args);}
void After(const CheckpointLoadWorkerFrame*f,void*context) noexcept {
    auto&o=*static_cast<Adapter*>(context);
    __try {
        if(!same(o,f))return;
        TI_LOCK(o,++o.report.afterCalls;o.report.nativeReturned=1;o.report.originalRax=f->result_rax;memcpy(o.report.originalXmm0,f->result_xmm0,16));
        if(get(o.error)||get(o.stopped))return;
        if(!owner(o)||!o.report.commitReturned||!worldRelations(o,true,false)||!equal(at<pair::Pair>(o.report.title+0x4A0),o.report.target)||
           !o.config.validateAttachment(o.config.validationContext,Point::After,o.report.title,o.report.root,o.report.world)){fail(o,Error::After);return;}
        TI_LOCK(o,o.report.identityObserved=1);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void Finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*exit,void*context) noexcept {
    auto&o=*static_cast<Adapter*>(context);
    __try {
        if(!same(o,f))return;
        if(!owner(o)||!exit->claimed||exit->token!=o.config.attemptToken)fail(o,Error::Owner);
        TI_LOCK(o,++o.report.finallyCalls;o.report.active=0;if(exit->abnormal)++o.report.abnormal);
        if(exit->abnormal)fail(o,Error::Abnormal);
        if(!exit->abnormal&&!o.report.nativeReturned)fail(o,Error::After);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
}
