// Actual archived completion/queue/pop code in an isolated owned allocation.
// Frame selection, allocator, UI, parent lifecycle and authority are NOT game code.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <stdexcept>
#include <vector>
#include <map>
#include "reward_menu_dispatch.h"
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
extern "C" int DispatchInvoke(void*,uint64_t);
extern "C" void DispatchInvokeReturn();
struct World {
    unsigned char* image=nullptr;unsigned char* heap=nullptr;uint64_t b=0,cursor=0,vtCursor=0;
    uint64_t root=0,world=0,state=0,layout=0,user=0,stack=0,callRsp=0,args=0;
    uint64_t city[52]{},district[52]{},person[2]{},pn[2]{},in[2]{},ph=0,ih=0,pc=0,ic=0;
    World(){
        image=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2400000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
        heap=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
        need(image&&heap,"Owned allocation failed");b=uint64_t(image);cursor=uint64_t(heap);vtCursor=b+0x1000000;
        root=obj("CSan14Data",0x86000);world=obj("CWorldData",0x1000);state=obj("CStrategyRewardState",0x600);
        layout=alloc(0x400);user=alloc(0x600);stack=alloc(0x100);callRsp=alloc(0x2000)+0x1000;args=callRsp-0x890+0x30;
        put(b+0x1FCA1E0,root);put(root+0x85130,world);put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);
        put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x3A,12);put(b+0x19E7310+0x10,uint64_t(6));
        put(b+0x19E7310+0x20,stack);put(stack+32,user);put(stack+40,state);put<uint32_t>(user+0x470,2);
        for(unsigned id=1;id<=51;++id){district[id]=obj("CDistrictData",0x40);put(root+0xDE40+id*8,district[id]);
            put<uint8_t>(district[id]+0x10,id==11?12:1);put<uint16_t>(district[id]+0x12,666);
            city[id]=obj("CCityData",0x100);put(root+0xDAA8+id*8,city[id]);put<uint16_t>(city[id]+0x10,uint16_t(id));
            put<uint8_t>(city[id]+0x30,11);put<uint16_t>(city[id]+0x4E,uint16_t(id));}
        auto leader=obj("CPersonData",0x200);put(root+0x148+666*8,leader);put<uint16_t>(leader+0x10,666);put<uint8_t>(leader+0x118,11);put<uint16_t>(leader+0x11A,19);
        unsigned ids[]={97,759};for(unsigned i=0;i<2;++i){person[i]=obj("CPersonData",0x200);put(root+0x148+ids[i]*8,person[i]);
            put<uint16_t>(person[i]+0x10,uint16_t(ids[i]));put<uint8_t>(person[i]+0x118,11);put<uint16_t>(person[i]+0x11A,19);}
        put(state+0x470,district[11]);put(state+0x478,layout);put<uint32_t>(layout+0x170,2);
        auto pointerPool=b+0x201D3A0;auto integerPool=b+0x19E1BF0;
        ph=alloc(8);ih=alloc(8);put<uint32_t>(ph,1);put<uint32_t>(ih,1);
        auto pheads=alloc(16),iheads=alloc(16),tails=alloc(16);pc=alloc(16);ic=alloc(16);
        for(unsigned i=0;i<2;++i){pn[i]=alloc(24);in[i]=alloc(24);put(pn[i],person[i]);put<uint32_t>(in[i],ids[i]);}
        put(pn[0]+8,pn[1]);put(in[0]+8,in[1]);put(in[1]+16,in[0]);
        put(pheads+8,pn[0]);put(iheads+8,in[0]);put(tails+8,in[1]);put(pc+8,uint64_t(2));put(ic+8,uint64_t(2));
        put(pointerPool+8,uint64_t(1));put(pointerPool+0x10,pheads);put(pointerPool+0x28,pc);put<uint32_t>(pointerPool+0x40,2);
        put(integerPool+8,uint64_t(1));put(integerPool+0x10,iheads);put(integerPool+0x18,tails);put(integerPool+0x28,ic);put<uint32_t>(integerPool+0x40,0x400);
        put(state+0x480,b+0x123F448);put(state+0x488,ph);put(args,b+0x123E210);put(args+8,ih);put(args+0x10,city[19]);
    }
    template<class T>void put(uint64_t address,T value){memcpy(reinterpret_cast<void*>(address),&value,sizeof value);}
    uint64_t alloc(size_t n){auto a=cursor;cursor+=(n+15)&~size_t(15);need(cursor<uint64_t(heap)+0x200000,"Fixture overflow");return a;}
    uint64_t obj(const char* name,size_t n){auto a=alloc(n),vt=vtCursor+8,loc=vtCursor+0x40,desc=vtCursor+0x80;vtCursor+=0x200;
        put(a,vt);put(vt-8,loc);put<uint32_t>(loc,1);put<uint32_t>(loc+12,uint32_t(desc-b));put<uint32_t>(loc+20,uint32_t(loc-b));
        auto decorated=std::string(".?AV")+name+"@@";memcpy(reinterpret_cast<void*>(desc+16),decorated.c_str(),decorated.size()+1);return a;}
    ~World(){if(heap)VirtualFree(heap,0,MEM_RELEASE);if(image)VirtualFree(image,0,MEM_RELEASE);}
};
static World* fixture=nullptr;
static bool releaseMenuPage=false,menuPageReleased=false;
static std::map<uint64_t,std::string> names;
struct Event {std::string event,object,top;uint64_t caller=0,count=0,queue=0,layout=0;DWORD thread=0;};
static std::vector<Event> events;
static uint64_t at(uint64_t p){return *reinterpret_cast<uint64_t*>(p);}
static std::string name(uint64_t p){auto it=names.find(p);return it==names.end()?"other":it->second;}
static void record(const char* event,uint64_t object,uint64_t caller){auto&w=*fixture;const auto count=at(w.b+0x19E7310+0x10);
    events.push_back({event,name(object),count?name(at(w.stack+(count-1)*8)):"none",caller-w.b,count,at(w.b+0x19E7310+0x30),at(w.state+0x478),GetCurrentThreadId()});}
