namespace a_save_upstream_gate {
bool Owner::Impl::simulation(void*v,const planning_simulation_boundary::detail::Call&call)noexcept {
 namespace pc=planning_checkpoint_save;auto&s=*static_cast<Impl*>(v);const auto&c=call.checkpoint;const auto&e=c.evidence;bool ok=false;
 AcquireSRWLockExclusive(&s.lock);
 __try {__try {
  if(!s.initialized||!s.armed||read(s.stopped)||s.r.error!=Error::None||!s.requested||s.r.active||s.gameCall||s.checkpointReserved||
   c.owner!=s.c.saveOwner||!same(e.binding.native,s.c.binding)||!e.gateRevision||e.gateRevision!=s.r.revision||!s.source()||
   at<uintptr_t>(s.c.base+0x1FCA1E0)!=s.c.root||at<uintptr_t>(s.c.root+0x85130)!=s.c.world)__leave;
  CheckpointLoadWorkerBridgeStats b[3]{};for(unsigned i=0;i<3;++i)if(!ASaveActionBridgeSnapshot(i,&b[i])||b[i].active)__leave;
  if(call.begin){
   if(!s.observed||!c.observed.gate.coveredGlobalUiHeld||!c.observed.gate.coveredPanelHeld||
    c.observed.gate.gameCalls!=s.r.gameCalls||c.observed.gate.uiSuppressed!=s.r.uiSuppressed||
    c.observed.gate.panelSuppressed!=s.r.panelSuppressed||c.observed.gate.uiForwarded!=s.r.uiForwarded||
    c.observed.gate.panelForwarded!=s.r.panelForwarded)__leave;
   for(unsigned i=0;i<3;++i)if(!pc::detail::SameStats(b[i],c.observed.gate.bridges[i]))__leave;
  }else{
   const auto&old=c.observed.gate;
   if(!s.observed||b[0].native_started<=old.bridges[0].native_started||b[0].native_returned<=old.bridges[0].native_returned||
    b[0].finally_calls<=old.bridges[0].finally_calls||s.r.uiSuppressed<=old.uiSuppressed||s.r.panelSuppressed<=old.panelSuppressed||
    s.r.uiForwarded!=old.uiForwarded||s.r.panelForwarded!=old.panelForwarded)__leave;
   for(unsigned i=0;i<3;++i)if(b[i].abnormal_exits!=old.bridges[i].abnormal_exits||b[i].cleanup_faults!=old.bridges[i].cleanup_faults)__leave;
  }
  if(!planning_simulation_boundary::detail::InvokeOwner(call))__leave;
  if(read(s.stopped)||!s.source()){s.fail(Error::Source);__leave;}ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.fail(Error::Exception);}}
 __finally{ReleaseSRWLockExclusive(&s.lock);}return ok;
}
}
