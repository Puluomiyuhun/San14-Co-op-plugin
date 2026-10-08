// Explicit fixture writes below simulate the next planning date. They are NOT
// execution of the real battle/date engine or a full-world checkpoint load.
 const bool saves=mode=="period-two-saves";fs::Artifact first{},second{};
 auto command=data.command(2,1);check(ar::Submit(*session,data.binding,1,command)&&rewardDispatch()==0,"period one actual reward replay");
 if(saves){check(session->Submit(request(1))&&dispatch(0,user)==0,"period one actual diagnostic Save admission");completeSave();check(session->CopyArtifact(1,first)&&!first.bytes.empty(),"first native readback bytes");}
 planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;
 check(interlock.Initialize(pc),"first Controller claims physical Owner period");
 pp::Receipt receipt{};
 if(mode=="period-duplicate-controller"){
  planning_input_interlock::Controller duplicate;check(!duplicate.Initialize(pc),"new object cannot reset Controller within same logical period");
 }else{
  bool duplicate=false;check(interlock.Request(true,1,duplicate)&&!duplicate,"first period Ready hold");
  if(mode=="period-no-observation")check(!pp::Retire(*session,*input,interlock,data.binding,receipt),"setter alone cannot retire period");
  else {
   check(interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"actual Game/User observation before retirement");
   if(mode=="period-cross-thread-snapshot"){
    planning_input_interlock::Report copy{};std::thread reader([&]{interlock.Snapshot(copy);});reader.join();
    check(copy.observed&&copy.coverage==7&&copy.revision==1,"retained window thread can read valid Controller without mutating its period");
   }else if(mode=="period-wrong-thread"){
    bool retired=true;std::thread other([&]{pp::Receipt copy{};retired=pp::Retire(*session,*input,interlock,data.binding,copy);});other.join();
    check(!retired,"foreign thread cannot retire native period");
   }else {
    const auto oldBinding=data.binding;check(pp::Retire(*session,*input,interlock,oldBinding,receipt),"old logical period retired under same Owner lock");
    check(receipt.serial==1&&receipt.reward.submitted==1&&receipt.reward.completed==1&&receipt.reward.readyRevision==1,"frozen receipt retains cumulative counters");
    pp::Receipt repeated{};check(!pp::Retire(*session,*input,interlock,oldBinding,repeated),"retirement is one-shot");
    check(!ar::Submit(*session,oldBinding,2,command)&&!ar::ReadyFence(*session,oldBinding,false,2)&&!ar::Bind(*session,rc)&&!session->Submit(request(2)),"retired legacy APIs cannot reopen admission");
    ag::Report beforeOld{},afterOld{};input->Snapshot(beforeOld);bool oldDuplicate=false;
    check(!interlock.Request(false,2,oldDuplicate)&&!interlock.Request(true,2,oldDuplicate)&&!interlock.BeginObservation(1),"retired Controller cannot mutate Gate before reward refuses");
    input->Snapshot(afterOld);check(beforeOld.requested&&afterOld.requested&&beforeOld.revision==afterOld.revision,"retired Controller rejection leaves Gate held and revision unchanged");
    if(mode!="period-retired-admission"){
     ++data.binding.period;++data.binding.epoch;++data.binding.room_input_digest[0];ar::Config next=rc;next.binding=data.binding;
     if(mode!="period-same-date")put<unsigned char>(world+0x37,mode=="period-skip-date"?1:21);
     if(mode=="period-wrong-world")put<uintptr_t>(root+0x85130,world+0x2000);
     if(mode=="period-wrong-binding")++next.binding.native.owner_generation;
     if(mode=="period-bad-sampler")next.sample=nullptr;
     const bool rebound=pp::Rebind(*session,*input,next,mode=="period-stale-serial"?2:1);
     const bool success=mode=="period-two-saves"||mode=="period-two-rewards";
     check(rebound==success,"only exact next period/source/date/serial can rebind");
     if(success){
      pp::Report current{};check(pp::Snapshot(*session,current)&&!current.retired&&current.serial==2&&current.reward.submitted==1&&current.reward.readyRevision==1&&current.reward.readyFence,"logical rebind retains sequence and closed fence");
      check(!ar::ReadyFence(*session,oldBinding,false,2)&&!ar::Submit(*session,oldBinding,2,command),"old period requests stale after rebind");
      planning_input_interlock::Report stale{};interlock.Snapshot(stale);check(!stale.observed&&!interlock.BeginObservation(1),"old date Controller cannot observe new period");
      check(ar::ReadyFence(*session,data.binding,false,2),"explicit new-period local release preserves gate hold for diagnostic Save");
      command=data.command(12,2);check(!ar::Submit(*session,data.binding,1,command)&&ar::Submit(*session,data.binding,2,command)&&rewardDispatch()==0,"second period continues global command sequence");
      if(saves){check(session->Submit(request(2))&&dispatch(0,user)==0,"same physical Owner second diagnostic Save admission");completeSave();check(session->CopyArtifact(2,second)&&!second.bytes.empty()&&first.bytes!=second.bytes,"two independent native storage readbacks across dates");}
      planning_input_interlock::Controller nextController;pc.binding=data.binding;check(nextController.Initialize(pc),"next period claims new Controller without resetting physical Owner");
      bool dup=false;check(nextController.Request(true,3,dup)&&nextController.BeginObservation(3)&&gameDispatch()==0&&rewardDispatch()==0&&nextController.EndObservation(3),"new Controller resumes cumulative Ready revision with actual callbacks");
      pp::Receipt nextReceipt{};check(pp::Retire(*session,*input,nextController,data.binding,nextReceipt)&&nextReceipt.serial==2&&nextReceipt.reward.submitted==2&&nextReceipt.reward.readyRevision==3,"second retirement retains next receipt");
      pp::Receipt historical{};check(pp::Historical(*session,1,historical)&&std::memcmp(&historical,&receipt,sizeof receipt)==0,"first receipt unchanged after second-period business and Save");
      check(data.bodies==2&&data.ctors==2&&data.dtors==2,"two actual owned reward containers completed");
      if(saves)check(binds==2&&queues==2&&nativeReads==4,"two full diagnostic Save/readback generations on same bridge bank");
     }else{pp::Report current{};check(pp::Snapshot(*session,current)&&current.retired&&current.serial==1&&current.reward.readyRevision==1,"failed rebind retains old closed period");}
    }
   }
  }
 }
 pp::Report final{};check(pp::Snapshot(*session,final),"final logical snapshot");
 check(!final.fullInputHeld&&!final.saveAuthorized&&!final.simulationPermit&&!final.worldReplacement,"lifecycle never promotes full boundary or world-load permission");
 ss::Report native{};session->Snapshot(native);check(!native.active_scopes&&!native.bridges[0].active&&!native.bridges[1].active&&data.nodes.empty(),"real callbacks and deep lists drained");
 printf("{\"result\":\"%s\",\"case\":\"%s\",\"checks\":%u,\"failures\":%u,\"period_serial\":%llu,\"retired_periods\":%llu,\"command_sequence\":%llu,\"ready_revision\":%llu,\"reward_calls\":%u,\"saves\":%u,\"native_reads\":%u,\"same_world_only\":true,\"fixture_date_transition\":true,\"game_access\":false,\"production_permit\":false}\n",failed?"FAIL":"PASS",mode.c_str(),passed,failed,final.serial,final.retiredCount,final.reward.submitted,final.reward.readyRevision,data.bodies,binds,nativeReads);
 return failed?1:0;
