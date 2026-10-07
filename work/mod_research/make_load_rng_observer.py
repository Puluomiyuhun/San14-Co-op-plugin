"""Observe RNG restoration and consumption across native load transitions."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'observe_rng_gate.cpp').read_text(encoding='utf-8')
a=s.index('static void dateFields(')
b=s.index('\nint wmain(',a)
s=s[:a]+r'''
template<class T> static bool maybe(HANDLE p,uint64_t a,T& v) {
    SIZE_T n=0;return ReadProcessMemory(p,reinterpret_cast<void*>(a),&v,sizeof(v),&n)&&n==sizeof(v);
}
static void location(FILE* f,HANDLE p,uint64_t base) {
    uint64_t root=0,world=0,vt=0;unsigned char date[8]{};
    bool ok=maybe(p,base+0x1FCA1E0,root)&&root && maybe(p,root+0x85130,world)&&world &&
        maybe(p,world,vt)&&vt==base+0x12AA638&&maybe(p,world+0x34,date);
    if(ok) std::fprintf(f,"\"date\":[%u,%u,%u],\"subday\":%u,\"player\":%u,",unsigned(date[0]|date[1]<<8),date[2],date[3],date[4],date[6]);
    else std::fprintf(f,"\"date\":null,");
    std::fprintf(f,"\"states\":[");
    uint64_t count=0,array=0;bool comma=false;
    if(maybe(p,base+0x19E7310+0x10,count)&&count<=64 && maybe(p,base+0x19E7310+0x20,array)) {
        for(uint64_t i=0;i<count;i++) {
            uint64_t state=0;char name[96]{};
            if(!maybe(p,array+i*8,state)||!state||!maybe(p,state+0x70,name))break;
            name[95]=0;bool valid=true;
            for(unsigned j=0;name[j];j++) if(!((name[j]>='a'&&name[j]<='z')||(name[j]>='A'&&name[j]<='Z')||(name[j]>='0'&&name[j]<='9')||name[j]=='_'))valid=false;
            if(!valid)break;
            std::fprintf(f,"%s\"%s\"",comma?",":"",name);comma=true;
        }
    }
    std::fprintf(f,"]");
}
static void contextDetails(FILE* f,HANDLE p,uint64_t base,const CONTEXT& c) {
    std::fprintf(f,",\"registers\":{\"rip\":%llu,\"rsp\":%llu,\"rbp\":%llu,\"rbx\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"r12\":%llu,\"r13\":%llu,\"r14\":%llu,\"r15\":%llu}",
        c.Rip,c.Rsp,c.Rbp,c.Rbx,c.Rsi,c.Rdi,c.R12,c.R13,c.R14,c.R15);
    unsigned char data[4096]{};size_t size=sizeof(data);SIZE_T count=0;
    while(size>=64 && !(ReadProcessMemory(p,reinterpret_cast<void*>(c.Rsp),data,size,&count)&&count==size))size/=2;
    std::fprintf(f,",\"stack_hex\":\"");if(size>=64)hexBytes(f,data,size);std::fprintf(f,"\"");
    uint64_t vt=0,col=0;uint32_t desc=0;
    if(maybe(p,c.Rbx,vt)&&vt>=base&&vt<base+0x2238000&&maybe(p,vt-8,col)&&col>=base&&col<base+0x2238000&&maybe(p,col+12,desc)&&desc<0x2237000) {
        char name[128]{};
        if(maybe(p,base+desc+16,name)) {
            name[127]=0;bool valid=true;
            for(unsigned i=0;name[i];i++)if(name[i]<32||name[i]>126||name[i]=='"'||name[i]=='\\')valid=false;
            if(valid)std::fprintf(f,",\"rbx_type\":\"%s\"",name);
        }
    }
    // Raw offsets are diagnostic only, not certified script identity fields.
    uint32_t mode=0,offset=0;uint64_t code=0;
    if(maybe(p,c.Rbx+0x1270,mode)&&maybe(p,c.Rbx+0x1274,offset)&&maybe(p,c.Rbx+0x58,code))
        std::fprintf(f,",\"rbx_diagnostic\":{\"field_1270\":%u,\"field_1274\":%u,\"field_58\":%llu}",mode,offset,code);
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    bool seed=c.Rip==base+0x3AA3E0;
    uint64_t caller=rd<uint64_t>(p,c.Rsp);
    uint32_t next=uint32_t(seed||c.Rip==base+0x3AA43B?c.Rcx:c.Rax);
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"tick_ms\":%llu,\"thread\":%lu,\"writer_rva\":%llu,\"caller_rva\":%llu,\"before\":%u,\"after\":%u,\"ecx\":%u,",
        seed?"rng_set":"rng_update",++sequence,GetTickCount64(),tid,c.Rip-base,
        caller>=base&&caller<base+0x2238000?caller-base:0,rd<uint32_t>(p,base+0x18EB8B0),next,uint32_t(c.Rcx));
    location(log,p,base);contextDetails(log,p,base,c);std::fprintf(log,"}\n");std::fflush(log);
    stageSamples++;started=true;return sequence>=2000;
}
''' + s[b:]
s=s.replace('0x3F9344','0x3AA3E0')
assert 'WriteProcessMemory(' not in s
(ROOT/'observe_load_rng.cpp').write_text(s,encoding='utf-8')
t=(ROOT/'test_rng_gate_observer.py').read_text(encoding='utf-8').replace('observe_rng_gate.exe','observe_load_rng.exe').replace('rng-gate-fixtures.json','load-rng-fixtures.json')
(ROOT/'test_load_rng_observer.py').write_text(t,encoding='utf-8')
t=(ROOT/'start_rng_gate_observer.py').read_text(encoding='utf-8')
t=t.replace('observe_rng_gate.exe','observe_load_rng.exe').replace('rng-gate-fixtures.json','load-rng-fixtures.json')
t=t.replace("('random_inputs_equal','focused_state_equal','person_task_sample_equal')", "('focused_state_equal','person_task_sample_equal')")
t=t.replace("points = (0x3F9344,", "# RNG mismatch is preserved as evidence; this experiment observes restoration, not turn repeatability.\n    points = (0x3AA3E0,")
t=t.replace("'0x3f9344'", "'0x3aa3e0'")
t=t.replace('Hardware execution breakpoints at combat gate and three consuming RNG stores, including caller identity.', 'Hardware execution breakpoints at RNG setter and three consuming stores, with raw stack snapshots and state names.')
t=t.replace('After day12 subday12 gate, or 10000 observations or timeout/cancel; game continues normally after detach', 'After 2000 RNG events or timeout/cancel; native game continues after detach')
(ROOT/'start_load_rng_observer.py').write_text(t,encoding='utf-8')
print('Created load RNG observer; no strict world-layout requirement during native load')
