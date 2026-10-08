#include "planning_input_boundary.h"
#include "checkpoint_native_input_core.h"
#include "native_storage_read_core.h"
#include <cstring>
#include <new>
#ifdef PLANNING_INPUT_BOUNDARY_FIXTURE
extern void PlanningInputBoundaryBeforePublish(HWND,bool);
#endif
namespace planning_input_boundary {
namespace ni=checkpoint_native_input;namespace pi=planning_input_interlock;
namespace {
constexpr uintptr_t WndRva=0x5122F0,BodyRva=0x510BE0,WindowRva=0x19055D0+0x18;
constexpr unsigned WndSize=0x78,BodySize=0x591;
const unsigned char WndHash[32]={0xac,0x9f,0x1f,0xc2,0x7b,0x57,0xc6,0x56,0xe8,0xa0,0xcf,0x57,0x11,0xe5,0xa0,0x7f,0x19,0x71,0x68,0x62,0x6d,0x38,0x23,0xbf,0x7f,0x3f,0x12,0xb9,0xf6,0xa6,0xe1,0xd4};
const unsigned char BodyHash[32]={0x81,0xec,0xfc,0x93,0xcc,0x2e,0x74,0x94,0xd5,0x0c,0xf5,0x87,0x8b,0x76,0x6e,0x37,0x96,0x34,0x9a,0x1e,0x9d,0x85,0x16,0xfd,0xe7,0x85,0xc3,0xf8,0xcd,0xfd,0x6c,0xd2};
void*volatile contexts[8]{};volatile LONG nextContext=-1;
bool code(uintptr_t base,uintptr_t address,size_t n)noexcept {
 if(!n||address>UINTPTR_MAX-n)return false;for(auto end=address+n;address<end;){MEMORY_BASIC_INFORMATION m{};
  if(VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||uintptr_t(m.AllocationBase)!=base||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef PLANNING_INPUT_BOUNDARY_FIXTURE
  if(m.Type!=MEM_IMAGE)return false;
#endif
  auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=address)return false;address=next<end?next:end;
 }return true;
}
}
struct Boundary::Impl {
 Config c{};Report r{};SRWLOCK lock=SRWLOCK_INIT;WNDPROC original=nullptr;bool attempted=false;
 unsigned char wndBytes[WndSize]{},bodyBytes[BodySize]{};unsigned bodySize=BodySize;
 std::uint64_t pendingTicket=0,pendingRevision=0,observedAt=0;bool pendingValue=false,pendingRetire=false;
 void fail(Error e)noexcept {if(r.error==Error::None)r.error=e;r.uncertain=true;r.acknowledged=false;}
 bool identity(bool installed)noexcept {__try {DWORD pid=0;const auto thread=GetWindowThreadProcessId(c.window,&pid);
  return IsWindow(c.window)&&!IsWindowUnicode(c.window)&&pid==GetCurrentProcessId()&&thread==r.windowThread&&
   uintptr_t(GetClassLongPtrA(c.window,GCLP_WNDPROC))==c.base+WndRva&&
   uintptr_t(GetWindowLongPtrA(c.window,GWLP_WNDPROC))==(installed?uintptr_t(entryFor(r.callbackSlot)):c.base+WndRva)&&
   *reinterpret_cast<const uintptr_t*>(c.base+WindowRva)==uintptr_t(c.window)&&
   code(c.base,c.base+WndRva,WndSize)&&code(c.base,c.base+BodyRva,bodySize)&&
   !memcmp(reinterpret_cast<const void*>(c.base+WndRva),wndBytes,WndSize)&&!memcmp(reinterpret_cast<const void*>(c.base+BodyRva),bodyBytes,bodySize);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool controller(pi::Report&x)noexcept {c.controller->Snapshot(x);
  return x.initialized&&x.error==pi::Error::None&&!x.uncertain&&!x.observing&&x.thread==r.ownerThread&&
   !x.reward.queued&&!x.reward.active&&!x.reward.uncertain&&x.reward.error==pi::ar::Error::None&&
   !x.owner.active_scopes&&!x.owner.save_lane&&!x.owner.stopped&&x.owner.error==a_save_user_owner::Error::None&&
   uintptr_t(x.gate.hooks.entries[0].binding.slot)==c.base+0x12CC9E0&&uintptr_t(x.gate.hooks.entries[0].binding.original)==c.base+0x3F8140&&
   x.gate.armed&&!x.gate.stopped&&x.gate.error==pi::ag::Error::None;
 }
 static WNDPROC entryFor(unsigned index)noexcept {const WNDPROC entries[]={entry<0>,entry<1>,entry<2>,entry<3>,entry<4>,entry<5>,entry<6>,entry<7>};return index<8?entries[index]:nullptr;}
 template<unsigned index>static LRESULT CALLBACK entry(HWND window,UINT message,WPARAM wparam,LPARAM lparam){
  auto*s=static_cast<Impl*>(InterlockedCompareExchangePointer(&contexts[index],nullptr,nullptr));
  if(!s||window!=s->c.window)return DefWindowProcA(window,message,wparam,lparam);
  bool forward=true;WNDPROC original=nullptr;AcquireSRWLockExclusive(&s->lock);
  if(!s->r.retired&&!s->identity(true)){s->fail(Error::Identity);}original=s->original;++s->r.active;
  if(!s->r.retired&&message==s->r.controlMessage){
   ++s->r.controlCalls;forward=false;
   if(s->r.error==Error::None&&s->pendingTicket&&std::uint64_t(wparam)==s->pendingTicket&&std::uint64_t(lparam)==s->pendingRevision){
    if(s->pendingRetire){
     #ifdef PLANNING_INPUT_BOUNDARY_FIXTURE
     PlanningInputBoundaryBeforePublish(window,true);
#endif
     SetLastError(0);const auto before=SetWindowLongPtrA(window,GWLP_WNDPROC,LONG_PTR(s->original));
     s->r.installed=uintptr_t(GetWindowLongPtrA(window,GWLP_WNDPROC))==uintptr_t(entryFor(index));
     if(before!=LONG_PTR(entryFor(index))||uintptr_t(GetWindowLongPtrA(window,GWLP_WNDPROC))!=uintptr_t(s->original)){s->r.publicationConflict=true;s->r.foreignSourceMayHaveBeenReplaced=before&&before!=LONG_PTR(entryFor(index));s->fail(Error::Publish);}
     else {s->r.retired=true;s->r.installed=false;s->r.retirementAcknowledged=true;}
    }
    s->r.held=s->pendingValue;s->r.acknowledgedRevision=s->pendingRevision;s->r.acknowledged=s->r.error==Error::None;s->observedAt=s->r.auditedSuppressed;s->pendingTicket=0;
   }else ++s->r.ignoredControl;
  }else {
   const auto decision=ni::ClassifyMessage({uintptr_t(window),message,uintptr_t(wparam),intptr_t(lparam)},uintptr_t(s->c.window),s->r.held&&!s->r.retired&&s->r.error==Error::None);
   if(decision.discard){++s->r.auditedSuppressed;forward=false;}
   else if(decision.classification==ni::MessageClass::AuditedGameplayInput)++s->r.auditedForwarded;
   else if(decision.classification==ni::MessageClass::Lifecycle)++s->r.lifecycleForwarded;
   else if(decision.classification==ni::MessageClass::UncoveredInput)++s->r.uncoveredForwarded;
   else ++s->r.unclassifiedForwarded;
  }
  ReleaseSRWLockExclusive(&s->lock);
  LRESULT result=0;bool returned=false;
  __try {result=forward?CallWindowProcA(original,window,message,wparam,lparam):0;returned=true;}
  __finally {AcquireSRWLockExclusive(&s->lock);--s->r.active;++s->r.finally;
   if(!returned)s->fail(Error::Exception);
   if(message==WM_NCDESTROY){s->r.destroyed=true;s->r.installed=false;s->r.acknowledged=false;s->r.held=false;s->pendingTicket=0;if(s->r.error==Error::None)s->r.error=Error::Destroyed;}
   ReleaseSRWLockExclusive(&s->lock);}
  return result;
 }
};
Boundary::Boundary():p_(new Impl){}
bool Boundary::Initialize(const Config&c)noexcept {auto&s=*p_;AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(s.attempted)__leave;s.attempted=true;s.c=c;if(!c.controller||!c.base||c.base>UINTPTR_MAX-0x2300000||!c.window){s.fail(Error::Config);__leave;}
  s.r.process=GetCurrentProcessId();DWORD pid=0;s.r.windowThread=GetWindowThreadProcessId(c.window,&pid);
  if(pid!=s.r.process||s.r.windowThread!=GetCurrentThreadId()){s.fail(Error::Thread);__leave;}
  pi::Report controller{};c.controller->Snapshot(controller);s.r.ownerThread=controller.thread;
  if(!s.controller(controller)||controller.requested){s.fail(Error::Identity);__leave;}
  if(!code(c.base,c.base+WndRva,WndSize)||!code(c.base,c.base+BodyRva,BodySize)){s.fail(Error::Source);__leave;}
  unsigned char hash[32]{};if(!native_storage_read::Sha256(reinterpret_cast<void*>(c.base+WndRva),WndSize,hash)||memcmp(hash,WndHash,32)){s.fail(Error::Source);__leave;}
#ifndef PLANNING_INPUT_BOUNDARY_FIXTURE
  if(!native_storage_read::Sha256(reinterpret_cast<void*>(c.base+BodyRva),BodySize,hash)||memcmp(hash,BodyHash,32)){s.fail(Error::Source);__leave;}
#else
  s.bodySize=32;
#endif
  memcpy(s.wndBytes,reinterpret_cast<void*>(c.base+WndRva),WndSize);memcpy(s.bodyBytes,reinterpret_cast<void*>(c.base+BodyRva),s.bodySize);
  if(!s.identity(false)){s.fail(Error::Identity);__leave;}
  s.r.controlMessage=RegisterWindowMessageA("San14.Coop.PlanningInputBoundary.v1");if(!s.r.controlMessage){s.fail(Error::Config);__leave;}
  const LONG index=InterlockedIncrement(&nextContext);if(index<0||index>=8){s.fail(Error::Publish);__leave;}s.r.callbackSlot=unsigned(index);if(InterlockedCompareExchangePointer(&contexts[index],&s,nullptr)){s.fail(Error::Publish);__leave;}
  s.original=reinterpret_cast<WNDPROC>(c.base+WndRva);
#ifdef PLANNING_INPUT_BOUNDARY_FIXTURE
  PlanningInputBoundaryBeforePublish(c.window,false);
#endif
  SetLastError(0);
  const auto previous=SetWindowLongPtrA(c.window,GWLP_WNDPROC,LONG_PTR(Impl::entryFor(s.r.callbackSlot)));const auto error=GetLastError();
  if(!previous&&error){s.fail(Error::Publish);__leave;}
  s.r.installed=uintptr_t(GetWindowLongPtrA(c.window,GWLP_WNDPROC))==uintptr_t(Impl::entryFor(s.r.callbackSlot));
  if(previous!=LONG_PTR(s.original)){s.r.publicationConflict=true;s.r.foreignSourceMayHaveBeenReplaced=true;s.original=reinterpret_cast<WNDPROC>(previous);s.fail(Error::Publish);__leave;}
  if(!s.r.installed||!s.identity(true)){s.fail(Error::Publish);__leave;}s.r.initialized=true;ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Source);}ReleaseSRWLockExclusive(&s.lock);return ok;}
bool Boundary::Request(bool held,std::uint64_t revision,bool&duplicate)noexcept {auto&s=*p_;duplicate=false;pi::Report x{};
 // Never hold a boundary lock while sampling Controller or Owner reports.
 if(!s.c.controller||!s.controller(x)||GetCurrentThreadId()!=s.r.ownerThread||!revision||x.revision!=revision||x.requested!=held||(held&&(!x.observed||x.coverage!=pi::BoundedCoverage)))return false;
 AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(!s.r.initialized||s.r.error!=Error::None||s.r.destroyed||s.r.retired||!s.identity(true))__leave;
  if(revision<s.r.revision)__leave;if(revision==s.r.revision){duplicate=s.r.requested==held;ok=duplicate;__leave;}
  if(s.r.ticket==UINT64_MAX)__leave;if(s.pendingTicket){s.fail(Error::Conflict);__leave;}s.r.revision=revision;s.r.requested=held;s.r.acknowledged=false;s.pendingRevision=revision;s.pendingValue=held;s.pendingRetire=false;s.pendingTicket=++s.r.ticket;
  if(!PostMessageA(s.c.window,s.r.controlMessage,WPARAM(s.pendingTicket),LPARAM(revision))){s.fail(Error::Post);__leave;}ok=true;
 }__finally {ReleaseSRWLockExclusive(&s.lock);}return ok;}
