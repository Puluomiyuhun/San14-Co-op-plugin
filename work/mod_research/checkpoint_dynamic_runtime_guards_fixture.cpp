#include "checkpoint_dynamic_runtime_guards.h"
#include "checkpoint_live_runtime_guards_profile.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
namespace g=checkpoint_dynamic_runtime_guards;namespace profile=checkpoint_live_runtime_guards_profile;
namespace pd=checkpoint_bound_input_pending;namespace qa=checkpoint_native_queue_adapter;
static g::Context context;static qa::Adapter queueAdapter;static g::Stamp currentStamp;
static checkpoint_load_input_boundary_fixture::Layout layout;
static unsigned failures=0,storageCalls=0;static bool storageRejected=false;
static uintptr_t base=0,queueMemory=0,menu=0;static g::Config activeConfig;static std::wstring scenario;
template<class T>void put(uintptr_t p,T v){memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static uintptr_t alloc(size_t n){return uintptr_t(VirtualAlloc(nullptr,n,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));}
static void check(bool x,const char*s){if(!x){++failures;printf("FAIL %s\n",s);}}
static void textState(uintptr_t p,uintptr_t vt,const char*n){put<uintptr_t>(p,vt);memcpy(reinterpret_cast<void*>(p+0x70),n,strlen(n)+1);}
static void sso(uintptr_t p,const char*s){memset(reinterpret_cast<void*>(p),0,32);memcpy(reinterpret_cast<void*>(p),s,strlen(s)+1);put<std::uint64_t>(p+16,strlen(s));put<std::uint64_t>(p+24,15);}
static void protect(uintptr_t p){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(p),4096,PAGE_NOACCESS,&old)!=0,"retire owned object page");}
static bool storageValid(void*)noexcept{
 ++storageCalls;
 // Own attachment helper is nonrecursive and does not call storageValid again.
 return !storageRejected&&g::Context::AttachmentOnly(&context)&&g::Context::OwnedReadBridgeOnly(&context);
}
static void nativeQueue(void*manager,const char*name,void*mode,void*closure){
 check(uintptr_t(manager)==base+0x19e7310&&!strcmp(name,"CSaveLoadState"),"owned queue arguments");
 check(!static_cast<DWORD*>(mode)[0]&&!static_cast<DWORD*>(mode)[1],"load mode");for(unsigned i=0;i<64;++i)check(!static_cast<BYTE*>(closure)[i],"empty callback");
 menu=alloc(4096);textState(menu,base+0x12db4c0,"CSaveLoadState");queueMemory=alloc(1024);
 put<DWORD>(queueMemory,0);put<uintptr_t>(queueMemory+8,menu);
 put<std::uint64_t>(base+0x19e7310+0x30,1);put<std::uint64_t>(base+0x19e7310+0x38,64);put<uintptr_t>(base+0x19e7310+0x40,queueMemory);
}

