// Included inside the observer's private namespace, after its stable context.
namespace hw=checkpoint_native_input_hwbp;namespace pd=checkpoint_bound_input_pending;
hw::Context hardware;pd::Adapter admission;pd::Config admissionConfig{};
CheckpointPushFrame admissionFrame{};
volatile LONG admissionReady=0,admissionRunning=0;
void* nativeOriginal=nullptr;
struct alignas(16) PrefetchNativeCall {
    std::uint64_t args[4]{},result_rax=0;
    void* original=nullptr;
    unsigned char result_xmm0[16]{};
};
static_assert(sizeof(PrefetchNativeCall)==0x40&&offsetof(PrefetchNativeCall,result_xmm0)==0x30);
extern "C" std::uint64_t CheckpointLivePrefetchOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CheckpointLivePrefetchCallOriginal(PrefetchNativeCall*);
bool readable(std::uintptr_t p,std::size_t n){
    if(!p||!n||p+n<p)return false;const auto end=p+n;
    while(p<end){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
        (m.Protect&(PAGE_GUARD|PAGE_NOACCESS))||!(m.Protect&(PAGE_READONLY|PAGE_READWRITE|PAGE_WRITECOPY|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))return false;
        const auto next=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;
    }return true;
}
bool extensionContext(){
    const auto m=config.base+0x19E7310;
    if(!config.generation||config.expectedMode>1||config.helperDeadlineMs<1||config.helperDeadlineMs>10000||!config.cache||!config.stack||
       config.stackCapacity<5||config.stackCapacity>4096||config.queueCapacity>4096||
       (!config.queueCapacity&&config.queue)||(config.queueCapacity&&!config.queue))return false;
    unsigned first=0,second=0;for(unsigned i=0;i<16;++i){first|=config.attachment[i];second|=config.attachment[i+16];}if(!first||!second)return false;
    if(at<std::uint64_t>(config.base+0x2025318)!=config.cache||at<std::uint64_t>(m+0x20)!=config.stack||at<std::uint64_t>(m+0x18)!=config.stackCapacity||
       at<std::uint64_t>(m+0x40)!=config.queue||at<std::uint64_t>(m+0x38)!=config.queueCapacity||at<std::uint64_t>(m+0x30)!=0)return false;
    return readable(config.states[4],0x668)&&readable(config.toolbar,0x8c)&&readable(config.states[2],0x488)&&readable(config.panel,0x1f8)&&
        readable(m,0x50)&&readable(config.stack,config.stackCapacity*8)&&(!config.queueCapacity||readable(config.queue,config.queueCapacity*16))&&
        readable(config.cache,0x3f4)&&at<DWORD>(config.cache+8)==config.expectedMode&&at<LONG>(config.cache+0x3ec)==-1&&!at<DWORD>(config.cache+0x3f0);
}
pd::Span refuseQueue(void*,std::uintptr_t,std::size_t)noexcept{
    // This observer never authorizes a queue and never invokes this resolver.
    AcquireSRWLockExclusive(&lock);++report.admissionResolverCalls;ReleaseSRWLockExclusive(&lock);return{};
}
void binding(hw::Binding& b){std::memcpy(b.attempt.data(),config.attachment,16);std::memcpy(b.attachment.data(),config.attachment+16,16);b.owner_generation=config.generation;}
bool initializeHardware(){
    hw::Config h{};binding(h.binding);h.site_rip=config.base+0x3f9daf;h.helper_deadline_ms=config.helperDeadlineMs;
#ifdef CHECKPOINT_LIVE_USER_THREADS_FIXTURE
    h.site_rip=config.reserved[1];
#endif
    return hw::Initialize(hardware,h);
}
void prepareLocked(const CheckpointPushFrame& f){
    ++report.admissionClaimed;
    if(!extensionContext()){++report.admissionErrors;report.admissionBindError=unsigned(pd::Error::Layout);return;}
    auto& c=admissionConfig;c.profile_base=config.base;binding(c.binding);std::memcpy(c.states,config.states,sizeof c.states);
    c.user={reinterpret_cast<const std::uint8_t*>(config.states[4]),0x668};c.toolbar={reinterpret_cast<const std::uint8_t*>(config.toolbar),0x8c};
    c.game={reinterpret_cast<const std::uint8_t*>(config.states[2]),0x488};c.panel={reinterpret_cast<const std::uint8_t*>(config.panel),0x1f8};
    c.manager={reinterpret_cast<const std::uint8_t*>(config.base+0x19e7310),0x50};c.stack={reinterpret_cast<const std::uint8_t*>(config.stack),config.stackCapacity*8};
    c.queue={reinterpret_cast<const std::uint8_t*>(config.queue),config.queueCapacity*16};c.load_cache={reinterpret_cast<const std::uint8_t*>(config.cache),0x3f4};
    c.expected_initial_cache_mode=config.expectedMode;c.resolve_created_queue=refuseQueue;
    const auto e=admission.Bind(c);report.admissionBindError=unsigned(e);
    if(e!=pd::Error::None){++report.admissionErrors;return;}
    admissionFrame=f;report.pendingBefore=admission.ObserveBefore(c.binding,f);
    if(report.pendingBefore.error!=pd::Error::None)++report.admissionErrors;
    InterlockedExchange(&admissionReady,1);
}
hw::PendingReport capture(void*,const hw::Binding& b,std::uint64_t c,const void*u)noexcept{return admission.ObserveBeforeFetch(b,c,u);}
void finishNative(bool abnormal)noexcept{
    hw::Finish(hardware);hw::HardwareReceipt r{};hw::Snapshot(hardware,r);
    AcquireSRWLockExclusive(&lock);report.hardware=r;++report.admissionFinished;if(abnormal)++report.admissionAbnormal;
    // Stop closes new callbacks and marks this still-in-flight observation as
    // incomplete. It never mutates an already-frozen hardware receipt.
    if(r.error!=hw::Error::None||!r.restored||r.restore_uncertain||InterlockedCompareExchange(&stopped,0,0))++report.admissionErrors;ReleaseSRWLockExclusive(&lock);
}
void runNative(PrefetchNativeCall& call){
    call.original=nativeOriginal;bool sample=false;
    AcquireSRWLockExclusive(&lock);
    if(InterlockedCompareExchange(&admissionReady,0,0)&&admissionFrame.thread_id==GetCurrentThreadId()&&!std::memcmp(call.args,admissionFrame.args,sizeof call.args)&&
       !InterlockedCompareExchange(&admissionRunning,1,0)){sample=true;++report.admissionStarted;}
    ReleaseSRWLockExclusive(&lock);
    if(!sample){CheckpointLivePrefetchCallOriginal(&call);return;}
    const bool began=hw::Begin(hardware,capture,nullptr,admissionConfig.binding,admissionFrame.call_id,reinterpret_cast<void*>(call.args[0]));
    AcquireSRWLockExclusive(&lock);report.admissionBeginOk=began?1:0;ReleaseSRWLockExclusive(&lock);
    __try{CheckpointLivePrefetchCallOriginal(&call);}
    __finally{finishNative(AbnormalTermination()!=FALSE);}
}
void completeLocked(const CheckpointPushFrame& f){
    if(!InterlockedCompareExchange(&admissionReady,0,0))return;
    report.pendingAfter=admission.ObserveAfter(admissionConfig.binding,f);
    if(report.pendingAfter.error!=pd::Error::None)++report.admissionErrors;
    const auto close=admission.CloseAfter(admissionConfig.binding,f.call_id);report.admissionCloseError=unsigned(close);
    if(close==pd::Error::None)++report.admissionClosed;else ++report.admissionErrors;
}
