// Observation payload only. No game calls or writes. Debug registers are
// rearmed by the parent observer and restored before detach.
static unsigned pointEpoch=0;
static bool sawDeserialize=false,sawWorker=false,sawStrategy=false,sawUser=false;
static bool startupComplete=false;
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target) {
    c.Dr6=0;c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
    c.Dr0=fixtureMode?target:base+(pointEpoch==0?0x2EE64C:pointEpoch==1?0x508BC2:0x3F9B00);
    if(!fixtureMode){c.Dr1=base+0x2FC850;c.Dr2=base+0x3F69F0;c.Dr3=base+0x3F72C0;c.Dr7|=0x54;}
}
static void startupFields(FILE* f,HANDLE p,uint64_t base,const CONTEXT& c) {
    uint64_t root=0,world=0,vt=0;
    if(maybe(p,base+0x1FCA1E0,root)&&root&&maybe(p,root+0x85130,world)&&world&&
       maybe(p,world,vt)&&vt==base+0x12AA638) {
        uint32_t mode=0,seed=0,cache=0,field454=0,field20a8=0;
        unsigned char rank=0,actor=0;unsigned char slots[30]{};
        bool ok=maybe(p,world+0x40,mode)&&maybe(p,world+0x3A,actor)&&maybe(p,world+0x165D,rank)&&
            maybe(p,base+0x18EB8B0,seed)&&maybe(p,base+0x1FCA518,cache)&&
            maybe(p,world+0x454,field454)&&maybe(p,world+0x20A8,field20a8)&&maybe(p,world+0x165E,slots);
        if(ok){
            std::fprintf(f,",\"world_context\":{\"force\":%u,\"mode\":%u,\"rank_derived_count\":%u,\"cached_force\":%u,\"global_rng\":%u,\"field_454\":%u,\"field_20a8\":%u,\"rank_arrays_hex\":\"",
                actor,mode,rank,cache,seed,field454,field20a8);hexBytes(f,slots,sizeof slots);std::fprintf(f,"\"}");
        }
    }
    if(c.Rip==base+0x2FC850) {
        uint16_t person=0;uint64_t personvt=0;
        if(maybe(p,c.Rcx,personvt)&&personvt==base+0x12A00D0&&maybe(p,c.Rcx+0x10,person))
            std::fprintf(f,",\"initializer_person_id\":%u",person);
        else std::fprintf(f,",\"initializer_person_id\":null");
        // The validated direct caller keeps its CTitleState pointer in RAX.
        // This witness is deliberately unavailable for other callers, missing
        // stacks, or a wrong vtable. It authorizes no mutation by itself.
        uint64_t caller=0,titlevt=0,force=0,ruler=0,rulervt=0;
        uint16_t rulerId=0,forceRulerId=0;uint32_t titlePhase=0;
        bool gotCaller=maybe(p,c.Rsp,caller)&&caller>=base&&caller<base+0x2240000;
        if(gotCaller)std::fprintf(f,",\"initializer_return_rva\":%llu",caller-base);
        else std::fprintf(f,",\"initializer_return_rva\":null");
        int forceId=-1;
        bool titleOk=gotCaller&&caller==base+0x4DA3BE&&root&&
            maybe(p,c.Rax,titlevt)&&titlevt==base+0x12DAAF0&&
            maybe(p,c.Rax+0x470,titlePhase)&&maybe(p,c.Rax+0x4A0,force)&&force&&
            maybe(p,c.Rax+0x4A8,ruler)&&ruler&&maybe(p,ruler,rulervt)&&rulervt==base+0x12A00D0&&
            maybe(p,ruler+0x10,rulerId)&&maybe(p,force+0x10,forceRulerId);
        if(titleOk){
            for(unsigned i=0;i<52;++i){uint64_t candidate=0;
                if(maybe(p,root+0xDCA0+i*8,candidate)&&candidate==force){forceId=int(i);break;}}
            titleOk=forceId>=0;
        }
        if(titleOk)std::fprintf(f,",\"native_handoff_context\":{\"title_phase_raw\":%u,\"selected_force_id\":%d,\"selected_person_id\":%u,\"force_ruler_id\":%u,\"argument_matches_title_person\":%s,\"selected_pair_matches\":%s}",
            titlePhase,forceId,rulerId,forceRulerId,c.Rcx==ruler?"true":"false",rulerId==forceRulerId?"true":"false");
        else std::fprintf(f,",\"native_handoff_context\":null");
    }
    if(c.Rip==base+0x3F69F0) {
        uint64_t statevt=0,begin=0,end=0;
        if(maybe(p,c.Rcx,statevt)&&statevt==base+0x12CD400&&maybe(p,c.Rcx+0x470,begin)&&maybe(p,c.Rcx+0x478,end))
            std::fprintf(f,",\"strategy_context\":{\"object\":%llu,\"field_470_raw\":%llu,\"field_478_raw\":%llu}",c.Rcx,begin,end);
    }
    if(c.Rip==base+0x3F72C0||c.Rip==base+0x3F9B00) {
        uint64_t statevt=0;
        const uint64_t expected=base+0x12CC4A8;
        if(maybe(p,c.Rcx,statevt)&&statevt==expected) {
            uint32_t phase=0;uint64_t ui=0,panel=0;unsigned char slots[40]{};
            if(maybe(p,c.Rcx+0x470,phase)&&maybe(p,c.Rcx+0x478,ui)&&maybe(p,c.Rcx+0x618,panel)&&maybe(p,c.Rcx+0x480,slots)) {
                std::fprintf(f,",\"state_context\":{\"object\":%llu,\"field_470_raw\":%u,\"field_478_raw\":%llu,\"field_618_raw\":%llu,\"field_480_hex\":\"",c.Rcx,phase,ui,panel);
                hexBytes(f,slots,sizeof slots);std::fprintf(f,"\"}");
            }
        }
    }
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    const char* event="unexpected";
    if(c.Rip==base+0x2EE64C){event="deserialize_return";sawDeserialize=true;sawWorker=sawStrategy=sawUser=false;pointEpoch=1;}
    else if(c.Rip==base+0x508BC2){event="load_worker_result";sawWorker=sawDeserialize&&uint32_t(c.Rbx)==1;pointEpoch=2;}
    else if(c.Rip==base+0x2FC850)event="native_identity_initializer";
    else if(c.Rip==base+0x3F69F0){event="strategy_initialize";sawStrategy=sawWorker;}
    else if(c.Rip==base+0x3F72C0){event="user_strategy_initialize";sawUser=sawStrategy&&sawWorker;}
    else if(c.Rip==base+0x3F9B00){event="first_user_update";startupComplete=sawDeserialize&&sawWorker&&sawStrategy&&sawUser;}
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"tick_ms\":%llu,\"thread\":%lu,\"rva\":%llu,\"eax\":%u,\"ebx\":%u,\"point_epoch\":%u,\"complete_path_seen\":%s,",
        event,++sequence,GetTickCount64(),tid,c.Rip-base,unsigned(c.Rax),unsigned(c.Rbx),pointEpoch,startupComplete?"true":"false");
    location(log,p,base);startupFields(log,p,base,c);std::fprintf(log,"}\n");std::fflush(log);
    ++stageSamples;
    return c.Rip==base+0x3F9B00||sequence>=64;
}
