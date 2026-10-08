// Direct data-core probes. These captures are explicit fixtures, not OS contexts.
// The three inherited integration cases separately exercise the actual parent.
namespace bound=checkpoint_native_task_provider_bound;
static void boundRequire(bool ok,const char*why){if(!ok){printf("FAIL: %s; terminating owned fixture before stack-job lifetime ends\n",why);fflush(stdout);ExitProcess(1);}}
struct BoundSwitch {tp::Provider* provider=nullptr;std::uint64_t generation=0;HANDLE start=nullptr,done=nullptr;bool opened=false;};
static DWORD WINAPI boundSwitch(void*p){auto&j=*static_cast<BoundSwitch*>(p);if(WaitForSingleObject(j.start,10000)==WAIT_OBJECT_0)j.opened=j.provider->OpenWindow(j.generation);SetEvent(j.done);return 0;}
static void boundSwitchAndWait(tp::Provider&p,std::uint64_t generation){BoundSwitch j{&p,generation,CreateEventW(nullptr,TRUE,FALSE,nullptr),CreateEventW(nullptr,TRUE,FALSE,nullptr),false};boundRequire(j.start&&j.done,"switch gates created");auto h=CreateThread(nullptr,0,boundSwitch,&j,0,nullptr);boundRequire(h!=nullptr,"switch thread created");SetEvent(j.start);boundRequire(WaitForSingleObject(j.done,10000)==WAIT_OBJECT_0&&WaitForSingleObject(h,10000)==WAIT_OBJECT_0,"other thread drained before stack job leaves scope");check(j.opened,"new Provider window actually selected by other thread");CloseHandle(h);CloseHandle(j.start);CloseHandle(j.done);}
static bool boundSame(const tp::Report&a,const tp::Report&b){return a.generation==b.generation&&a.attempt==b.attempt&&a.epoch==b.epoch&&a.events==b.events&&a.creations==b.creations&&a.retainedTasks==b.retainedTasks&&a.error==b.error&&a.rejected==b.rejected&&a.ignored==b.ignored&&a.windowOpen==b.windowOpen&&a.closed==b.closed;}
struct BoundWorker {tp::Provider* provider=nullptr;uintptr_t worker=0,callable=0,object=0,frame=0;HANDLE start=nullptr;bool entered=false,returned=false,done=false,yieldMode=false,yielded=false;HANDLE atYield=nullptr,resume=nullptr;};
static DWORD WINAPI boundWorker(void*p){auto&j=*static_cast<BoundWorker*>(p);if(WaitForSingleObject(j.start,10000)!=WAIT_OBJECT_0)return 1;
 tp::Capture w{};w.thread=GetCurrentThreadId();w.rsp=j.frame;put<uintptr_t>(j.frame,base+0x834D9B);w.rip=base+0x50B730;w.rcx=j.callable;j.entered=j.provider->Observe(w);
 if(j.yieldMode){w.rip=base+0x50B690;j.yielded=j.provider->Observe(w);SetEvent(j.atYield);if(WaitForSingleObject(j.resume,10000)!=WAIT_OBJECT_0)return 2;}
 w.rip=base+0x834D9B;w.rbx=j.worker+8;w.rdi=j.object;j.returned=j.provider->Observe(w);
 put<DWORD>(j.worker+0x58,1);w.rip=base+0x834DB4;j.done=j.provider->Observe(w);return 0;
}
static std::uint64_t boundPhaseNext=0;
static void boundBeforePhase(){if(boundPhaseNext){const auto generation=boundPhaseNext;boundPhaseNext=0;boundSwitchAndWait(provider,generation);}}
static void boundParentProbe(const tp::Config&cfg){
 if(providerCase!=L"bound-parent-switch")return;
 auto next=cfg;++next.generation.callbacks.id;++next.generation.attempt;++next.generation.epoch;
 check(provider.Register(next),"register second bank without changing current before actual parent");boundPhaseNext=next.generation.callbacks.id;
 b_reload_queue_parent_source::Report before{},after{};parentSource.Snapshot(before);
 const auto m=base+0x19E7310,stack=at<uintptr_t>(m+0x20);StatePort task{};task.image=base;task.state=at<uintptr_t>(stack+(at<std::uint64_t>(m+0x10)-1)*8);task.worker=alloc(4096)+8;task.object=task.worker+0x200;task.ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);task.done=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 // Once stale fresh has been rejected, the owned pool service raises its
 // explicit fixture exception, so no unobserved worker is allowed to hang.
 // This is NOT a production scheduler fence or proof that native work stops.
 parentThrow=2;bool caught=false;
 __try {actualParentPort(&task);}__except(GetExceptionCode()==0xE014CE02?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
 parentSource.Snapshot(after);tp::Report oldBank{},newBank{};provider.Snapshot(cfg.generation.callbacks.id,oldBank);provider.Snapshot(next.generation.callbacks.id,newBank);
 check(caught&&!boundPhaseNext&&after.error==b_reload_queue_parent_source::Error::Provider,"actual parent capture refused current switch before owned pool exception");
 check(after.scopes==before.scopes+1&&after.hits[0]==before.hits[0]+1&&after.accepted[0]==before.accepted[0],"actual OS fresh context reaches atomic expected Provider and is rejected");
 check(!after.active&&!after.uncertain&&after.finally==before.finally+1&&after.restored==before.restored+1&&after.abnormal==before.abnormal+1&&!memcmp(after.originalDr,after.restoredDr,sizeof after.originalDr),"error path actual PE FINALLY restores all six debug registers and drains active");
 check(!oldBank.events&&!oldBank.creations&&!newBank.events&&!newBank.creations&&oldBank.error==tp::Error::None&&newBank.error==tp::Error::None,"actual stale context cannot record into either bank");
 check(parentSource.EndWindow(queueBinding),"faulted parent can retire only after actual scope drainage");
 CheckpointLoadWorkerBridgeStats stats{};BReloadParentBridgeSnapshot(0,&stats);check(!stats.active&&!stats.cleanup_faults&&stats.abnormal_exits==1,"actual outer bridge cleanup completed after stale capture");
 CloseHandle(task.ready);CloseHandle(task.done);
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"actual_parent_switch\":true,\"actual_os_fresh_context\":true,\"parent_error\":%u,\"restored\":%u,\"active\":%u,\"fixture_pool_exception\":true,\"scheduler_fence\":false}\n",providerCase.c_str(),failures?"false":"true",failures,unsigned(after.error),after.restored-before.restored,after.active);fflush(stdout);ExitProcess(failures?1:0);
}
static void boundClosedProbe(const b_reload_queue_parent_source::Binding&b){tp::Report before{},after{};check(provider.Snapshot(b.generation,before)&&before.closed,"completed provider window before closed observation");tp::Capture c{};c.rip=base+0x50B4B3;c.rsp=1;c.thread=GetCurrentThreadId();check(!bound::ObserveExpected(provider,{b.generation,b.attempt,b.epoch},c),"closed window refused before invalid capture memory access");check(provider.Snapshot(b.generation,after)&&boundSame(before,after),"closed refusal cannot poison completed receipt");}
static void boundProbe(const tp::Config&cfg){
 if(providerCase.rfind(L"bound-",0)!=0||providerCase==L"bound-parent-switch")return;
 auto*p=new tp::Provider;auto next=cfg;++next.generation.callbacks.id;++next.generation.attempt;++next.generation.epoch;
 const bound::Binding old{cfg.generation.callbacks.id,cfg.generation.attempt,cfg.generation.epoch},fresh{next.generation.callbacks.id,next.generation.attempt,next.generation.epoch};
 check(p->Register(cfg)&&p->Register(next)&&p->OpenWindow(old.generation),"two real Provider banks registered; old selected");
 const auto manager=base+0x19E7310,stack=alloc(4096),state=alloc(4096),frame=alloc(4096);
 put<uintptr_t>(state,base+0x12CC4A8);put<uintptr_t>(stack,state);put<std::uint64_t>(manager+0x10,3);put<uintptr_t>(manager+0x20,stack);put<uintptr_t>(manager+0x48,state);put<uintptr_t>(frame+0x40,stack);
 tp::Capture c{};c.rip=base+0x50B4B3;c.rsp=frame;c.thread=GetCurrentThreadId();
 tp::Report a{},b{},aa{},bb{};check(p->Snapshot(old.generation,a)&&p->Snapshot(fresh.generation,b),"probe initial bank snapshots");
 bool switched=false,created=false;uintptr_t worker=0,callable=0,object=0;BoundWorker job{};HANDLE workerHandle=nullptr;
 if(providerCase==L"bound-switch-create"||providerCase==L"bound-old-worker"||providerCase==L"bound-cross-complete"||providerCase==L"bound-cross-resume"){
  check(bound::ObserveExpected(*p,old,c),"old bound fresh accepted before bank switch");
  worker=alloc(4096);callable=alloc(4096);object=alloc(4096);const auto holder=alloc(4096);
  put<uintptr_t>(state+0x50,worker);put<uintptr_t>(worker+0x50,callable);put<uintptr_t>(worker+8,object);put<DWORD>(object+0x10,GetCurrentThreadId());put<uintptr_t>(callable,base+0x12F2440);put<uintptr_t>(callable+8,holder);put<uintptr_t>(holder,stack);
  c.rip=base+0x50B598;c.rdi=worker;
  if(providerCase!=L"bound-switch-create"){
   job.provider=p;job.worker=worker;job.callable=callable;job.object=object;job.frame=alloc(4096);job.start=CreateEventW(nullptr,TRUE,FALSE,nullptr);job.yieldMode=providerCase==L"bound-cross-resume";job.atYield=CreateEventW(nullptr,TRUE,FALSE,nullptr);job.resume=CreateEventW(nullptr,TRUE,FALSE,nullptr);
   boundRequire(job.start&&job.atYield&&job.resume,"worker gates created");DWORD workerId=0;workerHandle=CreateThread(nullptr,0,boundWorker,&job,0,&workerId);
   boundRequire(workerHandle&&workerId!=GetCurrentThreadId(),"actual different worker thread waiting before attribution");put<DWORD>(object+0x10,workerId);
   check(bound::ObserveExpected(*p,old,c),"old bound creation uses selected bank");created=true;
  }
  check(p->Snapshot(old.generation,a),"old pre-switch observation recorded");
 }
 if(providerCase==L"bound-switch-fresh"||providerCase==L"bound-switch-create"||created){boundSwitchAndWait(*p,fresh.generation);switched=true;check(p->Snapshot(fresh.generation,b),"new window opened");}
 if(providerCase==L"bound-switch-fresh"||providerCase==L"bound-switch-create"){
  check(!bound::ObserveExpected(*p,old,c),"stale expected generation refused after other-thread OpenWindow");
  check(p->Snapshot(old.generation,aa)&&p->Snapshot(fresh.generation,bb)&&boundSame(a,aa)&&boundSame(b,bb),"stale rejection changes neither old nor current bank");
  c.rip=base+0x50B4B3;check(bound::ObserveExpected(*p,fresh,c),"new expected generation still accepts fresh capture");
 }else if(created){
  SetEvent(job.start);
  if(job.yieldMode){
   boundRequire(WaitForSingleObject(job.atYield,10000)==WAIT_OBJECT_0,"old worker actually waiting in yielded scope");check(job.entered&&job.yielded&&!job.returned&&!job.done,"old task is live and yielded, not an already-finished rejection");
   tp::Report paused{},unchanged{};check(p->Snapshot(old.generation,paused)&&paused.events==a.events+1&&paused.error==tp::Error::None,"actual old worker entry before yield");
   c.rip=base+0x50B4AE;check(!bound::ObserveExpected(*p,fresh,c),"new expected cannot resume live yielded old-bank record");
   check(p->Snapshot(old.generation,unchanged)&&boundSame(paused,unchanged),"cross-bank resume rejection leaves old task intact");
   check(p->Observe(c),"same old task is genuinely resumable through immutable legacy association");SetEvent(job.resume);
  }
  boundRequire(WaitForSingleObject(workerHandle,10000)==WAIT_OBJECT_0,"old worker drained before stack job leaves scope");CloseHandle(workerHandle);CloseHandle(job.start);CloseHandle(job.atYield);CloseHandle(job.resume);
  check(job.entered&&job.returned&&job.done,"ordinary old worker callbacks execute with immutable record");
  check(p->Snapshot(old.generation,aa)&&aa.events==a.events+3&&aa.error==tp::Error::None,"old worker entry/return/done actually update old bank");
  check(p->Snapshot(fresh.generation,bb)&&(job.yieldMode?(!bb.events&&!bb.creations&&bb.error==tp::Error::Attribution):boundSame(b,bb)),"old worker callbacks never update new bank events");a=aa;
  if(providerCase==L"bound-cross-resume"){
   check(job.yielded&&job.returned&&job.done,"rejected cross-bank resume followed by valid old resume drains normally");
  }else{
   put<uintptr_t>(state+0x50,0);c.rip=base+0x50B632;c.rdi=worker;check(p->Snapshot(old.generation,a),"old task done before parent completion");
   if(providerCase==L"bound-cross-complete"){
    check(!bound::ObserveExpected(*p,fresh,c),"new expected cannot complete old-bank record");
    check(p->Snapshot(old.generation,aa)&&boundSame(a,aa),"cross-bank completion cannot touch old task");
   }else{
    check(!bound::ObserveExpected(*p,old,c),"stale old parent completion explicitly refused");
    check(p->Snapshot(old.generation,aa)&&p->Snapshot(fresh.generation,bb)&&boundSame(a,aa)&&boundSame(b,bb),"stale completion contaminates neither bank");
    check(p->Observe(c),"legacy explicitly unbound old completion still resolves old immutable record");
    check(p->Snapshot(old.generation,aa)&&aa.events==a.events+1&&aa.error==tp::Error::None,"old legacy completion recorded in old bank");
    check(p->Snapshot(fresh.generation,bb)&&boundSame(b,bb),"legacy completion does not fall back to new bank");
   }
  }
 }else if(providerCase==L"bound-create-without-fresh"){
  c.rip=base+0x50B598;check(!bound::ObserveExpected(*p,old,c),"bound create without selection cannot pretend accepted");
  check(p->Snapshot(old.generation,aa)&&aa.error==tp::Error::Order&&!aa.creations&&!aa.events&&!aa.ignored,"missing selection is explicit order failure");
  check(p->Snapshot(fresh.generation,bb)&&boundSame(b,bb),"order failure does not mutate other bank");
 }else if(providerCase==L"bound-memory"){
  c.rsp=1;check(!bound::ObserveExpected(*p,old,c),"bad capture memory caught inside bound Provider lock");
  check(p->Snapshot(old.generation,aa)&&aa.error==tp::Error::Memory&&aa.exception,"memory error attributed to validated old bank");
  check(p->Snapshot(fresh.generation,bb)&&boundSame(b,bb),"memory exception leaves unrelated bank unchanged");
  boundSwitchAndWait(*p,fresh.generation);switched=true;c.rsp=frame;
  check(p->Observe(c),"TLS expected frame cleared after SEH for next ordinary capture");
  check(p->Snapshot(fresh.generation,bb)&&bb.events==1&&bb.error==tp::Error::None,"ordinary post-exception fresh uses current new bank");
 }else{
  auto invalid=old;
  if(providerCase==L"bound-generation")invalid.generation+=100;
  else if(providerCase==L"bound-attempt")++invalid.attempt;
  else if(providerCase==L"bound-epoch")++invalid.epoch;
  else if(providerCase==L"bound-point")c.rip=base+0x4DA240;
  else if(providerCase==L"bound-foreign-provider"){auto*foreign=new tp::Provider;check(!bound::ObserveExpected(*foreign,old,c),"same identity against unregistered other Provider refused");}
  else check(false,"known bound test case");
  if(providerCase!=L"bound-foreign-provider")check(!bound::ObserveExpected(*p,invalid,c),"wrong binding or nonparent point rejected");
  check(p->Snapshot(old.generation,aa)&&p->Snapshot(fresh.generation,bb)&&boundSame(a,aa)&&boundSame(b,bb),"invalid context causes no unrelated mutation");
  c.rip=base+0x50B4B3;check(bound::ObserveExpected(*p,old,c),"valid old binding works after refusal and TLS restoration");
 }
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"direct_provider_probe\":true,\"other_thread_switch\":%s,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",failures,switched?"true":"false");fflush(stdout);ExitProcess(failures?1:0);
}
