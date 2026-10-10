// Explicit cancel-choice successor; frozen predecessors are not modified.
// Reuse only owned services/world and dispatcher call-frame checks from the
// frozen fixture. Its fabricated-menu legacy main is compiled but never run.
#include "reward_menu_cancel_guard.h"
#define wmain SessionUnusedLegacyMain
#define DispatchCheck SessionUnusedLegacyDispatchCheck
#include "reward_menu_dispatch_fixture.cpp"
#undef DispatchCheck
#undef wmain
#include <thread>
extern "C" void CreationUserTail(void*,uintptr_t,unsigned);
extern "C" void CreationConsume(void*,uintptr_t);
extern "C" void CreationConsumeReturn();
namespace session=reward_menu_cancel_guard;
static session::Owner combined;
static uint64_t cancellationCallback=0;
static bool anyReceipt(){session::CancelReceipt cancelled{};reward_menu_closed_publication::Receipt confirmed{};return combined.ReadCancel(cancelled)||combined.ReadConfirmed(confirmed);}
static uint64_t creationAllocator=0,creationForce=0,createdAddress=0,unusedMenu=0;
static unsigned creationAllocations=0,creationInitializes=0,originalRewards=0;
static uint64_t ownedUiHelper=0;static unsigned uiHelperCalls=0;
static void uiHelperBefore(uint64_t p){need(p==ownedUiHelper,"owned UI helper before identity");++uiHelperCalls;}
static void uiHelperContext(uint64_t p,uint64_t context){need(p==ownedUiHelper&&context==0,"owned UI helper context");++uiHelperCalls;}
static void uiHelperDestroy(uint64_t p,unsigned flags){need(p==ownedUiHelper&&flags==1,"owned UI helper destroy");++uiHelperCalls;}
static const char*currentStage="start";
static LONG CALLBACK sessionException(EXCEPTION_POINTERS*p){if(p->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION)fprintf(stderr,"owned AV stage=%s rva=%llx rip=%llx address=%llx\n",currentStage,p->ContextRecord->Rip-fixture->b,p->ContextRecord->Rip,p->ExceptionRecord->ExceptionInformation[1]);return EXCEPTION_CONTINUE_SEARCH;}
static uint64_t creationManager(){return fixture->b+0x19E7310;}
static uint64_t creationForceGetter(uint64_t world){need(world==fixture->world,"actual command world getter argument");return creationForce;}
static uint64_t creationDistrictGetter(uint64_t force){need(force==creationForce,"actual command force getter argument");return fixture->district[11];}
static int creationValid(uint64_t p){return p==fixture->district[11];}
static uint64_t creationAllocate(uint64_t allocator,unsigned size,unsigned alignment,void*){
 need(allocator==creationAllocator&&size==0x490&&alignment==16,"native creator exact allocation");
 auto p=reinterpret_cast<uint64_t>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(p!=0,"owned native-created menu page");++creationAllocations;createdAddress=p;fixture->state=p;names[p]="Reward";return p;
}
static uint64_t creationReallocate(uint64_t,uint64_t,unsigned,void*){throw std::runtime_error("unexpected owned container growth");}
static void creationList(uint64_t p){need(p==createdAddress+0x480,"actual constructor selection instance");}
static void creationCallbackCopy(uint64_t,uint64_t){}
static int creationInitialize(uint64_t p,uint64_t,uint64_t){need(p==createdAddress,"same actual menu initialized");++creationInitializes;fixture->put(p+0x478,fixture->layout);return 1;}
static void creationActive(uint64_t,unsigned,uint64_t,uint64_t,uint64_t){}
static void creationGrow(uint64_t vector,uint64_t capacity){need(capacity&&capacity<=64,"owned bounded creation vector");auto old=at(vector),end=at(vector+8);need(end>=old&&end-old<=capacity*16,"creation vector extent");auto p=fixture->alloc(size_t(capacity)*16);if(old)memcpy(reinterpret_cast<void*>(p),reinterpret_cast<void*>(old),size_t(end-old));fixture->put(vector,p);fixture->put(vector+8,p+end-old);fixture->put(vector+16,p+capacity*16);}
static void originalReward(uint64_t){++originalRewards;throw std::runtime_error("original reward wrapper must stay suppressed");}
static void creationJump(uint64_t site,void*target){unsigned char code[14]={0xff,0x25,0,0,0,0};auto p=reinterpret_cast<uint64_t>(target);memcpy(code+6,&p,8);memcpy(reinterpret_cast<void*>(site),code,14);}
static void creationPatch(unsigned site,unsigned relay,void*target,unsigned count=5){auto&w=*fixture;creationJump(w.b+relay,target);memset(w.image+site,0x90,count);w.image[site]=0xe8;const int delta=int(relay)-int(site+5);memcpy(w.image+site+1,&delta,4);}
static const unsigned creationRanges[][2]={{0x3FA094,0x3FA0B4},{0x3FC270,0x3FCAB4},{0x3E2CF0,0x3E2E59},{0x509EC0,0x509EE2},{0x509E10,0x509EBD},{0x6082E0,0x6083A5}};
static void creationCode(const wchar_t*file){std::ifstream f(file,std::ios::binary);need(bool(f),"creation bounded input");std::vector<char>b((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());size_t n=0;for(const auto&r:creationRanges){need(n+r[1]-r[0]<=b.size(),"creation extent");memcpy(fixture->image+r[0],b.data()+n,r[1]-r[0]);n+=r[1]-r[0];}need(n==b.size(),"creation no trailing bytes");}
static void sourceProtection(DWORD protection){auto&w=*fixture;DWORD old=0;auto page=[&](unsigned a,unsigned e){a&=~0xfffU;e=(e+0xfff)&~0xfffU;need(VirtualProtect(w.image+a,e-a,protection,&old)!=0,"owned exact source protection");};for(const auto&r:creationRanges)page(r[0],r[1]);page(0x509FE0,0x50B690);page(0x910000,0x910100);FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000);}
static void sessionCopiedFree(uint64_t p){need(reinterpret_cast<uint64_t>(_ReturnAddress())==fixture->b+0x50B41B,"actual copied-vector destructor source");need(copiedAllocations.erase(p)==1&&VirtualFree(reinterpret_cast<void*>(p),0,MEM_RELEASE),"actual copied storage freed");++copiedFrees;need(combined.CopiedStorageReleased(p),"same session copied-storage receipt");}
extern "C" int DispatchCheck(unsigned stage,uint64_t manager,uint64_t top,uint64_t request,uint64_t end,uint64_t nativeRsp){
 if(stage==1){CONTEXT c{};c.ContextFlags=CONTEXT_FULL;c.Rip=fixture->b+0x50A9D7;c.Rsp=nativeRsp;DWORD64 b=0;auto*e=RtlLookupFunctionEntry(c.Rip,&b,nullptr);need(e&&b==fixture->b&&e->BeginAddress==functionEntry.BeginAddress&&e->EndAddress==functionEntry.EndAddress&&e->UnwindData==functionEntry.UnwindData,"exact original dispatch unwind lookup");PVOID data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,b,c.Rip,e,&c,&data,&frame,nullptr);need(c.Rip==reinterpret_cast<uint64_t>(&DispatchInvokeReturn)&&c.Rsp==DispatchExpectedRsp&&c.Rbp==0x1101&&c.R15==0x1108,"actual full caller frame unwind");unwindVerified=true;}
 reward_menu_closed_publication::Receipt absent{};need(!combined.ReadConfirmed(absent)&&!anyReceipt(),"no publication inside native dispatch");
 const bool ok=stage==1?combined.Select(manager,top,request,end):stage==2?combined.Finalized(manager,top):stage==3?combined.Freed(manager,top):combined.AfterCleanup();if(!ok)denied=true;return ok?1:0;
}
int wmain(int argc,wchar_t**argv){if(argc!=5)return 2;try{
 World w;fixture=&w;need(AddVectoredExceptionHandler(1,sessionException)!=nullptr,"owned failure trace");load(w,argv[1]);creationCode(argv[2]);const std::wstring mode=argv[4];const auto manager=w.b+0x19E7310;unusedMenu=w.state;
 {std::ifstream input(argv[3],std::ios::binary);std::vector<char> cb((std::istreambuf_iterator<char>(input)),{});need(cb.size()==35,"cancel bounded callback bytes");memcpy(w.image+0x5CC180,cb.data(),14);memcpy(w.image+0x4D4AA0,cb.data()+14,21);}
 // The old fixture's preconstructed menu is never selected or passed to any
 // source owner. Native creator allocation below replaces the state identity.
 auto oldMenuVt=at(unusedMenu);w.put(w.b+0x1331078-8,at(oldMenuVt-8));w.put(w.b+0x1331078+0x70,w.b+0x4D4AA0);w.put(w.b+0x1331078,w.b+0x6115A0);
 w.put(w.b+0x1331078+8,reinterpret_cast<uint64_t>(&creationInitialize));w.put(w.b+0x1331078+0x10,w.b+0x667B10);w.put(w.b+0x1331078+0x18,reinterpret_cast<uint64_t>(&resumeDouble));w.put(w.b+0x1331078+0x20,reinterpret_cast<uint64_t>(&pauseDouble));w.put(w.b+0x1331078+0x58,reinterpret_cast<uint64_t>(&creationActive));
 const auto oldWorld=w.world;w.world=w.obj("CWorldData",0x2000);memcpy(reinterpret_cast<void*>(w.world+8),reinterpret_cast<void*>(oldWorld+8),0x1000-8);w.put(w.root+0x85130,w.world);w.put<unsigned>(w.world+0x16A8,0xFFFFFFFF);
 generic(w,w.user,"User");const auto temporaryUserVt=at(w.user);memcpy(w.image+0x12CC4A8,reinterpret_cast<void*>(temporaryUserVt),0x100);w.put(w.user,w.b+0x12CC4A8);w.put<unsigned>(w.user+0x470,2);
 const char*lower[]={"Root","Motor","Game","Strategy"};for(unsigned i=0;i<4;++i){auto p=w.alloc(0x600);generic(w,p,lower[i]);w.put(w.stack+i*8,p);}w.put(manager+0x10,uint64_t(5));w.put(manager+0x18,uint64_t(32));w.put(manager+0x48,w.user);w.put(w.stack+40,uint64_t(0));
 auto layoutVt=w.alloc(0x100);w.put(w.layout,layoutVt);w.put(layoutVt,reinterpret_cast<uint64_t>(&deleteLayoutDouble));w.put(layoutVt+0x40,reinterpret_cast<uint64_t>(&beforeDouble));w.put(layoutVt+0x28,reinterpret_cast<uint64_t>(&contextDouble));w.put<unsigned>(w.layout+0x168,77);w.put<unsigned>(w.layout+0x170,0);
 creationAllocator=w.alloc(16);auto av=w.alloc(0x100);w.put(creationAllocator,av);w.put(av+0x40,reinterpret_cast<uint64_t>(&creationAllocate));w.put(av+0x48,reinterpret_cast<uint64_t>(&creationReallocate));w.put(av+0x58,reinterpret_cast<uint64_t>(&freeDouble));w.put(manager,creationAllocator);w.put(manager+8,creationAllocator);w.put(manager+0x28,creationAllocator);w.put(manager+0x30,uint64_t(0));w.put(manager+0x38,uint64_t(64));w.put(manager+0x40,w.alloc(64*16));creationForce=w.alloc(0x100);
 jump(w,0xF690,reinterpret_cast<void*>(&creationManager));jump(w,0x2F21E0,reinterpret_cast<void*>(&creationForceGetter));jump(w,0x20C110,reinterpret_cast<void*>(&creationDistrictGetter));jump(w,0x2F2BB0,reinterpret_cast<void*>(&creationValid));jump(w,0x811620,reinterpret_cast<void*>(&creationList));jump(w,0x1FEAC0,reinterpret_cast<void*>(&creationList));jump(w,0x3C6300,reinterpret_cast<void*>(&creationCallbackCopy));jump(w,0x50B7A0,reinterpret_cast<void*>(&creationGrow));jump(w,0x626050,reinterpret_cast<void*>(&originalReward));creationJump(w.b+0x50B3B6,reinterpret_cast<void*>(&CreationConsumeReturn));memcpy(w.image+0x12CDB40,"CStrategyRewardState",21);
 reward_menu_creation::Config c{};c.base=w.b;c.root=w.root;c.world=w.world;c.user=w.user;c.district=w.district[11];c.generation=7;c.thread=GetCurrentThreadId();c.year=203;c.month=8;c.day=11;c.force=12;for(unsigned i=0;i<5;++i)c.states[i]=at(w.stack+i*8);for(unsigned i=0;i<4;++i)c.relays[i]=w.b+0x910000+i*32;
 sourceProtection(PAGE_EXECUTE_READ);need(reward_menu_creation::Bind(c),"real creation binding");sourceProtection(PAGE_EXECUTE_READWRITE);creationPatch(0x3FA09A,0x910000,reinterpret_cast<void*>(&RewardMenuCreationDispatch));creationPatch(0x3FC3F3,0x910020,reinterpret_cast<void*>(&RewardMenuCreationCreate));creationPatch(0x3E2D80,0x910040,reinterpret_cast<void*>(&RewardMenuCreationName));creationPatch(0x50B35B,0x910060,reinterpret_cast<void*>(&RewardMenuCreationActivation),8);sourceProtection(PAGE_EXECUTE_READ);
 const char id[]="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";reward_menu_closed_publication::Receipt receipt{};session::CancelReceipt cancelled{};
 if(mode==L"no-creation"){need(!combined.Begin(7,id,0x900000,11,w.alloc(16))&&!anyReceipt(),"no fabricated creation evidence accepted");}
 else{
  currentStage="creation";CreationUserTail(w.image+0x3FA094,w.user,21);need(reward_menu_creation::Snapshot().phase==reward_menu_creation::Phase::Queued&&creationAllocations==1&&createdAddress!=unusedMenu,"actual new creation instance queued");
  currentStage="activate";ownedUiHelper=w.alloc(16);auto helperVt=w.alloc(0x100);w.put(ownedUiHelper,helperVt);w.put(helperVt,reinterpret_cast<uint64_t>(&uiHelperDestroy));w.put(helperVt+0x28,reinterpret_cast<uint64_t>(&uiHelperContext));w.put(helperVt+0x40,reinterpret_cast<uint64_t>(&uiHelperBefore));w.put(w.state+0x60,ownedUiHelper);w.put(manager+0x48,uint64_t(0));CreationConsume(w.image+0x50A7BA,manager);need(reward_menu_creation::Snapshot().phase==reward_menu_creation::Phase::Activated&&creationInitializes==1,"same actual menu stack activated");
  cancellationCallback=w.alloc(16);w.put(cancellationCallback,w.b+0x1337E00);w.put(cancellationCallback+8,w.state);w.put(w.b+0x1337E00+16,w.b+0x5CC180);
  currentStage="choice begin";need(combined.Begin(7,id,0x900000,11,cancellationCallback),"one creation claim arms confirm and cancel");need(!combined.Begin(7,id,0x900000,11,cancellationCallback),"choice bind once");need(reward_menu_creation::Snapshot().taken==1,"creation consumed exactly once for both choices");
  {
    // Later close dispatch has its own exact splices. Restore the creation-only
   // slice exit/activation before installing these owned, nonproduction hooks.
   sourceProtection(PAGE_EXECUTE_READWRITE);std::ifstream full(argv[1],std::ios::binary);std::vector<char>native((std::istreambuf_iterator<char>(full)),std::istreambuf_iterator<char>());const size_t fullOffset=(0x67A9C1-0x67A930)+(0x10AEA-0x10A60);memcpy(w.image+0x509FE0,native.data()+fullOffset,0x50B690-0x509FE0);
   patchCall(w,0x67A993,0x900000,reinterpret_cast<void*>(&RewardMenuHandoffGate_Entry));jump(w,0x50B7A0,reinterpret_cast<void*>(&growDouble));
   // Selection remains a service double; cancellation never needs a proposal.
   w.put(w.state+0x480,w.b+0x123F448);w.put(w.state+0x488,w.ph);w.put<unsigned>(w.layout+0x170,mode==L"confirm"||mode==L"pending-confirm"?2:0);
   w.put(manager+0x38,uint64_t(64));w.put(manager+0x40,w.alloc(64*16));
   const bool confirm=mode==L"confirm";
   const bool terminal=mode==L"pending-confirm"||mode==L"wrong-top-before"||mode==L"prequeued"||mode==L"wrong-generation"||mode==L"foreign-callback"||mode==L"source-tamper"||mode==L"wrong-thread";
   if(confirm||mode==L"pending-confirm")reinterpret_cast<void(*)(uint64_t)>(w.b+0x67A930)(w.state);
   if(terminal){
    if(mode==L"wrong-top-before")w.put(w.stack+40,unusedMenu);
    if(mode==L"prequeued")reinterpret_cast<void(*)(uint64_t)>(w.b+0x10A60)(manager);
    if(mode==L"source-tamper")w.image[0x5CC180]^=1;
    const auto before=at(manager+0x30);bool deniedRequest=false;
    if(mode==L"wrong-thread"){std::thread other([&]{deniedRequest=!combined.CancelNotify(7,cancellationCallback,100);});other.join();}
    else deniedRequest=!combined.CancelNotify(mode==L"wrong-generation"?8:7,mode==L"foreign-callback"?cancellationCallback+8:cancellationCallback,100);
    need(deniedRequest&&at(manager+0x30)==before&&combined.Snapshot().notifications==0&&!anyReceipt(),"bad cancellation cannot add untagged pop");
    if(mode==L"pending-confirm")need(reward_menu_handoff::Inspect().phase==reward_menu_handoff::Phase::pending&&reward_menu_handoff::Inspect().captures==1&&reward_menu_handoff::Inspect().takes==0,"pending confirm retained, not silently retired or consumed");
   }else{
    if(confirm){need(combined.ConfirmAndQueue(),"same choice owner confirms captured proposal");need(!combined.CancelNotify(7,cancellationCallback,100)&&at(manager+0x30)==1,"confirm choice excludes cancel without extra pop");}
    else{need(combined.CancelNotify(7,cancellationCallback,mode==L"zero-payload"?0:100),"actual bound callback queues cancellation once");need(!combined.ConfirmAndQueue()&&at(manager+0x30)==1,"cancel excludes confirm without proposal");need(reward_menu_handoff::Inspect().captures==0&&reward_menu_handoff::Inspect().takes==0&&reward_menu_handoff::Inspect().phase==reward_menu_handoff::Phase::retired,"cancel never captures/takes proposal");if(mode==L"duplicate-notify")need(!combined.CancelNotify(7,cancellationCallback,100)&&at(manager+0x30)==1&&combined.Snapshot().notifications==1,"duplicate notification never closes User");need(combined.Enter(),"cancellation guarded dispatch entered once");}
    need(!anyReceipt(),"queue and dispatch entry are not cancellation completion");
    // Actual full scheduler, supported by the frozen owned task/list services.
    auto pool=w.b+0x201D3A0,oldHeads=at(pool+0x10),oldCounts=at(pool+0x28);tempHeads=w.alloc(64*8);tempTails=w.alloc(64*8);tempCounts=w.alloc(64*8);w.put(tempHeads+8,at(oldHeads+8));w.put(tempTails+8,w.pn[1]);w.put(tempCounts+8,at(oldCounts+8));w.put(pool+0x10,tempHeads);w.put(pool+0x18,tempTails);w.put(pool+0x28,tempCounts);w.put<unsigned>(pool+0x40,64);tempHandle=w.alloc(8);w.put<unsigned>(tempHandle,2);w.put(w.b+0x201D418,uint64_t(1));w.put(w.b+0x201D420,uint64_t(2));
    auto task=w.alloc(0x100),mutex=w.alloc(0x40);w.put(task+0x10,mutex);w.put<unsigned>(task+0x78,1);for(unsigned i=0;i<6;++i){auto object=at(w.stack+i*8),vt=at(object);w.put(object+0x50,task);w.put(vt+0x30,reinterpret_cast<uint64_t>(&readyDouble));w.put(vt+0x60,reinterpret_cast<uint64_t>(&notifyDouble));}configObject=w.alloc(0x200);w.put<unsigned>(configObject+0x18c,1);w.put(w.b+0x123C328,reinterpret_cast<uint64_t>(&lockDouble));w.put(w.b+0x123C0D8,reinterpret_cast<uint64_t>(&lockDouble));w.put(w.b+0x1923F90,uint64_t(0x12345678abcd));
    jump(w,0x3A58B0,reinterpret_cast<void*>(&sessionCopiedFree));DispatchFaultReturn=w.b+0x50B3A8;DispatchSuccessReturn=w.b+0x50B394;DispatchCookieReturn=w.b+0x50B669;DispatchGetter=w.b+0xF570;patchCall(w,0x50A9D2,0x900020,reinterpret_cast<void*>(&DispatchSelect));patchCall(w,0x50B1B8,0x900040,reinterpret_cast<void*>(&DispatchFinalized));patchCall(w,0x50B26A,0x900060,reinterpret_cast<void*>(&DispatchFreed));patchCall(w,0x50B41B,0x900080,reinterpret_cast<void*>(&DispatchBoundary));FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000);
    need(RtlAddFunctionTable(&functionEntry,1,w.b),"owned exact scheduler unwind registration");releaseMenuPage=true;events.clear();copiedFrees=0;
    if(mode==L"duplicate-close")reinterpret_cast<void(*)(uint64_t)>(w.b+0x10A60)(manager);
    if(mode==L"wrong-top-after"){w.put(w.stack+40,unusedMenu);auto vt=at(unusedMenu);w.put(unusedMenu+0x50,task);w.put(vt+0x30,reinterpret_cast<uint64_t>(&readyDouble));w.put(vt+0x60,reinterpret_cast<uint64_t>(&notifyDouble));}
    if(mode==L"queued-only")need(!anyReceipt(),"no dispatch no publication");else{
     currentStage="full close dispatch";need(DispatchInvoke(w.image+0x509FE0,manager)==1,"original full scheduler returns with correct ABI");need(!anyReceipt(),"native return before owner Returned has no publication");const bool published=combined.Returned();need(published==(mode!=L"duplicate-close"&&mode!=L"wrong-top-after"),"dispatch outcome controls publication");need(unwindVerified&&copiedFrees==1&&copiedAllocations.empty(),"full actual scheduler unwind and copied-vector cleanup");
     if(published){
      if(confirm)need(combined.ReadConfirmed(receipt)&&!combined.ReadCancel(cancelled)&&receipt.proposal.count==2&&receipt.proposal.officers[0]==97&&receipt.proposal.officers[1]==759,"confirm still produces only original captured proposal");
      else{need(combined.ReadCancel(cancelled)&&!combined.ReadConfirmed(receipt)&&cancelled.cancelled&&cancelled.teardown_observed&&!cancelled.proposal_created&&!cancelled.production_permit&&cancelled.generation==7&&cancelled.menu==createdAddress,"cancel receipt has no reward proposal");const auto d=combined.Snapshot();need(d.notifications==1&&d.entered==1&&d.selected==1&&d.finalized==1&&d.closed==1&&d.storageReleased==1&&d.boundaries==1&&d.returned==1&&!d.active,"exactly one complete guarded cancellation");}
      MEMORY_BASIC_INFORMATION m{};need(menuPageReleased&&VirtualQuery(reinterpret_cast<void*>(createdAddress),&m,sizeof m)&&m.State==MEM_FREE&&uiHelperCalls==3&&at(manager+0x10)==5&&at(w.stack+32)==w.user,"only actual created menu is freed before receipt; User survives");
      bool read=false;std::thread reader([&]{session::CancelReceipt cpy{};reward_menu_closed_publication::Receipt rpy{};read=confirm?combined.ReadConfirmed(rpy):combined.ReadCancel(cpy);cpy.generation=0;rpy.proposal.officers[0]=1;});reader.join();need(read&&anyReceipt(),"immutable receipt cross-thread value read");
     }else need(!anyReceipt()&&!menuPageReleased&&at(manager+0x10)==6,"ambiguous close never frees or publishes");
    }need(RtlDeleteFunctionTable(&functionEntry),"remove owned scheduler unwind");
   }
  }
 }
 const auto report=combined.Snapshot();need(originalRewards==0,"no original reward native business call");const auto h=reward_menu_handoff::Inspect();printf("{\"passed\":true,\"case\":\"%ls\",\"phase\":%u,\"choice\":%u,\"error\":%u,\"notifications\":%llu,\"actual_creator_allocations\":%u,\"actual_created_menu_closed\":%s,\"cancel_published\":%s,\"confirm_published\":%s,\"handoff_captures\":%llu,\"handoff_takes\":%llu,\"original_rewards\":%u,\"production_permit\":false,\"game_access\":false}\n",mode.c_str(),unsigned(report.phase),unsigned(report.choice),report.error,report.notifications,creationAllocations,menuPageReleased?"true":"false",combined.ReadCancel(cancelled)?"true":"false",combined.ReadConfirmed(receipt)?"true":"false",h.captures,h.takes,originalRewards);return 0;
 }catch(const std::exception&e){fprintf(stderr,"session fixture: %s\n",e.what());return 1;}}
