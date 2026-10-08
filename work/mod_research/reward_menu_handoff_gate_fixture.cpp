// Owned memory builder derived from frozen reward_menu_observation_semantic_fixture.cpp.
// No observer/debugger code is included or invoked. IDs match the existing TLS fixture.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <stdexcept>
#include <vector>
#include <thread>
#include "reward_menu_handoff_gate.h"
using namespace reward_menu_handoff;
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
extern "C" int InvokeOwnedUpdate(void*,uint64_t);
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
static unsigned wrappers=0,commons=0,pops=0,others=0,input=0,layoutBefore=0,layoutContext=0,layoutDelete=0,exitNotify=0,listDestroy=0;
static uint64_t expectedState=0,expectedLayout=0;
static std::vector<std::string> teardown;
static int __fastcall commonDouble(){++commons;return 1;}
static int __fastcall wrapperDouble(uint64_t state){need(state==expectedState,"wrapper state");++wrappers;return commonDouble();}
static uint64_t __fastcall managerDouble(){return 0x12345678;}
static void __fastcall popDouble(uint64_t manager){need(manager==0x12345678,"manager double");++pops;}
static int __fastcall inputDouble(){++input;return 0;}
static void __fastcall noopDouble(){}
static void __fastcall otherDouble(uint64_t state){need(state==expectedState,"other state");++others;}
static void __fastcall beforeDouble(uint64_t layout){need(layout==expectedLayout,"exit before layout");++layoutBefore;teardown.push_back("layout_before");}
static void __fastcall contextDouble(uint64_t layout,uint64_t context){need(layout==expectedLayout&&context==0x987654,"exit context");++layoutContext;teardown.push_back("layout_context");}
static void __fastcall deleteDouble(uint64_t layout,unsigned flags){need(layout==expectedLayout&&flags==1,"exit delete");++layoutDelete;teardown.push_back("layout_delete");}
static void __fastcall notifyDouble(uint64_t, uint64_t* state){need(*state==expectedState,"exit callback");++exitNotify;teardown.push_back("exit_notify");}
static void __fastcall listDouble(uint64_t list){need(list==expectedState+0x480,"destructor list");++listDestroy;}
static void jump(World& w,uint64_t rva,void* target){unsigned char bytes[12]={0x48,0xB8};auto address=reinterpret_cast<uint64_t>(target);
    memcpy(bytes+2,&address,8);bytes[10]=0xFF;bytes[11]=0xE0;memcpy(w.image+rva,bytes,sizeof bytes);}
static void patch(World& w,uint32_t relay){unsigned char code[5]={0xE8};auto delta=int32_t(relay-0x67A998);memcpy(code+1,&delta,4);
    memcpy(w.image+0x67A993,code,sizeof code);FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000);}
