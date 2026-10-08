// Independent Root source exercise. Begin/configuration and engine business
// remain fixture services; root entry/return/done are never constructed Capture.
namespace rootports=b_reload_root_worker_ports;
struct RootExercise {StatePort* task=nullptr;rootports::Context ports{};unsigned bodies=0,before=0,after=0,finally=0;bool begun=false,abnormal=false;};
static thread_local RootExercise* rootExercise=nullptr;
static unsigned rootTotalBodies=0,rootCaptured=0;
static uintptr_t rootStatus(){return rootExercise?0:parentStatus();}
static void rootSync(void*){}
static BOOL rootSetEvent(HANDLE event){if(rootExercise&&event==rootExercise->task->done){
 // Done context occurs immediately before this actual archived IAT call.
 // Only now may the fixture stop the looping runner and wake the real parent.
 put<DWORD>(rootExercise->task->worker+0x5C,1);put<std::uint64_t>(base+0x19E7310+0x30,1);
 SetEvent(rootExercise->task->ready);
 }return SetEvent(event);}
static std::uint64_t rootUpdate(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
 check(rootExercise&&self==rootExercise->task->state&&a==11&&b==22&&c==33,"archived thunk forwards actual state and integer args");
 ++rootExercise->bodies;++rootTotalBodies;
 if(providerCase==L"root-native-exception")RaiseException(0xE014CF01,0,0,nullptr);
 return 0x12345678;
}
static void rootBefore(const CheckpointLoadWorkerFrame*f,void*){
 check(rootExercise&&f->args[0]==rootExercise->task->object&&f->args[1]==rootExercise->task->worker+8,"PE bridge receives real runner args");++rootExercise->before;
 rootExercise->begun=rootports::Begin(rootExercise->ports);
 if(!rootExercise->begun)RaiseException(0xE014CF02,0,0,nullptr);
}
static void rootAfter(const CheckpointLoadWorkerFrame*f,void*){++rootExercise->after;check(f->result_rax==0,"archived runner returns its real zero result");}
static void rootFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*x,void*){++rootExercise->finally;rootExercise->abnormal=x->abnormal!=0;if(rootExercise->begun)rootports::Finish(rootExercise->ports);}
static void rootPrepareMachine(){
 DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x50B000),4096,PAGE_READWRITE,&old),"owned Root thunk page writable");
 memcpy(reinterpret_cast<void*>(base+0x50B730),b_reload_root_worker_profile::ThunkBytes,sizeof b_reload_root_worker_profile::ThunkBytes);
 memcpy(reinterpret_cast<void*>(base+0x50B690),b_reload_root_worker_profile::YieldBytes,sizeof b_reload_root_worker_profile::YieldBytes);
 check(VirtualProtect(reinterpret_cast<void*>(base+0x50B000),4096,old,&old),"Root code page protection restored");
 check(FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+0x50B000),4096),"Root instruction cache refreshed");
 // Exact original thunk prolog: three saved registers, push rdi, sub rsp,20.
 const unsigned char thunkUnwind[]={1,0x14,8,0,0x14,0x32,0x10,0x70,0x0f,0x64,8,0,0x0a,0x54,7,0,5,0x34,6,0};
 const unsigned char yieldUnwind[]={1,6,2,0,6,0x32,2,0x30};
 memcpy(reinterpret_cast<void*>(base+0xB00),thunkUnwind,sizeof thunkUnwind);memcpy(reinterpret_cast<void*>(base+0xB40),yieldUnwind,sizeof yieldUnwind);
 auto*table=new RUNTIME_FUNCTION[2]{{0x50B690,0x50B6FF,0xB40},{0x50B730,0x50B79A,0xB00}};
 check(parentAddFunctions(table,2,base),"nonoverlapping actual Root thunk/yield unwind registered");
 for(auto rva:{0x50B782u,0x834D98u}){DWORD64 imageBase=0;auto*e=RtlLookupFunctionEntry(base+rva,&imageBase,nullptr);check(e&&imageBase==base&&e->BeginAddress==(rva==0x50B782?0x50B730u:0x834D10u),"Windows unwind selects real thunk and runner");}
 put<uintptr_t>(base+0x123C1D8,uintptr_t(&rootSetEvent));put<uintptr_t>(base+0x123C1E0,uintptr_t(&WaitForSingleObject));put<uintptr_t>(base+0x123C328,uintptr_t(&rootSync));put<uintptr_t>(base+0x123C0D8,uintptr_t(&rootSync));
 CheckpointLoadWorkerBridgeConfig cfg{};cfg.original=reinterpret_cast<void*>(base+0x834D10);cfg.before=rootBefore;cfg.after=rootAfter;cfg.finally=rootFinally;
 check(CheckpointLoadWorkerBridgeConfigure(1,&cfg),"independent exercise owns unused retained PE runner bridge slot");
}
static void rootProbe(const tp::Config&cfg){
 if(providerCase.rfind(L"root-",0)!=0)return;
 rootPrepareMachine();const unsigned iterations=providerCase==L"root-two-tasks"?2:1;
 for(unsigned n=0;n<iterations;++n){
  auto&e=*new RootExercise;auto state=layout.config.states[4];e.task=prepareState(state);rootExercise=&e;
  put<std::uint64_t>(e.task->callable+16,11);put<std::uint64_t>(e.task->callable+24,22);put<std::uint64_t>(e.task->callable+32,33);
  // The archived status caller and Update are real; their state business is a double.
  const auto vt=at<uintptr_t>(state);DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,PAGE_READWRITE,&old),"owned state callbacks writable");put<uintptr_t>(vt+0x28,uintptr_t(&rootUpdate));put<uintptr_t>(vt+0x30,uintptr_t(&rootStatus));check(VirtualProtect(reinterpret_cast<void*>(vt+0x28),16,old,&old),"state callback protection restored");
  rootports::Config c{&provider,base,{cfg.generation.callbacks.id,cfg.generation.attempt,cfg.generation.epoch},e.task->worker,e.task->callable,e.task->object,GetCurrentThreadId(),1000};
  if(providerCase==L"root-wrong-binding")++c.binding.epoch;
  if(providerCase==L"root-code-drift"){check(VirtualProtect(reinterpret_cast<void*>(base+0x50B730),1,PAGE_READWRITE,&old),"owned drift page writable");*reinterpret_cast<BYTE*>(base+0x50B730)^=1;check(VirtualProtect(reinterpret_cast<void*>(base+0x50B730),1,old,&old),"owned drift protection restored");}
  const bool initialized=rootports::Initialize(e.ports,c);
  if(providerCase==L"root-wrong-binding"||providerCase==L"root-code-drift"){
   check(!initialized,"invalid binding/code refused before observation begins");
   // No native worker body runs; release only the fixture parent as yielded.
   put<DWORD>(e.task->worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(e.task->done);
  }else{
   check(initialized,"immutable Root source context initialized");
   if(providerCase==L"root-old-worker-new-current"){auto next=cfg;++next.generation.callbacks.id;++next.generation.attempt;++next.generation.epoch;check(provider.Register(next),"new bank registered before old worker");boundSwitchAndWait(provider,next.generation.callbacks.id);}
   if(providerCase==L"root-stop-before-entry")rootports::Stop(e.ports);
   bool caught=false;__try{CheckpointLoadWorkerBridge1(e.task->object,e.task->worker+8,0,0);}
   __except(GetExceptionCode()==0xE014CF01||GetExceptionCode()==0xE014CF02?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
   const bool abnormal=providerCase==L"root-native-exception"||providerCase==L"root-stop-before-entry";
   check(caught==abnormal&&e.abnormal==abnormal&&e.before==1&&e.finally==1&&e.after==unsigned(!abnormal),"actual PE normal/exceptional outcome preserved");
   rootports::Report r{};check(rootports::Snapshot(e.ports,r),"retained Root source report");
   if(providerCase==L"root-stop-before-entry")check(!e.bodies&&!r.captured&&r.stopped&&r.error==rootports::Error::Stopped,"stopped observation invokes no native runner");
   else{
    check(r.finished&&r.restored&&!r.uncertain&&r.codeUnchanged&&!memcmp(r.originalDr,r.restoredDr,sizeof r.originalDr),"Root observation restores all six DR on real PE FINALLY");
    check(r.captured==(abnormal?1u:3u)&&r.accepted[0]==1&&r.accepted[1]==unsigned(!abnormal)&&r.accepted[2]==unsigned(!abnormal)&&!r.yields,"actual root entry/return/done points, no claimed yield");
    check(e.bodies==1&&(abnormal?r.providerScopeAbandoned==1:r.error==rootports::Error::None),"exact task entry active through body and normal/abnormal release");
    rootCaptured+=r.captured;
   }
   if(abnormal){put<DWORD>(e.task->worker+0x78,1);put<std::uint64_t>(base+0x19E7310+0x30,1);SetEvent(e.task->done);}
  }
  boundRequire(WaitForSingleObject(e.task->parent,10000)==WAIT_OBJECT_0,"fixture parent drained after Root source exercise");CloseHandle(e.task->parent);CloseHandle(e.task->ready);CloseHandle(e.task->done);rootExercise=nullptr;
 }
 tp::Report p{};provider.Snapshot(cfg.generation.callbacks.id,p);CheckpointLoadWorkerBridgeStats stats{};CheckpointLoadWorkerBridgeSnapshot(1,&stats);
 check(!stats.active&&!stats.cleanup_faults,"runner PE bridge has no active or cleanup fault");
 const bool normal=providerCase==L"root-normal"||providerCase==L"root-two-tasks";
 if(normal)check(p.creations==iterations&&p.events==6*iterations&&p.error==tp::Error::None,"actual parent fresh/create/complete and Root entry/return/done agree");
 if(providerCase==L"root-old-worker-new-current"){tp::Report newer{};provider.Snapshot(cfg.generation.callbacks.id+1,newer);check(p.creations==1&&p.events==5&&!newer.events&&!newer.creations,"old worker stays old, while stale parent completion is refused");}
 if(!normal&&providerCase!=L"root-old-worker-new-current")check(p.creations==1&&p.events==(providerCase==L"root-native-exception"?3u:2u),"rejected or exceptional Root has no return/done/completion receipt");
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"actual_root_worker_context\":%s,\"root_bodies\":%u,\"root_captures\":%u,\"tasks\":%llu,\"provider_events\":%llu,\"provider_error\":%u,\"root_activation_is_fixture\":true,\"nested_load_ports_composed\":false,\"game_access\":false}\n",providerCase.c_str(),failures?"false":"true",failures,rootCaptured?"true":"false",rootTotalBodies,rootCaptured,p.creations,p.events,unsigned(p.error));fflush(stdout);ExitProcess(failures?1:0);
}
