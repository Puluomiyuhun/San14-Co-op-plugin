"""Derive a gate/pair/eligibility/phase observer, preserving all earlier trials."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'observe_combat_gate.cpp').read_text(encoding='utf-8')
start=source.index('static bool observe(')
end=source.index('\nint wmain(',start)
helper=r'''
static void onePair(FILE* log,HANDLE p,uint64_t node) {
    uint64_t side=rd<uint64_t>(p,node);
    if(!side) throw std::runtime_error("Null pair first side");
    unsigned char a[24],b[24];readExact(p,side,a,sizeof(a));readExact(p,node+8,b,sizeof(b));
    std::fprintf(log,"{\"a\":\"");hexBytes(log,a,sizeof(a));
    std::fprintf(log,"\",\"b\":\"");hexBytes(log,b,sizeof(b));std::fprintf(log,"\"}");
}
static void allPairs(FILE* log,HANDLE p,uint64_t pairs) {
    uint64_t count=rd<uint64_t>(p,pairs+0xC0),node=rd<uint64_t>(p,pairs+0xA0),visited=0;
    if(count>2048)throw std::runtime_error("Unexpected pair count");
    std::fprintf(log,",\"pairs\":[");
    while(node) {
        if(visited>=count)throw std::runtime_error("Pair list length/cycle mismatch");
        if(visited)std::fprintf(log,",");onePair(log,p,node);visited++;
        node=rd<uint64_t>(p,node+0x30);
    }
    if(visited!=count)throw std::runtime_error("Pair count mismatch");
    std::fprintf(log,"]");
}
static void armySnapshot(FILE* log,HANDLE p,uint64_t base,uint64_t root) {
    uint64_t armies[501];readExact(p,root+0x7DF60,armies,sizeof(armies));
    for(unsigned i=0;i<501;i++)if(armies[i]!=armies[0]+i*0x200)throw std::runtime_error("Army table layout changed");
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
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    const uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World vtable mismatch");
    bool gate=c.Rip==base+0x3F9344,ready=c.Rip==base+0x16C685,decision=c.Rip==base+0x15C045;
    const char* kind=gate?"combat_gate":ready?"pairs_ready":decision?"pair_eligibility":"pair_phase";
    if(gate&&rd<uint64_t>(p,c.Rbx)!=base+0x12CC770)throw std::runtime_error("Progress vtable mismatch");
    if(ready&&c.Rbx!=base+0x1A24CF0)throw std::runtime_error("Battle manager mismatch");
    uint64_t manager=base+0x1A24CF0,effects=base+0x1A38A20,pairs=base+0x1A38840;
    if(!gate&&!ready&&c.R15!=pairs)throw std::runtime_error("Pair processor context mismatch");
    uint64_t filter=rd<uint64_t>(p,base+0x201EC70);
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"tick_ms\":%llu,\"thread\":%lu,\"rva\":%llu,",kind,++sequence,GetTickCount64(),tid,c.Rip-base);
    dateFields(log,p,world);
    unsigned hour=rd<uint8_t>(p,world+0x38),day=rd<uint8_t>(p,world+0x37);
    std::fprintf(log,",\"subday\":%u,\"global_rng\":%u,\"worker_90\":%u,\"pending_94\":%u,\"effect_count\":%llu,\"effect_pending_98\":%u,\"pair_count\":%llu,\"eax\":%u,\"special_filter_enabled\":%u,\"world_field_165c\":%u",
        hour,rd<uint32_t>(p,base+0x18EB8B0),rd<uint32_t>(p,manager+0x90),rd<uint32_t>(p,manager+0x94),
        rd<uint64_t>(p,effects+0x38),rd<uint32_t>(p,effects+0x98),rd<uint64_t>(p,pairs+0xC0),uint32_t(c.Rax),
        filter?rd<uint32_t>(p,filter):0,rd<uint8_t>(p,world+0x165C));
    if(gate)std::fprintf(log,",\"stage\":%u,\"rbp_gate\":%llu,\"rsi_substep\":%llu",rd<uint32_t>(p,c.Rbx+0x484),c.Rbp,c.Rsi);
    if(gate||ready) {
        allPairs(log,p,pairs);armySnapshot(log,p,base,root);
        std::fprintf(log,",\"force_predicate_inputs\":[");
        for(unsigned i=0;i<52;i++) {
            uint64_t f=rd<uint64_t>(p,root+0xDCA0+i*8);unsigned char rel[52];readExact(p,f+0xEA,rel,sizeof(rel));
            std::fprintf(log,"%s{\"id\":%u,\"field_12\":%u,\"field_194\":%u,\"field_ea_11d_hex\":\"",i?",":"",i,rd<uint8_t>(p,f+0x12),rd<uint8_t>(p,f+0x194));
            hexBytes(log,rel,sizeof(rel));std::fprintf(log,"\"}");
        }
        std::fprintf(log,"]");
    } else {
        std::fprintf(log,",\"pair\":");onePair(log,p,c.Rbx);
        if(decision)std::fprintf(log,",\"eligibility_before_special_filter\":%u",uint32_t(c.Rbp));
        else {
            if(c.Rdi<1||c.Rdi>7)throw std::runtime_error("Unexpected pair phase");
            std::fprintf(log,",\"phase\":%llu",c.Rdi);
        }
    }
    std::fprintf(log,"}\n");std::fflush(log);stageSamples++;started=true;
    return stageSamples>=3000 || (gate&&(day>12||(day==12&&hour>=12)));
}
'''
source=source[:start]+helper+source[end:]
# Only the debugger dispatcher/arming portion changes; helper RVAs remain intact.
head,main=source.split('\nint wmain(',1)
# Replace exact DR1/2/3 assignments and matching tests without cascading RVAs.
old=(ROOT/'observe_combat_gate.cpp').read_text(encoding='utf-8').split('\nint wmain(',1)[1]
main=old.replace('0x16C640','BRANCH_PAIR_READY').replace('0x16C685','BRANCH_DECISION').replace('0x3F935A','BRANCH_PHASE')
main=main.replace('BRANCH_PAIR_READY','0x16C685').replace('BRANCH_DECISION','0x15C045').replace('BRANCH_PHASE','0x15C0B0')
source=head+'\nint wmain('+main
assert 'WriteProcessMemory(' not in source
(ROOT/'observe_battle_branches.cpp').write_text(source,encoding='utf-8')
test=(ROOT/'test_combat_gate_observer.py').read_text(encoding='utf-8').replace('observe_combat_gate.exe','observe_battle_branches.exe').replace('combat-gate-fixtures.json','battle-branch-fixtures.json')
(ROOT/'test_battle_branch_observer.py').write_text(test,encoding='utf-8')
runner=(ROOT/'start_load_rng_observer.py').read_text(encoding='utf-8')
runner=runner.replace('load-rng-fixtures.json','battle-branch-fixtures.json').replace('observe_load_rng.exe','observe_battle_branches.exe')
runner=runner.replace('from finalize_lockstep_capture import diagnostics','from finalize_lockstep_capture import diagnostics\nfrom battle_branch_inputs import capture_branch_inputs')
runner=runner.replace('points = (0x3AA3E0,0x3AA3D5,0x3AA43B,0x3AA805)','points = (0x3F9344,0x16C685,0x15C045,0x15C0B0)')
runner=runner.replace("'0x3aa3e0'","'0x3f9344'")
runner=runner.replace('this experiment observes restoration, not turn repeatability.','this experiment diagnoses branches, not a matched-start repeatability trial.')
runner=runner.replace('    run.mkdir()',"    branch_inputs = capture_branch_inputs(reader)\n    assert branch_inputs == capture_branch_inputs(reader) and before == sample(reader)\n    run.mkdir()")
runner=runner.replace("('before-diagnostics.json',diag)","('before-diagnostics.json',diag),('before-branch-inputs.json',branch_inputs)")
runner=runner.replace('Hardware execution breakpoints at RNG setter and three consuming stores, with raw stack snapshots and state names. No game code/data writes.',
    'Hardware execution breakpoints at combat gate, pair rebuild return, per-pair eligibility and phase dispatch. No game code/data writes.')
runner=runner.replace('After 2000 RNG events or timeout/cancel; native game continues after detach','After day12 subday12 gate, 3000 events, or timeout/cancel; native game continues after detach')
(ROOT/'start_battle_branch_observer.py').write_text(runner,encoding='utf-8')
print('Generated independent branch observer, runner, and fixtures')
