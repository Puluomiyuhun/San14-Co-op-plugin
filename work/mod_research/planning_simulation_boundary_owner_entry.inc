namespace a_save_user_owner {
bool Owner::Impl::simulation(void*v,const planning_simulation_boundary::detail::Call&call)noexcept {
 namespace pc=planning_checkpoint_save;namespace pp=planning_period_owner;
 auto&s=*static_cast<Impl*>(v);auto&l=ar::lane;const auto&c=call.checkpoint;const auto&e=c.evidence;bool ok=false;
 AcquireSRWLockExclusive(&s.control);
 __try {__try {pp::Date now{};
  if(c.owner!=l.owner||!value(&s.initialized)||!value(&s.armed)||value(&s.error)||value(&s.stopped)||
   !pp::quiet()||l.periodRetired||!l.report.bound||!ar::binding(e.binding,l.config.binding)||
   !pp::periods.tracked||pp::periods.controller!=c.controller||GetCurrentThreadId()!=pp::periods.thread||
   e.periodSerial!=pp::periods.serial||!pp::readDate(now)||!pp::sameDate(pp::periods.date,e.date)||
   !l.report.readyFence||l.report.readyRevision!=e.readyRevision||e.cut!=l.report.completed||
   !pp::fresh(l.config)||!s.slots()||!s.gate.Valid()||rp::read(rp::state.revoked)||
   !rp::observe(rp::Boundary::Submit,false))__leave;
  CheckpointLoadWorkerBridgeStats b[2]{};
  for(unsigned i=0;i<2;++i)if(!ASaveUserOwnerBridgeSnapshot(i,&b[i])||b[i].active)__leave;
  if(call.begin){
   if(pp::periods.checkpointPhase||!pp::sameDate(now,e.date)||c.observed.reward.completed!=e.cut||
      c.observed.reward.submitted!=l.report.submitted||c.observed.owner.held_scopes!=s.heldScopes)__leave;
   for(unsigned i=0;i<2;++i)if(!pc::detail::SameStats(b[i],c.observed.owner.bridges[i]))__leave;
   pp::periods.startDate=e.date;
  }else{
   if(pp::periods.checkpointPhase||!pp::nextDate(e.date,now)||
      b[0].native_started!=c.observed.owner.bridges[0].native_started||
      b[0].native_returned!=c.observed.owner.bridges[0].native_returned||
      b[0].finally_calls<=c.observed.owner.bridges[0].finally_calls||
      s.heldScopes<=c.observed.owner.held_scopes)__leave;
   for(unsigned i=0;i<2;++i)if(b[i].abnormal_exits!=c.observed.owner.bridges[i].abnormal_exits||
     b[i].cleanup_faults!=c.observed.owner.bridges[i].cleanup_faults)__leave;
   if(!pc::detail::SameStats(b[1],c.observed.owner.bridges[1]))__leave;
   pp::periods.date=now;pp::periods.checkpointPhase=true;pp::periods.checkpointCopied=false;
  }ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Input);}}
 __finally{ReleaseSRWLockExclusive(&s.control);}return ok;
}
}