static void codes(World& w,const wchar_t* path){std::ifstream f(path,std::ios::binary);need(bool(f),"archive code input");
    std::vector<char> bytes((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
    need(bytes.size()==145+136+101,"unexpected bounded code input");
    memcpy(w.image+0x67A930,bytes.data(),145);memcpy(w.image+0x667B10,bytes.data()+145,136);memcpy(w.image+0x60B000,bytes.data()+281,101);
    jump(w,0x626050,reinterpret_cast<void*>(&wrapperDouble));jump(w,0xF690,reinterpret_cast<void*>(&managerDouble));
    jump(w,0x10A60,reinterpret_cast<void*>(&popDouble));jump(w,0x3A29E0,reinterpret_cast<void*>(&inputDouble));
    jump(w,0x76ECB0,reinterpret_cast<void*>(&noopDouble));jump(w,0x3A2700,reinterpret_cast<void*>(&noopDouble));
    jump(w,0x68F760,reinterpret_cast<void*>(&otherDouble));jump(w,0x1FED80,reinterpret_cast<void*>(&listDouble));
    jump(w,0x900000,reinterpret_cast<void*>(&RewardMenuHandoffGate_Entry));
    DWORD old=0;need(VirtualProtect(w.image,0x2400000,PAGE_EXECUTE_READWRITE,&old)!=0,"owned executable map");
    need(FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000)!=0,"owned code flush");
}
static void emit(const Proposal& p,bool took){auto r=Inspect();
    std::printf("{\"last_rejection\":%u,\"rejections\":%llu,",unsigned(r.last_rejection),r.rejections);
    std::printf("\"passed\":true,\"phase\":%u,\"error\":%u,\"calls\":%llu,\"captures\":%llu,\"takes\":%llu,\"took\":%s,\"wrapper_double_calls\":%u,\"common_double_calls\":%u,\"pop_double_calls\":%u,\"other_double_calls\":%u,\"input_double_calls\":%u,\"layout_before\":%u,\"layout_context\":%u,\"layout_delete\":%u,\"exit_notify\":%u,\"list_destroy\":%u,\"production_permit\":false,\"game_access\":false,\"proposal\":",
        unsigned(r.phase),unsigned(r.error),r.calls,r.captures,r.takes,took?"true":"false",wrappers,commons,pops,others,input,layoutBefore,layoutContext,layoutDelete,exitNotify,listDestroy);
    if(!took){std::puts("null}");return;}
    std::printf("{\"version\":%u,\"generation\":%llu,\"menu_id\":\"%s\",\"preview\":{\"kind\":\"reward\",\"force_id\":%u,\"district_id\":%u,\"funding_city_id\":%u,\"officer_ids\":[",p.version,p.generation,p.menu_id,p.force,p.district,p.funding_city);
    for(unsigned i=0;i<p.count;++i)std::printf("%s%u",i?",":"",p.officers[i]);std::puts("]}}}");
}
int wmain(int argc,wchar_t**argv){if(argc!=3)return 2;
    try{
        World w;codes(w,argv[1]);const std::wstring mode=argv[2];expectedState=w.state;expectedLayout=w.layout;
        auto update=[&]{need(InvokeOwnedUpdate(w.image+0x67A930,w.state)==1,"archived Update RBX/RSP/return failed");};
        auto vtable=w.alloc(0x200),callback=w.alloc(16),callbackVtable=w.alloc(0x40);
        w.put(w.layout,vtable);w.put(vtable+0x40,reinterpret_cast<uint64_t>(&beforeDouble));w.put(vtable+0x28,reinterpret_cast<uint64_t>(&contextDouble));
        w.put(vtable,reinterpret_cast<uint64_t>(&deleteDouble));w.put<uint32_t>(w.layout+0x168,77);
        w.put(callback,callbackVtable);w.put(callbackVtable+0x10,reinterpret_cast<uint64_t>(&notifyDouble));w.put(w.state+0x48,callback);
        Binding b;b.base=w.b;b.root=w.root;b.world=w.world;b.user=w.user;b.state=w.state;b.layout=w.layout;
        b.thread=GetCurrentThreadId();b.relay_rva=0x900000;b.force=12;b.district=11;b.year=203;b.month=8;b.day=11;b.generation=1;
        memcpy(b.menu_id,"123456789abcdef0123456789abcdef0",33);Proposal out;bool took=false;
        if(mode==L"unpatched-control"){update();update();need(wrappers==2&&commons==2&&pops==2,"natural double path");emit(out,false);return 0;}
        if(mode==L"bad-bind-source")w.image[0x67A993]=0x90;
        if(mode==L"bad-bind-source"){need(!Bind(b)&&Inspect().phase==Phase::fault,"wrong original source accepted");emit(out,false);return 0;}
        need(Bind(b),"binding failed");patch(w,b.relay_rva);
        if(mode==L"idle"||mode==L"event-one"){
            w.put<uint32_t>(w.layout+0x170,mode==L"idle"?0:1);update();
            need(Inspect().calls==0&&Inspect().captures==0,"non-confirm captured");
            need((mode==L"idle"?input:others)==1,"branch double missing");emit(out,false);return 0;
        }
        if(mode==L"rebind"){need(!Bind(b),"rebind allowed");update();}
        else if(mode==L"foreign-call"){need(RewardMenuHandoffGate_Entry(w.state)==0,"foreign return");}
        else if(mode==L"wrong-thread"){std::thread t(update);t.join();}
        else if(mode==L"source-tamper"){
            // Change displacement only to another relay to the same gate: entry is
            // still reached with the real return PC, but registered source differs.
            jump(w,0x900020,reinterpret_cast<void*>(&RewardMenuHandoffGate_Entry));patch(w,0x900020);update();
        }
        else if(mode==L"relay-tamper"){
            unsigned char relay[13]={0x49,0xBB};const auto address=reinterpret_cast<uint64_t>(&RewardMenuHandoffGate_Entry);
            memcpy(relay+2,&address,8);relay[10]=0x41;relay[11]=0xFF;relay[12]=0xE3;
            memcpy(w.image+b.relay_rva,relay,sizeof relay);FlushInstructionCache(GetCurrentProcess(),w.image+b.relay_rva,sizeof relay);update();
        }
        else if(mode==L"retire-before"){Retire();update();}
        else {
            if(mode==L"wrong-world"){auto other=w.alloc(0x1000);memcpy(reinterpret_cast<void*>(other),reinterpret_cast<void*>(w.world),0x1000);w.put(w.root+0x85130,other);}
            if(mode==L"wrong-viewer")w.put<uint8_t>(w.world+0x3A,2);
            if(mode==L"wrong-date")w.put<uint8_t>(w.world+0x37,21);
            if(mode==L"wrong-stack")w.put(w.stack+40,w.user);
            if(mode==L"wrong-layout"){auto other=w.alloc(0x400);memcpy(reinterpret_cast<void*>(other),reinterpret_cast<void*>(w.layout),0x400);w.put(w.state+0x478,other);}
            if(mode==L"empty")w.put(w.state+0x488,uint64_t(0));
            if(mode==L"cycle")w.put(w.pn[1]+8,w.pn[0]);
            if(mode==L"duplicate-person")w.put(w.pn[1],w.person[0]);
            if(mode==L"oversize")w.put(w.pc+8,uint64_t(17));
            if(mode==L"unreadable-world")w.put(w.root+0x85130,uint64_t(0x10000));
            update();
        }
        const bool faultBefore=(mode==L"foreign-call"||mode==L"wrong-thread"||mode==L"source-tamper"||mode==L"relay-tamper"||mode==L"wrong-world"||mode==L"wrong-viewer"||mode==L"wrong-date"||mode==L"wrong-stack"||mode==L"wrong-layout"||mode==L"empty"||mode==L"cycle"||mode==L"duplicate-person"||mode==L"oversize"||mode==L"unreadable-world");
        if(faultBefore){need(Inspect().phase==Phase::fault&&Inspect().captures==0,"unsafe capture");}
        else if(mode==L"retire-before"){need(Inspect().phase==Phase::retired&&Inspect().captures==0,"retired captured");}
        else{
            need(Inspect().phase==Phase::pending&&Inspect().captures==1,"expected pending");
            if(mode==L"repeat"||mode==L"duplicate-take"||mode==L"take-once"||mode==L"rebind")for(unsigned i=0;i<8;++i)update();
            if(mode==L"change-before-take"||mode==L"change-on-repeat"){w.put(w.pn[0],w.person[1]);w.put(w.pn[1],w.person[0]);if(mode==L"change-on-repeat")update();}
            if(mode==L"event-reset")w.put<uint32_t>(w.layout+0x170,0);
            if(mode==L"retire-pending")Retire();
            if(mode==L"exit-pending"){
                reinterpret_cast<void(__fastcall*)(uint64_t,uint64_t)>(w.image+0x667B10)(w.state,0x987654);
                need(*reinterpret_cast<uint64_t*>(w.state+0x478)==0&&*reinterpret_cast<uint32_t*>(w.state+8)==77,"archived exit writes");
                need(layoutBefore==1&&layoutContext==1&&layoutDelete==1&&exitNotify==1,"archived exit call sequence");
                need(teardown==std::vector<std::string>{"layout_before","layout_context","layout_delete","exit_notify"},"teardown helper order");
            }
            if(mode==L"destroy-pending"){
                w.put(w.state+0x48,uint64_t(0));reinterpret_cast<void(__fastcall*)(uint64_t)>(w.image+0x60B000)(w.state);
                need(listDestroy==1,"archived destructor list release");
            }
            if(mode==L"wrong-claim"){need(!TakeProposal("00000000000000000000000000000000",1,out)&&Inspect().phase==Phase::pending,"foreign claim consumed");}
            if(mode==L"wrong-generation"){need(!TakeProposal(b.menu_id,2,out)&&Inspect().phase==Phase::pending,"foreign generation consumed");}
            if(mode==L"take-wrong-thread"){std::thread t([&]{Proposal temporary;need(!TakeProposal(b.menu_id,1,temporary),"wrong-thread claim succeeded");});t.join();}
            took=TakeProposal(b.menu_id,1,out);
            const bool reject=(mode==L"change-before-take"||mode==L"change-on-repeat"||mode==L"event-reset"||mode==L"retire-pending"||mode==L"exit-pending"||mode==L"destroy-pending"||mode==L"take-wrong-thread");
            need(took!=reject,"claim outcome");
            if(took){need(out.count==2&&out.officers[0]==97&&out.officers[1]==759,"claimed selection differs");
                if(mode==L"duplicate-take"){Proposal second;need(!TakeProposal(b.menu_id,1,second)&&second.count==0&&Inspect().takes==1,"duplicate claim");}
                if(mode==L"change-after-take"){w.put(w.pn[0],w.person[1]);w.put(w.pn[1],w.person[0]);update();need(Inspect().phase==Phase::fault&&Inspect().proposal_was_taken,"post-claim change not held");}
                if(mode==L"retire-taken"){Retire();update();need(Inspect().phase==Phase::retired,"retire did not hold");}
                if(mode==L"duplicate-take"||mode==L"wrong-claim"||mode==L"wrong-generation"||mode==L"rebind")
                    need(Inspect().phase==Phase::taken&&Inspect().error==Error::none&&Inspect().rejections==1&&Inspect().last_rejection!=Error::none,"nonterminal rejection mixed with fault");
            }
        }
        need(wrappers==0&&commons==0&&pops==0,"natural reward route escaped gate");
        need(!Inspect().production_permit,"production permit fabricated");emit(out,took);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"fixture failure: %s\n",e.what());return 1;}
}
