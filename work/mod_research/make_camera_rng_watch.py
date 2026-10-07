"""Separate camera observer with one global RNG data-write watch.

Preserve the previous recorder and its evidence. This recorder never writes
game code/data; setting hardware debug registers still changes scheduling.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'observe_camera_route.cpp').read_text(encoding='utf-8')
def replace(old,new):
    global s
    assert s.count(old)==1,(old,s.count(old))
    s=s.replace(old,new)

replace('// Observation-only camera/tactics/RNG trace. No game code/data writes or calls. Debugger alters scheduling; RNG snapshot is before native store.',
        '// Observation-only camera/tactics trace plus AFTER-write RNG watch. No game code/data writes/calls. Debugger changes scheduling.')
replace('static bool started=false, fixtureMode=false;', '''static bool started=false, fixtureMode=false;
static uint64_t rngAddress=0;
static uint32_t previousObservedRng=0;
static void rngBaseline(FILE* log,HANDLE p) {
    previousObservedRng=rd<uint32_t>(p,rngAddress);
    std::fprintf(log,"{\\"event\\":\\"rng_watch_baseline\\",\\"value\\":%u}\\n",previousObservedRng);
}''')
replace('if(fixtureMode){auto v=rd<uint32_t>(p,c.Rcx);std::fprintf(log,"{\\"event\\":\\"fixture_hit\\",\\"value\\":%u}\\n",v);std::fflush(log);return ++fixtureSamples==3;}',r'''if(fixtureMode){
        auto value=rd<uint32_t>(p,rngAddress);
        std::fprintf(log,"{\"event\":\"fixture_write\",\"thread\":%lu,\"previous_observed\":%u,\"observed_after\":%u}\n",tid,previousObservedRng,value);
        previousObservedRng=value;std::fflush(log);return ++fixtureSamples==7;
    }''')
replace('rng=c.Rip==base+0x3AA805','rng=(c.Dr6&4)!=0')
replace('if(!entry&&!decision&&!rng&&!gate)', 'if((int(entry)+int(decision)+int(rng)+int(gate))!=1)')
replace('rng?"rng_update"', 'rng?"rng_write"')
replace('rd<uint32_t>(p,base+0x18EB8B0),uint32_t(c.Rax),uint32_t(c.Rcx),caller>=base',
        'previousObservedRng,rd<uint32_t>(p,rngAddress),uint32_t(c.Rcx),caller>=base')
replace('\\"before\\":%u,\\"after\\":%u,\\"range_ecx\\":%u',
        '\\"previous_observed\\":%u,\\"observed_after\\":%u,\\"ecx_at_stop\\":%u')
replace('        unsigned char stack[2048];SIZE_T n=0;size_t len=sizeof(stack);',r'''        std::fprintf(log,",\"rip_after_rva\":%llu",c.Rip>=base&&c.Rip<base+0x2238000?c.Rip-base:0);
        previousObservedRng=rd<uint32_t>(p,rngAddress);
        unsigned char stack[2048];SIZE_T n=0;size_t len=sizeof(stack);''')
# Add RIP outside stack_hex, not inside the opening quote.
replace(',\\"stack_hex\\":\\"",', '",')
replace('        previousObservedRng=rd<uint32_t>(p,rngAddress);\n        unsigned char stack',
        '        previousObservedRng=rd<uint32_t>(p,rngAddress);\n        std::fprintf(log,",\\"stack_hex\\":\\"");\n        unsigned char stack')
s=s.replace('submit_probe_fixture.exe','pending_watch_fixture.exe')
replace('fixtureMode=(!_wcsicmp(leaf,L"pending_watch_fixture.exe"));',
        'fixtureMode=(!_wcsicmp(leaf,L"pending_watch_fixture.exe"));\n        rngAddress=fixtureMode?target:base+0x18EB8B0;\n        if(rngAddress&3)throw std::runtime_error("Unaligned RNG watch");')
old='''                        c.Dr0=target; c.Dr6=0;
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
                        if(!fixtureMode) { c.Dr1=base+0x15B12F;c.Dr2=base+0x3AA805;c.Dr3=base+0x3F9344;c.Dr7|=0x54; }'''
replace(old,'''                        c.Dr0=fixtureMode?0:target;c.Dr1=fixtureMode?0:base+0x15B12F;
                        c.Dr2=rngAddress;c.Dr3=fixtureMode?0:base+0x3F9344;c.Dr6=0;
                        // L2 enabled, RW2=01/write, LEN2=11/four bytes.
                        c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|0x0d000010;
                        if(!fixtureMode)c.Dr7|=0x45;''')
replace('if(!stopping) {\n                        std::fprintf(log,"{\\"event\\":\\"armed\\"',
        'if(!stopping) {\n                        rngBaseline(log,process);\n                        std::fprintf(log,"{\\"event\\":\\"armed\\"')
start=s.index('                        bool ours=');end=s.index('\n                        if(ours)',start)
s=s[:start]+'''                        bool ours=(c.Dr6&4) || (!fixtureMode &&
                            (((c.Dr6&1)&&c.Rip==target)||((c.Dr6&2)&&c.Rip==base+0x15B12F)||((c.Dr6&8)&&c.Rip==base+0x3F9344)));'''+s[end:]
s=s.replace('                            bool wasStarted=started;\n','')
start=s.index('                            c.Dr6=0;c.EFlags|=0x10000;');end=s.index('\n                        }\n                    }',start)
s=s[:start]+'''                            if(c.Dr6&11)c.EFlags|=0x10000; // RF for execution markers only; data watch already executed.
                            c.Dr6=0;
                            check(SetThreadContext(it->second.handle,&c),"Resume observed thread");'''+s[end:]
assert 'WriteProcessMemory' not in s and '3AA805' not in s
(ROOT/'observe_camera_rng_watch.cpp').write_text(s,encoding='utf-8')
print('Generated AFTER-write global RNG watch with three camera/combat execution markers')
