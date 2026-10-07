struct ModePinned {
    uintptr_t states[5]{},root=0,world=0,cache=0;
    DWORD rng=0;
    unsigned char loadGlobals[0x38]{},saveGlobals[0x50]{};
    DWORD loadResult=0,saveResult=0;
};
static ModePinned pinned{};
static bool emptyString(uintptr_t p){
    auto n=at<uint64_t>(p+16),cap=at<uint64_t>(p+24);
    if(n||cap>32768||(cap<16&&cap!=15))return false;
    auto data=cap>=16?at<uintptr_t>(p):p;return data>=0x10000&&at<char>(data)==0;
}
static bool cacheGraph(bool emptyTable){
    uintptr_t nodes[600]{},heads[5]{},counts[5]{},starts[606]{},ends[606]{};unsigned used=0,spans=1;
    starts[0]=pinned.cache;ends[0]=pinned.cache+0x440;
    if(pinned.cache<0x10000||ends[0]>0x00007FFFFFFFFFFFull)return false;
    for(unsigned g=0;g<5;++g){
        auto owner=pinned.cache+(g?0x400+(g-1)*16:0x10);
        heads[g]=at<uintptr_t>(owner);counts[g]=at<uint64_t>(owner+8);
        if(heads[g]<0x10000||heads[g]>0x00007FFFFFFFFFEFull||counts[g]>120||(g==0&&counts[g]))return false;
        for(unsigned s=0;s<spans;++s)if(heads[g]<ends[s]&&starts[s]<heads[g]+16)return false;
        starts[spans]=heads[g];ends[spans++]=heads[g]+16;
    }
    for(unsigned g=0;g<5;++g){
        auto head=heads[g],count=counts[g];
        auto node=at<uintptr_t>(head),previous=head;
        for(uint64_t i=0;i<count;++i){
            if(node<0x10000||node>0x00007FFFFFFFFE9Full||node==head||at<uintptr_t>(node+8)!=previous)return false;
            for(unsigned s=0;s<spans;++s)if(node<ends[s]&&starts[s]<node+0x160)return false;
            starts[spans]=node;ends[spans++]=node+0x160;
            nodes[used++]=node;previous=node;node=at<uintptr_t>(node);
        }
        if(node!=head||at<uintptr_t>(head+8)!=previous)return false;
    }
    for(unsigned slot=0;slot<120;++slot){
        auto value=at<uintptr_t>(pinned.cache+0x20+slot*8);if(!value)continue;
        if(emptyTable)return false;bool found=false;
        for(unsigned before=0;before<slot;++before)if(at<uintptr_t>(pinned.cache+0x20+before*8)==value)return false;
        for(unsigned j=0;j<used;++j)if(nodes[j]+16==value)found=true;
        if(!found)return false;
    }
    return true;
}
static bool modeGuard(uintptr_t self,DWORD phase,bool capture=false){
    __try {
        auto manager=base+0x19E7310,stack=at<uintptr_t>(manager+0x20);
        const unsigned count=phase==LM_GUARD_MENU?6:5;
        if(!stack||at<uint64_t>(manager+0x10)!=count||at<uint64_t>(manager+0x30))return false;
        const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
        for(unsigned i=0;i<5;++i){auto statePtr=at<uintptr_t>(stack+i*8);
            if(!statePtr||memcmp(reinterpret_cast<void*>(statePtr+0x70),names[i],strlen(names[i])+1))return false;
            if(capture)pinned.states[i]=statePtr;else if(pinned.states[i]!=statePtr)return false;}
        if(pinned.states[4]!=cfg.expectedUser||at<uintptr_t>(pinned.states[4])!=base+0x12CC4A8||
           at<DWORD>(pinned.states[4]+0x470)!=2||!at<uintptr_t>(pinned.states[4]+0x618))return false;
        if(phase==LM_GUARD_MENU){
            if(self!=report.queuedState||at<uintptr_t>(stack+40)!=self||at<uintptr_t>(self)!=base+0x12DB4C0||
               memcmp(reinterpret_cast<void*>(self+0x70),"CSaveLoadState",15)||at<uintptr_t>(self+0x48))return false;
            auto list=at<uintptr_t>(self+0x470),dialog=at<uintptr_t>(self+0x478);
            if(!list||!dialog||at<uintptr_t>(list)!=base+0x12DBA18||at<int32_t>(list+0x170)!=-1)return false;
        }else if(self!=pinned.states[4])return false;
        auto toolbar=at<uintptr_t>(pinned.states[4]+0x478),panel=at<uintptr_t>(pinned.states[2]+0x480);
        if(!toolbar||!panel||at<int32_t>(toolbar+0x88)!=-1||at<DWORD>(pinned.states[2]+0x47C)||at<DWORD>(panel+0x1B0))return false;
        for(auto off:{0x4A8,0x4B0,0x4B8})if(at<uintptr_t>(pinned.states[4]+off))return false;
        auto special=at<uintptr_t>(base+0x201EC70);
        if((special&&at<DWORD>(special))||at<DWORD>(base+0x1A38EC8+0x28)!=(phase==LM_GUARD_MENU?1u:0u)||
           at<DWORD>(base+0x19E7510+0x13C)!=(phase==LM_GUARD_MENU?0u:1u))return false;
        auto capacity=at<uint64_t>(manager+0x38),data=at<uintptr_t>(manager+0x40);
        if(capacity>4096||((capacity==0)!=(data==0)))return false;
        if(data&&(data<0x10000||data>0x00007FFFFFFFFFFFULL-capacity*16))return false;
        for(auto off:{0,0x28}){auto alloc=at<uintptr_t>(manager+off);if(!alloc||at<uintptr_t>(alloc)!=base+0x1283498)return false;}
        const uintptr_t av=base+0x1283498;
        if(at<uintptr_t>(av+0x28)!=base+0x12C840||at<uintptr_t>(av+0x38)!=base+0x12C290||
           at<uintptr_t>(av+0x40)!=base+0x8388D0||at<uintptr_t>(av+0x48)!=base+0x1479B0)return false;
        auto root=at<uintptr_t>(base+0x1FCA1E0),world=at<uintptr_t>(root+0x85130),cache=at<uintptr_t>(base+0x2025318);
        if(!root||!world||!cache||at<uintptr_t>(root)!=base+0x12AA6B0||at<uintptr_t>(world)!=base+0x12AA638)return false;
        if(capture){pinned.root=root;pinned.world=world;pinned.cache=cache;pinned.rng=at<DWORD>(base+0x18EB8B0);
            memcpy(pinned.loadGlobals,reinterpret_cast<void*>(base+0x201ECD0),sizeof pinned.loadGlobals);
            memcpy(pinned.saveGlobals,reinterpret_cast<void*>(base+0x201ED10),sizeof pinned.saveGlobals);
            pinned.loadResult=at<DWORD>(base+0x201EC08);pinned.saveResult=at<DWORD>(base+0x201EC2C);}
        else if(root!=pinned.root||world!=pinned.world||cache!=pinned.cache||at<DWORD>(base+0x18EB8B0)!=pinned.rng)return false;
        if(at<uint16_t>(world+0x34)!=203||at<uint8_t>(world+0x36)!=8||at<uint8_t>(world+0x37)!=11||
           at<uint8_t>(world+0x3A)!=12||at<DWORD>(world+0x40)!=1||(at<DWORD>(world+0x16A8)&0x100))return false;
        if(at<DWORD>(cache+8)!=(phase==LM_GUARD_INITIAL?1u:0u)||at<DWORD>(cache+0x3F0)||at<int32_t>(cache+0x3EC)!=-1||!cacheGraph(phase==LM_GUARD_INITIAL))return false;
        if(memcmp(pinned.loadGlobals,reinterpret_cast<void*>(base+0x201ECD0),sizeof pinned.loadGlobals)||
           memcmp(pinned.saveGlobals,reinterpret_cast<void*>(base+0x201ED10),sizeof pinned.saveGlobals)||
           at<DWORD>(base+0x201EC08)!=pinned.loadResult||at<DWORD>(base+0x201EC2C)!=pinned.saveResult)return false;
        if(at<int32_t>(base+0x201ED10)!=-1||!emptyString(base+0x201ED18)||!emptyString(base+0x201ED38))return false;
        auto force=at<uintptr_t>(root+0xDCA0+12*8),person=at<uintptr_t>(root+0x148+666*8);
        auto city=at<uintptr_t>(root+0xDAA8+19*8),district=at<uintptr_t>(root+0xDE40+11*8);
        return at<uint16_t>(force+0x10)==666&&at<uint16_t>(person+0x10)==666&&at<uint8_t>(person+0x118)==11&&
            at<uint16_t>(person+0x11A)==19&&at<uint16_t>(city+0x10)==19&&at<uint8_t>(city+0x30)==11&&
            at<DWORD>(city+0x3C)==15204&&at<uint8_t>(district+0x10)==12&&at<uint8_t>(district+0x14)==18;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
