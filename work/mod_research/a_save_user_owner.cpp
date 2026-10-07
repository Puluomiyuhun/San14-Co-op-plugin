#include "a_save_user_owner.h"
#include <cstring>
#include <new>

namespace a_save_user_owner {
namespace fs=checkpoint_fresh_save;
namespace sb=checkpoint_live_storage_binding;
namespace {
LONG value(volatile LONG*p) noexcept{return InterlockedCompareExchange(p,0,0);}
constexpr std::uintptr_t slotRva[2]={0x12CC4A8+0x28,0x12DC5F8+0x28};
constexpr std::uintptr_t originalRva[2]={0x3F9B00,0x4AA650};
void* hook(unsigned i) noexcept{return i?reinterpret_cast<void*>(&ASaveUserOwnerBridge1):reinterpret_cast<void*>(&ASaveUserOwnerBridge0);}
bool same(const sb::Attachment&a,const sb::Attachment&b) noexcept{
 return a.pid==b.pid&&a.birth==b.birth&&a.base==b.base&&a.attempt==b.attempt&&a.generation==b.generation&&
  !std::memcmp(a.id,b.id,32)&&!std::memcmp(a.gameSha256,b.gameSha256,32);
}
}
struct Owner::Impl {
 Config config{};fs::Driver driver;checkpoint_serialized_storage_gate::Gate gate;
 checkpoint_load_hook_set::Set hooks;SRWLOCK control=SRWLOCK_INIT;
 unsigned char nativePrefix[2][32]{};
 volatile LONG once=0,initialized=0,armed=0,stopped=0,error=0,codeReady=0;
 std::uint64_t holdRevision=0,heldScopes=0,activeScopes=0;
 bool hold=false,holdObserved=false,saveLane=false;
 bool fail(Error e) noexcept{InterlockedCompareExchange(&error,LONG(e),0);return false;}
 bool slots(bool rawOnly=false) noexcept {
  __try {
   for(unsigned i=0;i<2;++i){
    const auto original=config.base+originalRva[i];
    if(value(&codeReady)){
     MEMORY_BASIC_INFORMATION page{};
     if(VirtualQuery(reinterpret_cast<void*>(original),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||
        (page.Protect!=PAGE_EXECUTE_READ&&page.Protect!=PAGE_EXECUTE_WRITECOPY)||
        std::memcmp(reinterpret_cast<const void*>(original),nativePrefix[i],32))return false;
    }
    auto p=*reinterpret_cast<void*volatile*>(config.base+slotRva[i]);
    if(rawOnly){if(p!=reinterpret_cast<void*>(config.base+originalRva[i]))return false;}
    else if(value(&armed)){if(p!=hook(i))return false;}
    else if(p!=hook(i)&&p!=reinterpret_cast<void*>(config.base+originalRva[i]))return false;
   }
   return true;
  }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
 }
 static bool storageOwner(void*v,const sb::Attachment&a,sb::Point p) noexcept {
  auto&s=*static_cast<Impl*>(v);
  return same(a,s.config.storage.attachment)&&s.slots()&&s.config.storage.checkOwner&&
   s.config.storage.checkOwner(s.config.storage.owner,a,p);
 }
 static bool storageReadBridge(void*v,std::uintptr_t slot,std::uintptr_t original,std::uintptr_t bridge) noexcept {
  auto&s=*static_cast<Impl*>(v);
  return s.config.storage.checkOwnedReadBridge&&s.config.storage.checkOwnedReadBridge(s.config.storage.owner,slot,original,bridge);
 }
 bool idleUser(const CheckpointLoadWorkerFrame&f) noexcept {
  namespace pd=checkpoint_native_input_pending;
  auto caller=config.base+0x50B785;
#ifdef A_SAVE_USER_OWNER_FIXTURE
  caller=config.caller;
#endif
  if(f.thread_id!=GetCurrentThreadId()||!f.call_id||!f.caller_entry_rsp||*reinterpret_cast<const std::uintptr_t*>(f.caller_entry_rsp)!=caller)return false;
  pd::Config c{};
  if(!config.sample_input(config.input_context,c)||c.profile_base!=config.base||c.states[4]!=f.args[0]||
     reinterpret_cast<std::uintptr_t>(c.manager.data)!=config.base+0x19E7310||
     reinterpret_cast<std::uintptr_t>(c.load_cache.data)!=*reinterpret_cast<const std::uintptr_t*>(config.base+0x2025318)||
     c.binding.attempt!=config.input_binding.attempt||c.binding.attachment!=config.input_binding.attachment||
     c.binding.owner_generation!=config.input_binding.owner_generation)return false;
  pd::Adapter inspector;if(inspector.Bind(c)!=pd::Error::None)return false;
  const auto result=inspector.InspectCurrent(config.input_binding);
  return result.error==pd::Error::None&&result.decision==pd::Decision::QuiescentObserved&&result.stack_count==5&&result.user_phase==2;
 }
 static bool select(CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);bool forward=true;
  AcquireSRWLockExclusive(&s.control);
  __try {__try {
   ++s.activeScopes;f->reserved_58=3; // tracked transparent/raw ordinary scope
   if(!value(&s.armed))__leave;
   if(s.activeScopes!=1){s.fail(Error::Overlap);s.driver.Stop();__leave;}
   if(s.saveLane){f->reserved_58=1;__leave;}
   // Stop revokes new work, including User suppression. Keep the earlier
   // saveLane branch: a save already bound must still finish its evidence.
   if(value(&s.stopped)||value(&s.error))__leave;
   if(f->slot==0&&s.hold){
    s.holdObserved=false;
    if(!s.slots()||!s.idleUser(*f)){s.fail(Error::Input);s.driver.Stop();__leave;}
    f->reserved_58=2;f->result_rax=0;std::memset(f->result_xmm0,0,sizeof f->result_xmm0);forward=false;
   }
  }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Input);s.driver.Stop();}}
  __finally{ReleaseSRWLockExclusive(&s.control);}
  return forward;
 }
 static void before(const CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);
  // Partial publication is transparent. Submit cannot succeed before Arm.
  if(f->reserved_58==1)s.driver.Before(*f);
 }
 static void after(const CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);if(f->reserved_58==1)s.driver.After(*f);
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);
  if(f->reserved_58==1)s.driver.Finally(*f,*e);
  const auto report=s.driver.Snapshot();
  AcquireSRWLockExclusive(&s.control);
  __try {
   if(s.activeScopes)--s.activeScopes;else s.fail(Error::Overlap);
   if(f->reserved_58==2&&!e->abnormal){++s.heldScopes;s.holdObserved=!s.activeScopes&&!value(&s.error);}
   if(report.status==fs::Status::Complete)s.saveLane=false;
  }__finally{ReleaseSRWLockExclusive(&s.control);}
 }
};
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c) noexcept {
 auto&s=*p_;if(InterlockedCompareExchange(&s.once,1,0))return s.fail(Error::Used);
 bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {__try {
  if(value(&s.stopped)){s.fail(Error::Stopped);__leave;}
  unsigned any=0;for(auto n:c.room_id)any|=n;
  if(!c.base||c.base>UINTPTR_MAX-0x2300000||!c.room_epoch||!any||c.storage.attachment.base!=c.base||!c.storage.checkOwner||!c.sample_input||!c.input_binding.owner_generation){s.fail(Error::Config);__leave;}
  s.config=c;
  if(!s.slots(true)){s.fail(Error::RawSlot);__leave;}
  auto binding=c.storage;binding.owner=&s;binding.checkOwner=Impl::storageOwner;
  if(binding.checkOwnedReadBridge)binding.checkOwnedReadBridge=Impl::storageReadBridge;
  if(!s.gate.Open(binding)){s.fail(Error::Storage);__leave;}
  fs::Config fc{};fc.base=c.base;
  std::memcpy(fc.save_directory,c.save_directory,sizeof fc.save_directory);std::memcpy(fc.intent_directory,c.intent_directory,sizeof fc.intent_directory);
  fc.claim=ASaveUserOwnerClaim;fc.owner=ASaveUserOwnerCurrentOwner;fc.storage=s.gate.Api();
#ifdef A_SAVE_USER_OWNER_FIXTURE
  fc.binder=c.binder;fc.queue=c.queue;fc.caller=c.caller;
#endif
  if(!s.driver.Initialize(fc)){s.fail(Error::Driver);__leave;}
  // Driver verified the supported image and saved instruction profile. Keep
  // the two raw entry prefixes pinned as well, so a later entry detour cannot
  // silently become this owner's alleged native original.
  for(unsigned i=0;i<2;++i)std::memcpy(s.nativePrefix[i],reinterpret_cast<const void*>(c.base+originalRva[i]),32);
  InterlockedExchange(&s.codeReady,1);
  if(!s.slots(true)){s.fail(Error::RawSlot);__leave;}
  ASaveUserOwnerBridgeConfig bc{};bc.size=sizeof bc;bc.select=Impl::select;bc.before=Impl::before;bc.after=Impl::after;bc.finally=Impl::finally;bc.context=&s;
  checkpoint_load_hook_set::Binding hooks[2]{};
  for(unsigned i=0;i<2;++i){
   bc.original=reinterpret_cast<void*>(c.base+originalRva[i]);
   if(!ASaveUserOwnerBridgeConfigure(i,&bc)){s.fail(Error::Bridge);__leave;}
   hooks[i]={reinterpret_cast<void*volatile*>(c.base+slotRva[i]),bc.original,hook(i)};
  }
  if(!s.hooks.Initialize(hooks,2)){s.fail(Error::Hooks);__leave;}
  if(value(&s.stopped)){s.fail(Error::Stopped);__leave;}
  InterlockedExchange(&s.initialized,1);ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Config);}}
 __finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
