#include "planning_checkpoint_save.h"
#include "planning_period_base_fixture.inc"
namespace pc=planning_checkpoint_save;namespace pp=planning_period_owner;
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
 auto q=request(1);q.cut=e.cut;check(!session->Submit(q),"ordinary Submit still rejects Ready");
 auto*selectedOwner=session;auto*selectedGate=input;auto*selectedController=&interlock;
 if(mode=="checkpoint-wrong-owner")selectedOwner=new ss::Owner;
 if(mode=="checkpoint-wrong-gate")selectedGate=new ag::Owner;
 planning_input_interlock::Controller foreign;
 if(mode=="checkpoint-wrong-controller")selectedController=&foreign;
 if(mode=="checkpoint-wrong-binding")++e.binding.epoch;
 if(mode=="checkpoint-wrong-serial")++e.periodSerial;
 if(mode=="checkpoint-wrong-observation")++e.observation;
 if(mode=="checkpoint-wrong-ready")++e.readyRevision;
 if(mode=="checkpoint-wrong-gate-revision")++e.gateRevision;
 if(mode=="checkpoint-wrong-cut"){++e.cut;q.cut=e.cut;}
 if(mode=="checkpoint-wrong-period")++q.period;
 if(mode=="checkpoint-wrong-date")q.day=21;
 if(mode=="checkpoint-date-drift")put<unsigned char>(world+0x37,21);
 if(mode=="checkpoint-stale-user")check(rewardDispatch()==0,"another real held User invalidates counter window");
 if(mode=="checkpoint-stale-game")check(gameDispatch()==0,"another real Game invalidates counter window");
 if(mode=="checkpoint-report-pending")reportPending(true,false);
 if(mode=="checkpoint-source-drift"){
  auto&e0=held.owner.hooks.entries[0];DWORD old=0,tmp=0;
  check(VirtualProtect(const_cast<void**>(e0.binding.slot),8,PAGE_READWRITE,&old)!=0,"owned slot writable for source-conflict fixture");
  InterlockedExchangePointer(e0.binding.slot,e0.binding.original);
  check(VirtualProtect(const_cast<void**>(e0.binding.slot),8,old,&tmp)!=0,"owned slot original protection restored");
 }
 bool accepted=false;
 if(mode=="checkpoint-wrong-thread"){std::thread t([&]{accepted=pc::Submit(*session,*input,interlock,e,q);});t.join();}
 else accepted=pc::Submit(*selectedOwner,*selectedGate,*selectedController,e,q);
 const bool normal=mode=="checkpoint-good"||mode=="checkpoint-stop"||mode=="checkpoint-post-report"||mode=="checkpoint-copy-wrong";
 check(accepted==normal,"only current observed exact scope can reserve held Save");
 if(normal){
  ar::Report ready{};ar::Snapshot(*session,ready);ag::Report g{};input->Snapshot(g);
  check(ready.readyFence&&ready.readyRevision==e.readyRevision&&g.requested&&g.revision==e.gateRevision,"admission retains Ready and Gate");
  check(!session->Submit(q)&&!pc::Submit(*session,*input,interlock,e,q),"ordinary and duplicate submit refuse");
  check(!ar::ReadyFence(*session,data.binding,false,2)&&!input->Hold(ic.binding,false,e.gateRevision+1),"both direct release paths refused during reservation");
  check(!interlock.Request(false,2,duplicate),"Controller release cannot open active Save");
  fs::Artifact artifact{};check(!pc::Copy(*session,*input,interlock,e,1,artifact)&&artifact.bytes.empty(),"early copy keeps reservation and returns no bytes");
  check(dispatch(0,user)==0,"existing actual User Save admission and upstream held cut");completeSave();
  ar::Snapshot(*session,ready);input->Snapshot(g);
  check(ready.readyFence&&g.requested&&g.revision==e.gateRevision,"native Save completion did not release Ready or Gate");
  check(!ar::ReadyFence(*session,data.binding,false,2)&&!input->Hold(ic.binding,false,e.gateRevision+1),"completed but un-copied reservation still refuses release");
  pp::Receipt receipt{};check(!pp::Retire(*session,*input,interlock,data.binding,receipt),"cannot retire outstanding copy reservation");
  check(!session->CopyArtifact(1,artifact),"ordinary Copy cannot bypass reserved metadata");
  if(mode=="checkpoint-stop")session->Stop();
  if(mode=="checkpoint-post-report")reportPending(true,false);
  if(mode=="checkpoint-copy-wrong"){
   auto wrong=e;++wrong.cut;check(!pc::Copy(*session,*input,interlock,wrong,1,artifact)&&artifact.bytes.empty(),"wrong Copy scope cannot consume reservation");
   check(!pc::Copy(*session,*input,foreign,e,1,artifact)&&!pc::Copy(*session,*input,interlock,e,2,artifact),"wrong Controller/generation Copy refused");
  }
  const bool copied=pc::Copy(*session,*input,interlock,e,1,artifact);
  check(copied==(mode=="checkpoint-good"||mode=="checkpoint-copy-wrong"),"original Copy/report/stop checks retained");
  if(copied){
   check(!artifact.bytes.empty()&&artifact.request.cut==e.cut&&artifact.request.period==e.binding.period&&artifact.report.file_bytes_verified,"real original Driver native readback artifact");
   ar::Snapshot(*session,ready);input->Snapshot(g);check(ready.readyFence&&g.requested&&g.revision==e.gateRevision,"Copy releases reservation only");
   check(!pc::Copy(*session,*input,interlock,e,1,artifact)&&artifact.bytes.empty(),"copied reservation consumed once");
   check(!pc::Submit(*session,*input,interlock,e,q),"old observation cannot issue second Save");
   check(interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"new actual post-Save observation");
   check(interlock.Request(false,2,duplicate),"explicit fresh Controller release works after copied reservation");
  }
 }
 ss::Report owner{};session->Snapshot(owner);ar::Report reward{};ar::Snapshot(*session,reward);ag::Report gate{};input->Snapshot(gate);
 check(!owner.active_scopes&&!owner.bridges[0].active&&!owner.bridges[1].active&&!gate.active,"all owned scopes drained");
 check(!owner.all_input_held&&!owner.room_ready&&!gate.saveAuthorized&&!gate.fullInputHold,"no full-input or production permit");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"saves\":%u,\"native_reads\":%u,\"ready_revision\":%llu,\"gate_revision\":%llu,\"game_access\":false,\"production_permit\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,binds,nativeReads,reward.readyRevision,gate.revision);
 return failed?1:0;
}
