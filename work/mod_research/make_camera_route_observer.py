"""Build an observation-only camera/tactics/RNG trace from the tested debugger loop."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'observe_rng_gate.cpp').read_text(encoding='utf-8')
a=s.index('static bool observe(');b=s.index('\nint wmain(',a)
body=r'''
static void cameraState(FILE* log,HANDLE p,uint64_t base) {
    uint64_t camera=base+0x19E7690;
    if(rd<uint64_t>(p,camera+0x50)!=base+0x123E520)throw std::runtime_error("Camera controller type mismatch");
    unsigned char raw[0x290];readExact(p,camera,raw,sizeof(raw));
    uint64_t linked=rd<uint64_t>(p,camera+0x280);
    std::fprintf(log,",\"camera\":{\"level\":%d,\"fraction\":%d,\"mode_288\":%u,\"linked_present\":%s,\"singleton_hex\":\"",
        rd<int32_t>(p,camera+0x230),rd<int32_t>(p,camera+0x234),rd<uint32_t>(p,camera+0x288),linked?"true":"false");
    hexBytes(log,raw,sizeof(raw));std::fprintf(log,"\",\"linked_hex\":");
    if(linked){unsigned char data[0xb0];readExact(p,linked,data,sizeof(data));std::fprintf(log,"\"");hexBytes(log,data,sizeof(data));std::fprintf(log,"\"");}
    else std::fprintf(log,"null");std::fprintf(log,"}");
}
static void routeContext(FILE* log,HANDLE p,uint64_t base,uint64_t world) {
    dateFields(log,p,world);
    std::fprintf(log,",\"subday\":%u,\"global_rng\":%u,\"worker_90\":%u,\"pending_94\":%u,\"effect_pending_98\":%u,\"effect_count\":%llu",
        rd<uint8_t>(p,world+0x38),rd<uint32_t>(p,base+0x18EB8B0),rd<uint32_t>(p,base+0x1A24D80),
        rd<uint32_t>(p,base+0x1A24D84),rd<uint32_t>(p,base+0x1A38AB8),rd<uint64_t>(p,base+0x1A38A58));
    cameraState(log,p,base);
    uint64_t manager=base+0x19E7310,count=rd<uint64_t>(p,manager+0x10),list=rd<uint64_t>(p,manager+0x20);
    if(count>64 || (count&&!list))throw std::runtime_error("State stack bound");
    int stage=-1;std::fprintf(log,",\"states\":[");
    for(uint64_t i=0;i<count;i++){
        uint64_t state=rd<uint64_t>(p,list+i*8);char name[96];readExact(p,state+0x70,name,sizeof(name));name[95]=0;
        for(unsigned j=0;name[j];j++)if(!((name[j]>='A'&&name[j]<='Z')||(name[j]>='a'&&name[j]<='z')||(name[j]>='0'&&name[j]<='9')||name[j]=='_'))throw std::runtime_error("State name invalid");
        std::fprintf(log,"%s\"%s\"",i?",":"",name);
        if(rd<uint64_t>(p,state)==base+0x12CC770)stage=rd<int32_t>(p,state+0x484);
    }
    std::fprintf(log,"],\"stage\":%d",stage);
}
static void tacticRecord(FILE* log,HANDLE p,uint64_t ptr) {
    unsigned char data[0x40];readExact(p,ptr,data,sizeof(data));
    std::fprintf(log,",\"tactic_record\":{\"actor_type\":%u,\"actor_id\":%u,\"raw_hex\":\"",rd<uint32_t>(p,ptr+8),rd<uint32_t>(p,ptr+12));
    hexBytes(log,data,sizeof(data));std::fprintf(log,"\"}");
}
static bool pastTurn(HANDLE p,uint64_t base) {
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    return rd<uint16_t>(p,world+0x34)!=203 || rd<uint8_t>(p,world+0x36)!=8 || rd<uint8_t>(p,world+0x37)>=21;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode){auto v=rd<uint32_t>(p,c.Rcx);std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",v);std::fflush(log);return ++fixtureSamples==3;}
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    bool entry=c.Rip==base+0x15B070,decision=c.Rip==base+0x15B12F,rng=c.Rip==base+0x3AA805,gate=c.Rip==base+0x3F9344;
    if(!entry&&!decision&&!rng&&!gate)throw std::runtime_error("Unexpected route marker");
    if(entry&&c.Rcx!=base+0x1A38A20)throw std::runtime_error("Tactics effect manager mismatch");
    if(gate&&rd<uint64_t>(p,c.Rbx)!=base+0x12CC770)throw std::runtime_error("Progress type mismatch");
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"tick_ms\":%llu,",entry?"tactic_dispatch":decision?"tactic_camera_decision":rng?"rng_update":"combat_gate",++sequence,tid,GetTickCount64());
    routeContext(log,p,base,world);
    if(entry||decision){tacticRecord(log,p,entry?c.Rdx:c.Rbx);if(decision)std::fprintf(log,",\"scene_eligible\":%u",uint32_t(c.Rax));}
    if(rng){
        uint64_t caller=rd<uint64_t>(p,c.Rsp);
        std::fprintf(log,",\"before\":%u,\"after\":%u,\"range_ecx\":%u,\"caller_rva\":%llu,\"registers\":{\"rip\":%llu,\"rsp\":%llu,\"rbp\":%llu,\"rbx\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"r12\":%llu,\"r13\":%llu,\"r14\":%llu,\"r15\":%llu},\"stack_hex\":\"",
            rd<uint32_t>(p,base+0x18EB8B0),uint32_t(c.Rax),uint32_t(c.Rcx),caller>=base&&caller<base+0x2238000?caller-base:0,
            c.Rip,c.Rsp,c.Rbp,c.Rbx,c.Rsi,c.Rdi,c.R12,c.R13,c.R14,c.R15);
        unsigned char stack[2048];SIZE_T n=0;size_t len=sizeof(stack);
        while(len>=64&&!(ReadProcessMemory(p,reinterpret_cast<void*>(c.Rsp),stack,len,&n)&&n==len))len/=2;
        if(len>=64)hexBytes(log,stack,len);std::fprintf(log,"\"");
    }
    if(gate){
        std::fprintf(log,",\"rbp_gate\":%llu,\"rsi_substep\":%llu,\"armies\":[",c.Rbp,c.Rsi);
        uint64_t pointers[501];readExact(p,root+0x7DF60,pointers,sizeof(pointers));
        for(unsigned i=0;i<501;i++)if(pointers[i]!=pointers[0]+i*0x200)throw std::runtime_error("Army table mismatch");
        std::vector<unsigned char> data(501*0x200);readExact(p,pointers[0],data.data(),data.size());bool comma=false;
        for(unsigned i=1;i<501;i++){
            auto row=data.data()+i*0x200;if(!row[0x10]||!(row[0x12]|row[0x13]))continue;
            uint64_t vt;std::memcpy(&vt,row,8);if(vt!=base+0x123E288)throw std::runtime_error("Army type mismatch");
            std::fprintf(log,"%s[%u,\"",comma?",":"",i);hexBytes(log,row+0x10,0x58);std::fprintf(log,"\"]");comma=true;
        }
        std::fprintf(log,"]");
    }
    std::fprintf(log,"}\n");std::fflush(log);stageSamples++;started=true;
    return sequence>=5000||pastTurn(p,base);
}
'''
s=s[:a]+body+s[b:]
# Change marker addresses only in the original debugger main, preserving the helpers.
head,main=s.split('\nint wmain(',1)
main=main.replace('0x3F9344','0x15B070').replace('0x3AA3D5','0x15B12F').replace('0x3AA43B','0x3AA805')
# Previous DR3 was RNG; now it is the combat gate. The newly substituted DR2 must stay RNG.
main=main.replace('c.Dr3=base+0x3AA805','c.Dr3=base+0x3F9344').replace('((c.Dr6&8) && c.Rip==base+0x3AA805)','((c.Dr6&8) && c.Rip==base+0x3F9344)')
main=main.replace('if(!stopping && (stopRequested || GetTickCount64()>=deadline || GetFileAttributesW(stopPath.c_str())!=INVALID_FILE_ATTRIBUTES))',
    'if(!stopping && (stopRequested || GetTickCount64()>=deadline || GetFileAttributesW(stopPath.c_str())!=INVALID_FILE_ATTRIBUTES || (!fixtureMode&&started&&pastTurn(process,base))))')
s=head+'\nint wmain('+main
s=s.replace('// Observation-only combat gate logger. No game code/data writes or game calls. RNG writers are observed before the native store.',
    '// Observation-only camera/tactics/RNG trace. No game code/data writes or calls. Debugger alters scheduling; RNG snapshot is before native store.')
assert 'WriteProcessMemory(' not in s and 'VirtualAllocEx(' not in s
(ROOT/'observe_camera_route.cpp').write_text(s,encoding='utf-8')
test=(ROOT/'test_rng_gate_observer.py').read_text().replace('observe_rng_gate.exe','observe_camera_route.exe').replace('rng-gate-fixtures.json','camera-route-fixtures.json')
(ROOT/'test_camera_route_observer.py').write_text(test,encoding='utf-8')
print('Generated camera route observer and debugger infrastructure tests')
