#include "planning_simulation_boundary.h"
#include "planning_period_base_fixture.inc"
namespace pc=planning_checkpoint_save;namespace pp=planning_period_owner;
namespace sim=planning_simulation_boundary;
static unsigned calls=0;
static bool simulate(void*)noexcept {
 ++calls;bool duplicate=false;check(!ar::ReadyFence(*session,rd->binding,false,2)&&!input->Hold(ic.binding,false,3),"boundary blocks direct release");
 check(!interlock.Request(false,2,duplicate),"boundary blocks Controller release");
 if(mode=="simulation-fault")RaiseException(0xE014AC11,0,0,nullptr);
 if(mode!="simulation-no-date")put<unsigned char>(world+0x37,mode=="simulation-wrong-date"?1:21);
 if(mode=="simulation-root-change"){put<uintptr_t>(root+0x85130,world+16);return true;}
 if(mode=="simulation-no-callbacks")return true;
 if(mode=="simulation-no-user"){check(gameDispatch()==0,"actual Game only");return true;}
 if(mode=="simulation-no-game"){check(rewardDispatch()==0,"actual User only");return true;}
 if(mode=="simulation-stop"){session->Stop();return true;}
 if(mode=="simulation-source-conflict"){
  ss::Report r{};session->Snapshot(r);auto&e0=r.hooks.entries[0];DWORD old=0,tmp=0;
  check(VirtualProtect(const_cast<void**>(e0.binding.slot),8,PAGE_READWRITE,&old)!=0,"owned source page writable");
  InterlockedExchangePointer(e0.binding.slot,e0.binding.original);
  check(VirtualProtect(const_cast<void**>(e0.binding.slot),8,old,&tmp)!=0,"owned source page protection restored");return true;
 }
 check(gameDispatch()==0&&rewardDispatch()==0,"actual held Game and User return");
 if(mode=="simulation-pending")reportPending(true,false);
 return mode!="simulation-false";
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];
 setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);
 cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;
 cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);
 wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;check(session->Initialize(cfg)&&session->Arm(),"same real User/Save owner");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;
 ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"upstream Gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1),"held same Gate");
 check(gameDispatch()==0,"Game hold observed");ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;
 check(ar::Bind(*session,rc),"reward lane binds same Owner");auto command=data.command(2,1);
 check(ar::Submit(*session,data.binding,1,command)&&rewardDispatch()==0,"actual one reward completed before cut");
 planning_input_interlock::Config config{};config.owner=session;config.gate=input;config.binding=data.binding;config.base=b;config.root=root;config.world=world;
 check(interlock.Initialize(config),"Controller claims current native period");bool duplicate=false;
 check(interlock.Request(true,1,duplicate)&&!duplicate,"Ready closes User without release");
 if(mode!="checkpoint-no-observation")check(interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"actual User/Game/UI/panel observation");
 planning_input_interlock::Report held{};interlock.Snapshot(held);pp::Report period{};check(pp::Snapshot(*session,period),"period snapshot");
 pc::Evidence e{};e.binding=data.binding;e.date=period.date;e.periodSerial=period.serial;e.readyRevision=held.revision;
 e.gateRevision=held.gateRevision;e.observation=held.observation;e.cut=held.reward.completed;

 if(mode=="simulation-stale")check(gameDispatch()==0,"stale Game invalidates start");
 if(mode=="simulation-wrong-binding")++e.binding.epoch;
 if(mode=="simulation-wrong-serial")++e.periodSerial;
 bool accepted=false;
 if(mode=="simulation-wrong-thread"){std::thread t([&]{accepted=sim::Execute(*session,*input,interlock,e,simulate,nullptr);});t.join();}
 else accepted=sim::Execute(*session,*input,interlock,e,simulate,nullptr);
 const bool good=mode=="simulation-good";
 check(accepted==good,"only completed same-world same-period boundary advances date");
 sim::Report sr{};sim::Snapshot(sr);
 if(good){
  check(sr.phase==sim::Phase::Checkpoint&&sr.entered==1&&sr.returned==1&&sr.finallyCount==1&&sr.start.date.day==11&&sr.checkpointDate.day==21,"owned callback lifecycle and exact date transition");
  pp::Snapshot(*session,period);check(period.serial==e.periodSerial&&period.binding.epoch==e.binding.epoch&&period.binding.period==e.binding.period&&period.date.day==21,"epoch and period unchanged");
  check(!sim::Execute(*session,*input,interlock,e,simulate,nullptr)&&calls==1,"one boundary per period");
  check(interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"same Controller actual new checkpoint observation");
  interlock.Snapshot(held);e.date=period.date;e.observation=held.observation;
  auto q=request(1);q.day=21;q.cut=e.cut;check(!session->Submit(q),"default Submit refuses Ready");
  pp::Receipt receipt{};check(!pp::Retire(*session,*input,interlock,data.binding,receipt),"no retire before copy");
  check(pc::Submit(*session,*input,interlock,e,q),"same-period held checkpoint accepted");
  check(dispatch(0,user)==0,"actual User save admission");completeSave();fs::Artifact artifact{};
  check(pc::Copy(*session,*input,interlock,e,1,artifact)&&artifact.request.day==21&&!artifact.bytes.empty(),"actual diagnostic saved current next date");
  check(!ar::ReadyFence(*session,data.binding,false,2)&&!input->Hold(ic.binding,false,3),"Copy keeps phase fenced until explicit next period");
  check(interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"post-copy observed boundary");
  check(pp::Retire(*session,*input,interlock,data.binding,receipt),"retire completed checkpoint phase");
  auto next=rc;next.binding.period=2;next.binding.epoch=8;next.binding.room_input_digest[0]=7;data.binding=next.binding;
  check(pp::Rebind(*session,*input,next,1),"explicit next period binds SAME already reached date");
  planning_input_interlock::Controller nextController;config.binding=next.binding;
  check(nextController.Initialize(config)&&nextController.Request(false,2,duplicate),"next Controller alone can release after rebind");
 }else{
  ar::Report rr{};ar::Snapshot(*session,rr);ag::Report gr{};input->Snapshot(gr);check(rr.readyFence&&gr.requested,"failed boundary never releases hold");
 }
 ss::Report owner{};session->Snapshot(owner);ag::Report gate{};input->Snapshot(gate);
 check(!owner.active_scopes&&!owner.bridges[0].active&&!owner.bridges[1].active&&!gate.active,"owned callbacks drained");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"saves\":%u,\"native_reads\":%u,\"callback_calls\":%u,\"game_access\":false,\"production_permit\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,binds,nativeReads,calls);
 return failed?1:0;
}
