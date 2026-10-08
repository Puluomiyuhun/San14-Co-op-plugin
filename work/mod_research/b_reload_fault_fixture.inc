// Owned-process fault injection. The helpers only suspend the current fixture
// thread; no process discovery, game access, forged Capture, or recovery reset.
static bool faultCase(){return providerCase.rfind(L"root-input-",0)==0;}
static bool faultAbnormal(){return faultCase()&&providerCase!=L"root-input-observer-exception";}
struct FaultInput {hw::Context input{};hw::Binding binding{};hw::HardwareReceipt receipt{};unsigned observed=0,finally=0;bool mutation=false,retryRefused=false;std::uint64_t changedDr[6]{};};
static FaultInput* faultState=nullptr;
static void faultForeignSite(){static volatile LONG marker=0;InterlockedIncrement(&marker);}
struct FaultDebugJob {HANDLE target=nullptr;bool mutate=false,ok=false;std::uint64_t dr[6]{};};
static DWORD WINAPI faultDebugJob(void*p){auto&j=*static_cast<FaultDebugJob*>(p);const auto count=SuspendThread(j.target);if(count==DWORD(-1))return 0;
 __try {if(count)__leave;CONTEXT c{};c.ContextFlags=CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(j.target,&c))__leave;
  if(j.mutate){if(c.Dr2||(c.Dr7&0x30))__leave;c.Dr2=uintptr_t(&faultForeignSite);c.Dr7|=0x10;if(!SetThreadContext(j.target,&c))__leave;c.ContextFlags=CONTEXT_DEBUG_REGISTERS;if(!GetThreadContext(j.target,&c))__leave;}
  const std::uint64_t values[]={c.Dr0,c.Dr1,c.Dr2,c.Dr3,c.Dr6,c.Dr7};memcpy(j.dr,values,sizeof values);j.ok=true;
 }__finally {if(ResumeThread(j.target)==DWORD(-1))j.ok=false;}return 0;
}
static void faultReadDebug(bool mutate,std::uint64_t out[6]){
 FaultDebugJob job{};job.mutate=mutate;
 boundRequire(DuplicateHandle(GetCurrentProcess(),GetCurrentThread(),GetCurrentProcess(),&job.target,THREAD_GET_CONTEXT|THREAD_SET_CONTEXT|THREAD_SUSPEND_RESUME|SYNCHRONIZE,FALSE,0)!=FALSE,"owned fault helper duplicates current fixture thread");
 auto h=CreateThread(nullptr,0,faultDebugJob,&job,0,nullptr);boundRequire(h&&WaitForSingleObject(h,10000)==WAIT_OBJECT_0,"owned fault helper fully drained");CloseHandle(h);CloseHandle(job.target);boundRequire(job.ok,"actual OS context read or fault injection verified");memcpy(out,job.dr,sizeof job.dr);
}
static hw::PendingReport faultObserve(void*p,const hw::Binding&b,std::uint64_t call,const void*user) noexcept {
 auto&f=*static_cast<FaultInput*>(p);check(b.owner_generation==f.binding.owner_generation&&call==71&&uintptr_t(user)==rootExercise->task->state,"input callback uses current actual Root/user identity");++f.observed;
 if(providerCase==L"root-input-observer-exception")RaiseException(0xE014CF03,0,0,nullptr);
 // This fault harness is not a planning/input authorization provider.
 return {};
}
static void faultInput(uintptr_t user){auto&f=*new FaultInput;faultState=&f;rootports::Report rootResult{};rootports::Snapshot(rootExercise->ports,rootResult);
 f.binding.attempt.fill(0x31);f.binding.attachment.fill(0x72);f.binding.owner_generation=rootResult.generation;
 hw::Config config{f.binding,uintptr_t(&HwbpFixtureBeforeCall),1000};
 boundRequire(hw::Initialize(f.input,config)&&hw::Begin(f.input,faultObserve,&f,f.binding,71,reinterpret_cast<void*>(user)),"real nested input arm borrows current Root slots");
 __try {
  if(providerCase!=L"root-input-exception-before"){HwbpFixtureUser=user;HwbpFixtureSite();}
  if(providerCase==L"root-input-foreign-dr"){faultReadDebug(true,f.changedDr);f.mutation=true;}
  if(faultAbnormal())RaiseException(0xE014CF01,0,0,nullptr);
 }__finally {++f.finally;hw::Finish(f.input);hw::Snapshot(f.input,f.receipt);
  if(f.mutation){std::uint64_t current[6]{};faultReadDebug(false,current);check(nestedDrEqual(current,f.changedDr),"input FINALLY does not overwrite another DR owner");
   auto*retry=new hw::Context;check(hw::Initialize(*retry,config)&&!hw::Begin(*retry,faultObserve,&f,f.binding,72,reinterpret_cast<void*>(user)),"uncertain child tombstone prevents another same-thread input scope");hw::HardwareReceipt r{};hw::Snapshot(*retry,r);f.retryRefused=r.error==hw::Error::AlreadyUsed&&!r.entered;check(f.retryRefused,"retry refused before hardware mutation");
  }
 }
}
static void faultVerify(const rootports::Report&r){auto&f=*faultState;const auto&h=f.receipt;const bool before=providerCase==L"root-input-exception-before",observer=providerCase==L"root-input-observer-exception";
 check(f.finally==1&&h.finished&&h.entered&&h.captured==unsigned(!before)&&h.observer_calls==unsigned(!before&&!observer),"actual nested FINALLY and prefetch counts match exception position");
 check(!h.queue_authorized&&!h.full_input_hold,"fault observation cannot authorize queue or input hold");
 if(f.mutation){std::uint64_t current[6]{};faultReadDebug(false,current);check(h.error==hw::Error::RestoreConflict&&!h.restored&&h.restore_uncertain&&nestedDrEqual(current,f.changedDr),"both FINALLY layers preserve foreign registers and report uncertainty");check(r.providerScopeAbandoned==1&&r.captured==1&&!r.accepted[1]&&!r.accepted[2]&&f.retryRefused,"uncertain exception has no Root return/done or next scope admission");}
 else {check(h.restored&&!h.restore_uncertain&&nestedDrEqual(h.original_dr,h.restored_dr),"native exception restores only the borrowed input slots");
  const auto expected=before?hw::Error::MissingCapture:observer?hw::Error::Observer:hw::Error::None;check(h.error==expected,"missing prefetch and observer exception are never clean success");
  if(observer)check(h.exception_code==0xE014CF03&&f.observed==1&&r.captured==3&&!r.providerScopeAbandoned,"observer fault contained while unchanged native business returns normally");
 }
 printf("{\"nested_fault\":\"%ls\",\"actual_input_captures\":%u,\"input_finally\":%u,\"input_restored\":%u,\"input_uncertain\":%u,\"input_error\":%u,\"root_captures\":%u,\"root_restored\":%u,\"root_uncertain\":%u,\"foreign_dr_mutation\":%s,\"retry_refused\":%s,\"game_access\":false}\n",providerCase.c_str(),h.captured,f.finally,h.restored,h.restore_uncertain,unsigned(h.error),r.captured,r.restored,r.uncertain,f.mutation?"true":"false",f.retryRefused?"true":"false");
}
