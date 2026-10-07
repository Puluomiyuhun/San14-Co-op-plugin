// Read-only observation payload. Worker layouts are per-native-thread, not a
// global assumed order: Title+590 may run before Title+520 has been joined.
static unsigned pointEpoch=0;
static uint64_t selectedUser=0,selectedStack=0,filteredHits=0;
static bool chainComplete=false;
static const char* stopReason="timeout_or_cancel";
static char expectedName[64]{};
static bool setExpectedName(const wchar_t* text){
    unsigned i=0;for(;text[i]&&i<63;++i){auto c=text[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='.'||c=='_'))return false;expectedName[i]=char(c);}
    return i&&i<63&&!text[i];
}
static void need(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct JoinWorker {
    uint64_t control=0,callable=0,handle=0,method=0,payload=0,startSequence=0,invokeSequence=0,payloadSequence=0,returnSequence=0,doneSequence=0,joinSequence=0;
    DWORD thread=0,startThread=0,joinThread=0;
};
static JoinWorker joinedWorkers[3];
static uint64_t boundLoad=0,boundTitle=0,boundClosure=0,boundSequence=0,callbackSequence=0;
static int sourceSlot=-1;
static char sourceName[64]{};
static bool formalUser(HANDLE p,uint64_t base){
    const auto manager=base+0x19E7310;
    return rd<uint64_t>(p,manager+0x10)==5&&rd<uint64_t>(p,manager+0x20)==selectedStack&&
        !rd<uint64_t>(p,manager+0x30)&&rd<uint64_t>(p,selectedStack+32)==selectedUser&&
        rd<uint64_t>(p,selectedUser)==base+0x12CC4A8&&rd<DWORD>(p,selectedUser+0x470)==2&&!rd<DWORD>(p,selectedUser+0x68);
}
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target,DWORD tid){
    uint64_t points[4]{};
    if(fixtureMode){points[0]=(pointEpoch&&selectedUser)?base+selectedUser:target;}
    else if(!boundLoad){points[0]=base+0x4DA240;}
    else {
        const JoinWorker* worker=nullptr;
        for(const auto& w:joinedWorkers)if(w.startSequence&&!w.joinSequence&&w.thread==tid){need(!worker,"Overlapping embedded worker thread identity");worker=&w;}
        if(worker){points[0]=base+0x834D98;points[1]=base+worker->payload;points[2]=base+0x834D9B;points[3]=base+0x834DB4;}
        else {points[0]=base+0x834B60;points[1]=base+(joinedWorkers[0].joinSequence?0x4CC690:0x4F7079);points[2]=base+0x4AAF64;points[3]=base+0x4AAF89;}
    }
    c.Dr6=0;c.Dr7&=~DWORD64(0xffff00ff);
    c.Dr0=points[0];c.Dr1=points[1];c.Dr2=points[2];c.Dr3=points[3];
    for(unsigned i=0;i<4;++i)if(points[i])c.Dr7|=DWORD64(1)<<(i*2);
}
static uint64_t formalTitle(HANDLE p,uint64_t base,bool requireLoad){
    const auto manager=base+0x19E7310,n=rd<uint64_t>(p,manager+0x10),array=rd<uint64_t>(p,manager+0x20);
    need(array&&((requireLoad&&n==4)||(!requireLoad&&(n==3||n==4))),"Unsupported Title formal stack length");
    need(rd<uint64_t>(p,array+16)==boundTitle,"Bound Title not at formal slot2");
    if(n==4)need(rd<uint64_t>(p,array+24)==boundLoad,"Unexpected Load address on formal stack");
    need(rd<uint64_t>(p,boundTitle)==base+0x12DAAF0,"Bound Title vtable changed");
    need(rd<int>(p,boundTitle+0x47C)==sourceSlot,"Title/source slot mismatch");
    return n;
}
static void readSourceName(HANDLE p,uint64_t base){
    const auto s=base+0x201ECE0,n=rd<uint64_t>(p,s+16),cap=rd<uint64_t>(p,s+24);
    need(n>0&&n<sizeof(sourceName)&&cap>=n&&cap<=8192&&(cap>=16||cap==15),"Invalid source name SSO");
    readExact(p,cap>=16?rd<uint64_t>(p,s):s,sourceName,size_t(n+1));
    need(!sourceName[n]&&!strcmp(sourceName,expectedName),"Load source filename differs from expected manual save");
}
static void emit(FILE* log,const char* event,uint64_t rva,DWORD tid,int role,const JoinWorker* w,uint64_t nativeReturn=0,uint64_t done=0,uint64_t nativeResult=0,const uint64_t* cleanup=nullptr){
    std::fprintf(log,"{\"seq\":%llu,\"event\":\"%s\",\"rva\":\"0x%llx\",\"thread\":%lu,\"role\":%d,\"load\":%llu,\"title\":%llu,\"source_slot\":%d,\"source_name\":\"%s\",\"native_return\":%llu,\"done\":%llu,\"native_result\":%llu,\"lost_events\":0",
        ++sequence,event,rva,tid,role,boundLoad,boundTitle,sourceSlot,sourceName,nativeReturn,done,nativeResult);
    std::fprintf(log,",\"load_closure\":%llu",boundClosure);
    if(w)std::fprintf(log,",\"control\":%llu,\"callable\":%llu,\"handle\":%llu,\"callable_method\":%llu,\"payload_rva\":\"0x%llx\",\"worker_thread\":%lu,\"start_seq\":%llu",w->control,w->callable,w->handle,w->method,w->payload,w->thread,w->startSequence);
    if(cleanup)std::fprintf(log,",\"cleanup_fields\":[%llu,%llu,%llu]",cleanup[0],cleanup[1],cleanup[2]);
    std::fprintf(log,"}\n");std::fflush(log);need(!std::ferror(log),"Trace write failure");++stageSamples;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid){
    if(fixtureMode){
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",rd<uint32_t>(p,c.Rcx));std::fflush(log);
        ++fixtureSamples;if(selectedUser)pointEpoch=pointEpoch?0:1;return selectedUser?false:fixtureSamples==3;
    }
    if(++filteredHits>20000){stopReason="hardware_event_limit";return true;}
    need(sequence<64,"Selected record limit");
    const auto rva=c.Rip-base;
    if(rva==0x4DA240){
        need(!boundLoad,"Second Load before selected chain completed");
        const auto load=c.Rcx;
        need(rd<uint64_t>(p,load)==base+0x12DBD68&&rd<DWORD>(p,load+0x470)==1,"Load entry type/phase");
        const auto closure=rd<uint64_t>(p,load+0x48);
        need(closure&&rd<uint64_t>(p,closure)==base+0x12EA4D0&&rd<uint64_t>(p,base+0x12EA4D0+0x10)==base+0x4FAC30,"Load completion closure binding");
        boundLoad=load;boundClosure=closure;boundTitle=rd<uint64_t>(p,closure+8);
        sourceSlot=rd<int>(p,base+0x201ECD0);need(sourceSlot>=0&&sourceSlot<120,"Source slot range");
        need(!rd<DWORD>(p,base+0x201ECD4)&&!rd<DWORD>(p,base+0x201ECD8),"Special load route unsupported");
        readSourceName(p,base);formalTitle(p,base,true);
        need(rd<uint64_t>(p,base+0x19E7310+0x48)==boundLoad,"Load not current native state");
        const auto scheduler=rd<uint64_t>(p,load+0x50);
        need(scheduler&&rd<DWORD>(p,rd<uint64_t>(p,scheduler+8)+0x10)==tid,"Load Update native thread mismatch");
        joinedWorkers[0].control=load+0x478;joinedWorkers[0].payload=0x508B40;
        joinedWorkers[1].control=boundTitle+0x520;joinedWorkers[1].payload=0x4DA390;
        joinedWorkers[2].control=boundTitle+0x590;joinedWorkers[2].payload=0x466600;
        emit(log,"load_bound",rva,tid,-1,nullptr,rd<uint64_t>(p,c.Rsp));boundSequence=sequence;++pointEpoch;return false;
    }
    if(!boundLoad)return false;
    if(rva==0x4CC690){
        if(c.Rcx!=boundTitle)return false;
        need(!callbackSequence&&joinedWorkers[0].joinSequence&&c.Rdx==boundLoad&&rd<uint64_t>(p,c.Rsp)==base+0x497134,"Title callback lacks bound Load finalizer origin");
        formalTitle(p,base,true);need(rd<DWORD>(p,base+0x201EC08)==1,"Native load failed before Title callback");
        // No historical Load read here or in any Title worker/join path.
        emit(log,"load_finalize_title_callback",rva,tid,-1,nullptr,rd<uint64_t>(p,c.Rsp),0,1);callbackSequence=sequence;return false;
    }
    if(rva==0x834B60){
        int role=-1;for(int i=0;i<3;++i)if(c.Rcx==joinedWorkers[i].control)role=i;
        if(role<0)return false;
        auto& w=joinedWorkers[role];need(!w.startSequence,"Duplicate selected embedded worker start");
        const uint64_t callers[]={0x4DA2F4,0x4BEEC2,0x4BEF2B};const auto caller=rd<uint64_t>(p,c.Rsp);
        need(caller==base+callers[role],"Selected start caller mismatch");formalTitle(p,base,role==0||role==1);
        if(role){need(callbackSequence&&joinedWorkers[0].joinSequence,"Title start before observed Load join/callback");
            need(rd<DWORD>(p,boundTitle+0x470)==(role==1?13u:15u),"Title start phase mismatch");}
        if(role==2)need(joinedWorkers[1].doneSequence,"Title590 start before observed Title520 completion");
        w.handle=rd<uint64_t>(p,w.control);w.callable=rd<uint64_t>(p,w.control+0x48);w.method=rd<uint64_t>(p,base+0x138E8D0);
        need(w.handle&&rd<uint64_t>(p,w.control+8)&&w.callable,"Embedded worker not constructed");
        need(rd<uint64_t>(p,w.callable)==base+0x138E8C0&&rd<uint64_t>(p,w.callable+8)==base+w.payload,"Selected payload differs from constructed callable");
        w.thread=rd<DWORD>(p,w.handle+0x10);w.startThread=tid;
        need(w.thread&&w.thread!=tid&&!rd<DWORD>(p,w.control+0x54),"Invalid worker thread or stop flag");
        for(int i=0;i<3;++i)if(i!=role&&joinedWorkers[i].startSequence&&!joinedWorkers[i].joinSequence)need(joinedWorkers[i].thread!=w.thread,"Active worker thread alias");
        w.startSequence=sequence+1;emit(log,"worker_start",rva,tid,role,&w,caller,rd<DWORD>(p,w.control+0x50));++pointEpoch;return false;
    }
    if(rva==0x4F7079||rva==0x4AAF64||rva==0x4AAF89){
        const int role=rva==0x4F7079?0:rva==0x4AAF64?1:2;auto& w=joinedWorkers[role];
        if(c.Rbx!=(role?boundTitle:boundLoad))return false;
        need(w.doneSequence&&w.returnSequence&&w.payloadSequence&&!w.joinSequence,"Join without unique paired native worker completion");
        formalTitle(p,base,role==0);
        const uint64_t cleanup[]={rd<uint64_t>(p,w.control),rd<uint64_t>(p,w.control+8),rd<uint64_t>(p,w.control+0x60)};
        need(!cleanup[0]&&!cleanup[1]&&!cleanup[2],"Native join cleanup fields not null");
        if(!role)need(rd<DWORD>(p,boundLoad+0x470)==2&&rd<DWORD>(p,base+0x201EC08)==1,"Load join phase/result mismatch");
        else need(rd<DWORD>(p,boundTitle+0x470)==16,"Title join phase mismatch");
        w.joinThread=tid;w.joinSequence=sequence+1;emit(log,"worker_join_return",rva,tid,role,&w,0,rd<DWORD>(p,w.control+0x50),role?0:1,cleanup);++pointEpoch;
        if(joinedWorkers[0].joinSequence&&joinedWorkers[1].joinSequence&&joinedWorkers[2].joinSequence){chainComplete=true;stopReason="load_and_both_Title_joins_observed";return true;}
        return false;
    }
    int role=-1;for(int i=0;i<3;++i){const auto& w=joinedWorkers[i];if(w.startSequence&&!w.joinSequence&&w.thread==tid)role=i;}
    if(role<0)return false;
    auto& w=joinedWorkers[role];
    if(rva!=w.payload&&rva!=0x834D98&&rva!=0x834D9B&&rva!=0x834DB4)return false;
    formalTitle(p,base,role==0);
    need(rd<uint64_t>(p,w.control)==w.handle&&rd<uint64_t>(p,w.control+0x48)==w.callable&&rd<DWORD>(p,w.handle+0x10)==tid,"Worker receipt identity changed");
    need(rd<uint64_t>(p,w.callable)==base+0x138E8C0&&rd<uint64_t>(p,w.callable+8)==base+w.payload&&rd<uint64_t>(p,base+0x138E8D0)==w.method,"Worker callable payload/method changed");
    const auto done=rd<DWORD>(p,w.control+0x50);need(done==(rva==0x834DB4?1u:0u),"Worker done publication order");
    need(!rd<DWORD>(p,w.control+0x54),"Worker stopped before completion");
    const char* name=nullptr;
    if(rva==0x834D98){need(c.Rbx==w.control&&c.Rdi==w.handle&&c.Rcx==w.callable&&!w.invokeSequence,"Runner invocation binding/duplicate");name="runner_invocation";w.invokeSequence=sequence+1;}
    else if(rva==w.payload){need(w.invokeSequence&&!w.payloadSequence&&c.Rcx==w.callable,"Actual payload entry binding/duplicate");name="actual_payload_entry";w.payloadSequence=sequence+1;}
    else if(rva==0x834D9B){need(w.payloadSequence&&!w.returnSequence&&c.Rbx==w.control&&c.Rdi==w.handle,"Runner return binding/duplicate");name="runner_return";w.returnSequence=sequence+1;}
    else {need(w.returnSequence&&!w.doneSequence&&c.Rbx==w.control&&c.Rdi==w.handle,"Runner done binding/duplicate");name="runner_done_store";w.doneSequence=sequence+1;}
    emit(log,name,rva,tid,role,&w,rva==w.payload?rd<uint64_t>(p,c.Rsp):0,done,role==0&&rva==0x834D9B?rd<DWORD>(p,base+0x201EC08):0);return false;
}
