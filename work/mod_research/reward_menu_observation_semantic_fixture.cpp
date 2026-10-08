// Owned process memory, synthetic CONTEXT inputs. Never calls recorder main.
#define wmain menu_recorder_entry_not_run
#include "reward_menu_observation.cpp"
#undef wmain
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
        put(b+0x19E7310+0x20,stack);put(stack+32,user);put(stack+40,state);put<uint32_t>(user+0x470,2);selectedUser=user;
        for(unsigned id=1;id<=51;++id){district[id]=obj("CDistrictData",0x40);put(root+0xDE40+id*8,district[id]);
            put<uint8_t>(district[id]+0x10,id==11?12:1);put<uint16_t>(district[id]+0x12,666);
            city[id]=obj("CCityData",0x100);put(root+0xDAA8+id*8,city[id]);put<uint16_t>(city[id]+0x10,uint16_t(id));
            put<uint8_t>(city[id]+0x30,11);put<uint16_t>(city[id]+0x4E,uint16_t(id));}
        unsigned ids[]={620,666};for(unsigned i=0;i<2;++i){person[i]=obj("CPersonData",0x200);put(root+0x148+ids[i]*8,person[i]);
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
int wmain(int argc,wchar_t**argv){
    if(argc!=3)return 2;FILE*log=_wfsopen(argv[1],L"wx",_SH_DENYNO);if(!log)return 2;
    bool rejected=false;const std::wstring mode=argv[2];
    try{
        World w;observationPid=123;observationBirth=456;observationBase=w.b;setExpectedName(L"owned-menu");emitBinding(log);
        auto hit=[&](uint64_t rva){CONTEXT c{};c.Rip=w.b+rva;c.Rsp=w.callRsp;c.Rcx=w.state;c.Rbx=w.state;c.R13=w.state;c.Rax=1;
            if(rva==0x626275){c.Rcx=w.args;c.Rsp=w.callRsp-0x890;}
            if(mode==L"wrong-rsp"&&rva==0x67A998)c.Rsp+=8;
            if(mode==L"wrong-common-frame"&&rva==0x626275)c.Rsp+=8;
            observe(log,GetCurrentProcess(),w.b,c,11);
        };
        if(mode==L"bad-type")w.put(w.state,w.b+0x123F448);
        if(mode==L"wrong-viewer")w.put<uint8_t>(w.world+0x3A,2);
        if(mode==L"bad-stack")w.put(w.stack+40,w.user);
        if(mode==L"cycle")w.put(w.pn[1]+8,w.pn[0]);
        if(mode==L"duplicate-person")w.put(w.pn[1],w.person[0]);
        if(mode==L"oversize")w.put(w.pc+8,uint64_t(65));
        if(mode==L"empty")w.put(w.state+0x488,uint64_t(0));
        if(mode==L"orphan-common"){hit(0x626275);}
        else if(mode==L"orphan-return"){hit(0x67A998);}
        else{
            hit(0x67A930);hit(0x67A930); // Stable Update is intentionally de-duplicated.
            if(mode==L"selection-change"){w.put(w.pn[0],w.person[1]);w.put(w.pn[1],w.person[0]);
                w.put<uint32_t>(w.in[0],666);w.put<uint32_t>(w.in[1],620);hit(0x67A930);}
            if(mode==L"event-one"||mode==L"idle-only"||mode==L"empty"){
                w.put<uint32_t>(w.layout+0x170,mode==L"event-one"?1U:0U);hit(0x67A930);
            }else{
                hit(0x67A993);if(mode==L"nested")hit(0x67A993);
                if(mode==L"bad-funding")w.put(w.args+0x10,w.city[20]);
                if(mode==L"different-ids")w.put<uint32_t>(w.in[0],666);
                if(mode==L"bad-predecessor")w.put(w.in[1]+16,uint64_t(0));
                if(mode!=L"wrapper-no-common")hit(0x626275);
                if(mode==L"duplicate-common")hit(0x626275);
                if(mode!=L"unreturned")hit(0x67A998);
            }
        }
    }catch(const std::exception&error){rejected=true;std::fprintf(log,"{\"event\":\"error\",\"message\":\"%s\"}\n",error.what());}
    fclose(log);std::printf("{\"rejected\":%s,\"complete\":%s,\"samples\":%llu,\"contexts_are_models\":true,\"game_access\":false}\n",rejected?"true":"false",chainComplete?"true":"false",sequence);
    return rejected?1:0;
}
