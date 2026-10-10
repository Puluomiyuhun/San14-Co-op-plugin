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
#include "reward_result_observation_decode.inc"
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
    uint64_t points[]={base+0x67A993,base+0x626275,base+0x62627A,base+0x67A998};
    if(fixtureMode){points[0]=(pointEpoch&&selectedUser)?base+selectedUser:target;points[1]=points[2]=points[3]=0;}
    c.Dr6=0;c.Dr7&=~DWORD64(0xffff00ff);c.Dr0=points[0];c.Dr1=points[1];c.Dr2=points[2];c.Dr3=points[3];
    for(unsigned i=0;i<4;++i)if(points[i])c.Dr7|=DWORD64(1)<<(i*2);
}
struct WrapperSpan {
 uint64_t state=0,rsp=0,args=0,root=0,world=0;unsigned viewer=0,year=0,month=0,day=0;
 std::string preview;bool common=false,returned=false;
};
static std::map<DWORD,WrapperSpan> wrapperSpans;

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
    const bool commonPoint=rva==0x626275||rva==0x62627A;
    const auto state=commonPoint?c.R13:rva==0x67A998?c.Rbx:c.Rcx;
    auto it=wrapperSpans.find(tid);
    if(rva==0x62627A)need(it!=wrapperSpans.end()&&it->second.common&&!it->second.returned,"Orphan or duplicate business return");
    const auto args=rva==0x626275?c.Rcx:rva==0x62627A?it->second.args:0;
    auto d=decodeMenu(p,base,state,args);
    if(rva==0x67A993){
        need(c.Rbx==state&&d.event==2&&it==wrapperSpans.end(),"Wrapper entry/event/recursion mismatch");
        WrapperSpan span;span.state=state;span.rsp=c.Rsp;span.preview=d.preview();span.root=d.root;span.world=d.world;
        span.viewer=d.viewer;span.year=d.year;span.month=d.month;span.day=d.day;
        wrapperSpans.emplace(tid,span);emitMenu(log,"wrapper_call",rva,c,tid,d);
    }else{
        need(it!=wrapperSpans.end(),"Orphan event");auto& span=it->second;
        need(span.state==state&&span.root==d.root&&span.world==d.world&&span.viewer==d.viewer&&
             span.year==d.year&&span.month==d.month&&span.day==d.day,"Business identity changed");
        need(span.preview==d.preview(),"UI and common ID drafts differ");
        if(rva==0x626275){
            need(!span.common&&c.Rsp+0x890==span.rsp&&c.Rcx==c.Rsp+0x30,"Common wrapper frame/args identity differs");
            span.common=true;span.args=c.Rcx;emitMenu(log,"common_call",rva,c,tid,d);
        }else if(rva==0x62627A){
            need(c.Rsp+0x890==span.rsp&&span.args==c.Rsp+0x30,"Business return frame/args identity differs");
            // EAX is still the exact native common return here. RCX is volatile;
            // decode from the saved stack args, never RCX or wrapper-return EAX.
            span.returned=true;emitMenu(log,"common_return",rva,c,tid,d);
        }else if(rva==0x67A998){
            need(span.rsp==c.Rsp&&(!span.common||span.returned),"Wrapper return lacks matching business return");
            emitMenu(log,"wrapper_return",rva,c,tid,d);wrapperSpans.erase(it);
            chainComplete=wrapperSpans.empty();stopReason="one_wrapper_return_observed";return chainComplete;
        }else throw std::runtime_error("Unrecognized result observation point");
    }
    return false;
}
