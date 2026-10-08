 namespace ps=planning_period_session;
 check(data.binding.room_input_digest==SessionDigests[0],"Python and C++ scope digest agree including full 128-bit epochs");
 planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;
 check(interlock.Initialize(pc),"actual native Controller before local session mapping");
 auto*host=new ps::Session;
 auto firstScope=scope;
 if(mode=="session-init-drift"){
  ++scope.timelineEpoch[15];check(!host->Initialize(*session,*input,interlock,scope,rc,b,root,world),"late epoch byte drift rejected");
 }else{
  check(host->Initialize(*session,*input,interlock,scope,rc,b,root,world),"trusted local scope adopts actual native period");
  auto*other=new ps::Session;check(!other->Initialize(*session,*input,interlock,scope,rc,b,root,world),"second Session cannot remap physical bank");
  auto command=data.command(2,1);auto staleScope=scope;++staleScope.timelineEpoch[15];
  check(!host->Submit(staleScope,1,command)&&!host->Submit(scope,0,command)&&!host->Submit(scope,2,command),"wrong epoch zero and gap never dispatch");
  check(host->Submit(scope,1,command)&&rewardDispatch()==0,"first network global sequence executes once through same Owner");
  check(!host->Submit(scope,1,command),"old sequence cannot replay");
  bool duplicate=false;check(interlock.Request(true,1,duplicate),"first hold setter");
  pp::Receipt receipt{};
  if(mode=="session-no-observation")check(!host->Retire(scope,receipt),"scope mapping cannot authorize unobserved retirement");
  else{
   check(interlock.BeginObservation(1)&&gameDispatch()==0&&rewardDispatch()==0&&interlock.EndObservation(1),"real Game/User observation");
   ps::Next next{};auto desired=SessionScopes[1];
   if(mode=="session-not-retired")check(!host->PlanNext(desired,next),"no transition plan before actual retirement");
   check(host->Retire(scope,receipt)&&receipt.reward.completed==1,"native retirement frozen with network scope");
   check(!host->Retire(scope,receipt)&&!host->Submit(scope,2,command),"retired scope cannot repeat retirement or submit");
   ps::Scope historicalScope{};pp::Receipt historical{};check(host->Historical(1,historicalScope,historical),"first scope and native receipt retained");
   if(mode=="session-room-drift")++desired.room[15];
   if(mode=="session-binding-drift")++desired.bindingEpoch[15];
   if(mode=="session-old-epoch")desired.timelineEpoch=scope.timelineEpoch;
   if(mode=="session-cut-reset")desired.baseSequence=0;
   if(mode=="session-skip-period")++desired.period;
   if(mode=="session-skip-date")desired.date.day=1;
   if(mode=="session-viewer")desired.date.viewer=2;
   const bool invalid=mode=="session-room-drift"||mode=="session-binding-drift"||mode=="session-old-epoch"||mode=="session-cut-reset"||mode=="session-skip-period"||mode=="session-skip-date"||mode=="session-viewer";
   const bool planned=host->PlanNext(desired,next);check(planned!=invalid,"only exact next authenticated logical scope produces mapping");
   if(planned){
    check(next.binding.room_input_digest==SessionDigests[1]&&next.binding.epoch==2&&next.scope.baseSequence==1,"next random epoch maps to local ordinal with preserved cut");
    auto nextConfig=rc;nextConfig.binding=next.binding;
    if(mode=="session-plan-tamper")++next.binding.native.owner_generation;
    if(mode=="session-serial-tamper")++next.retiredSerial;
    if(mode=="session-sampler-drift")nextConfig.context=host;
    // Explicit fixture-only date/sampler mutation. No native time engine runs.
    if(mode!="session-wrong-date")put<unsigned char>(world+0x37,21);
    data.binding=nextConfig.binding;
    if(mode=="session-world-drift")put<uintptr_t>(root+0x85130,world+0x2000);
    bool rebound=false;if(mode=="session-wrong-thread"){std::thread t([&]{rebound=host->Rebind(next,nextConfig);});t.join();}
    else rebound=host->Rebind(next,nextConfig);
    const bool reject=mode=="session-plan-tamper"||mode=="session-serial-tamper"||mode=="session-sampler-drift"||mode=="session-wrong-thread"||mode=="session-wrong-date"||mode=="session-world-drift";
    check(rebound!=reject,"formal native rebind requires unaltered mapping and actual date/world/thread");
    if(rebound){
     command=data.command(12,2);check(!host->Submit(desired,2,command),"new period remains blocked pending real Controller adoption");
     check(!host->Adopt(interlock),"old Controller cannot attach to next logical scope");
     auto*nextController=new planning_input_interlock::Controller;pc.binding=nextConfig.binding;
     check(nextController->Initialize(pc)&&host->Adopt(*nextController),"new actual Controller adopts retained physical bank");
     check(!host->Adopt(*nextController)&&!host->Submit(firstScope,2,command),"duplicate adoption and prior network epoch rejected");
     check(nextController->Request(false,2,duplicate),"new period explicit release; mapper never implicitly releases");
     check(!host->Submit(desired,1,command)&&!host->Submit(desired,3,command),"second period cannot reset or skip global command sequence");
     check(host->Submit(desired,2,command)&&rewardDispatch()==0,"second period global sequence two executes via retained Owner");
     check(nextController->Request(true,3,duplicate)&&nextController->BeginObservation(3)&&gameDispatch()==0&&rewardDispatch()==0&&nextController->EndObservation(3),"next real boundary observed");
     pp::Receipt finalReceipt{};check(host->Retire(desired,finalReceipt)&&finalReceipt.reward.completed==2&&finalReceipt.serial==2,"two physical executions and two logical retirements");
     ps::Scope copy{};pp::Receipt old{};check(host->Historical(1,copy,old)&&old.serial==historical.serial&&old.reward.completed==1&&copy.timelineEpoch==historicalScope.timelineEpoch,"old history unchanged");
     check(data.bodies==2&&data.ctors==2&&data.dtors==2&&data.nodes.empty(),"two actual native container lifecycles complete");
    }else{ps::Report r{};host->Snapshot(r);check(r.retired&&r.historyCount==1&&r.binding.epoch==1,"failed transition leaves old period closed");}
   }
  }
 }
 ps::Report r{};host->Snapshot(r);check(!r.fullInputHeld&&!r.saveAuthorized&&!r.simulationPermit&&!r.worldReplacement,"scope mapping grants no gameplay permissions");
 ss::Report own{};session->Snapshot(own);check(!own.active_scopes&&!own.bridges[0].active&&!own.bridges[1].active&&data.nodes.empty(),"owned native scopes drained");
 printf("{\"result\":\"%s\",\"case\":\"%s\",\"checks\":%u,\"failures\":%u,\"reward_calls\":%u,\"history\":%llu,\"local_epoch\":%llu,\"game_access\":false,\"actual_simulation\":false,\"production_permit\":false}\n",failed?"FAIL":"PASS",mode.c_str(),passed,failed,data.bodies,r.historyCount,r.binding.epoch);
 return failed?1:0;
