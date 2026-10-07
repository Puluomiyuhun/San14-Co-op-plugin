from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=(ROOT/'reward_eligibility_fixture.cpp').read_text()
s=s.replace('#define REWARD_ELIGIBILITY\n','').replace('#include "reward_container_probe.h"\n#include "reward_eligibility_probe.h"','#include "reward_execution_pilot.h"')
s=s.replace('static unsigned updates=0,calls=0;', 'static unsigned updates=0,calls=0,submits=0,appends=0,constructs=0,destructs=0;')
s=s.replace('static Node personNodes[3]{},taskNode{};', 'static Node personNodes[3]{},taskNode{},mainNode{},cityNode{};\nstatic uint64_t mainHandle=3,cityHandle=4;')
start=s.index('static int __fastcall predicate');end=s.index('static DWORD WINAPI tick',start)
c=(ROOT/'reward_container_fixture.cpp').read_text()
begin=c.index('static RewardArgs* __fastcall ctor');finish=c.index('static DWORD WINAPI tick')
funcs=c[begin:finish].replace('argumentsOk','argsOk')
funcs=funcs.replace('    return node;','''    if(test==L"precommit-gold-drift" && appends==3) ref<uint32_t>(city+0x34)=83208;
    if(test==L"wrong-id" && appends==3) nodes[0].value=98;
    return node;''')
s=s[:start]+'''template<class T> static T& ref(uintptr_t p) { return *reinterpret_cast<T*>(p); }
static Node nodes[3]{};static uint64_t handle=7;
'''+funcs+'''static int __fastcall predicate(uintptr_t person) {
    calls++;
    if(ref<uintptr_t>(person)!=base+0x12A00D0)argsOk=false;
    if(test==L"query-exception" && calls==2) RaiseException(0xE0000015,0,0,nullptr);
    if(test==L"eligibility-denied" && calls==2)return 0;
    if(test==L"eligibility-drift" && calls==5)return 0;
    return 1;
}
static int __fastcall submit(RewardArgs* args) {
    submits++;
    if(args->funding!=city || args->handle!=uintptr_t(&handle) || counts[7]!=3)argsOk=false;
    if(test==L"submit-exception")RaiseException(0xE0000016,0,0,nullptr);
    if(test==L"submit-rejected")return 0;
    ref<uint32_t>(city+0x34)-=300;ref<uint8_t>(district+0x14)--;
    for(unsigned i=0;i<3;i++) {
        if(nodes[i].value!=PROBE_IDS[i])argsOk=false;
        auto person=ref<uintptr_t>(root+0x148+PROBE_IDS[i]*8);
        ref<uint8_t>(person+0x120)=100;ref<uint16_t>(person+0x196)|=2;
    }
    if(test==L"unexpected-effect")ref<uint32_t>(city+0x34)--;
    return 1;
}
'''+s[end:]
s=s.replace('put<uint8_t>(person+0x118,11);','put<uint8_t>(person+0x118,9);put<uint8_t>(person+0x11E,4);')
s=s.replace('    auto dll=LoadLibraryW', '''    put<uintptr_t>(city,base+0x129FD10);put<uintptr_t>(ruler,base+0x12A00D0);
    put<uintptr_t>(base+0x129FD10+0x18,base+0x211540);put<uintptr_t>(base+0x129FD10+0x80,base+0x209A00);
    put<uintptr_t>(base+0x129FD10+0x90,base+0x20C2E0);
    put<uint16_t>(ref<uintptr_t>(root+0xDCA0+12*8)+0x10,666);
    put<uint8_t>(ref<uintptr_t>(root+0xDE40+9*8)+0x10,12);
    put<uintptr_t>(root+0xC8,base+0x123F3F8);put<uintptr_t>(root+0xD0,uintptr_t(&mainHandle));
    mainNode={district,0,0};heads[3]=tails[3]=uintptr_t(&mainNode);counts[3]=1;
    put<uintptr_t>(root+0x78,base+0x123F3B8);put<uintptr_t>(root+0x80,uintptr_t(&cityHandle));
    cityNode={city,0,0};heads[4]=tails[4]=uintptr_t(&cityNode);counts[4]=1;
    put<uint64_t>(np+0x30,5);put<uint64_t>(hp+0x30,6);
    auto dll=LoadLibraryW''')
