namespace a_save_user_owner {
bool Owner::Impl::checkpoint(void*v,const planning_checkpoint_save::detail::Call&call)noexcept {
 namespace pc=planning_checkpoint_save;namespace pp=planning_period_owner;
 auto&s=*static_cast<Impl*>(v);auto&l=ar::lane;bool ok=false;
 AcquireSRWLockExclusive(&s.control);
 __try {__try {
  const auto&e=call.evidence;pp::Date now{};
  if(call.owner!=l.owner||!value(&s.initialized)||!value(&s.armed)||value(&s.error)||value(&s.stopped)||
     !ar::healthy()||l.periodRetired||!l.report.bound||!ar::binding(e.binding,l.config.binding)||
     (planning_simulation_boundary::detail::Held()&&!pp::periods.checkpointPhase)||!pp::periods.tracked||pp::periods.controller!=call.controller||GetCurrentThreadId()!=pp::periods.thread||
     e.periodSerial!=pp::periods.serial||!pp::readDate(now)||!pp::sameDate(now,pp::periods.date)||!pp::sameDate(now,e.date)||
     !l.report.readyFence||l.report.readyRevision!=e.readyRevision||l.report.active||l.report.queued||l.report.uncertain||l.running||
     l.report.submitted!=l.report.completed||e.cut!=l.report.completed||s.hold||s.activeScopes)__leave;
  CheckpointLoadWorkerBridgeStats bridges[2]{};
  for(unsigned i=0;i<2;++i)if(!ASaveUserOwnerBridgeSnapshot(i,&bridges[i])||bridges[i].active)__leave;
  if(call.action==pc::detail::Action::Submit){
   const auto&q=call.request;const auto&observed=call.observed;
   if(s.checkpointActive||s.saveLane||!e.observation||
      (s.checkpointConsumedSerial==e.periodSerial&&e.observation<=s.checkpointConsumedObservation)||
      observed.reward.submitted!=l.report.submitted||observed.reward.completed!=l.report.completed||
      observed.reward.readyRevision!=l.report.readyRevision||!observed.reward.readyFence||
      observed.owner.held_scopes!=s.heldScopes||q.period!=e.binding.period||q.cut!=e.cut||
      q.year!=e.date.year||q.month!=e.date.month||q.day!=e.date.day||q.force!=e.date.viewer||
      q.generation!=call.generation||!pp::fresh(l.config))__leave;
   for(unsigned i=0;i<2;++i)if(!pc::detail::SameStats(bridges[i],observed.owner.bridges[i]))__leave;
   // The remaining checks are the original Submit report/source/storage lane.
   // Only this explicit path permits readyFence; ordinary Submit is unchanged.
   if(rp::read(rp::state.revoked)){s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();__leave;}
   if(q.room_epoch!=s.config.room_epoch||std::memcmp(q.room_id,s.config.room_id,32))__leave;
   const auto reportCursor=*reinterpret_cast<const unsigned short*>(rp::state.world+0x165A);
   if(!rp::observe(rp::Boundary::Submit,false)){InterlockedIncrement64(&rp::state.submitRejected);__leave;}
   if(!s.slots()||!s.gate.Valid()){s.fail(Error::Storage);s.driver.Stop();__leave;}
   if(reportCursor!=*reinterpret_cast<const unsigned short*>(rp::state.world+0x165A)){
    InterlockedIncrement64(&rp::state.submitRejected);rp::record(rp::Boundary::Submit,a_save_early_guard::Decision::Drift,false);__leave;
   }
   if(!value(&s.stopped)&&s.driver.Submit(q)){
    rp::state.cursor=reportCursor;rp::state.generation=q.generation;InterlockedExchange(&rp::state.pinned,1);s.saveLane=true;
    s.checkpointActive=true;s.checkpointEvidence=e;s.checkpointController=call.controller;s.checkpointGate=call.gate;
    s.checkpointGeneration=q.generation;s.checkpointConsumedSerial=e.periodSerial;s.checkpointConsumedObservation=e.observation;ok=true;
   }
  }else{
   if(!s.checkpointActive||s.checkpointController!=call.controller||s.checkpointGate!=call.gate||
      s.checkpointGeneration!=call.generation||!pc::detail::Same(s.checkpointEvidence,e)||!call.artifact||
      !rp::read(rp::state.ready)||rp::state.owner!=call.owner)__leave;
   const auto generation=call.generation;
   if(!generation||generation!=rp::state.generation){InterlockedIncrement64(&rp::state.copyRejected);rp::record(rp::Boundary::Copy,a_save_early_guard::Decision::Binding,false);__leave;}
   const auto saved=s.driver.Snapshot();if(saved.generation!=generation||saved.status!=fs::Status::Complete)__leave;
   if(rp::read(rp::state.revoked)||!rp::observe(rp::Boundary::Copy,true)||!rp::fields()){
    rp::record(rp::Boundary::Copy,a_save_early_guard::Decision::Drift,true);InterlockedIncrement64(&rp::state.copyRejected);
    s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();__leave;
   }
   if(!value(&s.error)&&!value(&s.stopped)&&s.driver.CopyArtifact(generation,*call.artifact)){
    s.checkpointActive=false;if(pp::periods.checkpointPhase)pp::periods.checkpointCopied=true;ok=true;
   }
  }
 }__except(EXCEPTION_EXECUTE_HANDLER){
  InterlockedIncrement64(&rp::state.submitRejected);rp::record(rp::Boundary::Submit,a_save_early_guard::Decision::Unreadable,true);
  s.fail(Error::Input);InterlockedExchange(&s.stopped,1);s.driver.Stop();
 }}__finally{ReleaseSRWLockExclusive(&s.control);}return ok;
}
}
