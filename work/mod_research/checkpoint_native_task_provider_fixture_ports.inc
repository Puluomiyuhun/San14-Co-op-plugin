// Native source ports and native lifecycle bodies are explicit owned-memory
// doubles. The provider reads them itself; no successful core receipt is forged.
namespace tp=checkpoint_native_task_provider;
static tp::Provider provider;
static uintptr_t lateOriginalSelf=0,auxCallable=0;
static unsigned lateOriginalCalls=0,auxBodies=0;
static bool omitJoin[3]{};
static tp::Capture capture(uintptr_t image,uintptr_t rva){tp::Capture c{};c.rip=image+rva;c.thread=GetCurrentThreadId();return c;}
static void observe(tp::Capture c){const bool ok=provider.Observe(c);if(!ok){tp::Report r{};provider.Snapshot(generationIndex+2,r);printf("PORT fail rva=%llx err=%u exception=%lu\n",c.rip-base,unsigned(r.error),r.exception);}check(ok,"actual owned source port accepted");}
struct StatePort {
    uintptr_t image=0,state=0,worker=0,callable=0,slot=0,object=0;
    HANDLE ready=nullptr,done=nullptr,parent=nullptr;DWORD workerTid=0;bool abnormal=false;
};
static StatePort* lateTask=nullptr;
static DWORD WINAPI parentPort(void*p){
    auto&t=*static_cast<StatePort*>(p);uintptr_t sp[12]{};sp[8]=t.slot;
    auto c=capture(t.image,0x50B4B3);c.rsp=uintptr_t(sp);c.rdi=t.worker;observe(c);
    c.rip=t.image+0x50B598;observe(c);SetEvent(t.ready);
    WaitForSingleObject(t.done,INFINITE);
    put<uintptr_t>(t.state+0x50,0);if(t.abnormal)return 0;c=capture(t.image,0x50B632);c.rdi=t.worker;c.rsp=uintptr_t(sp);observe(c);return 0;
}
static StatePort* prepareState(uintptr_t self){
    auto*t=new StatePort;t->image=base;t->state=self;t->workerTid=GetCurrentThreadId();
    auto n=at<std::uint64_t>(base+0x19E7310+0x10);for(unsigned i=0;i<n;++i)if(at<uintptr_t>(stackArray+i*8)==self)t->slot=stackArray+i*8;
    check(t->slot!=0,"state really belongs to formal stack");
    t->worker=alloc(4096);t->callable=t->worker+0x100;t->object=t->worker+0x200;
    put<uintptr_t>(t->worker+8,t->object);put<DWORD>(t->object+0x10,t->workerTid);put<uintptr_t>(t->worker+0x50,t->callable);
    put<uintptr_t>(t->callable,base+0x12F2440);put<uintptr_t>(base+0x12F2440+0x10,base+0x50B730);put<uintptr_t>(t->callable+8,t->worker+0x300);put<uintptr_t>(t->worker+0x300,t->slot);
    put<uintptr_t>(self+0x50,t->worker);put<uintptr_t>(base+0x19E7310+0x48,self);
    t->ready=CreateEventW(nullptr,TRUE,FALSE,nullptr);t->done=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    t->parent=CreateThread(nullptr,0,parentPort,t,0,nullptr);check(t->parent&&WaitForSingleObject(t->ready,10000)==WAIT_OBJECT_0,"native parent source captured before worker entry");return t;
}
static void enterState(StatePort&t){uintptr_t sp[]={t.image+0x834D9B};auto c=capture(t.image,0x50B730);c.rcx=t.callable;c.rsp=uintptr_t(sp);observe(c);}
static void leaveState(StatePort&t,bool abnormal){
    if(abnormal){check(provider.Abnormal(),"abnormal native task releases exact old scope");t.abnormal=true;SetEvent(t.done);check(WaitForSingleObject(t.parent,10000)==WAIT_OBJECT_0,"abnormal parent remains uncompleted but leaves fixture thread");CloseHandle(t.parent);CloseHandle(t.ready);CloseHandle(t.done);return;}
    auto c=capture(t.image,0x834D9B);c.rbx=t.worker+8;c.rdi=t.object;observe(c);
    put<DWORD>(t.worker+0x58,1);c.rip=t.image+0x834DB4;observe(c);SetEvent(t.done);
    check(WaitForSingleObject(t.parent,10000)==WAIT_OBJECT_0,"native state parent joined");CloseHandle(t.parent);CloseHandle(t.ready);CloseHandle(t.done);
}
using Invoke=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
static std::uint64_t runState(Invoke fn,std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
    auto*t=prepareState(uintptr_t(self));put<std::uint64_t>(t->callable+16,a);put<std::uint64_t>(t->callable+24,b);put<std::uint64_t>(t->callable+32,c);enterState(*t);std::uint64_t result=0;
    __try {result=fn(self,a,b,c);}__finally{leaveState(*t,AbnormalTermination()!=FALSE);}return result;
}
static std::uint64_t routedUser(std::uint64_t s,std::uint64_t a,std::uint64_t b,std::uint64_t c){return runState(GuestSessionUserInvoke,s,a,b,c);}
static std::uint64_t routedMenu(std::uint64_t s,std::uint64_t a,std::uint64_t b,std::uint64_t c){return runState(GuestSessionMenuInvoke,s,a,b,c);}
static std::uint64_t routedGame(std::uint64_t s,std::uint64_t a,std::uint64_t b,std::uint64_t c){return runState(GuestSessionGameInvoke,s,a,b,c);}
static std::uint64_t routedLoad(std::uint64_t s,std::uint64_t a,std::uint64_t b,std::uint64_t c){return runState(GuestSessionUpdateInvoke,s,a,b,c);}
struct EmbeddedPort {unsigned role=0;uintptr_t image=0,owner=0,control=0,callable=0,object=0;HANDLE handle=nullptr;DWORD tid=0;bool abnormal=false;};
static EmbeddedPort* embeddedPorts[3]{};
static DWORD WINAPI embeddedEntry(void*p){auto&t=*static_cast<EmbeddedPort*>(p);
    put<DWORD>(t.control+0x50,0);auto c=capture(t.image,0x834D98);c.rcx=t.callable;c.rbx=t.control;c.rdi=t.object;observe(c);
    c.rip=t.image+(t.role==0?0x508B40:t.role==1?0x4DA390:0x466600);observe(c);
    __try {invokeWorker(t.callable);}
    __except(GetExceptionCode()==0xE014CC91||GetExceptionCode()==0xE014CC92||GetExceptionCode()==0xE014CC93?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){t.abnormal=true;provider.Abnormal();return 1;}
    c.rip=t.image+0x834D9B;observe(c);put<DWORD>(t.control+0x50,1);c.rip=t.image+0x834DB4;observe(c);return 0;
}
static EmbeddedPort* startEmbedded(unsigned role){
    auto*t=new EmbeddedPort;embeddedPorts[role]=t;t->role=role;t->image=base;t->owner=role?title:load;
    t->control=t->owner+(role==0?0x478:role==1?0x520:0x590);t->callable=role==0?loadCallable:role==1?titleCallable:auxCallable;t->object=alloc(4096);
    t->handle=CreateThread(nullptr,0,embeddedEntry,t,CREATE_SUSPENDED,&t->tid);check(t->handle!=nullptr,"actual separate embedded thread created");
    put<uintptr_t>(t->control,t->object);put<uintptr_t>(t->control+8,t->object+0x100);put<uintptr_t>(t->control+0x48,t->callable);put<DWORD>(t->control+0x50,1);put<uintptr_t>(t->control+0x60,uintptr_t(t->handle));put<DWORD>(t->object+0x10,t->tid);put<uintptr_t>(t->object+0x20,uintptr_t(t->handle));
    uintptr_t sp[]={base+(role==0?0x4DA2F4:role==1?0x4BEEC2:0x4BEF2B)};auto c=capture(base,0x834B60);c.rcx=t->control;c.rsp=uintptr_t(sp);observe(c);
    check(ResumeThread(t->handle)!=DWORD(-1),"embedded worker starts after source receipt");return t;
}
static void joinEmbedded(unsigned role){auto&t=*embeddedPorts[role];check(WaitForSingleObject(t.handle,10000)==WAIT_OBJECT_0,"real OS embedded join");CloseHandle(t.handle);t.handle=nullptr;
    put<uintptr_t>(t.control,0);put<uintptr_t>(t.control+8,0);put<uintptr_t>(t.control+0x60,0);
    if(!omitJoin[role]){auto c=capture(t.image,role==0?0x4F7079:role==1?0x4AAF64:0x4AAF89);c.rbx=t.owner;observe(c);}
}
static void bindLoadPort(){auto c=capture(base,0x4DA240);c.rcx=load;observe(c);}
static void callbackPort(){uintptr_t sp[]={base+0x497134};auto c=capture(base,0x4CC690);c.rcx=title;c.rdx=load;c.rsp=uintptr_t(sp);observe(c);}