static uint64_t __fastcall managerDouble(){record("manager_getter_double",fixture->state,reinterpret_cast<uint64_t>(_ReturnAddress()));return fixture->b+0x19E7310;}
static void __fastcall beforeDouble(uint64_t layout){need(layout==fixture->layout,"layout identity");record("layout_before_double",fixture->state,reinterpret_cast<uint64_t>(_ReturnAddress()));}
static void __fastcall contextDouble(uint64_t layout,uint64_t context){need(layout==fixture->layout&&context==0,"layout cleanup context");record("layout_context_double",fixture->state,reinterpret_cast<uint64_t>(_ReturnAddress()));}
static void __fastcall deleteLayoutDouble(uint64_t layout,unsigned flags){need(layout==fixture->layout&&flags==1,"layout destroy flags");record("layout_destroy_double",fixture->state,reinterpret_cast<uint64_t>(_ReturnAddress()));}
static void __fastcall listDouble(uint64_t list){need(list==fixture->state+0x480,"selection owner");record("selection_destroy_double",fixture->state,reinterpret_cast<uint64_t>(_ReturnAddress()));}
static int __fastcall pauseDouble(uint64_t object){record("other_pause_double",object,reinterpret_cast<uint64_t>(_ReturnAddress()));return 1;}
static int __fastcall finalizeDouble(uint64_t object){record("other_finalize_double",object,reinterpret_cast<uint64_t>(_ReturnAddress()));return 1;}
static int __fastcall resumeDouble(uint64_t object){record("parent_resume_double",object,reinterpret_cast<uint64_t>(_ReturnAddress()));return 1;}
static void __fastcall destructorDouble(uint64_t object,unsigned flags){need(flags==0,"dispatcher destructor flag");record("other_destructor_double",object,reinterpret_cast<uint64_t>(_ReturnAddress()));}
static void __fastcall freeDouble(uint64_t,uint64_t object){record("allocator_free_double",object,reinterpret_cast<uint64_t>(_ReturnAddress()));if(releaseMenuPage&&object==fixture->state){need(VirtualFree(reinterpret_cast<void*>(object),0,MEM_RELEASE)!=0,"owned menu allocation released");menuPageReleased=true;}}
static std::map<uint64_t,uint64_t> copiedAllocations;
static void __fastcall growDouble(uint64_t vector,uint64_t capacity){need(capacity>0&&capacity<=64,"bounded copied request allocation");
 auto old=at(vector),end=at(vector+8);need(end>=old&&end-old<=capacity*16,"copied vector length");auto buffer=reinterpret_cast<uint64_t>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(buffer!=0,"copied vector allocation");
 if(old){memcpy(reinterpret_cast<void*>(buffer),reinterpret_cast<void*>(old),size_t(end-old));need(copiedAllocations.erase(old)==1&&VirtualFree(reinterpret_cast<void*>(old),0,MEM_RELEASE),"owned growth previous free");}
 copiedAllocations[buffer]=capacity*16;auto&w=*fixture;w.put(vector,buffer);w.put(vector+8,buffer+(end-old));w.put(vector+16,buffer+capacity*16);
}
static uint64_t __fastcall tempHandleDouble(uint64_t,unsigned,unsigned);
static uint64_t __fastcall tempAppendDouble(uint64_t,unsigned,unsigned char);
static void __fastcall tempPopDouble(uint64_t);
static void __fastcall tempClearDouble(uint64_t,unsigned);
static void __fastcall tempReleaseDouble(uint64_t,uint64_t);
static void __fastcall copiedFreeDouble(uint64_t);
static void __fastcall lockDouble(uint64_t){}
static uint64_t __fastcall configDouble();
static void jump(World&w,uint64_t rva,void* target){unsigned char code[12]={0x48,0xB8};auto address=reinterpret_cast<uint64_t>(target);memcpy(code+2,&address,8);code[10]=0xFF;code[11]=0xE0;memcpy(w.image+rva,code,sizeof code);}
static void load(World&w,const wchar_t* path){std::ifstream file(path,std::ios::binary);need(bool(file),"explicit owned code input");
    std::vector<char> bytes((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
    struct Range {unsigned start,end;};const Range ranges[]={{0x67A930,0x67A9C1},{0x10A60,0x10AEA},{0x509FE0,0x50B690},{0x667B10,0x667B98},{0x60B000,0x60B065},{0x6115A0,0x6115D4},{0x665CD0,0x665CD6},{0xEF9F20,0xEF9F41},{0x17D2400,0x17D2440}};
    size_t n=0;for(const auto&r:ranges){need(n+(r.end-r.start)<=bytes.size(),"truncated bounded archive");memcpy(w.image+r.start,bytes.data()+n,r.end-r.start);n+=r.end-r.start;}need(n==bytes.size(),"extra bounded archive bytes");
    jump(w,0xF690,reinterpret_cast<void*>(&managerDouble));jump(w,0x50B7A0,reinterpret_cast<void*>(&growDouble));
    jump(w,0x1FED80,reinterpret_cast<void*>(&listDouble));
    jump(w,0x17040,reinterpret_cast<void*>(&tempHandleDouble));jump(w,0x172D0,reinterpret_cast<void*>(&tempAppendDouble));jump(w,0xC7660,reinterpret_cast<void*>(&tempPopDouble));jump(w,0x16C50,reinterpret_cast<void*>(&tempClearDouble));jump(w,0x16D10,reinterpret_cast<void*>(&tempReleaseDouble));jump(w,0x3A58B0,reinterpret_cast<void*>(&copiedFreeDouble));jump(w,0xF570,reinterpret_cast<void*>(&configDouble));
    DWORD old=0;need(VirtualProtect(w.image,0x2400000,PAGE_EXECUTE_READWRITE,&old)!=0,"owned code protection");need(FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000)!=0,"owned flush");
}
static void generic(World&w,uint64_t object,const char* label){names[object]=label;auto vt=w.alloc(0x100);w.put(object,vt);
    w.put(vt,reinterpret_cast<uint64_t>(&destructorDouble));w.put(vt+0x10,reinterpret_cast<uint64_t>(&finalizeDouble));
    w.put(vt+0x18,reinterpret_cast<uint64_t>(&resumeDouble));w.put(vt+0x20,reinterpret_cast<uint64_t>(&pauseDouble));w.put<uint32_t>(object+0x6C,1);
}

namespace life=reward_menu_lifecycle;
static reward_menu_dispatch::Guard dispatchGuard;
static life::Owner lifecycle;
extern "C" void DispatchSelect();extern "C" void DispatchFinalized();extern "C" void DispatchFreed();extern "C" void DispatchBoundary();
extern "C" {uint64_t DispatchFaultReturn=0,DispatchSuccessReturn=0,DispatchCookieReturn=0,DispatchGetter=0,DispatchExpectedRsp=0;}
static bool denied=false,unwindVerified=false;
static RUNTIME_FUNCTION functionEntry{0x509FE0,0x50B690,0x17D2400};
static uint64_t tempHandle=0,tempHeads=0,tempTails=0,tempCounts=0,configObject=0;static unsigned prepNotifications=0,copiedFrees=0;
static uint64_t __fastcall tempHandleDouble(uint64_t,unsigned,unsigned){return tempHandle;}
static uint64_t __fastcall tempAppendDouble(uint64_t,unsigned index,unsigned char){need(index==2,"temporary stack-list slot");auto&w=*fixture;auto node=w.alloc(24),previous=at(tempTails+16);if(previous)w.put(previous+8,node);else w.put(tempHeads+16,node);w.put(node+16,previous);w.put(tempTails+16,node);w.put(tempCounts+16,at(tempCounts+16)+1);return node;}
static void __fastcall tempPopDouble(uint64_t){auto&w=*fixture;auto node=at(tempTails+16);need(node!=0,"temporary stack not empty");auto previous=at(node+16);w.put(tempTails+16,previous);if(previous)w.put(previous+8,uint64_t(0));else w.put(tempHeads+16,uint64_t(0));w.put(tempCounts+16,at(tempCounts+16)-1);}
static void __fastcall tempClearDouble(uint64_t,unsigned){auto&w=*fixture;w.put(tempHeads+16,uint64_t(0));w.put(tempTails+16,uint64_t(0));w.put(tempCounts+16,uint64_t(0));}
static void __fastcall tempReleaseDouble(uint64_t,uint64_t){}
static uint64_t __fastcall configDouble(){return configObject;}
static int __fastcall readyDouble(uint64_t){return 0;}
static void __fastcall notifyDouble(uint64_t,unsigned,uint64_t,uint64_t){++prepNotifications;}
static void __fastcall copiedFreeDouble(uint64_t p){need(reinterpret_cast<uint64_t>(_ReturnAddress())==fixture->b+0x50B41B,"original vector destructor call");need(copiedAllocations.erase(p)==1&&VirtualFree(reinterpret_cast<void*>(p),0,MEM_RELEASE),"original exit frees actual owned copied-vector allocation");++copiedFrees;need(dispatchGuard.CopiedStorageReleased(p),"guard correlates freed copied request");}
extern "C" int DispatchCheck(unsigned stage,uint64_t manager,uint64_t top,uint64_t request,uint64_t end,uint64_t nativeRsp){
 if(stage==1){CONTEXT c{};c.ContextFlags=CONTEXT_FULL;c.Rip=fixture->b+0x50A9D7;c.Rsp=nativeRsp;DWORD64 foundBase=0;auto*entry=RtlLookupFunctionEntry(c.Rip,&foundBase,nullptr);need(entry&&entry->BeginAddress==functionEntry.BeginAddress&&entry->EndAddress==functionEntry.EndAddress&&entry->UnwindData==functionEntry.UnwindData&&foundBase==fixture->b,"actual original runtime-function table");PVOID data=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,foundBase,c.Rip,entry,&c,&data,&frame,nullptr);need(c.Rip==reinterpret_cast<uint64_t>(&DispatchInvokeReturn)&&c.Rsp==DispatchExpectedRsp&&c.Rbp==0x1101&&c.Rbx==0x1102&&c.Rsi==0x1103&&c.Rdi==0x1104&&c.R12==0x1105&&c.R13==0x1106&&c.R14==0x1107&&c.R15==0x1108,"original unwind metadata reconstructs actual complete-function caller frame");unwindVerified=true;}
 bool ok=stage==1?dispatchGuard.Select(manager,top,request,end):stage==2?dispatchGuard.Finalized(manager,top):stage==3?dispatchGuard.Freed(manager,top):dispatchGuard.AfterCleanup();if(!ok)denied=true;return ok?1:0;
}
static void patchCall(World&w,unsigned site,unsigned relay,void*entry){jump(w,relay,entry);w.image[site]=0xe8;const int delta=int(relay)-int(site+5);memcpy(w.image+site+1,&delta,4);}
int wmain(int argc,wchar_t**argv){if(argc!=3)return 2;
 try{
  World w;fixture=&w;load(w,argv[1]);const std::wstring mode=argv[2];const auto manager=w.b+0x19E7310;
  if(mode==L"normal-freed"){auto page=VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);need(page!=nullptr,"separate owned menu page");memcpy(page,reinterpret_cast<void*>(w.state),0x600);w.state=reinterpret_cast<uint64_t>(page);w.put(w.stack+40,w.state);releaseMenuPage=true;}
  names[w.state]="Reward";generic(w,w.user,"User");
  const char*lower[]={"Root","Motor","Game","Strategy"};for(unsigned i=0;i<4;++i){auto p=w.alloc(0x600);generic(w,p,lower[i]);w.put(w.stack+i*8,p);}
  auto menuVt=at(w.state);w.put(menuVt,w.b+0x6115A0);w.put(menuVt+0x10,w.b+0x667B10);w.put(menuVt+0x18,w.b+0x665CD0);w.put(menuVt+0x20,w.b+0x665CD0);w.put<uint32_t>(w.state+0x6C,1);
  auto layoutVt=w.alloc(0x100);w.put(w.layout,layoutVt);w.put(layoutVt,reinterpret_cast<uint64_t>(&deleteLayoutDouble));
  w.put(layoutVt+0x40,reinterpret_cast<uint64_t>(&beforeDouble));w.put(layoutVt+0x28,reinterpret_cast<uint64_t>(&contextDouble));w.put<uint32_t>(w.layout+0x168,77);
  auto allocator=w.alloc(16),allocatorVt=w.alloc(0x100);w.put(allocator,allocatorVt);w.put(allocatorVt+0x58,reinterpret_cast<uint64_t>(&freeDouble));
  w.put(manager,allocator);w.put(manager+0x28,allocator);auto pending=w.alloc(64*16);names[pending]="PendingStorage";
  w.put(manager+0x30,uint64_t(0));w.put(manager+0x38,uint64_t(64));w.put(manager+0x40,pending);
  // Explicit native-services model: temporary list helper and already-completed
  // task objects. No branch inside 509FE0 is skipped or substituted for setup.
  auto pool=w.b+0x201D3A0,oldHeads=at(pool+0x10),oldCounts=at(pool+0x28);tempHeads=w.alloc(64*8);tempTails=w.alloc(64*8);tempCounts=w.alloc(64*8);w.put(tempHeads+8,at(oldHeads+8));w.put(tempTails+8,w.pn[1]);w.put(tempCounts+8,at(oldCounts+8));w.put(pool+0x10,tempHeads);w.put(pool+0x18,tempTails);w.put(pool+0x28,tempCounts);w.put<unsigned>(pool+0x40,64);tempHandle=w.alloc(8);w.put<unsigned>(tempHandle,2);w.put(w.b+0x201D418,uint64_t(1));w.put(w.b+0x201D420,uint64_t(2));
  auto task=w.alloc(0x100),mutex=w.alloc(0x40);w.put(task+0x10,mutex);w.put<unsigned>(task+0x78,1);
  for(unsigned i=0;i<6;++i){auto object=at(w.stack+i*8),vt=at(object);w.put(object+0x50,task);w.put(vt+0x30,reinterpret_cast<uint64_t>(&readyDouble));w.put(vt+0x60,reinterpret_cast<uint64_t>(&notifyDouble));}
  configObject=w.alloc(0x200);w.put<unsigned>(configObject+0x18c,1);w.put(w.b+0x123C328,reinterpret_cast<uint64_t>(&lockDouble));w.put(w.b+0x123C0D8,reinterpret_cast<uint64_t>(&lockDouble));w.put(w.b+0x1923F90,uint64_t(0x12345678abcd));
  need(RtlAddFunctionTable(&functionEntry,1,w.b),"register unchanged original unwind table");
  reward_menu_handoff::Binding cap{};cap.base=w.b;cap.root=w.root;cap.world=w.world;cap.user=w.user;cap.state=w.state;cap.layout=w.layout;cap.thread=GetCurrentThreadId();cap.relay_rva=0x900000;cap.force=12;cap.district=11;cap.year=203;cap.month=8;cap.day=11;cap.generation=7;memset(cap.menu_id,'a',32);
  need(reward_menu_handoff::Bind(cap),"real capture binding");patchCall(w,0x67A993,0x900000,reinterpret_cast<void*>(&RewardMenuHandoffGate_Entry));
  reinterpret_cast<void(*)(uint64_t)>(w.b+0x67A930)(w.state);need(reward_menu_handoff::Inspect().captures==1,"actual Update intercepts one proposal");
  life::Config c{};c.base=w.b;c.root=w.root;c.world=w.world;c.menu=w.state;c.layout=w.layout;c.thread=GetCurrentThreadId();c.year=203;c.month=8;c.day=11;c.force=12;c.generation=7;memcpy(c.menu_id,cap.menu_id,33);for(unsigned i=0;i<5;++i)c.states[i]=at(w.stack+i*8);
  need(lifecycle.Capture(c),"actual TakeProposal transfers once");need(!lifecycle.Capture(c),"capture cannot repeat");
  DispatchFaultReturn=w.b+0x50B3A8;DispatchSuccessReturn=w.b+0x50B394;DispatchCookieReturn=w.b+0x50B669;DispatchGetter=w.b+0xF570;
  patchCall(w,0x50A9D2,0x900020,reinterpret_cast<void*>(&DispatchSelect));patchCall(w,0x50B1B8,0x900040,reinterpret_cast<void*>(&DispatchFinalized));patchCall(w,0x50B26A,0x900060,reinterpret_cast<void*>(&DispatchFreed));
  patchCall(w,0x50B41B,0x900080,reinterpret_cast<void*>(&DispatchBoundary));
  FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000);
  life::ClosedTicket ticket{};need(!lifecycle.TakeClosed(ticket),"capture is not teardown");need(lifecycle.CloseOnce(),"one native enqueue");need(!lifecycle.CloseOnce()&&at(manager+0x30)==1,"duplicate API never queues again");need(!lifecycle.TakeClosed(ticket),"queue is not teardown");
  if(mode==L"duplicate")reinterpret_cast<void(*)(uint64_t)>(w.b+0x10A60)(manager);
  if(mode==L"wrong-top"){auto extra=w.alloc(0x600);generic(w,extra,"DifferentMenu");w.put(w.stack+40,extra);auto vt=at(extra);w.put(vt+0x30,reinterpret_cast<uint64_t>(&readyDouble));w.put(vt+0x60,reinterpret_cast<uint64_t>(&notifyDouble));w.put(extra+0x50,task);}
  if(mode==L"queued-only"){need(!lifecycle.TakeClosed(ticket)&&events.empty(),"unconsumed queue cannot allow reward");}
  else {need(dispatchGuard.Enter(w.b,manager,lifecycle),"bounded dispatcher guard enters");need(DispatchInvoke(w.image+0x509FE0,manager)==1,"full archived entry/GS-cookie/epilogue restores caller registers and RSP");const bool normalReturn=dispatchGuard.Returned();need(normalReturn==!denied,"return receipt matches rejection");need(unwindVerified&&copiedFrees==1&&copiedAllocations.empty(),"full original cleanup releases copied storage before return");}
  std::vector<std::string> freed;unsigned cleanup=0;for(const auto&e:events){if(e.event=="allocator_free_double"&&e.caller==0x50B26A)freed.push_back(e.object);if(e.event!="allocator_free_double")++cleanup;}
  auto r=lifecycle.Snapshot();
  if(mode==L"normal"||mode==L"normal-freed"){
   need(!denied&&freed==std::vector<std::string>{"Reward"}&&at(manager+0x10)==5&&at(w.stack+32)==w.user&&(menuPageReleased||at(w.state+0x478)==0),"actual exact-menu teardown and original User resume");
   if(releaseMenuPage){MEMORY_BASIC_INFORMATION m{};need(menuPageReleased&&VirtualQuery(reinterpret_cast<void*>(w.state),&m,sizeof m)==sizeof m&&m.State==MEM_FREE,"old menu address is actually unmapped before ticket");}
   need(lifecycle.TakeClosed(ticket)&&ticket.teardown_observed&&!ticket.production_permit&&ticket.proposal.generation==7&&ticket.proposal.count==2&&ticket.proposal.officers[0]==97&&ticket.proposal.officers[1]==759,"same captured IDs after close");need(!lifecycle.TakeClosed(ticket),"close ticket one use");
  }else if(mode==L"wrong-top"||mode==L"duplicate")need(denied&&r.error==4&&freed.empty()&&cleanup==0&&!lifecycle.TakeClosed(ticket)&&at(manager+0x10)==6&&at(w.state+0x478)==w.layout,"consumer rejects before any pause/cleanup");
  else need(mode==L"queued-only","known mode");
  need(RtlDeleteFunctionTable(&functionEntry),"remove owned unwind table");
  auto dr=dispatchGuard.Snapshot();need(dr.returned==1&&!dr.active,"actual original dispatcher has returned");
  r=lifecycle.Snapshot();printf("{\"passed\":true,\"case\":\"%ls\",\"queued\":%llu,\"selected\":%llu,\"finalized\":%llu,\"closed\":%llu,\"taken\":%llu,\"error\":%u,\"native_cleanup_events\":%u,\"game_access\":false,\"production_permit\":false,\"full_archived_entry_exit\":true,\"original_cookie_check\":true,\"original_unwind_verified\":true,\"copied_storage_actually_freed\":true,\"native_exception_handler_executed\":false,\"task_services_double\":true}\n",mode.c_str(),r.queued,r.selected,r.finalized,r.closed,r.taken,r.error,cleanup);return 0;
 }catch(const std::exception&e){fprintf(stderr,"lifecycle fixture: %s\n",e.what());return 1;}
}
