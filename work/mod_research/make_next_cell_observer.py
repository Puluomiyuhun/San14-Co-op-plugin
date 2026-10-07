"""Derive a narrow data/worker/consumer observer from the validated debug loop."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'observe_pending_writes.cpp').read_text(encoding='utf-8')
def replace(old,new):
    global s
    assert s.count(old)==1,old
    s=s.replace(old,new)
replace('// Observation-only: two four-byte write watches plus two execution markers. No game code/data writes or game calls.',
        '// Observation-only: one two-byte write watch and three execution markers. No game memory writes or native calls.')
replace('static uint32_t previousObserved[2]{};', 'static uint16_t previousObserved=0;')
replace('// L0..L3 enabled; RW0/RW1=01 (write), LEN0/LEN1=11 (four bytes).\n    c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x00dd0055;',
        '// L0..L3 enabled; RW0=01 (write), LEN0=01 (two bytes); others execute.\n    c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x00050055;')
a=s.index('static void snapshot(');b=s.index('\nint wmain(',a)
s=s[:a]+r'''
static void workList(FILE* f,HANDLE p,uint64_t base,uint64_t manager,unsigned off) {
    uint64_t handle=rd<uint64_t>(p,manager+off+8),pool=base+0x201D3A0,node=0,count=0;
    if(handle) {
        uint32_t index=rd<uint32_t>(p,handle),cap=rd<uint32_t>(p,pool+0x40);
        if(cap!=0x14000||index>=cap)throw std::runtime_error("Work list handle invalid");
        node=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x10)+index*8);
        count=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x28)+index*8);
    }
    if(count>501)throw std::runtime_error("Work list count invalid");
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),first=rd<uint64_t>(p,root+0x7DF60),seen=0;
    std::fprintf(f,",\"%s_ids\":[",off?"pending":"working");
    while(node) {
        if(seen>=count)throw std::runtime_error("Work list cycle or count mismatch");
        uint64_t ptr=rd<uint64_t>(p,node);
        if(ptr<first||ptr>=first+501*0x200||(ptr-first)%0x200)throw std::runtime_error("Work list object invalid");
        std::fprintf(f,"%s%llu",seen?",":"",(ptr-first)/0x200);
        seen++;node=rd<uint64_t>(p,node+8);
    }
    if(seen!=count)throw std::runtime_error("Work list truncated");
    std::fprintf(f,"]");
}
static bool snapshot(FILE* f,HANDLE p,uint64_t base) {
    std::fprintf(f,"\"next_cell\":%u",rd<uint16_t>(p,watches[0]));
    if(fixtureMode)return false;
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    uint64_t unit=rd<uint64_t>(p,root+0x7DF60+17*8),manager=base+0x1A24CF0;
    if(unit+0x48!=watches[0]||rd<uint64_t>(p,unit)!=base+0x123E288)throw std::runtime_error("Watched army relocated or wrong type");
    std::fprintf(f,",\"army_id\":17,\"leader\":%u,\"actual_cell\":%u,\"soldiers\":%u,\"worker_90\":%u,\"task_done_70\":%u,\"pending_94\":%u,\"global_rng\":%u,",
        rd<uint16_t>(p,unit+0x12),rd<uint16_t>(p,unit+0x2a),rd<uint16_t>(p,unit+0x16),
        rd<uint32_t>(p,manager+0x90),rd<uint32_t>(p,manager+0x70),rd<uint32_t>(p,manager+0x94),rd<uint32_t>(p,base+0x18EB8B0));
    location(f,p,base);workList(f,p,base,manager,0);workList(f,p,base,manager,0x10);
    uint64_t count=rd<uint64_t>(p,base+0x19E7310+0x10),array=rd<uint64_t>(p,base+0x19E7310+0x20);
    if(count>64)throw std::runtime_error("State stack count invalid");
    bool found=false;
    for(uint64_t i=0;i<count;i++) {
        auto state=rd<uint64_t>(p,array+i*8);
        if(rd<uint64_t>(p,state)==base+0x12CC770) {
            std::fprintf(f,",\"progress_stage\":%u",rd<uint32_t>(p,state+0x484));found=true;
        }
    }
    if(!found)std::fprintf(f,",\"progress_stage\":null");
    unsigned char date[8];readExact(p,world+0x34,date,8);
    return date[0]!=203||date[1]!=0||date[2]!=8||date[3]>=13;
}
static void initialSnapshot(FILE* log,HANDLE p,uint64_t base) {
    previousObserved=rd<uint16_t>(p,watches[0]);
    std::fprintf(log,"{\"event\":\"watch_baseline\",\"tick_ms\":%llu,",GetTickCount64());
    snapshot(log,p,base);std::fprintf(log,"}\n");std::fflush(log);
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    bool late=false;
    for(unsigned slot=0;slot<4;slot++) {
        if(!(c.Dr6&(1ULL<<slot)))continue;
        // The execution marker fires for all units. Only persist army17 consumers.
        if(slot==3&&!fixtureMode&&c.Rdi+0x48!=watches[0]) {
            uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
            if(rd<uint8_t>(p,world+0x37)>=13)return true;
            continue;
        }
        const char* name=slot==0?"next_cell_write":slot==1?"worker_enter":slot==2?"worker_return":"movement_consume";
        std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"tick_ms\":%llu,\"thread\":%lu,\"slot\":%u,\"rip\":%llu,\"rip_rva\":%llu,",
            name,++sequence,GetTickCount64(),tid,slot,c.Rip,c.Rip>=base&&c.Rip<base+0x2238000?c.Rip-base:0);
        if(slot==0) {
            uint16_t value=rd<uint16_t>(p,watches[0]);
            std::fprintf(log,"\"previous_observed\":%u,\"observed_after\":%u,",previousObserved,value);
            previousObserved=value;writeSamples++;
        }
        late=snapshot(log,p,base)||late;contextDetails(log,p,base,c);
        if(slot==3&&!fixtureMode) {
            uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
            if(rd<uint8_t>(p,world+0x37)>=12)late=true;
        }
        std::fprintf(log,",\"rcx\":%llu,\"rdx\":%llu,\"r8\":%llu,\"r9\":%llu",c.Rcx,c.Rdx,c.R8,c.R9);
        unsigned char code[64]{};
        if(c.Rip>=32&&maybe(p,c.Rip-32,code)) {
            std::fprintf(log,",\"code_window_start\":%llu,\"code_window_hex\":\"",c.Rip-32);hexBytes(log,code,sizeof(code));std::fprintf(log,"\"");
        }
        std::fprintf(log,"}\n");stageSamples++;started=true;
    }
    std::fflush(log);
    return fixtureMode?bool(c.Dr6&8):late||sequence>=1500;
}
''' + s[b:]
replace('observer pid base watch0_rva watch1_rva marker_rva gate_rva timeout_seconds log.jsonl',
        'observer pid base watch_absolute enter_rva return_rva consume_rva timeout_seconds log.jsonl')
replace('target=base+rva;', 'target=rva;')
replace(' || rva>0x3000000', '')
s=s.replace('pending_watch_fixture.exe','next_cell_fixture.exe')
replace('if((watches[0]&3)||(watches[1]&3))throw std::runtime_error("Unaligned data watch");',
        'if(watches[0]&1)throw std::runtime_error("Unaligned two-byte data watch");')
replace('if(!fixtureMode && (rva!=0x1A24D84 || watches[1]!=base+0x1A38AB8 || watches[2]!=base+0x3AA3E0 || watches[3]!=base+0x3F9344))',
        'if(!fixtureMode && (watches[0]!=rd<uint64_t>(process,rd<uint64_t>(process,base+0x1FCA1E0)+0x7DF60+17*8)+0x48 || watches[1]!=base+0x16C2C0 || watches[2]!=base+0x16C2B7 || watches[3]!=base+0x2A9D94))')
replace('bool ours=(c.Dr6&3)||((c.Dr6&4)&&c.Rip==watches[2])||((c.Dr6&8)&&c.Rip==watches[3]);',
        'bool ours=(c.Dr6&1)||((c.Dr6&2)&&c.Rip==watches[1])||((c.Dr6&4)&&c.Rip==watches[2])||((c.Dr6&8)&&c.Rip==watches[3]);')
replace('if(c.Dr6&12)c.EFlags|=0x10000;', 'if(c.Dr6&14)c.EFlags|=0x10000;')
(ROOT/'observe_next_cell.cpp').write_text(s,encoding='utf-8')
print('Generated observe_next_cell.cpp')
