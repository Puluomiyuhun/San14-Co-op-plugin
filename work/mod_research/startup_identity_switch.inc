// Research pilot: changes a Title selection pair before the native MOV RCX.
// It never writes world identity, calls game functions, or patches game code.
#include "startup_switch_profile.h"
#define observe observeStartupOnly
#define armPoints armObserverPoints
#include "startup_identity_observe.inc"
#undef observe
#undef armPoints

static bool executeHandoff=false,handoffWritten=false,handoffReturned=false;
static std::wstring reservationPath;
static unsigned handoffStep=0;
struct SelectionPair {uint64_t force,person;};
struct HandoffWitness {uint64_t root,world,title;SelectionPair source,target;};
static HandoffWitness handoff{};

static void demand(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
static bool samePair(const SelectionPair& a,const SelectionPair& b){return a.force==b.force&&a.person==b.person;}
static void verifySwitchProfile(HANDLE p,uint64_t base){
    for(const auto& item:switchFingerprints){std::vector<unsigned char> actual(item.size);
        readExact(p,base+item.rva,actual.data(),actual.size());
        demand(std::memcmp(actual.data(),item.data,item.size)==0,"switch_code_profile_mismatch");}
    demand(rd<uint64_t>(p,base+0x12CC4A8+0x28)==base+0x3F9B00,"existing_user_update_hook");
}
static void titleStack(HANDLE p,uint64_t base,uint64_t title){
    const char* expected[]={"CRootState","CMotorGameState","CTitleState"};
    demand(rd<uint64_t>(p,base+0x19E7310+0x10)==3,"not_title_only_stack");
    auto array=rd<uint64_t>(p,base+0x19E7310+0x20);
    for(unsigned i=0;i<3;++i){auto state=rd<uint64_t>(p,array+i*8);char name[96]{};
        readExact(p,state+0x70,name,sizeof name);name[95]=0;
        demand(std::strcmp(name,expected[i])==0,"wrong_title_stack_order");
        if(i==2)demand(state==title,"title_object_not_on_stack");}
}
static void personForce(HANDLE p,uint64_t base,uint64_t root,uint64_t person,uint16_t id,unsigned districtId,unsigned forceId){
    demand(rd<uint64_t>(p,person)==base+vt_CPersonData&&rd<uint16_t>(p,person+0x10)==id,"person_type_or_id_mismatch");
    demand(rd<uint8_t>(p,person+0x118)==districtId,"person_district_mismatch");
    auto district=rd<uint64_t>(p,root+0xDE40+districtId*8);
    demand(rd<uint64_t>(p,district)==base+vt_CDistrictData&&rd<uint8_t>(p,district+0x10)==forceId,"district_force_mismatch");
    demand(rd<uint8_t>(p,district+0x11)!=0&&rd<uint16_t>(p,district+0x12)==id,"main_district_leader_mismatch");
}
static void checkpointSample(HANDLE p,uint64_t root,FILE* log=nullptr){
    size_t checked=0,differentRecords=0,differentBytes=0,readFailures=0;bool comma=false;
    if(log)std::fprintf(log,"{\"event\":\"checkpoint_sample_comparison\",\"stage\":\"title_selection_boundary\",\"differences\":[");
    for(const auto& item:checkpointRecords){
        ++checked;std::vector<unsigned char> actual(item.size);bool readable=true;
        try{auto object=rd<uint64_t>(p,root+item.table+item.id*8);readExact(p,object+0x10,actual.data(),actual.size());}
        catch(const std::exception&){readable=false;}
        if(!readable){++readFailures;
            if(log)std::fprintf(log,"%s{\"table_rva\":%llu,\"id\":%u,\"read_error\":true}",comma?",":"",item.table,item.id);
            comma=true;continue;
        }
        std::vector<size_t> changed;
        for(size_t i=0;i<item.size;++i){
            if(item.army&&i>=0x138&&i<0x140)continue;
            if(actual[i]!=item.bytes[i])changed.push_back(i);
        }
        if(changed.empty())continue;
        ++differentRecords;differentBytes+=changed.size();
        if(log){
            std::fprintf(log,"%s{\"table_rva\":%llu,\"id\":%u,\"changes\":[",comma?",":"",item.table,item.id);bool innerComma=false;
            for(auto i:changed){std::fprintf(log,"%s{\"object_offset\":%zu,\"expected\":%u,\"actual\":%u}",innerComma?",":"",i+0x10,unsigned(item.bytes[i]),unsigned(actual[i]));innerComma=true;}
            std::fprintf(log,"]}");
        }
        comma=true;
    }
    if(log){std::fprintf(log,"],\"checked_records\":%zu,\"different_records\":%zu,\"different_bytes\":%zu,\"unreadable_records\":%zu,\"only_excluded_field\":\"army+0x148..0x150\"}\n",checked,differentRecords,differentBytes,readFailures);std::fflush(log);}
    demand(readFailures==0,"checkpoint_sample_read_failure_no_write");
    demand(differentRecords==0,"checkpoint_sample_mismatch_no_write");
}
static HandoffWitness inspectHandoff(HANDLE p,uint64_t base,const CONTEXT& c,FILE* log=nullptr){
    demand(c.Rip==base+0x4DA3B2,"wrong_handoff_instruction");
    demand(sawDeserialize&&sawWorker&&!sawStrategy&&!sawUser,"wrong_load_order_for_handoff");
    demand(!handoffWritten&&handoffStep==0,"handoff_already_consumed");
    HandoffWitness w{};w.root=rd<uint64_t>(p,base+0x1FCA1E0);w.world=rd<uint64_t>(p,w.root+0x85130);w.title=c.Rax;
    demand(rd<uint64_t>(p,w.world)==base+vt_CWorldData,"world_type_mismatch");
    demand(rd<uint64_t>(p,w.title)==base+vt_CTitleState,"title_type_mismatch");titleStack(p,base,w.title);
    demand(rd<uint16_t>(p,w.world+0x34)==203&&rd<uint8_t>(p,w.world+0x36)==8&&rd<uint8_t>(p,w.world+0x37)==11&&rd<uint8_t>(p,w.world+0x38)==0,"wrong_checkpoint_date");
    demand(rd<uint32_t>(p,w.world+0x40)==1&&rd<uint8_t>(p,w.world+0x3A)==12,"wrong_world_mode_or_source");
    demand(rd<uint8_t>(p,w.world+0x165D)==2&&rd<uint32_t>(p,w.world+0x20A8)==1,"unexpected_postload_fields");
    w.source={rd<uint64_t>(p,w.root+0xDCA0+12*8),rd<uint64_t>(p,w.root+0x148+666*8)};
    w.target={rd<uint64_t>(p,w.root+0xDCA0+2*8),rd<uint64_t>(p,w.root+0x148+952*8)};
    demand(samePair(rd<SelectionPair>(p,w.title+0x4A0),w.source),"title_selection_not_source_pair");
    demand(rd<uint64_t>(p,w.source.force)==base+vt_CForceData&&rd<uint16_t>(p,w.source.force+0x10)==666,"source_force_ruler_mismatch");
    demand(rd<uint64_t>(p,w.target.force)==base+vt_CForceData&&rd<uint16_t>(p,w.target.force+0x10)==952,"target_force_ruler_mismatch");
    personForce(p,base,w.root,w.source.person,666,11,12);personForce(p,base,w.root,w.target.person,952,2,2);
    demand(rd<uint8_t>(p,w.source.force+0x47)==6&&rd<uint8_t>(p,w.target.force+0x47)==7,"rank_profile_mismatch");
    checkpointSample(p,w.root,log);
    MEMORY_BASIC_INFORMATION m{};auto at=w.title+0x4A0;
    demand(VirtualQueryEx(p,reinterpret_cast<void*>(at),&m,sizeof m)==sizeof m,"selection_memory_query_failed");
    demand(m.State==MEM_COMMIT&&!(m.Protect&(PAGE_GUARD|PAGE_NOACCESS))&&
        (m.Protect==PAGE_READWRITE||m.Protect==PAGE_WRITECOPY)&&at+sizeof(SelectionPair)<=reinterpret_cast<uint64_t>(m.BaseAddress)+m.RegionSize,"selection_memory_not_writable");
    return w;
}
static void reserveHandoff(HANDLE p){
    demand(!reservationPath.empty(),"missing_attempt_journal");
    HANDLE file=CreateFileW(reservationPath.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
    check(file!=INVALID_HANDLE_VALUE,"Reserve one-shot handoff");
    char text[256]{};int size=std::snprintf(text,sizeof text,"{\"stage\":\"INTENT\",\"pid\":%lu,\"source_force\":12,\"target_force\":2,\"automatic_retry_allowed\":false}\n",GetProcessId(p));
    DWORD written=0;BOOL ok=WriteFile(file,text,DWORD(size),&written,nullptr);BOOL flushed=FlushFileBuffers(file);CloseHandle(file);
    demand(ok&&written==DWORD(size)&&flushed,"attempt_journal_not_durable");
}
static void writeSelection(HANDLE p,const HandoffWitness& w){
    demand(samePair(rd<SelectionPair>(p,w.title+0x4A0),w.source),"selection_changed_before_write");
    reserveHandoff(p);SIZE_T written=0;
    BOOL ok=WriteProcessMemory(p,reinterpret_cast<void*>(w.title+0x4A0),&w.target,sizeof w.target,&written);
    SelectionPair after{};bool exact=maybe(p,w.title+0x4A0,after)&&samePair(after,w.target);
    if(!ok||written!=sizeof w.target||!exact){
        SIZE_T restored=0;BOOL rollback=WriteProcessMemory(p,reinterpret_cast<void*>(w.title+0x4A0),&w.source,sizeof w.source,&restored);
        bool verified=maybe(p,w.title+0x4A0,after)&&samePair(after,w.source);
        demand(rollback&&restored==sizeof w.source&&verified,"selection_write_and_rollback_uncertain_reload_required");
        throw std::runtime_error("selection_write_failed_rolled_back_no_retry");
    }
    handoffWritten=true;handoff=w;
}
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target){
    armObserverPoints(c,base,target);
    if(!fixtureMode)c.Dr1=base+(handoffStep==0?0x4DA3B2:handoffStep==2?0x4DA3BE:0x2FC850);
}
static void switchRow(FILE* f,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid,const char* event){
    std::fprintf(f,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"rva\":%llu,\"handoff_written\":%s,",event,++sequence,tid,c.Rip-base,handoffWritten?"true":"false");
    location(f,p,base);startupFields(f,p,base,c);std::fprintf(f,"}\n");std::fflush(f);++stageSamples;
}
static bool observe(FILE* f,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid){
    if(fixtureMode)return observeStartupOnly(f,p,base,c,tid);
    if(c.Rip==base+0x4DA3B2){
        switchRow(f,p,base,c,tid,"title_selection_boundary");
        auto witness=inspectHandoff(p,base,c,f);
        if(!executeHandoff){std::fprintf(f,"{\"event\":\"handoff_dry_pass\",\"game_data_written\":false}\n");std::fflush(f);return true;}
        writeSelection(p,witness);handoffStep=1;++pointEpoch;
        std::fprintf(f,"{\"event\":\"title_selection_written\",\"source_force\":12,\"target_force\":2,\"source_ruler\":666,\"target_ruler\":952,\"adapter_written_bytes\":16,\"world_identity_written_by_adapter\":false}\n");std::fflush(f);
        return false;
    }
    if(c.Rip==base+0x2FC850){
        demand(handoffWritten&&handoffStep==1,"unexpected_or_repeated_identity_call");
        demand(c.Rax==handoff.title&&c.Rcx==handoff.target.person&&rd<uint64_t>(p,c.Rsp)==base+0x4DA3BE,"wrong_native_identity_arguments_or_caller");
        demand(samePair(rd<SelectionPair>(p,handoff.title+0x4A0),handoff.target),"selected_pair_reverted");
        demand(rd<uint8_t>(p,handoff.world+0x3A)==12,"identity_changed_before_native_initializer");
        bool stop=observeStartupOnly(f,p,base,c,tid);handoffStep=2;++pointEpoch;return stop;
    }
    if(c.Rip==base+0x4DA3BE){
        demand(handoffWritten&&handoffStep==2,"unexpected_initializer_return");
        demand(rd<uint8_t>(p,handoff.world+0x3A)==2&&rd<uint8_t>(p,handoff.world+0x165D)==1,"native_identity_postconditions_failed");
        handoffReturned=true;handoffStep=3;++pointEpoch;switchRow(f,p,base,c,tid,"native_identity_return");return false;
    }
    if(c.Rip==base+0x3F69F0||c.Rip==base+0x3F72C0||c.Rip==base+0x3F9B00){
        demand(handoffReturned&&rd<uint8_t>(p,handoff.world+0x3A)==2,"strategy_identity_not_target");
    }
    bool done=observeStartupOnly(f,p,base,c,tid);
    if(c.Rip==base+0x3F9B00){
        demand(startupComplete&&rd<uint32_t>(p,c.Rcx+0x470)==2&&rd<uint64_t>(p,c.Rcx+0x478)&&rd<uint64_t>(p,c.Rcx+0x618),"target_user_state_not_ready");
        std::fprintf(f,"{\"event\":\"target_user_state_observed\",\"force\":2,\"native_ui_objects_present\":true,\"visual_menu_verification_pending\":true,\"native_gameplay_enabled\":false}\n");std::fflush(f);
    }
    return done;
}
