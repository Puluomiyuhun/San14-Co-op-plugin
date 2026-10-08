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
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
extern "C" void CompletionQueueTail(void*);
extern "C" void CompletionConsume(void*,uint64_t);
extern "C" void CompletionConsumeReturn();
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
static void __fastcall freeDouble(uint64_t,uint64_t object){record("allocator_free_double",object,reinterpret_cast<uint64_t>(_ReturnAddress()));}
static void __fastcall growDouble(uint64_t vector,uint64_t capacity){need(capacity>0&&capacity<=64,"bounded native vector allocation");
    auto&w=*fixture;auto previous=at(vector),oldEnd=at(vector+8);need(oldEnd>=previous&&oldEnd-previous<=capacity*16,"vector growth size");
    auto buffer=w.alloc(size_t(capacity)*16);if(previous)memcpy(reinterpret_cast<void*>(buffer),reinterpret_cast<void*>(previous),size_t(oldEnd-previous));
    w.put(vector,buffer);w.put(vector+8,buffer+(oldEnd-previous));w.put(vector+16,buffer+capacity*16);
}
static void jump(World&w,uint64_t rva,void* target){unsigned char code[12]={0x48,0xB8};auto address=reinterpret_cast<uint64_t>(target);memcpy(code+2,&address,8);code[10]=0xFF;code[11]=0xE0;memcpy(w.image+rva,code,sizeof code);}
static void load(World&w,const wchar_t* path){std::ifstream file(path,std::ios::binary);need(bool(file),"explicit owned code input");
    std::vector<char> bytes((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
    struct Range {unsigned start,end;};const Range ranges[]={{0x67A99C,0x67A9AE},{0x10A60,0x10AEA},{0x50A7BA,0x50B3B6},{0x667B10,0x667B98},{0x60B000,0x60B065},{0x6115A0,0x6115D4},{0x665CD0,0x665CD6}};
    size_t n=0;for(const auto&r:ranges){need(n+(r.end-r.start)<=bytes.size(),"truncated bounded archive");memcpy(w.image+r.start,bytes.data()+n,r.end-r.start);n+=r.end-r.start;}need(n==bytes.size(),"extra bounded archive bytes");
    jump(w,0xF690,reinterpret_cast<void*>(&managerDouble));jump(w,0x50B7A0,reinterpret_cast<void*>(&growDouble));
    jump(w,0x1FED80,reinterpret_cast<void*>(&listDouble));jump(w,0x50B3B6,reinterpret_cast<void*>(&CompletionConsumeReturn));
    DWORD old=0;need(VirtualProtect(w.image,0x2400000,PAGE_EXECUTE_READWRITE,&old)!=0,"owned code protection");need(FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000)!=0,"owned flush");
}
static void generic(World&w,uint64_t object,const char* label){names[object]=label;auto vt=w.alloc(0x100);w.put(object,vt);
    w.put(vt,reinterpret_cast<uint64_t>(&destructorDouble));w.put(vt+0x10,reinterpret_cast<uint64_t>(&finalizeDouble));
    w.put(vt+0x18,reinterpret_cast<uint64_t>(&resumeDouble));w.put(vt+0x20,reinterpret_cast<uint64_t>(&pauseDouble));w.put<uint32_t>(object+0x6C,1);
}
int wmain(int argc,wchar_t**argv){if(argc!=3)return 2;
    try{
        World w;fixture=&w;load(w,argv[1]);const std::wstring mode=argv[2];const auto manager=w.b+0x19E7310;
        names[w.state]="Reward";generic(w,w.user,"User");
        const char*lower[]={"Root","Motor","Game","Strategy"};for(unsigned i=0;i<4;++i){auto p=w.alloc(0x600);generic(w,p,lower[i]);w.put(w.stack+i*8,p);}
        auto menuVt=at(w.state);w.put(menuVt,w.b+0x6115A0);w.put(menuVt+0x10,w.b+0x667B10);w.put(menuVt+0x18,w.b+0x665CD0);w.put(menuVt+0x20,w.b+0x665CD0);w.put<uint32_t>(w.state+0x6C,1);
        auto layoutVt=w.alloc(0x100);w.put(w.layout,layoutVt);w.put(layoutVt,reinterpret_cast<uint64_t>(&deleteLayoutDouble));
        w.put(layoutVt+0x40,reinterpret_cast<uint64_t>(&beforeDouble));w.put(layoutVt+0x28,reinterpret_cast<uint64_t>(&contextDouble));w.put<uint32_t>(w.layout+0x168,77);
        auto allocator=w.alloc(16),allocatorVt=w.alloc(0x100);w.put(allocator,allocatorVt);w.put(allocatorVt+0x58,reinterpret_cast<uint64_t>(&freeDouble));
        w.put(manager,allocator);w.put(manager+0x28,allocator);auto pending=w.alloc(64*16);names[pending]="PendingStorage";
        w.put(manager+0x30,uint64_t(0));w.put(manager+0x38,uint64_t(64));w.put(manager+0x40,pending);
        auto enqueue=[&]{CompletionQueueTail(w.image+0x67A99C);need(at(manager+0x30)>0,"native queue did not grow");
            const auto q=at(manager+0x40)+(at(manager+0x30)-1)*16;need(*reinterpret_cast<uint32_t*>(q)==1&&at(q+8)==0,"queue is not untagged pop");};
        auto consume=[&]{CompletionConsume(w.image+0x50A7BA,manager);need(at(manager+0x30)==0&&at(manager+0x40)==0&&at(manager+0x38)==0,"native pending owner not cleared");};
        if(mode!=L"empty-consume")enqueue();
        if(mode==L"duplicate-pop")enqueue();
        uint64_t extra=0;
        if(mode==L"changed-top-push"||mode==L"changed-top-replace"){
            extra=w.alloc(0x600);generic(w,extra,"DifferentMenu");
            if(mode==L"changed-top-push"){w.put(w.stack+48,extra);w.put(manager+0x10,uint64_t(7));}
            else w.put(w.stack+40,extra);
        }
        const auto queued=at(manager+0x30);const auto topBefore=at(w.stack+(at(manager+0x10)-1)*8);
        if(mode!=L"queued-only")consume();
        if(mode==L"late-duplicate"){
            // Re-establish only allocator capacity for a second independent
            // source-tail invocation. The stack is already back at User.
            w.put(manager+0x38,uint64_t(64));w.put(manager+0x40,pending);enqueue();consume();
        }
        const auto remaining=at(manager+0x10);const auto layoutAfter=at(w.state+0x478);
        std::vector<std::string> freed;for(const auto&e:events)if(e.event=="allocator_free_double"&&e.caller==0x50B26A)freed.push_back(e.object);
        if(mode==L"normal")need(freed==std::vector<std::string>{"Reward"}&&remaining==5&&layoutAfter==0&&at(w.stack+32)==w.user,"normal source route");
        else if(mode==L"duplicate-pop"||mode==L"late-duplicate")need(freed==std::vector<std::string>{"Reward","User"}&&remaining==4,"duplicate pop risk not demonstrated");
        else if(mode==L"changed-top-push")need(freed==std::vector<std::string>{"DifferentMenu"}&&remaining==6&&layoutAfter==w.layout&&at(w.stack+40)==w.state,"different pushed top not popped");
        else if(mode==L"changed-top-replace")need(freed==std::vector<std::string>{"DifferentMenu"}&&remaining==5&&layoutAfter==w.layout,"replacement top not popped");
        else if(mode==L"queued-only")need(freed.empty()&&remaining==6&&layoutAfter==w.layout&&queued==1,"enqueue is not close");
        else if(mode==L"empty-consume")need(freed.empty()&&remaining==6&&layoutAfter==w.layout,"empty consume changed menu");
        else throw std::runtime_error("unknown fixture mode");
        FILETIME creation{},exit{},kernel{},user{};need(GetProcessTimes(GetCurrentProcess(),&creation,&exit,&kernel,&user)!=0,"owned process birth");
        const auto birth=(uint64_t(creation.dwHighDateTime)<<32)|creation.dwLowDateTime;
        std::printf("{\"root\":%llu,\"world\":%llu,\"viewer\":%u,\"date\":[%u,%u,%u],",w.root,w.world,unsigned(*reinterpret_cast<unsigned char*>(w.world+0x3A)),unsigned(*reinterpret_cast<unsigned short*>(w.world+0x34)),unsigned(*reinterpret_cast<unsigned char*>(w.world+0x36)),unsigned(*reinterpret_cast<unsigned char*>(w.world+0x37)));
        std::printf("\"schema\":\"san14.reward-menu-completion-owned-trace.v1\",\"passed\":true,\"pid\":%u,\"birth\":%llu,\"thread\":%u,\"base\":%llu,\"menu\":%llu,\"user\":%llu,\"queued_before_consume\":%llu,\"top_before_consume\":\"%s\",\"remaining\":%llu,\"reward_layout_cleared\":%s,\"final_top\":\"%s\",\"events\":[",GetCurrentProcessId(),birth,GetCurrentThreadId(),w.b,w.state,w.user,queued,name(topBefore).c_str(),remaining,layoutAfter==0?"true":"false",name(at(w.stack+(remaining-1)*8)).c_str());
        for(size_t i=0;i<events.size();++i){const auto&e=events[i];std::printf("%s{\"seq\":%zu,\"event\":\"%s\",\"caller_rva\":%llu,\"thread\":%u,\"object\":\"%s\",\"top\":\"%s\",\"count\":%llu,\"queue\":%llu,\"layout_nonzero\":%s}",i?",":"",i+1,e.event.c_str(),e.caller,e.thread,e.object.c_str(),e.top.c_str(),e.count,e.queue,e.layout?"true":"false");}
        std::puts("],\"success_branch_selected_by_fixture\":true,\"authority_did_not_drive_native_close\":true,\"full_dispatcher_executed\":false,\"menu_lifetime_lock\":false,\"game_access\":false,\"production_permit\":false}");return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"completion fixture failed: %s\n",e.what());return 1;}
}
