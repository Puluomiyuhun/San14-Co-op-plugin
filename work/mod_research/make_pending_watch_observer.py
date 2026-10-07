"""Derive a separate mixed data/execution observer; preserve previous experiments."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
s = (ROOT/'observe_load_rng.cpp').read_text(encoding='utf-8')
def replace(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

replace('// Observation-only combat gate logger. No game code/data writes or game calls. RNG writers are observed before the native store.',
        '// Observation-only: two four-byte write watches plus two execution markers. No game code/data writes or game calls.')
replace('static bool started=false, fixtureMode=false;', '''static bool started=false, fixtureMode=false;
static uint64_t watches[4]{};
static uint32_t previousObserved[2]{};
static uint64_t writeSamples=0, markerSamples=0, gateSamples=0;
static void arm(CONTEXT& c) {
    c.Dr0=watches[0]; c.Dr1=watches[1]; c.Dr2=watches[2]; c.Dr3=watches[3]; c.Dr6=0;
    // L0..L3 enabled; RW0/RW1=01 (write), LEN0/LEN1=11 (four bytes).
    c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x00dd0055;
}''')
a = s.index('static bool observe(')
b = s.index('\nint wmain(', a)
s = s[:a] + r'''
static void snapshot(FILE* f,HANDLE p,uint64_t base) {
    std::fprintf(f,"\"pending_94\":%u,\"effect_pending_98\":%u",rd<uint32_t>(p,watches[0]),rd<uint32_t>(p,watches[1]));
    if(!fixtureMode) {
        std::fprintf(f,",\"worker_90\":%u,\"effect_count_38\":%llu,\"pair_count_c0\":%llu,\"global_rng\":%u,",
            rd<uint32_t>(p,base+0x1A24D80),rd<uint64_t>(p,base+0x1A38A58),rd<uint64_t>(p,base+0x1A38900),rd<uint32_t>(p,base+0x18EB8B0));
        location(f,p,base);
    }
}
static void initialSnapshot(FILE* log,HANDLE p,uint64_t base) {
    previousObserved[0]=rd<uint32_t>(p,watches[0]); previousObserved[1]=rd<uint32_t>(p,watches[1]);
    std::fprintf(log,"{\"event\":\"watch_baseline\",\"tick_ms\":%llu,",GetTickCount64());
    snapshot(log,p,base);std::fprintf(log,"}\n");std::fflush(log);
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    for(unsigned slot=0;slot<4;slot++) {
        if(!(c.Dr6&(1ULL<<slot)))continue;
        const char* name=slot<2?"field_write":slot==2?"load_rng_setter":"combat_gate";
        std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"tick_ms\":%llu,\"thread\":%lu,\"slot\":%u,\"rip\":%llu,\"rip_rva\":%llu,",
            name,++sequence,GetTickCount64(),tid,slot,c.Rip,c.Rip>=base&&c.Rip<base+0x2238000?c.Rip-base:0);
        if(slot<2) {
            uint32_t value=rd<uint32_t>(p,watches[slot]);
            std::fprintf(log,"\"previous_observed\":%u,\"observed_after\":%u,",previousObserved[slot],value);
            previousObserved[slot]=value;writeSamples++;
        } else if(slot==2) {
            std::fprintf(log,"\"setter_value\":%u,",uint32_t(c.Rcx));markerSamples++;
        } else {
            std::fprintf(log,"\"rbp_gate\":%llu,\"rsi_substep\":%llu,",c.Rbp,c.Rsi);gateSamples++;
        }
        snapshot(log,p,base);contextDetails(log,p,base,c);
        if(slot==3&&!fixtureMode) {
            if(rd<uint64_t>(p,c.Rbx)!=base+0x12CC770)throw std::runtime_error("Progress vtable mismatch");
            std::fprintf(log,",\"stage\":%u",rd<uint32_t>(p,c.Rbx+0x484));
            const auto root=rd<uint64_t>(p,base+0x1FCA1E0);
            uint64_t armies[501];readExact(p,root+0x7DF60,armies,sizeof(armies));
            for(unsigned i=0;i<501;i++)if(armies[i]!=armies[0]+i*0x200)throw std::runtime_error("Army table layout mismatch");
            std::vector<unsigned char> rows(501*0x200);readExact(p,armies[0],rows.data(),rows.size());
            std::fprintf(log,",\"armies\":[");bool comma=false;
            for(unsigned i=1;i<501;i++) {
                const auto row=rows.data()+i*0x200;
                if(!row[0x10]||!(row[0x12]|row[0x13]))continue;
                uint64_t vt;std::memcpy(&vt,row,8);
                if(vt!=base+0x123E288)throw std::runtime_error("Army vtable mismatch");
                std::fprintf(log,"%s[%u,\"",comma?",":"",i);hexBytes(log,row+0x10,0x58);std::fprintf(log,"\"]");comma=true;
            }
            std::fprintf(log,"]");
        }
        // Data break RIP is after the write. Preserve bytes; decode offline from verified boundaries.
        unsigned char code[64]{};
        if(c.Rip>=32 && maybe(p,c.Rip-32,code)) {
            std::fprintf(log,",\"code_window_start\":%llu,\"code_window_hex\":\"",c.Rip-32);
            hexBytes(log,code,sizeof(code));std::fprintf(log,"\"");
        }
        std::fprintf(log,"}\n");
    }
    std::fflush(log); stageSamples++; started=true;
    if(fixtureMode)return gateSamples>0;
    // End once two daily combat gates have had their chance to run.
    uint64_t root=0,world=0;unsigned char date[8]{};
    bool late=(c.Dr6&8)&&maybe(p,base+0x1FCA1E0,root)&&root&&maybe(p,root+0x85130,world)&&world&&maybe(p,world+0x34,date)
        &&date[0]==203&&date[1]==0&&date[2]==8&&(date[3]>12||(date[3]==12&&date[4]>=12));
    return late||sequence>=3000;
}
''' + s[b:]
replace('6;\n    if(argc', '9;\n    if(argc')
replace('Usage: probe pid base rva timeout_seconds log.jsonl [expected.bin recorded.bin]', 'Usage: observer pid base watch0_rva watch1_rva marker_rva gate_rva timeout_seconds log.jsonl')
replace('unsigned timeout=wcstoul(argv[4],nullptr,0);', '''watches[0]=target; watches[1]=base+_wcstoui64(argv[4],nullptr,0);
    watches[2]=base+_wcstoui64(argv[5],nullptr,0); watches[3]=base+_wcstoui64(argv[6],nullptr,0);
    unsigned timeout=wcstoul(argv[7],nullptr,0);''')
s=s.replace('argv[5])+L".stop"', 'argv[8])+L".stop"').replace('_wfsopen(argv[5],', '_wfsopen(argv[8],')
s=s.replace('submit_probe_fixture.exe','pending_watch_fixture.exe')
replace('if(!fixtureMode && rva!=0x3AA3E0) throw std::runtime_error("Unexpected native observer entry");', '''if((watches[0]&3)||(watches[1]&3))throw std::runtime_error("Unaligned data watch");
        if(!fixtureMode && (rva!=0x1A24D84 || watches[1]!=base+0x1A38AB8 || watches[2]!=base+0x3AA3E0 || watches[3]!=base+0x3F9344))
            throw std::runtime_error("Unexpected native observer addresses");''')
a=s.index('                        c.Dr0=target; c.Dr6=0;')
b=s.index('\n                    }',a)
s=s[:a]+'''                        arm(c);
                        check(SetThreadContext(th,&c),"Arm data and execution breakpoints");'''+s[b:]
replace('if(!stopping) {\n                        std::fprintf(log,"{\\"event\\":\\"armed\\"', 'if(!stopping) {\n                        initialSnapshot(log,process,base);\n                        std::fprintf(log,"{\\"event\\":\\"armed\\"')
a=s.index('                        bool ours=')
b=s.index('\n                        if(ours)',a)
s=s[:a]+'''                        bool ours=(c.Dr6&3)||((c.Dr6&4)&&c.Rip==watches[2])||((c.Dr6&8)&&c.Rip==watches[3]);'''+s[b:]
s=s.replace('                            bool wasStarted=started;\n','')
a=s.index('                            c.Dr6=0;c.EFlags|=0x10000;')
b=s.index('\n                        }\n                    }',a)
s=s[:a]+'''                            if(c.Dr6&12)c.EFlags|=0x10000; // RF only for execution breakpoints.
                            c.Dr6=0;
                            check(SetThreadContext(it->second.handle,&c),"Resume observed thread");'''+s[b:]
assert 'WriteProcessMemory' not in s and 'if(started) c.Dr7' not in s
(ROOT/'observe_pending_writes.cpp').write_text(s,encoding='utf-8')
print('Generated observer with two data writes and two execution markers')
