#include "checkpoint_live_runtime_guards_v2.h"
#include "checkpoint_live_runtime_guards_profile.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
namespace g=checkpoint_live_runtime_guards_v2;namespace profile=checkpoint_live_runtime_guards_profile;
namespace pd=checkpoint_bound_input_pending;namespace qa=checkpoint_native_queue_adapter;
static g::Context context;static qa::Adapter queueAdapter;static g::Stamp currentStamp;
static checkpoint_load_input_boundary_fixture::Layout layout;
static unsigned failures=0,storageCalls=0;static bool storageRejected=false;
static uintptr_t base=0,queueMemory=0,menu=0;static std::wstring scenario;
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
static g::Config configure(){
 check(layout.initialize(),"owned layout");base=layout.config.base;
 for(const auto&a:CheckpointLiveSessionAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
 for(const auto&a:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size);
 auto m=base+0x19e7310;put<std::uint64_t>(m+0x10,5);put<std::uint64_t>(m+0x18,16);put<std::uint64_t>(m+0x30,0);put<std::uint64_t>(m+0x38,0);put<uintptr_t>(m+0x40,0);put<uintptr_t>(m+0x48,0);
 put<uintptr_t>(layout.config.root,base+0x12aa6b0);put<uintptr_t>(layout.config.world,base+0x12aa638);
 put<DWORD>(layout.config.cache+8,0);put<uintptr_t>(layout.config.states[1],base+0x12f22d8);
 g::Config c{};c.pid=GetCurrentProcessId();FILETIME b{},e{},k{},u{};GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u);c.birth=(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;
 c.base=base;c.owner_module=uintptr_t(GetModuleHandleW(nullptr));c.expected.attempt=layout.config.attempt;c.expected.epoch=17;
 memset(c.expected.owner_binding,0x63,32);memcpy(c.expected.checkpoint_sha256,profile::checkpoint_sha,32);currentStamp=c.expected;c.current_stamp=&currentStamp;
 c.initial=layout.config;c.initial.menu=0;c.queue=&queueAdapter;c.storage_valid=storageValid;
 c.request_intent=L"C:\\owned-test\\request.intent";c.identity_intent=L"C:\\owned-test\\identity.intent";memcpy(c.supported_image_sha256,profile::image_sha,32);
 for(unsigned i=0;i<5;++i){auto slot=reinterpret_cast<void*volatile*>(base+profile::slots[i]);auto original=reinterpret_cast<void*>(base+profile::originals[i]);*slot=original;c.hooks[i]={slot,original,reinterpret_cast<void*>(&nativeQueue)};}
 auto fileSlot=reinterpret_cast<void*volatile*>(alloc(4096));*fileSlot=reinterpret_cast<void*>(&configure);c.hooks[5]={fileSlot,reinterpret_cast<void*>(&configure),reinterpret_cast<void*>(&nativeQueue)};
 return c;
}
static void owned(const g::Config&c){for(const auto&h:c.hooks)*h.slot=h.hook;}
static bool createMenu(const g::Config&c){
 pd::Config p{};p.profile_base=base;p.binding.attempt.fill(0xa1);p.binding.attachment.fill(0xb2);p.binding.owner_generation=17;memcpy(p.states,c.initial.states,sizeof p.states);
 auto span=[](uintptr_t a,size_t n){return pd::Span{reinterpret_cast<const BYTE*>(a),n};};
 p.user=span(c.initial.states[4],0x668);p.toolbar=span(layout.toolbar,0x8c);p.game=span(c.initial.states[2],0x488);p.panel=span(layout.panel,0x1f8);p.manager=span(base+0x19e7310,0x50);p.stack=span(layout.stack,128);p.load_cache=span(c.initial.cache,0x3f4);p.expected_initial_cache_mode=0;
 p.resolve_created_queue=qa::Adapter::ResolveCallback;p.queue_resolver_context=&queueAdapter;
 qa::Config q{};q.pending=p;q.controller_identity=&context;q.cache=c.initial.cache;q.validate_external=g::Context::QueueGuard;q.external_context=&context;q.fixture_native=nativeQueue;
 check(queueAdapter.Initialize(q),"queue initialize guard permits idle current0");
 owned(c);put<uintptr_t>(base+0x19e7310+0x48,c.initial.states[4]);
 pd::Adapter pending;check(pending.Bind(p)==pd::Error::None,"actual pending binding");
 uintptr_t caller=base+0x50b785;CheckpointPushFrame f{};f.args[0]=c.initial.states[4];f.thread_id=GetCurrentThreadId();f.call_id=1;f.caller_entry_rsp=uintptr_t(&caller);
 check(pending.ObserveBefore(p.binding,f).error==pd::Error::None,"pending BEFORE");
 check(pending.ObserveBeforeFetch(p.binding,1,reinterpret_cast<void*>(f.args[0])).pending_admission_candidate,"unit callback prefetch observation");
 check(pending.ObserveAfter(p.binding,f).pending_admission_candidate,"pending AFTER");
 pd::Ticket ticket{};check(pending.BeginAuthorizedLoadPush(p.binding,1,ticket)==pd::Error::None,"real private ticket creation");
 check(queueAdapter.Authorize(ticket,f,&context),"real adapter authorize guard");auto result=queueAdapter.Queue();
 check(result.data&&pending.CommitAuthorizedLoadPush(ticket,result)==pd::Error::None,"native queue body and exact allocation resolution");
 return g::Context::SessionGuard(&context,g::ns::Point::BindMenu);
}
static int finish(){g::Report r{};context.Snapshot(r);unsigned touched=0,accepted=0;for(unsigned i=0;i<29;++i){touched+=r.calls[i]!=0;accepted+=r.accepted[i]!=0;}
 printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"point_types_called\":%u,\"point_types_accepted\":%u,\"storage_calls\":%u,\"guard_error\":%u,\"exception\":%lu,\"load_retired\":%u,\"identity_returned\":%u,\"game_access\":false,\"native_lifecycle_is_owned_model\":true}\n",scenario.c_str(),failures?"false":"true",failures,touched,accepted,storageCalls,unsigned(r.last_error),r.exception,r.load_retired,r.identity_returned);
 return failures?1:0;
}
int wmain(int argc,wchar_t**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=2)return 2;scenario=argv[1];auto c=configure();
 if(scenario==L"bad-intent")c.identity_intent=c.request_intent;
 check(context.Initialize(c)==(scenario!=L"bad-intent"),"immutable configuration validated");if(scenario==L"bad-intent")return finish();
 check(storageCalls==0,"Initialize does not require unopened storage gate");
 if(scenario==L"wrong-stamp")++currentStamp.epoch;
 if(scenario==L"wrong-image")put<BYTE>(base+0x3f9b00,0);
 if(scenario==L"wrong-native-slot")*c.hooks[2].slot=reinterpret_cast<void*>(&finish);
 if(scenario==L"storage-rejected")storageRejected=true;
 if(scenario==L"rng-stale")put<DWORD>(base+0x18eb8b0,c.initial.expectedRng+1);
 if(scenario==L"wrong-stamp"||scenario==L"wrong-image"||scenario==L"wrong-native-slot"||scenario==L"storage-rejected"||scenario==L"rng-stale"){
  check(!g::Context::SessionGuard(&context,g::ns::Point::Initialize),"fresh guard rejects inconsistent attachment/profile/slot/storage/RNG");return finish();}
 check(g::Context::SessionGuard(&context,g::ns::Point::Initialize),"Session Initialize original slots/current0");
 check(g::Context::SessionGuard(&context,g::ns::Point::Arm),"Arm original slots/current0");
 if(scenario==L"mixed-cleanup"){
  *c.hooks[0].slot=c.hooks[0].hook;protect(c.initial.states[4]);protect(c.initial.states[2]);
  check(g::Context::SessionGuard(&context,g::ns::Point::RestoreBeforeCommit),"cleanup allows owned/original mixture without retired UI reads");return finish();}
 if(scenario==L"wrong-queue-receipt"){owned(c);check(!g::Context::SessionGuard(&context,g::ns::Point::BindMenu),"no fabricated queue receipt");return finish();}
 check(createMenu(c),"Session binds actual created queue adapter menu");
 if(scenario==L"foreign-owned-slot"){*c.hooks[1].slot=reinterpret_cast<void*>(&finish);check(!g::Context::AttachmentOnly(&context),"foreign hook rejected");return finish();}
 auto m=base+0x19e7310;put<std::uint64_t>(m+0x10,6);put<std::uint64_t>(m+0x30,0);put<uintptr_t>(layout.stack+40,menu);put<uintptr_t>(m+0x48,menu);
 check(g::Context::SessionGuard(&context,g::ns::Point::BeforeRequest),"shared BeforeRequest accepts real Menu stage");
 check(g::Context::RequestGuard(&context,g::rq::Point::MenuReceipt),"MenuReceipt");
 put<uintptr_t>(m+0x48,c.initial.states[2]);
 check(g::Context::SessionGuard(&context,g::ns::Point::BeforeRequest),"shared BeforeRequest accepts Game stage");
 for(unsigned p=1;p<6;++p)check(g::Context::RequestGuard(&context,g::rq::Point(p)),"Game pre-CAS request point");
 check(g::Context::SessionGuard(&context,g::ns::Point::RestoreBeforeCommit),"pre-CAS cleanup envelope");
 put<LONG>(c.initial.cache+0x3ec,63);
 check(g::Context::SessionGuard(&context,g::ns::Point::AfterRequest),"AfterRequest allows actual63");
 check(g::Context::RequestGuard(&context,g::rq::Point::AfterCas),"AfterCas does not reuse pending-1 boundary");
 auto load=alloc(4096),title=alloc(4096),closure=alloc(4096);textState(load,base+0x12dbd68,"CLoadState");textState(title,base+0x12daaf0,"CTitleState");
 put<DWORD>(load+0x470,1);put<uintptr_t>(load+0x48,closure);put<uintptr_t>(closure,base+0x12ea4d0);put<uintptr_t>(closure+8,title);put<uintptr_t>(base+0x12ea4d0+0x10,base+0x4fac30);put<LONG>(title+0x47c,63);put<DWORD>(title+0x470,13);
 put<std::uint64_t>(m+0x10,4);put<uintptr_t>(layout.stack+16,title);put<uintptr_t>(layout.stack+24,load);put<uintptr_t>(m+0x48,load);put<LONG>(base+0x201ecd0,63);sso(base+0x201ece0,g::by::TargetName);
 // Retire initial Game/User and world before invoking ANY loading guard.
 protect(c.initial.states[2]);protect(c.initial.states[4]);protect(c.initial.world);
 auto world=alloc(0x22000);put<uintptr_t>(c.initial.root+0x85130,world);put<uintptr_t>(world,base+0x12aa638);put<WORD>(world+0x34,203);put<BYTE>(world+0x36,8);put<BYTE>(world+0x37,11);put<BYTE>(world+0x3a,12);put<BYTE>(world+0x165d,2);
 if(scenario==L"wrong-load-request"){put<LONG>(base+0x201ecd0,34);check(!g::Context::LifecycleGuard(&context,g::lc::Point::Bind,load,title),"other request cannot bind live Load");return finish();}
 check(g::Context::LifecycleGuard(&context,g::lc::Point::Bind,load,title),"Load Bind with retired old world/UI");
 check(g::Context::BytesGuard(&context,g::by::Point::Bind,load,title),"byte Bind precedes worker publication");
 check(g::Context::LifecycleGuard(&context,g::lc::Point::Before,load,title),"Load phase1 BEFORE");
 check(g::Context::BytesGuard(&context,g::by::Point::WorkerBefore,load,title),"worker can begin before phase2 publication");
 put<DWORD>(load+0x470,2);check(g::Context::LifecycleGuard(&context,g::lc::Point::After,load,title),"Load phase2 AFTER");
 for(auto p:{g::by::Point::ReadBefore,g::by::Point::ReadAfter,g::by::Point::WorkerAfter})check(g::Context::BytesGuard(&context,p,load,title),"live worker/read attachment");
 put<DWORD>(load+0x470,4);check(g::Context::LifecycleGuard(&context,g::lc::Point::Before,load,title),"Load completion BEFORE retains63");
 put<DWORD>(load+8,0x7ffffffd);put<LONG>(base+0x201ecd0,-1);sso(base+0x201ece0,"");put<LONG>(c.initial.cache+0x3ec,-1);put<std::uint64_t>(m+0x30,1);put<DWORD>(queueMemory,1);put<uintptr_t>(queueMemory+8,0);
 check(g::Context::LifecycleGuard(&context,g::lc::Point::After,load,title),"completion exact pop1 and cleared request accepted");
 protect(load); // Title guard must NEVER dereference historical Load.
 auto forceA=alloc(4096),forceB=alloc(4096),personA=alloc(4096),personB=alloc(4096);
 put<uintptr_t>(c.initial.root+0xdca0+12*8,forceA);put<uintptr_t>(c.initial.root+0xdca0+2*8,forceB);put<uintptr_t>(c.initial.root+0x148+666*8,personA);put<uintptr_t>(c.initial.root+0x148+952*8,personB);
 put<uintptr_t>(title+0x4a0,forceA);put<uintptr_t>(title+0x4a8,personA);
 if(scenario==L"wrong-title"){check(!g::Context::IdentityGuard(&context,g::ti::Point::Before,title+16,c.initial.root,world),"different Title rejected before retired Load access");return finish();}
 for(unsigned p=1;p<=4;++p)check(g::Context::IdentityGuard(&context,g::ti::Point(p),title,c.initial.root,world),"source world and source pair before identity CAS");
 put<uintptr_t>(title+0x4a0,forceB);put<uintptr_t>(title+0x4a8,personB);
 check(g::Context::IdentityGuard(&context,g::ti::Point::AfterCompareExchange,title,c.initial.root,world),"target pair with still-source world before native initializer");
 put<BYTE>(world+0x3a,2);put<BYTE>(world+0x165d,1);put<DWORD>(title+0x470,15);put<std::uint64_t>(m+0x10,3);
 check(g::Context::IdentityGuard(&context,g::ti::Point::After,title,c.initial.root,world),"target world after initializer");
 check(!g::Context::BytesGuard(&context,g::by::Point::WorkerAfter,load,title),"retired Load refused without dereferencing protected page");
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
  check(!g::Context::PlanningGuard(&context,g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"type/lifecycle/phase mismatch remains rejected");return finish();}
 if(scenario==L"wrong-epoch"){check(!g::Context::PlanningGuard(&context,g::pr::Point::Before,c.expected.attempt,18),"old/different epoch cannot receive planning receipt");return finish();}
 check(g::Context::PlanningGuard(&context,g::pr::Point::Before,c.expected.attempt,c.expected.epoch),"new User BEFORE never reads protected historical states");
 check(g::Context::PlanningGuard(&context,g::pr::Point::After,c.expected.attempt,c.expected.epoch),"new User AFTER");
 g::Report r{};context.Snapshot(r);for(unsigned i=0;i<29;++i)check(r.accepted[i]>0,"all29 point types exercised with real guard code");check(!r.exception,"no retired-memory exception used as success");
 return finish();
}
