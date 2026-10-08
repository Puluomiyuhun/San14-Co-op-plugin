static SRWLOCK producer=SRWLOCK_INIT;
static volatile LONG taskStarts=0;
static checkpoint_native_task_provider::Provider provider;
static HANDLE held=nullptr,releaseHolder=nullptr;
static const char* caseName=nullptr;
static DWORD WINAPI holdManager(void*){EnterCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90));SetEvent(held);WaitForSingleObject(releaseHolder,INFINITE);LeaveCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90));return 0;}
static DWORD WINAPI releaseLater(void*){Sleep(150);
 if(!strcmp(caseName,"stop-during"))b_reload_root_activation::Stop();
 if(!strcmp(caseName,"source-drift")){unsigned char bad=0xcc;require(span(0x834D10,&bad,1,PAGE_EXECUTE_READ),"owned source drift");return 0;}
 if(!strcmp(caseName,"iat-drift")){const auto p=uintptr_t(GetProcAddress(GetModuleHandleW(L"kernel32.dll"),"LeaveCriticalSection"));require(span(0x123C0D8,&p,8,PAGE_READONLY),"owned IAT drift");return 0;}
 SetEvent(releaseHolder);return 0;
}
int main(int argc,char**argv){require(argc==2,"case argument");caseName=argv[1];require(ownedPrepare(uintptr_t(GetModuleHandleW(nullptr))),"owned preparation");
 using namespace b_reload_cold_registration;
 const bool deadline=!strcmp(caseName,"deadline"),success=!strcmp(caseName,"delayed"),stopped=!strcmp(caseName,"stop-before")||!strcmp(caseName,"stop-during"),outside=!strcmp(caseName,"outside-owner");
 require(Prepare({ownedBase,&provider,1000},{&producer,&taskStarts,uintptr_t(&ownedEntry),deadline?40u:2000u}),"prepare same actual Provider lifecycle");
 b_reload_lifecycle::Plan plan{};require(b_reload_lifecycle::PreparedPlan(plan)&&span(0x1447B6,plan.after,5,PAGE_EXECUTE_READ)&&b_reload_lifecycle::Arm(),"publish source and Arm exactly once");
 const auto publishedIat=at<uintptr_t>(ownedBase+0x123C0D8);require(publishedIat==uintptr_t(&BReloadRootActivationBridge0),"real activation IAT installed");
 if(outside)require(!Register(nullptr),"outside actual owner rejected");
 if(!strcmp(caseName,"task-started"))InterlockedIncrement(&taskStarts);
 if(!strcmp(caseName,"stop-before"))b_reload_root_activation::Stop();
 held=CreateEventW(nullptr,TRUE,FALSE,nullptr);releaseHolder=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 const auto holder=CreateThread(nullptr,0,holdManager,nullptr,0,nullptr);require(holder&&WaitForSingleObject(held,3000)==WAIT_OBJECT_0,"manager held");
 HANDLE helper=nullptr;if(!deadline)helper=CreateThread(nullptr,0,releaseLater,nullptr,0,nullptr);
 reinterpret_cast<void(*)(uintptr_t)>(ownedBase+0x1447B2)(ownedBase+0x1A24DA0);
 const auto r=Snapshot();b_reload_lifecycle::Report life{};b_reload_lifecycle::Snapshot(life);b_reload_root_activation::Report a{};b_reload_root_activation::Snapshot(a);
 require(ownedConstructed==4&&r.prepared&&r.attempts==1&&r.provider==uintptr_t(&provider)&&r.base==ownedBase&&life.entered==1&&life.finally==1&&!life.abnormal,"same actual lifecycle and Provider");
 require(r.wait.suspends==r.wait.resumes&&!r.wait.uncertain,"all own suspension increments restored");
 if(success){require(r.error==Error::None&&r.oldCalls==1&&r.registered==1&&r.wait.initialWaitVerified==4&&r.wait.pending&&a.threads==4&&a.initialWaitVerified==4&&life.returned==1&&life.coldPools==1&&life.error==b_reload_lifecycle::Error::None,"actual original registration succeeds after delayed cold wait");}
 else {require(r.error!=Error::None&&!r.registered&&!life.coldPools&&!a.threads&&!life.returned&&life.error==b_reload_lifecycle::Error::Activation,"failed wait/registration cannot claim old pool");require(r.oldCalls==unsigned(stopped),"only stopping reaches actual original refusal");}
 using WaitError=b_reload_cold_registration_wait::Error;
 if(deadline)require(r.error==Error::Wait&&r.wait.error==WaitError::Deadline&&r.wait.pending&&!r.wait.callbackCalls,"exact deadline refusal after actual pending");
 if(!strcmp(caseName,"source-drift")||!strcmp(caseName,"iat-drift"))require(r.error==Error::Wait&&r.wait.error==WaitError::Source&&r.wait.pending&&!r.wait.callbackCalls,"exact source drift refusal after actual pending");
 if(!strcmp(caseName,"task-started"))require(r.error==Error::Wait&&r.wait.error==WaitError::TaskStarted&&!r.wait.suspends&&!r.wait.callbackCalls,"exact task started refusal");
 if(outside)require(r.error==Error::Owner&&!r.wait.attempts&&!r.oldCalls,"exact owner refusal before coordination");
 if(stopped)require(r.error==Error::Registration&&r.wait.error==WaitError::Callback&&r.wait.callbackCalls==1&&r.wait.initialWaitVerified==4&&r.oldCalls==1&&a.error==b_reload_root_activation::Error::None,"actual original stop refusal after four exact waits");
 require(!Register(nullptr)&&!memcmp(&r,&Snapshot(),sizeof r),"second call refused without old claim retry");
 if(helper){require(WaitForSingleObject(helper,3000)==WAIT_OBJECT_0,"helper done");CloseHandle(helper);}
 if(!strcmp(caseName,"source-drift"))require(span(0x834D10,b_reload_root_worker_profile::RunnerBytes,sizeof b_reload_root_worker_profile::RunnerBytes,PAGE_EXECUTE_READ),"restore owned diagnostic source");
 if(!strcmp(caseName,"iat-drift"))require(span(0x123C0D8,&publishedIat,8,PAGE_READONLY),"restore owned diagnostic IAT");
 SetEvent(releaseHolder);require(WaitForSingleObject(holder,3000)==WAIT_OBJECT_0,"manager holder exit");CloseHandle(holder);CloseHandle(held);CloseHandle(releaseHolder);
 for(auto&w:ownedWorkers){put<DWORD>(w.control+0x54,1);SetEvent(w.ready);}
 unsigned exits=0,locks=0;for(auto&w:ownedWorkers){require(WaitForSingleObject(w.thread,3000)==WAIT_OBJECT_0,"native worker exit");DWORD code=99;require(GetExitCodeThread(w.thread,&code)&&!code,"worker exit0");++exits;auto*cs=reinterpret_cast<CRITICAL_SECTION*>(w.object+0x110);require(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"worker CS balanced");LeaveCriticalSection(cs);DeleteCriticalSection(cs);++locks;CloseHandle(w.thread);CloseHandle(w.ready);CloseHandle(w.done);CloseHandle(w.initial);}
 for(auto*cs:{reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90),reinterpret_cast<CRITICAL_SECTION*>(ownedCounter+0x10)}){require(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"global CS balanced");LeaveCriticalSection(cs);DeleteCriticalSection(cs);++locks;}
 b_reload_root_activation::Snapshot(a);if(success)require(a.outerBefore==4&&a.outerFinally==4&&a.error==b_reload_root_activation::Error::None&&!a.uncertain,"actual four activation outer FINALLY");
 require(at<uintptr_t>(ownedBase+0x123C0D8)==publishedIat&&!memcmp(reinterpret_cast<void*>(plan.address),plan.after,5),"same once-published source/bridge remains");
 printf("{\"passed\":true,\"registration_error\":%u,\"old_calls\":%u,\"registered\":%u,\"cold_pools\":%u,\"wait_error\":%u,\"wait_verified\":%u,\"pending\":%u,\"suspends\":%u,\"resumes\":%u,\"initial_waits\":%u,\"outer_finally\":%u,\"worker_exits\":%u,\"balanced_locks\":%u}\n",unsigned(r.error),r.oldCalls,r.registered,life.coldPools,unsigned(r.wait.error),r.wait.initialWaitVerified,r.wait.pending,r.wait.suspends,r.wait.resumes,a.initialWaitVerified,a.outerFinally,exits,locks);return 0;
}
