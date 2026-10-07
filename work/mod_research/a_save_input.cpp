#include "a_save_input.h"
#include "native_storage_read_core.h"
#include <cstring>
#include <new>
namespace a_save_input {
namespace {
constexpr uintptr_t slots[]={0x12CC9B8+0x28,0x1297CF8+0x18};
constexpr uintptr_t originals[]={0x3F8140,0x1AC3C0};
constexpr size_t sizes[]={0x5DB,0x63};
constexpr unsigned char hashes[2][32]={
 {0x66,0x89,0x16,0x77,0x31,0xD2,0x68,0xCA,0x83,0x8B,0x24,0x90,0x56,0x90,0x22,0xF8,0x41,0x2B,0x40,0xF7,0x58,0x69,0xF9,0x93,0x3A,0xAF,0x0E,0x8A,0xF0,0x04,0xB6,0x9F},
 {0x8D,0x94,0x1D,0x86,0xAB,0x42,0xF5,0x5B,0xBF,0x18,0x78,0xF4,0x6D,0x1E,0x05,0xAC,0xA7,0xDD,0x29,0x84,0x74,0x03,0x0C,0x8C,0xC0,0xFD,0x7D,0x53,0x4B,0x86,0x70,0xD6}};
LONG read(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool same(const pending::Binding&a,const pending::Binding&b){return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
void*hook(unsigned i){return i?reinterpret_cast<void*>(&ASaveInputBridge1):reinterpret_cast<void*>(&ASaveInputBridge0);}
}
struct Owner::Impl {
 Config c{};Report r{};checkpoint_load_hook_set::Set hooks;
 SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0,stopped=0;
 bool initialized=false,armed=false,requested=false,observed=false,validated=false;
 uintptr_t game=0,states[5]{};DWORD gameThread=0;std::uint64_t gameCall=0,gameUi=0;
 unsigned char prefixes[2][32]{};
 void fail(Error e){if(r.error==Error::None)r.error=e;observed=false;}
 bool source(bool raw=false)noexcept{__try {
  for(unsigned i=0;i<2;++i){
   MEMORY_BASIC_INFORMATION page{};auto target=c.base+originals[i];
   if(VirtualQuery(reinterpret_cast<void*>(target),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
      (page.Protect!=PAGE_EXECUTE_READ&&page.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef A_SAVE_INPUT_FIXTURE
   if(page.Type!=MEM_IMAGE||uintptr_t(page.AllocationBase)!=c.base)return false;
   unsigned char hash[32]{};if(!native_storage_read::Sha256(reinterpret_cast<void*>(target),sizes[i],hash)||memcmp(hash,hashes[i],32))return false;
#else
   if(initialized&&memcmp(reinterpret_cast<void*>(target),prefixes[i],32))return false;
#endif
   auto slot=c.base+slots[i];if(VirtualQuery(reinterpret_cast<void*>(slot),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
      (page.Protect!=PAGE_READONLY&&page.Protect!=PAGE_WRITECOPY))return false;
#ifndef A_SAVE_INPUT_FIXTURE
   if(page.Type!=MEM_IMAGE||uintptr_t(page.AllocationBase)!=c.base)return false;
#endif
   auto p=at<uintptr_t>(slot);if(raw){if(p!=target)return false;}else if(armed){if(p!=uintptr_t(hook(i)))return false;}else if(p!=target&&p!=uintptr_t(hook(i)))return false;
  }return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool layout(const CheckpointLoadWorkerFrame&f)noexcept {__try {
  if(at<uintptr_t>(c.base+0x1FCA1E0)!=c.root||at<uintptr_t>(c.root+0x85130)!=c.world||
     at<uintptr_t>(c.root)!=c.base+0x12AA6B0||at<uintptr_t>(c.world)!=c.base+0x12AA638)return false;
  pending::Config p{};if(!c.sample(c.context,p)||!same(p.binding,c.binding)||p.profile_base!=c.base||p.states[2]!=f.args[0]||
    uintptr_t(p.manager.data)!=c.base+0x19E7310||uintptr_t(p.load_cache.data)!=at<uintptr_t>(c.base+0x2025318))return false;
  auto manager=c.base+0x19E7310,stack=at<uintptr_t>(manager+0x20);const auto n=at<std::uint64_t>(manager+0x10);
  if(!validated){pending::Adapter inspect;if(inspect.Bind(p)!=pending::Error::None)return false;const auto result=inspect.InspectCurrent(c.binding);
   if(result.error!=pending::Error::None||result.decision!=pending::Decision::QuiescentObserved)return false;
   memcpy(states,p.states,sizeof states);game=p.states[2];validated=true;
  }
  if(memcmp(states,p.states,sizeof states)||!stack||uintptr_t(p.stack.data)!=stack||p.stack.size<48||game!=f.args[0])return false;
  for(unsigned i=0;i<5;++i)if(at<uintptr_t>(stack+i*8)!=states[i])return false;
  if(n==5){pending::Adapter inspect;if(inspect.Bind(p)!=pending::Error::None)return false;auto result=inspect.InspectCurrent(c.binding);return result.error==pending::Error::None&&result.decision==pending::Decision::QuiescentObserved;}
  // Retain only this consumer gate during the specific Save state; this does
  // not certify it is OUR save or authorize any export. Unknown modals fail.
  if(n!=6)return false;auto save=at<uintptr_t>(stack+40);
  return save&&at<uintptr_t>(save)==c.base+0x12DC5F8&&!memcmp(reinterpret_cast<void*>(save+0x70),"CSaveState",11)&&at<unsigned>(save+0x470)<=4;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 static bool select(CheckpointLoadWorkerFrame*f,void*v)noexcept {
  auto&s=*static_cast<Impl*>(v);bool forward=true;AcquireSRWLockExclusive(&s.lock);
  __try {__try {
   ++s.r.active;f->reserved_58=0;
   if(f->slot==0){++s.r.gameCalls;__leave;}
   if(!s.armed||!s.requested||read(s.stopped)||s.r.error!=Error::None){++s.r.uiForwarded;__leave;}
   uintptr_t caller=s.c.base+0x3F85F6;
#ifdef A_SAVE_INPUT_FIXTURE
   caller=s.c.fixtureUiCaller;
#endif
   CheckpointLoadWorkerOwner owner{};
   if(!s.source()||!s.gameCall||s.gameThread!=GetCurrentThreadId()||!ASaveInputCurrentOwner(&owner)||
      owner.slot!=0||owner.token!=s.c.binding.owner_generation||owner.call_id!=s.gameCall||
      owner.current_depth!=owner.owner_depth+1||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=caller||
      f->args[0]!=s.c.base+0x1FC8410||at<uintptr_t>(f->args[0])!=s.c.base+0x1297CF8){s.fail(Error::Scope);++s.r.uiForwarded;__leave;}
   ++s.r.uiSuppressed;++s.gameUi;f->reserved_58=2;f->result_rax=0;memset(f->result_xmm0,0,16);forward=false;
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception);++s.r.uiForwarded;}}
  __finally{ReleaseSRWLockExclusive(&s.lock);}return forward;
 }
 static void before(const CheckpointLoadWorkerFrame*f,void*v)noexcept {
  if(f->slot)return;auto&s=*static_cast<Impl*>(v);AcquireSRWLockExclusive(&s.lock);
  __try {__try {
   if(!s.armed||!s.requested||read(s.stopped)||s.r.error!=Error::None)__leave;
   uintptr_t caller=s.c.base+0x50B785;
#ifdef A_SAVE_INPUT_FIXTURE
   caller=s.c.fixtureGameCaller;
#endif
   if(s.r.active!=1||s.gameCall||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=caller||
      f->thread_id!=GetCurrentThreadId()||!s.source()||!s.layout(*f)||!ASaveInputClaim(f,s.c.binding.owner_generation)){s.fail(Error::Input);__leave;}
   s.gameCall=f->call_id;s.gameThread=f->thread_id;s.gameUi=0;s.observed=false;
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception);}}
  __finally{ReleaseSRWLockExclusive(&s.lock);}
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*v)noexcept {
  auto&s=*static_cast<Impl*>(v);AcquireSRWLockExclusive(&s.lock);
  __try {
   if(s.r.active)--s.r.active;else s.fail(Error::Scope);
   if(e->abnormal)s.fail(Error::Exception);
   if(f->slot==0&&s.gameCall==f->call_id&&s.gameThread==GetCurrentThreadId()){
    s.observed=s.gameUi>0&&!s.r.active&&!e->abnormal&&s.r.error==Error::None;
    s.gameCall=0;s.gameThread=0;s.gameUi=0;
   }
  }__finally{ReleaseSRWLockExclusive(&s.lock);}
 }
};
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c)noexcept {
 auto&s=*p_;if(InterlockedCompareExchange(&s.once,1,0))return false;
 unsigned attempt=0,attachment=0;for(auto n:c.binding.attempt)attempt|=n;for(auto n:c.binding.attachment)attachment|=n;
 if(!c.base||c.base>UINTPTR_MAX-0x2300000||!c.root||!c.world||!c.sample||!attempt||!attachment||!c.binding.owner_generation){s.fail(Error::Config);return false;}
 s.c=c;if(!s.source(true)){s.fail(Error::Source);return false;}
 for(unsigned i=0;i<2;++i)memcpy(s.prefixes[i],reinterpret_cast<void*>(c.base+originals[i]),32);
 ASaveInputBridgeConfig bridge{};bridge.size=sizeof bridge;bridge.select=Impl::select;bridge.before=Impl::before;bridge.finally=Impl::finally;bridge.context=&s;
 checkpoint_load_hook_set::Binding bindings[2]{};
 for(unsigned i=0;i<2;++i){bridge.original=reinterpret_cast<void*>(c.base+originals[i]);if(!ASaveInputBridgeConfigure(i,&bridge)){s.fail(Error::Bridge);return false;}
  bindings[i]={reinterpret_cast<void*volatile*>(c.base+slots[i]),bridge.original,hook(i)};}
 if(!s.hooks.Initialize(bindings,2)){s.fail(Error::Hooks);return false;}s.initialized=true;return true;
}
bool Owner::Arm()noexcept {auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.lock);
 __try {if(!s.initialized||s.armed||s.r.error!=Error::None||read(s.stopped))__leave;if(!s.source(true)){s.fail(Error::Source);__leave;}
  if(read(s.stopped))__leave;if(!s.hooks.Publish(1)){s.fail(Error::Hooks);__leave;}
  if(read(s.stopped))__leave;if(!s.hooks.Publish(0)){s.fail(Error::Hooks);__leave;}
  if(read(s.stopped))__leave;s.armed=true;ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.lock);}return ok;}
bool Owner::Hold(const pending::Binding&b,bool hold,std::uint64_t revision)noexcept {auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.lock);
 __try {if(!s.armed||read(s.stopped)||s.r.error!=Error::None||s.r.active||!same(b,s.c.binding)||!revision||revision<=s.r.revision)__leave;
  if(!s.source()){s.fail(Error::Source);__leave;}s.requested=hold;s.r.revision=revision;s.observed=false;ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.lock);}return ok;}
void Owner::Stop()noexcept{InterlockedExchange(&p_->stopped,1);}
void Owner::Snapshot(Report&out)noexcept{auto&s=*p_;AcquireSRWLockExclusive(&s.lock);
 __try {out=s.r;out.initialized=s.initialized;out.armed=s.armed;out.stopped=read(s.stopped);out.requested=s.requested&&!out.stopped;
  out.coveredGlobalUiHeld=out.requested&&s.observed&&!out.active&&out.error==Error::None;
  s.hooks.Snapshot(out.hooks);for(unsigned i=0;i<2;++i)ASaveInputBridgeSnapshot(i,&out.bridges[i]);
 }__finally{ReleaseSRWLockExclusive(&s.lock);}}
}
