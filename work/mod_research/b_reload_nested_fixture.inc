// Compose actual archived generic Root runner/thunk with the existing complete
// queue/Load/Title exercise. Business callbacks and activation stay explicit
// fixtures; Root captures are obtained only from actual OS instruction context.
namespace lease=b_reload_nested_debug;
struct NestedReleaseJob {lease::Lease value{};bool result=true;};
static DWORD WINAPI nestedForeignRelease(void*p){auto&j=*static_cast<NestedReleaseJob*>(p);j.result=lease::Release(j.value);return 0;}
static void nestedLeaseProbe(){
 tp::Report p{};check(provider.Snapshot(generationIndex+2,p),"lease probe fixed generation");
 lease::Lease value{};
 check(lease::Acquire(&provider,base,p.generation+1,base+0x4DA240,base+0x834B60,value)==lease::Result::Refused&&!value.owner,"wrong generation cannot borrow Root slots");
 auto*foreign=new tp::Provider;
 check(lease::Acquire(foreign,base,p.generation,base+0x4DA240,base+0x834B60,value)==lease::Result::Refused,"different Provider cannot borrow same addresses");
 check(lease::Acquire(&provider,base,p.generation,base+0x4DA241,base+0x834B60,value)==lease::Result::Refused,"unlisted site cannot borrow");
 check(lease::Acquire(&provider,base,p.generation,base+0x4DA240,base+0x834B60,value)==lease::Result::Granted,"Root lends exact native Load start pair");
 const auto saved=value;lease::Lease duplicate{};
 check(lease::Acquire(&provider,base,p.generation,base+0x4F7079,0,duplicate)==lease::Result::Refused,"overlapping child scope refused");
 rootports::Report r{};rootports::Snapshot(rootExercise->ports,r);std::uint64_t dr[6]{};memcpy(dr,r.originalDr,sizeof dr);
 dr[0]=dr[2]=0;dr[1]=base+0x834D9B;dr[3]=base+0x50B690;dr[5]=(dr[5]&~0xffull)|0x44;
 check(lease::Match(saved,dr,false),"exact Root layout matches live lease");
 auto forged=saved;++forged.serial;check(!lease::Match(forged,dr,false),"matching layout without valid serial refused");
 dr[4]|=1;check(!lease::Match(saved,dr,false),"pending debug event cannot be erased by restore");dr[4]&=~1ull;
 ++dr[1];check(!lease::Match(saved,dr,false),"changed Root return slot refused");--dr[1];
 dr[0]=base+0x4DA240;dr[2]=base+0x834B60;dr[5]|=0x11;
 check(lease::Match(saved,dr,true)&&!lease::Match(saved,dr,false),"borrowed layout distinct from restored Root layout");
 auto*job=new NestedReleaseJob;job->value=saved;HANDLE h=CreateThread(nullptr,0,nestedForeignRelease,job,0,nullptr);
 boundRequire(h&&WaitForSingleObject(h,10000)==WAIT_OBJECT_0,"owned lease rejection thread drained");CloseHandle(h);
 check(!job->result&&lease::Release(saved)&&!lease::Release(saved),"only original thread releases exact lease once");
 check(lease::Acquire(&provider,base,p.generation,base+0x4F7079,0,value)==lease::Result::Granted,"next distinct child lease can be acquired");
 check(value.serial!=saved.serial&&!lease::Match(saved,dr,true)&&!lease::Release(saved)&&lease::Release(value),"retired child lease cannot release or certify next child");
}
static bool nestedMachinePrepared=false;
static unsigned nestedTasks=0,nestedCaptures=0,nestedLoadTasks=0;
static BOOL nestedSetEvent(HANDLE event){
 if(rootExercise&&event==rootExercise->task->done)return rootSetEvent(event);
 return nativeSetEventDouble(event);
}
static void nestedPrepare(){
 if(!nestedMachinePrepared){rootPrepareMachine();nestedMachinePrepared=true;}
 put<uintptr_t>(base+0x123C1D8,uintptr_t(&nestedSetEvent));
 put<uintptr_t>(base+0x123C1E0,uintptr_t(&nativeWaitDouble));
}
static std::uint64_t runState(Invoke fn,std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
 nestedPrepare();auto&e=*new RootExercise;e.task=prepareState(uintptr_t(self));
 check(!rootExercise,"no nested generic Root exercise activation");rootExercise=&e;e.fn=fn;e.args[0]=a;e.args[1]=b;e.args[2]=c;
 put<std::uint64_t>(e.task->callable+16,a);put<std::uint64_t>(e.task->callable+24,b);put<std::uint64_t>(e.task->callable+32,c);
 const auto vt=at<uintptr_t>(self),update=at<uintptr_t>(vt+0x28),status=at<uintptr_t>(vt+0x30);
 DWORD old=0;boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,PAGE_READWRITE,&old)!=FALSE,"fixture state dispatch writable");
 put<uintptr_t>(vt+0x28,uintptr_t(&rootUpdate));put<uintptr_t>(vt+0x30,uintptr_t(&rootStatus));
 boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,old,&old)!=FALSE,"fixture dispatch protection restored");
 tp::Report p{};check(provider.Snapshot(generationIndex+2,p),"active Provider binding for Root fixture activation");
 rootports::Config cfg{&provider,base,{p.generation,p.attempt,p.epoch},e.task->worker,e.task->callable,e.task->object,GetCurrentThreadId(),1000};
 boundRequire(rootports::Initialize(e.ports,cfg),"Root source context initialized before actual runner");
 __try{CheckpointLoadWorkerBridge1(e.task->object,e.task->worker+8,0,0);}
 __finally{
  // The PE bridge restores observers first; only owned fixture parent teardown
  // follows. An exception is never converted to normal Root completion.
  if(AbnormalTermination()){put<DWORD>(e.task->worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(e.task->done);}
  boundRequire(WaitForSingleObject(e.task->parent,10000)==WAIT_OBJECT_0,"actual generic Root parent drained");
  CloseHandle(e.task->parent);CloseHandle(e.task->ready);CloseHandle(e.task->done);
  boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,PAGE_READWRITE,&old)!=FALSE,"restore owned business dispatch");
  put<uintptr_t>(vt+0x28,update);put<uintptr_t>(vt+0x30,status);
  boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,old,&old)!=FALSE,"restore business page protection");rootExercise=nullptr;
 }
 rootports::Report r{};check(rootports::Snapshot(e.ports,r),"Root source result retained across nested callbacks");
 check(r.captured==3&&r.accepted[0]==1&&r.accepted[1]==1&&r.accepted[2]==1&&!r.yields,"actual Root entry/return/done in queue composition");
 check(r.error==rootports::Error::None&&r.finished&&r.restored&&!r.uncertain&&!memcmp(r.originalDr,r.restoredDr,sizeof r.originalDr),"Root and nested scopes restore original six debug registers");
 check(e.bodies==1&&e.before==1&&e.after==1&&e.finally==1&&!e.abnormal,"archived generic runner invokes original fixture business exactly once");
 ++nestedTasks;nestedCaptures+=r.captured;if(fn==GuestSessionUpdateInvoke)++nestedLoadTasks;
 return e.value;
}
