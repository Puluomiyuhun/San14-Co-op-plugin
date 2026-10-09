#include "a_save_abort_owner.h"
#include "a_save_runtime_exports.h"
#include "a_native_turn_runtime.h"
#include "a_save_repeat_exports.h"
#include "a_save_runtime_publish_evidence.h"
#include <cstring>
#include <new>
namespace w=a_save_runtime_wire;
namespace r=a_save_local_runtime;
namespace {
volatile LONG busy=0,used=0,stopped=0,serverStarted=0,serverExited=0,serverSucceeded=0;
r::Runtime*runtime=nullptr;r::Plans plans{};w::Prepare prepared{};
a_save_dispatch_ipc::Server*server=nullptr;HANDLE shutdownEvent=nullptr,serverThread=nullptr;HMODULE module=nullptr;
bool transfer(void*dst,const void*src,size_t n)noexcept {__try {memcpy(dst,src,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool nonzero(const unsigned char*p,size_t n)noexcept {unsigned x=0;for(size_t i=0;i<n;++i)x|=p[i];return x!=0;}
bool sameNonce(const unsigned char*n)noexcept {return nonzero(prepared.nonce,32)&&!memcmp(n,prepared.nonce,32);}
template<class T>bool read(void*p,T&v,w::Op op)noexcept {w::Header h{};return p&&transfer(&h,p,sizeof h)&&h.magic==w::Magic&&h.version==w::Version&&h.size==sizeof v&&h.operation==unsigned(op)&&!h.result&&transfer(&v,p,sizeof v);}
template<class T>DWORD finish(void*p,T&v,w::Result result)noexcept {v.header.result=unsigned(result);return transfer(p,&v,sizeof v)?unsigned(result):unsigned(w::Result::BadEnvelope);}
void binding(const w::NativeBinding&s,checkpoint_native_input::Binding&d)noexcept {memcpy(d.attempt.data(),s.attempt,16);memcpy(d.attachment.data(),s.attachment,16);d.owner_generation=s.ownerGeneration;}
void endpoint(const w::Endpoint&s,checkpoint_live_storage_binding::Endpoint&d)noexcept {d.address=s.address;d.moduleIndex=s.moduleIndex;memcpy(d.first32,s.first32,32);}
void config(const w::Prepare&s,r::Config&d)noexcept {
 d.pid=s.pid;d.birth=s.birth;d.base=s.base;memcpy(d.roomId,s.roomId,32);d.nativeRoomEpoch=s.nativeRoomEpoch;
 d.source.base=s.base;binding(s.native,d.source.binding);d.source.root=s.root;d.source.world=s.world;d.source.cache=s.cache;memcpy(d.source.states,s.states,sizeof s.states);
 const auto&a=s.storage;auto&b=d.storage;b.attachment.pid=a.pid;b.attachment.birth=a.birth;b.attachment.attempt=a.attempt;b.attachment.generation=a.generation;b.attachment.base=a.base;
 memcpy(b.attachment.id,a.id,32);memcpy(b.attachment.gameSha256,a.gameSha256,32);b.moduleCount=a.moduleCount;
 for(unsigned i=0;i<3;++i){const auto&m=a.modules[i];auto&n=b.modules[i];n.base=m.base;n.sizeOfImage=m.sizeOfImage;n.timestamp=m.timestamp;memcpy(n.path,m.path,sizeof m.path);n.fileSize=m.fileSize;memcpy(n.fileSha256,m.fileSha256,32);memcpy(n.headerSha256,m.headerSha256,32);}
 endpoint(a.contextInit,b.contextInit);endpoint(a.exists,b.exists);endpoint(a.size,b.size);endpoint(a.read,b.read);b.storage=a.storage;b.vtable=a.vtable;b.counter=a.counter;b.vtableModuleIndex=a.vtableModuleIndex;b.counterModuleIndex=a.counterModuleIndex;b.cachedGeneration=a.cachedGeneration;memcpy(b.contextCode,a.contextCode,sizeof a.contextCode);
 d.planning.native=d.source.binding;d.planning.period=s.period;d.planning.epoch=s.epoch;memcpy(d.planning.room_input_digest.data(),s.roomInputDigest,32);
 d.year=s.year;d.ruler=s.ruler;d.month=s.month;d.day=s.day;d.force=s.force;memcpy(d.saveDirectory,s.saveDirectory,sizeof s.saveDirectory);memcpy(d.intentDirectory,s.intentDirectory,sizeof s.intentDirectory);
}
DWORD WINAPI serve(void*)noexcept {const bool ok=server->Run(shutdownEvent);InterlockedExchange(&serverSucceeded,ok?1:0);runtime->Stop();InterlockedExchange(&serverExited,1);return ok?0:1;}
w::Result prepare(w::Prepare&v) {
 if(InterlockedCompareExchange(&stopped,0,0))return w::Result::Stopped;
 if(v.reserved||!nonzero(v.nonce,32))return w::Result::Rejected;
 if(InterlockedCompareExchange(&used,1,0))return w::Result::Used;
 prepared=v;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&ASaveRuntimePrepare),&module))return w::Result::Rejected;
 runtime=new(std::nothrow)r::Runtime;if(!runtime)return w::Result::Allocation;
 r::Config c{};config(v,c);return runtime->Prepare(c,plans)?w::Result::Ok:w::Result::Rejected;
}
w::Result plan(w::Plans&v)noexcept {
 memset(v.inlines,0,sizeof v.inlines);memset(v.slots,0,sizeof v.slots);memset(v.counters,0,sizeof v.counters);
 r::Report report{};runtime->Snapshot(report);if(!report.prepared)return w::Result::NotPrepared;
 v.pid=prepared.pid;v.birth=prepared.birth;v.base=prepared.base;v.module=uintptr_t(module);
 for(unsigned i=0;i<3;++i){auto&p=v.inlines[i];MEMORY_BASIC_INFORMATION mi{};
  if(i<2){const auto&q=plans.gate.patches[i];p.address=q.address;p.size=q.size;p.relay=plans.gate.relay;memcpy(p.before,q.before,7);memcpy(p.after,q.after,7);}
  else{p.address=plans.parent.site;p.relay=plans.parent.relay;p.size=5;memcpy(p.before,plans.parent.before,5);memcpy(p.after,plans.parent.after,5);}
  if(VirtualQuery(reinterpret_cast<void*>(p.address),&mi,sizeof mi)!=sizeof mi)return w::Result::Rejected;p.protection=mi.Protect;
 }
 for(unsigned i=0;i<4;++i){const auto&e=i<2?plans.ownerSlots.entries[i]:plans.gateSlots.entries[i-2];auto&s=v.slots[i];if(!e.known)return w::Result::Rejected;s.address=uintptr_t(e.binding.slot);s.original=uintptr_t(e.binding.original);s.hook=uintptr_t(e.binding.hook);s.protection=e.protection;}
 return ASaveRuntimeUserCounters(v.counters)&&ASaveRuntimeGateCounters(v.counters+2)&&ASaveRuntimeParentCounters(v.counters+5)?w::Result::Ok:w::Result::Rejected;
}
w::Result snapshot(w::Snapshot&v)noexcept {
 w::Counter before[7]{};std::uint32_t valid=0,lease=0,frame=0,state=0;std::uint64_t sequence=0;
 v.restoreReady=0;v.hostCacheValid=0;v.hostCacheAddress=ASaveRuntimePublishHostCacheAddress();memset(v.counters,0,sizeof v.counters);
 if(!ASaveRuntimePublishEvidence(before,&valid,&lease,&frame,&state,&sequence))return w::Result::NotReady;
 r::Report x{};runtime->Snapshot(x);v.error=unsigned(x.error);v.prepared=x.prepared;v.ownerArmed=x.ownerArmed;v.sourcesArmed=x.sourcesArmed;v.stopped=x.stopped;v.ready=x.readyForControlledRequest;
 const auto&o=x.owner;const auto&s=o.save;v.ownerError=unsigned(o.error);v.ownerStopped=o.stopped;v.saveLane=o.save_lane;v.saveStatus=unsigned(s.status);v.saveError=s.error;v.binds=s.binds;v.queues=s.queues;v.phaseMask=s.phase_mask;v.workerJoined=s.worker_joined;v.originalReturned=s.original_returned;v.fileVerified=s.file_bytes_verified;
 v.saveGeneration=s.generation;v.saveActive=s.active;v.ownerActive=o.active_scopes;v.gateActive=x.gate.active;v.parentActive=x.parent.active;v.parentBefore=x.parent.before;v.parentAfter=x.parent.after;v.parentFinally=x.parent.finally;
 v.parentError=unsigned(x.parent.error);v.hostInitialized=x.parent.hostInitialized;v.hostThread=x.parent.hostThread;v.mailboxStopped=x.mailbox.stopped;v.mailboxCount=x.mailbox.count;for(unsigned i=0;i<2;++i)v.mailboxStates[i]=unsigned(x.mailbox.records[i].state);
 std::uint64_t nextSequence=0;if(!ASaveRuntimePublishEvidence(v.counters,&valid,&lease,&frame,&state,&nextSequence))return w::Result::NotReady;
 v.hostCacheValid=valid;v.hostLease=lease;v.hostFrame=frame;v.hostState=state;v.hostCacheSequence=nextSequence;
 for(unsigned i=0;i<7;++i)if(before[i].started!=v.counters[i].started)return w::Result::NotReady;
 if(sequence!=v.hostCacheSequence)return w::Result::NotReady;
 v.productionPermit=x.productionPermit;v.allWritersProven=x.allWritersProven;
 a_save_abort::Receipt abort{};const bool aborted=a_save_abort::Snapshot(prepared.base,s.generation,x.parent.hostThread,abort)&&abort.ownerError==unsigned(o.error)&&s.status==checkpoint_fresh_save::Status::Uncertain&&s.error==54&&!s.file_bytes_verified;
 const bool terminal=aborted||(s.status==checkpoint_fresh_save::Status::Idle&&!s.binds&&!s.queues)||(s.status==checkpoint_fresh_save::Status::Cancelled&&!s.binds&&!s.queues)||
  (s.status==checkpoint_fresh_save::Status::Complete&&s.file_bytes_verified&&s.worker_joined&&s.original_returned&&!s.error);
 // initializeHost marks hostInitialized before the first BeforeFrame, the
 // only operation that can acquire the producer lease. Failed pre-init Arm
 // therefore needs no fabricated host cache, but still needs stopped/drained
 // Owner and quiescent actual bridge banks.
 v.restoreReady=v.stopped&&v.ownerStopped&&(!v.hostInitialized||v.hostCacheValid)&&!v.hostLease&&!v.hostFrame&&!v.saveLane&&!v.saveActive&&!v.ownerActive&&!v.gateActive&&!v.parentActive&&terminal;
 r::RepeatReport repeat{};runtime->RepeatSnapshot(repeat);
 v.restoreReady=v.restoreReady&&!repeat.lease&&!repeat.frame&&!repeat.drainPending;
 return w::Result::Ok;
}
w::Result start(w::StartServer&v) {
 if(InterlockedCompareExchange(&stopped,0,0))return w::Result::Stopped;
 if(InterlockedCompareExchange(&serverStarted,0,0))return w::Result::Used;
 if(!wmemchr(v.pipeName,0,180)||!v.clientPid||!nonzero(v.secret,32))return w::Result::Rejected;
 a_save_dispatch_ipc::Config c{};if(!runtime->ConfigureTransport(c))return w::Result::NotReady;
 InterlockedExchange(&serverStarted,1);c.pipeName=v.pipeName;c.clientPid=v.clientPid;c.idleTimeoutMs=v.idleTimeoutMs;memcpy(c.secret,v.secret,32);
 server=new(std::nothrow)a_save_dispatch_ipc::Server;if(!server){InterlockedExchange(&serverExited,1);runtime->Stop();return w::Result::Allocation;}
 shutdownEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!shutdownEvent||!server->Open(c)){InterlockedExchange(&serverExited,1);runtime->Stop();return w::Result::Rejected;}
 serverThread=CreateThread(nullptr,0,serve,nullptr,0,nullptr);if(!serverThread){SetEvent(shutdownEvent);InterlockedExchange(&serverExited,1);runtime->Stop();return w::Result::Rejected;}return w::Result::Ok;
}
w::Result serverStatus(w::ServerStatus&v)noexcept {
 v.started=unsigned(InterlockedCompareExchange(&serverStarted,0,0));v.threadExited=unsigned(InterlockedCompareExchange(&serverExited,0,0));v.runSucceeded=unsigned(InterlockedCompareExchange(&serverSucceeded,0,0));
 a_save_dispatch_ipc::Diagnostics d{};if(server)server->Inspect(d);v.opened=d.opened;v.running=d.running;v.closed=d.closed;v.stopped=d.stopped;v.osError=d.osError;v.requests=d.requests;v.submits=d.submits;v.copies=d.copies;v.lastSequence=d.lastSequence;return w::Result::Ok;
}
template<class T>DWORD invoke(void*p,w::Op op,w::Result(*body)(T&))noexcept {T v{};if(!read(p,v,op))return unsigned(w::Result::BadEnvelope);
 if(InterlockedCompareExchange(&busy,1,0))return finish(p,v,w::Result::Busy);
 w::Result result=w::Result::Exception;try {if(op!=w::Op::Prepare&&(!runtime||!sameNonce(v.nonce)))result=w::Result::NotPrepared;else result=body(v);}catch(...){InterlockedExchange(&stopped,1);if(shutdownEvent)SetEvent(shutdownEvent);if(runtime)runtime->Stop();}
 InterlockedExchange(&busy,0);return finish(p,v,result);
}
namespace rw=a_save_repeat_wire;
void nextData(const rw::NextData&s,r::Next&d)noexcept {
 d.previousGeneration=s.previousGeneration;memcpy(d.previousSha256,s.previousSha256,32);
 d.generation=s.generation;d.period=s.period;d.epoch=s.epoch;memcpy(d.inputDigest,s.inputDigest,32);
 d.year=s.year;d.month=s.month;d.day=s.day;
}
void nextData(const r::Next&s,rw::NextData&d)noexcept {
 d.previousGeneration=s.previousGeneration;memcpy(d.previousSha256,s.previousSha256,32);
 d.generation=s.generation;d.period=s.period;d.epoch=s.epoch;memcpy(d.inputDigest,s.inputDigest,32);
 d.year=s.year;d.month=s.month;d.day=s.day;
}
w::Result requestNext(rw::Next&v)noexcept {
 if(InterlockedCompareExchange(&stopped,0,0))return w::Result::Stopped;
 r::Next n{};nextData(v.request,n);return runtime->RequestNext(n)?w::Result::Ok:w::Result::Rejected;
}
w::Result repeatSnapshot(rw::Snapshot&v)noexcept {
 r::RepeatReport x{};runtime->RepeatSnapshot(x);
 v.state=unsigned(x.state);v.error=unsigned(x.error);v.hostThread=x.hostThread;v.requested=x.requested;v.stopped=x.stopped;
 v.activeGeneration=x.activeGeneration;v.retiredSerial=x.retiredSerial;v.retiredCount=x.retiredCount;
 nextData(x.request,v.request);v.previousArtifactMatched=x.previousArtifactMatched;v.nativeDateMatched=x.nativeDateMatched;
 v.bLoadedProven=x.bLoadedProven;v.simulationEnabled=x.simulationEnabled;
 v.lease=x.lease;v.frame=x.frame;v.drainPending=x.drainPending;return w::Result::Ok;
}
w::Result armOwner(w::Command&)noexcept {return runtime->ArmOwner()?w::Result::Ok:w::Result::Rejected;}
w::Result armSources(w::Command&)noexcept {return runtime->ArmPublishedSources()?w::Result::Ok:w::Result::Rejected;}
w::Result stop(w::Command&)noexcept {InterlockedExchange(&stopped,1);if(shutdownEvent)SetEvent(shutdownEvent);runtime->Stop();return w::Result::Ok;}
}
A_SAVE_RUNTIME_EXPORT ASaveRuntimePrepare(void*p)noexcept{return invoke<w::Prepare>(p,w::Op::Prepare,prepare);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimePlans(void*p)noexcept{return invoke<w::Plans>(p,w::Op::Plans,plan);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeArmOwner(void*p)noexcept{return invoke<w::Command>(p,w::Op::ArmOwner,armOwner);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeArmPublishedSources(void*p)noexcept{return invoke<w::Command>(p,w::Op::ArmPublishedSources,armSources);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeSnapshot(void*p)noexcept{return invoke<w::Snapshot>(p,w::Op::Snapshot,snapshot);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeStop(void*p)noexcept{return invoke<w::Command>(p,w::Op::Stop,stop);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeStartServer(void*p)noexcept{return invoke<w::StartServer>(p,w::Op::StartServer,start);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeServerStatus(void*p)noexcept{return invoke<w::ServerStatus>(p,w::Op::ServerStatus,serverStatus);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRequestNext(void*p)noexcept{return invoke<a_save_repeat_wire::Next>(p,a_save_repeat_wire::NextOp,requestNext);}
A_SAVE_RUNTIME_EXPORT ASaveRuntimeRepeatSnapshot(void*p)noexcept{return invoke<a_save_repeat_wire::Snapshot>(p,a_save_repeat_wire::SnapshotOp,repeatSnapshot);}
