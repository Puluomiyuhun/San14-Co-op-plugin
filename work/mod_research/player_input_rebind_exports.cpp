#include "player_input_rebind_exports.h"
#include "player_input_rebind_owner.h"
#include <cstring>
namespace {
namespace w=player_input_rebind_wire;namespace o=player_input_rebind;namespace p=player_input_policy;
o::Owner*owner=new o::Owner;w::Config config{};SRWLOCK lock=SRWLOCK_INIT;bool attempted=false;
bool copy(void*d,const void*s,size_t n)noexcept{__try{memcpy(d,s,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
std::uint64_t birth(){FILETIME b{},e{},k{},u{};return GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u)?(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime:0;}
p::Binding binding(const w::Binding&v){p::Binding b{};memcpy(b.room.data(),v.room,16);memcpy(b.attachment.data(),v.attachment,16);memcpy(b.epoch.data(),v.epoch,16);b.period=v.period;b.seat=v.seat;return b;}
bool nonce(const unsigned char*n){unsigned v=0;for(unsigned i=0;i<32;++i)v|=n[i];return v!=0;}
void snapshot(w::Snapshot&v){o::Report r{};owner->Snapshot(r);v.pid=config.pid;v.birth=config.birth;v.window=config.window;v.windowThread=r.windowThread;memcpy(v.binding.room,r.binding.room.data(),16);memcpy(v.binding.attachment,r.binding.attachment.data(),16);memcpy(v.binding.epoch,r.binding.epoch.data(),16);v.binding.period=r.binding.period;v.binding.seat=r.binding.seat;
 v.phase=unsigned(r.state.phase);v.localReady=r.state.localReady;v.error=unsigned(r.error);v.initialized=r.initialized;v.installed=r.installed;v.pending=r.pending;v.acknowledged=r.acknowledged;v.held=r.held;v.uncertain=r.uncertain;v.destroyed=r.destroyed;
 v.revision=r.revision;v.acknowledgedRevision=r.acknowledgedRevision;v.active=r.active;v.finally=r.finally;v.leaseId=r.lease.id;v.leaseSequence=r.lease.sequence;v.leaseRevision=r.lease.revision;v.leasesIssued=r.leasesIssued;v.leasesCompleted=r.leasesCompleted;v.suppressed=r.suppressed;v.auditedForwarded=r.auditedForwarded;v.lifecycleForwarded=r.lifecycleForwarded;v.uncoveredForwarded=r.uncoveredForwarded;v.unclassifiedForwarded=r.unclassifiedForwarded;v.publicationWrites=r.publicationWrites;
 v.remoteMessagesAllowed=r.remoteMessagesAllowed;v.remoteExecutionPolicyOpen=r.remoteExecutionPolicyOpen;v.localCommandPolicyOpen=r.localCommandPolicyOpen;v.allInputHeld=0;v.osQueueDrained=0;v.nativeReceiptVerified=0;v.controlMessage=r.controlMessage;
}
template<class T>DWORD invoke(void*ptr,w::Op op)noexcept{T v{};if(!ptr||!copy(&v,ptr,sizeof v)||v.header.magic!=w::Magic||v.header.version!=1||v.header.size!=sizeof v||v.header.op!=unsigned(op)||v.header.result)return 1;
 AcquireSRWLockExclusive(&lock);unsigned result=2;
 __try{__try{
 if constexpr(sizeof(T)==sizeof(w::Config)){
  if(attempted||v.pid!=GetCurrentProcessId()||v.birth!=birth()||!nonce(v.nonce))__leave;attempted=true;config=v;
  o::Config c{};c.base=uintptr_t(v.base);c.window=HWND(uintptr_t(v.window));c.binding=binding(v.binding);if(owner->Initialize(c))result=0;
 }else{
  if(!attempted||memcmp(v.nonce,config.nonce,32)||config.pid!=GetCurrentProcessId()||config.birth!=birth())__leave;
  if constexpr(sizeof(T)==sizeof(w::Snapshot)){snapshot(v);result=0;}
  else if constexpr(sizeof(T)==sizeof(w::Rebind)){if(owner->Rebind(binding(v.binding),binding(v.nextBinding),v.revision))result=0;}
  else if constexpr(sizeof(T)==sizeof(w::Request)){bool duplicate=false;if(v.localReady<=1&&owner->Request(binding(v.binding),{p::Phase(v.phase),v.localReady!=0},v.revision,duplicate))result=0;}
  else {o::Lease lease{v.lease,v.sequence,v.revision};bool ok=false;
   if(op==w::Op::Acquire){if(!v.lease)ok=owner->Acquire(binding(v.binding),v.revision,v.sequence,lease);if(ok)v.lease=lease.id;}
   else if(op==w::Op::Complete)ok=owner->Complete(binding(v.binding),lease);
   else if(op==w::Op::Unknown)ok=owner->Unknown(binding(v.binding),lease);
   if(ok)result=0;
  }
 }
 }__except(EXCEPTION_EXECUTE_HANDLER){result=3;}}
 __finally{ReleaseSRWLockExclusive(&lock);}v.header.result=result;return copy(ptr,&v,sizeof v)?result:1;
}
}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputInitialize(void*p)noexcept{return invoke<w::Config>(p,w::Op::Initialize);}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputRequest(void*p)noexcept{return invoke<w::Request>(p,w::Op::Request);}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputAcquire(void*p)noexcept{return invoke<w::Lease>(p,w::Op::Acquire);}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputComplete(void*p)noexcept{return invoke<w::Lease>(p,w::Op::Complete);}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputUnknown(void*p)noexcept{return invoke<w::Lease>(p,w::Op::Unknown);}
extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputSnapshot(void*p)noexcept{return invoke<w::Snapshot>(p,w::Op::Snapshot);}

extern "C" __declspec(dllexport) DWORD WINAPI PlayerInputRebind(void*p)noexcept{return invoke<w::Rebind>(p,w::Op::Rebind);}
