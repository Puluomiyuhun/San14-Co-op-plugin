"""Trace callers of the three discovered consuming RNG variants and combat gates."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'observe_combat_gate.cpp').read_text(encoding='utf-8')
s=s.replace('0x16C640','0x3AA3D5').replace('0x16C685','0x3AA43B').replace('0x3F935A','0x3AA805')
s=s.replace('c.Dr7|=started?0x54:0x14;', 'c.Dr7|=0x54;')
a=s.index('    const char* kind=')
b=s.index('    uint64_t armies[501];',a)
s=s[:a]+r'''
    bool gate=c.Rip==base+0x3F9344;
    uint64_t manager=base+0x1A24CF0,effects=base+0x1A38A20,pairs=base+0x1A38840;
    unsigned hour=rd<uint8_t>(p,world+0x38),day=rd<uint8_t>(p,world+0x37);
    if(!gate) {
        uint64_t caller=rd<uint64_t>(p,c.Rsp);
        uint32_t next=uint32_t(c.Rip==base+0x3AA43B?c.Rcx:c.Rax);
        std::fprintf(log,"{\"event\":\"rng_update\",\"seq\":%llu,\"thread\":%lu,\"writer_rva\":%llu,\"caller_rva\":%llu,\"before\":%u,\"after\":%u,\"range_register_ecx\":%u,",
            ++sequence,tid,c.Rip-base,caller>=base&&caller<base+0x2238000?caller-base:0,
            rd<uint32_t>(p,base+0x18EB8B0),next,uint32_t(c.Rcx));
        dateFields(log,p,world);std::fprintf(log,",\"subday\":%u}\n",hour);std::fflush(log);
        stageSamples++;started=true;return sequence>=10000;
    }
    if(rd<uint64_t>(p,c.Rbx)!=base+0x12CC770) throw std::runtime_error("Progress vtable mismatch");
    std::fprintf(log,"{\"event\":\"combat_gate\",\"seq\":%llu,\"thread\":%lu,",++sequence,tid);
    dateFields(log,p,world);
    std::fprintf(log,",\"subday\":%u,\"global_rng\":%u,\"worker_90\":%u,\"pending_94\":%u,\"effect_count\":%llu,\"effect_pending_98\":%u,\"pair_count\":%llu,\"stage\":%u,\"rbp_gate\":%llu,\"rsi_substep\":%llu",
        hour,rd<uint32_t>(p,base+0x18EB8B0),rd<uint32_t>(p,manager+0x90),rd<uint32_t>(p,manager+0x94),
        rd<uint64_t>(p,effects+0x38),rd<uint32_t>(p,effects+0x98),rd<uint64_t>(p,pairs+0xC0),
        rd<uint32_t>(p,c.Rbx+0x484),c.Rbp,c.Rsi);
''' + s[b:]
s=s.replace('No game code/data writes or game calls.', 'No game code/data writes or game calls. RNG writers are observed before the native store.')
assert 'WriteProcessMemory(' not in s
(ROOT/'observe_rng_gate.cpp').write_text(s,encoding='utf-8')
t=(ROOT/'test_combat_gate_observer.py').read_text(encoding='utf-8').replace('observe_combat_gate.exe','observe_rng_gate.exe').replace('combat-gate-fixtures.json','rng-gate-fixtures.json')
(ROOT/'test_rng_gate_observer.py').write_text(t,encoding='utf-8')
t=(ROOT/'start_combat_gate_observer.py').read_text(encoding='utf-8').replace('observe_combat_gate.exe','observe_rng_gate.exe').replace('combat-gate-fixtures.json','rng-gate-fixtures.json')
t=t.replace('(0x3F9344,0x16C640,0x16C685,0x3F935A)','(0x3F9344,0x3AA3D5,0x3AA43B,0x3AA805)')
t=t.replace('Hardware execution breakpoints at combat gate, entry, pair-generation return, combat return.','Hardware execution breakpoints at combat gate and three consuming RNG stores, including caller identity.')
t=t.replace('or timeout/cancel;', 'or 10000 observations or timeout/cancel;')
(ROOT/'start_rng_gate_observer.py').write_text(t,encoding='utf-8')
print('Created RNG call-site observer')
