#include "checkpoint_task_attribution_core.h"
#include "checkpoint_persistent_route_six_adapter.h"
#include <cstdio>
#include <cstring>
#include <stdexcept>
namespace ta=checkpoint_task_attribution;namespace pr=checkpoint_persistent_route;
namespace {
ta::Core core;ta::Adapter attributed;pr::Router router;pr::SixAdapter six;
constexpr std::uint64_t base=0x140000000,answer=0xFEDCBA9876543210;
CheckpointLoadWorkerEntry entries[6]={CheckpointPersistentBridge0,CheckpointPersistentBridge1,CheckpointPersistentBridge2,CheckpointPersistentBridge3,CheckpointPersistentBridge4,CheckpointPersistentBridge5};
struct Counts{unsigned id;LONG before[6]{},after[6]{},finally[6]{},abnormal=0;};Counts counts[2]{{1},{2}};
volatile LONG errors=0,nativeCalls=0,caught=0;HANDLE beginEvent,doneEvent,readyEvent,goEvent,threadHandle;
DWORD workerThread=0;volatile LONG quit=0;const char* mode=nullptr;
ta::Ticket tickets[258];ta::Creation creation[258];
struct Command{unsigned ticket=0,slot=0,operation=0;bool enter=true,expectedEnter=true;std::uint64_t arg=0,serialOffset=0;}command;
void check(bool ok){if(!ok)InterlockedIncrement(&errors);}
void before(const CheckpointLoadWorkerFrame* f,void* p){auto& c=*static_cast<Counts*>(p);InterlockedIncrement(&c.before[f->slot]);
 if(f->slot==4)check(CheckpointPersistentClaim(f,100+c.id)==1);
 if(f->slot==5){CheckpointLoadWorkerOwner o{};check(CheckpointPersistentCurrentOwner(&o)==1&&o.token==100+c.id&&o.slot==4);}
 if(!strcmp(mode,"before-exception"))RaiseException(0xE014AA11,0,0,nullptr);
}
void after(const CheckpointLoadWorkerFrame* f,void* p){InterlockedIncrement(&static_cast<Counts*>(p)->after[f->slot]);}
void finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){auto& c=*static_cast<Counts*>(p);InterlockedIncrement(&c.finally[f->slot]);if(x->abnormal)InterlockedIncrement(&c.abnormal);}
std::uint64_t native(std::uint64_t,std::uint64_t op,std::uint64_t,std::uint64_t){
 InterlockedIncrement(&nativeCalls);
 if(op==1)check(entries[5](0x12345678,0,0,0)==answer);
 if(op==2)RaiseException(0xE014AA12,0,0,nullptr);
 if(op==3){SetEvent(readyEvent);check(WaitForSingleObject(goEvent,5000)==WAIT_OBJECT_0);}
 return answer;
}
DWORD invoke(unsigned slot,std::uint64_t arg,unsigned op){__try{check(entries[slot](arg,op,0,0)==answer);return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
ta::Entry entryFor(unsigned i){const auto& c=creation[i];ta::Entry e{};e.serial=c.serial;e.site=base+(unsigned(c.kind)>=4?0x4FABC0:0x50B730);e.caller=base+0x834D9B;e.state=c.state;e.worker=c.worker;e.callable=c.callable;e.thread=GetCurrentThreadId();return e;}
DWORD WINAPI worker(void*){
 for(;;){WaitForSingleObject(beginEvent,INFINITE);if(InterlockedCompareExchange(&quit,0,0))break;
   ta::Execution execution;bool active=false;
   if(command.enter){auto e=entryFor(command.ticket);e.serial+=command.serialOffset;active=core.Enter(tickets[command.ticket],e,execution);check(active==command.expectedEnter);}
   if(command.operation==4){check(core.RecordYield(tickets[command.ticket],base+0x50B690,GetCurrentThreadId()));SetEvent(readyEvent);check(WaitForSingleObject(goEvent,5000)==WAIT_OBJECT_0);}
   const auto ex=invoke(command.slot,command.arg,command.operation==4?0:command.operation);if(ex)InterlockedIncrement(&caught);
   if(active)check(core.Leave(execution,ex?ta::Outcome::Abnormal:ta::Outcome::Returned));
   SetEvent(doneEvent);
 }return 0;
}
void start(Command c){command=c;ResetEvent(doneEvent);SetEvent(beginEvent);}
void finish(){check(WaitForSingleObject(doneEvent,5000)==WAIT_OBJECT_0);}
void run(Command c){start(c);finish();}
bool make(unsigned index,unsigned gen,ta::Kind kind,std::uint64_t reuse=0){
 auto& c=creation[index];c.kind=kind;c.serial=index+1;c.state=reuse?reuse:0x100000+index*0x2000;c.callable=c.state+0x1000;
 c.parentThread=GetCurrentThreadId();c.workerThread=workerThread;
 switch(kind){
 case ta::Kind::EmbeddedLoad:c.worker=c.state+0x478;c.creationSite=base+0x4DA2EF;c.payload=base+0x508B40;break;
 case ta::Kind::Title520:c.worker=c.state+0x520;c.creationSite=base+0x4BEEBD;c.payload=base+0x4DA390;break;
 case ta::Kind::Title590:c.worker=c.state+0x590;c.creationSite=base+0x4BEF26;c.payload=base+0x466600;break;
 default:c.worker=c.state+0x800;c.creationSite=base+0x50B598;c.selectionSite=base+0x50B4B3;c.formalSlot=c.state+0x1800;c.payload=base+0x50B730;break;
 }
 return core.RecordCreation(gen,c,tickets[index]);
}
bool complete(unsigned i){const auto& c=creation[i];ta::Completion x{};x.serial=c.serial;x.worker=c.worker;x.callable=c.callable;x.thread=GetCurrentThreadId();x.done=1;
 x.site=base+(c.kind==ta::Kind::EmbeddedLoad?0x4F7079:c.kind==ta::Kind::Title520?0x4AAF64:c.kind==ta::Kind::Title590?0x4AAF89:0x50B632);return core.RecordCompletion(tickets[i],x);}
void publish(){check(router.PublishForOfflineExercise(1,attributed.ProxyGeneration(2)));}
DWORD WINAPI differentJoin(void*){check(complete(0));return 0;}
}
int main(int argc,char** argv){
 if(argc!=2)return 2;mode=argv[1];check(core.Initialize(base));check(attributed.Initialize(core));
 for(unsigned i=0;i<2;i++){ta::Generation g{};g.callbacks={i+1,before,after,finally,&counts[i]};g.attempt=i+1;g.epoch=i+10;g.attachment[0]=static_cast<unsigned char>(i+1);check(core.RegisterGeneration(g));}
 check(router.Initialize(pr::Config{attributed.ProxyGeneration(1),true}));check(six.Initialize(router));auto config=six.Configuration(reinterpret_cast<void*>(native));
 for(unsigned i=0;i<6;i++)check(CheckpointPersistentBridgeConfigure(i,&config)==1);
 beginEvent=CreateEventW(nullptr,FALSE,FALSE,nullptr);doneEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);readyEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);goEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 threadHandle=CreateThread(nullptr,0,worker,nullptr,0,&workerThread);check(threadHandle!=nullptr);
 if(!strcmp(mode,"late-old-root")||!strcmp(mode,"all-state-kinds")){
   const unsigned n=!strcmp(mode,"all-state-kinds")?4:1;
   for(unsigned i=0;i<n;i++)check(make(i,1,static_cast<ta::Kind>(i)));publish();
   for(unsigned i=0;i<n;i++){run({i,i,0,true,true,creation[i].state,0});check(counts[0].before[i]==1&&counts[1].before[i]==0);}
   check(make(n,2,ta::Kind::User));run({n,0,0,true,true,creation[n].state,0});check(counts[1].before[0]==1);
 }else if(!strcmp(mode,"unknown-root")){
   publish();for(unsigned i=0;i<6;i++)run({0,i,0,false,true,0x987654,0});check(nativeCalls==6);for(auto& c:counts)for(auto v:c.before)check(v==0);check(attributed.ForwardedUnknown()==6);
 }else if(!strcmp(mode,"pointer-reuse")){
   check(make(0,1,ta::Kind::User));run({0,0,0,true,true,creation[0].state,0});check(complete(0));publish();
   check(make(1,2,ta::Kind::User,creation[0].state));run({0,0,0,true,false,creation[0].state,0});run({1,0,0,true,true,creation[1].state,0});check(counts[0].before[0]==1&&counts[1].before[0]==1&&nativeCalls==3);
 }else if(!strcmp(mode,"active-cutover")||!strcmp(mode,"resume-same-ticket")){
   check(make(0,1,ta::Kind::User));const bool resume=!strcmp(mode,"resume-same-ticket");start({0,0,resume?4u:3u,true,true,creation[0].state,0});check(WaitForSingleObject(readyEvent,5000)==WAIT_OBJECT_0);publish();
   if(resume){check(core.RecordResume(tickets[0],base+0x50B4AE,GetCurrentThreadId()));check(!core.RecordResume(tickets[0],base+0x50B4AE,GetCurrentThreadId()));}
   SetEvent(goEvent);finish();check(counts[0].before[0]==1&&counts[0].after[0]==1&&counts[1].before[0]==0);
 }else if(!strcmp(mode,"embedded-and-read")){
   for(unsigned i=0;i<3;i++)check(make(i,1,static_cast<ta::Kind>(4+i)));publish();
   for(unsigned i=0;i<3;i++)run({i,4,1,true,true,creation[i].callable,0});
   check(counts[0].before[4]==3&&counts[0].before[5]==1&&counts[1].before[4]==0&&nativeCalls==6);check(attributed.ForwardedUnknown()==2);
 }else if(!strcmp(mode,"embedded-join-other-thread")){
   check(make(0,1,ta::Kind::Title520));run({0,4,0,true,true,creation[0].callable,0});
   HANDLE join=CreateThread(nullptr,0,differentJoin,nullptr,0,nullptr);check(join!=nullptr);check(WaitForSingleObject(join,5000)==WAIT_OBJECT_0);CloseHandle(join);
   publish();check(make(1,2,ta::Kind::Title520,creation[0].state));run({1,4,0,true,true,creation[1].callable,0});check(counts[0].before[4]==1&&counts[1].before[4]==1);
 }else if(!strcmp(mode,"read-without-worker")){
   check(make(0,1,ta::Kind::EmbeddedLoad));publish();run({0,5,0,true,true,0x123,0});check(counts[0].before[5]==0&&counts[1].before[5]==0&&nativeCalls==1);
 }else if(!strcmp(mode,"wrong-frame")||!strcmp(mode,"wrong-serial")){
   check(make(0,1,ta::Kind::User));publish();bool serial=!strcmp(mode,"wrong-serial");run({0,0,0,true,!serial,creation[0].state+(serial?0:8),serial?1u:0u});check(counts[0].before[0]==0&&counts[1].before[0]==0&&nativeCalls==1);
 }else if(!strcmp(mode,"native-exception")||!strcmp(mode,"before-exception")){
   check(make(0,1,ta::Kind::User));publish();const bool beforeFault=!strcmp(mode,"before-exception");run({0,0,beforeFault?0u:2u,true,true,creation[0].state,0});check(caught==1&&counts[0].before[0]==1&&counts[0].after[0]==0&&counts[0].finally[0]==1&&counts[0].abnormal==1&&counts[1].before[0]==0);check(nativeCalls==(beforeFault?0:1));check(!complete(0));
 }else if(!strcmp(mode,"cross-thread")){
   check(make(0,1,ta::Kind::User));ta::Execution x;check(!core.Enter(tickets[0],entryFor(0),x));publish();invoke(0,creation[0].state,0);check(nativeCalls==1&&counts[1].before[0]==0);
 }else if(!strcmp(mode,"duplicate-creation")){
   check(make(0,1,ta::Kind::User));check(!make(1,2,ta::Kind::User,creation[0].state));check(!core.RecordResume(tickets[0],base+0x50B4AE,GetCurrentThreadId()));
 }else if(!strcmp(mode,"bounded-records")){
   for(unsigned i=0;i<256;i++)check(make(i,1,ta::Kind::User));check(!make(256,2,ta::Kind::User));
 }else return 3;
 InterlockedExchange(&quit,1);SetEvent(beginEvent);check(WaitForSingleObject(threadHandle,5000)==WAIT_OBJECT_0);
 for(auto h:{threadHandle,beginEvent,doneEvent,readyEvent,goEvent})CloseHandle(h);
 ta::Report r{};core.Snapshot(r);pr::Report route{};router.Snapshot(route);check(!r.activeExecutions&&!attributed.Faults()&&!six.Faults()&&!route.active&&route.entered==route.released);
 for(unsigned i=0;i<6;i++){CheckpointPersistentBridgeStats s{};check(CheckpointPersistentBridgeSnapshot(i,&s)==1&&s.started==s.finally_calls&&!s.active&&!s.cleanup_faults);for(auto& c:counts)check(c.before[i]==c.finally[i]);}
 std::printf("{\"passed\":%s,\"errors\":%ld,\"current_proxy\":%llu,\"created\":%llu,\"entered\":%llu,\"resumed\":%llu,\"completed\":%llu,\"rejected\":%llu,\"unknown_forwarded\":%llu,\"native_calls\":%ld,\"old_user_before\":%ld,\"new_user_before\":%ld,\"scheduler_fence\":false,\"production_publication\":false,\"receipt_provider\":\"owned fixture captured-data doubles\"}\n",errors?"false":"true",errors,route.current,r.created,r.entered,r.resumed,r.completed,r.rejected,attributed.ForwardedUnknown(),nativeCalls,counts[0].before[0],counts[1].before[0]);
 return errors?1:0;
}
