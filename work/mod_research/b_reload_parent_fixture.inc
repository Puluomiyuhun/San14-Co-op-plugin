// Owned fixture dependencies. The whole native scheduler runs; storage/pool
// preparation and root worker business are explicit substitutes, not game AI.
static auto& parentSource=*new b_reload_parent_source::Owner;
static b_reload_parent_source::Plan parentPlan{};
static thread_local StatePort* parentTask=nullptr;
static thread_local uintptr_t parentTemporaryState=0;
static thread_local uintptr_t parentOtherStates[6]{},parentSavedWorkers[6]{};
static thread_local unsigned parentStateCount=0;
static unsigned parentQueueChecks=0;
static unsigned parentThrow=0;
static DWORD WINAPI actualParentPort(void*);
// Each range is registered separately. Overlapping enclosing ranges from
// disjoint arrays can make Windows stop at a table with no matching entry.
static bool parentAddFunctions(PRUNTIME_FUNCTION table,DWORD count,DWORD64 image){for(DWORD i=0;i<count;++i)if(!RtlAddFunctionTable(table+i,1,image))return false;return true;}
static LONG CALLBACK parentExceptionTrace(EXCEPTION_POINTERS*e){auto code=e->ExceptionRecord->ExceptionCode;if(code!=0xE014CE01&&code!=0xE014CE02)return EXCEPTION_CONTINUE_SEARCH;auto c=*e->ContextRecord;printf("TRACE exception=%lx\n",code);for(unsigned i=0;i<16&&c.Rip;++i){DWORD64 imageBase=0;auto*f=RtlLookupFunctionEntry(c.Rip,&imageBase,nullptr);printf("TRACE %u rip=%llx rva=%llx rsp=%llx unwind=%lx\n",i,c.Rip,c.Rip-base,c.Rsp,f?f->UnwindData:0);if(f){void*data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,imageBase,c.Rip,f,&c,&data,&frame,nullptr);}else {c.Rip=at<uintptr_t>(c.Rsp);c.Rsp+=8;}}fflush(stdout);return EXCEPTION_CONTINUE_SEARCH;}
static uintptr_t parentPool(){check(parentTask!=nullptr,"pool helper only inside owned parent");if(parentThrow==2)RaiseException(0xE014CE02,0,0,nullptr);return parentTask->worker-8;}
static uintptr_t parentPhaseService(){static unsigned char config[4096]{};*reinterpret_cast<DWORD*>(config+0x18C)=1;return uintptr_t(config);}
static uintptr_t parentStatus(){b_reload_parent_source::QueueOwner q{};check(b_reload_parent_source::Owner::CurrentQueueOwner(q)&&q.base==base&&q.manager==base+0x19E7310,"real queue phase owner precedes hardware phase");++parentQueueChecks;if(parentTemporaryState){put<uintptr_t>(parentTemporaryState,0);parentTemporaryState=0;}if(parentThrow==1)RaiseException(0xE014CE01,0,0,nullptr);return 1;}
static void parentBeforeWake(HANDLE h){if(parentTask&&h==parentTask->ready)for(unsigned i=0;i<parentStateCount;++i)if(parentOtherStates[i]!=parentTask->state)put<uintptr_t>(parentOtherStates[i]+0x50,parentSavedWorkers[i]);}
static void parentNoop(){}
static void parentJump(uintptr_t rva,uintptr_t target){unsigned char j[]={0x48,0xb8,0,0,0,0,0,0,0,0,0xff,0xe0};memcpy(j+2,&target,8);DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+rva),sizeof j,PAGE_READWRITE,&old),"owned helper writable");memcpy(reinterpret_cast<void*>(base+rva),j,sizeof j);check(VirtualProtect(reinterpret_cast<void*>(base+rva),sizeof j,PAGE_EXECUTE_READ,&old),"owned helper RX");}
static void prepareParentMachine(){
 if(!generationIndex){
  DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x509000),0x3000,PAGE_READWRITE,&old),"owned scheduler storage writable");
  memcpy(reinterpret_cast<void*>(base+0x509FE0),b_reload_parent_profile::SchedulerBytes,sizeof b_reload_parent_profile::SchedulerBytes);
  // Explicit fixture caller uses the actual direct call-site and its return;
  // it does not pretend to implement the rest of the game's 13Dxxx caller.
  const unsigned char head[]={0x48,0x83,0xec,0x28},tail[]={0x48,0x83,0xc4,0x28,0xc3};
  memcpy(reinterpret_cast<void*>(base+0x13DC05),head,4);memcpy(reinterpret_cast<void*>(base+0x13DC09),b_reload_parent_profile::OuterCall,5);memcpy(reinterpret_cast<void*>(base+0x13DC0E),tail,5);
  const unsigned char uw[]={1,0x28,11,0,0x28,0x34,0x37,0,0x18,1,0x2e,0,0x0c,0xf0,0x0a,0xe0,8,0xd0,6,0xc0,4,0x70,3,0x60,2,0x50,0,0};
  const unsigned char callerUw[]={1,4,1,0,4,0x42,0,0};
  memcpy(reinterpret_cast<void*>(base+0xA00),uw,sizeof uw);memcpy(reinterpret_cast<void*>(base+0xA40),callerUw,sizeof callerUw);
  auto*table=new RUNTIME_FUNCTION[2]{{0x13DC05,0x13DC13,0xA40},{0x509FE0,0x50B690,0xA00}};check(parentAddFunctions(table,2,base),"owned caller plus exact scheduler prologue unwind");
  check(VirtualProtect(reinterpret_cast<void*>(base+0x13D000),4096,PAGE_EXECUTE_READ,&old)&&VirtualProtect(reinterpret_cast<void*>(base+0x509000),0x3000,PAGE_EXECUTE_READ,&old),"archived scheduler and caller RX");
 }
 for(auto rva:{0x50A7A9u,0x50B4B8u}){DWORD64 imageBase=0;auto*entry=RtlLookupFunctionEntry(base+rva,&imageBase,nullptr);check(entry&&imageBase==base&&entry->BeginAddress==0x509FE0&&entry->EndAddress==0x50B690&&entry->UnwindData==0xA00,"Windows lookup selects exact scheduler runtime unwind in both generations");}
 // These helpers are outside the retained scheduler/call-site pages.
 parentJump(0x145B20,uintptr_t(&parentPool));parentJump(0xF570,uintptr_t(&parentPhaseService));
 {DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(base+0x834EF0),sizeof b_reload_parent_profile::WaitBytes,PAGE_READWRITE,&old),"owned wait storage writable");memcpy(reinterpret_cast<void*>(base+0x834EF0),b_reload_parent_profile::WaitBytes,sizeof b_reload_parent_profile::WaitBytes);check(VirtualProtect(reinterpret_cast<void*>(base+0x834EF0),sizeof b_reload_parent_profile::WaitBytes,old,&old),"owned wait RX");}
 put<uintptr_t>(base+0x12F2440+0x20,uintptr_t(&parentNoop));
 if(!generationIndex){
  check(parentSource.Initialize({base,&provider,1000}),"parent sources validate entire archived scheduler");check(parentSource.PreparedPlan(parentPlan),"parent exact two-call plan");
  if(providerCase==L"parent-stop-before-arm")parentSource.Stop();
  for(auto&p:parentPlan.patches){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(p.address),5,PAGE_READWRITE,&old),"owned fixture source writable");memcpy(reinterpret_cast<void*>(p.address),p.after,5);check(VirtualProtect(reinterpret_cast<void*>(p.address),5,old,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(p.address),5),"owned fixture exact source publication");}
  if(providerCase==L"parent-code-drift"||providerCase==L"parent-patch-drift"){auto address=providerCase==L"parent-code-drift"?base+0x509FE2:parentPlan.patches[1].address+1;DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(address),1,PAGE_READWRITE,&old),"owned drift target writable");*reinterpret_cast<BYTE*>(address)^=1;check(VirtualProtect(reinterpret_cast<void*>(address),1,old,&old),"owned drift target RX");}
  const bool refused=providerCase==L"parent-stop-before-arm"||providerCase==L"parent-code-drift"||providerCase==L"parent-patch-drift";
  check(parentSource.Arm()!=refused,"already installed parent call-site bytes admitted or safely refused");
  if(refused){b_reload_parent_source::Report report{};parentSource.Snapshot(report);check(!report.armed&&!report.scopes&&!report.active,"refused owner never starts captures");printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"parent_refused\":true,\"error\":%u}\n",providerCase.c_str(),failures?"false":"true",failures,unsigned(report.error));fflush(stdout);ExitProcess(failures?1:0);}
 }
}
static void parentExceptionProbe(unsigned phase){
 b_reload_parent_source::Report before{},after{};parentSource.Snapshot(before);auto m=base+0x19E7310,stack=at<uintptr_t>(m+0x20);StatePort task{};task.image=base;task.state=at<uintptr_t>(stack+(at<std::uint64_t>(m+0x10)-1)*8);task.worker=alloc(4096)+8;task.object=task.worker+0x200;task.ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);task.done=CreateEventW(nullptr,TRUE,FALSE,nullptr);parentThrow=phase;bool caught=false;AddVectoredExceptionHandler(1,parentExceptionTrace);
 __try {actualParentPort(&task);}__except(GetExceptionCode()==0xE014CE00+phase?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
 parentSource.Snapshot(after);check(caught&&after.error==b_reload_parent_source::Error::Exception&&after.scopes==before.scopes+1&&after.finally==before.finally+1&&after.abnormal==1&&!after.active&&!after.uncertain&&after.restored==before.restored+1,"actual archived scheduler exception crosses PE bridge FINALLY and restores");
 check(after.phaseStarted==before.phaseStarted+(phase==2)&&!memcmp(after.originalDr,after.restoredDr,sizeof after.originalDr),"queue exception never arms; worker exception restores exact prior debug state");
 CheckpointLoadWorkerBridgeStats stats{};BReloadParentBridgeSnapshot(0,&stats);check(stats.abnormal_exits==1&&!stats.active&&!stats.cleanup_faults&&stats.native_started==stats.native_returned+1,"native exception is not reported as normal returned");
 printf("{\"parent_exception_phase\":%u,\"caught\":%s,\"finally\":%u,\"restored\":%u,\"error\":%u}\n",phase,caught?"true":"false",after.finally,after.restored,unsigned(after.error));CloseHandle(task.ready);CloseHandle(task.done);
}
static DWORD WINAPI actualParentPort(void*p){
 auto&t=*static_cast<StatePort*>(p);parentTask=&t;
 // The pre-existing fixture root worker executes on its main thread. Its
 // callable/pool are owned doubles, while selection/assignment/completion are
 // now executed by unmodified 509FE0 and observed via real OS CONTEXT.
 auto m=base+0x19E7310;const auto n=at<std::uint64_t>(m+0x10),stack=at<uintptr_t>(m+0x20);
 parentStateCount=unsigned(n);for(unsigned i=0;i<n;++i){auto state=at<uintptr_t>(stack+i*8);parentOtherStates[i]=state;parentSavedWorkers[i]=at<uintptr_t>(state+0x50);if(state==t.state)put<uintptr_t>(state+0x50,0);else{auto dummy=alloc(4096);put<uintptr_t>(dummy+0x10,dummy+0x100);put<DWORD>(dummy+0x78,1);put<uintptr_t>(state+0x50,dummy);}}
 auto first=at<uintptr_t>(stack),vt=at<uintptr_t>(first);if(!vt){vt=alloc(4096);parentTemporaryState=first;put<uintptr_t>(first,vt);}DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(vt+0x30),8,PAGE_READWRITE,&old),"owned status slot writable");put<uintptr_t>(vt+0x30,uintptr_t(&parentStatus));check(VirtualProtect(reinterpret_cast<void*>(vt+0x30),8,old,&old),"owned status protection restored");
 put<uintptr_t>(t.object+0x20,uintptr_t(t.ready));put<uintptr_t>(t.worker+0x10,t.object+0x100);put<uintptr_t>(t.worker+0x68,uintptr_t(t.done));put<DWORD>(t.worker-8+0x208,0);put<std::uint64_t>(m+0x30,0);
 using Native=void(*)(uintptr_t,uintptr_t,uintptr_t,uintptr_t);
 reinterpret_cast<Native>(base+0x13DC05)(m,0,0,0);
 check(!at<uintptr_t>(m+0x48)&&!at<uintptr_t>(t.state+0x50),"native scheduler clears state worker and manager current");
 for(unsigned i=0;i<n;++i)if(parentOtherStates[i]!=t.state)put<uintptr_t>(parentOtherStates[i]+0x50,parentSavedWorkers[i]);
 put<std::uint64_t>(m+0x30,0);parentTask=nullptr;return 0;
}
