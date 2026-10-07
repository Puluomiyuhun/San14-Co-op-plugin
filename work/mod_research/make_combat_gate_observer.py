"""Derive a narrow gate/pair/return observer; preserve the original A/B binary."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
source = (ROOT / 'observe_lockstep.cpp').read_text(encoding='utf-8')
begin = source.index('static void stageSample(')
end = source.index('\nint wmain(', begin)
helper = r'''
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    const uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638) throw std::runtime_error("World vtable mismatch");
    const char* kind=c.Rip==base+0x3F9344?"combat_gate":c.Rip==base+0x16C640?"combat_entry":
        c.Rip==base+0x16C685?"pairs_ready":"combat_return";
    bool gate=c.Rip==base+0x3F9344,ret=c.Rip==base+0x3F935A;
    if((gate||ret) && rd<uint64_t>(p,c.Rbx)!=base+0x12CC770) throw std::runtime_error("Progress vtable mismatch");
    if(c.Rip==base+0x16C640 && c.Rcx!=base+0x1A24CF0) throw std::runtime_error("Manager address mismatch");
    uint64_t manager=base+0x1A24CF0,effects=base+0x1A38A20,pairs=base+0x1A38840;
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"rva\":%llu,",kind,++sequence,tid,c.Rip-base);
    dateFields(log,p,world);
    unsigned hour=rd<uint8_t>(p,world+0x38),day=rd<uint8_t>(p,world+0x37);
    std::fprintf(log,",\"subday\":%u,\"global_rng\":%u,\"worker_90\":%u,\"pending_94\":%u,\"effect_count\":%llu,\"effect_pending_98\":%u,\"pair_count\":%llu,\"eax\":%u",
        hour,rd<uint32_t>(p,base+0x18EB8B0),rd<uint32_t>(p,manager+0x90),rd<uint32_t>(p,manager+0x94),
        rd<uint64_t>(p,effects+0x38),rd<uint32_t>(p,effects+0x98),rd<uint64_t>(p,pairs+0xC0),uint32_t(c.Rax));
    if(gate||ret) std::fprintf(log,",\"stage\":%u,\"rbp_gate\":%llu,\"rsi_substep\":%llu",rd<uint32_t>(p,c.Rbx+0x484),c.Rbp,c.Rsi);
    uint64_t armies[501];readExact(p,root+0x7DF60,armies,sizeof(armies));
    for(unsigned i=0;i<501;i++) if(armies[i]!=armies[0]+i*0x200) throw std::runtime_error("Army table layout changed");
    std::vector<unsigned char> rows(501*0x200);readExact(p,armies[0],rows.data(),rows.size());
    std::fprintf(log,",\"armies\":[");bool comma=false;
    for(unsigned i=1;i<501;i++) {
        const auto row=rows.data()+i*0x200;
        if(!row[0x10] || !(row[0x12]|row[0x13])) continue;
        uint64_t vt;std::memcpy(&vt,row,8);
        if(vt!=base+0x123E288) throw std::runtime_error("Army vtable mismatch");
        std::fprintf(log,"%s[%u,\"",comma?",":"",i);hexBytes(log,row+0x10,0x58);std::fprintf(log,"\"]");comma=true;
    }
    std::fprintf(log,"]}\n");std::fflush(log);stageSamples++;started=true;
    // Detach after seeing day12's scheduled combat interval, not a full turn.
    return gate && (day>12 || (day==12 && hour>=12));
}
'''
source = source[:begin] + helper + source[end:]
source = source.replace('0x3F9219', '0x3F9344').replace('0x16AC60', '0x16C640').replace('0x2A9DA4', '0x16C685').replace('0x3F9B00', '0x3F935A')
source = source.replace('// Derived observation-only stage logger. SAN14_REPLAY is a separate development\n// build which substitutes a recorded command at that existing native call only.\n// Neither build patches game code, allocates remote code or creates a game call.',
    '// Observation-only combat gate logger. No game code/data writes or game calls.')
assert 'WriteProcessMemory(' not in source
(ROOT / 'observe_combat_gate.cpp').write_text(source, encoding='utf-8')
test = (ROOT / 'test_lockstep_observer.py').read_text(encoding='utf-8')
test = test.replace('observe_lockstep.exe', 'observe_combat_gate.exe').replace('lockstep-observer-fixtures.json', 'combat-gate-fixtures.json')
(ROOT / 'test_combat_gate_observer.py').write_text(test, encoding='utf-8')
print('Created independent combat gate logger and infrastructure checks')
