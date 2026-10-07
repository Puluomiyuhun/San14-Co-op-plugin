// Synthetic observation payload test, not execution of native game logic.
#define wmain unused_observer_main
#include "observe_startup_identity.cpp"
#undef wmain
#include <array>
template<class T>static void put(uint64_t at,T value){std::memcpy(reinterpret_cast<void*>(at),&value,sizeof value);}
static void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
int wmain(int argc,wchar_t** argv){
    if(argc!=2)return 2;
    unsigned char* module=nullptr;FILE* log=nullptr;
    try{
        module=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2240000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));require(module!=nullptr,"module allocation");
        const auto base=reinterpret_cast<uint64_t>(module);
        std::vector<unsigned char> rootBytes(0x86000),worldBytes(0x2200),stateBytes(0x700),strategyBytes(0x4B0),personBytes(0x200),titleBytes(0x600),forceBytes(0x1D0);
        auto address=[](auto& x){return reinterpret_cast<uint64_t>(x.data());};
        auto root=address(rootBytes),world=address(worldBytes),state=address(stateBytes),strategy=address(strategyBytes),person=address(personBytes);
        auto title=address(titleBytes),force=address(forceBytes);
        uint64_t returnAddress=base+0x4DA3BE;
        put<uint64_t>(base+0x1FCA1E0,root);put<uint64_t>(root+0x85130,world);put<uint64_t>(world,base+0x12AA638);
        put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x3A,12);
        put<uint32_t>(world+0x40,1);put<uint8_t>(world+0x165D,2);put<uint32_t>(base+0x1FCA518,12);put<uint32_t>(base+0x18EB8B0,123);
        put<uint64_t>(state,base+0x12CC4A8);put<uint64_t>(strategy,base+0x12CD400);put<uint64_t>(person,base+0x12A00D0);put<uint16_t>(person+0x10,952);
        put<uint64_t>(title,base+0x12DAAF0);put<uint32_t>(title+0x470,15);put<uint64_t>(title+0x4A0,force);put<uint64_t>(title+0x4A8,person);
        put<uint16_t>(force+0x10,952);put<uint64_t>(root+0xDCA0+2*8,force);
        std::memcpy(reinterpret_cast<void*>(state+0x70),"CUserStrategyState",19);
        std::array<uint64_t,1> states{state};put<uint64_t>(base+0x19E7310+0x10,1);put<uint64_t>(base+0x19E7310+0x20,address(states));
        log=_wfsopen(argv[1],L"w",_SH_DENYNO);require(log!=nullptr,"log open");
        CONTEXT c{};c.Rax=1;
        armPoints(c,base,base+0x2EE64C);require(c.Dr0==base+0x2EE64C&&c.Dr1==base+0x2FC850&&c.Dr7==0x55,"initial points");
        c.Rip=base+0x2EE64C;require(!observe(log,GetCurrentProcess(),base,c,1),"deserialize should continue");
        armPoints(c,base,base+0x2EE64C);require(c.Dr0==base+0x508BC2&&pointEpoch==1,"post-deserialize points");
        c.Rip=base+0x508BC2;c.Rbx=1;require(!observe(log,GetCurrentProcess(),base,c,1),"worker should continue");
        armPoints(c,base,base+0x2EE64C);require(c.Dr0==base+0x3F9B00&&pointEpoch==2,"post-worker points");
        c.Rip=base+0x2FC850;c.Rcx=person;c.Rax=title;c.Rsp=reinterpret_cast<uint64_t>(&returnAddress);require(!observe(log,GetCurrentProcess(),base,c,1),"identity event");
        c.Rip=base+0x3F69F0;c.Rcx=strategy;require(!observe(log,GetCurrentProcess(),base,c,1),"strategy event");
        c.Rip=base+0x3F72C0;c.Rcx=state;require(!observe(log,GetCurrentProcess(),base,c,1),"user initialize event");
        put<uint32_t>(state+0x470,2);put<uint64_t>(state+0x478,0x123000);put<uint64_t>(state+0x618,0x124000);
        c.Rip=base+0x3F9B00;require(observe(log,GetCurrentProcess(),base,c,1)&&startupComplete,"complete stop");
        sawDeserialize=sawWorker=sawStrategy=sawUser=startupComplete=false;
        put<uint64_t>(root+0x85130,0);c.Rcx=0;
        require(observe(log,GetCurrentProcess(),base,c,1)&&!startupComplete,"incomplete null path must not certify success");
        put<uint64_t>(root+0x85130,world);c.Rip=base+0x2FC850;c.Rcx=person;
        returnAddress=base+0x4DA3BF;observe(log,GetCurrentProcess(),base,c,1); // Wrong caller, even with valid objects.
        returnAddress=base+0x4DA3BE;put<uint64_t>(title,base+0x12CC4A8);observe(log,GetCurrentProcess(),base,c,1);
        put<uint64_t>(title,base+0x12DAAF0);c.Rcx=0;observe(log,GetCurrentProcess(),base,c,1); // Mismatch must remain visible.
        c.Rcx=person;put<uint16_t>(force+0x10,666);observe(log,GetCurrentProcess(),base,c,1);
        put<uint16_t>(force+0x10,952);c.Rsp=0;observe(log,GetCurrentProcess(),base,c,1);
        std::fclose(log);log=nullptr;VirtualFree(module,0,MEM_RELEASE);module=nullptr;
        std::printf("{\"result\":\"PASS\",\"events\":12,\"adaptive_transitions\":2,\"handoff_negative_cases\":5,\"scope\":\"Synthetic memory readers and adaptive point selection only; no native identity change\"}\n");return 0;
    }catch(const std::exception& e){if(log)std::fclose(log);if(module)VirtualFree(module,0,MEM_RELEASE);std::fprintf(stderr,"%s\n",e.what());return 1;}
}
