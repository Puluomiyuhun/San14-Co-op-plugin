#pragma once
#include "checkpoint_load_input_boundary.h"
#include <cstring>

// Own-process synthetic memory only, shared by isolated tests. Never include in
// a production installer. No game process/Steam access, no native game call.
namespace checkpoint_load_input_boundary_fixture {
namespace core=checkpoint_load_input_boundary;
struct Layout {
    core::Config config{};
    core::Call call{};
    void* image=nullptr;
    void* arena=nullptr;
    std::uintptr_t manager=0,stack=0,worker=0,handle=0,iterator=0,toolbar=0,panel=0,list=0,dialog=0;
    Layout()=default;
    Layout(const Layout&)=delete;
    ~Layout(){if(image)VirtualFree(image,0,MEM_RELEASE);if(arena)VirtualFree(arena,0,MEM_RELEASE);}
    template<class T> static void put(std::uintptr_t p,T v){*reinterpret_cast<T*>(p)=v;}
    template<class T> static T get(std::uintptr_t p){return *reinterpret_cast<T*>(p);}
    bool initialize(core::Stage stage=core::Stage::GameBefore){
        if(image||arena)return false;
        image=VirtualAlloc(nullptr,0x2200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        arena=VirtualAlloc(nullptr,0x100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if(!image||!arena)return false;
        config.base=reinterpret_cast<std::uintptr_t>(image);auto mem=reinterpret_cast<std::uintptr_t>(arena);
        config.attempt=17;config.expectedRng=0x12345678;
        for(unsigned i=0;i<5;++i)config.states[i]=mem+0x10000+i*0x1000;
        config.menu=mem+0x15000;config.root=mem+0x30000;config.world=mem+0xC0000;
        config.cache=mem+0x50000;config.keyboard=mem+0x60000;
        manager=config.base+0x19E7310;stack=mem+0x1000;
        worker=mem+0x20000;handle=mem+0x21000;iterator=mem+0x22000;
        toolbar=mem+0x70000;panel=mem+0x71000;list=mem+0x72000;dialog=mem+0x73000;
        put<std::uint64_t>(manager+0x10,6);put<std::uintptr_t>(manager+0x20,stack);
        const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState","CSaveLoadState"};
        for(unsigned i=0;i<6;++i){auto p=i<5?config.states[i]:config.menu;
            put<std::uintptr_t>(stack+i*8,p);std::memcpy(reinterpret_cast<void*>(p+0x70),names[i],std::strlen(names[i])+1);}
        put<std::uintptr_t>(config.states[4],config.base+0x12CC4A8);
        put<std::uintptr_t>(config.states[2],config.base+0x12CC9B8);
        put<std::uintptr_t>(config.menu,config.base+0x12DB4C0);
        put<DWORD>(config.states[4]+0x470,2);
        put<std::uintptr_t>(config.states[4]+0x478,toolbar);put<std::int32_t>(toolbar+0x88,-1);
        put<std::uintptr_t>(config.states[2]+0x480,panel);
        put<DWORD>(config.base+0x1A38EC8+0x28,1);
        put<std::uintptr_t>(config.menu+0x470,list);put<std::uintptr_t>(config.menu+0x478,dialog);
        put<std::uintptr_t>(list,config.base+0x12DBA18);put<std::int32_t>(list+0x170,-1);
        put<std::uintptr_t>(config.base+0x1FCA1E0,config.root);
        put<std::uintptr_t>(config.root+0x85130,config.world);
        put<std::uintptr_t>(config.base+0x2025318,config.cache);
        put<std::int32_t>(config.cache+0x3EC,-1);
        put<std::uint16_t>(config.world+0x34,config.year);put<std::uint8_t>(config.world+0x36,config.month);
        put<std::uint8_t>(config.world+0x37,config.day);put<std::uint8_t>(config.world+0x3A,config.force);
        put<DWORD>(config.world+0x40,1);put<DWORD>(config.base+0x18EB8B0,config.expectedRng);
        put<std::uintptr_t>(config.base+0x1FCA0A0,config.keyboard);
        put<DWORD>(config.base+0x1FCA0A0+12,1);
        setStage(stage);return true;
    }
    void setStage(core::Stage stage){
        for(unsigned i=0;i<5;++i)put<std::uintptr_t>(config.states[i]+0x50,0);
        put<std::uintptr_t>(config.menu+0x50,0);
        const unsigned index=stage==core::Stage::MenuAfter?5:2;
        const auto current=index==5?config.menu:config.states[2];
        put<DWORD>(current+0x6C,3);
        put<std::uintptr_t>(current+0x50,worker);put<std::uintptr_t>(manager+0x48,current);
        put<std::uintptr_t>(worker+8,handle);put<DWORD>(handle+0x10,GetCurrentThreadId());
        const auto callable=worker+0x18;
        put<std::uintptr_t>(worker+0x50,callable);put<std::uintptr_t>(callable,config.base+0x12F2440);
        put<std::uintptr_t>(config.base+0x12F2440+0x10,config.base+0x50B730);
        put<std::uintptr_t>(callable+8,iterator);put<std::uintptr_t>(iterator,stack+index*8);
        call=core::Call{};call.stage=stage;call.args[0]=current;
        for(unsigned i=1;i<4;++i){call.args[i]=0x1000+i;put<std::uint64_t>(callable+8+i*8,call.args[i]);}
        call.thread=call.pairedThread=GetCurrentThreadId();call.callId=call.pairedCallId=18;
        call.callerEntryRsp=iterator+0x100;call.pairedWorker=worker;
        put<std::uintptr_t>(call.callerEntryRsp,config.base+0x50B785);
        call.originalReturned=stage==core::Stage::MenuAfter;
    }
};
}