extern "C" uintptr_t DynamicGuardEntries[6]={uintptr_t(&CheckpointPersistentBridge0),uintptr_t(&CheckpointPersistentBridge1),uintptr_t(&CheckpointPersistentBridge2),uintptr_t(&CheckpointPersistentBridge3),uintptr_t(&CheckpointPersistentBridge4),uintptr_t(&CheckpointPersistentBridge5)};
extern "C" std::uint64_t DynamicGuardInvoke(unsigned,uintptr_t);
extern "C" char DynamicGuardReturn;
namespace la=checkpoint_persistent_logical_adapter;
static la::Adapter logical;
struct Job {unsigned family=0,point=0,stage=0;uintptr_t a=0,b=0,c=0;bool result=false,ran=false;};static Job job;
static const CheckpointPushFrame* currentFrame=nullptr;
static bool createMenu(const g::Config&);
static void runJob(const void* frame){
 if(job.ran)return;job.ran=true;
 switch(job.family){
 case 0:job.result=g::Context::SessionGuard(&context,g::ns::Point(job.point));break;
 case 1:job.result=g::Context::RequestGuard(&context,g::rq::Point(job.point));break;
 case 2:job.result=g::Context::BytesGuard(&context,g::by::Point(job.point),job.a,job.b);break;
 case 3:job.result=g::Context::LifecycleGuard(&context,g::lc::Point(job.point),job.a,job.b);break;
 case 4:job.result=g::Context::IdentityGuard(&context,g::ti::Point(job.point),job.a,job.b,job.c);break;
 case 5:{const auto&f=*static_cast<const CheckpointPushFrame*>(frame);auto copy=f;
   job.result=g::Context::PlanningGuard(&context,g::pr::Point(job.point),scenario==L"copied-planning-frame"?copy:f,job.a,job.b,activeConfig.expected.generation);break;}
 case 6:currentFrame=static_cast<const CheckpointPushFrame*>(frame);job.result=createMenu(activeConfig);currentFrame=nullptr;break;
 case 7:job.result=queueAdapter.Queue().data!=nullptr;break;
 }
}
static void db(const CheckpointPushFrame*f,void*)noexcept{if(job.stage==1)runJob(f);}
static void da(const CheckpointPushFrame*f,void*)noexcept{if(job.stage==3)runJob(f);}
static void df(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*){}
static void wb(const CheckpointLoadWorkerFrame*f,void*){if(job.stage==1)runJob(f);}
static void wa(const CheckpointLoadWorkerFrame*f,void*){if(job.stage==3)runJob(f);}
static void wf(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*){}
static std::uint64_t nativeOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){return 0x8877665544332211ull;}
static void installBridges(const g::Config&c){
 la::Config l{};l.generation=c.expected.generation+(scenario==L"wrong-callback-generation"?1:0);
 for(unsigned i=0;i<4;++i){l.dispatchBefore[i]=db;l.dispatchAfter[i]=da;l.dispatchFinally[i]=df;}
 for(unsigned i=0;i<2;++i){l.workerBefore[i]=wb;l.workerAfter[i]=wa;l.workerFinally[i]=wf;}
 check(logical.Initialize(l),"immutable actual logical adapter");auto generation=logical.RouteGeneration();
 for(unsigned i=0;i<6;++i){if(i==5&&scenario==L"unconfigured-bridge")continue;CheckpointPersistentBridgeConfig b{};b.original=reinterpret_cast<void*>(&nativeOriginal);b.before=generation.before;b.after=generation.after;b.finally=generation.finally;b.context=generation.context;check(CheckpointPersistentBridgeConfigure(i,&b)==1,"actual persistent entry configuration");}
}
static bool invoke(unsigned slot,unsigned stage,uintptr_t self,Job value){job=value;job.stage=stage;check(DynamicGuardInvoke(slot,self)==0x8877665544332211ull,"native original preserved");check(job.ran,"real bridge callback ran");return job.result;}
static bool SG(g::ns::Point p){unsigned v=unsigned(p);if(v==0||v==1||v==5)return g::Context::SessionGuard(&context,p);
 auto current=at<uintptr_t>(base+0x19e7310+0x48);unsigned slot=v==2?0:current==menu?1:2;
 return invoke(slot,slot==2?1:3,current,{0,v});}
static bool RQ(g::rq::Point p){unsigned v=unsigned(p);return invoke(v?2:1,v?1:3,v?activeConfig.initial.states[2]:menu,{1,v});}
static bool BY(g::by::Point p,uintptr_t l,uintptr_t t){unsigned v=unsigned(p),slot=v==1?3:(v==2||v==3?4:5);uintptr_t self=slot==3?l:slot==4?at<uintptr_t>(l+0x478+0x48):0x500000;
 return invoke(slot,(v==3||v==5)?3:1,self,{2,v,0,l,t});}
