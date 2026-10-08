// Observation only: no save request, function skip, field write, or permit.
static unsigned pointEpoch=0;
static uint64_t selectedUser=0,selectedStack=0,filteredHits=0;
static DWORD observationPid=0;
static uint64_t observationBirth=0,observationBase=0;
static bool chainComplete=false;
static const char* stopReason="timeout_or_cancel";
static char expectedName[64]{}; // Per-run identity, not an asserted save filename.
static bool setExpectedName(const wchar_t* text){
    unsigned i=0;for(;text[i]&&i<63;++i){auto c=text[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='_'))return false;expectedName[i]=char(c);}
    return i&&i<63&&!text[i];
}
static void need(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static bool formalUser(HANDLE p,uint64_t base){
    const auto manager=base+0x19E7310;
    return rd<uint64_t>(p,manager+0x10)==5&&rd<uint64_t>(p,manager+0x20)==selectedStack&&
        !rd<uint64_t>(p,manager+0x30)&&rd<uint64_t>(p,selectedStack+32)==selectedUser&&
        rd<uint64_t>(p,selectedUser)==base+0x12CC4A8&&rd<DWORD>(p,selectedUser+0x470)==2&&!rd<DWORD>(p,selectedUser+0x68)&&
        rd<uint64_t>(p,base+0x12CC4D0)==base+0x3F9B00&&rd<uint64_t>(p,base+0x12CC9E0)==base+0x3F8140;
}
static void emitBinding(FILE* log){
    std::fprintf(log,"{\"event\":\"observation_binding\",\"pid\":%lu,\"birth\":%llu,\"base\":%llu,\"run_id\":\"%s\",\"game_data_writes\":0,\"native_requests\":0}\n",observationPid,observationBirth,observationBase,expectedName);std::fflush(log);
}
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target,DWORD){
    uint64_t points[]={base+0x2F7C28,base+0x2F7C2D,base+0x16C1A0,base+0x16C2B7};
    if(fixtureMode){points[0]=(pointEpoch&&selectedUser)?base+selectedUser:target;points[1]=points[2]=points[3]=0;}
    c.Dr6=0;c.Dr7&=~DWORD64(0xffff00ff);
    c.Dr0=points[0];c.Dr1=points[1];c.Dr2=points[2];c.Dr3=points[3];
    for(unsigned i=0;i<4;++i)if(points[i])c.Dr7|=DWORD64(1)<<(i*2);
}
struct SaveSpan {DWORD thread=0;uint64_t rsp=0,archive=0;bool entered=false,returned=false;};
struct ArmySpan {uint64_t rsp=0,returnPc=0;};
static SaveSpan saveSpan;
static std::map<DWORD,ArmySpan> armySpans;
static bool hadOrphan=false;
static void emitSpan(FILE* log,const char* name,uint64_t rva,const CONTEXT& c,DWORD tid,
                     uint64_t archive,uint64_t stream,uint64_t archiveStream,uint64_t manager,uint64_t returnPc,bool orphan){
    LARGE_INTEGER counter{};check(QueryPerformanceCounter(&counter),"Read observation clock");
    std::fprintf(log,"{\"seq\":%llu,\"event\":\"%s\",\"rva\":%llu,\"thread\":%lu,\"rsp\":%llu,\"archive\":%llu,\"stream\":%llu,\"archive_stream\":%llu,\"manager\":%llu,\"return_pc\":%llu,\"rbx\":%llu,\"orphan\":%s,\"counter\":%lld,\"pid\":%lu,\"birth\":%llu,\"base\":%llu,\"run_id\":\"%s\",\"lost_events\":0}\n",
        ++sequence,name,rva,tid,c.Rsp,archive,stream,archiveStream,manager,returnPc,c.Rbx,orphan?"true":"false",counter.QuadPart,observationPid,observationBirth,observationBase,expectedName);
    std::fflush(log);need(!std::ferror(log),"Trace write failure");++stageSamples;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid){
    if(fixtureMode){
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",rd<uint32_t>(p,c.Rcx));std::fflush(log);
        ++fixtureSamples;if(selectedUser)pointEpoch=pointEpoch?0:1;return selectedUser?false:fixtureSamples==3;
    }
    if(++filteredHits>4096){stopReason="hardware_event_limit";return true;}
    const auto rva=c.Rip-base;uint64_t archive=0,stream=0,archiveStream=0,manager=0,returnPc=0;const char* name=nullptr;bool orphan=false;
    if(rva==0x2F7C28){
        need(!saveSpan.entered,"Second or nested Save span unsupported");archive=c.Rcx;stream=c.Rdx;
        need(archive&&stream,"Save archive or stream absent");archiveStream=rd<uint64_t>(p,archive+0x10);need(archiveStream==stream,"Save stream binding changed");
        saveSpan={tid,c.Rsp,archive,true,false};name="save_scope_enter";
    }else if(rva==0x2F7C2D){
        need(saveSpan.entered&&!saveSpan.returned&&saveSpan.thread==tid&&saveSpan.rsp==c.Rsp&&saveSpan.archive==c.Rbx,"Save return not paired to native entry");
        saveSpan.returned=true;name="save_scope_return";
    }else if(rva==0x16C1A0){
        manager=c.Rcx;need(manager==base+0x1A24CF0&&!armySpans.count(tid),"Army worker identity or recursion differs");
        returnPc=rd<uint64_t>(p,c.Rsp);need(returnPc!=0,"Army native return absent");armySpans.emplace(tid,ArmySpan{c.Rsp,returnPc});name="army_worker_enter";
    }else if(rva==0x16C2B7){
        returnPc=rd<uint64_t>(p,c.Rsp);const auto item=armySpans.find(tid);orphan=item==armySpans.end();
        if(orphan)hadOrphan=true;
        else {need(item->second.rsp==c.Rsp&&item->second.returnPc==returnPc,"Army return not paired to native entry");armySpans.erase(item);}
        name="army_worker_return";
    }else throw std::runtime_error("Unrecognized owned observation point");
    emitSpan(log,name,rva,c,tid,archive,stream,archiveStream,manager,returnPc,orphan);
    if(saveSpan.returned&&armySpans.empty()){
        chainComplete=!hadOrphan;stopReason=hadOrphan?"save_observed_with_censored_worker":"save_span_and_worker_returns_observed";return true;
    }
    return false;
}
