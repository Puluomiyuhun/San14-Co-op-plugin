// This payload observes native instructions. It never skips or submits them.
static unsigned pointEpoch=0;
static uint64_t selectedUser=0,selectedStack=0,filteredHits=0;
static DWORD observationPid=0;
static uint64_t observationBirth=0,observationBase=0;
static bool chainComplete=false;
static const char* stopReason="timeout_or_cancel";
static char expectedName[64]{};
static bool setExpectedName(const wchar_t* text){
    unsigned i=0;for(;text[i]&&i<63;++i){auto c=text[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'))return false;expectedName[i]=char(c);}
    return i&&i<63&&!text[i];
}
#include "reward_menu_observation_decode.inc"
static bool formalUser(HANDLE p,uint64_t base){
    const auto manager=base+0x19E7310;
    return rd<uint64_t>(p,manager+0x10)==5&&rd<uint64_t>(p,manager+0x20)==selectedStack&&
        !rd<uint64_t>(p,manager+0x30)&&rd<uint64_t>(p,selectedStack+32)==selectedUser&&
        rd<uint64_t>(p,selectedUser)==base+0x12CC4A8&&rd<DWORD>(p,selectedUser+0x470)==2&&!rd<DWORD>(p,selectedUser+0x68)&&
        rd<uint64_t>(p,base+0x12CC4D0)==base+0x3F9B00&&rd<uint64_t>(p,base+0x12CC9E0)==base+0x3F8140;
}
static void emitBinding(FILE* log){
    std::fprintf(log,"{\"event\":\"observation_binding\",\"pid\":%lu,\"birth\":%llu,\"base\":%llu,\"run_id\":\"%s\",\"game_data_writes\":0,\"native_requests\":0,\"native_suppression\":false}\n",observationPid,observationBirth,observationBase,expectedName);std::fflush(log);
}
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target,DWORD){
    uint64_t points[]={base+0x67A930,base+0x67A993,base+0x626275,base+0x67A998};
    if(fixtureMode){points[0]=(pointEpoch&&selectedUser)?base+selectedUser:target;points[1]=points[2]=points[3]=0;}
    c.Dr6=0;c.Dr7&=~DWORD64(0xffff00ff);c.Dr0=points[0];c.Dr1=points[1];c.Dr2=points[2];c.Dr3=points[3];
    for(unsigned i=0;i<4;++i)if(points[i])c.Dr7|=DWORD64(1)<<(i*2);
}
struct WrapperSpan {uint64_t state=0,rsp=0;std::string preview;bool common=false;};
static std::map<DWORD,WrapperSpan> wrapperSpans;
static std::map<uint64_t,std::string> menuSamples;
static void emitMenu(FILE* log,const char* event,uint64_t rva,const CONTEXT& c,DWORD tid,const MenuDraft& d){
    LARGE_INTEGER counter{};check(QueryPerformanceCounter(&counter),"Read menu observation clock");
    std::fprintf(log,"{\"seq\":%llu,\"event\":\"%s\",\"rva\":%llu,\"thread\":%lu,\"rsp\":%llu,\"state\":%llu,\"root\":%llu,\"world\":%llu,\"viewer\":%u,\"date\":[%u,%u,%u],\"ui_event_code_raw\":%u,\"eax\":%u,\"preview\":%s,\"counter\":%lld,\"pid\":%lu,\"birth\":%llu,\"base\":%llu,\"run_id\":\"%s\",\"lost_events\":0}\n",
        ++sequence,event,rva,tid,c.Rsp,d.state,d.root,d.world,d.viewer,d.year,d.month,d.day,d.event,unsigned(c.Rax),d.preview().c_str(),counter.QuadPart,observationPid,observationBirth,observationBase,expectedName);
    std::fflush(log);need(!std::ferror(log),"Trace write failure");++stageSamples;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid){
    if(fixtureMode){
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",rd<uint32_t>(p,c.Rcx));std::fflush(log);
        ++fixtureSamples;if(selectedUser)pointEpoch=pointEpoch?0:1;return selectedUser?false:fixtureSamples==3;
    }
    if(++filteredHits>12000||sequence>=256){stopReason="hardware_event_limit";return true;}
    const auto rva=c.Rip-base;
    const auto state=rva==0x626275?c.R13:rva==0x67A998?c.Rbx:c.Rcx;
    auto d=decodeMenu(p,base,state,rva==0x626275?c.Rcx:0);
    if(rva==0x67A930){
        // Update samples distinguish drafts, not constructor/destructor lifetimes.
        auto signature=d.preview()+":"+std::to_string(d.event)+":"+std::to_string(d.root)+":"+std::to_string(d.world)+":"+std::to_string(d.viewer)+":"+std::to_string(d.day);
        if(menuSamples[state]==signature)return false;menuSamples[state]=signature;
        emitMenu(log,"menu_update",rva,c,tid,d);
    }else if(rva==0x67A993){
        need(c.Rbx==state&&d.event==2&&!wrapperSpans.count(tid),"Wrapper entry/event/recursion mismatch");
        wrapperSpans.emplace(tid,WrapperSpan{state,c.Rsp,d.preview(),false});emitMenu(log,"wrapper_call",rva,c,tid,d);
    }else if(rva==0x626275){
        auto it=wrapperSpans.find(tid);need(it!=wrapperSpans.end()&&it->second.state==state&&!it->second.common,"Orphan/duplicate common call");
        need(c.Rsp+0x890==it->second.rsp&&c.Rcx==c.Rsp+0x30,"Common wrapper frame/args identity differs");
        need(it->second.preview==d.preview(),"UI and common ID drafts differ");it->second.common=true;emitMenu(log,"common_call",rva,c,tid,d);
    }else if(rva==0x67A998){
        auto it=wrapperSpans.find(tid);need(it!=wrapperSpans.end()&&it->second.state==state&&it->second.rsp==c.Rsp,"Wrapper return identity mismatch");
        emitMenu(log,"wrapper_return",rva,c,tid,d);wrapperSpans.erase(it);
        chainComplete=wrapperSpans.empty();stopReason="one_wrapper_return_observed";return chainComplete;
    }else throw std::runtime_error("Unrecognized menu observation point");
    return false;
}
