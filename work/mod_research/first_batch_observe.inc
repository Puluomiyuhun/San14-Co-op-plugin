// Included by a generated hardware-breakpoint observer. No target memory writes.
static bool selectedBatch=false,generatedBatch=false;
static uint64_t progressObject=0,pointEpoch=0;
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target) {
    c.Dr0=fixtureMode?target:base+(selectedBatch?0x3F935F:0x3F9344);
    c.Dr6=0;c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|(fixtureMode?1:0x55);
    if(!fixtureMode){c.Dr1=base+0x16C640;c.Dr2=base+(generatedBatch?0x16AC60:0x16C685);c.Dr3=base+0x15C045;}
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode){
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",rd<uint32_t>(p,c.Rcx));std::fflush(log);
        return ++fixtureSamples==3;
    }
    auto root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    bool gate=c.Rip==base+0x3F9344,boundary=c.Rip==base+0x3F935F,entry=c.Rip==base+0x16C640;
    bool ready=c.Rip==base+0x16C685,decision=c.Rip==base+0x15C045,damage=c.Rip==base+0x16AC60;
    if(!gate&&!boundary&&!entry&&!ready&&!decision&&!damage)throw std::runtime_error("Unknown decision point");
    auto subday=rd<uint8_t>(p,world+0x38),day=rd<uint8_t>(p,world+0x37);
    if(day!=11||rd<uint8_t>(p,world+0x36)!=8||rd<uint16_t>(p,world+0x34)!=203)
        throw std::runtime_error("Outside checkpoint34 first-day window");
    if(gate||boundary){
        if(rd<uint64_t>(p,c.Rbx)!=base+0x12CC770)throw std::runtime_error("Progress type mismatch");
        if(rd<uint32_t>(p,c.Rbx+0x484)!=(boundary?13u:12u))throw std::runtime_error("Stage mismatch");
        if(gate&&subday>10)throw std::runtime_error("Missed first scheduled batch");
        progressObject=c.Rbx;
        if(gate&&subday==10){selectedBatch=true;pointEpoch++;}
    }
    if(!gate&&!selectedBatch)throw std::runtime_error("Unexpected combat before selected interval");
    if(entry&&c.Rcx!=base+0x1A24CF0)throw std::runtime_error("Manager mismatch");
    if(ready&&c.Rbx!=base+0x1A24CF0)throw std::runtime_error("Build-return context mismatch");
    if(decision&&c.R15!=base+0x1A38840)throw std::runtime_error("Pair processor mismatch");
    if(ready){if(generatedBatch)throw std::runtime_error("Repeated build");generatedBatch=true;pointEpoch++;}
    const char* kind=gate?"combat_gate":boundary?"batch_boundary":entry?"combat_entry":ready?"pairs_ready":decision?"pair_eligibility":"casualty_request";
    auto manager=base+0x1A24CF0,effects=base+0x1A38A20,pairs=base+0x1A38840;
    auto filter=rd<uint64_t>(p,base+0x201EC70);
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"tick_ms\":%llu,",kind,++sequence,tid,GetTickCount64());
    dateFields(log,p,world);
    std::fprintf(log,",\"subday\":%u,\"stage\":%u,\"global_rng\":%u,\"worker_90\":%u,\"pending_94\":%u,\"effect_count\":%llu,\"effect_pending_98\":%u,\"pair_count\":%llu,\"special_filter\":%u,\"special_mode_4\":%u,\"world_165c\":%u",
        subday,rd<uint32_t>(p,progressObject+0x484),rd<uint32_t>(p,base+0x18EB8B0),
        rd<uint32_t>(p,manager+0x90),rd<uint32_t>(p,manager+0x94),rd<uint64_t>(p,effects+0x38),rd<uint32_t>(p,effects+0x98),
        rd<uint64_t>(p,pairs+0xC0),filter?rd<uint32_t>(p,filter):0,filter?rd<uint32_t>(p,filter+4):0,rd<uint8_t>(p,world+0x165C));
    if(gate||boundary)std::fprintf(log,",\"rbp_gate\":%llu,\"rsi_substep\":%llu",c.Rbp,c.Rsi);
    if(ready)std::fprintf(log,",\"build_result\":%u",uint32_t(c.Rax));
    if(decision){
        std::fprintf(log,",\"pair\":");onePair(log,p,c.Rbx);
        std::fprintf(log,",\"eligibility_before_special_filter\":%u,\"resolved_forces\":[%u,%u]",uint32_t(c.Rbp),rd<uint32_t>(p,c.Rsp+0xA8),rd<uint32_t>(p,c.Rsp+0xAC));
    }
    if(damage)std::fprintf(log,",\"target_kind\":%u,\"target_id\":%u,\"amount\":%d,\"source_kind\":%u,\"source_id\":%u,\"caller_rva\":%llu",
        uint32_t(c.Rcx),uint32_t(c.Rdx),int32_t(c.R8),uint32_t(c.R9),rd<uint32_t>(p,c.Rsp+0x28),rd<uint64_t>(p,c.Rsp)-base);
    if((gate&&selectedBatch)||ready||boundary){
        armySnapshot(log,p,base,root);allPairs(log,p,pairs);inputLists(log,p,base,root);forceInputs(log,p,root);
    }
    std::fprintf(log,"}\n");std::fflush(log);stageSamples++;started=true;
    if(stageSamples>4096)throw std::runtime_error("Event bound exceeded");
    return boundary;
}
