#include "a_native_turn_control.h"
#include "a_save_repeat_parent.h"
#include "a_save_parent_adapter.h"
// Explicit successor: only add authenticated Host cache capture at parent FINALLY.
#include "a_save_runtime_publish_evidence.h"
namespace {
struct RuntimePublishHostCache {volatile LONG64 sequence=0;volatile LONG valid=0,lease=0,frame=0,state=0;};
RuntimePublishHostCache runtimePublishHost;
static void runtimePublishCapture(a_save_dispatch_host::Host&host){
 a_save_dispatch_host::Report report{};if(!host.Snapshot(report))return;
 InterlockedIncrement64(&runtimePublishHost.sequence);
 InterlockedExchange(&runtimePublishHost.valid,report.initialized?1:0);
 InterlockedExchange(&runtimePublishHost.lease,report.lease?1:0);
 InterlockedExchange(&runtimePublishHost.frame,report.frame?1:0);
 InterlockedExchange(&runtimePublishHost.state,LONG(report.state));
 InterlockedIncrement64(&runtimePublishHost.sequence);
}
}
#include "a_save_parent_adapter.h"
#include "native_storage_read_core.h"
#include <cstring>
namespace a_save_repeat_parent {
namespace {a_save_parent_adapter::Adapter*bound=nullptr;void*context=nullptr;Control before=nullptr,after=nullptr,cancel=nullptr;volatile LONG once=0,ready=0;}
bool Bind(a_save_parent_adapter::Adapter&a,void*c,Control b,Control e,Control stop)noexcept {
 a_save_parent_adapter::Report r{};a.Snapshot(r);if(!r.initialized||r.armed||r.stopped||!c||!b||!e||!stop||InterlockedCompareExchange(&once,1,0))return false;
 bound=&a;context=c;before=b;after=e;cancel=stop;InterlockedExchange(&ready,1);return true;
}
bool Invoke(a_save_parent_adapter::Adapter*a,unsigned action)noexcept {if(!InterlockedCompareExchange(&ready,0,0))return true;if(a!=bound)return false;return (action==0?before:action==1?after:cancel)(context);}
}
#ifdef A_SAVE_REPEAT_PARENT_FAULT_FIXTURE
extern "C" void ASaveRepeatFixtureBeforeHost();
extern "C" bool ASaveRepeatFixtureSkipAfter();
#endif
namespace a_save_parent_adapter {
namespace {
constexpr unsigned char originalCall[]={0xe8,0xd2,0xc3,0x3c,0x00};
#ifndef A_SAVE_PARENT_ADAPTER_FIXTURE
constexpr unsigned char schedulerPrefix[]={0x40,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0x6c,0x24,0x90,0x48,0x81,0xec,0x70,0x1,0x0,0x0,0x48,0xc7,0x45,0xc0,0xfe,0xff,0xff,0xff};
constexpr unsigned char parentHash[]={0x88,0x91,0x87,0x48,0xc8,0x83,0x4f,0x99,0xd2,0x2a,0x10,0x34,0xa2,0x8b,0xf0,0x64,0xdc,0x49,0xdf,0xa0,0xba,0x95,0x49,0x30,0xdc,0x4b,0x22,0x9e,0xb3,0xd7,0x61,0x80};
#endif
struct Scope {Adapter*self=nullptr;std::uint64_t call=0;DWORD thread=0;bool hostFrame=false,after=false;uintptr_t base=0;bool controlBoundary=false;bool repeatEntered=false,repeatClosed=false;};
thread_local Scope scope;
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool rx(uintptr_t p,size_t n,uintptr_t allocation,bool image)noexcept {
 if(!p||!n||p>UINTPTR_MAX-n)return false;for(auto end=p+n;p<end;){MEMORY_BASIC_INFORMATION m{};
 if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.AllocationBase)!=allocation||
   (m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef A_SAVE_PARENT_ADAPTER_FIXTURE
 if(image&&m.Type!=MEM_IMAGE)return false;
#else
 (void)image;
#endif
 auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;}return true;
}
}
bool CurrentBoundary(uintptr_t base)noexcept {return scope.self&&scope.controlBoundary&&scope.base==base&&scope.thread==GetCurrentThreadId();}
void Adapter::fail(Error e)noexcept {AcquireSRWLockExclusive(&lock_);if(r_.error==Error::None)r_.error=e;r_.stopped=1;ReleaseSRWLockExclusive(&lock_);InterlockedExchange(&stopped_,1);if(c_.mailbox)c_.mailbox->Stop();}
bool Adapter::sources(bool raw)noexcept {__try {const auto b=c_.planning.base;
 if(!rx(p_.site,5,b,true)||memcmp(reinterpret_cast<void*>(p_.site),raw?p_.before:p_.after,5)||!rx(b+0x509FE0,32,b,true))return false;
#ifndef A_SAVE_PARENT_ADAPTER_FIXTURE
 if(memcmp(reinterpret_cast<void*>(b+0x509FE0),schedulerPrefix,sizeof schedulerPrefix))return false;
 unsigned char bytes[0x343]{},hash[32]{};if(!rx(b+0x13D9C0,sizeof bytes,b,true))return false;
 memcpy(bytes,reinterpret_cast<void*>(b+0x13D9C0),sizeof bytes);memcpy(bytes+0x13DC09-0x13D9C0,originalCall,5);
 if(!native_storage_read::Sha256(bytes,sizeof bytes,hash)||memcmp(hash,parentHash,32)||at<uintptr_t>(b+0x1282658+0x10)!=b+0x13D9C0)return false;
#endif
 if(p_.relay){const unsigned char jump[]={0xff,0x25,0,0,0,0};if(!rx(p_.relay,14,p_.relay,false)||memcmp(reinterpret_cast<void*>(p_.relay),jump,6)||at<uintptr_t>(p_.relay+6)!=uintptr_t(&BReloadParentBridge0))return false;}
 return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool Adapter::prepare()noexcept {p_.site=c_.planning.base+0x13DC09;memcpy(p_.before,originalCall,5);if(!sources(true))return false;
 for(uintptr_t delta=0x2400000;delta<0x60000000&&!p_.relay;delta+=0x10000){auto want=(c_.planning.base+delta+0xFFFF)&~uintptr_t(0xFFFF);if(want<c_.planning.base)break;p_.relay=uintptr_t(VirtualAlloc(reinterpret_cast<void*>(want),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));}
 if(!p_.relay)return false;unsigned char jump[14]={0xff,0x25,0,0,0,0};const auto target=uintptr_t(&BReloadParentBridge0);memcpy(jump+6,&target,8);memcpy(reinterpret_cast<void*>(p_.relay),jump,14);
 const auto delta=std::int64_t(p_.relay)-std::int64_t(p_.site+5);if(delta<INT32_MIN||delta>INT32_MAX)return false;p_.after[0]=0xe8;const auto rel=std::int32_t(delta);memcpy(p_.after+1,&rel,4);
 DWORD old=0;return VirtualProtect(reinterpret_cast<void*>(p_.relay),4096,PAGE_EXECUTE_READ,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(p_.relay),4096);}
bool Adapter::Initialize(const Config&c)noexcept {if(InterlockedCompareExchange(&once_,1,0))return false;
 if(!c.planning.base||!c.planning.root||!c.planning.world||!c.planning.owner||!c.planning.gate||!c.controller||!c.mailbox||!c.host||!c.producer||!c.readyRevision){fail(Error::Config);return false;}c_=c;
 if(!prepare()){fail(Error::Source);return false;}CheckpointLoadWorkerBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(c_.planning.base+0x509FE0);bridge.before=before;bridge.after=after;bridge.finally=finally;bridge.context=this;
 if(!BReloadParentBridgeConfigure(0,&bridge)){fail(Error::Bridge);return false;}AcquireSRWLockExclusive(&lock_);r_.initialized=1;ReleaseSRWLockExclusive(&lock_);return true;}
bool Adapter::PreparedPlan(Plan&out)noexcept {AcquireSRWLockShared(&lock_);const bool ok=r_.initialized&&!r_.stopped;out=ok?p_:Plan{};ReleaseSRWLockShared(&lock_);return ok;}
bool Adapter::Arm()noexcept {if(!r_.initialized||InterlockedCompareExchange(&stopped_,0,0)||!sources(false)){fail(Error::Publish);return false;}if(InterlockedCompareExchange(&armed_,1,0))return false;AcquireSRWLockExclusive(&lock_);r_.armed=1;ReleaseSRWLockExclusive(&lock_);return true;}
bool Adapter::initializeHost()noexcept {
 if(!c_.controller->Initialize(c_.planning))return false;bool duplicate=false;
 if(!c_.controller->Request(true,c_.readyRevision,duplicate)||!c_.mailbox->Initialize())return false;
 a_save_dispatch_host::Config host{c_.planning.owner,c_.planning.gate,c_.controller,c_.mailbox,c_.producer};
 if(!c_.host->Initialize(host))return false;AcquireSRWLockExclusive(&lock_);r_.hostInitialized=1;ReleaseSRWLockExclusive(&lock_);return true;}
void Adapter::before(const CheckpointLoadWorkerFrame*f,void*v)noexcept {auto&s=*static_cast<Adapter*>(v);if(!f||f->slot||!InterlockedCompareExchange(&s.armed_,0,0))return;
 __try {
 if(scope.self||f->thread_id!=GetCurrentThreadId()||f->args[0]!=s.c_.planning.base+0x19E7310||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=s.c_.planning.base+0x13DC0E||!s.sources(false)){s.fail(Error::Order);return;}
 AcquireSRWLockExclusive(&s.lock_);const bool wrong=s.r_.hostThread&&s.r_.hostThread!=f->thread_id;if(!s.r_.hostThread)s.r_.hostThread=f->thread_id;ReleaseSRWLockExclusive(&s.lock_);if(wrong){s.fail(Error::Thread);return;}
 if(!BReloadParentClaim(f,f->call_id)){s.fail(Error::Order);return;}scope={&s,f->call_id,f->thread_id,false,false,s.c_.planning.base,false};
 AcquireSRWLockExclusive(&s.lock_);++s.r_.before;++s.r_.active;s.r_.lastCall=f->call_id;const bool initialized=s.r_.hostInitialized!=0;ReleaseSRWLockExclusive(&s.lock_);
 scope.controlBoundary=true;__try {
 if(!initialized){if(InterlockedCompareExchange(&s.stopped_,0,0))return;if(!s.initializeHost()){s.fail(Error::Initialize);return;}}
 scope.repeatEntered=true;if(!a_save_repeat_parent::Invoke(&s,0)){s.fail(Error::Host);return;}
#ifdef A_SAVE_REPEAT_PARENT_FAULT_FIXTURE
 ASaveRepeatFixtureBeforeHost();
#endif
 scope.hostFrame=!a_native_turn::Running()&&s.c_.host->BeforeFrame();if(scope.hostFrame){AcquireSRWLockExclusive(&s.lock_);++s.r_.hostBefore;ReleaseSRWLockExclusive(&s.lock_);}
 }__finally{scope.controlBoundary=false;}
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Order);}}
void Adapter::after(const CheckpointLoadWorkerFrame*f,void*v)noexcept {auto&s=*static_cast<Adapter*>(v);if(!f||scope.self!=&s||scope.call!=f->call_id)return;
 CheckpointLoadWorkerOwner owner{};if(scope.thread!=GetCurrentThreadId()||!BReloadParentCurrentOwner(&owner)||owner.call_id!=f->call_id||owner.token!=f->call_id||owner.owner_depth!=1||owner.current_depth!=1||!s.sources(false)){s.fail(Error::Order);return;}
 #ifdef A_SAVE_REPEAT_PARENT_FAULT_FIXTURE
 if(ASaveRepeatFixtureSkipAfter())return;
#endif
 scope.after=true;AcquireSRWLockExclusive(&s.lock_);++s.r_.after;ReleaseSRWLockExclusive(&s.lock_);
 bool ok=true;scope.controlBoundary=true;__try {if(scope.hostFrame)ok=s.c_.host->AfterFrame();if(scope.repeatEntered){scope.repeatClosed=true;if(!a_save_repeat_parent::Invoke(&s,1))ok=false;}}__finally{scope.controlBoundary=false;}AcquireSRWLockExclusive(&s.lock_);s.r_.hostAfter+=scope.hostFrame&&ok;ReleaseSRWLockExclusive(&s.lock_);if(!ok)s.fail(Error::Host);}
void Adapter::finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*v)noexcept {auto&s=*static_cast<Adapter*>(v);if(!f||!x||scope.self!=&s||scope.call!=f->call_id)return;
 if(scope.repeatEntered&&!scope.repeatClosed){scope.controlBoundary=true;__try {scope.repeatClosed=true;if(!a_save_repeat_parent::Invoke(&s,2))s.fail(Error::Host);}__finally{scope.controlBoundary=false;}}
 if(x->abnormal||!scope.after)s.fail(Error::Abnormal);runtimePublishCapture(*s.c_.host);AcquireSRWLockExclusive(&s.lock_);++s.r_.finally;s.r_.abnormal+=x->abnormal;--s.r_.active;ReleaseSRWLockExclusive(&s.lock_);scope={};}
void Adapter::Stop()noexcept {fail(Error::Stopped);}
void Adapter::Snapshot(Report&out)noexcept {AcquireSRWLockShared(&lock_);out=r_;ReleaseSRWLockShared(&lock_);}
}