static bool LC(g::lc::Point p,uintptr_t l,uintptr_t t){return invoke(3,p==g::lc::Point::After?3:1,l,{3,unsigned(p),0,l,t});}
static bool TI(g::ti::Point p,uintptr_t t,uintptr_t r,uintptr_t w){return invoke(4,p==g::ti::Point::After?3:1,at<uintptr_t>(t+0x520+0x48),{4,unsigned(p),0,t,r,w});}
static bool PG(g::pr::Point p,std::uint64_t a,std::uint64_t e){return invoke(0,p==g::pr::Point::After?3:1,at<uintptr_t>(base+0x19e7310+0x48),{5,unsigned(p),0,uintptr_t(a),uintptr_t(e)});}
static void makeIdentity(uintptr_t root,const g::ti::Identity&i){
 auto force=alloc(4096),person=alloc(4096),district=alloc(4096);put<uintptr_t>(root+0xdca0+i.force*8,force);put<uintptr_t>(root+0x148+i.ruler*8,person);put<uintptr_t>(root+0xde40+i.district*8,district);
 put<uintptr_t>(force,base+0x129fe58);put<WORD>(force+0x10,i.ruler);put<uintptr_t>(person,base+0x12a00d0);put<WORD>(person+0x10,i.ruler);put<BYTE>(person+0x118,i.district);
 put<uintptr_t>(district,base+0x129fec8);put<BYTE>(district+0x10,i.force);put<BYTE>(district+0x11,1);put<WORD>(district+0x12,i.ruler);
}
static g::Config configure(){
 check(layout.initialize(),"owned layout");base=layout.config.base;
 for(const auto&a:CheckpointLiveSessionAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
 for(const auto&a:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
 auto m=base+0x19e7310;put<std::uint64_t>(m+0x10,5);put<std::uint64_t>(m+0x18,16);put<std::uint64_t>(m+0x30,0);put<std::uint64_t>(m+0x38,0);put<uintptr_t>(m+0x40,0);put<uintptr_t>(m+0x48,0);
 put<uintptr_t>(layout.config.root,base+0x12aa6b0);put<uintptr_t>(layout.config.world,base+0x12aa638);
 put<DWORD>(layout.config.cache+8,0);put<uintptr_t>(layout.config.states[1],base+0x12f22d8);
 g::Config c{};c.pid=GetCurrentProcessId();FILETIME b{},e{},k{},u{};GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u);c.birth=(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;
 c.base=base;c.owner_module=uintptr_t(GetModuleHandleW(nullptr));c.expected.attempt=layout.config.attempt;c.expected.epoch=17;c.expected.generation=31;
 memset(c.expected.owner_binding,0x63,32);memcpy(c.expected.checkpoint_sha256,profile::checkpoint_sha,32);currentStamp=c.expected;c.current_stamp=&currentStamp;
 c.initial=layout.config;c.initial.menu=0;c.initial.year=201;c.initial.month=3;c.initial.day=21;c.initial.force=7;c.initialIdentity={1001,7,9};
 c.worldProfile={209,9,1,{777,12,13},{955,2,3}};
 strcpy_s(c.fileProfile.name,g::fp::SupportedName);c.fileProfile.slot=63;c.fileProfile.size=345678;memset(c.fileProfile.sha256,0x73,32);
 if(scenario==L"alternate-dynamic"){c.worldProfile={219,12,21,{2001,23,25},{3001,42,43}};c.fileProfile.size=456789;memset(c.fileProfile.sha256,0x92,32);}
 memcpy(c.expected.checkpoint_sha256,c.fileProfile.sha256,32);currentStamp=c.expected;
 put<WORD>(c.initial.world+0x34,WORD(c.initial.year));put<BYTE>(c.initial.world+0x36,BYTE(c.initial.month));put<BYTE>(c.initial.world+0x37,BYTE(c.initial.day));put<BYTE>(c.initial.world+0x3a,BYTE(c.initial.force));put<BYTE>(c.initial.world+0x165d,1);makeIdentity(c.initial.root,c.initialIdentity);
 for(auto&label:c.fixtureCallers)label=uintptr_t(&DynamicGuardReturn);
c.queue=&queueAdapter;c.storage_valid=storageValid;
 c.request_intent=L"C:\\owned-test\\request.intent";c.identity_intent=L"C:\\owned-test\\identity.intent";memcpy(c.supported_image_sha256,profile::image_sha,32);
 for(unsigned i=0;i<5;++i){auto slot=reinterpret_cast<void*volatile*>(base+profile::slots[i]);auto original=reinterpret_cast<void*>(base+profile::originals[i]);*slot=original;c.hooks[i]={slot,original,reinterpret_cast<void*>(DynamicGuardEntries[i])};}
 auto fileSlot=reinterpret_cast<void*volatile*>(alloc(4096));*fileSlot=reinterpret_cast<void*>(&configure);c.hooks[5]={fileSlot,reinterpret_cast<void*>(&configure),reinterpret_cast<void*>(DynamicGuardEntries[5])};
 return c;
}
static void owned(const g::Config&c){for(const auto&h:c.hooks)*h.slot=h.hook;}
static bool createMenu(const g::Config&c){
 pd::Config p{};p.profile_base=base;p.binding.attempt.fill(0xa1);p.binding.attachment.fill(0xb2);p.binding.owner_generation=17;memcpy(p.states,c.initial.states,sizeof p.states);
 auto span=[](uintptr_t a,size_t n){return pd::Span{reinterpret_cast<const BYTE*>(a),n};};
 p.user=span(c.initial.states[4],0x668);p.toolbar=span(layout.toolbar,0x8c);p.game=span(c.initial.states[2],0x488);p.panel=span(layout.panel,0x1f8);p.manager=span(base+0x19e7310,0x50);p.stack=span(layout.stack,128);p.load_cache=span(c.initial.cache,0x3f4);p.expected_initial_cache_mode=0;
 p.resolve_created_queue=qa::Adapter::ResolveCallback;p.queue_resolver_context=&queueAdapter;
 qa::Config q{};q.pending=p;q.controller_identity=&context;q.cache=c.initial.cache;q.validate_external=g::Context::QueueGuard;q.external_context=&context;q.fixture_native=nativeQueue;q.fixture_user_caller=uintptr_t(&DynamicGuardReturn);
 check(queueAdapter.Initialize(q),"queue initialize guard permits idle current0");
 owned(c);put<uintptr_t>(base+0x19e7310+0x48,c.initial.states[4]);
 pd::Adapter pending;check(pending.Bind(p)==pd::Error::None,"actual pending binding");
 const auto&f=*currentFrame;
 check(pending.ObserveBefore(p.binding,f).error==pd::Error::None,"pending BEFORE");
 check(pending.ObserveBeforeFetch(p.binding,f.call_id,reinterpret_cast<void*>(f.args[0])).pending_admission_candidate,"unit callback prefetch observation");
 check(pending.ObserveAfter(p.binding,f).pending_admission_candidate,"pending AFTER");
 pd::Ticket ticket{};check(pending.BeginAuthorizedLoadPush(p.binding,f.call_id,ticket)==pd::Error::None,"real private ticket creation");
 check(queueAdapter.Authorize(ticket,f,&context),"real adapter authorize guard");
 if(scenario==L"delayed-queue-call")return true;
 auto result=queueAdapter.Queue();
 check(result.data&&pending.CommitAuthorizedLoadPush(ticket,result)==pd::Error::None,"native queue body and exact allocation resolution");
 return g::Context::SessionGuard(&context,g::ns::Point::BindMenu);
}
static int finish(){g::Report r{};context.Snapshot(r);unsigned touched=0,accepted=0;for(unsigned i=0;i<29;++i){touched+=r.calls[i]!=0;accepted+=r.accepted[i]!=0;}
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"point_types_called\":%u,\"point_types_accepted\":%u,\"storage_calls\":%u,\"guard_error\":%u,\"exception\":%lu,\"load_retired\":%u,\"identity_returned\":%u,\"game_access\":false,\"native_lifecycle_is_owned_model\":true}\n",scenario.c_str(),failures?"false":"true",failures,touched,accepted,storageCalls,unsigned(r.last_error),r.exception,r.load_retired,r.identity_returned);
 return failures?1:0;
}
int wmain(int argc,wchar_t**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=2)return 2;scenario=argv[1];auto c=configure();activeConfig=c;installBridges(c);owned(c);
 if(scenario==L"bad-intent")c.identity_intent=c.request_intent;
 if(scenario==L"invalid-profile")c.fileProfile.size=0;
 if(scenario==L"wrong-caller")c.fixtureCallers[0]+=1;
 check(context.Initialize(c)==(scenario!=L"bad-intent"&&scenario!=L"invalid-profile"),"immutable configuration validated");if(scenario==L"bad-intent"||scenario==L"invalid-profile")return finish();
 check(storageCalls==0,"Initialize does not require unopened storage gate");
 if(scenario==L"unconfigured-bridge"){check(!SG(g::ns::Point::Initialize),"slot pointer alone cannot certify configured persistent bridge");return finish();}
 if(scenario==L"wrong-stamp")++currentStamp.epoch;
 if(scenario==L"wrong-image")put<BYTE>(base+0x3f9b00,0);
 if(scenario==L"wrong-native-slot")*c.hooks[2].slot=reinterpret_cast<void*>(&finish);
 if(scenario==L"storage-rejected")storageRejected=true;
 if(scenario==L"rng-stale")put<DWORD>(base+0x18eb8b0,c.initial.expectedRng+1);
 if(scenario==L"wrong-stamp"||scenario==L"wrong-image"||scenario==L"wrong-native-slot"||scenario==L"storage-rejected"||scenario==L"rng-stale"){
  check(!SG(g::ns::Point::Initialize),"fresh guard rejects inconsistent attachment/profile/slot/storage/RNG");return finish();}
 check(SG(g::ns::Point::Initialize),"Session Initialize requires owned configured slots, permits idle current0");
 check(SG(g::ns::Point::Arm),"Arm requires owned configured slots, permits idle current0");
 if(scenario==L"mixed-cleanup"){
  *c.hooks[0].slot=c.hooks[0].original;protect(c.initial.states[4]);protect(c.initial.states[2]);
  check(!SG(g::ns::Point::RestoreBeforeCommit),"generation guard never approves partial restoration of persistent owner hooks");return finish();}
 if(scenario==L"wrong-queue-receipt"){owned(c);check(!SG(g::ns::Point::BindMenu),"no fabricated queue receipt");return finish();}
 if(scenario==L"missing-mapping"){check(!g::Context::SessionGuard(&context,g::ns::Point::BindMenu),"direct unscoped callback denied");return finish();}
 if(scenario==L"wrong-callback-generation"){check(!invoke(0,3,c.initial.states[4],{0,2}),"old or foreign generation denied");return finish();}
 if(scenario==L"wrong-caller"){check(!invoke(0,3,c.initial.states[4],{0,2}),"actual caller label mismatch denied");return finish();}
 check(invoke(0,3,c.initial.states[4],{6}),"Session binds actual created queue adapter menu");
 if(scenario==L"delayed-queue-call"){
  check(!invoke(0,3,c.initial.states[4],{7}),"authorization cannot escape to a later actual User call");qa::Report q{};queueAdapter.Snapshot(q);check(q.native_calls==0,"late capability never calls native queue");return finish();}
 if(scenario==L"late-bind-call"){check(!SG(g::ns::Point::BindMenu),"resolved menu cannot be rebound from a different actual call");return finish();}
 if(scenario==L"foreign-owned-slot"){*c.hooks[1].slot=reinterpret_cast<void*>(&finish);check(!g::Context::AttachmentOnly(&context),"foreign hook rejected");return finish();}
 auto m=base+0x19e7310;put<std::uint64_t>(m+0x10,6);put<std::uint64_t>(m+0x30,0);put<uintptr_t>(layout.stack+40,menu);put<uintptr_t>(m+0x48,menu);
 check(SG(g::ns::Point::BeforeRequest),"shared BeforeRequest accepts real Menu stage");
 check(RQ(g::rq::Point::MenuReceipt),"MenuReceipt");
 put<uintptr_t>(m+0x48,c.initial.states[2]);
 check(SG(g::ns::Point::BeforeRequest),"shared BeforeRequest accepts Game stage");
 for(unsigned p=1;p<6;++p)check(RQ(g::rq::Point(p)),"Game pre-CAS request point");
 check(SG(g::ns::Point::RestoreBeforeCommit),"pre-CAS cleanup envelope");
 put<LONG>(c.initial.cache+0x3ec,63);
 check(SG(g::ns::Point::AfterRequest),"AfterRequest allows actual63");
 check(RQ(g::rq::Point::AfterCas),"AfterCas does not reuse pending-1 boundary");
 auto load=alloc(4096),title=alloc(4096),closure=alloc(4096);textState(load,base+0x12dbd68,"CLoadState");textState(title,base+0x12daaf0,"CTitleState");
 put<DWORD>(load+0x470,1);put<uintptr_t>(load+0x48,closure);put<uintptr_t>(closure,base+0x12ea4d0);put<uintptr_t>(closure+8,title);put<uintptr_t>(base+0x12ea4d0+0x10,base+0x4fac30);put<LONG>(title+0x47c,63);put<DWORD>(title+0x470,13);
 put<std::uint64_t>(m+0x10,4);put<uintptr_t>(layout.stack+16,title);put<uintptr_t>(layout.stack+24,load);put<uintptr_t>(m+0x48,load);put<LONG>(base+0x201ecd0,63);sso(base+0x201ece0,c.fileProfile.name);
 auto loadCallable=alloc(4096),titleCallable=alloc(4096);put<uintptr_t>(load+0x478+0x48,loadCallable);put<uintptr_t>(loadCallable,base+0x138e8c0);put<uintptr_t>(loadCallable+8,base+0x508b40);put<uintptr_t>(title+0x520+0x48,titleCallable);put<uintptr_t>(titleCallable,base+0x138e8c0);put<uintptr_t>(titleCallable+8,base+0x4da390);
 // Retire initial Game/User and world before invoking ANY loading guard.
 protect(c.initial.states[2]);protect(c.initial.states[4]);protect(c.initial.world);
 auto world=alloc(0x22000);put<uintptr_t>(c.initial.root+0x85130,world);put<uintptr_t>(world,base+0x12aa638);put<WORD>(world+0x34,c.worldProfile.year);put<BYTE>(world+0x36,c.worldProfile.month);put<BYTE>(world+0x37,c.worldProfile.day);put<BYTE>(world+0x3a,c.worldProfile.source.force);put<BYTE>(world+0x165d,2);
 if(scenario==L"wrong-load-request"){put<LONG>(base+0x201ecd0,34);check(!LC(g::lc::Point::Bind,load,title),"other request cannot bind live Load");return finish();}
 check(LC(g::lc::Point::Bind,load,title),"Load Bind with retired old world/UI");
 check(BY(g::by::Point::Bind,load,title),"byte Bind precedes worker publication");
 check(LC(g::lc::Point::Before,load,title),"Load phase1 BEFORE");
 check(BY(g::by::Point::WorkerBefore,load,title),"worker can begin before phase2 publication");
 put<DWORD>(load+0x470,2);check(LC(g::lc::Point::After,load,title),"Load phase2 AFTER");
 for(auto p:{g::by::Point::ReadBefore,g::by::Point::ReadAfter,g::by::Point::WorkerAfter})check(BY(p,load,title),"live worker/read attachment");
 put<DWORD>(load+0x470,4);check(LC(g::lc::Point::Before,load,title),"Load completion BEFORE retains63");
 put<DWORD>(load+8,0x7ffffffd);put<LONG>(base+0x201ecd0,-1);sso(base+0x201ece0,"");put<LONG>(c.initial.cache+0x3ec,-1);put<std::uint64_t>(m+0x30,1);put<DWORD>(queueMemory,1);put<uintptr_t>(queueMemory+8,0);
 check(LC(g::lc::Point::After,load,title),"completion exact pop1 and cleared request accepted");
 protect(load); // Title guard must NEVER dereference historical Load.
 makeIdentity(c.initial.root,c.worldProfile.source);makeIdentity(c.initial.root,c.worldProfile.target);
 auto forceA=at<uintptr_t>(c.initial.root+0xdca0+c.worldProfile.source.force*8),forceB=at<uintptr_t>(c.initial.root+0xdca0+c.worldProfile.target.force*8),personA=at<uintptr_t>(c.initial.root+0x148+c.worldProfile.source.ruler*8),personB=at<uintptr_t>(c.initial.root+0x148+c.worldProfile.target.ruler*8);
 put<uintptr_t>(title+0x4a0,forceA);put<uintptr_t>(title+0x4a8,personA);
 if(scenario==L"wrong-title"){check(!TI(g::ti::Point::Before,title+16,c.initial.root,world),"different Title rejected before retired Load access");return finish();}
 for(unsigned p=1;p<=4;++p)check(TI(g::ti::Point(p),title,c.initial.root,world),"source world and source pair before identity CAS");
 put<uintptr_t>(title+0x4a0,forceB);put<uintptr_t>(title+0x4a8,personB);
 check(TI(g::ti::Point::AfterCompareExchange,title,c.initial.root,world),"target pair with still-source world before native initializer");
 put<BYTE>(world+0x3a,c.worldProfile.target.force);put<BYTE>(world+0x165d,1);put<DWORD>(title+0x470,15);put<std::uint64_t>(m+0x10,3);
 check(TI(g::ti::Point::After,title,c.initial.root,world),"target world after initializer");
 check(!invoke(4,3,loadCallable,{2,unsigned(g::by::Point::WorkerAfter),0,load,title}),"retired Load refused without dereferencing protected page");
 protect(title);auto game=alloc(4096),strategy=alloc(4096),user=alloc(4096);
 const bool reuseLoad=scenario==L"game-reuses-load"||scenario==L"wrong-load-type"||scenario==L"forged-game-name";
 const bool reuseTitle=scenario==L"strategy-reuses-title"||scenario==L"wrong-title-type";
 if(reuseLoad){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(load),4096,PAGE_READWRITE,&old)!=0,"allocator owns reused former Load page");game=load;memset(reinterpret_cast<void*>(game),0,4096);}
 if(reuseTitle){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(title),4096,PAGE_READWRITE,&old)!=0,"allocator owns reused former Title page");strategy=title;memset(reinterpret_cast<void*>(strategy),0,4096);}
 textState(game,base+0x12cc9b8,"CGameState");textState(strategy,base+0x12cd400,"CStrategyState");textState(user,base+0x12cc4a8,"CUserStrategyState");put<DWORD>(user+0x470,2);
 if(scenario==L"wrong-load-type")textState(game,base+0x12dbd68,"CLoadState");
 if(scenario==L"forged-game-name")put<uintptr_t>(game,base+0x12dbd68);
 if(scenario==L"wrong-title-type")textState(strategy,base+0x12daaf0,"CTitleState");
 if(scenario==L"phase0-still-rejected")put<DWORD>(user+0x470,0);
 put<uintptr_t>(layout.stack+16,game);put<uintptr_t>(layout.stack+24,strategy);put<uintptr_t>(layout.stack+32,user);put<std::uint64_t>(m+0x10,5);put<std::uint64_t>(m+0x30,0);put<uintptr_t>(m+0x48,user);
 if(scenario==L"wrong-load-type"||scenario==L"forged-game-name"||scenario==L"wrong-title-type"||scenario==L"phase0-still-rejected"){
  check(!PG(g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"type/lifecycle/phase mismatch remains rejected");return finish();}
 if(scenario==L"wrong-epoch"){check(!PG(g::pr::Point::Before,c.expected.attempt,18),"old/different epoch cannot receive planning receipt");return finish();}
 if(scenario==L"planning-wrong-date"){put<BYTE>(world+0x37,11);check(!PG(g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"incoming date exact");return finish();}
 if(scenario==L"planning-wrong-district"){put<BYTE>(personB+0x118,1);check(!PG(g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"incoming target district exact");return finish();}
 if(scenario==L"copied-planning-frame"){check(!PG(g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"copied frame lacks actual scope identity");return finish();}
 check(PG(g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"new User BEFORE never reads protected historical states");
 check(PG(g::pr::Point::After,c.expected.attempt,c.expected.epoch),"new User AFTER");
 g::Report r{};context.Snapshot(r);for(unsigned i=0;i<29;++i)check(r.accepted[i]>0,"all29 point types exercised with real guard code");check(!r.exception,"no retired-memory exception used as success");
 return finish();
}
