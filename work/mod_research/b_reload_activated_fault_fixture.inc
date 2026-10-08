// Fault injection is confined to the owned native cold worker. No direct Root
// Begin, fabricated Capture, live process discovery, or DR recovery/reset.
namespace afh=checkpoint_persistent_input_hwbp;
extern "C" {extern uintptr_t HwbpFixtureUser;void HwbpFixtureSite();extern unsigned char HwbpFixtureBeforeCall;}
struct ActivatedFault {afh::Context context{};afh::Binding binding{};afh::HardwareReceipt receipt{};unsigned observerCalls=0,finally=0;bool caught=false,retryRefused=false,foreignPreserved=false;std::uint64_t changed[6]{};};
static ActivatedFault activatedFault;
static bool activatedForeign(){return providerCase==L"activated-fault-foreign-dr";}
static bool activatedObserver(){return providerCase==L"activated-fault-observer";}
static void activatedForeignSite(){static volatile LONG value=0;InterlockedIncrement(&value);}
struct ActivatedDebugJob {HANDLE target=nullptr;bool mutate=false,ok=false;std::uint64_t dr[6]{};};
static DWORD WINAPI activatedDebugJob(void*p){auto&j=*static_cast<ActivatedDebugJob*>(p);const auto count=SuspendThread(j.target);if(count==DWORD(-1))return 0;
 __try {if(count)__leave;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(j.target,&c))__leave;
  if(j.mutate){if(c.Dr2||(c.Dr7&0x30))__leave;c.Dr2=uintptr_t(&activatedForeignSite);c.Dr7|=0x10;if(!SetThreadContext(j.target,&c))__leave;c.ContextFlags=CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(j.target,&c))__leave;}
  const std::uint64_t dr[]={c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7};memcpy(j.dr,dr,sizeof dr);j.ok=true;
 }__finally{if(ResumeThread(j.target)==DWORD(-1))j.ok=false;}return 0;
}
static void activatedReadDebug(bool mutate,std::uint64_t out[6]){ActivatedDebugJob job{};job.mutate=mutate;
 boundRequire(DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&job.target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)!=FALSE,"fault helper duplicates only its owned current worker");
 auto h=CreateThread(nullptr,0,activatedDebugJob,&job,0,nullptr);boundRequire(h&&WaitForSingleObject(h,10000)==WAIT_OBJECT_0,"owned helper completes real debug-register access");CloseHandle(h);CloseHandle(job.target);boundRequire(job.ok,"actual debug context read/write confirmed");memcpy(out,job.dr,sizeof job.dr);
}
static afh::PendingReport activatedObserve(void*p,const afh::Binding&b,std::uint64_t call,const void*user) noexcept {auto&f=*static_cast<ActivatedFault*>(p);
 check(activatedIsWorker()&&b.owner_generation==f.binding.owner_generation&&call==71&&uintptr_t(user)==activatedQueue.task.state,"actual child callback belongs to activation-owned Root task");++f.observerCalls;
 if(activatedObserver())RaiseException(0xE014CF13,0,0,nullptr);
 return {}; // No input authorization is supplied by this diagnostic observer.
}
static std::uint64_t activatedFaultBusiness(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){auto&f=activatedFault;tp::Report p{};
 boundRequire(provider.Snapshot(generationIndex+2,p),"same immutable generation available to child config");f.binding.attempt.fill(0x31);f.binding.attachment.fill(0x72);f.binding.owner_generation=p.generation;
 afh::Config cfg{f.binding,uintptr_t(&HwbpFixtureBeforeCall),1000};boundRequire(afh::Initialize(f.context,cfg)&&afh::Begin(f.context,activatedObserve,&f,f.binding,71,reinterpret_cast<void*>(self)),"child hardware observation borrows actual automatically activated Root");
 __try {
  HwbpFixtureUser=uintptr_t(self);HwbpFixtureSite();
  if(activatedForeign())activatedReadDebug(true,f.changed);
  if(!activatedObserver())RaiseException(0xE014CF11,0,0,nullptr);
 }__finally {
  ++f.finally;afh::Finish(f.context);afh::Snapshot(f.context,f.receipt);
  if(activatedForeign()){std::uint64_t actual[6]{};activatedReadDebug(false,actual);check(nestedDrEqual(actual,f.changed),"child FINALLY preserves foreign DR mutation");
   auto*retry=new afh::Context;check(afh::Initialize(*retry,cfg)&&!afh::Begin(*retry,activatedObserve,&f,f.binding,72,reinterpret_cast<void*>(self)),"uncertain child refuses new same-thread observer before native continuation");afh::HardwareReceipt r{};afh::Snapshot(*retry,r);f.retryRefused=r.error==afh::Error::AlreadyUsed&&!r.entered;check(f.retryRefused,"retained child tombstone prevents duplicate admission");
  }
 }
 return 0;
}
static void activatedFaultCaught(){auto&f=activatedFault;auto&q=activatedQueue;f.caught=true;
 if(activatedForeign()){std::uint64_t actual[6]{};activatedReadDebug(false,actual);f.foreignPreserved=nestedDrEqual(actual,f.changed);check(f.foreignPreserved,"automatic Root FINALLY also leaves foreign debug state untouched");}
 // Only owned parent teardown after the actual original exception has crossed
 // both PE FINALLY boundaries. This is not normal task completion or recovery.
 put<DWORD>(q.task.worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(q.task.done);
}
[[noreturn]] static void activatedFaultCompleted(const aq::Report&initial){auto&q=activatedQueue;auto&f=activatedFault;
 check(initial.taskCount==1&&initial.tasks[0].finished&&initial.gateEntries==1&&initial.gateFinishes==1,"one actual IAT task activation and one actual cleanup");
 if(activatedObserver()){put<DWORD>(q.task.worker+0x5c,1);SetEvent(q.task.ready);}
 boundRequire(WaitForSingleObject(q.thread,10000)==WAIT_OBJECT_0,"fault worker exits naturally or after owned normal completion stop");aq::Report r{};aq::Snapshot(r);const auto&rootReport=r.tasks[0].ports;const auto&child=f.receipt;
 check(r.threads==1&&r.taskCount==1&&r.initialWaitVerified==1&&r.outerBefore==1&&r.outerFinally==1&&r.gateEntries==1&&r.gateFinishes==1,"no duplicate Root task or IAT scope minted by fault cleanup");
 check(child.entered&&child.captured==1&&child.finished&&f.finally==1&&!child.queue_authorized&&!child.full_input_hold&&f.observerCalls==1,"fault exercised actual hardware capture and exactly one nested FINALLY with no authority");
 CheckpointLoadWorkerBridgeStats outer{};BReloadRootActivationBridgeSnapshot(1,&outer);check(outer.started==1&&outer.scope_claims==1&&outer.finally_calls==1&&!outer.active&&!outer.cleanup_faults,"one real outer owner claim drains without duplicate claim");
 if(activatedForeign()){
  check(child.error==afh::Error::RestoreConflict&&!child.restored&&child.restore_uncertain&&f.retryRefused&&f.foreignPreserved,"child conflict stays uncertain and forbids same-thread retry");
  check(r.error==aq::Error::Ports&&r.uncertain&&rootReport.error==rootports::Error::Conflict&&!rootReport.restored&&rootReport.uncertain&&rootReport.captured==1&&rootReport.providerScopeAbandoned==1&&r.tasks[0].abnormal&&f.caught,"actual automatic owner receives unresolved child conflict and retains failure");
 }else{
  check(child.restored&&!child.restore_uncertain&&nestedDrEqual(child.original_dr,child.restored_dr)&&rootReport.restored&&!rootReport.uncertain&&!r.uncertain,"restorable nested faults preserve hardware ownership");
  if(activatedObserver())check(child.error==afh::Error::Observer&&child.exception_code==0xE014CF13&&r.error==aq::Error::None&&rootReport.error==rootports::Error::None&&rootReport.captured==3&&!f.caught&&!r.tasks[0].abnormal,"contained observer failure remains child error while original task returns normally");
  else check(child.error==afh::Error::None&&r.error==aq::Error::None&&rootReport.captured==1&&rootReport.providerScopeAbandoned==1&&r.tasks[0].abnormal&&f.caught,"business SEH propagates through automatic owner and abandons its sole immutable task");
 }
 aq::Stop();aq::Report after{};aq::Snapshot(after);check(after.taskCount==r.taskCount&&after.gateEntries==r.gateEntries&&after.gateFinishes==r.gateFinishes&&after.error==r.error&&after.uncertain==r.uncertain,"stop does not clear or rewrite failure receipts");
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"actual_root_activation\":true,\"full_queue_executed\":false,\"tasks\":%u,\"outer_claims\":%llu,\"root_captures\":%u,\"root_restored\":%u,\"root_uncertain\":%u,\"child_captures\":%u,\"child_error\":%u,\"child_uncertain\":%u,\"owner_error\":%u,\"owner_uncertain\":%u,\"business_seh_caught\":%s,\"same_thread_retry_refused\":%s,\"further_task_attempted\":false,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",failures,r.taskCount,outer.scope_claims,rootReport.captured,rootReport.restored,rootReport.uncertain,child.captured,unsigned(child.error),child.restore_uncertain,unsigned(r.error),r.uncertain,f.caught?"true":"false",f.retryRefused?"true":"false");fflush(stdout);ExitProcess(failures?1:0);
}
static void activatedFaultProbe(){if(providerCase.rfind(L"activated-fault-",0)!=0)return;runState(activatedFaultBusiness,layout.config.states[4],0,0,0);boundRequire(false,"fault probe must end after its single native task");}
