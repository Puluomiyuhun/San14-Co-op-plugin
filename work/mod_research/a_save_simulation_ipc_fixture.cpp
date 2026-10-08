// Owned synchronous engine-thread fixture, not a production game scheduler.
#include "planning_checkpoint_save.h"
#include "planning_simulation_boundary.h"
#include "planning_period_session.h"
#include "planning_period_base_fixture.inc"
#include "a_save_held_ipc.h"
#include <fcntl.h>
#include <io.h>
namespace pcs=planning_checkpoint_save;namespace hi=a_save_held_ipc;
#pragma pack(push,1)
struct ScopeWire {unsigned char room[16],binding[16],epoch[16],digest[32];std::uint64_t period,cut;unsigned short year;unsigned char month,day,viewer;};
struct Bootstrap {unsigned char secret[32],room_id[32];std::uint64_t epoch;unsigned char nonce[16];};
#pragma pack(pop)
static_assert(sizeof(Bootstrap)==88);static_assert(sizeof(ScopeWire)==101);
static planning_period_session::Scope planningScope{};
static planning_period_session::Session*periodSession=new planning_period_session::Session;
static unsigned runs=0;
static planning_input_interlock::Controller*currentController=&interlock;
static ar::Config currentReward{};
static planning_period_session::Scope decode(const ScopeWire&w){
 planning_period_session::Scope out{};memcpy(out.room.data(),w.room,16);memcpy(out.bindingEpoch.data(),w.binding,16);memcpy(out.timelineEpoch.data(),w.epoch,16);memcpy(out.scopeDigest.data(),w.digest,32);
 out.period=w.period;out.baseSequence=w.cut;out.date={w.year,w.month,w.day,w.viewer};return out;
}
static bool simulateDiagnostic(void*)noexcept {
 ++runs;auto d=planningScope.date;
 if(d.day!=21)d.day+=10;else{d.day=1;if(d.month!=12)++d.month;else{d.month=1;++d.year;}}
 // Test double: no battle engine. These are owned fixture memory only.
 put<unsigned short>(world+0x34,d.year);put<unsigned char>(world+0x36,d.month);put<unsigned char>(world+0x37,d.day);
 return gameDispatch()==0&&rewardDispatch()==0;
}
static pcs::Evidence evidence;
static unsigned submitCalls=0,copyCalls=0;static HANDLE shutdownEvent=nullptr;static bool stopInPermit=false;
static bool permit(void*,const fs::Request&q,const unsigned char*)noexcept{
 if(stopInPermit)SetEvent(shutdownEvent);
 auto d=planningScope.date;if(runs)d={get<unsigned short>(world+0x34),get<unsigned char>(world+0x36),get<unsigned char>(world+0x37),get<unsigned char>(world+0x3A)};if(d.day!=21)d.day+=10;else{d.day=1;if(d.month!=12)++d.month;else{d.month=1;++d.year;}}
 return q.generation>=1&&q.generation<=2&&q.period==q.generation&&q.year==d.year&&q.month==d.month&&q.day==d.day&&q.force==d.viewer&&q.ruler==666;
}
static bool save(void*,const fs::Request&q,const unsigned char*)noexcept{
 ++submitCalls;
 if(q.generation==2){
  // Trusted owned parent sends this new identity only after model B completion.
  // This test stdio is configuration only; native save still arrives via pipe.
  ScopeWire nextWire{};if(fread(&nextWire,1,sizeof nextWire,stdin)!=sizeof nextWire)return false;
  auto nextScope=decode(nextWire);planning_period_owner::Receipt receipt{};
  check(currentController->BeginObservation(evidence.readyRevision)&&gameDispatch()==0&&rewardDispatch()==0&&currentController->EndObservation(evidence.readyRevision),"actual post-Copy observation before Session retirement");
  auto rewritten=planningScope;rewritten.date=nextScope.date;
  check(!periodSession->Retire(rewritten,receipt),"cannot rewrite original planning scope to checkpoint date");
  if(!periodSession->Retire(planningScope,receipt))return false;
  planning_period_session::Next next{};if(!periodSession->PlanNext(nextScope,next))return false;
  auto changed=planningScope;changed.timelineEpoch=nextScope.timelineEpoch;
  planning_period_session::Next wrong{};check(!periodSession->PlanNext(changed,wrong),"new epoch alone cannot impersonate next period");
  auto invalid=nextScope;invalid.timelineEpoch=planningScope.timelineEpoch;
  check(!periodSession->PlanNext(invalid,wrong),"old network epoch cannot become next native period");
  invalid=nextScope;invalid.room[0]^=1;check(!periodSession->PlanNext(invalid,wrong),"different room rejected");
  invalid=nextScope;invalid.baseSequence++;check(!periodSession->PlanNext(invalid,wrong),"different cut rejected");
  invalid=nextScope;invalid.date.day=21;check(!periodSession->PlanNext(invalid,wrong),"skipped next planning date rejected");
  rd->binding=next.binding;currentReward.binding=next.binding;
  if(!periodSession->Rebind(next,currentReward))return false;
  auto*controller=new planning_input_interlock::Controller;
  planning_input_interlock::Config config{};config.owner=session;config.gate=input;config.binding=next.binding;config.base=b;config.root=root;config.world=world;
  if(!controller->Initialize(config)||!periodSession->Adopt(*controller))return false;
  currentController=controller;planningScope=nextScope;
  check(controller->BeginObservation(evidence.readyRevision)&&gameDispatch()==0&&rewardDispatch()==0&&controller->EndObservation(evidence.readyRevision),"new period actual Ready observation");
  planning_input_interlock::Report observed{};controller->Snapshot(observed);planning_period_owner::Report actual{};planning_period_owner::Snapshot(*session,actual);
  evidence.binding=actual.binding;evidence.date=actual.date;evidence.periodSerial=actual.serial;evidence.readyRevision=observed.revision;evidence.gateRevision=observed.gateRevision;evidence.observation=observed.observation;evidence.cut=actual.reward.completed;
  planning_period_session::Scope historical{};planning_period_owner::Receipt historicalReceipt{};
  check(periodSession->Historical(1,historical,historicalReceipt)&&historical.date.day==1&&historicalReceipt.date.day==11,"Session preserves original planning scope and end-date receipt");
  printf("{\"event\":\"NEXT_SCOPE_ADOPTED\",\"period\":%llu,\"initial_day\":%u,\"native_digest\":\"",planningScope.period,planningScope.date.day);for(auto x:evidence.binding.room_input_digest)printf("%02x",x);puts("\"}");fflush(stdout);
 }
 check(!session->Submit(q),"ordinary Submit still refuses held Ready");
 if(q.cut!=evidence.cut)return false;
 auto initial=evidence;
 if(!planning_simulation_boundary::Execute(*session,*input,*currentController,initial,simulateDiagnostic,nullptr))return false;
 check(!pcs::Submit(*session,*input,*currentController,initial,q),"old planning observation cannot admit end-date Save");
 check(currentController->BeginObservation(initial.readyRevision)&&gameDispatch()==0&&rewardDispatch()==0&&currentController->EndObservation(initial.readyRevision),"new actual end-date observation after trusted diagnostic callback");
 planning_input_interlock::Report after{};currentController->Snapshot(after);planning_period_owner::Report current{};
 check(planning_period_owner::Snapshot(*session,current),"post-simulation native date");
 evidence.date=current.date;evidence.readyRevision=after.revision;evidence.gateRevision=after.gateRevision;evidence.observation=after.observation;
 check(current.binding.epoch==initial.binding.epoch&&current.binding.period==initial.binding.period&&current.serial==initial.periodSerial,"same native logical period and epoch after date transition");
 printf("{\"event\":\"SIMULATION_BOUNDARY_COMPLETE\",\"initial_day\":%u,\"saved_day\":%u,\"same_epoch\":true,\"actual_battle_engine\":false}\n",planningScope.date.day,current.date.day);fflush(stdout);
 if(failed||!pcs::Submit(*session,*input,*currentController,evidence,q))return false;
 // This owned thread plays both the trusted host and diagnostic engine. Real
 // games need owner-thread dispatch; a pipe service cannot invoke this directly.
 check(dispatch(0,user)==0,"held-save uses actual User bridge");completeSave();
 ar::Report reward{};ar::Snapshot(*session,reward);ag::Report gate{};input->Snapshot(gate);
 check(reward.readyFence&&reward.readyRevision==1&&gate.requested,"Ready and Gate remain held during native save");return !failed;
}
static bool copy(void*,std::uint64_t generation,fs::Artifact&artifact)noexcept{
 ++copyCalls;if(!pcs::Copy(*session,*input,*currentController,evidence,generation,artifact))return false;
 ar::Report reward{};ar::Snapshot(*session,reward);ag::Report gate{};input->Snapshot(gate);
 check(reward.readyFence&&reward.readyRevision==1&&gate.requested,"Copy completes without releasing either hold");
 printf("{\"event\":\"HELD_SAVE_COPIED\",\"generation\":%llu,\"ready_held\":%s,\"gate_held\":%s,\"ready_revision\":%llu,\"game_access\":false,\"production_permit\":false}\n",generation,reward.readyFence?"true":"false",gate.requested?"true":"false",reward.readyRevision);fflush(stdout);return !failed;
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4&&(argc!=5||strcmp(argv[4],"permit-stop")))return 2;
 _setmode(_fileno(stdin),_O_BINARY);mode="held-ipc";stopInPermit=argc==5;
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"PREPARED\",\"pid\":%lu,\"birth\":\"%llu\",\"game_access\":false}\n",GetCurrentProcessId(),birth());fflush(stdout);
 Bootstrap init{};if(fread(&init,1,sizeof init,stdin)!=sizeof init)return 3;
 ScopeWire wire{};if(fread(&wire,1,sizeof wire,stdin)!=sizeof wire)return 3;
 memcpy(planningScope.room.data(),wire.room,16);memcpy(planningScope.bindingEpoch.data(),wire.binding,16);memcpy(planningScope.timelineEpoch.data(),wire.epoch,16);memcpy(planningScope.scopeDigest.data(),wire.digest,32);
 planningScope=decode(wire);
 setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);
 cfg.room_epoch=init.epoch;memcpy(cfg.room_id,init.room_id,32);cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[1],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[2]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;put<unsigned short>(world+0x34,wire.year);put<unsigned char>(world+0x36,wire.month);put<unsigned char>(world+0x37,wire.day);put<unsigned char>(world+0x3A,wire.viewer);check(session->Initialize(cfg)&&session->Arm(),"one physical held-save Owner");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"matching held-save Gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1)&&gameDispatch()==0,"actual initial Game boundary");
 check(planning_period_session::MakeBinding(planningScope,cfg.input_binding,1,data.binding),"dynamic complete Room scope maps native binding");
 ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;currentReward=rc;check(ar::Bind(*session,rc),"same reward lane");
 planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;bool duplicate=false;
 check(interlock.Initialize(pc)&&interlock.Request(true,1,duplicate)&&interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"actual Controller Ready observation before pipe admission");
 check(periodSession->Initialize(*session,*input,*currentController,planningScope,rc,b,root,world),"actual retained Session binds captured planning start");
 planning_input_interlock::Report ir{};interlock.Snapshot(ir);planning_period_owner::Report pr{};check(planning_period_owner::Snapshot(*session,pr),"current native period");
 evidence.binding=data.binding;evidence.date=pr.date;evidence.periodSerial=pr.serial;evidence.readyRevision=ir.revision;evidence.gateRevision=ir.gateRevision;evidence.observation=ir.observation;evidence.cut=0;if(failed)return 4;
 printf("{\"event\":\"PLANNING_SCOPE_BOUND\",\"initial_day\":%u,\"period\":%llu,\"session_initialized\":true,\"native_digest\":\"",planningScope.date.day,planningScope.period);for(auto x:data.binding.room_input_digest)printf("%02x",x);puts("\"}");fflush(stdout);
 wchar_t name[180]=L"\\\\.\\pipe\\san14-a-save-";const auto prefix=wcslen(name);for(unsigned i=0;i<16;++i)swprintf_s(name+prefix+i*2,_countof(name)-prefix-i*2,L"%02x",init.nonce[i]);
 hi::Config c{};c.owner=session;c.pipeName=name;c.clientPid=strtoul(argv[3],nullptr,10);c.room_epoch=init.epoch;memcpy(c.room_id,init.room_id,32);memcpy(c.secret,init.secret,32);c.permit=permit;c.submit=save;c.copy=copy;
 // Missing execution ports cannot silently fall back to the legacy Owner API.
 {hi::Server absent;auto invalid=c;invalid.copy=nullptr;check(!absent.Open(invalid),"required complete trusted execution port pair");}
 // Failed Open's destructor calls Stop on c_.owner only after config acceptance;
 // the null-port refusal above must therefore leave the actual Owner alive.
 ss::Report alive{};session->Snapshot(alive);check(!alive.stopped,"null port refused before claiming live Owner");
 shutdownEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);if(!shutdownEvent)return 5;
 hi::Server server;if(!server.Open(c)){CloseHandle(shutdownEvent);return 6;}SecureZeroMemory(&init,sizeof init);SecureZeroMemory(c.secret,32);
 printf("{\"schema\":\"san14.a-save-ipc-fixture.v1\",\"event\":\"READY\",\"pid\":%lu,\"birth\":\"%llu\",\"source_kind\":\"FIXTURE_ONLY\",\"capabilities\":0,\"pipe_name\":\"",GetCurrentProcessId(),birth());for(const wchar_t*p=name;*p;++p){if(*p==L'\\')putchar('\\');putchar(char(*p));}puts("\"}");fflush(stdout);
 server.Run(shutdownEvent);CloseHandle(shutdownEvent);hi::Diagnostics d{};server.Inspect(d);ss::Report r{};session->Snapshot(r);ar::Report ar{};a_reward_save_owner::Snapshot(*session,ar);ag::Report g{};input->Snapshot(g);
 check(runs<=2,"at most two trusted diagnostic simulation callbacks");check(!r.active_scopes&&data.nodes.empty(),"actual callback scopes drained");
 printf("{\"event\":\"FINAL\",\"result\":\"%s\",\"game_access\":false,\"submits\":%llu,\"copies\":%llu,\"completed\":%u,\"owner_stopped\":%u,\"ipc_closed\":%s,\"active\":%llu,\"checks_failed\":%u,\"backend_submit_calls\":%u,\"backend_copy_calls\":%u,\"ready_held\":%s,\"gate_held\":%s,\"ready_revision\":%llu,\"full_input_held\":false,\"production_permit\":false}\n",failed?"FAIL":"PASS",d.submits,d.copies,r.save.completed_requests,r.stopped,d.closed?"true":"false",r.active_scopes,failed,submitCalls,copyCalls,ar.readyFence?"true":"false",g.requested?"true":"false",ar.readyRevision);fflush(stdout);return failed?7:0;
}
