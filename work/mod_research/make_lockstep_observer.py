"""Derive a bounded, observation-only hardware-breakpoint logger.
Reuses the already exercised debugger attach/cleanup implementation.
"""
from pathlib import Path

root = Path(__file__).resolve().parent
source = (root / "observe_submit.cpp").read_text()
# Remove all replay-only preprocessor branches. This target must never write game data.
lines = source.splitlines(keepends=True)
result = []
stack = []
active = True
for line in lines:
    if line.startswith("#ifdef SAN14_REPLAY"):
        stack.append(active); active = False
    elif line.startswith("#else") and stack:
        active = stack[-1] and not active
    elif line.startswith("#endif") and stack:
        active = stack.pop()
    elif active:
        result.append(line)
source = "".join(result)
source = source.replace("#include <cstring>", "#include <cstring>\n#include <vector>")
helper = r'''
template<class T> static T rd(HANDLE p,uint64_t a) { T v{};readExact(p,a,&v,sizeof(v));return v; }
static uint64_t sequence=0, stageSamples=0, casualtySamples=0, moveSamples=0, fixtureSamples=0;
static bool started=false, fixtureMode=false;
static void hexBytes(FILE* f,const unsigned char* data,size_t size) {
    static const char digits[]="0123456789abcdef";
    for(size_t i=0;i<size;i++) { std::fputc(digits[data[i]>>4],f);std::fputc(digits[data[i]&15],f); }
}
static void dateFields(FILE* log,HANDLE p,uint64_t world) {
    unsigned char date[8]; readExact(p,world+0x34,date,8);
    uint32_t inputs[4];readExact(p,world+0x450,inputs,16);
    std::fprintf(log,"\"date\":[%u,%u,%u],\"player\":%u,\"world_inputs\":[%u,%u,%u,%u]",
        unsigned(date[0]|date[1]<<8),date[2],date[3],date[6],inputs[0],inputs[1],inputs[2],inputs[3]);
}
static void stageSample(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    const uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,c.Rbx)!=base+0x12CC770 || rd<uint64_t>(p,world)!=base+0x12AA638)
        throw std::runtime_error("Stage/world vtable mismatch");
    uint32_t stage=rd<uint32_t>(p,c.Rbx+0x484);
    if(stage>30) throw std::runtime_error("Invalid progress stage");
    uint64_t armies[501];readExact(p,root+0x7DF60,armies,sizeof(armies));
    for(unsigned i=0;i<501;i++) if(armies[i]!=armies[0]+i*0x200) throw std::runtime_error("Army table layout changed");
    std::vector<unsigned char> rows(501*0x200);readExact(p,armies[0],rows.data(),rows.size());
    std::fprintf(log,"{\"event\":\"stage\",\"seq\":%llu,\"thread\":%lu,\"stage\":%u,",++sequence,tid,stage);
    dateFields(log,p,world);
    std::fprintf(log,",\"global_rng\":%u,\"armies\":[",rd<uint32_t>(p,base+0x18EB8B0));
    bool comma=false;
    for(unsigned i=1;i<501;i++) {
        const auto row=rows.data()+i*0x200;
        if(!row[0x10] || !(row[0x12]|row[0x13])) continue;
        if(rd<uint64_t>(p,armies[i])!=base+0x123E288) throw std::runtime_error("Army vtable mismatch");
        std::fprintf(log,"%s[%u,\"",comma?",":"",i);hexBytes(log,row+0x10,0x58);std::fprintf(log,"\"]");comma=true;
    }
    std::fprintf(log,"],\"cities\":[");
    for(unsigned i=0;i<52;i++) {
        uint64_t city=rd<uint64_t>(p,root+0xDAA8+i*8);
        unsigned char row[0x58];readExact(p,city+0x10,row,sizeof(row));
        std::fprintf(log,"%s[%u,\"",i?",":"",i);hexBytes(log,row,sizeof(row));std::fprintf(log,"\"]");
    }
    std::fprintf(log,"]}\n");std::fflush(log);stageSamples++;started=true;
}
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);
        std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    if(c.Rip==base+0x3F9219) stageSample(log,p,base,c,tid);
    else if(c.Rip==base+0x16AC60) {
        uint32_t sourceId=rd<uint32_t>(p,c.Rsp+0x28);
        uint64_t caller=rd<uint64_t>(p,c.Rsp);
        std::fprintf(log,"{\"event\":\"casualty_request\",\"seq\":%llu,\"thread\":%lu,\"target_kind\":%u,\"target_id\":%u,\"amount\":%d,\"source_kind\":%u,\"source_id\":%u,\"caller_rva\":%llu}\n",
            ++sequence,tid,uint32_t(c.Rcx),uint32_t(c.Rdx),int32_t(c.R8),uint32_t(c.R9),sourceId,caller-base);
        std::fflush(log);casualtySamples++;
    } else if(c.Rip==base+0x2A9DA4) {
        uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),first=rd<uint64_t>(p,root+0x7DF60);
        if(c.Rdi<first || c.Rdi>=first+501*0x200 || (c.Rdi-first)%0x200)
            throw std::runtime_error("Move object outside army table");
        std::fprintf(log,"{\"event\":\"move_write\",\"seq\":%llu,\"thread\":%lu,\"army_id\":%llu,\"from\":%u,\"to\":%u}\n",
            ++sequence,tid,(c.Rdi-first)/0x200,rd<uint16_t>(p,c.Rdi+0x2A),uint16_t(c.Rax));
        std::fflush(log);moveSamples++;
    } else if(c.Rip==base+0x3F9B00 && started) {
        uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
        if(rd<uint8_t>(p,world+0x37)!=11) {
            std::fprintf(log,"{\"event\":\"planning_return\",");dateFields(log,p,world);
            std::fprintf(log,",\"global_rng\":%u,\"stage_samples\":%llu,\"casualty_requests\":%llu,\"move_writes\":%llu}\n",
                rd<uint32_t>(p,base+0x18EB8B0),stageSamples,casualtySamples,moveSamples);
            std::fflush(log);return true;
        }
    }
    return false;
}
'''
source = source.replace("int wmain(", helper + "\nint wmain(")
source = source.replace('unsigned timeout=wcstoul(argv[4],nullptr,0);',
'''unsigned timeout=wcstoul(argv[4],nullptr,0);
    std::wstring stopPath=std::wstring(argv[5])+L".stop";''')