bool Boundary::Retire(std::uint64_t revision,bool&duplicate)noexcept {auto&s=*p_;duplicate=false;pi::Report x{};
 if(!s.c.controller||GetCurrentThreadId()!=s.r.ownerThread)return false;
 AcquireSRWLockExclusive(&s.lock);if(s.r.retired){duplicate=revision==s.r.revision&&s.r.retirementAcknowledged&&!s.r.active;ReleaseSRWLockExclusive(&s.lock);return duplicate;}ReleaseSRWLockExclusive(&s.lock);
 if(!s.controller(x)||x.requested||x.revision!=revision)return false;
 AcquireSRWLockExclusive(&s.lock);bool ok=false;
 __try {if(!s.r.initialized||s.r.error!=Error::None||s.r.destroyed||!s.identity(true)||s.r.held||s.r.requested||s.pendingTicket||!s.r.acknowledged||s.r.acknowledgedRevision!=revision||s.r.revision!=revision||s.r.ticket==UINT64_MAX)__leave;
  s.r.acknowledged=false;s.pendingRetire=true;s.pendingRevision=revision;s.pendingValue=false;s.pendingTicket=++s.r.ticket;
  if(!PostMessageA(s.c.window,s.r.controlMessage,WPARAM(s.pendingTicket),LPARAM(revision))){s.fail(Error::Post);__leave;}ok=true;
 }__finally {ReleaseSRWLockExclusive(&s.lock);}return ok;}
void Boundary::Snapshot(Report&out)noexcept {auto&s=*p_;pi::Report x{};const bool valid=s.c.controller&&s.controller(x);
 AcquireSRWLockExclusive(&s.lock);__try {out=s.r;
  const bool current=valid&&s.r.initialized&&s.r.error==Error::None&&!s.r.destroyed&&s.identity(true)&&!s.r.active&&x.revision==s.r.revision&&x.requested==s.r.requested&&(!s.r.requested||(x.observed&&x.coverage==pi::BoundedCoverage));
  out.retirementAcknowledged=out.retired&&out.retirementAcknowledged&&out.error==Error::None&&!out.active;
  out.acknowledged=out.acknowledged&&!out.retired&&current&&s.pendingTicket==0&&out.acknowledgedRevision==out.revision;
  out.auditedSuppressionObserved=out.acknowledged&&out.held&&out.auditedSuppressed>s.observedAt;
 }__finally {ReleaseSRWLockExclusive(&s.lock);}}
}
