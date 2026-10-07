// Dedicated manual-observation debugger fixture: owned process only;
// subsequent load events are synthetic scaffolding, never a full native load.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <stdexcept>
#include "auto_reload_profile.h"
static void need(bool b,const char* m){if(!b)throw std::runtime_error(m);}
template<class T>static void put(unsigned char* p,size_t at,T value){std::memcpy(p+at,&value,sizeof value);}
template<class T>static T get(unsigned char* p,size_t at){T value{};std::memcpy(&value,p+at,sizeof value);return value;}
static void nativeString(unsigned char* p,const char* text){size_t n=std::strlen(text);need(n<16,"fixture filename too long");std::memcpy(p,text,n+1);put(p,16,uint64_t(n));put(p,24,uint64_t(15));}
static void callHook(unsigned char* module,size_t slot,uint64_t target,void* argument,bool identity=false){
    unsigned char* code=module+0x10000+slot*0x100;
    // Preserve all touched ABI nonvolatile registers, reserve home area, then call.
    std::vector<unsigned char> bytes={0x53,0x56,0x57,0x41,0x54,0x48,0x83,0xEC,0x28,0x48,0x89,0xCF,0x41,0xBC,1,0,0,0,0xBB,1,0,0,0};
    if(identity){bytes.insert(bytes.end(),{0x48,0x89,0xC8});}else{bytes.insert(bytes.end(),{0x31,0xC0});}
    bytes.push_back(0xE8);auto next=uint64_t(code)+bytes.size()+4;int32_t offset=int32_t(target-next);
    for(unsigned i=0;i<4;++i)bytes.push_back(static_cast<unsigned char>(uint32_t(offset)>>(8*i)));
    bytes.insert(bytes.end(),{0x48,0x83,0xC4,0x28,0x41,0x5C,0x5F,0x5E,0x5B,0xC3});
    std::memcpy(code,bytes.data(),bytes.size());FlushInstructionCache(GetCurrentProcess(),code,bytes.size());
    reinterpret_cast<void(*)(void*)>(code)(argument);
}
int wmain(int argc,wchar_t** argv){
    try{
        need(argc==4,"ready go case required");std::wstring test=argv[3];
        auto module=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2240000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));need(module!=nullptr,"fixture image allocation");
        auto manager=static_cast<unsigned char*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));need(manager!=nullptr,"manager allocation");
        const uint64_t base=uint64_t(module);put(module,0,uint16_t(0x5a4d));
        for(const auto& g:ar_guards)std::memcpy(module+g.rva,g.bytes,g.size);
        put(module,0x12CC9B8+0x28,base+0x3F8140);put(module,0x12CC4A8+0x28,base+0x3F9B00);
        module[0x3F8194]=0xC3; // Native consumer branch ends here in this fixture.
        for(size_t i=2;i<9;++i){auto& g=ar_guards[i];size_t at=g.rva+g.size;
            if(g.rva==0x3F69F0)module[at++]=0x5D;
            if(g.rva==0x3F9B00)module[at++]=0x5E;
            module[at]=0xC3;
        }
        module[0x4DA3BE]=0xC3;
        std::vector<unsigned char> root(0x85200),world(0x3000),force(0x200),person(0x300),metadata(0x200),binding(0x40),title(0x700);
        std::vector<std::vector<unsigned char>> states(5,std::vector<unsigned char>(0x700));
        const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
        std::vector<uint64_t> statePointers;for(unsigned i=0;i<5;++i){std::strcpy(reinterpret_cast<char*>(states[i].data()+0x70),names[i]);statePointers.push_back(uint64_t(states[i].data()));}
        put(module,0x19E7310+0x10,uint64_t(5));put(module,0x19E7310+0x20,uint64_t(statePointers.data()));
        put(states[2].data(),0,base+0x12CC9B8);put(states[3].data(),0,base+0x12CD400);put(states[4].data(),0,base+0x12CC4A8);
        put(states[4].data(),0x470,uint32_t(2));put(states[4].data(),0x478,uint64_t(0x1111));put(states[4].data(),0x618,uint64_t(0x2222));
        put(module,0x1FCA1E0,uint64_t(root.data()));put(root.data(),0x85130,uint64_t(world.data()));
        put(world.data(),0,base+0x12AA638);put(world.data(),0x34,uint16_t(203));world[0x36]=8;world[0x37]=11;world[0x3A]=12;put(world.data(),0x40,uint32_t(1));
        put(root.data(),0xDCA0+12*8,uint64_t(force.data()));put(force.data(),0x10,uint16_t(666));
        put(root.data(),0x148+666*8,uint64_t(person.data()));put(person.data(),0,base+0x12A00D0);put(person.data(),0x10,uint16_t(666));
        put(module,0x2025318,uint64_t(manager));put(manager,0x3EC,int32_t(-1));put(manager,0x20+34*8,uint64_t(metadata.data()));nativeString(metadata.data()+0x128,"svdexSC34.s14");
        put(binding.data(),0,uint32_t(34));nativeString(binding.data()+0x10,"svdexSC34.s14");put(title.data(),0x4A8,uint64_t(person.data()));
        if(test==L"wrong_mode")put(manager,8,uint32_t(1));
        if(test==L"wrong_pending")put(manager,0x3EC,int32_t(9));
        if(test==L"missing_cache")put(manager,0x20+34*8,uint64_t(0));
        if(test==L"wrong_filename")nativeString(binding.data()+0x10,"svdexSC35.s14");
        if(test==L"wrong_target")put(binding.data(),0,uint32_t(35));
        if(test==L"wrong_date")world[0x37]=21;
        if(test==L"wrong_code")module[0x4BF5C3]^=1;
        if(test==L"pending_transition")put(module,0x19E7310+0x30,uint64_t(1));
        if(test==L"readonly_request"){DWORD old;need(VirtualProtect(manager,4096,PAGE_READONLY,&old)!=FALSE,"readonly fixture");}
        std::vector<unsigned char> before(manager,manager+4096);
        FILE* ready=nullptr;need(_wfopen_s(&ready,argv[1],L"w")==0,"ready file");
        FILETIME ft{},xt{},kt{},ut{};need(GetProcessTimes(GetCurrentProcess(),&ft,&xt,&kt,&ut)!=FALSE,"birth");
        std::fprintf(ready,"{\"pid\":%lu,\"base\":%llu,\"birth\":%llu}\n",GetCurrentProcessId(),base,(uint64_t(ft.dwHighDateTime)<<32|ft.dwLowDateTime));std::fclose(ready);
        const auto deadline=GetTickCount64()+30000;while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES&&GetTickCount64()<deadline)Sleep(10);
        need(GetFileAttributesW(argv[2])!=INVALID_FILE_ATTRIBUTES,"fixture go timeout");
        if(test==L"wrong_code"){module[0x4BF5C3]^=1;}
        // User action is represented by the target-binding callback below; observer cannot request it.
        const int32_t request=get<int32_t>(manager,0x3EC);bool consumed=get<uint32_t>(states[2].data(),0x474)==1;
        unsigned changes=0;for(unsigned i=0;i<4096;++i)if(before[i]!=manager[i]){need(i>=0x3EC&&i<0x3F0,"write_outside_pending_slot");++changes;}
        bool mapsUnavailable=false,mapsRestored=false;
        if(test!=L"timeout"&&test!=L"cancel"&&test!=L"wrong_birth"){
            if(test==L"stall_after_request"){Sleep(2500);}else{
                callHook(module,1,base+0x4BF5C3,binding.data());
                if(test==L"deserialize_id_map_unavailable"||test==L"worker_id_map_unavailable"){
                    put(root.data(),0x148+666*8,uint64_t(1));
                    put(root.data(),0xDCA0+12*8,uint64_t(1));
                    mapsUnavailable=true;
                }
                if(test==L"deserialize_wrong_date")world[0x37]=21;
                callHook(module,2,base+0x2EE64C,nullptr);
                if(test==L"deserialize_id_map_unavailable"){
                    put(root.data(),0x148+666*8,uint64_t(person.data()));
                    put(root.data(),0xDCA0+12*8,uint64_t(force.data()));
                    mapsRestored=true;
                }
                callHook(module,3,base+0x508BC2,nullptr);
                callHook(module,4,base+0x4DA3B2,title.data(),true);
                callHook(module,5,base+0x3F69F0,states[3].data());
                callHook(module,6,base+0x3F72C0,states[4].data());
                put(manager,0x3EC,int32_t(-1));put(states[2].data(),0x474,uint32_t(0));
                if(test==L"initial_user_phase0"||test==L"initial_ui_not_ready"){
                    put(states[4].data(),0x470,uint32_t(test==L"initial_user_phase0"?0:2));put(states[4].data(),0x478,uint64_t(0));
                    callHook(module,7,base+0x3F9B00,states[4].data());
                    put(states[4].data(),0x470,uint32_t(2));put(states[4].data(),0x478,uint64_t(0x1111));
                }
                if(test==L"invalid_user_phase")put(states[4].data(),0x470,uint32_t(7));
                callHook(module,7,base+0x3F9B00,states[4].data());
            }
        }
        BOOL debugger=TRUE;const auto detachDeadline=GetTickCount64()+5000;
        do{need(CheckRemoteDebuggerPresent(GetCurrentProcess(),&debugger)!=FALSE,"check detached");if(debugger)Sleep(10);}while(debugger&&GetTickCount64()<detachDeadline);
        std::printf("{\"request\":%d,\"consumed\":%s,\"changed_request_bytes\":%u,\"debugger_attached\":%s,\"semantic_maps_unavailable_at_deserialize\":%s,\"semantic_maps_restored_before_worker\":%s,\"game_process_access\":false}\n",request,consumed?"true":"false",changes,debugger?"true":"false",mapsUnavailable?"true":"false",mapsRestored?"true":"false");
        VirtualFree(manager,0,MEM_RELEASE);VirtualFree(module,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
