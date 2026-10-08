#undef session
// Executed only after real generation work and inherited old-report comparisons.
static void lifecycleFaultAfterGeneration(){
 if(!lifecycleFaultTarget()){
  if(!generationIndex){lifecycleAdvance=new lfg::Gate;check(lifecycleAdvance->Initialize(provider,2,*currentSession,admissionBundle->controller),"trusted local next-generation gate bound to actual reports");}
  else {lfg::Report g{};lifecycleAdvance->Snapshot(g);check(g.opened&&g.registerCalls==1&&g.openCalls==1,"healthy prior generation permits one actual next registration and open");}
  return;
 }
 auto*gate=new lfg::Gate;boundRequire(gate->Initialize(provider,generationIndex+2,*currentSession,admissionBundle->controller),"fault gate binds actual failed sources");
 tp::Report before{},after{},absent{};provider.Snapshot(generationIndex+2,before);ns::Report sb{},sa{};currentSession->Snapshot(sb);
 auto next=lifecycleFaultConfig;next.generation.callbacks.id= generationIndex+3;++next.generation.attempt;++next.generation.epoch;next.session=new ns::Session;
 check(!gate->RegisterAndOpen(next)&&!gate->RegisterAndOpen(next),"actual failed input blocks both first advance and retry");
 lfg::Report g{};gate->Snapshot(g);check(g.error==lfg::Error::Input&&g.finished&&g.attempts==1&&!g.registerCalls&&!g.openCalls&&!g.registered&&!g.opened&&!g.schedulerFence&&!g.roomReady&&!g.fullWorld,"failed gate performs no Provider Register or OpenWindow and no permit");
 check(!provider.Snapshot(generationIndex+3,absent),"next immutable generation genuinely does not exist");provider.Snapshot(generationIndex+2,after);currentSession->Snapshot(sa);check(!memcmp(&before,&after,sizeof before)&&!memcmp(&sb,&sa,sizeof sb),"refusal leaves failed generation's actual source and session history unchanged");
 if(generationIndex){lfg::Report previous{};lifecycleAdvance->Snapshot(previous);check(previous.opened&&previous.registerCalls==1&&previous.openCalls==1,"second-generation fault followed a healthy gated first completion");}
 lifecycleStopWorkers();aq::Report r{};life::Report s{};aq::Snapshot(r);life::Snapshot(s);const unsigned expected=generationIndex?9u:1u;
 check(r.error==aq::Error::None&&!r.uncertain&&r.threads==4&&r.taskCount==expected&&r.gateEntries==expected&&r.gateFinishes==expected&&r.outerBefore==4&&r.outerFinally==4,"four native workers drain after exact real tasks without automatic next generation");
 check(s.entered==1&&s.returned==1&&s.finally==1&&s.coldPools==1&&s.unownedTasks==generationIndex+1,"actual pool initialized once and retained for all attempted generations");
 for(unsigned i=0;i<r.taskCount;++i){const auto&t=r.tasks[i];check(t.finished&&!t.abnormal&&t.ports.captured==3&&t.ports.restored&&!t.ports.uncertain&&t.thread==activatedQueue.tid,"observer exception contained inside actual Root; same warm worker receipts clean");}
 life::Stop();
 printf("{\"case\":\"%ls\",\"passed\":%s,\"startup_and_fault_composed\":true,\"fault_generation\":%u,\"registered_workers\":%u,\"root_tasks\":%u,\"completed_queue_generations\":%u,\"observer_seh_actual\":true,\"next_register_calls\":%u,\"next_open_calls\":%u,\"next_generation_absent\":true,\"earlier_history_checked\":%s,\"scheduler_fence\":false,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",generationIndex+2,r.threads,r.taskCount,generationIndex,g.registerCalls,g.openCalls,generationIndex?"true":"false");fflush(stdout);ExitProcess(failures?1:0);
}

#define session (*currentSession)
