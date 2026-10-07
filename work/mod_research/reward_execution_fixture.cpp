#define REWARD_FIXTURE
#include "reward_execution_pilot.h"
#include <cstdio>
#include <string>

static uintptr_t base=0,root=0,state=0,city=0,district=0;
static unsigned updates=0,calls=0,submits=0,appends=0,constructs=0,destructs=0;static bool argsOk=true;
static std::wstring test;
struct Node { uintptr_t value,next,previous; };
static Node personNodes[3]{},taskNode{},mainNode{},cityNode{};
static uint64_t mainHandle=3,cityHandle=4;
static uint64_t heads[0x14000]{},tails[0x14000]{},counts[0x14000]{},personHandle=1,taskHandle=2;
template<class T> static void put(uintptr_t a,T v) { *reinterpret_cast<T*>(a)=v; }
static void __fastcall original(void* self,uintptr_t a,uintptr_t b,uintptr_t c) {
    updates++;if(uintptr_t(self)!=state || a!=1 || b!=2 || c!=3) argsOk=false;
}
template<class T> static T& ref(uintptr_t p) { return *reinterpret_cast<T*>(p); }
static Node nodes[3]{};static uint64_t handle=7;
static RewardArgs* __fastcall ctor(RewardArgs* args) {
    constructs++;
    args->vtable=base+0x123E210; args->handle=0; args->funding=0;
    if(test==L"ctor-failure") return args;
    args->handle=uintptr_t(&handle);
    ref<uint64_t>(base+HANDLE_POOL_RVA+0x30)++;
    return args;
}
static uintptr_t __fastcall add(uintptr_t pool,uint32_t slot,uint8_t atEnd) {
    appends++;
    if(pool!=base+NODE_POOL_RVA || slot!=7 || atEnd!=1) argsOk=false;
    if(test==L"append-failure" && appends==2) return 0;
    if(test==L"append-exception" && appends==2) RaiseException(0xE0000014,0,0,nullptr);
    auto node=uintptr_t(&nodes[appends-1]);
    if(test==L"wrong-order") {
        nodes[appends-1].next=heads[slot];
        if(heads[slot]) ref<uint64_t>(heads[slot]+16)=node;
        else tails[slot]=node;
        heads[slot]=node;
    } else {
        nodes[appends-1].previous=tails[slot];
        if(tails[slot]) ref<uint64_t>(tails[slot]+8)=node;
        else heads[slot]=node;
        tails[slot]=node;
    }
    counts[slot]++; ref<uint64_t>(pool+0x30)++;
    if(test==L"wrong-count" && appends==3) counts[slot]++;
    if(test==L"cycle" && appends==3) nodes[2].next=heads[slot];
    if(test==L"precommit-gold-drift" && appends==3) ref<uint32_t>(city+0x34)=83208;
    if(test==L"wrong-id" && appends==3) nodes[0].value=98;
    return node;
}
static void __fastcall dtor(RewardArgs* args) {
    destructs++;
    if(!args->handle) return;
    if(test==L"cleanup-leak") return;
    heads[7]=tails[7]=counts[7]=0;
    ref<uint64_t>(base+NODE_POOL_RVA+0x30)=5;
    ref<uint64_t>(base+HANDLE_POOL_RVA+0x30)=6;
    args->handle=0;
}
static int __fastcall predicate(uintptr_t person) {
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
static DWORD WINAPI tick(void*) {
    for(unsigned i=0;i<11;i++) {
        auto fn=*reinterpret_cast<ProbeUpdate*>(base+PROBE_VTABLE_RVA+0x28);
        fn(reinterpret_cast<void*>(state),1,2,3);
    }
    return 0;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=3)return 2;test=argv[2];
    base=uintptr_t(VirtualAlloc(nullptr,0x2100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    root=uintptr_t(VirtualAlloc(nullptr,0x100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!base || !root)return 3;
    state=base+0x200000;city=root+0x88000;district=root+0x8A000+11*0x40;
    auto world=root+0x87000,ruler=root+0x89000;
    put<uintptr_t>(base+0x1FCA1E0,root);put<uintptr_t>(root+0x85130,world);
    put<uint16_t>(world+0x34,203);put<uint8_t>(world+0x36,8);put<uint8_t>(world+0x37,11);put<uint8_t>(world+0x3A,12);
    for(unsigned i=0;i<52;i++) {
        auto d=root+0x8A000+i*0x40,f=root+0x8B000+i*0x100;
        put<uintptr_t>(root+0xDE40+i*8,d);put<uintptr_t>(d,base+0x129FEC8);
        put<uintptr_t>(root+0xDCA0+i*8,f);put<uintptr_t>(f,base+0x129FE58);
    }
    for(unsigned i=0;i<=500;i++) {
        auto unit=root+0xA0000+i*0x200;
        put<uintptr_t>(root+0x7DF60+i*8,unit);put<uintptr_t>(unit,base+0x123E288);
    }
    put<uintptr_t>(base+0x129FEC8+0x18,base+0x211610);put<uintptr_t>(base+0x129FE58+0x60,base+0x20B610);
    put<uintptr_t>(base+0x123E288+0x18,base+0x211420);put<uintptr_t>(base+0x12A00D0+0x18,base+0x2119F0);
    put<uintptr_t>(root+0xDAA8+19*8,city);put<uintptr_t>(root+0x148+666*8,ruler);
    put<uint16_t>(city+0x10,19);put<uint8_t>(city+0x30,11);put<uint16_t>(city+0x4E,19);
    put<uint32_t>(city+0x34,83308);put<uint32_t>(city+0x3C,15204);
    put<uint16_t>(ruler+0x10,666);put<uint16_t>(ruler+0x11A,19);
    put<uint8_t>(district+0x10,12);put<uint16_t>(district+0x12,666);put<uint8_t>(district+0x14,18);
    for(unsigned i=0;i<3;i++) {
        auto person=root+0x90000+i*0x200;
        put<uintptr_t>(root+0x148+PROBE_IDS[i]*8,person);put<uintptr_t>(person,base+0x12A00D0);
        put<uint16_t>(person+0x10,static_cast<uint16_t>(PROBE_IDS[i]));put<uint8_t>(person+0x118,9);put<uint8_t>(person+0x11E,4);
        put<uint8_t>(person+0x120,PROBE_LOYALTY[i]);put<uint16_t>(person+0x196,128);
        personNodes[i]={person,i<2?uintptr_t(&personNodes[i+1]):0,i?uintptr_t(&personNodes[i-1]):0};
    }
    auto stack=base+0x210000;
    put<uint64_t>(base+0x19E7310+0x10,5);put<uintptr_t>(base+0x19E7310+0x20,stack);put<uintptr_t>(stack+32,state);
    put<uintptr_t>(state,base+PROBE_VTABLE_RVA);put<uint32_t>(state+0x470,2);
    auto hookSlot=reinterpret_cast<ProbeUpdate*>(base+PROBE_VTABLE_RVA+0x28);*hookSlot=&original;
    // The common installation gate checks integer-pool availability; query mode never allocates from it.
    auto np=base+NODE_POOL_RVA,hp=base+HANDLE_POOL_RVA;
    put<uintptr_t>(np+8,1);put<uintptr_t>(np+0x10,uintptr_t(heads));put<uintptr_t>(np+0x18,uintptr_t(tails));put<uintptr_t>(np+0x28,uintptr_t(counts));
    put<uint64_t>(np+0x38,32768);put<uint32_t>(np+0x40,1024);put<uint64_t>(hp+0x38,1024);
    auto pp=base+0x201D3A0;
    put<uintptr_t>(pp+8,1);put<uintptr_t>(pp+0x10,uintptr_t(heads));put<uintptr_t>(pp+0x18,uintptr_t(tails));put<uintptr_t>(pp+0x28,uintptr_t(counts));put<uint32_t>(pp+0x40,0x14000);
    put<uintptr_t>(root+0xF8,base+0x123F448);put<uintptr_t>(root+0x100,uintptr_t(&personHandle));
    heads[1]=uintptr_t(&personNodes[0]);tails[1]=uintptr_t(&personNodes[2]);counts[1]=3;
    auto manager=root+0x96000,action=root+0x97000;
    put<uintptr_t>(root+0x85128,manager);put<uintptr_t>(manager+0x10,base+0x129BB28);put<uintptr_t>(manager+0x18,uintptr_t(&taskHandle));
    taskNode={action,0,0};heads[2]=tails[2]=uintptr_t(&taskNode);counts[2]=1;
    put<uintptr_t>(action,base+0x129BB48);put<uintptr_t>(action+0x18,base+0x123E210);
    put<uintptr_t>(base+0x129BB48+0x18,base+0x1D4330);put<uintptr_t>(base+0x129BB48+0xB0,base+0x20BA50);
    put<uintptr_t>(city,base+0x129FD10);put<uintptr_t>(ruler,base+0x12A00D0);
    put<uintptr_t>(base+0x129FD10+0x18,base+0x211540);put<uintptr_t>(base+0x129FD10+0x80,base+0x209A00);
    put<uintptr_t>(base+0x129FD10+0x90,base+0x20C2E0);
    put<uint16_t>(ref<uintptr_t>(root+0xDCA0+12*8)+0x10,666);
    put<uint8_t>(ref<uintptr_t>(root+0xDE40+9*8)+0x10,12);
    put<uintptr_t>(root+0xC8,base+0x123F3F8);put<uintptr_t>(root+0xD0,uintptr_t(&mainHandle));
    mainNode={district,0,0};heads[3]=tails[3]=uintptr_t(&mainNode);counts[3]=1;
    put<uintptr_t>(root+0x78,base+0x123F3B8);put<uintptr_t>(root+0x80,uintptr_t(&cityHandle));
    cityNode={city,0,0};heads[4]=tails[4]=uintptr_t(&cityNode);counts[4]=1;
    put<uint64_t>(np+0x30,5);put<uint64_t>(hp+0x30,6);
    auto dll=LoadLibraryW(argv[1]);if(!dll)return 4;
    auto install=reinterpret_cast<ProbeInstall>(GetProcAddress(dll,"InstallRewardProbe"));
    auto cancel=reinterpret_cast<ProbeInstall>(GetProcAddress(dll,"CancelRewardProbe"));
    auto report=reinterpret_cast<RewardProbeReportData*>(GetProcAddress(dll,"RewardProbeReport"));
    auto execution=reinterpret_cast<RewardExecutionData*>(GetProcAddress(dll,"RewardExecutionReport"));
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
    auto thread=CreateThread(nullptr,0,tick,nullptr,0,nullptr);
    if(!thread || WaitForSingleObject(thread,10000)!=WAIT_OBJECT_0)return 6;CloseHandle(thread);
    LONG status=5,error=0;unsigned wantCalls=6,wantSubmit=0,wantCtor=1,wantAppend=3,wantDtor=1;
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
    printf("{\"case\":\"%ls\",\"passed\":%s,\"status\":%ld,\"error\":%ld,\"predicate_calls\":%u,\"submit_calls\":%u,\"constructs\":%u,\"appends\":%u,\"destructs\":%u,\"original_updates\":%u}\n",
        test.c_str(),passed?"true":"false",report->status,report->error,calls,submits,constructs,appends,destructs,updates);
    return passed?0:1;
}
