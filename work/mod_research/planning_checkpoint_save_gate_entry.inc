namespace a_save_upstream_gate {
bool Owner::Impl::checkpoint(void*v,const planning_checkpoint_save::detail::Call&call)noexcept {
 namespace pc=planning_checkpoint_save;auto&s=*static_cast<Impl*>(v);bool ok=false;
 AcquireSRWLockExclusive(&s.lock);
 __try {__try {
  const auto&e=call.evidence;
  if(!s.initialized||!s.armed||read(s.stopped)||s.r.error!=Error::None||!s.requested||s.r.active||s.gameCall||
     call.owner!=s.c.saveOwner||!same(e.binding.native,s.c.binding)||!e.gateRevision||e.gateRevision!=s.r.revision||!s.source()||
     at<uintptr_t>(s.c.base+0x1FCA1E0)!=s.c.root||at<uintptr_t>(s.c.root+0x85130)!=s.c.world)__leave;
  CheckpointLoadWorkerBridgeStats bridges[3]{};
  for(unsigned i=0;i<3;++i)if(!ASaveActionBridgeSnapshot(i,&bridges[i])||bridges[i].active)__leave;
  // __leave above exits this guarded block even inside the loop.
  checkpoint_load_hook_set::Report hooks{};s.hooks.Snapshot(hooks);
  if(!hooks.initialized||hooks.count!=2||hooks.exceptionCode)__leave;
  for(unsigned i=0;i<2;++i){const auto&h=hooks.entries[i];
   if(!h.known||!h.published||h.error||!h.binding.slot||*h.binding.slot!=h.binding.hook)__leave;}
  if(call.action==pc::detail::Action::Submit){
   if(s.checkpointReserved||!s.observed||!call.observed.gate.coveredGlobalUiHeld||!call.observed.gate.coveredPanelHeld||
      call.observed.gate.gameCalls!=s.r.gameCalls||call.observed.gate.uiSuppressed!=s.r.uiSuppressed||
      call.observed.gate.uiForwarded!=s.r.uiForwarded||call.observed.gate.panelSuppressed!=s.r.panelSuppressed||
      call.observed.gate.panelForwarded!=s.r.panelForwarded||call.observed.gate.userTailSuppressed!=s.r.userTailSuppressed||
      call.observed.gate.userTailForwarded!=s.r.userTailForwarded)__leave;
   for(unsigned i=0;i<3;++i)if(!pc::detail::SameStats(bridges[i],call.observed.gate.bridges[i]))__leave;
   // Gate -> Owner is the established tail callback order. Owner's submission
   // checks never acquire Gate/Controller, and the storage callbacks prohibit
   // reentrant owner calls. No inverse Owner -> Gate acquisition is introduced.
   if(!pc::detail::InvokeOwner(call))__leave;
   s.checkpointReserved=true;s.checkpointEvidence=e;s.checkpointController=call.controller;s.checkpointGeneration=call.generation;
  }else{
   if(!s.checkpointReserved||s.checkpointController!=call.controller||s.checkpointGeneration!=call.generation||
      !pc::detail::Same(s.checkpointEvidence,e))__leave;
   if(!pc::detail::InvokeOwner(call))__leave;
   s.checkpointReserved=false;
  }
  if(read(s.stopped)||!s.source()){
   // A source/Stop race after Driver acceptance is terminal; do not open Gate
   // or allow replay. The accepted Owner is explicitly stopped as well.
   s.checkpointReserved=true;s.fail(Error::Source);__leave;
  }
  ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){s.checkpointReserved=true;s.fail(Error::Exception);}}
 __finally{ReleaseSRWLockExclusive(&s.lock);}return ok;
}
}
