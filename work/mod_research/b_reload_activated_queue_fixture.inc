// Owned cold-pool constructor and synchronous fixture dispatch. Actual parent
// assignment, initial wait, long-lived runner, IAT activation and Root captures
// are executed natively; no direct Root Initialize/Begin occurs in runState.
namespace aq=b_reload_root_activation;
struct ActivatedQueue {
 StatePort task{};HANDLE initial=nullptr,thread=nullptr;DWORD tid=0;
 RootExercise* exercise=nullptr;unsigned tasks=0;bool prepared=false;
};
static ActivatedQueue activatedQueue;
static bool activatedIsWorker(){return activatedQueue.tid&&GetCurrentThreadId()==activatedQueue.tid;}
static std::uint64_t activatedArgument(unsigned i){return activatedQueue.exercise&&i<3?activatedQueue.exercise->args[i]:0;}
static uintptr_t activatedStatus(){return activatedIsWorker()?0:parentStatus();}
static DWORD activatedWait(HANDLE h,DWORD timeout){auto&q=activatedQueue;
 if(q.initial&&activatedIsWorker()&&h==q.task.ready){SetEvent(q.initial);return WaitForSingleObject(h,timeout);}
 return nativeWaitDouble(h,timeout);
}
static BOOL activatedSet(HANDLE h){auto&q=activatedQueue;parentBeforeWake(h);
 if(q.prepared&&h==q.task.done){put<std::uint64_t>(base+0x19E7310+0x30,1);return SetEvent(h);}
 if(q.prepared&&h==q.task.ready)return SetEvent(h);
 return nativeSetEventDouble(h);
}
static uintptr_t activatedCopy(uintptr_t source,uintptr_t target){memcpy(reinterpret_cast<void*>(target),reinterpret_cast<void*>(source),40);return target;}
static void activatedSwap(uintptr_t source,uintptr_t target){const auto a=at<uintptr_t>(source+0x38),b=at<uintptr_t>(target+0x38);boundRequire(a&&b,"owned callable copy has source and stable allocation");memcpy(reinterpret_cast<void*>(b),reinterpret_cast<void*>(a),40);}
static std::uint64_t activatedBusiness(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
 auto&q=activatedQueue;check(activatedIsWorker()&&q.exercise&&!rootExercise,"business occurs only on current persistent runner task");rootExercise=q.exercise;
 __try{return rootUpdate(self,a,b,c);}__finally{rootExercise=nullptr;}
}
static DWORD WINAPI activatedEntry(void*){using Entry=DWORD(*)(void*);return reinterpret_cast<Entry>(base+0x83A930)(reinterpret_cast<void*>(activatedQueue.task.object));}
static void activatedPrepare(){auto&q=activatedQueue;
 if(!q.prepared){
  rootPrepareMachine();yieldPrepare();auto&t=q.task;t.image=base;t.worker=alloc(4096)+8;t.callable=t.worker+0x100;t.object=t.worker+0x200;
  t.ready=CreateEventW(nullptr,FALSE,FALSE,nullptr);t.done=CreateEventW(nullptr,TRUE,TRUE,nullptr);q.initial=CreateEventW(nullptr,TRUE,FALSE,nullptr);
  put<uintptr_t>(t.worker+8,t.object);put<uintptr_t>(t.worker+0x10,t.object+0x100);put<uintptr_t>(t.worker+0x50,t.callable);put<DWORD>(t.worker+0x58,1);put<uintptr_t>(t.worker+0x68,uintptr_t(t.done));put<DWORD>(t.worker+0x70,1);
  put<uintptr_t>(t.object+0x20,uintptr_t(t.ready));put<uintptr_t>(t.object+0x30,t.worker+8);put<uintptr_t>(t.object+0x38,base+0x834D10);put<DWORD>(t.object+8,2);q.prepared=true;
  boundRequire(aq::Initialize({base,&provider,1000})&&aq::PublishIat(),"Root activation IAT published once before native pool wake");
  put<uintptr_t>(base+0x123C1D8,uintptr_t(&activatedSet));put<uintptr_t>(base+0x123C1E0,uintptr_t(&activatedWait));
  q.thread=CreateThread(nullptr,0,activatedEntry,nullptr,CREATE_SUSPENDED,&q.tid);boundRequire(q.thread!=nullptr,"cold generic native worker constructed");t.workerTid=q.tid;put<DWORD>(t.object+0x10,q.tid);put<uintptr_t>(t.object+0x18,uintptr_t(q.thread));
  boundRequire(ResumeThread(q.thread)!=DWORD(-1)&&WaitForSingleObject(q.initial,10000)==WAIT_OBJECT_0,"owned worker parked at native initial wait before task");
 }
 // New fixture worlds retain the native runner, thread object and IAT wrapper.
 // Only fixture-owned callable table and external synchronization are installed.
 put<uintptr_t>(base+0x12F2440,uintptr_t(&activatedCopy));put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(base+0x12F2440+0x20,uintptr_t(&parentNoop));
 parentJump(0x160F0,uintptr_t(&activatedSwap));put<uintptr_t>(base+0x123C1D8,uintptr_t(&activatedSet));put<uintptr_t>(base+0x123C1E0,uintptr_t(&activatedWait));
 aq::Report r{};boundRequire(aq::Snapshot(r)&&r.error==aq::Error::None&&at<uintptr_t>(r.iatSlot)==r.replacement,"retained activation owner verified before each task");
}
static std::uint64_t runState(Invoke fn,std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
 activatedPrepare();auto&q=activatedQueue;auto&e=*new RootExercise;e.task=&q.task;e.fn=fn;e.args[0]=a;e.args[1]=b;e.args[2]=c;q.exercise=&e;q.task.state=uintptr_t(self);
 const auto vt=at<uintptr_t>(self),update=at<uintptr_t>(vt+0x28),status=at<uintptr_t>(vt+0x30);
 DWORD old=0;boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,PAGE_READWRITE,&old)!=FALSE,"owned dispatch writable");put<uintptr_t>(vt+0x28,uintptr_t(&activatedBusiness));put<uintptr_t>(vt+0x30,uintptr_t(&activatedStatus));boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,old,&old)!=FALSE,"owned dispatch restored protection");
 actualParentPort(&q.task);aq::Report report{};const auto deadline=GetTickCount64()+10000;
 do{aq::Snapshot(report);if(report.tasks[q.tasks].finished||report.error!=aq::Error::None)break;Sleep(1);}while(GetTickCount64()<deadline);
 const auto&r=report.tasks[q.tasks].ports;
 boundRequire(report.error==aq::Error::None&&report.taskCount==q.tasks+1&&report.tasks[q.tasks].finished,"automatic source finishes exact immutable task before dispatcher reuse");
 check(r.captured==3&&r.accepted[0]==1&&r.accepted[1]==1&&r.accepted[2]==1&&r.yields==unsigned(e.yielded)&&r.accepted[3]==unsigned(e.yielded),"real Root entry/yield/return/done captured on automatically activated worker");
 check(r.error==rootports::Error::None&&r.finished&&r.restored&&!r.uncertain&&nestedDrEqual(r.originalDr,r.restoredDr),"automatic Root and nested scopes restore hardware state");
 check(e.bodies==1&&!e.abnormal&&report.tasks[q.tasks].binding.generation==generationIndex+2&&r.thread==q.tid,"real root source pins exact task generation and persistent thread");
 boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,PAGE_READWRITE,&old)!=FALSE,"restore owned callback slots");put<uintptr_t>(vt+0x28,update);put<uintptr_t>(vt+0x30,status);boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,old,&old)!=FALSE,"owned callback protection restored");
 ++q.tasks;++nestedTasks;nestedCaptures+=r.captured;if(fn==GuestSessionUpdateInvoke)++nestedLoadTasks;q.exercise=nullptr;return e.value;
}
static void activatedFinish(){auto&q=activatedQueue;boundRequire(q.tasks==16,"all sixteen queue Root tasks used one native runner");put<DWORD>(q.task.worker+0x5c,1);SetEvent(q.task.ready);boundRequire(WaitForSingleObject(q.thread,10000)==WAIT_OBJECT_0,"persistent Root worker drained after both generations");
 aq::Report r{};aq::Snapshot(r);check(r.error==aq::Error::None&&!r.uncertain&&r.threads==1&&r.taskCount==16&&r.gateEntries==16&&r.gateFinishes==16&&r.initialWaitVerified==1&&r.outerBefore==1&&r.outerFinally==1,"one cold publication and sixteen actual IAT task activations across two generations");
 for(unsigned i=0;i<16;++i)check(r.tasks[i].ports.captured==3&&r.tasks[i].ports.restored&&r.tasks[i].binding.generation==(i<8?2u:3u),"each retained automatic task belongs to exact original generation");
 printf("{\"automatic_root_activation\":true,\"full_queue_composed\":true,\"root_tasks\":%u,\"root_thread_count\":%u,\"initial_wait_proofs\":%u,\"iat_entries\":%u,\"iat_finishes\":%u,\"outer_finally\":%u,\"existing_pool_supported\":false}\n",r.taskCount,r.threads,r.initialWaitVerified,r.gateEntries,r.gateFinishes,r.outerFinally);
 CloseHandle(q.thread);CloseHandle(q.initial);CloseHandle(q.task.ready);CloseHandle(q.task.done);aq::Stop();
}
