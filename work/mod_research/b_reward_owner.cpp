#include "b_reward_owner.h"
#include "a_runtime_reward_source.h"
#include "a_save_local_binding.h"
#include "a_save_early_guard.h"
#include "native_storage_read_core.h"
#include <cstring>
#ifdef B_REWARD_FIXTURE
#include <cstdio>
#endif
namespace {
namespace w=b_reward_wire;namespace a=a_runtime_reward_wire;namespace ph=checkpoint_planning_hold;namespace rw=checkpoint_reward_owned_replay;namespace pd=checkpoint_native_input_pending;
extern "C" bool ARewardSaveOwnerSuppressedConfigure(void(*)(const CheckpointLoadWorkerFrame*,void*));
#ifdef B_REWARD_FIXTURE
extern "C" uintptr_t BRewardFixtureCaller();
#endif
constexpr uintptr_t slots[]={0x12CC4D0,0x12DB4E8,0x12CC9E0,0x12DBD90,0x138E8D0};
constexpr uintptr_t originals[]={0x3F9B00,0x4AA200,0x3F8140,0x4A85C0,0x4FABC0};
template<class T>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}
bool nz(const unsigned char*p,size_t n){unsigned v=0;while(n--)v|=*p++;return v!=0;}
std::uint64_t birth(){FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
bool transfer(void*d,const void*s,size_t n)noexcept{__try{memcpy(d,s,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
struct Owner {
 SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0;w::Configure config{};w::Snapshot report{};ph::Binding binding{};
 a_save_local_binding::Sampler sampler;a_runtime_reward_source::SourceProvider source;a_save_early_guard::Guard guard;checkpoint_load_hook_set::Set hooks;
 rw::Command command{};rw::Owner*running=nullptr;bool stopped=false,armed=false,restored=false,success=false;unsigned short cursor=0;std::uint64_t scopes=0;
 void fail(unsigned e,bool uncertain=false){if(!report.reward.error)report.reward.error=e;report.reward.state=5;report.reward.uncertain|=unsigned(uncertain);stopped=true;report.reward.queued=0;success=false;}
 bool rawSlots(bool own)noexcept {__try{for(unsigned i=0;i<5;++i){const auto expected=i==0&&own?uintptr_t(&ASaveUserOwnerBridge0):config.base+originals[i];if(at<uintptr_t>(config.base+slots[i])!=expected)return false;}return at<uintptr_t>(config.storageVtable+8)==config.readOriginal;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool identity()noexcept {__try{return GetCurrentProcessId()==config.context.pid&&birth()==config.context.birth&&at<uintptr_t>(config.base+0x1FCA1E0)==config.root&&at<uintptr_t>(config.root+0x85130)==config.world&&at<unsigned short>(config.world+0x34)==config.year&&at<unsigned char>(config.world+0x36)==config.month&&at<unsigned char>(config.world+0x37)==config.day&&at<unsigned char>(config.world+0x3A)==config.viewer&&at<unsigned short>(config.world+0x165A)==cursor;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool code()noexcept {__try{
#ifndef B_REWARD_FIXTURE
 if(config.base!=uintptr_t(GetModuleHandleW(nullptr)))return false;
 constexpr unsigned char expected[]={0x20,0xda,0xc8,0x7a,0xef,0x24,0xde,0xbe,0x8d,0x58,0xea,0xc2,0x03,0x6f,0xca,0x2b,0x79,0x14,0x9d,0xa9,0x70,0xb7,0xd1,0xa9,0x0f,0xb4,0x5c,0xfb,0x2b,0x3e,0xab,0x94};
 unsigned char hash[32]{};if(!native_storage_read::Sha256(reinterpret_cast<const unsigned char*>(config.base+0x3F9B00),0x5B4,hash)||memcmp(hash,expected,32))return false;
#endif
 MEMORY_BASIC_INFORMATION m{};return VirtualQuery(reinterpret_cast<void*>(config.base+0x3F9B00),&m,sizeof m)==sizeof m&&(m.Protect==PAGE_EXECUTE_READ||m.Protect==PAGE_EXECUTE_WRITECOPY);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool idle(const CheckpointLoadWorkerFrame*f)noexcept{__try{
 auto caller=config.base+0x50B785;
#ifdef B_REWARD_FIXTURE
 caller=BRewardFixtureCaller();
#endif
 if(!f||f->slot||f->args[0]!=config.states[4]||!f->call_id||f->thread_id!=GetCurrentThreadId()||!f->caller_entry_rsp||at<uintptr_t>(f->caller_entry_rsp)!=caller||!identity()||!rawSlots(true)||!code())return false;
 pd::Config c{};if(!sampler.Capture(c))return false;pd::Adapter inspector;if(inspector.Bind(c)!=pd::Error::None)return false;auto v=inspector.InspectCurrent(binding.native);
 const auto g=guard.Observe(binding.native);
#ifdef B_REWARD_FIXTURE
 fprintf(stderr,"B idle input error %u decision %u guard %u\n",unsigned(v.error),unsigned(v.decision),unsigned(g.decision));
#endif
 return v.error==pd::Error::None&&v.decision==pd::Decision::QuiescentObserved&&g.decision==a_save_early_guard::Decision::QuietReportsObserved;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 static bool select(CheckpointLoadWorkerFrame*f,void*v)noexcept{auto&s=*static_cast<Owner*>(v);AcquireSRWLockExclusive(&s.lock);bool forward=true;
 __try{++s.scopes;f->reserved_58=0;if(s.stopped||!s.armed)__leave;if(!s.report.reward.queued)__leave;
 if(s.scopes!=1||!s.idle(f)){s.fail(3);__leave;}
 s.report.reward.queued=0;s.report.reward.active=1;s.report.reward.state=3;s.report.reward.hostThread=GetCurrentThreadId();s.success=false;f->reserved_58=5;f->result_rax=0;memset(f->result_xmm0,0,16);forward=false;
 }__finally{ReleaseSRWLockExclusive(&s.lock);}return forward;}
 static void replay(const CheckpointLoadWorkerFrame*f,void*v){auto&s=*static_cast<Owner*>(v);rw::Owner*reward=nullptr;ph::Context*hold=nullptr;bool success=false;rw::Report actual{};
 try{
  if(!ASaveUserOwnerClaim(f,s.binding.native.owner_generation))throw 3;
  CheckpointLoadWorkerOwner claimed{};if(!ASaveUserOwnerCurrentOwner(&claimed)||claimed.call_id!=f->call_id||claimed.token!=s.binding.native.owner_generation||claimed.slot||claimed.owner_depth!=claimed.current_depth)throw 3;
  a_reward_save_owner::Source fresh{};if(!s.source.Capture(s.config.states[4],s.command.command_force,fresh))throw 3;
  reward=RewardOwnedCreate(&fresh.reward);if(!reward)throw 4;
  AcquireSRWLockExclusive(&s.lock);s.running=reward;const bool live=!s.stopped;ReleaseSRWLockExclusive(&s.lock);if(!live)throw 5;
  fresh.admission.capture_owned_command=&RewardOwnedCapture;fresh.admission.replay_source_context=reward;hold=PlanningHoldCreate(&fresh.admission);if(!hold)throw 4;
  if(PlanningHoldRequest(hold,&s.binding,unsigned(ph::Operation::Hold),1)!=unsigned(ph::Status::Ok)||!RewardOwnedPrepare(reward,&s.command)||RewardOwnedExecute(reward,hold,1)!=1)throw 4;
  success=true;
 }catch(int e){AcquireSRWLockExclusive(&s.lock);s.fail(unsigned(e));ReleaseSRWLockExclusive(&s.lock);}catch(...){AcquireSRWLockExclusive(&s.lock);s.fail(6,true);ReleaseSRWLockExclusive(&s.lock);}
 if(reward)RewardOwnedSnapshot(reward,&actual);
 AcquireSRWLockExclusive(&s.lock);s.running=nullptr;ReleaseSRWLockExclusive(&s.lock);
 const bool cleaned=!reward||RewardOwnedDestroy(reward);if(hold)PlanningHoldDestroy(hold);
 AcquireSRWLockExclusive(&s.lock);auto&r=s.report.reward;r.replayState=unsigned(actual.state);r.replayError=unsigned(actual.error);r.nativeReturned=actual.native_returned;r.argsReleased=actual.args_released;r.ownedSlotCleared=actual.owned_slot_cleared;r.ctorCalls=actual.ctor_calls;r.appendCalls=actual.append_calls;r.dtorCalls=actual.dtor_calls;r.captureCalls=actual.capture_calls;r.executeCalls=actual.execute_calls;memcpy(r.commandSha256,actual.command_sha256.data(),32);memcpy(r.semanticSha256,actual.semantic_sha256.data(),32);
 s.report.nativeClean=cleaned&&(!reward||(actual.args_released&&actual.owned_slot_cleared));s.success=success&&cleaned&&!s.stopped;
 if(!cleaned)s.fail(7,true);else if(!success&&actual.native_returned)r.uncertain=1;ReleaseSRWLockExclusive(&s.lock);
 }
 static void finally(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*v)noexcept{auto&s=*static_cast<Owner*>(v);AcquireSRWLockExclusive(&s.lock);
 if(s.scopes)--s.scopes;else s.fail(3,true);if(f->reserved_58==5){auto&r=s.report.reward;r.active=0;++r.finallyCalls;if(e->abnormal){++r.abnormalCalls;s.fail(6,true);}else if(s.success&&!s.stopped&&s.identity()&&s.rawSlots(true)&&s.guard.Observe(s.binding.native).decision==a_save_early_guard::Decision::QuietReportsObserved){r.completed=r.submitted;r.state=4;}else if(!r.error)s.fail(3,r.nativeReturned!=0);}
 ReleaseSRWLockExclusive(&s.lock);}
 bool configure(const w::Configure&c)noexcept {if(InterlockedCompareExchange(&once,1,0))return false;config=c;report.reward.context=c.context;memcpy(report.reward.nonce,c.nonce,32);
 __try {if(c.reserved||c.context.pid!=GetCurrentProcessId()||c.context.birth!=birth()||!nz(c.nonce,32)||c.base<0x10000||c.base>UINTPTR_MAX-0x2300000||!c.storageVtable||!c.readOriginal)return false;
 memcpy(binding.native.attempt.data(),c.context.native.attempt,16);memcpy(binding.native.attachment.data(),c.context.native.attachment,16);binding.native.owner_generation=c.context.native.ownerGeneration;binding.period=c.context.period;binding.epoch=c.context.epoch;memcpy(binding.room_input_digest.data(),c.context.inputDigest,32);
 bool viewerBound=false;for(const auto&actor:c.actors)if(actor.force==c.viewer&&actor.ruler==c.ruler)viewerBound=true;if(!viewerBound)return false;
 cursor=at<unsigned short>(c.world+0x165A);if(!identity()||!rawSlots(false)||!code())return false;
 a_save_local_binding::Config input{};input.binding=binding.native;input.base=c.base;input.root=c.root;input.world=c.world;input.cache=c.cache;memcpy(input.states,c.states,sizeof input.states);if(!sampler.Initialize(input))return false;
 a_runtime_reward_source::Config sourceConfig{};sourceConfig.base=c.base;sourceConfig.root=c.root;sourceConfig.world=c.world;sourceConfig.user=c.states[4];sourceConfig.binding=binding;sourceConfig.year=c.year;sourceConfig.month=c.month;sourceConfig.day=c.day;sourceConfig.viewer=c.viewer;sourceConfig.sample_input=a_save_local_binding::Sampler::Sample;sourceConfig.input_context=&sampler;for(unsigned i=0;i<2;++i)sourceConfig.actors[i]={c.actors[i].force,c.actors[i].ruler,c.actors[i].district};if(!source.Initialize(sourceConfig))return false;
 a_save_early_guard::Config g{};g.base=c.base;g.root=c.root;g.world=c.world;g.user=c.states[4];g.binding=binding.native;if(!guard.Initialize(g)||guard.Observe(binding.native).decision!=a_save_early_guard::Decision::QuietReportsObserved)return false;
 ASaveUserOwnerBridgeConfig bridge{};bridge.size=sizeof bridge;bridge.original=reinterpret_cast<void*>(c.base+originals[0]);bridge.context=this;bridge.select=select;bridge.finally=finally;
 if(!ARewardSaveOwnerSuppressedConfigure(replay)||!ASaveUserOwnerBridgeConfigure(0,&bridge))return false;
 checkpoint_load_hook_set::Binding hook{reinterpret_cast<void*volatile*>(c.base+slots[0]),bridge.original,reinterpret_cast<void*>(&ASaveUserOwnerBridge0)};
 if(!hooks.Initialize(&hook,1)||!hooks.Publish(0))return false;armed=true;report.reward.configured=1;report.reward.state=1;report.nativeClean=1;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
 bool submit(const w::Submit&q)noexcept {
 auto&d=report.reward;if(!armed||stopped||!d.configured||d.queued||d.active||d.uncertain||d.error||d.submitted!=d.completed||q.sequence!=d.submitted+1||!q.sequence||memcmp(&q.context,&config.context,sizeof q.context)||!identity()||!rawSlots(true))return false;
 const auto&c=q.command;const a::Actor*actor=nullptr;for(const auto&x:config.actors)if(x.force==c.actor)actor=&x;const auto now=GetTickCount64();
 if(c.reserved||!actor||actor->ruler!=c.ruler||actor->district!=c.district||c.year!=config.year||c.month!=config.month||c.day!=config.day||c.viewer!=config.viewer||!nz(c.nonce,32)||!c.count||c.count>16||c.expiresAtTick<=now||c.expiresAtTick-now>60000)return false;
 for(unsigned i=0;i<16;++i){if(i<c.count){if(c.officers[i]>=6000)return false;for(unsigned j=0;j<i;++j)if(c.officers[i]==c.officers[j])return false;}else if(c.officers[i])return false;}
 command={};memcpy(command.nonce.data(),c.nonce,32);command.year=c.year;command.month=c.month;command.day=c.day;command.viewer_force=c.viewer;command.command_force=c.actor;command.ruler=c.ruler;command.funding_city=c.city;command.charged_district=c.district;command.count=c.count;memcpy(command.officers,c.officers,sizeof c.officers);command.expires_at_tick=c.expiresAtTick;
 d.sequence=d.submitted=q.sequence;d.state=2;d.queued=1;report.nativeClean=0;return true;
 }
 void stop(){stopped=true;if(report.reward.queued){report.reward.queued=0;report.nativeClean=1;report.reward.state=5;report.reward.error=5;}if(running)RewardOwnedCancel(running);}
 bool restore(){CheckpointLoadWorkerBridgeStats b{};if(!stopped||report.reward.queued||report.reward.active||scopes||running||!report.nativeClean||!ASaveUserOwnerBridgeSnapshot(0,&b)||b.active||b.cleanup_faults)return false;if(!hooks.RestoreAll())return false;restored=true;armed=false;return rawSlots(false);}
 void snapshot(w::Snapshot&out){out=report;auto&r=out.reward;r.stopped=stopped;r.queued=report.reward.queued;r.active=report.reward.active;r.readyResealed=0;out.armed=armed;out.admissionClosed=stopped;out.slotRestored=restored&&rawSlots(false);
 CheckpointLoadWorkerBridgeStats b{};ASaveUserOwnerBridgeSnapshot(0,&b);out.bridgeStarted=b.started;out.bridgeActive=b.active;out.bridgeFinally=b.finally_calls;out.bridgeCleanupFaults=b.cleanup_faults;
 out.restoreVerified=out.slotRestored&&stopped&&!scopes&&!r.active&&!r.queued&&!r.uncertain&&out.nativeClean&&!b.active&&!b.cleanup_faults;
 }
} owner;
volatile LONG callBusy=0;
template<class T>DWORD invoke(void*p,w::Op op)noexcept {T v{};a_save_runtime_wire::Header h{};if(!p||!transfer(&h,p,sizeof h)||h.magic!=a_save_runtime_wire::Magic||h.version!=1||h.size!=sizeof v||h.operation!=unsigned(op)||h.result||!transfer(&v,p,sizeof v))return 1;
 if(InterlockedCompareExchange(&callBusy,1,0))return 3;unsigned result=6;
 AcquireSRWLockExclusive(&owner.lock);
 __try {__try {auto*nonce=reinterpret_cast<unsigned char*>(&v)+sizeof h;if(op!=w::Op::Configure&&memcmp(nonce,owner.config.nonce,32))__leave;
 if constexpr(sizeof(T)==sizeof(w::Configure)){if(owner.configure(reinterpret_cast<const w::Configure&>(v)))result=0;else owner.fail(1);}
 else if constexpr(sizeof(T)==sizeof(w::Submit)){if(owner.submit(reinterpret_cast<const w::Submit&>(v)))result=0;}
 else if constexpr(sizeof(T)==sizeof(w::Snapshot)){owner.snapshot(reinterpret_cast<w::Snapshot&>(v));memcpy(reinterpret_cast<unsigned char*>(&v)+sizeof h,nonce,32);result=0;}
 else {if(op==w::Op::Stop){owner.stop();result=0;}else if(op==w::Op::Restore&&owner.restore())result=0;}
 }__except(EXCEPTION_EXECUTE_HANDLER){owner.fail(6,true);result=7;}}
 __finally{ReleaseSRWLockExclusive(&owner.lock);InterlockedExchange(&callBusy,0);}
 h.result=result;memcpy(&v,&h,sizeof h);return transfer(p,&v,sizeof v)?result:1;
}
}
extern "C" __declspec(dllexport) DWORD WINAPI BRewardConfigure(void*p)noexcept{return invoke<b_reward_wire::Configure>(p,b_reward_wire::Op::Configure);}
extern "C" __declspec(dllexport) DWORD WINAPI BRewardSubmit(void*p)noexcept{return invoke<b_reward_wire::Submit>(p,b_reward_wire::Op::Submit);}
extern "C" __declspec(dllexport) DWORD WINAPI BRewardSnapshot(void*p)noexcept{return invoke<b_reward_wire::Snapshot>(p,b_reward_wire::Op::Snapshot);}
extern "C" __declspec(dllexport) DWORD WINAPI BRewardStop(void*p)noexcept{return invoke<b_reward_wire::Command>(p,b_reward_wire::Op::Stop);}
extern "C" __declspec(dllexport) DWORD WINAPI BRewardRestore(void*p)noexcept{return invoke<b_reward_wire::Command>(p,b_reward_wire::Op::Restore);}
