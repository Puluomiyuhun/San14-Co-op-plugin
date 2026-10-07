#include "checkpoint_dynamic_cc_load_observer.h"
#include "native_storage_read_core.h"
#include <cstring>
#include <limits>
namespace checkpoint_dynamic_cc_load_observer {
#define LOCKED(o,code) do{AcquireSRWLockExclusive(&(o).lock);__try{code;}__finally{ReleaseSRWLockExclusive(&(o).lock);}}while(0)
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static LONG get(volatile LONG& v){return InterlockedCompareExchange(&v,0,0);}
static void fail(Observer&o,Error e,DWORD exception=0){InterlockedCompareExchange(&o.error,LONG(e),0);if(exception)LOCKED(o,o.report.exceptionCode=exception);}
static bool guarded(Observer&o,Point p){
    if(get(o.stopped)||get(o.initialized)!=2)return false;
    return o.config.validateAttachment(o.config.validationContext,p,o.report.load,o.report.title);
}
static uintptr_t workerCaller(const Config&c){
#ifdef CHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE
    return c.fixtureWorkerCaller;
#else
    return c.base+0x834D9B;
#endif
}
static uintptr_t readCaller(const Config&c){
#ifdef CHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE
    return c.fixtureReadCaller;
#else
    return c.base+0x3A9227;
#endif
}
static uintptr_t parentCaller(const Config&c){
#ifdef CHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE
    return c.fixtureParentCaller;
#else
    return c.base+0x2F77CF;
#endif
}
static bool readable(uintptr_t p,size_t n){
    if(p<0x10000||!n||p>std::numeric_limits<uintptr_t>::max()-n)return false;
    const auto end=p+n;
    while(p<end){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||(m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;
        const DWORD protection=m.Protect&0xff;if(protection!=PAGE_READONLY&&protection!=PAGE_READWRITE&&protection!=PAGE_WRITECOPY&&protection!=PAGE_EXECUTE_READ&&protection!=PAGE_EXECUTE_READWRITE&&protection!=PAGE_EXECUTE_WRITECOPY)return false;
        const auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next;
    }return true;
}
static bool owner(Observer&o,const CheckpointLoadWorkerFrame*f){
    if(get(o.workerClaimed)!=2)return false;
    CheckpointLoadWorkerOwner current{};
    return CheckpointLoadWorkerCurrentOwner(&current)&&current.token==o.config.attemptToken&&current.slot==0&&
        current.call_id==o.workerFrame.call_id&&current.thread_id==o.workerFrame.thread_id&&current.thread_id==f->thread_id;
}
static bool same(const CheckpointLoadWorkerFrame&a,const CheckpointLoadWorkerFrame&b){return a.call_id==b.call_id&&a.slot==b.slot&&a.thread_id==b.thread_id&&a.caller_entry_rsp==b.caller_entry_rsp&&!memcmp(a.args,b.args,sizeof a.args);}
bool Initialize(Observer&o,const Config&c) noexcept {
    if(InterlockedCompareExchange(&o.initialized,1,0))return false;
    if(!checkpoint_dynamic_file_profile::Capture(c.profile,o.profile)||c.base<0x10000||!c.storage||!c.storageVtable||!c.readMethod||!c.attemptToken||!c.validateAttachment){fail(o,Error::Configuration);return false;}
    o.config=c;o.config.profile=&o.profile;o.report.token=c.attemptToken;InterlockedExchange(&o.initialized,2);return true;
}
bool BindLoad(Observer&o,uintptr_t load,uintptr_t title) noexcept {
    if(get(o.initialized)!=2||get(o.stopped)||!load||!title||InterlockedCompareExchange(&o.bound,1,0))return false;
    __try {
        LOCKED(o,o.report.load=load;o.report.title=title;o.report.worker=load+0x478);
        if(at<uintptr_t>(load)!=o.config.base+0x12DBD68||at<DWORD>(load+0x470)!=1||!guarded(o,Point::Bind)){fail(o,Error::Binding);return false;}
        InterlockedExchange(&o.bound,2);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());return false;}
}
void Stop(Observer&o) noexcept {InterlockedExchange(&o.stopped,1);fail(o,Error::Stopped);}
void Snapshot(Observer&o,Report&out) noexcept {
    AcquireSRWLockShared(&o.lock);out=o.report;ReleaseSRWLockShared(&o.lock);
    out.error=get(o.error);out.stopped=get(o.stopped);
    out.observedWorkerAndBytes=!out.error&&!out.stopped&&out.bytesMatched&&out.workerReturned&&
        out.workerBefore==1&&out.workerAfter==1&&out.workerFinally==1&&out.readBefore==1&&out.readAfter==1&&out.readFinally==1&&
        !out.workerAbnormal&&!out.readAbnormal&&!out.activeWorker&&!out.activeRead&&out.ownedReadCandidates==1;
}
void WorkerBefore(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        const auto callable=uintptr_t(f->args[0]);
        if(get(o.initialized)!=2||!callable)return;
        const auto payload=at<uintptr_t>(callable+8);
        if(payload!=o.config.base+0x508B40){LOCKED(o,++o.report.otherWorkers;if(payload==o.config.base+0x4DA390)++o.report.titleWorkers);return;}
        if(get(o.bound)!=2||get(o.stopped)){fail(o,Error::Binding);return;}
        auto caller=at<uintptr_t>(f->caller_entry_rsp);
        if(f->slot!=0||f->thread_id!=GetCurrentThreadId()||caller!=workerCaller(o.config)||
           at<uintptr_t>(callable)!=o.config.base+0x138E8C0||at<uintptr_t>(o.report.worker+0x48)!=callable){fail(o,Error::WorkerIdentity);return;}
        if(!guarded(o,Point::WorkerBefore)){fail(o,Error::Guard);return;}
        if(InterlockedCompareExchange(&o.workerClaimed,1,0)){fail(o,Error::WorkerDuplicate);return;}
        if(!CheckpointLoadWorkerClaim(f,o.config.attemptToken)){fail(o,Error::Owner);return;}
        LOCKED(o,o.workerFrame=*f;++o.report.workerBefore;o.report.activeWorker=1;o.report.callable=callable;
            o.report.workerCall=f->call_id;o.report.workerThread=f->thread_id;o.report.workerCaller=caller);
        InterlockedExchange(&o.workerClaimed,2);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void WorkerAfter(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        if(get(o.workerClaimed)!=2||!same(*f,o.workerFrame))return;
        LOCKED(o,++o.report.workerAfter;o.report.workerRax=f->result_rax;memcpy(o.report.workerXmm0,f->result_xmm0,16));
        if(!owner(o,f)||!guarded(o,Point::WorkerAfter)){fail(o,Error::Guard);return;}
        DWORD result=at<DWORD>(o.config.base+0x201EC08);
        LOCKED(o,o.report.nativeResult=result;o.report.workerReturned=1);
        if(result!=1)fail(o,Error::NativeResult);
        if(o.report.readAfter!=1||!o.report.bytesMatched||o.report.activeRead)fail(o,Error::MissingRead);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void WorkerFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*exit,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        if(get(o.workerClaimed)!=2||!same(*f,o.workerFrame))return;
        if(!owner(o,f)||!exit->claimed||exit->token!=o.config.attemptToken)fail(o,Error::Owner);
        LOCKED(o,++o.report.workerFinally;o.report.activeWorker=0;if(exit->abnormal)++o.report.workerAbnormal);
        if(exit->abnormal)fail(o,Error::Abnormal);
        if(!exit->abnormal&&(!o.report.workerReturned||o.report.activeRead))fail(o,Error::Unpaired);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void ReadBefore(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        if(!owner(o,f)){LOCKED(o,++o.report.unownedReads);return;}
        LOCKED(o,++o.report.ownedReadCandidates);
        if(InterlockedCompareExchange(&o.readClaimed,1,0)){fail(o,Error::ReadDuplicate);return;}
        // Track even malformed owned calls through FINALLY; they still forward.
        LOCKED(o,o.readFrame=*f;++o.report.readBefore;o.report.activeRead=1;o.report.readCall=f->call_id;o.report.readThread=f->thread_id;
            o.report.buffer=f->args[2];o.report.requested=std::uint32_t(f->args[3]));
        InterlockedExchange(&o.readClaimed,2);
        const auto caller=at<uintptr_t>(f->caller_entry_rsp),parent=at<uintptr_t>(f->caller_entry_rsp+0x50);
        LOCKED(o,o.report.readCaller=caller;o.report.parentCaller=parent);
        if(f->slot!=1||caller!=readCaller(o.config)||parent!=parentCaller(o.config)){fail(o,Error::ReadPath);return;}
        if(f->args[0]!=o.config.storage||std::int32_t(f->args[3])!=std::int32_t(o.profile.size)||
           !readable(f->args[1],checkpoint_dynamic_file_profile::NameBytes)||memcmp(reinterpret_cast<void*>(f->args[1]),o.profile.name,checkpoint_dynamic_file_profile::NameBytes)||
           !readable(f->args[2],o.profile.size)){fail(o,Error::ReadArguments);return;}
        if(!guarded(o,Point::ReadBefore))fail(o,Error::Guard);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void ReadAfter(const CheckpointLoadWorkerFrame*f,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        if(get(o.readClaimed)!=2||!same(*f,o.readFrame))return;
        LOCKED(o,++o.report.readAfter;o.report.readRax=f->result_rax;o.report.returned=std::uint32_t(f->result_rax);memcpy(o.report.readXmm0,f->result_xmm0,16));
        if(!owner(o,f)||!guarded(o,Point::ReadAfter)){fail(o,Error::Guard);return;}
        if(std::int32_t(f->result_rax)!=std::int32_t(o.profile.size)){fail(o,Error::ReadReturn);return;}
        if(get(o.error))return;
        unsigned char hash[32]{};
        if(!readable(f->args[2],o.profile.size)||!native_storage_read::Sha256(reinterpret_cast<void*>(f->args[2]),o.profile.size,hash)){fail(o,Error::Memory);return;}
        LOCKED(o,memcpy(o.report.sha256,hash,32));
        if(memcmp(hash,o.profile.sha256,32)){fail(o,Error::ReadHash);return;}
        LOCKED(o,o.report.bytesMatched=1);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
void ReadFinally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*exit,void*ctx) noexcept {
    auto&o=*static_cast<Observer*>(ctx);
    __try {
        if(get(o.readClaimed)!=2||!same(*f,o.readFrame))return;
        LOCKED(o,++o.report.readFinally;o.report.activeRead=0;if(exit->abnormal)++o.report.readAbnormal);
        if(!owner(o,f)||exit->claimed)fail(o,Error::Owner);
        if(exit->abnormal)fail(o,Error::Abnormal);
        if(!exit->abnormal&&o.report.readAfter!=1)fail(o,Error::Unpaired);
    }__except(EXCEPTION_EXECUTE_HANDLER){fail(o,Error::Memory,GetExceptionCode());}
}
}
