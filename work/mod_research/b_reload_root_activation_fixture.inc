// Owned constructor and task business. Native initial wait, scheduler, runner,
// generic thunk, IAT call sites, PE activation and Root events execute on CPU.
namespace act=b_reload_root_activation;
struct ActivationExercise {StatePort t{};HANDLE initial=nullptr,handle=nullptr;DWORD tid=0;unsigned bodies=0;bool abnormal=false;};
static ActivationExercise* activationExercise=nullptr;
static bool activationIsWorker(){return activationExercise&&GetCurrentThreadId()==activationExercise->tid;}
static uintptr_t activationStatus(){return GetCurrentThreadId()==activationExercise->tid?0:parentStatus();}
static DWORD activationWait(HANDLE h,DWORD ms){if(activationExercise&&h==activationExercise->t.ready&&GetCurrentThreadId()==activationExercise->tid)SetEvent(activationExercise->initial);return WaitForSingleObject(h,ms);}
static BOOL activationSet(HANDLE h){parentBeforeWake(h);auto&e=*activationExercise;
 if(h==e.t.done)put<std::uint64_t>(base+0x19E7310+0x30,1);
 if(h==e.t.ready&&providerCase==L"activation-wrong-wait"){put<DWORD>(e.t.worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(e.t.done);}
 return SetEvent(h);
}
static uintptr_t activationCopy(uintptr_t source,uintptr_t target){memcpy(reinterpret_cast<void*>(target),reinterpret_cast<void*>(source),40);return target;}
static void activationSwap(uintptr_t source,uintptr_t target){const auto temp=at<uintptr_t>(source+0x38),stable=at<uintptr_t>(target+0x38);check(temp&&stable,"owned callable storage has both source and stable target");memcpy(reinterpret_cast<void*>(stable),reinterpret_cast<void*>(temp),40);}
static std::uint64_t activationBusiness(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){auto&e=*activationExercise;check(self==e.t.state&&a==0&&b==0&&c==0,"automatic activated native thunk arguments");++e.bodies;if(providerCase==L"activation-exception")RaiseException(0xE014CF01,0,0,nullptr);return 0;}
static DWORD WINAPI activationEntry(void*){auto&e=*activationExercise;
 if(providerCase==L"activation-wrong-wait"){SetEvent(e.initial);WaitForSingleObject(e.t.ready,10000);return 0;}
 __try {using Entry=DWORD(*)(void*);return reinterpret_cast<Entry>(base+0x83A930)(reinterpret_cast<void*>(e.t.object));}
 __except(GetExceptionCode()==0xE014CF01?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){e.abnormal=true;put<DWORD>(e.t.worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(e.t.done);return 1;}
}
static LONG CALLBACK activationFault(EXCEPTION_POINTERS*e){if(e->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION){auto*c=e->ContextRecord;printf("ACTFAULT tid=%lu ip=%llx rcx=%llx rdx=%llx\n",GetCurrentThreadId(),c->Rip-base,c->Rcx,c->Rdx);for(unsigned i=0;i<12;++i)printf("STACK %u %llx rva=%llx\n",i,at<uintptr_t>(c->Rsp+i*8),at<uintptr_t>(c->Rsp+i*8)-base);fflush(stdout);}return EXCEPTION_CONTINUE_SEARCH;}
static void activationProbe(const tp::Config&){if(providerCase.rfind(L"activation-",0)!=0)return;AddVectoredExceptionHandler(1,activationFault);rootPrepareMachine();
 auto&e=*new ActivationExercise;activationExercise=&e;auto&t=e.t;t.image=base;t.state=layout.config.states[4];t.worker=alloc(4096)+8;t.callable=t.worker+0x100;t.object=t.worker+0x200;
 auto m=base+0x19E7310,arr=at<uintptr_t>(m+0x20);for(unsigned i=0;i<at<unsigned>(m+0x10);++i)if(at<uintptr_t>(arr+i*8)==t.state)t.slot=arr+i*8;
 t.ready=CreateEventW(nullptr,FALSE,FALSE,nullptr);t.done=CreateEventW(nullptr,TRUE,TRUE,nullptr);e.initial=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 put<uintptr_t>(t.worker+8,t.object);put<uintptr_t>(t.worker+0x10,t.object+0x100);put<uintptr_t>(t.worker+0x50,t.callable);put<DWORD>(t.worker+0x58,1);put<uintptr_t>(t.worker+0x68,uintptr_t(t.done));put<DWORD>(t.worker+0x70,1);
 put<uintptr_t>(base+0x12F2440,uintptr_t(&activationCopy));parentJump(0x160F0,uintptr_t(&activationSwap));put<uintptr_t>(t.callable,base+0x12F2440);put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(t.callable+8,t.worker+0x300);put<uintptr_t>(t.worker+0x300,t.slot);put<std::uint64_t>(t.callable+16,11);put<std::uint64_t>(t.callable+24,22);put<std::uint64_t>(t.callable+32,33);
 put<uintptr_t>(t.object+0x20,uintptr_t(t.ready));put<uintptr_t>(t.object+0x30,t.worker+8);put<uintptr_t>(t.object+0x38,base+0x834D10);put<DWORD>(t.object+8,2);
 put<uintptr_t>(base+0x123C1D8,uintptr_t(&activationSet));put<uintptr_t>(base+0x123C1E0,uintptr_t(&activationWait));
 const auto vt=at<uintptr_t>(t.state);DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,PAGE_READWRITE,&old),"owned activation business callbacks writable");put<uintptr_t>(vt+0x28,uintptr_t(&activationBusiness));put<uintptr_t>(vt+0x30,uintptr_t(&activationStatus));check(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,old,&old),"owned callback protection restored");
 boundRequire(act::Initialize({base,&provider,1000})&&act::PublishIat(),"real IAT owner initialized and atomically published");
 e.handle=CreateThread(nullptr,0,activationEntry,nullptr,CREATE_SUSPENDED,&e.tid);boundRequire(e.handle!=nullptr,"owned generic worker constructed");t.workerTid=e.tid;put<DWORD>(t.object+0x10,e.tid);put<uintptr_t>(t.object+0x18,uintptr_t(e.handle));boundRequire(ResumeThread(e.handle)!=DWORD(-1)&&WaitForSingleObject(e.initial,10000)==WAIT_OBJECT_0,"worker has reached its initial wait service");
 const unsigned tasks=providerCase==L"activation-two-tasks"?2:1;
 for(unsigned i=0;i<tasks;++i){
  actualParentPort(&t);act::Report r{};const auto deadline=GetTickCount64()+10000;
  do {act::Snapshot(r);if(providerCase==L"activation-wrong-wait"||r.tasks[i].finished)break;Sleep(1);}while(GetTickCount64()<deadline);
  if(providerCase==L"activation-wrong-wait"){check(r.error==act::Error::Wait&&!r.initialWaitVerified&&!r.gateEntries&&!e.bodies,"already/non-native wait refused without worker publication or captures");break;}
  check(r.taskCount==i+1&&r.tasks[i].finished&&r.tasks[i].ports.restored&&!r.tasks[i].ports.uncertain,"automatic task source drained before next reuse");
  check(r.tasks[i].ports.captured==(providerCase==L"activation-exception"?1u:3u),"actual auto Root capture count");
 }
 if(providerCase!=L"activation-exception"&&providerCase!=L"activation-wrong-wait"){put<DWORD>(t.worker+0x5c,1);SetEvent(t.ready);}
 boundRequire(WaitForSingleObject(e.handle,10000)==WAIT_OBJECT_0,"owned long-lived generic runner drained");CloseHandle(e.handle);CloseHandle(e.initial);CloseHandle(t.ready);CloseHandle(t.done);
 act::Report r{};act::Snapshot(r);if(providerCase!=L"activation-wrong-wait")check(r.initialWaitVerified==1&&r.threads==1&&r.outerBefore==1&&r.outerFinally==1&&r.gateEntries==tasks&&r.gateFinishes==tasks&&e.bodies==tasks,"one published long-lived runner activates each immutable task automatically");
 if(providerCase==L"activation-exception")check(e.abnormal&&r.tasks[0].abnormal&&r.tasks[0].ports.providerScopeAbandoned==1,"real PE outer FINALLY abandons exceptional Root task");
 if(providerCase==L"activation-two-tasks")check(r.error==act::Error::None&&r.tasks[0].ports.accepted[2]==1&&r.tasks[1].ports.accepted[2]==1,"same native runner observes both task completions without direct fixture Begin");
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"automatic_root_activation\":true,\"registered_tasks\":%u,\"root_bodies\":%u,\"gate_entries\":%u,\"gate_finishes\":%u,\"initial_wait_verified\":%u,\"outer_entries\":%u,\"outer_finally\":%u,\"activation_error\":%u,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",failures,r.taskCount,e.bodies,r.gateEntries,r.gateFinishes,r.initialWaitVerified,r.outerBefore,r.outerFinally,unsigned(r.error));fflush(stdout);ExitProcess(failures?1:0);
}
