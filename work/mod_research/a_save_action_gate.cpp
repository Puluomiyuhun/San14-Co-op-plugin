#include "a_save_action_gate.h"
#include "native_storage_read_core.h"
#include <cstring>
#include <new>
#include <vector>
extern "C" void ASaveActionUserTail();
extern "C" {uintptr_t ASaveActionUserEpilogue=0;}
static bool (*tailSelect)(uintptr_t,uintptr_t,void*)noexcept=nullptr;
static void*tailContext=nullptr;
extern "C" bool ASaveActionTailSelect(uintptr_t user,uintptr_t caller)noexcept {return tailSelect&&tailSelect(user,caller,tailContext);}
namespace a_save_action_gate {
namespace {
constexpr uintptr_t slots[]={0x12CC9B8+0x28,0x1297CF8+0x18};
constexpr uintptr_t originals[]={0x3F8140,0x1AC3C0,0x3FA820,0x3F9B00};
constexpr size_t sizes[]={0x5DB,0x63,32,0x5B4};
constexpr unsigned char hashes[4][32]={
 {0x66,0x89,0x16,0x77,0x31,0xD2,0x68,0xCA,0x83,0x8B,0x24,0x90,0x56,0x90,0x22,0xF8,0x41,0x2B,0x40,0xF7,0x58,0x69,0xF9,0x93,0x3A,0xAF,0x0E,0x8A,0xF0,0x04,0xB6,0x9F},
 {0x8D,0x94,0x1D,0x86,0xAB,0x42,0xF5,0x5B,0xBF,0x18,0x78,0xF4,0x6D,0x1E,0x05,0xAC,0xA7,0xDD,0x29,0x84,0x74,0x03,0x0C,0x8C,0xC0,0xFD,0x7D,0x53,0x4B,0x86,0x70,0xD6},
 {0xbc,0x61,0x5e,0x70,0x45,0x55,0xf3,0x7b,0x2e,0x7b,0xa1,0x1e,0xdc,0x35,0x0c,0xf8,0xe6,0x33,0x02,0x7d,0x21,0xd0,0xf9,0x0c,0x84,0xbf,0x7b,0xf1,0xc8,0x6d,0x62,0xff},
 {0x20,0xda,0xc8,0x7a,0xef,0x24,0xde,0xbe,0x8d,0x58,0xea,0xc2,0x03,0x6f,0xca,0x2b,0x79,0x14,0x9d,0xa9,0x70,0xb7,0xd1,0xa9,0x0f,0xb4,0x5c,0xfb,0x2b,0x3e,0xab,0x94}};
LONG read(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool same(const pending::Binding&a,const pending::Binding&b){return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
void*hook(unsigned i){return i==2?reinterpret_cast<void*>(&ASaveActionBridge2):i?reinterpret_cast<void*>(&ASaveActionBridge1):reinterpret_cast<void*>(&ASaveActionBridge0);}
}
struct Owner::Impl {
 Config c{};Report r{};Plan plan{};bool published=false;checkpoint_load_hook_set::Set hooks;
 SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0,stopped=0;
 bool initialized=false,armed=false,requested=false,observed=false,validated=false;
 uintptr_t game=0,states[5]{};DWORD gameThread=0;std::uint64_t gameCall=0,gameUi=0,gamePanel=0;
 unsigned char prefixes[4][32]{};
 void fail(Error e){if(r.error==Error::None)r.error=e;observed=false;if(c.saveOwner)c.saveOwner->Stop();}
 bool codeRange(uintptr_t start,size_t size,uintptr_t allocation)noexcept {
  if(!size||start>UINTPTR_MAX-size)return false;const auto end=start+size;
  for(auto cursor=start;cursor<end;){MEMORY_BASIC_INFORMATION page{};
   if(VirtualQuery(reinterpret_cast<void*>(cursor),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
      uintptr_t(page.AllocationBase)!=allocation||
      (page.Protect!=PAGE_EXECUTE_READ&&page.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef A_SAVE_ACTION_FIXTURE
   if(allocation==c.base&&page.Type!=MEM_IMAGE)return false;
#endif
   const auto limit=uintptr_t(page.BaseAddress)+page.RegionSize;if(limit<=cursor)return false;cursor=limit<end?limit:end;
  }return true;
 }
 bool sources(bool raw=false)noexcept {__try {
  for(unsigned i=0;i<4;++i){
   MEMORY_BASIC_INFORMATION page{};auto target=c.base+originals[i];
   if(!codeRange(target,sizes[i],c.base)||VirtualQuery(reinterpret_cast<void*>(target),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
      (page.Protect!=PAGE_EXECUTE_READ&&page.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef A_SAVE_ACTION_FIXTURE
   if(page.Type!=MEM_IMAGE||uintptr_t(page.AllocationBase)!=c.base)return false;
   unsigned char code[0x600]{},hash[32]{};memcpy(code,reinterpret_cast<void*>(target),sizes[i]);
   if(!raw&&(i==0||i==3)){auto&p=plan.patches[i==0?0:1];memcpy(code+p.address-target,p.before,p.size);}
   if(!native_storage_read::Sha256(code,sizes[i],hash)||memcmp(hash,hashes[i],32))return false;
#else
   if(initialized&&memcmp(reinterpret_cast<void*>(target),prefixes[i],32))return false;
#endif
  }
  for(unsigned i=0;i<2;++i){auto&p=plan.patches[i];MEMORY_BASIC_INFORMATION page{};
   if(!codeRange(p.address,p.size,c.base)||VirtualQuery(reinterpret_cast<void*>(p.address),&page,sizeof page)!=sizeof page||page.Protect!=PAGE_EXECUTE_READ||
      memcmp(reinterpret_cast<void*>(p.address),raw?p.before:p.after,p.size))return false;
   auto slot=c.base+slots[i];if(VirtualQuery(reinterpret_cast<void*>(slot),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
      slot+8>uintptr_t(page.BaseAddress)+page.RegionSize||(page.Protect!=PAGE_READONLY&&page.Protect!=PAGE_WRITECOPY))return false;
#ifndef A_SAVE_ACTION_FIXTURE
   if(page.Type!=MEM_IMAGE||uintptr_t(page.AllocationBase)!=c.base)return false;
#endif
   auto value=at<uintptr_t>(slot);if(armed){if(value!=uintptr_t(hook(i)))return false;}else if(value!=c.base+originals[i])return false;
  }
  if(plan.relay){MEMORY_BASIC_INFORMATION page{};if(!codeRange(plan.relay,46,plan.relay)||VirtualQuery(reinterpret_cast<void*>(plan.relay),&page,sizeof page)!=sizeof page||page.Protect!=PAGE_EXECUTE_READ)return false;
   const uintptr_t targets[]={uintptr_t(&ASaveActionBridge2),uintptr_t(&ASaveActionUserTail)};
   for(unsigned i=0;i<2;++i){const auto p=plan.relay+i*32;const unsigned char op[]={0xff,0x25,0,0,0,0};if(memcmp(reinterpret_cast<void*>(p),op,6)||at<uintptr_t>(p+6)!=targets[i])return false;}
  }
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool source()noexcept{return sources(false);}
 bool prepare()noexcept {__try {
  plan.patches[0].address=c.base+0x3F8606;plan.patches[0].size=5;
  const unsigned char panel[]={0xe8,0x15,0x22,0,0},user[]={0x48,0x8b,0x86,0x78,0x04,0,0};
  memcpy(plan.patches[0].before,panel,5);plan.patches[1].address=c.base+0x3F9DAF;plan.patches[1].size=7;memcpy(plan.patches[1].before,user,7);
  if(!sources(true))return false;
  // Retained leaf relays only tail-jump; no copied prolog or invented unwind.
  for(uintptr_t d=0x2400000;d<0x60000000&&!plan.relay;d+=0x10000){
   const auto wanted=(c.base+d+0xFFFF)&~uintptr_t(0xFFFF);
   if(wanted<c.base)break;plan.relay=uintptr_t(VirtualAlloc(reinterpret_cast<void*>(wanted),4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
  }
  if(!plan.relay)return false;
  const uintptr_t targets[]={uintptr_t(&ASaveActionBridge2),uintptr_t(&ASaveActionUserTail)};
  for(unsigned i=0;i<2;++i){unsigned char op[14]={0xff,0x25,0,0,0,0};memcpy(op+6,&targets[i],8);memcpy(reinterpret_cast<void*>(plan.relay+i*32),op,14);
   auto&p=plan.patches[i];const auto delta=std::int64_t(plan.relay+i*32)-std::int64_t(p.address+5);
   if(delta<INT32_MIN||delta>INT32_MAX)return false;const auto rel=std::int32_t(delta);p.after[0]=0xe8;memcpy(p.after+1,&rel,4);if(i)p.after[5]=p.after[6]=0x90;
  }
  DWORD old=0;return VirtualProtect(reinterpret_cast<void*>(plan.relay),4096,PAGE_EXECUTE_READ,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(plan.relay),4096);
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
   if(!s.armed||!s.requested||read(s.stopped)||s.r.error!=Error::None){if(f->slot==2)++s.r.panelForwarded;else ++s.r.uiForwarded;__leave;}
   uintptr_t caller=s.c.base+(f->slot==2?0x3F860B:0x3F85F6);
#ifdef A_SAVE_ACTION_FIXTURE
   if(f->slot==1)caller=s.c.fixtureUiCaller;
#endif
   CheckpointLoadWorkerOwner owner{};
   if(!s.source()||!s.gameCall||s.gameThread!=GetCurrentThreadId()||!ASaveActionCurrentOwner(&owner)||
      owner.slot!=0||owner.token!=s.c.binding.owner_generation||owner.call_id!=s.gameCall||
      owner.current_depth!=owner.owner_depth+1||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=caller||
      (f->slot==1?(f->args[0]!=s.c.base+0x1FC8410||at<uintptr_t>(f->args[0])!=s.c.base+0x1297CF8):(f->args[0]!=s.game))){s.fail(Error::Scope);++s.r.uiForwarded;__leave;}
   if(f->slot==2){++s.r.panelSuppressed;++s.gamePanel;}else{++s.r.uiSuppressed;++s.gameUi;}f->reserved_58=2;f->result_rax=0;memset(f->result_xmm0,0,16);forward=false;
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception);++s.r.uiForwarded;}}
  __finally{ReleaseSRWLockExclusive(&s.lock);}return forward;
 }
 static void before(const CheckpointLoadWorkerFrame*f,void*v)noexcept {
  if(f->slot)return;auto&s=*static_cast<Impl*>(v);AcquireSRWLockExclusive(&s.lock);
  __try {__try {
   if(!s.armed||!s.requested||read(s.stopped)||s.r.error!=Error::None)__leave;
   uintptr_t caller=s.c.base+0x50B785;
#ifdef A_SAVE_ACTION_FIXTURE
   caller=s.c.fixtureGameCaller;
#endif
   if(s.r.active!=1||s.gameCall||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=caller||
      f->thread_id!=GetCurrentThreadId()||!s.source()||!s.layout(*f)||!ASaveActionClaim(f,s.c.binding.owner_generation)){s.fail(Error::Input);__leave;}
   s.gameCall=f->call_id;s.gameThread=f->thread_id;s.gameUi=0;s.gamePanel=0;s.observed=false;
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception);}}
  __finally{ReleaseSRWLockExclusive(&s.lock);}
 }
 static bool userTail(uintptr_t user,uintptr_t caller,void*v)noexcept {
  auto&s=*static_cast<Impl*>(v);bool held=false;AcquireSRWLockExclusive(&s.lock);
  __try {__try {
   if(!s.armed||!s.requested||read(s.stopped)||s.r.error!=Error::None){++s.r.userTailForwarded;__leave;}
   CheckpointLoadWorkerOwner owner{};a_save_user_owner::Report save{};s.c.saveOwner->Snapshot(save);
   if(!s.source()||!s.validated||caller!=s.c.base+0x3F9DB4||user!=s.states[4]||
      at<uintptr_t>(s.c.root+0x85130)!=s.c.world||at<unsigned>(user+0x470)!=2||
      at<uintptr_t>(s.c.base+0x19E7310+0x20)==0||at<std::uint64_t>(s.c.base+0x19E7310+0x10)!=5||
      save.stopped||save.error!=a_save_user_owner::Error::None||!save.save_lane||save.active_scopes!=1||
      !ASaveUserOwnerCurrentOwner(&owner)||owner.slot||owner.thread_id!=GetCurrentThreadId()||
      owner.current_depth!=1||owner.owner_depth!=1||owner.token!=save.save.generation){s.fail(Error::Scope);++s.r.userTailForwarded;__leave;}
   const auto stack=at<uintptr_t>(s.c.base+0x19E7310+0x20);
   for(unsigned i=0;i<5;++i)if(at<uintptr_t>(stack+i*8)!=s.states[i]){s.fail(Error::Input);__leave;}
   if(s.r.error!=Error::None){++s.r.userTailForwarded;__leave;}
   ++s.r.userTailSuppressed;held=true;
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception);++s.r.userTailForwarded;}}
  __finally{ReleaseSRWLockExclusive(&s.lock);}return held;
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*v)noexcept {
  auto&s=*static_cast<Impl*>(v);AcquireSRWLockExclusive(&s.lock);
  __try {
   if(s.r.active)--s.r.active;else s.fail(Error::Scope);
   if(e->abnormal)s.fail(Error::Exception);
   if(f->slot==0&&s.gameCall==f->call_id&&s.gameThread==GetCurrentThreadId()){
    s.observed=s.gameUi>0&&s.gamePanel>0&&!s.r.active&&!e->abnormal&&s.r.error==Error::None;
    s.gameCall=0;s.gameThread=0;s.gameUi=0;s.gamePanel=0;
   }
  }__finally{ReleaseSRWLockExclusive(&s.lock);}
 }
};
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c)noexcept {
 auto&s=*p_;if(InterlockedCompareExchange(&s.once,1,0))return false;
 unsigned attempt=0,attachment=0;for(auto n:c.binding.attempt)attempt|=n;for(auto n:c.binding.attachment)attachment|=n;
 if(!c.base||c.base>UINTPTR_MAX-0x2300000||!c.root||!c.world||!c.saveOwner||!c.sample||!attempt||!attachment||!c.binding.owner_generation){s.fail(Error::Config);return false;}
 PROCESS_MITIGATION_USER_SHADOW_STACK_POLICY cet{};
 if(!GetProcessMitigationPolicy(GetCurrentProcess(),ProcessUserShadowStackPolicy,&cet,sizeof cet)||cet.EnableUserShadowStack){s.fail(Error::Config);return false;}
 s.c=c;if(!s.prepare()){s.fail(Error::Source);return false;}
 for(unsigned i=0;i<4;++i)memcpy(s.prefixes[i],reinterpret_cast<void*>(c.base+originals[i]),32);
 ASaveActionBridgeConfig bridge{};bridge.size=sizeof bridge;bridge.select=Impl::select;bridge.before=Impl::before;bridge.finally=Impl::finally;bridge.context=&s;
 checkpoint_load_hook_set::Binding bindings[2]{};
 for(unsigned i=0;i<3;++i){bridge.original=reinterpret_cast<void*>(c.base+originals[i]);if(!ASaveActionBridgeConfigure(i,&bridge)){s.fail(Error::Bridge);return false;}
  if(i<2)bindings[i]={reinterpret_cast<void*volatile*>(c.base+slots[i]),bridge.original,hook(i)};}
 if(!s.hooks.Initialize(bindings,2)){s.fail(Error::Hooks);return false;}if(tailSelect){s.fail(Error::Used);return false;}tailSelect=Impl::userTail;tailContext=&s;ASaveActionUserEpilogue=c.base+0x3FA09F;s.initialized=true;return true;
}
bool Owner::PreparedPlan(Plan&out)noexcept{auto&s=*p_;if(!s.initialized||s.armed||read(s.stopped)||s.r.error!=Error::None)return false;out=s.plan;return true;}
bool Owner::Arm()noexcept {auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.lock);
 __try {if(!s.initialized||s.armed||s.r.error!=Error::None||read(s.stopped))__leave;if(!s.source()){s.fail(Error::Source);__leave;}
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
  out.coveredGlobalUiHeld=out.requested&&s.observed&&!out.active&&out.error==Error::None;out.coveredPanelHeld=out.coveredGlobalUiHeld;out.ownedUserTailTransform=s.armed;
  s.hooks.Snapshot(out.hooks);for(unsigned i=0;i<3;++i)ASaveActionBridgeSnapshot(i,&out.bridges[i]);
 }__finally{ReleaseSRWLockExclusive(&s.lock);}}
}