start=s.index('    auto query=reinterpret_cast');end=s.index('    auto thread=CreateThread',start)
s=s[:start]+'''    auto execution=reinterpret_cast<RewardExecutionData*>(GetProcAddress(dll,"RewardExecutionReport"));
    if(!install || !cancel || !report || !execution)return 5;
    RewardProbeConfig config{REWARD_PROBE_MAGIC,1,test==L"dry"?0U:1U,base,uintptr_t(&ctor),uintptr_t(&add),uintptr_t(&dtor),uintptr_t(&predicate),uintptr_t(&submit)};
    if(test==L"bad-config")config.version=2;
    auto code=install(&config),duplicate=install(&config);
    if(test==L"unknown-task")put<uintptr_t>(action,base+0x129F6C8);
    if(test==L"virtual-target")put<uintptr_t>(base+0x129FD10+0x80,base+0x58E520);
    if(test==L"gold-drift")put<uint32_t>(city+0x34,83208);
    if(test==L"foreign-owner")put<uint8_t>(ref<uintptr_t>(root+0xDE40+9*8)+0x10,10);
    if(test==L"scope-drift")mainNode.value=ref<uintptr_t>(root+0xDE40+9*8);
    if(test==L"funding-drift")put<uint16_t>(city+0x4E,20);
    if(test==L"cancel")cancel(nullptr);
'''+s[end:]
start=s.index('    LONG status=5,error=0;');s=s[:start]+'''    LONG status=5,error=0;unsigned wantCalls=6,wantSubmit=0,wantCtor=1,wantAppend=3,wantDtor=1;
    if(test==L"dry")status=3;
    else if(test==L"execute"){status=4;wantSubmit=1;}
    else if(test==L"submit-exception"){status=6;wantSubmit=1;}
    else if(test==L"submit-rejected"){error=73;wantSubmit=1;}
    else if(test==L"unexpected-effect"){error=74;wantSubmit=1;}
    else if(test==L"eligibility-drift"){error=68;wantCalls=5;}
    else if(test==L"precommit-gold-drift"){error=13;wantCalls=3;}
    else if(test==L"ctor-failure"){error=41;wantCalls=3;wantAppend=0;}
    else if(test==L"append-failure"){error=44;wantCalls=3;wantAppend=2;}
    else if(test==L"append-exception"){status=6;wantCalls=3;wantAppend=2;}
    else if(test==L"wrong-id"){error=47;wantCalls=3;}
    else if(test==L"wrong-count"){error=45;wantCalls=3;}
    else if(test==L"cycle"){error=48;wantCalls=3;}
    else if(test==L"cleanup-leak"){error=49;wantSubmit=1;}
    else {
        wantCalls=wantCtor=wantAppend=wantDtor=0;
        if(test==L"eligibility-denied"){error=68;wantCalls=2;}
        else if(test==L"query-exception"){status=6;wantCalls=2;}
        else if(test==L"unknown-task")error=62;
        else if(test==L"virtual-target")error=65;
        else if(test==L"foreign-owner")error=14;
        else if(test==L"scope-drift")error=66;
        else if(test==L"funding-drift")error=12;
        else if(test==L"gold-drift")error=13;
        else if(test==L"cancel")status=7;
        else if(test==L"bad-config")error=30;
        else return 7;
    }
    bool passed=report->status==status && report->error==error && calls==wantCalls &&
        execution->predicateCalls==calls && submits==wantSubmit && execution->submitCalls==submits &&
        constructs==wantCtor && appends==wantAppend && destructs==wantDtor && updates==11 && argsOk &&
        *hookSlot==&original && !report->activeCallbacks && duplicate==1001 && (test==L"bad-config"?code==30:code==0);
    if(constructs && test!=L"cleanup-leak")passed=passed && ref<uint64_t>(np+0x30)==5 && ref<uint64_t>(hp+0x30)==6;
    if(test==L"execute")passed=passed && execution->postconditions && execution->submitReturned && execution->submitResult==1;
    printf("{\\"case\\":\\"%ls\\",\\"passed\\":%s,\\"status\\":%ld,\\"error\\":%ld,\\"predicate_calls\\":%u,\\"submit_calls\\":%u,\\"constructs\\":%u,\\"appends\\":%u,\\"destructs\\":%u,\\"original_updates\\":%u}\\n",
        test.c_str(),passed?"true":"false",report->status,report->error,calls,submits,constructs,appends,destructs,updates);
    return passed?0:1;
}
'''
(ROOT/'reward_execution_fixture.cpp').write_text(s)
