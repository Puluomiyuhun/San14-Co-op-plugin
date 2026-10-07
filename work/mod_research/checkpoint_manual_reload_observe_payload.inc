// Manual read-only load observation. No pending-slot or identity write path.
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#include "auto_reload_profile.h"
static bool syntheticFixture=false,reloadComplete=false;
static bool sawBinding=false,sawDeserialize=false,sawWorker=false,sawIdentity=false,sawStrategy=false,sawUser=false;
static unsigned pointEpoch=0;
static uint64_t lastObservationRva=0;
static uint64_t originalManager=0,initialUser=0,newUser=0;
static std::wstring checkpointPath;
static HANDLE checkpointHandle=INVALID_HANDLE_VALUE;
static const char* checkpointSha="afd4c6c5f8a30f659ac523b85f522b02b2c03536ed5e55736677ca1927827d95";
static const char* expectedFilename="svdexSC34.s14";
static void demand(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
static std::string hashFile(HANDLE file){
    LARGE_INTEGER zero{};check(SetFilePointerEx(file,zero,nullptr,FILE_BEGIN),"Rewind hash input");
    BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
    demand(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)==0,"hash_open");
    unsigned char digest[32]{};std::vector<unsigned char> buffer(65536);
    try{
        demand(BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)==0,"hash_create");
        DWORD got=0;
        do{check(ReadFile(file,buffer.data(),DWORD(buffer.size()),&got,nullptr),"Hash file read");
           if(got)demand(BCryptHashData(hash,buffer.data(),got,0)==0,"hash_data");}while(got);
        demand(BCryptFinishHash(hash,digest,32,0)==0,"hash_finish");
        BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(algorithm,0);
    }catch(...){if(hash)BCryptDestroyHash(hash);BCryptCloseAlgorithmProvider(algorithm,0);throw;}
    std::string result;char item[3];for(unsigned char c:digest){sprintf_s(item,"%02x",c);result+=item;}return result;
}
static void pinCheckpoint(const wchar_t* processPath){
    if(!syntheticFixture){
        demand(checkpointPath==L"C:\\Program Files (x86)\\Steam\\userdata\\391007908\\872410\\remote\\svdexSC34.s14","wrong_checkpoint_path");
        HANDLE binary=CreateFileW(processPath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        demand(binary!=INVALID_HANDLE_VALUE,"game_binary_open_failed");
        std::string got;try{got=hashFile(binary);CloseHandle(binary);}catch(...){CloseHandle(binary);throw;}
        demand(got=="42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025","game_build_sha_mismatch");
    }
    checkpointHandle=CreateFileW(checkpointPath.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    demand(checkpointHandle!=INVALID_HANDLE_VALUE,"checkpoint_pin_failed");
    LARGE_INTEGER size{};check(GetFileSizeEx(checkpointHandle,&size),"Checkpoint length");
    demand(size.QuadPart==274920&&hashFile(checkpointHandle)==checkpointSha,"checkpoint_hash_mismatch");
}
static std::string nativeString(HANDLE p,uint64_t object){
    uint64_t size=rd<uint64_t>(p,object+16),capacity=rd<uint64_t>(p,object+24);
    demand(size<=512&&capacity>=size&&capacity<=32768,"invalid_native_string");
    uint64_t address=capacity>=16?rd<uint64_t>(p,object):object;
    std::vector<char> value(size+1);readExact(p,address,value.data(),value.size());
    demand(value[size]==0&&std::strlen(value.data())==size,"invalid_native_string_terminator");
    return std::string(value.data(),size);
}
static void verifyReloadProfile(HANDLE p,uint64_t base){
    for(const auto& g:ar_guards){std::vector<unsigned char> actual(g.size);readExact(p,base+g.rva,actual.data(),g.size);
        demand(std::memcmp(actual.data(),g.bytes,g.size)==0,"reload_code_profile_mismatch");}
    demand(rd<uint64_t>(p,base+0x12CC9B8+0x28)==base+0x3F8140,"game_update_vtable_mismatch");
    demand(rd<uint64_t>(p,base+0x12CC4A8+0x28)==base+0x3F9B00,"user_update_vtable_mismatch");
}
static uint64_t worldHeaderCheck(HANDLE p,uint64_t base){
    auto root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    demand(rd<uint64_t>(p,world)==base+0x12AA638,"world_type_mismatch");
    demand(rd<uint16_t>(p,world+0x34)==203&&rd<uint8_t>(p,world+0x36)==8&&rd<uint8_t>(p,world+0x37)==11&&rd<uint8_t>(p,world+0x38)==0,"not_checkpoint34_date");
    return root;
}
static uint64_t finalizedWorldCheck(HANDLE p,uint64_t base){
    auto root=worldHeaderCheck(p,base);
    auto world=rd<uint64_t>(p,root+0x85130);
    demand(rd<uint8_t>(p,world+0x3A)==12&&rd<uint32_t>(p,world+0x40)==1,"wrong_local_identity_or_world_mode");
    auto force=rd<uint64_t>(p,root+0xDCA0+12*8),person=rd<uint64_t>(p,root+0x148+666*8);
    demand(rd<uint16_t>(p,force+0x10)==666&&rd<uint64_t>(p,person)==base+0x12A00D0&&rd<uint16_t>(p,person+0x10)==666,"wrong_local_ruler");
    return root;
}
static std::vector<uint64_t> exactPlanning(HANDLE p,uint64_t base){
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    auto stateManager=base+0x19E7310;
    demand(rd<uint64_t>(p,stateManager+0x10)==5,"not_idle_planning_stack");
    demand(rd<uint64_t>(p,stateManager+0x30)==0,"pending_state_transition");
    auto array=rd<uint64_t>(p,stateManager+0x20);std::vector<uint64_t> states;
    for(unsigned i=0;i<5;++i){auto state=rd<uint64_t>(p,array+8*i);char name[96]{};readExact(p,state+0x70,name,96);name[95]=0;
        demand(std::strcmp(name,names[i])==0,"wrong_planning_state_order");states.push_back(state);}
    demand(rd<uint64_t>(p,states[2])==base+0x12CC9B8&&rd<uint64_t>(p,states[3])==base+0x12CD400&&rd<uint64_t>(p,states[4])==base+0x12CC4A8,"planning_state_type_mismatch");
    demand(rd<uint32_t>(p,states[4]+0x470)==2&&rd<uint64_t>(p,states[4]+0x478)&&rd<uint64_t>(p,states[4]+0x618),"user_menu_not_ready");
    return states;
}

static void initialPlanning(HANDLE p,uint64_t base){
    finalizedWorldCheck(p,base);auto states=exactPlanning(p,base);initialUser=states[4];
    originalManager=rd<uint64_t>(p,base+0x2025318);
    demand(originalManager>=0x10000&&rd<int32_t>(p,originalManager+0x3EC)==-1,"initial_pending_request");
}
static void armPoints(CONTEXT& c,uint64_t base,uint64_t){
    const uint64_t points[]={0x4BF5C3,0x2EE64C,0x508BC2,0x3F9B00};
    demand(pointEpoch<4,"invalid_observer_epoch");
    c.Dr0=base+points[pointEpoch];c.Dr1=base+0x2FC850;c.Dr2=base+0x3F69F0;c.Dr3=base+0x3F72C0;
    c.Dr6=0;c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x55;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid){
    lastObservationRva=c.Rip-base;const char* event="unexpected";
    if(c.Rip==base+0x4BF5C3){
        demand(pointEpoch==0&&!sawBinding&&rd<uint32_t>(p,c.Rcx)==34&&rd<uint32_t>(p,c.Rcx+4)==0&&rd<uint32_t>(p,c.Rcx+8)==0,"wrong_native_target_binding");
        demand(nativeString(p,c.Rcx+0x10)==expectedFilename,"bound_filename_mismatch");
        sawBinding=true;pointEpoch=1;event="native_target_bound";
    }else if(c.Rip==base+0x2EE64C){
        demand(sawBinding&&pointEpoch==1&&int32_t(c.Rax)>=0,"deserialize_failed_or_wrong_order");
        // 2EE69D -> 2F3410/2F3B93 rebuilds semantic maps later. Header only here.
        worldHeaderCheck(p,base);sawDeserialize=true;pointEpoch=2;event="deserialize_return";
    }else if(c.Rip==base+0x508BC2){
        demand(sawDeserialize&&pointEpoch==2&&uint32_t(c.Rbx)==1,"load_worker_failed_or_wrong_order");
        finalizedWorldCheck(p,base);sawWorker=true;pointEpoch=3;event="load_worker_result";
    }else if(c.Rip==base+0x2FC850){
        demand(sawWorker&&!sawIdentity&&rd<uint64_t>(p,c.Rcx)==base+0x12A00D0&&rd<uint16_t>(p,c.Rcx+0x10)==666,"wrong_or_repeated_identity_initializer");
        demand(rd<uint64_t>(p,c.Rsp)==base+0x4DA3BE,"unexpected_identity_caller");
        sawIdentity=true;event="native_identity_initializer";
    }else if(c.Rip==base+0x3F69F0){demand(sawIdentity&&!sawStrategy,"strategy_initialization_order");sawStrategy=true;event="strategy_initialize";
    }else if(c.Rip==base+0x3F72C0){demand(sawStrategy&&!sawUser,"user_initialization_order");sawUser=true;newUser=c.Rcx;event="user_strategy_initialize";
    }else if(c.Rip==base+0x3F9B00){
        demand(sawBinding&&sawDeserialize&&sawWorker&&sawIdentity&&sawStrategy&&sawUser,"incomplete_reload_route");
        demand(c.Rcx==newUser&&rd<uint64_t>(p,c.Rcx)==base+0x12CC4A8,"unexpected_rebuilt_user");
        const auto phase=rd<uint32_t>(p,c.Rcx+0x470);
        // 3F72E8 initializes phase0; 3F7541 can retain it, while 3F7549
        // chooses phase2. 3F9B23..35 dispatches phase0 to 402730. Thus a
        // first User callback is NOT proof of a ready command menu. Phase1
        // is conservatively retained as unready, never accepted as success.
        demand(phase<=2,"unexpected_rebuilt_user_phase");
        const auto count=rd<uint64_t>(p,base+0x19E7310+0x10),queued=rd<uint64_t>(p,base+0x19E7310+0x30);
        if(phase!=2||!rd<uint64_t>(p,c.Rcx+0x478)||!rd<uint64_t>(p,c.Rcx+0x618)||count!=5||queued!=0){
            event="rebuilt_user_waiting_for_planning";
            std::fprintf(log,"{\"event\":\"planning_not_ready\",\"phase\":%u,\"state_count\":%llu,\"queued\":%llu}\n",phase,count,queued);
        }else{
            finalizedWorldCheck(p,base);auto states=exactPlanning(p,base);
            demand(c.Rcx==states[4],"unexpected_rebuilt_user_stack");
            const auto currentManager=rd<uint64_t>(p,base+0x2025318);
            demand(currentManager==originalManager&&rd<int32_t>(p,currentManager+0x3EC)==-1,"final_request_cleanup_mismatch");
            demand(hashFile(checkpointHandle)==checkpointSha,"checkpoint_changed_after_load");
            reloadComplete=true;event="manual_same_player_reload_observed";
        }
    }else demand(false,"unexpected_observer_point");
    std::fprintf(log,"{\"event\":\"%s\",\"sequence\":%llu,\"thread\":%lu,\"rva\":%llu,\"epoch\":%u,\"rcx\":%llu,\"rax\":%llu,\"initial_user\":%llu,\"initialized_user\":%llu,",event,++sequence,tid,c.Rip-base,pointEpoch,c.Rcx,c.Rax,initialUser,newUser);
    location(log,p,base);std::fprintf(log,"}\n");std::fflush(log);return reloadComplete;
}
