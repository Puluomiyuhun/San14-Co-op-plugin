static SRWLOCK producer=SRWLOCK_INIT;
static volatile LONG taskStarts=0;
static HANDLE holderReady=nullptr,holderRelease=nullptr;
static bool holdProducer=false;
static HANDLE replacementEvent=nullptr;
static DWORD WINAPI holder(void*){if(holdProducer)AcquireSRWLockShared(&producer);else EnterCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90));SetEvent(holderReady);WaitForSingleObject(holderRelease,INFINITE);if(holdProducer)ReleaseSRWLockShared(&producer);else LeaveCriticalSection(reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90));return 0;}
static DWORD WINAPI delayedRelease(void*){Sleep(150);if(replacementEvent)InterlockedExchangePointer(reinterpret_cast<void*volatile*>(ownedWorkers[0].object+0x20),replacementEvent);else SetEvent(holderRelease);return 0;}
static unsigned callbacks=0;
static bool rejectCallback=false;
static bool continuation(void*) noexcept {++callbacks;const bool acquired=TryAcquireSRWLockShared(&producer)!=FALSE;if(acquired)ReleaseSRWLockShared(&producer);return !acquired&&!rejectCallback;}
static void waitCold(){for(auto&w:ownedWorkers)require(WaitForSingleObject(w.initial,3000)==WAIT_OBJECT_0,"worker reached wait service");}
int main(int argc,char**argv){require(argc==2,"case");const char*name=argv[1];const bool delay=!strcmp(name,"delayed"),deadline=!strcmp(name,"deadline"),eventSet=!strcmp(name,"event-set"),busy=!strcmp(name,"producer-busy"),handleChanged=!strcmp(name,"handle-changed");
 require(ownedPrepare(uintptr_t(GetModuleHandleW(nullptr))),"owned source preparation");
 HANDLE holderThread=nullptr,releaser=nullptr;
 if(delay||deadline||eventSet||busy||handleChanged){holdProducer=busy;holderReady=CreateEventW(nullptr,TRUE,FALSE,nullptr);holderRelease=CreateEventW(nullptr,TRUE,FALSE,nullptr);holderThread=CreateThread(nullptr,0,holder,nullptr,0,nullptr);require(holderThread&&WaitForSingleObject(holderReady,3000)==WAIT_OBJECT_0,"owned lock held");}
 reinterpret_cast<void(*)(uintptr_t)>(ownedBase+0x509580)(ownedBase+0x1A24DA0);require(ownedConstructed==4,"four workers constructed without wait");
 if(delay||deadline||eventSet||handleChanged)Sleep(30);else waitCold();
 b_reload_cold_wait::Config c{};c.base=ownedBase;c.producerLock=&producer;c.taskStarts=&taskStarts;c.deadlineMs=(deadline||busy)?40:2000;
 for(unsigned i=0;i<4;++i){auto&w=ownedWorkers[i];c.workers[i]={uintptr_t(w.object),w.control,w.tid,uintptr_t(&ownedEntry)};}
 using Error=b_reload_cold_wait::Error;Error expected=Error::None;
 if(handleChanged){replacementEvent=CreateEventW(nullptr,FALSE,FALSE,nullptr);expected=Error::Binding;}
 if(delay||handleChanged)releaser=CreateThread(nullptr,0,delayedRelease,nullptr,0,nullptr);
 if(deadline||busy)expected=Error::Deadline;
 if(!strcmp(name,"source")){c.workers[0].threadStart=uintptr_t(&holder);expected=Error::Source;}
 if(!strcmp(name,"warm")){auto&w=ownedWorkers[0];ResetEvent(w.initial);ResetEvent(w.done);SetEvent(w.ready);require(WaitForSingleObject(w.done,3000)==WAIT_OBJECT_0&&WaitForSingleObject(w.initial,3000)==WAIT_OBJECT_0,"execute one ordinary native task");require(ownedBodies==1,"native body executed");expected=Error::Warm;}
 if(!strcmp(name,"task-started")){InterlockedIncrement(&taskStarts);expected=Error::TaskStarted;}
 if(eventSet){SetEvent(ownedWorkers[0].ready);expected=Error::Event;}
 if(!strcmp(name,"callback-refused")){rejectCallback=true;expected=Error::Callback;}
 const bool prior=!strcmp(name,"prior-suspended");if(prior){require(SuspendThread(ownedWorkers[0].thread)==0,"owned prior suspend");expected=Error::Thread;}
 if(!strcmp(name,"binding")){c.workers[0].control+=8;expected=Error::Binding;}
 // A valid self-created thread with unreviewed entry/context must not be pending.
 HANDLE unknownThread=nullptr,unknownEvent=nullptr;unsigned char unknownObject[0x80]{},unknownControl[0x80]{};
 if(!strcmp(name,"unknown-context")){unknownEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);holderReady=CreateEventW(nullptr,TRUE,FALSE,nullptr);holderRelease=unknownEvent;holdProducer=false;DWORD tid=0;unknownThread=CreateThread(nullptr,0,holder,nullptr,0,&tid);require(unknownThread&&WaitForSingleObject(holderReady,3000)==WAIT_OBJECT_0,"unknown context ready");auto o=uintptr_t(unknownObject),k=uintptr_t(unknownControl);put<DWORD>(o+0x10,tid);put<uintptr_t>(o+0x18,uintptr_t(unknownThread));auto ev=CreateEventW(nullptr,FALSE,FALSE,nullptr);put<uintptr_t>(o+0x20,uintptr_t(ev));put<uintptr_t>(o+0x30,k);put<uintptr_t>(o+0x38,ownedBase+0x834D10);put<uintptr_t>(k,o);put<DWORD>(k+0x50,1);c.workers[0]={o,k,tid,uintptr_t(&holder)};expected=Error::Context;}
 b_reload_cold_wait::Coordinator coordinator;const bool ok=coordinator.Run(c,continuation,nullptr);const auto r=coordinator.Snapshot();
 require(ok==(expected==Error::None)&&r.error==expected,"expected coordination result");require(r.attempts==1&&r.suspends==r.resumes&&!r.uncertain,"paired suspension restoration");require(r.callbackCalls==callbacks&&callbacks==unsigned(expected==Error::None||expected==Error::Callback),"exact callback count");
 require(!coordinator.Run(c,continuation,nullptr)&&!memcmp(&r,&coordinator.Snapshot(),sizeof r),"old attempt remains immutable");
 if(delay)require(r.pending>0&&r.rounds>1&&r.initialWaitVerified==4,"actual delayed contexts then initial waits");
 if(prior)require(ResumeThread(ownedWorkers[0].thread)==1,"external prior suspension preserved");
 if(handleChanged){put<uintptr_t>(uintptr_t(ownedWorkers[0].object)+0x20,uintptr_t(ownedWorkers[0].ready));CloseHandle(replacementEvent);replacementEvent=nullptr;}
 if(holderThread)SetEvent(holderRelease);if(releaser){require(WaitForSingleObject(releaser,3000)==WAIT_OBJECT_0,"release helper exit");CloseHandle(releaser);}if(holderThread){require(WaitForSingleObject(holderThread,3000)==WAIT_OBJECT_0,"holder exit");CloseHandle(holderThread);CloseHandle(holderReady);CloseHandle(holderRelease);}
 if(unknownThread){SetEvent(unknownEvent);require(WaitForSingleObject(unknownThread,3000)==WAIT_OBJECT_0,"unknown thread exit");CloseHandle(unknownThread);CloseHandle(unknownEvent);CloseHandle(holderReady);CloseHandle(reinterpret_cast<HANDLE>(at<uintptr_t>(uintptr_t(unknownObject)+0x20)));}
 // Original native entry has not been patched. Let every worker finish normally.
 for(auto&w:ownedWorkers){put<DWORD>(w.control+0x54,1);SetEvent(w.ready);}
 unsigned exits=0,locks=0;for(auto&w:ownedWorkers){require(WaitForSingleObject(w.thread,3000)==WAIT_OBJECT_0,"native worker exit");DWORD code=99;require(GetExitCodeThread(w.thread,&code)&&!code,"native worker exit code");++exits;auto*cs=reinterpret_cast<CRITICAL_SECTION*>(w.object+0x110);require(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"balanced worker CS");LeaveCriticalSection(cs);DeleteCriticalSection(cs);++locks;CloseHandle(w.thread);CloseHandle(w.ready);CloseHandle(w.done);CloseHandle(w.initial);}
 for(auto*cs:{reinterpret_cast<CRITICAL_SECTION*>(ownedManager+0x90),reinterpret_cast<CRITICAL_SECTION*>(ownedCounter+0x10)}){require(cs->RecursionCount==0&&TryEnterCriticalSection(cs),"balanced global CS");LeaveCriticalSection(cs);DeleteCriticalSection(cs);++locks;}
 printf("{\"passed\":true,\"error\":%u,\"rounds\":%u,\"pending\":%u,\"verified\":%u,\"suspends\":%u,\"resumes\":%u,\"callbacks\":%u,\"elapsed_ms\":%llu,\"worker_exits\":%u,\"balanced_locks\":%u,\"warm\":%u}\n",unsigned(r.error),r.rounds,r.pending,r.initialWaitVerified,r.suspends,r.resumes,r.callbackCalls,r.elapsedMs,exits,locks,r.warm[0]);return 0;
}
