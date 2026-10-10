// Explicit successor: physical predicates retained; no reward Owner dependency.
#include "player_input_lease_owner.h"
#include "native_storage_read_core.h"
#include <cstring>
#include <new>
#ifdef PLAYER_INPUT_LEASE_FIXTURE
extern void PlayerInputLeaseBeforePublish(HWND);
#endif
namespace player_input_lease {
namespace ni=checkpoint_native_input;
namespace {
constexpr uintptr_t WndRva=0x5122F0,BodyRva=0x510BE0,WindowRva=0x19055D0+0x18;
constexpr unsigned WndSize=0x78,BodySize=0x591;
const unsigned char WndHash[32]={0xac,0x9f,0x1f,0xc2,0x7b,0x57,0xc6,0x56,0xe8,0xa0,0xcf,0x57,0x11,0xe5,0xa0,0x7f,0x19,0x71,0x68,0x62,0x6d,0x38,0x23,0xbf,0x7f,0x3f,0x12,0xb9,0xf6,0xa6,0xe1,0xd4};
const unsigned char BodyHash[32]={0x81,0xec,0xfc,0x93,0xcc,0x2e,0x74,0x94,0xd5,0x0c,0xf5,0x87,0x8b,0x76,0x6e,0x37,0x96,0x34,0x9a,0x1e,0x9d,0x85,0x16,0xfd,0xe7,0x85,0xc3,0xf8,0xcd,0xfd,0x6c,0xd2};
void*volatile contexts[8]{};volatile LONG nextContext=-1;
bool code(uintptr_t base,uintptr_t address,size_t n)noexcept {
 if(!n||address>UINTPTR_MAX-n)return false;for(auto end=address+n;address<end;){MEMORY_BASIC_INFORMATION m{};
  if(VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.AllocationBase)!=base||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef PLAYER_INPUT_LEASE_FIXTURE
  if(m.Type!=MEM_IMAGE)return false;
#endif
  auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=address)return false;address=next<end?next:end;
 }return true;
}
}
struct Owner::Impl {
 Config c{};Report r{};SRWLOCK lock=SRWLOCK_INIT;WNDPROC original=nullptr;bool attempted=false;
 unsigned char wndBytes[WndSize]{},bodyBytes[BodySize]{};unsigned bodySize=BodySize;
 policy::State requested{};std::uint64_t pendingTicket=0;
 void fail(Error e)noexcept {if(r.error==Error::None)r.error=e;r.uncertain=true;r.acknowledged=false;r.held=true;}
 bool identity(bool installed)noexcept {__try {DWORD pid=0;const auto thread=GetWindowThreadProcessId(c.window,&pid);
  return IsWindow(c.window)&&!IsWindowUnicode(c.window)&&pid==GetCurrentProcessId()&&thread==r.windowThread&&
   uintptr_t(GetClassLongPtrA(c.window,GCLP_WNDPROC))==c.base+WndRva&&
   uintptr_t(GetWindowLongPtrA(c.window,GWLP_WNDPROC))==(installed?uintptr_t(entryFor(r.callbackSlot)):c.base+WndRva)&&
   *reinterpret_cast<const uintptr_t*>(c.base+WindowRva)==uintptr_t(c.window)&&
   code(c.base,c.base+WndRva,WndSize)&&code(c.base,c.base+BodyRva,bodySize)&&
   !memcmp(reinterpret_cast<const void*>(c.base+WndRva),wndBytes,WndSize)&&!memcmp(reinterpret_cast<const void*>(c.base+BodyRva),bodyBytes,bodySize);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 static WNDPROC entryFor(unsigned index)noexcept {const WNDPROC entries[]={entry<0>,entry<1>,entry<2>,entry<3>,entry<4>,entry<5>,entry<6>,entry<7>};return index<8?entries[index]:nullptr;}
 template<unsigned index>static LRESULT CALLBACK entry(HWND window,UINT message,WPARAM wparam,LPARAM lparam){
  auto*s=static_cast<Impl*>(InterlockedCompareExchangePointer(&contexts[index],nullptr,nullptr));
  if(!s||window!=s->c.window)return DefWindowProcA(window,message,wparam,lparam);
  bool forward=true,accepted=false;WNDPROC original=nullptr;AcquireSRWLockExclusive(&s->lock);
  if(!s->identity(true))s->fail(Error::Identity);original=s->original;++s->r.active;
  if(message==s->r.controlMessage){forward=false;
   if(s->r.error==Error::None&&s->pendingTicket&&std::uint64_t(wparam)==s->pendingTicket&&std::uint64_t(lparam)==s->r.revision){
    s->r.state=s->requested;s->r.held=policy::Hold(s->requested)||s->r.lease.id!=0;s->pendingTicket=0;s->r.pending=false;accepted=true;
   }else ++s->r.ignoredControl;
  }else{
   auto state=s->r.held?policy::State{policy::Phase::Terminal,false}:policy::State{policy::Phase::Planning,false};
   const auto decision=policy::Decide({uintptr_t(window),message,uintptr_t(wparam),intptr_t(lparam)},uintptr_t(window),state);
   if(decision.discard){++s->r.suppressed;forward=false;}
   else if(decision.classification==ni::MessageClass::AuditedGameplayInput)++s->r.auditedForwarded;
   else if(decision.classification==ni::MessageClass::Lifecycle)++s->r.lifecycleForwarded;
   else if(decision.classification==ni::MessageClass::UncoveredInput)++s->r.uncoveredForwarded;
   else ++s->r.unclassifiedForwarded;
  }
  ReleaseSRWLockExclusive(&s->lock);LRESULT result=0;bool returned=false;
  __try {result=forward?CallWindowProcA(original,window,message,wparam,lparam):0;returned=true;}
  __finally {AcquireSRWLockExclusive(&s->lock);--s->r.active;++s->r.finally;
   if(!returned)s->fail(Error::Exception);
   if(accepted&&returned&&s->r.error==Error::None){s->r.acknowledged=true;s->r.acknowledgedRevision=s->r.revision;}
   if(message==WM_NCDESTROY){s->r.destroyed=true;s->r.installed=false;s->r.pending=false;s->pendingTicket=0;s->fail(Error::Destroyed);}
   ReleaseSRWLockExclusive(&s->lock);}
  return result;
 }
 bool current()noexcept {
  if(!r.initialized||r.error!=Error::None||r.destroyed||!identity(true)){if(r.initialized&&!r.destroyed)fail(Error::Identity);return false;}
  return !r.pending&&!r.active&&r.acknowledged&&r.acknowledgedRevision==r.revision;
 }
};
Owner::Owner():p_(new Impl){}
bool Owner::Initialize(const Config&c)noexcept {auto&s=*p_;AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(s.attempted)__leave;s.attempted=true;s.c=c;
  if(!c.base||c.base>UINTPTR_MAX-0x2300000||!c.window||!policy::Valid(c.binding)){s.fail(Error::Config);__leave;}
  s.r.process=GetCurrentProcessId();DWORD pid=0;s.r.windowThread=GetWindowThreadProcessId(c.window,&pid);s.r.ownerThread=GetCurrentThreadId();
  if(pid!=s.r.process||s.r.windowThread!=GetCurrentThreadId()){s.fail(Error::Thread);__leave;}
  if(!code(c.base,c.base+WndRva,WndSize)||!code(c.base,c.base+BodyRva,BodySize)){s.fail(Error::Source);__leave;}
  unsigned char hash[32]{};if(!native_storage_read::Sha256(reinterpret_cast<void*>(c.base+WndRva),WndSize,hash)||memcmp(hash,WndHash,32)){s.fail(Error::Source);__leave;}
#ifndef PLAYER_INPUT_LEASE_FIXTURE
  if(!native_storage_read::Sha256(reinterpret_cast<void*>(c.base+BodyRva),BodySize,hash)||memcmp(hash,BodyHash,32)){s.fail(Error::Source);__leave;}
#else
  s.bodySize=32;
#endif
  memcpy(s.wndBytes,reinterpret_cast<void*>(c.base+WndRva),WndSize);memcpy(s.bodyBytes,reinterpret_cast<void*>(c.base+BodyRva),s.bodySize);
  if(!s.identity(false)){s.fail(Error::Identity);__leave;}
  s.r.controlMessage=RegisterWindowMessageA("San14.Coop.PlayerInputPolicy.v1");if(!s.r.controlMessage){s.fail(Error::Config);__leave;}
  const LONG index=InterlockedIncrement(&nextContext);if(index<0||index>=8){s.fail(Error::Publish);__leave;}s.r.callbackSlot=unsigned(index);
  if(InterlockedCompareExchangePointer(&contexts[index],&s,nullptr)){s.fail(Error::Publish);__leave;}
  s.original=reinterpret_cast<WNDPROC>(c.base+WndRva);
#ifdef PLAYER_INPUT_LEASE_FIXTURE
  PlayerInputLeaseBeforePublish(c.window);
#endif
  SetLastError(0);++s.r.publicationWrites;const auto previous=SetWindowLongPtrA(c.window,GWLP_WNDPROC,LONG_PTR(Impl::entryFor(s.r.callbackSlot)));const auto error=GetLastError();
  if(!previous&&error){s.fail(Error::Publish);__leave;}
  s.r.installed=uintptr_t(GetWindowLongPtrA(c.window,GWLP_WNDPROC))==uintptr_t(Impl::entryFor(s.r.callbackSlot));
  if(previous!=LONG_PTR(s.original)){s.r.publicationConflict=true;s.r.foreignSourceMayHaveBeenReplaced=true;s.original=reinterpret_cast<WNDPROC>(previous);s.fail(Error::Publish);__leave;}
  if(!s.r.installed||!s.identity(true)){s.fail(Error::Publish);__leave;}s.r.initialized=true;ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Source);}ReleaseSRWLockExclusive(&s.lock);return ok;
}
bool Owner::Request(const policy::Binding&binding,policy::State state,std::uint64_t revision,bool&duplicate)noexcept {
 auto&s=*p_;duplicate=false;if(!policy::Same(binding,s.c.binding)||!policy::Valid(state)||!revision)return false;
 AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(!s.r.initialized||s.r.error!=Error::None||s.r.destroyed)__leave;if(!s.identity(true)){s.fail(Error::Identity);__leave;}
  if(revision==s.r.revision){duplicate=policy::Same(state,s.requested);ok=duplicate;__leave;}
  if(s.r.pending||s.r.revision==UINT64_MAX||revision!=s.r.revision+1||s.r.ticket==UINT64_MAX||(s.r.revision&&s.r.state.phase==policy::Phase::Terminal))__leave;
  if(s.r.lease.id)__leave;
  s.requested=state;s.r.revision=revision;s.r.acknowledged=false;s.r.pending=true;s.pendingTicket=++s.r.ticket;
  if(policy::Hold(state))s.r.held=true;
  if(!PostMessageA(s.c.window,s.r.controlMessage,WPARAM(s.pendingTicket),LPARAM(revision))){s.fail(Error::Post);__leave;}ok=true;
 }__finally {ReleaseSRWLockExclusive(&s.lock);}return ok;
}
bool Owner::Acquire(const policy::Binding&binding,std::uint64_t revision,std::uint64_t sequence,Lease&out)noexcept {
 auto&s=*p_;out={};AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(!policy::Same(binding,s.c.binding)||!s.current()||revision!=s.r.revision||!policy::MayExecuteRemote(s.r.state)||s.r.lease.id||!sequence||s.r.leasesIssued==UINT64_MAX||sequence!=s.r.leasesIssued+1)__leave;
  s.r.lease={sequence,sequence,revision};s.r.held=true;++s.r.leasesIssued;out=s.r.lease;ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.lock);}return ok;
}
bool Owner::Complete(const policy::Binding&binding,const Lease&lease)noexcept {
 auto&s=*p_;AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(!policy::Same(binding,s.c.binding)||!lease.id||s.r.error!=Error::None||!s.identity(true)||lease.id!=s.r.lease.id||lease.sequence!=s.r.lease.sequence||lease.revision!=s.r.lease.revision)__leave;
  s.r.lease={};s.r.held=s.r.pending||policy::Hold(s.r.state);++s.r.leasesCompleted;ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.lock);}return ok;
}
bool Owner::Unknown(const policy::Binding&binding,const Lease&lease)noexcept {
 auto&s=*p_;AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(!policy::Same(binding,s.c.binding)||!lease.id||lease.id!=s.r.lease.id||lease.sequence!=s.r.lease.sequence||lease.revision!=s.r.lease.revision)__leave;
  s.requested=s.r.state={policy::Phase::Terminal,false};s.r.pending=false;s.pendingTicket=0;s.fail(Error::Lease);ok=true;
 }__finally{ReleaseSRWLockExclusive(&s.lock);}return ok;
}
void Owner::Snapshot(Report&out)noexcept {auto&s=*p_;
 AcquireSRWLockExclusive(&s.lock);__try {const bool current=s.current();out=s.r;
  out.acknowledged=out.acknowledged&&current;out.localCommandPolicyOpen=current&&!s.r.held&&!s.r.lease.id;
  out.remoteMessagesAllowed=current&&policy::MayReceiveRemote(s.r.state);out.remoteExecutionPolicyOpen=current&&!s.r.lease.id&&policy::MayExecuteRemote(s.r.state);
 }__finally {ReleaseSRWLockExclusive(&s.lock);}
}
}
