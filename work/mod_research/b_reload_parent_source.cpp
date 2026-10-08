#include "b_reload_parent_source.h"
#include "b_reload_parent_profile.h"
#include <cstring>
#include <new>
namespace b_reload_parent_source {
namespace {
constexpr uintptr_t points[]={0x50B4B3,0x50B598,0x50B4AE,0x50B632};
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
struct Debug {DWORD64 v[6]{};};
Debug read(const CONTEXT&c){return{{c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7}};}
void write(CONTEXT&c,const Debug&v){c.Dr0=v.v[0];c.Dr1=v.v[1];c.Dr2=v.v[2];c.Dr3=v.v[3];c.Dr6=v.v[4];c.Dr7=v.v[5];}
bool same(const Debug&a,const Debug&b){return a.v[0]==b.v[0]&&a.v[1]==b.v[1]&&a.v[2]==b.v[2]&&a.v[3]==b.v[3]&&(a.v[5]&~0x400ull)==(b.v[5]&~0x400ull);}
struct Job {HANDLE target=nullptr;uintptr_t base=0;bool restore=false,attempted=false,completed=false;Debug original{},observed{};Error error=Error::None;DWORD os=0;};
Debug armed(const Job&j){Debug d=j.original;for(unsigned i=0;i<4;++i)d.v[i]=j.base+points[i];d.v[5]|=0x55;return d;}
DWORD WINAPI helper(void*p){auto&j=*static_cast<Job*>(p);auto prior=SuspendThread(j.target);if(prior==DWORD(-1)){j.error=Error::Helper;j.os=GetLastError();j.completed=true;return 0;}
 if(prior)j.error=Error::Occupied;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;
 if(j.error==Error::None&&!GetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}
 if(j.error==Error::None){j.observed=read(c);if(!j.restore){j.original=j.observed;if(c.Dr0||c.Dr1||c.Dr2||c.Dr3||(c.Dr7&0xFFFF00FFull)||(c.Dr6&0xE00Full))j.error=Error::Occupied;else write(c,armed(j));}
  else if(!same(j.observed,armed(j))||((j.observed.v[4]^j.original.v[4])&0xE00Full))j.error=Error::Restore;else write(c,j.original);
  if(j.error==Error::None){j.attempted=true;if(!SetThreadContext(j.target,&c)){j.error=Error::Context;j.os=GetLastError();}else {CONTEXT v{};v.ContextFlags=CONTEXT_DEBUG_REGISTERS;
   if(!GetThreadContext(j.target,&v)){j.error=Error::Context;j.os=GetLastError();}else {j.observed=read(v);const auto expected=read(c);if(memcmp(expected.v,j.observed.v,sizeof expected.v))j.error=Error::Context;}}}}
 if(ResumeThread(j.target)==DWORD(-1)){j.error=Error::Restore;j.os=GetLastError();}j.completed=true;return 0;
}
}
struct Owner::Impl {
 Config c{};Report r{};Plan plan{};SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0,stopped=0,busy=0;
 struct Scope {Impl* owner=nullptr;std::uint64_t call=0;DWORD thread=0;HANDLE target=nullptr;bool phase=false,needsRestore=false,uncertain=false;Job arm{},restore{};};
 Scope scopes[128]{};static thread_local Scope* current;static PVOID veh;
 bool initialized=false,installed=false;
 void fail(Error e,DWORD os=0){AcquireSRWLockExclusive(&lock);if(r.error==Error::None)r.error=e;if(os)r.osError=os;ReleaseSRWLockExclusive(&lock);}
 bool range(uintptr_t p,size_t n,uintptr_t allocation)noexcept {
  if(!n||p>UINTPTR_MAX-n)return false;const auto end=p+n;while(p<end){MEMORY_BASIC_INFORMATION m{};
   if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.AllocationBase)!=allocation||
    (m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef B_RELOAD_PARENT_FIXTURE
   if(allocation==c.base&&m.Type!=MEM_IMAGE)return false;
#endif
   const auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;
  }return true;
 }
 bool sources(bool raw)noexcept {__try {
  const auto b=c.base;
  for(unsigned i=0;i<2;++i){const auto&p=plan.patches[i];if(!range(p.address,5,b)||memcmp(reinterpret_cast<void*>(p.address),raw?p.before:p.after,5))return false;}
  // Only our exact second call-site is normalized. Any other scheduler drift
  // fails; private native bytes are generated from a pinned archive, not Git.
  unsigned char scheduler[sizeof b_reload_parent_profile::SchedulerBytes]{};
  if(!range(b+0x509FE0,sizeof scheduler,b))return false;memcpy(scheduler,reinterpret_cast<void*>(b+0x509FE0),sizeof scheduler);
  if(!raw)memcpy(scheduler+0x50B41B-0x509FE0,plan.patches[1].before,5);
  if(memcmp(scheduler,b_reload_parent_profile::SchedulerBytes,sizeof scheduler))return false;
  if(plan.relay){if(!range(plan.relay,46,plan.relay))return false;const uintptr_t targets[]={uintptr_t(&BReloadParentBridge0),uintptr_t(&BReloadParentBridge1)};
   const unsigned char op[]={0xff,0x25,0,0,0,0};for(unsigned i=0;i<2;++i)if(memcmp(reinterpret_cast<void*>(plan.relay+i*32),op,6)||at<uintptr_t>(plan.relay+i*32+6)!=targets[i])return false;}
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool prepare()noexcept {__try {
  const uintptr_t sites[]={0x13DC09,0x50B41B};const unsigned char*raw[]={b_reload_parent_profile::OuterCall,b_reload_parent_profile::PhaseCall};
  for(unsigned i=0;i<2;++i){plan.patches[i].address=c.base+sites[i];memcpy(plan.patches[i].before,raw[i],5);}
  if(!sources(true))return false;
  for(uintptr_t delta=0x2400000;delta<0x60000000&&!plan.relay;delta+=0x10000){auto wanted=(c.base+delta+0xFFFF)&~uintptr_t(0xFFFF);if(wanted<c.base)break;plan.relay=uintptr_t(VirtualAlloc(reinterpret_cast<void*>(wanted),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));}
  if(!plan.relay)return false;const uintptr_t targets[]={uintptr_t(&BReloadParentBridge0),uintptr_t(&BReloadParentBridge1)};
  for(unsigned i=0;i<2;++i){unsigned char op[14]={0xff,0x25,0,0,0,0};memcpy(op+6,&targets[i],8);memcpy(reinterpret_cast<void*>(plan.relay+i*32),op,14);
   auto&p=plan.patches[i];auto delta=std::int64_t(plan.relay+i*32)-std::int64_t(p.address+5);if(delta<INT32_MIN||delta>INT32_MAX)return false;
   const auto rel=std::int32_t(delta);p.after[0]=0xe8;memcpy(p.after+1,&rel,4);
  }DWORD old=0;return VirtualProtect(reinterpret_cast<void*>(plan.relay),4096,PAGE_EXECUTE_READ,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(plan.relay),4096);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool run(Scope&q,Job&j){auto h=CreateThread(nullptr,0,helper,&j,0,nullptr);if(!h){fail(Error::Helper,GetLastError());return false;}
  const auto waited=WaitForSingleObject(h,c.helperDeadlineMs);if(waited!=WAIT_OBJECT_0){q.uncertain=true;fail(Error::Deadline);if(WaitForSingleObject(h,INFINITE)!=WAIT_OBJECT_0)return false;}
  CloseHandle(h);if(j.error!=Error::None)fail(j.error,j.os);return waited==WAIT_OBJECT_0&&j.completed&&j.error==Error::None;
 }
 bool eligible(){AcquireSRWLockShared(&lock);const bool ok=installed&&r.error==Error::None&&!get(stopped);ReleaseSRWLockShared(&lock);return ok;}
 static void before(const CheckpointLoadWorkerFrame*f,void*v){auto&s=*static_cast<Impl*>(v);if(!f||f->slot||!s.eligible())return;
  __try {
   if(current||IsDebuggerPresent()||!s.sources(false)||f->thread_id!=GetCurrentThreadId()||f->args[0]!=s.c.base+0x19E7310||
    !f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=s.c.base+0x13DC0E){s.fail(Error::Order);return;}
   if(InterlockedCompareExchange(&s.busy,1,0)){s.fail(Error::Occupied);return;}
   AcquireSRWLockExclusive(&s.lock);if(s.r.scopes>=128){s.r.error=Error::Capacity;ReleaseSRWLockExclusive(&s.lock);InterlockedExchange(&s.busy,0);return;}
   auto&q=s.scopes[s.r.scopes++];q.owner=&s;q.call=f->call_id;q.thread=GetCurrentThreadId();++s.r.active;memset(s.r.originalDr,0,sizeof s.r.originalDr);memset(s.r.restoredDr,0,sizeof s.r.restoredDr);ReleaseSRWLockExclusive(&s.lock);current=&q;
   if(!BReloadParentClaim(f,1))s.fail(Error::Order);
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception,GetExceptionCode());}
 }
 static void after(const CheckpointLoadWorkerFrame*f,void*v){auto&s=*static_cast<Impl*>(v);auto*q=current;if(!f||f->slot!=1||!q||q->owner!=&s||!s.eligible())return;
  __try {
   CheckpointLoadWorkerOwner owner{};if(q->phase||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=s.c.base+0x50B420||!BReloadParentCurrentOwner(&owner)||
    owner.slot||owner.call_id!=q->call||owner.thread_id!=GetCurrentThreadId()||owner.owner_depth!=1||owner.current_depth!=2||!s.sources(false)){s.fail(Error::Order);return;}
   q->phase=true;AcquireSRWLockExclusive(&s.lock);++s.r.phaseStarted;ReleaseSRWLockExclusive(&s.lock);
   if(!DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&q->target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)){s.fail(Error::Helper,GetLastError());return;}
   q->arm.target=q->target;q->arm.base=s.c.base;const bool ok=s.run(*q,q->arm);q->needsRestore=q->arm.attempted;
   AcquireSRWLockExclusive(&s.lock);memcpy(s.r.originalDr,q->arm.original.v,sizeof s.r.originalDr);if(!ok)s.r.uncertain|=unsigned(q->uncertain);ReleaseSRWLockExclusive(&s.lock);
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception,GetExceptionCode());}
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*x,void*v){auto&s=*static_cast<Impl*>(v);auto*q=current;if(!f||!x||f->slot||!q||q->owner!=&s||q->call!=f->call_id)return;
  bool restored=!q->needsRestore;if(q->needsRestore){q->restore.target=q->target;q->restore.base=s.c.base;q->restore.restore=true;q->restore.original=q->arm.original;restored=s.run(*q,q->restore);}
  if(x->abnormal)s.fail(Error::Exception);
  AcquireSRWLockExclusive(&s.lock);++s.r.finally;s.r.abnormal+=x->abnormal;s.r.restored+=restored;s.r.uncertain|=unsigned(q->uncertain||!restored);--s.r.active;
  memcpy(s.r.restoredDr,q->needsRestore?q->restore.observed.v:q->arm.observed.v,sizeof s.r.restoredDr);ReleaseSRWLockExclusive(&s.lock);
  if(restored&&!q->uncertain){current=nullptr;if(q->target){CloseHandle(q->target);q->target=nullptr;}InterlockedExchange(&s.busy,0);} // retain uncertain tombstone
 }
 void capture(Scope&q,CONTEXT&ctx,unsigned i){if(!eligible()){if(get(stopped))fail(Error::Stopped);return;}
  Sample sample{};sample.rip=ctx.Rip;sample.rsp=ctx.Rsp;sample.rdi=ctx.Rdi;sample.thread=GetCurrentThreadId();sample.point=i;
  const auto slot=at<uintptr_t>(ctx.Rsp+0x40),state=at<uintptr_t>(slot);sample.state=state;
  const auto m=c.base+0x19E7310,a=at<uintptr_t>(m+0x20),n=at<std::uint64_t>(m+0x10);
  if(!a||n<3||n>6||slot<a||slot-a>=n*8||(slot-a)%8||at<uintptr_t>(m+0x48)!=state){fail(Error::Order);return;}
  const auto vt=at<uintptr_t>(state);const bool known=vt==c.base+0x12CC4A8||vt==c.base+0x12DB4C0||vt==c.base+0x12CC9B8||vt==c.base+0x12DBD68;
  if(!known){sample.skipped=2;AcquireSRWLockExclusive(&lock);++r.unknownSkipped;ReleaseSRWLockExclusive(&lock);}
  else if(i==3&&at<uintptr_t>(state+0x50)){
   if(ctx.Rdi!=at<uintptr_t>(state+0x50)||!at<DWORD>(ctx.Rdi+0x78)){fail(Error::Order);return;}
   sample.skipped=1;AcquireSRWLockExclusive(&lock);++r.yieldedSkipped;ReleaseSRWLockExclusive(&lock);
  }else {if(i==3&&!ctx.Rdi){fail(Error::Order);return;}
   checkpoint_native_task_provider::Capture actual{ctx.Rip,ctx.Rcx,ctx.Rdx,ctx.Rbx,ctx.Rdi,ctx.Rsp,sample.thread};sample.accepted=c.provider->Observe(actual);if(!sample.accepted)fail(Error::Provider);
  }
  AcquireSRWLockExclusive(&lock);++r.hits[i];r.accepted[i]+=sample.accepted;r.last[i]=sample;ReleaseSRWLockExclusive(&lock);(void)q;
 }
 static LONG body(EXCEPTION_POINTERS*ep,Scope*&claimed){auto*q=current;if(!q||!q->phase||!q->needsRestore||!ep||!ep->ExceptionRecord||!ep->ContextRecord||ep->ExceptionRecord->ExceptionCode!=EXCEPTION_SINGLE_STEP)return EXCEPTION_CONTINUE_SEARCH;
  auto&s=*q->owner;auto&c=*ep->ContextRecord;unsigned slot=4;for(unsigned i=0;i<4;++i)if(c.Rip==s.c.base+points[i])slot=i;
  if(slot==4||uintptr_t(ep->ExceptionRecord->ExceptionAddress)!=c.Rip||GetCurrentThreadId()!=q->thread||!same(read(c),armed(q->arm))||(c.Dr6&0xE00Full)!=(DWORD64(1)<<slot))return EXCEPTION_CONTINUE_SEARCH;
  claimed=q;c.EFlags|=0x10000;c.Dr6&=~(DWORD64(1)<<slot);s.capture(*q,c,slot);return EXCEPTION_CONTINUE_EXECUTION;
 }
 static LONG CALLBACK handler(EXCEPTION_POINTERS*ep){Scope*claimed=nullptr;__try{return body(ep,claimed);}__except(EXCEPTION_EXECUTE_HANDLER){if(!claimed)return EXCEPTION_CONTINUE_SEARCH;claimed->owner->fail(Error::Exception,GetExceptionCode());return EXCEPTION_CONTINUE_EXECUTION;}}
};
thread_local Owner::Impl::Scope* Owner::Impl::current=nullptr;PVOID Owner::Impl::veh=nullptr;
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c)noexcept {auto&s=*p_;if(InterlockedCompareExchange(&s.once,1,0)||!c.base||c.base>UINTPTR_MAX-0x2300000||!c.provider||!c.helperDeadlineMs||c.helperDeadlineMs>10000)return false;
 s.c=c;if(!s.prepare()){s.fail(Error::Source);return false;}CheckpointLoadWorkerBridgeConfig b{};b.before=Impl::before;b.after=Impl::after;b.finally=Impl::finally;b.context=&s;
 for(unsigned i=0;i<2;++i){b.original=reinterpret_cast<void*>(c.base+(i?0xF570:0x509FE0));if(!BReloadParentBridgeConfigure(i,&b)){s.fail(Error::Bridge);return false;}}
 HMODULE module=nullptr;if(Impl::veh||!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&Impl::handler),&module)){s.fail(Error::Bridge);return false;}
 Impl::veh=AddVectoredExceptionHandler(1,Impl::handler);if(!Impl::veh){s.fail(Error::Bridge);return false;}
 s.initialized=true;s.r.initialized=1;return true;
}
bool Owner::PreparedPlan(Plan&p)noexcept {auto&s=*p_;if(!s.initialized||s.installed||get(s.stopped)||s.r.error!=Error::None)return false;p=s.plan;return true;}
bool Owner::Arm()noexcept {auto&s=*p_;AcquireSRWLockExclusive(&s.lock);bool ok=s.initialized&&!s.installed&&!get(s.stopped)&&s.r.error==Error::None;
 if(ok&&!s.sources(false)){s.r.error=Error::Source;ok=false;}if(ok){s.installed=true;s.r.armed=1;}ReleaseSRWLockExclusive(&s.lock);return ok;
}
void Owner::Stop()noexcept {InterlockedExchange(&p_->stopped,1);}
void Owner::Snapshot(Report&out)noexcept {auto&s=*p_;AcquireSRWLockShared(&s.lock);out=s.r;out.stopped=get(s.stopped);ReleaseSRWLockShared(&s.lock);}
bool Owner::CurrentQueueOwner(QueueOwner&out)noexcept {out={};auto*q=Impl::current;if(!q||q->phase||!q->owner->eligible())return false;CheckpointLoadWorkerOwner own{};
 if(!BReloadParentCurrentOwner(&own)||own.slot||own.token!=1||own.call_id!=q->call||own.thread_id!=GetCurrentThreadId()||own.owner_depth!=1||own.current_depth!=1)return false;
 out={q->owner->c.base,q->owner->c.base+0x19E7310,q->thread,q->call};return true;
}
}