source = source.replace('if(stopRequested', 'if(stopRequested') # no-op for audit clarity
source = source.replace('(stopRequested || GetTickCount64()>=deadline)',
    '(stopRequested || GetTickCount64()>=deadline || GetFileAttributesW(stopPath.c_str())!=INVALID_FILE_ATTRIBUTES)')
source = source.replace('uint16_t mz=0;', '''fixtureMode=(!_wcsicmp(leaf,L"submit_probe_fixture.exe"));
        if(!fixtureMode && rva!=0x3F9219) throw std::runtime_error("Unexpected native observer entry");
        uint16_t mz=0;''')
source = source.replace('c.Dr7=(c.Dr7&~(DWORD64(0xf)<<16))|1;',
'''c.Dr7=(c.Dr7&~DWORD64(0xffff00ff))|1;
                        if(!fixtureMode) { c.Dr1=base+0x16AC60;c.Dr2=base+0x2A9DA4;c.Dr3=base+0x3F9B00;c.Dr7|=0x14; }''')
start = source.index('                        if(c.Rip==target && (c.Dr6&1)) {')
end = source.index('\n                        }\n', start) + len('\n                        }')
source = source[:start] + r'''                        bool ours=(c.Rip==target && (c.Dr6&1)) ||
                            (!fixtureMode && (((c.Dr6&2) && c.Rip==base+0x16AC60) ||
                            ((c.Dr6&4) && c.Rip==base+0x2A9DA4) || ((c.Dr6&8) && c.Rip==base+0x3F9B00)));
                        if(ours) {
                            bool wasStarted=started;
                            stopping=observe(log,process,base,c,event.dwThreadId) || stopping;
                            hit=stageSamples>0 || fixtureSamples>0;
                            status=DBG_CONTINUE;
                            c.Dr6=0;c.EFlags|=0x10000; // resume this instruction once, preserving all ordinary registers
                            if(started) c.Dr7|=0x40;
                            check(SetThreadContext(it->second.handle,&c),"Resume observed instruction");
                            if(!wasStarted && started) {
                                for(auto& [otherId,other]:threads) if(otherId!=event.dwThreadId) {
                                    auto otherContext=context(other.handle,CONTEXT_DEBUG_REGISTERS);
                                    otherContext.Dr7|=0x40;
                                    check(SetThreadContext(other.handle,&otherContext),"Arm planning return observation");
                                }
                            }
                        }''' + source[end:]
source = source.replace('c.Dr7|=0x14;', 'c.Dr7|=started?0x54:0x14;')
source = source.replace('// Default build observes one native call.', '// Derived observation-only stage logger.')
assert "WriteProcessMemory(" not in source
(root / "observe_lockstep.cpp").write_text(source, encoding="utf-8")
print("Wrote observation-only native logger")
