#pragma once
// Read-only extraction of the supported planning boundary. No save/cache APIs.
#include <cstring>
#include "native_file_identity_probe_profile.h"
struct ProbeGuardSnapshot {
    uintptr_t states[5]{},root=0,world=0,cache=0,cacheSlots[120]{};
    DWORD rng=0,cacheMode=0;
};
template<class T> static T probeAt(uintptr_t p){return *reinterpret_cast<const T*>(p);}
#ifndef NATIVE_FILE_IDENTITY_FIXTURE
static bool probeIdleString(uintptr_t p){
    auto size=probeAt<uint64_t>(p+16),cap=probeAt<uint64_t>(p+24);
    if(size || cap>32768 || (cap<16&&cap!=15))return false;
    auto data=cap>=16?probeAt<uintptr_t>(p):p;
    return data>=0x10000&&probeAt<char>(data)==0;
}
static bool probeGuard(uintptr_t b,uintptr_t self,ProbeGuardSnapshot& s,bool capture){
    __try {
        const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
        auto manager=b+PROBE_MANAGER,stack=probeAt<uintptr_t>(manager+0x20);
        if(probeAt<uint64_t>(manager+0x10)!=5||probeAt<uint64_t>(manager+0x30)!=0||!stack)return false;
        if(probeAt<uintptr_t>(stack+32)!=self||probeAt<uintptr_t>(self)!=b+PROBE_USER_VT||
           probeAt<uint32_t>(self+0x470)!=2||!probeAt<uintptr_t>(self+0x478)||!probeAt<uintptr_t>(self+0x618))return false;
        for(unsigned i=0;i<5;++i){auto p=probeAt<uintptr_t>(stack+i*8);
            if(!p||std::memcmp(reinterpret_cast<void*>(p+0x70),names[i],std::strlen(names[i])+1))return false;
            if(capture)s.states[i]=p;else if(s.states[i]!=p)return false;}
        auto toolbar=probeAt<uintptr_t>(self+0x478),panel=probeAt<uintptr_t>(s.states[2]+0x480);
        if(!panel||probeAt<int32_t>(toolbar+0x88)!=-1||probeAt<uint32_t>(s.states[2]+0x47C)||probeAt<uint32_t>(panel+0x1B0))return false;
        if(probeAt<uintptr_t>(self+0x4A8)||probeAt<uintptr_t>(self+0x4B0)||probeAt<uintptr_t>(self+0x4B8))return false;
        auto special=probeAt<uintptr_t>(b+0x201EC70);
        if((special&&probeAt<uint32_t>(special))||probeAt<uint32_t>(b+0x1A38EC8+0x28)||probeAt<uint32_t>(b+0x19E7510+0x13C)!=1)return false;
        auto root=probeAt<uintptr_t>(b+0x1FCA1E0),world=probeAt<uintptr_t>(root+0x85130),cache=probeAt<uintptr_t>(b+0x2025318);
        auto rng=probeAt<DWORD>(b+0x18EB8B0);
        if(!root||!world||!cache||probeAt<uintptr_t>(root)!=b+0x12AA6B0||probeAt<uintptr_t>(world)!=b+0x12AA638)return false;
        if(probeAt<uint16_t>(world+0x34)!=203||probeAt<uint8_t>(world+0x36)!=8||probeAt<uint8_t>(world+0x37)!=11||
           probeAt<uint8_t>(world+0x3A)!=12||probeAt<uint32_t>(world+0x40)!=1||(probeAt<uint32_t>(world+0x16A8)&0x100))return false;
        if(capture){s.root=root;s.world=world;s.cache=cache;s.rng=rng;s.cacheMode=probeAt<DWORD>(cache+8);}
        else if(root!=s.root||world!=s.world||cache!=s.cache||rng!=s.rng||probeAt<DWORD>(cache+8)!=s.cacheMode)return false;
        if(s.cacheMode>1||probeAt<int32_t>(cache+0x3EC)!=-1||probeAt<uint32_t>(cache+0x3F0)||probeAt<uint64_t>(cache+0x18))return false;
        auto head=probeAt<uintptr_t>(cache+0x10);
        if(!head||probeAt<uintptr_t>(head)!=head||probeAt<uintptr_t>(head+8)!=head)return false;
        for(unsigned i=0;i<120;++i){auto value=probeAt<uintptr_t>(cache+0x20+i*8);
            if(capture)s.cacheSlots[i]=value;else if(s.cacheSlots[i]!=value)return false;}
        if(probeAt<int32_t>(b+0x201ED10)!=-1||!probeIdleString(b+0x201ED18)||!probeIdleString(b+0x201ED38))return false;
        auto force=probeAt<uintptr_t>(root+0xDCA0+12*8),person=probeAt<uintptr_t>(root+0x148+666*8);
        auto city=probeAt<uintptr_t>(root+0xDAA8+19*8),district=probeAt<uintptr_t>(root+0xDE40+11*8);
        if(probeAt<uint16_t>(force+0x10)!=666||probeAt<uint16_t>(person+0x10)!=666||probeAt<uint8_t>(person+0x118)!=11||
           probeAt<uint16_t>(person+0x11A)!=19||probeAt<uint16_t>(city+0x10)!=19||probeAt<uint8_t>(city+0x30)!=11||
           probeAt<uint32_t>(city+0x3C)!=15204||probeAt<uint8_t>(district+0x10)!=12||probeAt<uint8_t>(district+0x14)!=18)return false;
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
#endif
