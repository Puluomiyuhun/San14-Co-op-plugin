// Read-only debug-event payload. No game calls, instruction patches or data writes.
// All samples are taken while Windows holds the debuggee at an execution BP.
static unsigned pointEpoch=0;
static uint64_t selectedUser=0,selectedStack=0,selectedWorker=0,selectedCallable=0;
static DWORD parentThread=0,workerThread=0;
static bool freshSeen=false,bodyDispatched=false,yieldSeen=false,chainComplete=false;
static uint64_t filteredHits=0;
static const char* stopReason="timeout_or_cancel";
static void armPoints(CONTEXT& c,uint64_t base,uint64_t target) {
    const uint64_t sets[][4]={
        {0x50B4B3,0x50B4AE,0x50B598,0x50B690},
        {0x50B730,0x50B690,0x50B5F9,0x50B632},
        {0x50B782,0x50B785,0x50B690,0x50B632},
        {0x834D9B,0x834DB4,0x50B690,0x50B632},
        {0x834DB4,0x50B5F9,0x50B607,0x50B632},
        {0x50B5F9,0x50B607,0x50B632,0x50B690},
        {0x50B607,0x50B632,0x50B690,0x50B5F9},
        {0x50B632,0x50B690,0x50B5F9,0x50B607},
        {0x50B632,0x50B785,0x834D9B,0x834DB4}};
    c.Dr6=0;c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|(fixtureMode?1:0x55);
    if(fixtureMode){c.Dr0=(pointEpoch&&selectedUser)?base+selectedUser:target;c.Dr1=c.Dr2=c.Dr3=0;return;}
    const auto* a=sets[pointEpoch];c.Dr0=base+a[0];c.Dr1=base+a[1];c.Dr2=base+a[2];c.Dr3=base+a[3];
}
static bool formalUser(HANDLE p,uint64_t base) {
    const auto manager=base+0x19E7310;
    if(rd<uint64_t>(p,manager+0x10)!=5||rd<uint64_t>(p,manager+0x20)!=selectedStack||
       rd<uint64_t>(p,manager+0x30)||rd<uint64_t>(p,selectedStack+32)!=selectedUser||
       rd<uint64_t>(p,selectedUser)!=base+0x12CC4A8||rd<uint32_t>(p,selectedUser+0x470)!=2||
       rd<uint32_t>(p,selectedUser+0x68))return false;
    return true;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",rd<uint32_t>(p,c.Rcx));
        std::fflush(log);++fixtureSamples;if(selectedUser)pointEpoch=pointEpoch?0:1;return selectedUser?false:fixtureSamples==3;
    }
    if(++filteredHits>4096){stopReason="hardware_event_limit";return true;}
    const auto rva=c.Rip-base;
    const bool parentPoint=rva==0x50B4B3||rva==0x50B4AE||rva==0x50B598||rva==0x50B5F9||rva==0x50B607||rva==0x50B632;
    uint64_t state=0,worker=0,slot=0,callable=0;
    if(parentPoint){slot=rd<uint64_t>(p,c.Rsp+0x40);state=rd<uint64_t>(p,slot);worker=c.Rdi;}
    else if(rva==0x50B730){callable=c.Rcx;slot=rd<uint64_t>(p,rd<uint64_t>(p,callable+8));state=rd<uint64_t>(p,slot);worker=rd<uint64_t>(p,state+0x50);}
    else if(rva==0x834D9B||rva==0x834DB4){
        if(!selectedWorker||c.Rbx!=selectedWorker+8||tid!=workerThread)return false;
        worker=c.Rbx-8;callable=rd<uint64_t>(p,worker+0x50);slot=rd<uint64_t>(p,rd<uint64_t>(p,callable+8));state=rd<uint64_t>(p,slot);
    } else {state=(rva==0x50B690||rva==0x50B782)?c.Rcx:c.Rbx;if(state!=selectedUser)return false;
        worker=rd<uint64_t>(p,state+0x50);if(!worker)return false;callable=rd<uint64_t>(p,worker+0x50);slot=rd<uint64_t>(p,rd<uint64_t>(p,callable+8));}
    if(state!=selectedUser||slot!=selectedStack+32)return false;
    if(!formalUser(p,base))throw std::runtime_error("Selected formal User changed");
    if(parentThread&&parentPoint&&tid!=parentThread)throw std::runtime_error("Selected parent thread changed");
    if(rva==0x50B4B3||rva==0x50B4AE){
        if(pointEpoch)return false;parentThread=tid;freshSeen=rva==0x50B4B3;
        std::fprintf(log,"{\"event\":\"%s\",\"rva\":\"0x%llx\",\"seq\":%llu,\"thread\":%lu,\"state\":%llu,\"existing_worker\":%llu}\n",
            freshSeen?"new_pool_selection":"existing_task_resume",rva,++sequence,tid,state,worker);
        if(!freshSeen){stopReason="existing_task_resume_not_new_admission";return true;}
        return false;
    }
    if(!selectedWorker){
        if(rva!=0x50B598||!freshSeen)return false;
        selectedWorker=worker;selectedCallable=rd<uint64_t>(p,worker+0x50);
        workerThread=rd<DWORD>(p,rd<uint64_t>(p,worker+8)+0x10);
        if(!workerThread||workerThread==parentThread)throw std::runtime_error("Invalid native worker thread binding");
    }
    if(worker!=selectedWorker)throw std::runtime_error("Selected native worker changed");
    callable=rd<uint64_t>(p,worker+0x50);
    if(callable!=selectedCallable||rd<uint64_t>(p,callable)!=base+0x12F2440||
       rd<uint64_t>(p,base+0x12F2440+0x10)!=base+0x50B730)throw std::runtime_error("Native state callable binding changed");
    auto nativeThread=rd<DWORD>(p,rd<uint64_t>(p,worker+8)+0x10);
    if(nativeThread!=workerThread||(!parentPoint&&tid!=workerThread))throw std::runtime_error("Native thread mismatch");
    const char* name=nullptr;
    if(rva==0x50B598){name="state_attached";pointEpoch=1;}
    else if(rva==0x50B730){
        if(rd<uint64_t>(p,c.Rsp)!=base+0x834D9B)throw std::runtime_error("Unexpected state callable return address");
        name="state_callable_enter";pointEpoch=2;
    }else if(rva==0x50B782){name="user_update_dispatch";bodyDispatched=true;}
    else if(rva==0x50B785){name="user_update_return";pointEpoch=3;}
    else if(rva==0x834D9B){name="callable_return";pointEpoch=4;}
    else if(rva==0x834DB4){name="runner_done_store";pointEpoch=5;}
    else if(rva==0x50B5F9){name="parent_observed_done";pointEpoch=6;}
    else if(rva==0x50B607){name="state_detached";pointEpoch=7;}
    else if(rva==0x50B690){name="cooperative_yield_enter";yieldSeen=true;pointEpoch=8;}
    else if(rva==0x50B632){name="dispatcher_common_tail";chainComplete=pointEpoch==7&&bodyDispatched&&!yieldSeen;}
    if(!name)throw std::runtime_error("Unexpected selected tap");
    const auto attached=rd<uint64_t>(p,state+0x50);
    std::fprintf(log,"{\"seq\":%llu,\"event\":\"%s\",\"rva\":\"0x%llx\",\"thread\":%lu,\"native_thread\":%lu,\"state\":%llu,\"worker\":%llu,\"control\":%llu,\"slot\":%llu,\"callable\":%llu,\"callable_entry\":%llu,\"attached\":%llu,\"done\":%u,\"yielded\":%u,\"stopped\":%u,\"lost_events\":0,\"module_base\":%llu}\n",
        ++sequence,name,rva,tid,nativeThread,state,worker,worker+8,slot,callable,base+0x50B730,attached,
        rd<uint32_t>(p,worker+0x58),rd<uint32_t>(p,worker+0x78),rd<uint32_t>(p,worker+0x5C),base);
    ++stageSamples;std::fflush(log);if(std::ferror(log))throw std::runtime_error("Trace write failure");
    if(sequence>=32){stopReason="selected_event_limit";return true;}
    if(rva==0x50B632){stopReason=chainComplete?"normal_chain":"yield_or_incomplete_chain";return true;}
    return false;
}