std::uintptr_t ASaveRuntimePublishHostCacheAddress()noexcept {return reinterpret_cast<std::uintptr_t>(&runtimePublishHost);}
bool ASaveRuntimePublishEvidence(a_save_runtime_wire::Counter out[7],std::uint32_t*valid,std::uint32_t*lease,std::uint32_t*frame,std::uint32_t*state,std::uint64_t*sequence)noexcept {
 if(!out||!valid||!lease||!frame||!state||!sequence)return false;
 auto counters=[](a_save_runtime_wire::Counter*p){return ASaveRuntimeUserCounters(p)&&ASaveRuntimeGateCounters(p+2)&&ASaveRuntimeParentCounters(p+5);};
 a_save_runtime_wire::Counter before[7]{},after[7]{};if(!counters(before))return false;
 const auto begin=InterlockedCompareExchange64(&runtimePublishHost.sequence,0,0);if(begin&1)return false;
 *valid=std::uint32_t(InterlockedCompareExchange(&runtimePublishHost.valid,0,0));*lease=std::uint32_t(InterlockedCompareExchange(&runtimePublishHost.lease,0,0));*frame=std::uint32_t(InterlockedCompareExchange(&runtimePublishHost.frame,0,0));*state=std::uint32_t(InterlockedCompareExchange(&runtimePublishHost.state,0,0));
 const auto end=InterlockedCompareExchange64(&runtimePublishHost.sequence,0,0);if(end!=begin||!counters(after))return false;
 for(unsigned i=0;i<7;++i){if(before[i].started!=after[i].started||before[i].active||after[i].active)return false;out[i]=after[i];}
 *sequence=std::uint64_t(end);return true;
}
