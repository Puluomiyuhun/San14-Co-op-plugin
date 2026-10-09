// Explicit factory environment-mapping successor; production configure/guards unchanged.
#include "b_warm_profile.h"
static const b_warm_profile::Profile& wp() noexcept {return b_warm_profile::Get();}
#include "checkpoint_complete_live_owner.h"
#include "checkpoint_authorized_forward_admission_controller.h"
#include "checkpoint_live_runtime_guards_v2.h"
#include "checkpoint_serialized_storage_gate.h"
#include "b_warm_retire_session.h"
#include <cstring>
#include <cwchar>

namespace checkpoint_complete_live_owner {
namespace ns=checkpoint_forward_native_session;namespace ad=checkpoint_authorized_forward_admission;
namespace qa=checkpoint_native_queue_adapter;namespace hw=checkpoint_native_input_hwbp;
namespace pr=checkpoint_forward_planning_observer_v2;namespace gd=checkpoint_live_runtime_guards_v2;
namespace sg=checkpoint_serialized_storage_gate;namespace sb=checkpoint_live_storage_binding;
namespace {
constexpr unsigned char GameSha[]={0x42,0xd5,0x3b,0xb4,0x2c,0x03,0x3c,0x60,0x27,0xb6,0xda,0x75,0xe8,0x07,0x7f,0x41,0x70,0xf4,0xd6,0x84,0xab,0xb0,0xf5,0x74,0x83,0xa6,0x61,0x22,0x5d,0x05,0x20,0x25};
LONG get(volatile LONG&v)noexcept{return InterlockedCompareExchange(&v,0,0);}
std::uint64_t processBirth()noexcept{FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
bool nonzero(const unsigned char*p,size_t n)noexcept{unsigned a=0;for(size_t i=0;i<n;++i)a|=p[i];return a!=0;}
bool path(const wchar_t*p)noexcept{return p[0]&&p[1]==L':'&&p[2]==L'\\'&&!p[511]&&!wcsstr(p,L"\\..\\");}
bool absent(const wchar_t*p)noexcept{if(GetFileAttributesW(p)!=INVALID_FILE_ATTRIBUTES)return false;const auto e=GetLastError();return e==ERROR_FILE_NOT_FOUND||e==ERROR_PATH_NOT_FOUND;}
template<size_t N>void copyText(char(&out)[N],const char*p)noexcept{
    __try{if(!p)return;for(size_t i=0;i<N-1&&p[i];++i)out[i]=p[i];}
    __except(EXCEPTION_EXECUTE_HANDLER){out[0]=0;}
}
void* entries(unsigned i)noexcept{void* const p[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};return i<6?p[i]:nullptr;}
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
// Private own-process environment adaptation. Never present in DLL exports,
// production Config or production binary; validators/Gate are not substituted.
struct FixtureAddresses {
    ad::Original userOriginal=nullptr;qa::Native queueNative=nullptr;
    uintptr_t hardwareSite=0,userCaller=0,workerCaller=0,readCaller=0,updateCaller=0,parentCaller=0,menuCaller=0,gameCaller=0;
    void* originals[5]{};
} fixtureAddresses;
#endif
struct Owner {
    SRWLOCK control=SRWLOCK_INIT;
    Config config{};gd::Stamp stamp{};ns::Session session;ad::Controller admission;
    qa::Adapter queue;hw::Context hardware;pr::Observer planning;gd::Context guards;sg::Gate storage;
    HMODULE module=nullptr;
    volatile LONG once=0,state=0,error=0,exception=0,osError=0,installCalls=0,intentCreated=0,intentDurable=0,modulePinned=0,installed=0,stop=0,restoreCalls=0,restoreReturned=0;
    volatile LONG64 sequence=0;
    bool fail(LONG e,DWORD ex=0,DWORD os=0)noexcept{InterlockedCompareExchange(&error,e,0);if(ex)InterlockedExchange(&exception,LONG(ex));if(os)InterlockedExchange(&osError,LONG(os));InterlockedExchange(&state,4);return false;}
    bool shape()noexcept{
        const auto&c=config;
        if(!b_warm_profile::Ready()||c.magic!=Magic||c.size!=sizeof(Config)||c.version!=Version||c.reserved||c.reserved2||c.reserved3||
           c.pid!=GetCurrentProcessId()||c.birth!=processBirth()||!c.attempt||!c.epoch||!c.generation||
           !nonzero(c.attachment,32)||!nonzero(c.ownerBinding,32)||!nonzero(c.nonce,32)||std::memcmp(c.gameSha256,GameSha,32)||
           c.expectedMode!=0||c.helperDeadlineMs<50||c.helperDeadlineMs>5000||c.stackCapacity<5||c.stackCapacity>4096||
           c.queueCapacity||c.queue||!c.root||!c.world||!c.cache||!c.keyboard||!c.toolbar||!c.panel||!c.stack||
           c.ownedReadBridge.address!=uintptr_t(&CheckpointLoadWorkerBridge1)||
           c.ownedReadBridge.moduleIndex>=c.storageModuleCount||c.storageModuleCount>3||c.storageModules[c.ownedReadBridge.moduleIndex].base!=uintptr_t(module))return false;
#ifndef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
        if(c.base!=uintptr_t(GetModuleHandleW(nullptr))||c.storageModuleCount!=3)return false;
#else
        if(c.storageModuleCount!=1)return false;
#endif
        for(auto s:c.states)if(!s)return false;
        for(auto p:{c.localPath,c.installIntent,c.requestIntent,c.identityIntent})if(!path(p))return false;
        const auto leaf=wcsrchr(c.localPath,L'\\');if(!leaf||wcscmp(leaf+1,L"svdexccSC03.s14"))return false;
        const wchar_t* paths[]={c.localPath,c.installIntent,c.requestIntent,c.identityIntent};
        for(unsigned i=0;i<4;++i)for(unsigned j=0;j<i;++j)if(!_wcsicmp(paths[i],paths[j]))return false;
        return absent(c.installIntent)&&absent(c.requestIntent)&&absent(c.identityIntent);
    }
    static bool storageValid(void*p)noexcept{return static_cast<Owner*>(p)->storage.Valid();}
    static bool storageOwner(void*p,const sb::Attachment&a,sb::Point)noexcept{
        auto&o=*static_cast<Owner*>(p);const auto&c=o.config;
        return a.pid==c.pid&&a.birth==c.birth&&a.base==c.base&&a.attempt==c.attempt&&a.generation==c.generation&&
            !memcmp(a.id,c.attachment,32)&&!memcmp(a.gameSha256,c.gameSha256,32)&&gd::Context::AttachmentOnly(&o.guards);
    }
    static bool storageHook(void*p,uintptr_t slot,uintptr_t original,uintptr_t bridge)noexcept{
        auto&o=*static_cast<Owner*>(p);return slot==o.config.storageVtable+8&&original==o.config.read.address&&bridge==uintptr_t(&CheckpointLoadWorkerBridge1)&&gd::Context::OwnedReadBridgeOnly(&o.guards);
    }
    static bool sessionGuard(void*p,ns::Point point)noexcept{return gd::Context::SessionGuard(&static_cast<Owner*>(p)->guards,point);}
    static void userAfter(void*p,ns::Session&s,const CheckpointPushFrame*f)noexcept{ad::Controller::UserAfter(&static_cast<Owner*>(p)->admission,s,f);}
    static void trace(void*p,ad::Event e)noexcept{
        if(e!=ad::Event::Close)return;auto&o=*static_cast<Owner*>(p);ad::Report r{};
        if(o.admission.Snapshot(r)&&(r.blocked||r.stopped))o.queue.Stop();
    }
    bool configure();
    bool reserve()noexcept{
        struct Intent{std::uint64_t magic,attempt,epoch,birth,base;DWORD pid,size;unsigned char nonce[32],binding[32],configSha[32],targetSha[32];b_warm_profile::Profile profile;};
        Intent record{b_warm_profile::Magic,config.attempt,config.epoch,config.birth,config.base,config.pid,sizeof(b_warm_profile::Config),{},{},{},{}};
        record.profile=wp();memcpy(record.nonce,config.nonce,32);memcpy(record.binding,config.ownerBinding,32);memcpy(record.targetSha,wp().file.sha256,32);
        b_warm_profile::Config accepted{};accepted.profile=wp();accepted.owner=config;
        if(!native_storage_read::Sha256(&accepted,sizeof accepted,record.configSha))return fail(7);
        auto h=CreateFileW(config.installIntent,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
        if(h==INVALID_HANDLE_VALUE)return fail(8,0,GetLastError());InterlockedExchange(&intentCreated,1);
        DWORD wrote=0;bool ok=WriteFile(h,&record,sizeof record,&wrote,nullptr)&&wrote==sizeof record&&FlushFileBuffers(h);
        auto err=ok?0:GetLastError();if(!CloseHandle(h)){ok=false;err=GetLastError();}
        if(!ok)return fail(9,0,err);InterlockedExchange(&intentDurable,1);return true;
    }
    bool installBody(const Config*supplied){
        ++installCalls;if(InterlockedCompareExchange(&once,1,0))return fail(1);
        config=*supplied;InterlockedExchange(&state,1);
        if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&InstallCheckpointCompleteLiveOwner),&module))return fail(2,0,GetLastError());
        InterlockedExchange(&modulePinned,1);if(!shape())return fail(3);
        if(!configure())return fail(4);
        if(!reserve())return false;
        if(get(stop))return fail(5);
        if(!session.ArmHooks())return fail(6);
        InterlockedExchange(&installed,1);InterlockedExchange(&state,2);return true;
    }
    bool install(const Config*c)noexcept{__try{return installBody(c);}__except(EXCEPTION_EXECUTE_HANDLER){return fail(10,GetExceptionCode());}}
    void requestStop()noexcept{InterlockedExchange(&stop,1);queue.Stop();admission.Stop();session.Stop();if(get(state)==2)InterlockedExchange(&state,3);}
    void snapshot(Report&)noexcept;
};
Owner owner;
bool Owner::configure(){
    const auto&c=config;ns::Config s{};auto&b=s.request.boundary;
    b.base=c.base;memcpy(b.states,c.states,sizeof b.states);b.root=c.root;b.world=c.world;b.cache=c.cache;b.keyboard=c.keyboard;b.attempt=c.attempt;b.expectedRng=c.rng;b.year=wp().before.year;b.month=wp().before.month;b.day=wp().before.day;b.force=wp().currentForce;
    constexpr uintptr_t slotRva[]={0x12cc4d0,0x12db4e8,0x12cc9e0,0x12dbd90,0x138e8d0};
    constexpr uintptr_t originalRva[]={0x3f9b00,0x4aa200,0x3f8140,0x4a85c0,0x4fabc0};
    for(unsigned i=0;i<6;++i)s.hooks[i]={reinterpret_cast<void*volatile*>(i==5?c.storageVtable+8:c.base+slotRva[i]),reinterpret_cast<void*>(i==5?c.read.address:c.base+originalRva[i]),entries(i)};
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
    for(unsigned i=0;i<5;++i)s.hooks[i].original=fixtureAddresses.originals[i];
#endif
    stamp.attempt=c.attempt;stamp.epoch=c.epoch;memcpy(stamp.owner_binding,c.ownerBinding,32);memcpy(stamp.checkpoint_sha256,wp().file.sha256,32);
    gd::Config g{};g.pid=c.pid;g.birth=c.birth;g.base=c.base;g.owner_module=uintptr_t(module);g.expected=stamp;g.current_stamp=&stamp;g.initial=b;
    memcpy(g.hooks,s.hooks,sizeof g.hooks);g.queue=&queue;g.storage_valid=storageValid;g.storage_context=this;g.request_intent=c.requestIntent;g.identity_intent=c.identityIntent;memcpy(g.supported_image_sha256,c.gameSha256,32);
    if(!guards.Initialize(g))return false;
    sb::Config storageConfig{};auto&a=storageConfig.attachment;a.pid=c.pid;a.birth=c.birth;a.attempt=c.attempt;a.generation=c.generation;a.base=c.base;memcpy(a.id,c.attachment,32);memcpy(a.gameSha256,c.gameSha256,32);
    memcpy(storageConfig.modules,c.storageModules,sizeof storageConfig.modules);storageConfig.moduleCount=c.storageModuleCount;storageConfig.contextInit=c.contextInit;storageConfig.exists=c.exists;storageConfig.size=c.fileSize;storageConfig.read=c.read;storageConfig.ownedReadBridge=c.ownedReadBridge;
    storageConfig.storage=c.storage;storageConfig.vtable=c.storageVtable;storageConfig.counter=c.storageCounter;storageConfig.vtableModuleIndex=c.vtableModuleIndex;storageConfig.counterModuleIndex=c.counterModuleIndex;storageConfig.cachedGeneration=c.cachedGeneration;memcpy(storageConfig.contextCode,c.contextCode,sizeof storageConfig.contextCode);
    storageConfig.checkOwner=storageOwner;storageConfig.checkOwnedReadBridge=storageHook;storageConfig.owner=this;if(!storage.Open(storageConfig))return false;
    qa::pd::Config pending{};memcpy(pending.binding.attempt.data(),c.attachment,16);memcpy(pending.binding.attachment.data(),c.attachment+16,16);pending.binding.owner_generation=c.generation;pending.profile_base=c.base;
    auto span=[](uintptr_t p,size_t n)->qa::pd::Span{return{reinterpret_cast<const std::uint8_t*>(p),n};};
    pending.user=span(c.states[4],0x668);pending.toolbar=span(c.toolbar,0x8c);pending.game=span(c.states[2],0x488);pending.panel=span(c.panel,0x1f8);pending.manager=span(c.base+0x19e7310,0x50);pending.stack=span(c.stack,size_t(c.stackCapacity)*8);pending.queue=c.queue?span(c.queue,size_t(c.queueCapacity)*16):qa::pd::Span{};pending.load_cache=span(c.cache,0x3f4);
    memcpy(pending.states,c.states,sizeof pending.states);pending.expected_initial_cache_mode=c.expectedMode;pending.resolve_created_queue=qa::Adapter::ResolveCallback;pending.queue_resolver_context=&queue;
    qa::Config q{};q.pending=pending;q.controller_identity=&admission;q.cache=c.cache;q.validate_external=gd::Context::QueueGuard;q.external_context=&guards;
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
    q.fixture_native=fixtureAddresses.queueNative;q.fixture_user_caller=fixtureAddresses.userCaller;
#endif
    if(!queue.Initialize(q))return false;
    hw::Config h{};h.binding=pending.binding;h.site_rip=c.base+0x3f9daf;h.helper_deadline_ms=c.helperDeadlineMs;
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
    h.site_rip=fixtureAddresses.hardwareSite;
#endif
    if(!hw::Initialize(hardware,h))return false;
    pr::Config p{};p.base=c.base;p.persistentRootState=c.states[0];p.persistentMotorState=c.states[1];p.previousUser=c.states[4];p.attempt=c.attempt;p.epoch=c.epoch;p.session=&session;p.validate=gd::Context::PlanningGuard;p.context=&guards;
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
    p.fixtureCaller=fixtureAddresses.userCaller;
#endif
    if(!pr::Initialize(planning,p)||!b_warm_retire::Bind(session,planning))return false;
    ad::Config controller{};controller.session=&session;controller.pending=pending;controller.attempt=c.attempt;controller.original=reinterpret_cast<ad::Original>(c.base+0x3f9b00);controller.expected_prefetch_site=h.site_rip;controller.prefetch_provider=hw::MakeProvider(hardware);
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
    controller.original=fixtureAddresses.userOriginal;
#endif
    controller.authorize_queue=qa::Adapter::AuthorizeCallback;controller.authorize_queue_context=&queue;controller.queue=qa::Adapter::QueueCallback;controller.queue_context=&queue;controller.next_before=pr::Before;controller.next_after=pr::After;controller.next_context=&planning;controller.trace=trace;controller.trace_context=this;
    if(!admission.Initialize(controller))return false;
    s.request.storage=storage.Api();s.request.localPath=c.localPath;s.request.intentPath=c.requestIntent;memcpy(s.request.ownerBinding,c.ownerBinding,32);s.request.validate=gd::Context::RequestGuard;s.request.context=&guards;
    s.bytes.base=c.base;s.bytes.storage=c.storage;s.bytes.storageVtable=c.storageVtable;s.bytes.readMethod=c.read.address;s.bytes.attemptToken=c.attempt;s.bytes.validateAttachment=gd::Context::BytesGuard;s.bytes.validationContext=&guards;
    s.lifecycle.base=c.base;s.lifecycle.attemptToken=c.attempt;s.lifecycle.validateAttachment=gd::Context::LifecycleGuard;s.lifecycle.validationContext=&guards;
    s.identity.base=c.base;s.identity.attemptToken=c.attempt;s.identity.intentPath=c.identityIntent;memcpy(s.identity.ownerBinding,c.ownerBinding,32);s.identity.validateAttachment=gd::Context::IdentityGuard;s.identity.validationContext=&guards;
#ifdef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
    s.fixtureDispatchCaller[0]=fixtureAddresses.userCaller;s.fixtureDispatchCaller[1]=fixtureAddresses.menuCaller;s.fixtureDispatchCaller[2]=fixtureAddresses.gameCaller;s.fixtureDispatchCaller[3]=fixtureAddresses.updateCaller;
    s.bytes.fixtureWorkerCaller=fixtureAddresses.workerCaller;s.bytes.fixtureReadCaller=fixtureAddresses.readCaller;s.bytes.fixtureParentCaller=fixtureAddresses.parentCaller;
    s.lifecycle.fixtureUpdateCaller=fixtureAddresses.updateCaller;s.identity.fixtureWorkerCaller=fixtureAddresses.workerCaller;
#endif
    s.dispatchForwardTargets[0]=reinterpret_cast<void*>(&CheckpointAuthorizedForwardAdmissionOriginal);s.validate=sessionGuard;s.context=this;s.userAfter=userAfter;s.userObservationBefore=ad::Controller::Before;s.userObservationAfter=ad::Controller::After;s.userObservationContext=&admission;
    return session.Initialize(s);
}
void Owner::snapshot(Report&out)noexcept{
    out=Report{};out.sequence=std::uint64_t(InterlockedIncrement64(&sequence));out.attempt=config.attempt;out.epoch=config.epoch;
    auto set=[&](Value v,std::uint64_t n){out.value[unsigned(v)]=n;};
#define O(name,field) set(Value::name,std::uint64_t(get(field)))
    O(OwnerState,state);O(OwnerError,error);O(OwnerException,exception);O(OsError,osError);O(InstallCalls,installCalls);O(InstallIntentCreated,intentCreated);O(InstallIntentDurable,intentDurable);O(ModulePinned,modulePinned);O(Installed,installed);O(StopRequested,stop);O(RestoreCalls,restoreCalls);O(RestoreReturned,restoreReturned);
#undef O
    ns::Report s{};session.Snapshot(s);ad::Report a{};admission.Snapshot(a);qa::Report q{};queue.Snapshot(q);pr::Report p{};pr::Snapshot(planning,p);sg::Report z{};storage.Snapshot(z);gd::Report g{};guards.Snapshot(g);
#define S(name,field) set(Value::name,static_cast<std::uint64_t>(s.field))
    S(SessionState,state);S(SessionError,error);S(SessionException,exceptionCode);S(Armed,armed);S(MenuBound,menuBound);S(RequestInFlight,requestInFlight);S(RequestSettled,requestSettled);S(CasPublished,casPublished);set(Value::MayHavePublished,s.casPublished||s.mayHavePublished);S(HooksRestored,hooksRestored);S(ActiveDispatch,activeDispatch);S(ActiveWorker,activeWorker);S(ActiveRead,activeRead);S(UserControllerCalls,userControllerCalls);S(DispatchUnpaired,dispatchUnpaired);
#undef S
#define Q(name,field) set(Value::name,static_cast<std::uint64_t>(q.field))
    Q(QueueStage,stage);Q(QueueError,error);Q(QueueNativeCalls,native_calls);Q(QueueNativeReturned,native_returned);Q(QueueVerified,native_result_verified);Q(QueueResolverCalls,resolver_calls);Q(QueueAuthorized,authorized);Q(QueueStopped,stopped);Q(QueueMayHaveQueued,may_have_queued);
#undef Q
#define A(name,field) set(Value::name,static_cast<std::uint64_t>(a.field))
    A(ControllerError,error);A(ControllerBlocked,blocked);A(ControllerActive,active);A(ControllerStopped,stopped);A(ControllerFinished,finished);A(ControllerOriginalCalls,original_calls);A(ControllerAbnormal,original_abnormal);A(ControllerQueueCalls,queue_calls);A(ControllerQueueReturned,queue_returned);A(ControllerAuthorizeCalls,queue_authorize_calls);A(ControllerAuthorized,queue_authorized);A(ControllerCommit,commit_succeeded);A(ControllerBind,menu_bound);A(ControllerClosed,closed);
#undef A
#define R(name,field) set(Value::name,static_cast<std::uint64_t>(s.request.field))
    R(RequestState,state);R(RequestMenuCalls,menuCalls);R(RequestGameCalls,gameCalls);R(RequestReadAttempts,readAttempts);R(RequestCasAttempts,casAttempts);R(RequestCasApplied,casApplied);R(RequestIntentCreated,intentCreated);R(RequestIntentDurable,intentDurable);R(RequestPostGuard,postGuard);R(RequestOsError,osError);R(RequestException,exceptionCode);R(RequestObservedPending,observedPending);
#undef R
#define B(name,field) set(Value::name,s.bytes.field)
    B(BytesError,error);B(BytesWorkerBefore,workerBefore);B(BytesWorkerAfter,workerAfter);B(BytesWorkerFinally,workerFinally);B(BytesWorkerAbnormal,workerAbnormal);B(BytesReadBefore,readBefore);B(BytesReadAfter,readAfter);B(BytesReadFinally,readFinally);B(BytesReadAbnormal,readAbnormal);B(BytesMatched,bytesMatched);B(BytesWorkerReturned,workerReturned);B(BytesObserved,observedWorkerAndBytes);B(BytesActiveWorker,activeWorker);B(BytesActiveRead,activeRead);
#undef B
#define L(name,field) set(Value::name,s.lifecycle.field)
    L(LifecycleError,error);L(LifecycleBound,bound);L(LifecycleInFlight,inFlight);L(LifecycleJoinReturned,joinReturned);L(LifecycleRequestCleared,requestCleared);L(LifecycleSuccessFlag,successFlag);L(LifecycleExactPop,exactPop);L(LifecycleFrozen,completionFrozen);L(LifecycleReady,receiptReady);
#undef L
#define I(name,field) set(Value::name,s.identity.field)
    I(IdentityError,error);I(IdentityActive,active);I(IdentityAbnormal,abnormal);I(IdentityCommitCalls,commitCalls);I(IdentityCasAttempts,casAttempts);I(IdentityCasApplied,casApplied);I(IdentityIntentCreated,intentCreated);I(IdentityIntentDurable,intentDurable);I(IdentityNativeReturned,nativeReturned);I(IdentityObserved,identityObserved);I(IdentityReady,receiptReady);
#undef I
#define P(name,field) set(Value::name,p.field)
    P(PlanningError,error);P(PlanningException,exceptionCode);P(PlanningBefore,before);P(PlanningAfter,after);P(PlanningInFlight,inFlight);P(PlanningWaiting,waitingForReceipt);P(PlanningReceiptBound,receiptBound);P(PlanningStack,formalPlanningStack);P(PlanningIdentity,identityMatched);P(PlanningRequestCleared,requestCleared);P(PlanningUi,uiObjectsPresent);P(PlanningNativeReturned,nativeReturned);P(PlanningObserved,planningBoundaryObserved);P(PlanningUserReused,previousUserAddressReused);P(PlanningUiForceMatches,uiForceContextMatches);P(PlanningSessionError,sessionHadError);P(PlanningSessionStop,sessionStopRequested);
#undef P
    set(Value::HardwareError,unsigned(a.prefetch.error));set(Value::HardwareEntered,a.prefetch.entered);set(Value::HardwareCaptured,a.prefetch.captured);set(Value::HardwareRestored,a.prefetch.restored);set(Value::HardwareFinished,a.prefetch.finished);set(Value::HardwareRestoreUncertain,a.prefetch.restore_uncertain);
    set(Value::StorageError,unsigned(z.error));set(Value::StorageValidations,z.validationAttempts);set(Value::StorageOpened,z.opened);set(Value::StorageInvalidated,z.lastBinding.invalidated);
    set(Value::GuardError,unsigned(g.first_error));set(Value::GuardException,g.exception);for(auto n:g.calls)out.value[unsigned(Value::GuardChecks)]+=n;
    for(unsigned i=0;i<6;++i){const auto&x=s.hooks.entries[i];auto&h=out.hooks[i];h.slot=uintptr_t(x.binding.slot);h.original=uintptr_t(x.binding.original);h.hook=uintptr_t(x.binding.hook);h.observed=x.observed;h.protection=x.protection;h.lastProtection=x.lastProtection;h.error=x.error;h.known=x.known;h.dirty=x.dirty;h.published=x.published;h.restored=x.restored;}
    for(unsigned i=0;i<4;++i){const auto&v=s.dispatchStats[i];out.bridges[i]={v.started,v.native_returned,v.abnormal_exits,0,0,0};}
    for(unsigned i=4;i<6;++i){const auto&v=i==4?s.workerStats:s.readStats;out.bridges[i]={v.started,v.native_returned,v.abnormal_exits,0,0,v.cleanup_faults};}
    static_assert(sizeof s.bytes==sizeof out.bytesReceipt&&sizeof s.lifecycle==sizeof out.lifecycleReceipt&&sizeof s.identity==sizeof out.identityReceipt&&sizeof a.prefetch==sizeof out.hardwareReceipt);
    static_assert(sizeof p.beforeSample==sizeof out.planningBeforeSample);
    memcpy(out.bytesReceipt,&s.bytes,sizeof s.bytes);memcpy(out.lifecycleReceipt,&s.lifecycle,sizeof s.lifecycle);memcpy(out.identityReceipt,&s.identity,sizeof s.identity);memcpy(out.hardwareReceipt,&a.prefetch,sizeof a.prefetch);memcpy(out.requestReadSha,s.request.read.nativeSha256[1],32);
    out.planningAttempt=p.attempt;out.planningEpoch=p.epoch;out.planningUserCall=p.userCall;out.planningIdentityCall=p.identityWorkerCall;out.planningCompletedCall=p.completedLoadCall;out.planningUser=p.observedUser;memcpy(out.planningBeforeSample,&p.beforeSample,sizeof p.beforeSample);memcpy(out.planningAfterSample,&p.afterSample,sizeof p.afterSample);copyText(out.requestStage,s.request.stage);copyText(out.planningFailure,p.failedField);
}
}
}
extern "C" DWORD WINAPI DescribeCheckpointCompleteLiveOwner(void*p){
    using namespace checkpoint_complete_live_owner;
    __try{if(!p)return 1;Description d{};HMODULE m=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(&DescribeCheckpointCompleteLiveOwner),&m))return 2;d.module=uintptr_t(m);for(unsigned i=0;i<4;++i)d.dispatchBridge[i]=uintptr_t(entries(i));d.workerBridge=uintptr_t(entries(4));d.readBridge=uintptr_t(entries(5));d.authorizedForward=uintptr_t(&CheckpointAuthorizedForwardAdmissionOriginal);*static_cast<Description*>(p)=d;return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 3;}
}
extern "C" DWORD WINAPI InstallCheckpointCompleteLiveOwner(void*p){
    using namespace checkpoint_complete_live_owner;
    AcquireSRWLockExclusive(&owner.control);DWORD result=1;__try{result=p&&owner.install(static_cast<const Config*>(p))?0:1;}__finally{ReleaseSRWLockExclusive(&owner.control);}return result;
}
extern "C" DWORD WINAPI GetCheckpointCompleteLiveOwnerReport(void*p){
    using namespace checkpoint_complete_live_owner;
    if(!p)return 1;AcquireSRWLockShared(&owner.control);DWORD result=0;__try{__try{owner.snapshot(*static_cast<Report*>(p));}__except(EXCEPTION_EXECUTE_HANDLER){result=2;}}__finally{ReleaseSRWLockShared(&owner.control);}return result;
}
extern "C" DWORD WINAPI StopCheckpointCompleteLiveOwner(void*){
    using namespace checkpoint_complete_live_owner;
    // Only atomics: revoke immediately even while Install owns control. Waiting
    // for that lock must not permit a queued Stop to publish a fresh request.
    owner.requestStop();AcquireSRWLockExclusive(&owner.control);ReleaseSRWLockExclusive(&owner.control);return 0;
}
extern "C" DWORD WINAPI RestoreCheckpointCompleteLiveOwnerBeforeCommit(void*){
    using namespace checkpoint_complete_live_owner;
    owner.requestStop();AcquireSRWLockExclusive(&owner.control);DWORD result=1;__try{InterlockedIncrement(&owner.restoreCalls);if(owner.session.RestoreBeforeCommit()){InterlockedIncrement(&owner.restoreReturned);result=0;}}__finally{ReleaseSRWLockExclusive(&owner.control);}return result;
}
#ifndef CHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
#endif