bool Owner::Arm() noexcept {
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {
  if(!value(&s.initialized)||value(&s.armed)||value(&s.error)||value(&s.stopped))__leave;
  if(!s.slots(true)||!s.gate.Valid()){s.fail(Error::RawSlot);__leave;}
  // Save first, admission User last. Slot CAS/protection restoration are real;
  // this does not purport to stop all engine or input threads.
  if(value(&s.stopped))__leave;
  if(!s.hooks.Publish(1)){s.fail(Error::Arm);__leave;}
  if(value(&s.stopped))__leave;
  if(!s.hooks.Publish(0)){s.fail(Error::Arm);__leave;}
  if(value(&s.stopped))__leave;
  InterlockedExchange(&s.armed,1);ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
bool Owner::Submit(const fs::Request&q) noexcept {
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {
  if(!value(&s.armed)||value(&s.error)||value(&s.stopped)||s.hold||s.saveLane||s.activeScopes)__leave;
  if(q.room_epoch!=s.config.room_epoch||std::memcmp(q.room_id,s.config.room_id,32))__leave;
  if(!s.slots()||!s.gate.Valid()){s.fail(Error::Storage);s.driver.Stop();__leave;}
  if(!value(&s.stopped)){ok=s.driver.Submit(q);if(ok)s.saveLane=true;}
 }__finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
bool Owner::SetUserHold(bool hold,std::uint64_t revision) noexcept {
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {
  if(!value(&s.armed)||value(&s.error)||value(&s.stopped)||s.saveLane||s.activeScopes||!revision||revision<=s.holdRevision)__leave;
  if(!s.slots()){s.fail(Error::RawSlot);s.driver.Stop();__leave;}
  s.hold=hold;s.holdObserved=false;s.holdRevision=revision;ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.control);}return ok;
}
void Owner::Stop() noexcept {
 auto&s=*p_;InterlockedExchange(&s.stopped,1);s.driver.Stop();
 // No Gate.Stop/RestoreAll/unload: a bound save and cached frames may continue.
}
void Owner::Snapshot(Report&out) noexcept {
 auto&s=*p_;out={};out.error=Error(value(&s.error));out.initialized=value(&s.initialized);out.armed=value(&s.armed);out.stopped=value(&s.stopped);
 out.save=s.driver.Snapshot();s.gate.Snapshot(out.storage);s.hooks.Snapshot(out.hooks);
 for(unsigned i=0;i<2;++i)ASaveUserOwnerBridgeSnapshot(i,&out.bridges[i]);
 AcquireSRWLockExclusive(&s.control);
 __try {out.hold_revision=s.holdRevision;out.held_scopes=s.heldScopes;out.active_scopes=s.activeScopes;out.user_hold_requested=s.hold&&!value(&s.stopped);out.user_subset_held=s.hold&&s.holdObserved&&!s.activeScopes&&!value(&s.error)&&!value(&s.stopped);out.save_lane=s.saveLane;}
 __finally{ReleaseSRWLockExclusive(&s.control);}
}
bool Owner::CopyArtifact(std::uint64_t generation,fs::Artifact&out) noexcept{
 auto&s=*p_;bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {if(!value(&s.error))ok=s.driver.CopyArtifact(generation,out);}
 __finally{ReleaseSRWLockExclusive(&s.control);}return ok;
}
}
