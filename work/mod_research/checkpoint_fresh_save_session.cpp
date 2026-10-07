#include "checkpoint_fresh_save_session.h"
#include <cstring>
#include <new>

namespace checkpoint_fresh_save_session {
namespace fs=checkpoint_fresh_save;
namespace sb=checkpoint_live_storage_binding;
namespace {
LONG value(volatile LONG*p) noexcept{return InterlockedCompareExchange(p,0,0);}
constexpr std::uintptr_t slotRva[2]={0x12CC4A8+0x28,0x12DC5F8+0x28};
constexpr std::uintptr_t originalRva[2]={0x3F9B00,0x4AA650};
void* hook(unsigned i) noexcept{return i?reinterpret_cast<void*>(&CheckpointFreshSaveSessionBridge1):reinterpret_cast<void*>(&CheckpointFreshSaveSessionBridge0);}
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
 static void before(const CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);
  // Partial publication is transparent. Submit cannot succeed before Arm.
  if(value(&s.armed))s.driver.Before(*f);
 }
 static void after(const CheckpointLoadWorkerFrame*f,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);s.driver.After(*f);
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*v) noexcept {
  auto&s=*static_cast<Impl*>(v);s.driver.Finally(*f,*e);
 }
};
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c) noexcept {
 auto&s=*p_;if(InterlockedCompareExchange(&s.once,1,0))return s.fail(Error::Used);
 bool ok=false;AcquireSRWLockExclusive(&s.control);
 __try {__try {
  if(value(&s.stopped)){s.fail(Error::Stopped);__leave;}
  unsigned any=0;for(auto n:c.room_id)any|=n;
  if(!c.base||c.base>UINTPTR_MAX-0x2300000||!c.room_epoch||!any||c.storage.attachment.base!=c.base||!c.storage.checkOwner){s.fail(Error::Config);__leave;}
  s.config=c;
  if(!s.slots(true)){s.fail(Error::RawSlot);__leave;}
  auto binding=c.storage;binding.owner=&s;binding.checkOwner=Impl::storageOwner;
  if(binding.checkOwnedReadBridge)binding.checkOwnedReadBridge=Impl::storageReadBridge;
  if(!s.gate.Open(binding)){s.fail(Error::Storage);__leave;}
  fs::Config fc{};fc.base=c.base;
  std::memcpy(fc.save_directory,c.save_directory,sizeof fc.save_directory);std::memcpy(fc.intent_directory,c.intent_directory,sizeof fc.intent_directory);
  fc.claim=CheckpointFreshSaveSessionClaim;fc.owner=CheckpointFreshSaveSessionCurrentOwner;fc.storage=s.gate.Api();
#ifdef CHECKPOINT_FRESH_SAVE_SESSION_FIXTURE
  fc.binder=c.binder;fc.queue=c.queue;fc.caller=c.caller;
#endif
  if(!s.driver.Initialize(fc)){s.fail(Error::Driver);__leave;}
  // Driver verified the supported image and saved instruction profile. Keep
  // the two raw entry prefixes pinned as well, so a later entry detour cannot
  // silently become this owner's alleged native original.
  for(unsigned i=0;i<2;++i)std::memcpy(s.nativePrefix[i],reinterpret_cast<const void*>(c.base+originalRva[i]),32);
  InterlockedExchange(&s.codeReady,1);
  if(!s.slots(true)){s.fail(Error::RawSlot);__leave;}
  CheckpointLoadWorkerBridgeConfig bc{};bc.before=Impl::before;bc.after=Impl::after;bc.finally=Impl::finally;bc.context=&s;
  checkpoint_load_hook_set::Binding hooks[2]{};
  for(unsigned i=0;i<2;++i){
   bc.original=reinterpret_cast<void*>(c.base+originalRva[i]);
   if(!CheckpointFreshSaveSessionBridgeConfigure(i,&bc)){s.fail(Error::Bridge);__leave;}
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
  if(!value(&s.armed)||value(&s.error)||value(&s.stopped))__leave;
  if(q.room_epoch!=s.config.room_epoch||std::memcmp(q.room_id,s.config.room_id,32))__leave;
  if(!s.slots()||!s.gate.Valid()){s.fail(Error::Storage);s.driver.Stop();__leave;}
  if(!value(&s.stopped))ok=s.driver.Submit(q);
 }__finally{ReleaseSRWLockExclusive(&s.control);}
 return ok;
}
void Owner::Stop() noexcept {
 auto&s=*p_;InterlockedExchange(&s.stopped,1);s.driver.Stop();
 // No Gate.Stop/RestoreAll/unload: a bound save and cached frames may continue.
}
void Owner::Snapshot(Report&out) noexcept {
 auto&s=*p_;out={};out.error=Error(value(&s.error));out.initialized=value(&s.initialized);out.armed=value(&s.armed);out.stopped=value(&s.stopped);
 out.save=s.driver.Snapshot();s.gate.Snapshot(out.storage);s.hooks.Snapshot(out.hooks);
 for(unsigned i=0;i<2;++i)CheckpointFreshSaveSessionBridgeSnapshot(i,&out.bridges[i]);
}
bool Owner::CopyArtifact(std::uint64_t generation,fs::Artifact&out) noexcept{return p_->driver.CopyArtifact(generation,out);}
}
