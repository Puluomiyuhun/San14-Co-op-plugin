// Isolated process: real copied native identity function, synthetic title/state
// scaffolding. This is not a game load, UI or two-client acceptance test.
#define main unused_identity_fixture_main
#include "identity_pair_fixture.cpp"
#undef main
#define wmain unused_debugger_main
#include "startup_identity_switch.cpp"
#undef wmain
#include <array>

int main(int argc,char** argv){
    unsigned char* module=nullptr;unsigned char* title=nullptr;FILE* log=nullptr;
    try{
        demand(argc==5,"input case journal trace required");std::string test=argv[2];
        std::ifstream input(argv[1],std::ios::binary);demand(bool(input),"input missing");
        demand(integer(input,0x1414FACE)==0x1414FACE,"input magic");readBytes(input,world,sizeof world);
        auto n=integer(input,6001);for(unsigned i=0;i<n;++i){auto id=integer(input,6000);readBytes(input,people[id],0x200);}
        readBytes(input,forces,sizeof forces);readBytes(input,districts,sizeof districts);readBytes(input,cities,sizeof cities);readBytes(input,objects,sizeof objects);readBytes(input,ranks,sizeof ranks);
        auto planningCityA0=rd<uint32_t>(static_cast<const void*>(cities[13]),0xA0);
        auto districtsCount=integer(input,52);for(unsigned i=0;i<districtsCount;++i)integer(input,51);demand(input.peek()==EOF,"extra input");
        code=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x10000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));demand(code!=nullptr,"local native code allocation");
        for(const auto& b:nativeBlocks)std::memcpy(code+b.offset,b.bytes,b.size);
        for(const auto& p:patches)wr(code,p.at,int32_t(p.target)-int32_t(p.next));
        for(const auto& s:dataSlots)std::memcpy(code+s.offset,s.bytes,8);
        // Unsupported native branches fail in this isolated process.
        for(unsigned at:{0xB000u,0xB020u,0xB040u}){code[at]=0x0F;code[at+1]=0x0B;}
        installVT();wr(code,slot(0x1FCA1E0),uintptr_t(root));
        std::array<std::array<unsigned char,0x200>,64> armies{};
        for(unsigned i=0;i<64;++i)wr(root,0x7DF60+i*8,uint64_t(armies[i].data()));
        for(const auto& r:checkpointRecords){auto at=rd<uint64_t>(static_cast<const void*>(root),r.table+r.id*8);std::memcpy(reinterpret_cast<void*>(at+0x10),r.bytes,r.size);}
        module=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2240000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));demand(module!=nullptr,"synthetic module allocation");
        title=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x1000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));demand(title!=nullptr,"synthetic title allocation");
        auto base=uint64_t(module);std::vector<unsigned char> extendedWorld(0x2200);std::memcpy(extendedWorld.data(),world,sizeof world);auto w=uint64_t(extendedWorld.data());
        wr(root,0x85130,w);wr(module,0x1FCA1E0,uint64_t(root));wr(extendedWorld.data(),0,uint64_t(base+vt_CWorldData));wr(extendedWorld.data(),0x20A8,uint32_t(1));
        std::memcpy(module+vt_CWorldData,worldVT,sizeof worldVT);std::memcpy(module+vt_CPersonData,personVT,sizeof personVT);
        std::memcpy(module+vt_CForceData,forceVT,sizeof forceVT);std::memcpy(module+vt_CDistrictData,districtVT,sizeof districtVT);
        for(unsigned id:{666u,952u})wr(people[id],0,base+vt_CPersonData);
        for(unsigned id:{12u,2u})wr(forces[id],0,base+vt_CForceData);
        for(unsigned id:{11u,2u})wr(districts[id],0,base+vt_CDistrictData);
        for(const auto& f:switchFingerprints)std::memcpy(module+f.rva,f.data,f.size);
        wr(module,0x12CC4A8+0x28,base+0x3F9B00);
        wr(title,0,base+vt_CTitleState);wr(title,0x470,uint32_t(15));wr(title,0x4A0,SelectionPair{uint64_t(forces[12]),uint64_t(people[666])});
        std::memcpy(title+0x70,"CTitleState",12);
        std::array<unsigned char,0x100> rootState{},motorState{};
        std::memcpy(rootState.data()+0x70,"CRootState",11);std::memcpy(motorState.data()+0x70,"CMotorGameState",16);
        std::array<uint64_t,3> states{uint64_t(rootState.data()),uint64_t(motorState.data()),uint64_t(title)};
        wr(module,0x19E7310+0x10,uint64_t(3));wr(module,0x19E7310+0x20,uint64_t(states.data()));
        DWORD old=0;demand(VirtualProtect(code,0xC000,PAGE_EXECUTE_READ,&old)!=FALSE,"native code protection");
        demand(FlushInstructionCache(GetCurrentProcess(),code,0xC000)!=FALSE,"native code flush");
        fixtureMode=false;executeHandoff=test!="dry";sawDeserialize=sawWorker=true;pointEpoch=2;
        std::string journal=argv[3];reservationPath.assign(journal.begin(),journal.end());
        CONTEXT c{};c.Rip=base+0x4DA3B2;c.Rax=uint64_t(title);c.Rcx=0xABCDEF;
        if(test=="wrong_instruction")c.Rip++;
        if(test=="wrong_order")sawWorker=false;
        if(test=="wrong_title_type")wr(title,0,base+vt_CForceData);
        if(test=="wrong_stack")states[2]=uint64_t(motorState.data());
        if(test=="wrong_pair")wr(title,0x4A0,SelectionPair{uint64_t(forces[2]),uint64_t(people[666])});
        if(test=="wrong_date")wr(extendedWorld.data(),0x37,uint8_t(21));
        if(test=="wrong_mode")wr(extendedWorld.data(),0x40,uint32_t(4));
        if(test=="wrong_ruler")wr(forces[2],0x10,uint16_t(666));
        if(test=="wrong_district")wr(people[952],0x118,uint8_t(11));
        if(test=="wrong_rank")wr(forces[2],0x47,uint8_t(6));
        if(test=="wrong_checkpoint"){cities[13][0x34]^=1;people[952][0x120]^=1;}
        if(test=="wrong_load_phase"){demand(planningCityA0!=0,"planning phase control is empty");wr(cities[13],0xA0,planningCityA0);}
        if(test=="wrong_code")module[0x4DA3B2]^=1;
        if(test=="readonly_title")demand(VirtualProtect(title,0x1000,PAGE_READONLY,&old)!=FALSE,"title readonly protection");
        if(test=="existing_journal"){std::ofstream prior(argv[3]);prior<<"existing attempt\n";}
        auto titleBefore=std::vector<unsigned char>(title,title+0x1000),worldBefore=extendedWorld;
        auto citiesBefore=std::vector<unsigned char>(cities[0],cities[0]+sizeof cities);
        auto contextBefore=c;
        demand(fopen_s(&log,argv[4],"w")==0&&log!=nullptr,"fixture trace open");
        bool rejected=false;std::string rejection;unsigned nativeCalls=0;
        try{
            verifySwitchProfile(GetCurrentProcess(),base);
            // Run the production guard directly for the wrong-instruction case;
            // the observer dispatch would never route that unrelated instruction.
            if(test=="wrong_instruction")inspectHandoff(GetCurrentProcess(),base,c);
            else observe(log,GetCurrentProcess(),base,c,1);
        }catch(const std::exception& e){rejected=true;rejection=e.what();}
        bool successCase=test=="execute"||test=="repeat_blocked";
        demand(std::memcmp(&contextBefore,&c,sizeof c)==0,"adapter_changed_cpu_arguments");
        if(successCase){
            demand(!rejected&&handoffWritten,"valid handoff did not execute");
            demand(extendedWorld==worldBefore,"adapter_wrote_world_state");
            auto selected=rd<SelectionPair>(GetCurrentProcess(),uint64_t(title)+0x4A0);
            demand(selected.force==uint64_t(forces[2])&&selected.person==uint64_t(people[952]),"wrong selected pair");
            for(unsigned i=0;i<0x1000;++i)if(titleBefore[i]!=title[i])demand(i>=0x4A0&&i<0x4B0,"unexpected title write");
            uint64_t returnAddress=base+0x4DA3BE;c.Rip=base+0x2FC850;c.Rcx=selected.person;c.Rsp=uint64_t(&returnAddress);
            observe(log,GetCurrentProcess(),base,c,1);
            reinterpret_cast<void(*)(void*)>(code+fn_initialize_player)(reinterpret_cast<void*>(selected.person));++nativeCalls;
            c.Rip=base+0x4DA3BE;observe(log,GetCurrentProcess(),base,c,1);
            demand(handoffReturned&&extendedWorld[0x3A]==2&&extendedWorld[0x165D]==1,"native initializer result");
            for(unsigned i=0;i<extendedWorld.size();++i)if(worldBefore[i]!=extendedWorld[i])demand(i==0x3A||i==0x165D,"unexpected native world write");
            if(test=="repeat_blocked"){
                auto current=extendedWorld;c.Rip=base+0x2FC850;bool blocked=false;
                try{observe(log,GetCurrentProcess(),base,c,1);}catch(const std::exception&){blocked=true;}
                demand(blocked&&extendedWorld==current,"repeated initialization not blocked");
            }
        }else{
            demand(rejected==(test!="dry"),"wrong guard result");
            demand(!handoffWritten&&extendedWorld==worldBefore&&std::memcmp(title,titleBefore.data(),0x1000)==0,"rejected or dry case wrote game buffers");
        }
        demand(std::memcmp(cities,citiesBefore.data(),sizeof cities)==0,"city data changed");
        if(!successCase&&test!="existing_journal")demand(GetFileAttributesW(reservationPath.c_str())==INVALID_FILE_ATTRIBUTES,"unexpected execution reservation");
        std::fclose(log);log=nullptr;
        std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"rejected\":%s,\"reason\":\"%s\",\"selection_written\":%s,\"native_initializer_calls\":%u,\"game_process_access\":false}\n",test.c_str(),rejected?"true":"false",rejection.c_str(),handoffWritten?"true":"false",nativeCalls);
        VirtualFree(module,0,MEM_RELEASE);VirtualFree(title,0,MEM_RELEASE);VirtualFree(code,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){if(log)std::fclose(log);if(module)VirtualFree(module,0,MEM_RELEASE);if(title)VirtualFree(title,0,MEM_RELEASE);if(code)VirtualFree(code,0,MEM_RELEASE);std::fprintf(stderr,"%s\n",e.what());return 1;}
}
