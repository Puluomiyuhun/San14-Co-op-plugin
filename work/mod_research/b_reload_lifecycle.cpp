#include "b_reload_lifecycle.h"
#include "b_reload_lifecycle_bridge.h"
#include "b_reload_lifecycle_profile.h"
#include <cstring>
namespace b_reload_lifecycle {
namespace {
struct State {Config c{};Report r{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0,armed=0,stopped=0,entered=0;};State state;
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
void fail(Error e){AcquireSRWLockExclusive(&state.lock);if(state.r.error==Error::None)state.r.error=e;ReleaseSRWLockExclusive(&state.lock);}
bool page(uintptr_t p,size_t n,uintptr_t allocation) noexcept {MEMORY_BASIC_INFORMATION m{};if(p>UINTPTR_MAX-n||VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.AllocationBase)!=allocation||p+n>uintptr_t(m.BaseAddress)+m.RegionSize||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef B_RELOAD_LIFECYCLE_FIXTURE
 if(allocation==state.c.base&&m.Type!=MEM_IMAGE)return false;
#endif
 return true;
}
bool sources(bool raw) noexcept {__try {const auto&x=state.r.plan;const auto b=state.c.base;
 if(!page(b+0x509580,sizeof b_reload_lifecycle_profile::InitBytes,b)||memcmp(reinterpret_cast<void*>(b+0x509580),b_reload_lifecycle_profile::InitBytes,sizeof b_reload_lifecycle_profile::InitBytes)||!page(x.address,5,b)||memcmp(reinterpret_cast<void*>(x.address),raw?x.before:x.after,5))return false;
 if(x.relay){const unsigned char op[]={0xff,0x25,0,0,0,0};if(!page(x.relay,14,x.relay)||memcmp(reinterpret_cast<void*>(x.relay),op,6)||at<uintptr_t>(x.relay+6)!=uintptr_t(&BReloadLifecycleBridge0))return false;}return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool emptyPool() noexcept {__try {for(unsigned i=0;i<4;++i)if(at<uintptr_t>(state.c.base+0x1A24DA0+0x10+uintptr_t(i)*0x80))return false;return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
void before(const CheckpointLoadWorkerFrame*f,void*){if(!f||!get(state.armed)||get(state.stopped)||!sources(false)||InterlockedCompareExchange(&state.entered,1,0)){fail(Error::Order);return;}
 __try {const auto pool=state.c.base+0x1A24DA0;if(f->thread_id!=GetCurrentThreadId()||f->args[0]!=pool||at<uintptr_t>(f->caller_entry_rsp)!=state.c.base+0x1447BB||!emptyPool()||!BReloadLifecycleClaim(f,pool)){fail(Error::Source);return;}
 AcquireSRWLockExclusive(&state.lock);++state.r.entered;ReleaseSRWLockExclusive(&state.lock);
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception);}}
void after(const CheckpointLoadWorkerFrame*f,void*){CheckpointLoadWorkerOwner owner{};if(!f||!BReloadLifecycleCurrentOwner(&owner)||owner.call_id!=f->call_id||owner.token!=state.c.base+0x1A24DA0||!sources(false)){fail(Error::Source);return;}
 if(!RegisterColdPool(f)){fail(Error::Activation);return;}AcquireSRWLockExclusive(&state.lock);++state.r.returned;ReleaseSRWLockExclusive(&state.lock);
}
void finally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*x,void*){AcquireSRWLockExclusive(&state.lock);++state.r.finally;if(x&&x->abnormal){++state.r.abnormal;if(state.r.error==Error::None)state.r.error=Error::Exception;}ReleaseSRWLockExclusive(&state.lock);}
}
bool Initialize(const Config&c) noexcept {if(InterlockedCompareExchange(&state.once,1,0)||!c.base||c.base>UINTPTR_MAX-0x2300000||!c.provider)return false;state.c=c;auto&x=state.r.plan;x.address=c.base+0x1447B6;memcpy(x.before,b_reload_lifecycle_profile::InitCall,5);
 if(!sources(true)){fail(Error::Source);return false;}if(!emptyPool()){fail(Error::AlreadyRunning);return false;}
 for(uintptr_t delta=0x2400000;delta<0x60000000&&!x.relay;delta+=0x10000){const auto wanted=(c.base+delta+0xffff)&~uintptr_t(0xffff);if(wanted<c.base)break;x.relay=uintptr_t(VirtualAlloc(reinterpret_cast<void*>(wanted),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));}
 if(!x.relay){fail(Error::Relay);return false;}unsigned char jump[14]={0xff,0x25,0,0,0,0};const auto target=uintptr_t(&BReloadLifecycleBridge0);memcpy(jump+6,&target,8);memcpy(reinterpret_cast<void*>(x.relay),jump,14);const auto displacement=std::int64_t(x.relay)-std::int64_t(x.address+5);if(displacement<INT32_MIN||displacement>INT32_MAX){fail(Error::Relay);return false;}x.after[0]=0xe8;const auto relative=std::int32_t(displacement);memcpy(x.after+1,&relative,4);DWORD old=0;if(!VirtualProtect(reinterpret_cast<void*>(x.relay),4096,PAGE_EXECUTE_READ,&old)||!FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(x.relay),14)){fail(Error::Relay);return false;}
 CheckpointLoadWorkerBridgeConfig hook{};hook.original=reinterpret_cast<void*>(c.base+0x509580);hook.before=before;hook.after=after;hook.finally=finally;if(!BReloadLifecycleBridgeConfigure(0,&hook)||!b_reload_root_activation::Initialize(c)){fail(Error::Bridge);return false;}state.r.initialized=1;return true;
}
bool PreparedPlan(Plan&p) noexcept {if(!state.r.initialized||get(state.armed)||get(state.stopped)||state.r.error!=Error::None)return false;p=state.r.plan;return true;}
bool Arm() noexcept {if(!state.r.initialized||get(state.armed)||get(state.stopped)||state.r.error!=Error::None||!sources(false)||!emptyPool()){fail(Error::Source);return false;}if(!b_reload_root_activation::PublishIat()){fail(Error::Activation);return false;}InterlockedExchange(&state.armed,1);state.r.armed=1;return true;}
void Stop() noexcept {InterlockedExchange(&state.stopped,1);b_reload_root_activation::Stop();}
void Snapshot(Report&r) noexcept {AcquireSRWLockShared(&state.lock);r=state.r;ReleaseSRWLockShared(&state.lock);WorkerStatistics(r.coldPools,r.unownedTasks);}
}
