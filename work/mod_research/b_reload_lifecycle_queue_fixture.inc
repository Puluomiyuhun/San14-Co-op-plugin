// Composition-only fixture. Frozen lifecycle and queue implementations are linked
// unchanged. The archive's four-worker initializer runs once; the same owned
// worker then handles both complete queue generations. Engine/file effects and
// the constructor's explicit initial-wait coordination remain test substitutes.
static unsigned lifecycleQueueWarmGeneration=UINT_MAX;
static void lifecycleQueuePrepare(){
 lifecyclePrepare();
 // The startup constructor double has finished its four pool controls. The
 // complete queue also calls this shared constructor for embedded Load/Title
 // workers; restore that fixture service instead of misclassifying them as
 // additional pool threads. No archived caller or production check is changed.
 parentJump(0x833CB0,uintptr_t(&nativeCtorDouble));
 // prepareNativeMachine refreshes fixture services for a new world. Retain the
 // actual initialized pool, entry source, IAT owner and worker identities.
 put<uintptr_t>(base+0x12F2440,uintptr_t(&activatedCopy));
 put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);
 put<uintptr_t>(base+0x12F2440+0x20,uintptr_t(&parentNoop));
 parentJump(0x160F0,uintptr_t(&activatedSwap));
 put<uintptr_t>(base+0x123C1D8,uintptr_t(&activatedSet));
 put<uintptr_t>(base+0x123C1E0,uintptr_t(&lifecycleWait));
 aq::Report r{};life::Report s{};life::Snapshot(s);
 boundRequire(aq::Snapshot(r)&&r.error==aq::Error::None&&!r.uncertain&&
  r.threads==4&&r.initialWaitVerified==4&&at<uintptr_t>(r.iatSlot)==r.replacement,
  "same cold-published four-worker owner survives queue world changes");
 boundRequire(s.error==life::Error::None&&s.entered==1&&s.returned==1&&s.finally==1&&
  !s.abnormal&&s.coldPools==1&&!memcmp(reinterpret_cast<void*>(s.plan.address),s.plan.after,5),
  "startup initializer executes once and its exact source remains owned");
 for(unsigned i=0;i<4;++i){const auto&t=lifecycleTask(i);
  boundRequire(t.worker==base+0x1A24DA0+8+uintptr_t(i)*0x80&&
   at<uintptr_t>(t.worker+8)==t.object&&at<DWORD>(t.object+0x10)==t.workerTid&&
   at<uintptr_t>(t.object+0x38)==uintptr_t(&BReloadRootActivationBridge1),
   "new world cannot reset persistent native pool controls");
 }
 if(lifecycleQueueWarmGeneration!=generationIndex){
  lifecycleQueueWarmGeneration=generationIndex;
  const auto prior=lifecycleWarmBodies;lifecycleWarmup();
  boundRequire(lifecycleWarmBodies==prior+1,"one unticketed ordinary task in each generation");
 }
}
static void lifecycleQueueFinish(){
 boundRequire(activatedQueue.tasks==16,"two complete queue generations use sixteen actual Root tasks");
 lifecycleStopWorkers();
 aq::Report r{};life::Report s{};aq::Snapshot(r);life::Snapshot(s);
 check(r.error==aq::Error::None&&!r.uncertain&&r.threads==4&&r.taskCount==16&&
  r.gateEntries==16&&r.gateFinishes==16&&r.initialWaitVerified==4&&
  r.outerBefore==4&&r.outerFinally==4,"four retained workers drain with sixteen exact task receipts");
 check(s.error==life::Error::None&&s.entered==1&&s.returned==1&&s.finally==1&&
  s.coldPools==1&&s.unownedTasks==2&&lifecycleWarmBodies==2,
  "single native startup and transparent ordinary work across both generations");
 unsigned yields=0;for(unsigned i=0;i<16;++i){const auto&t=r.tasks[i];
  check(t.ports.captured==3&&t.ports.restored&&!t.ports.uncertain&&t.finished&&!t.abnormal&&
   t.binding.generation==(i<8?2u:3u)&&t.thread==activatedQueue.tid,
   "retained task receipt pins original generation and same warmed worker");
  yields+=t.ports.yields;
 }
 check(yields==(providerCase==L"nested-input-yield"?2u:0u),"one real nested yield per generation in selected scenario");
 printf("{\"startup_and_full_queue_composed\":true,\"initializer_calls\":%u,\"registered_workers\":%u,\"ordinary_tasks\":%u,\"root_tasks\":%u,\"root_captures\":%u,\"root_yields\":%u,\"outer_finally\":%u,\"same_task_worker\":true,\"real_game_reload\":false}\n",
  s.entered,r.threads,s.unownedTasks,r.taskCount,nestedCaptures,yields,r.outerFinally);
 for(unsigned i=0;i<4;++i){auto&t=lifecycleTask(i);CloseHandle(lifecycleThreads[i]);
  CloseHandle(lifecycleInitial[i]);CloseHandle(t.ready);CloseHandle(t.done);}
 life::Stop();
}
