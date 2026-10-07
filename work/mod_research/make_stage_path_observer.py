"""Preserve the old full stage sample while closing its branch-observation gaps."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=(ROOT/'observe_lockstep.cpp').read_text(encoding='utf-8')
source=source.replace('#include <vector>','#include <vector>\n#include <set>')
helpers=r'''
static void pathState(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c) {
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    uint64_t filter=rd<uint64_t>(p,base+0x201EC70);
    std::fprintf(log,",\"subday\":%u,\"rbp\":%llu,\"rsi\":%llu,\"rdi\":%llu,\"eax\":%u,\"tick_ms\":%llu,\"pending_94\":%u,\"effect_pending_98\":%u,\"effect_count\":%llu,\"pair_count\":%llu,\"special_filter\":%u,\"world_165c\":%u",
        rd<uint8_t>(p,world+0x38),c.Rbp,c.Rsi,c.Rdi,uint32_t(c.Rax),GetTickCount64(),
        rd<uint32_t>(p,base+0x1A24D84),rd<uint32_t>(p,base+0x1A38AB8),rd<uint64_t>(p,base+0x1A38A58),
        rd<uint64_t>(p,base+0x1A38900),filter?rd<uint32_t>(p,filter):0,rd<uint8_t>(p,world+0x165C));
}
static void onePair(FILE* log,HANDLE p,uint64_t node) {
    uint64_t side=rd<uint64_t>(p,node);
    if(!side)throw std::runtime_error("Null pair first side");
    unsigned char a[24],b[24];readExact(p,side,a,sizeof(a));readExact(p,node+8,b,sizeof(b));
    std::fprintf(log,"{\"a\":\"");hexBytes(log,a,sizeof(a));std::fprintf(log,"\",\"b\":\"");hexBytes(log,b,sizeof(b));std::fprintf(log,"\"}");
}
static void allPairs(FILE* log,HANDLE p,uint64_t base) {
    uint64_t count=rd<uint64_t>(p,base+0x1A38900),node=rd<uint64_t>(p,base+0x1A388E0),last=0,visited=0;
    if(count>2048)throw std::runtime_error("Unexpected pair count");
    std::fprintf(log,",\"pairs\":[");
    while(node) {
        if(visited>=count || rd<uint64_t>(p,node+0x38)!=last)throw std::runtime_error("Pair links/count mismatch");
        if(visited)std::fprintf(log,",");onePair(log,p,node);visited++;last=node;node=rd<uint64_t>(p,node+0x30);
    }
    if(visited!=count)throw std::runtime_error("Pair count mismatch");std::fprintf(log,"]");
}
static void inputLists(FILE* log,HANDLE p,uint64_t base,uint64_t root) {
    const uint64_t first=rd<uint64_t>(p,root+0x7DF60);
    std::fprintf(log,",\"input_lists\":[");
    const unsigned offsets[]={0x58,0x68,0x88,0x98,0x138};
    for(unsigned li=0;li<5;li++) {
        unsigned off=offsets[li];bool ann=off==0x138;
        uint64_t pool=base+(ann?0x1FC9760:0x201D3A0),vt=rd<uint64_t>(p,root+off);
        unsigned expected=ann?0x12AA618:off==0x88?0x123F3C8:off==0x98?0x123F3D8:0x123E200;
        if(vt!=base+expected || !rd<uint64_t>(p,pool+8))throw std::runtime_error("Input list type/pool mismatch");
        uint64_t handle=rd<uint64_t>(p,root+off+8),count=0,node=0,tail=0;
        if(handle) {
            unsigned slot=rd<uint32_t>(p,handle),cap=rd<uint32_t>(p,pool+0x40);
            if(cap!=(ann?0x40u:0x14000u)||slot>=cap)throw std::runtime_error("Input list handle mismatch");
            count=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x28)+slot*8);
            node=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x10)+slot*8);
            tail=rd<uint64_t>(p,rd<uint64_t>(p,pool+0x18)+slot*8);
        }
        if(count>(ann?128u:501u))throw std::runtime_error("Input list count outside bound");
        std::fprintf(log,"%s{\"root_offset\":%u,\"count\":%llu,\"entries\":[",li?",":"",off,count);
        uint64_t visited=0,previous=0;std::set<uint64_t> seen;
        while(node) {
            if(visited>=count||!seen.insert(node).second||rd<uint64_t>(p,node+(ann?0x38:0x10))!=previous)throw std::runtime_error("Input list links invalid");
            if(visited)std::fprintf(log,",");
            if(ann) {
                unsigned char raw[48];readExact(p,node,raw,sizeof(raw));std::fprintf(log,"{\"raw_00_30\":\"");hexBytes(log,raw,sizeof(raw));std::fprintf(log,"\",\"army_members\":[");
                for(unsigned k=0;k<3;k++) {
                    uint64_t object;std::memcpy(&object,raw+k*8,8);long long id=-1;
                    if(object>=first&&object<first+501*0x200&&(object-first)%0x200==0)id=(object-first)/0x200;
                    std::fprintf(log,"%s%lld",k?",":"",id);
                }
                std::fprintf(log,"]}");
            } else {
                uint64_t object=rd<uint64_t>(p,node);unsigned id;
                if(off==0x58||off==0x68) {
                    if(object<first||object>=first+501*0x200||(object-first)%0x200||rd<uint64_t>(p,object)!=base+0x123E288)throw std::runtime_error("Invalid army list element");
                    id=unsigned((object-first)/0x200);
                } else id=rd<uint16_t>(p,object+0x10);
                std::fprintf(log,"%u",id);
            }
            visited++;previous=node;node=rd<uint64_t>(p,node+(ann?0x30:8));
        }
        if(visited!=count||previous!=tail)throw std::runtime_error("Input list tail/count mismatch");std::fprintf(log,"]}");
    }
    std::fprintf(log,"]");
}
static void forceInputs(FILE* log,HANDLE p,uint64_t root) {
    std::fprintf(log,",\"forces\":[");
    for(unsigned i=0;i<52;i++) {
        uint64_t f=rd<uint64_t>(p,root+0xDCA0+i*8);unsigned char rel[52];readExact(p,f+0xEA,rel,sizeof(rel));
        std::fprintf(log,"%s{\"id\":%u,\"field_12\":%u,\"field_194\":%u,\"relations\":\"",i?",":"",i,rd<uint8_t>(p,f+0x12),rd<uint8_t>(p,f+0x194));hexBytes(log,rel,sizeof(rel));std::fprintf(log,"\"}");
    }
    std::fprintf(log,"]");
}
'''
at=source.index('static void stageSample(')
source=source[:at]+helpers+source[at:]
needle='    dateFields(log,p,world);\n    std::fprintf(log,",\\\"global_rng'
assert source.count(needle)==1
source=source.replace(needle,'    dateFields(log,p,world);\n    pathState(log,p,base,c);\n    std::fprintf(log,",\\\"frame_start_ms\\\":%u,\\\"budget_elapsed_ms\\\":%u",rd<uint32_t>(p,c.Rsp+0x30),uint32_t(c.Rax));\n    if(stage==12) { inputLists(log,p,base,root);forceInputs(log,p,root);allPairs(log,p,base); }\n    std::fprintf(log,",\\\"global_rng')
a=source.index('static bool observe(');b=source.index('\nint wmain(',a)
observe=r'''
static bool observe(FILE* log,HANDLE p,uint64_t base,const CONTEXT& c,DWORD tid) {
    if(fixtureMode) {
        auto calls=rd<uint32_t>(p,c.Rcx);std::fprintf(log,"{\"event\":\"fixture_hit\",\"value\":%u}\n",calls);std::fflush(log);
        return ++fixtureSamples==3;
    }
    uint64_t root=rd<uint64_t>(p,base+0x1FCA1E0),world=rd<uint64_t>(p,root+0x85130);
    if(rd<uint64_t>(p,world)!=base+0x12AA638)throw std::runtime_error("World type mismatch");
    if(c.Rip==base+0x3F9219) {
        stageSample(log,p,base,c,tid);
        auto day=rd<uint8_t>(p,world+0x37),hour=rd<uint8_t>(p,world+0x38);
        return (day>11 || (day==11&&hour>=12)) || stageSamples>600;
    }
    bool entry=c.Rip==base+0x16C640,ready=c.Rip==base+0x16C685;
    if(entry && c.Rcx!=base+0x1A24CF0)throw std::runtime_error("Battle entry context mismatch");
    if(ready && c.Rbx!=base+0x1A24CF0)throw std::runtime_error("Battle return context mismatch");
    if(!entry&&!ready&&(c.R15!=base+0x1A38840||c.Rdi<1||c.Rdi>7))throw std::runtime_error("Battle phase context mismatch");
    std::fprintf(log,"{\"event\":\"%s\",\"seq\":%llu,\"thread\":%lu,\"rva\":%llu,",entry?"battle_entry":ready?"pairs_ready":"pair_phase",++sequence,tid,c.Rip-base);
    dateFields(log,p,world);pathState(log,p,base,c);
    if(entry)std::fprintf(log,",\"caller_rva\":%llu",rd<uint64_t>(p,c.Rsp)-base);
    else if(ready) {allPairs(log,p,base);inputLists(log,p,base,root);forceInputs(log,p,root);}
    else {std::fprintf(log,",\"phase\":%llu,\"pair\":",c.Rdi);onePair(log,p,c.Rbx);}
    std::fprintf(log,"}\n");std::fflush(log);
    if(sequence>3000)throw std::runtime_error("Observation bound exceeded");return false;
}
'''
source=source[:a]+observe+source[b:]
head,main=source.split('\nint wmain(',1)
main=main.replace('0x16AC60','0x16C640').replace('0x2A9DA4','0x16C685').replace('0x3F9B00','0x15C0B0')
main=main.replace('c.Dr7|=started?0x54:0x14;','c.Dr7|=0x54;')
main=main.replace('if(started) c.Dr7|=0x40;','')
start=main.index('                            if(!wasStarted && started) {')
end=main.index('\n                        }',start)
main=main[:start]+main[end:]
main=main.replace('                            bool wasStarted=started;','                            LARGE_INTEGER costStart{},costEnd{};QueryPerformanceCounter(&costStart);')
needle='                            stopping=observe(log,process,base,c,event.dwThreadId) || stopping;'
main=main.replace(needle,needle+r'''
                            QueryPerformanceCounter(&costEnd);
                            std::fprintf(log,"{\"event\":\"observer_cost\",\"seq\":%llu,\"qpc_ticks\":%lld}\n",sequence,costEnd.QuadPart-costStart.QuadPart);std::fflush(log);''')
main=main.replace('        std::fprintf(log,"{\\\"event\\\":\\\"attached\\\",\\\"pid\\\":%lu,\\\"target_rva\\\":%llu}\\n",pid,rva);',
    '        LARGE_INTEGER frequency{};check(QueryPerformanceFrequency(&frequency),"QPC frequency");\n        std::fprintf(log,"{\\\"event\\\":\\\"attached\\\",\\\"pid\\\":%lu,\\\"target_rva\\\":%llu,\\\"qpc_frequency\\\":%lld}\\n",pid,rva,frequency.QuadPart);')
source=head+'\nint wmain('+main
assert 'WriteProcessMemory(' not in source and 'VirtualAllocEx(' not in source
(ROOT/'observe_stage_path.cpp').write_text(source,encoding='utf-8')
test=(ROOT/'test_lockstep_observer.py').read_text(encoding='utf-8').replace('observe_lockstep.exe','observe_stage_path.exe').replace('lockstep-observer-fixtures.json','stage-path-fixtures.json')
(ROOT/'test_stage_path_observer.py').write_text(test,encoding='utf-8')
print('Generated stage-path observer and infrastructure fixtures')
