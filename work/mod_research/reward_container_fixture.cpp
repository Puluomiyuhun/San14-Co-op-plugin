#define REWARD_FIXTURE
#include "reward_container_probe.h"
#include <cstdio>
#include <string>

static uintptr_t base=0,root=0,city=0,district=0,state=0;
static uint64_t heads[REWARD_POOL_SLOTS]{},tails[REWARD_POOL_SLOTS]{},counts[REWARD_POOL_SLOTS]{};
struct Node { uint64_t value,next,previous; };
static Node nodes[3]{};
static uint64_t handle=7;
static unsigned originals=0,appends=0,constructs=0,destructs=0;
static bool argumentsOk=true;
static std::wstring test;
template<class T> static void put(uintptr_t p,T v) { *reinterpret_cast<T*>(p)=v; }
template<class T> static T& ref(uintptr_t p) { return *reinterpret_cast<T*>(p); }
static void __fastcall original(void* self,uintptr_t a,uintptr_t b,uintptr_t c) {
    originals++;
    if(uintptr_t(self)!=state || a!=0x112233 || b!=0x445566 || c!=0x778899) argumentsOk=false;
}
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
    if(pool!=base+NODE_POOL_RVA || slot!=7 || atEnd!=1) argumentsOk=false;
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
static DWORD WINAPI tick(void*) {
    for(unsigned i=0;i<11;i++) {
        auto update=ref<ProbeUpdate>(base+PROBE_VTABLE_RVA+0x28);
        update(reinterpret_cast<void*>(state),0x112233,0x445566,0x778899);
    }
    return 0;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=3) return 2;
    test=argv[2];
    base=uintptr_t(VirtualAlloc(nullptr,0x2100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    root=uintptr_t(VirtualAlloc(nullptr,0x100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!base || !root) return 3;
    city=root+0x88000; district=root+0x89000; state=base+0x200000;
    auto world=root+0x87000,ruler=root+0x8A000;
    put<uintptr_t>(base+0x1FCA1E0,root); put<uintptr_t>(root+0x85130,world);
    put<uint16_t>(world+0x34,203); put<uint8_t>(world+0x36,8); put<uint8_t>(world+0x37,11); put<uint8_t>(world+0x3A,12);
    put<uintptr_t>(root+0xDAA8+19*8,city); put<uintptr_t>(root+0xDE40+11*8,district); put<uintptr_t>(root+0x148+666*8,ruler);
    put<uint16_t>(city+0x10,19); put<uint8_t>(city+0x30,11); put<uint32_t>(city+0x34,83308); put<uint32_t>(city+0x3C,15204);
    put<uint16_t>(city+0x4E,19); put<uint16_t>(ruler+0x10,666); put<uint16_t>(ruler+0x11A,19);
    put<uint8_t>(district+0x10,12); put<uint16_t>(district+0x12,666); put<uint8_t>(district+0x14,18);
    for(unsigned i=0;i<3;i++) {
        auto person=root+0x8B000+i*0x200;
        put<uintptr_t>(root+0x148+PROBE_IDS[i]*8,person);
        put<uint16_t>(person+0x10,static_cast<uint16_t>(PROBE_IDS[i])); put<uint8_t>(person+0x118,11);
        put<uint8_t>(person+0x120,PROBE_LOYALTY[i]); put<uint16_t>(person+0x196,128);
    }
    auto stack=base+0x210000;
    put<uint64_t>(base+0x19E7310+0x10,5); put<uintptr_t>(base+0x19E7310+0x20,stack); put<uintptr_t>(stack+32,state);
    put<uintptr_t>(state,base+PROBE_VTABLE_RVA); put<uint32_t>(state+0x470,2);
    auto slot=reinterpret_cast<ProbeUpdate*>(base+PROBE_VTABLE_RVA+0x28); *slot=&original;
    auto p=base+NODE_POOL_RVA,h=base+HANDLE_POOL_RVA;
    put<uint64_t>(p+8,1); put<uintptr_t>(p+0x10,uintptr_t(heads)); put<uintptr_t>(p+0x18,uintptr_t(tails)); put<uintptr_t>(p+0x28,uintptr_t(counts));
    put<uint64_t>(p+0x30,5); put<uint64_t>(p+0x38,0x8000); put<uint32_t>(p+0x40,REWARD_POOL_SLOTS);
    put<uint64_t>(h+0x30,6); put<uint64_t>(h+0x38,REWARD_POOL_SLOTS);
    auto dll=LoadLibraryW(argv[1]); if(!dll) return 4;
    auto install=reinterpret_cast<ProbeInstall>(GetProcAddress(dll,"InstallRewardProbe"));
    auto cancel=reinterpret_cast<ProbeInstall>(GetProcAddress(dll,"CancelRewardProbe"));
    auto report=reinterpret_cast<RewardProbeReportData*>(GetProcAddress(dll,"RewardProbeReport"));
    if(!install || !cancel || !report) return 5;
    RewardProbeConfig config{REWARD_PROBE_MAGIC,1,0,base,uintptr_t(&ctor),uintptr_t(&add),uintptr_t(&dtor)};
    if(test==L"bad-config") config.version=2;
    if(test==L"wrong-pool-capacity") put<uint32_t>(p+0x40,0x14000);
    auto installCode=install(&config),duplicateCode=install(&config);
    if(test==L"gold-drift") put<uint32_t>(city+0x34,83000);
    if(test==L"owner-drift") put<uint8_t>(district+0x10,11);
    if(test==L"rewarded-drift") put<uint16_t>(root+0x8B000+0x196,130);
    if(test==L"cancel") cancel(nullptr);
    HANDLE thread=CreateThread(nullptr,0,tick,nullptr,0,nullptr);
    if(!thread || WaitForSingleObject(thread,10000)!=WAIT_OBJECT_0) return 6;
    CloseHandle(thread);
    unsigned expectedConstructs=1,expectedAppends=3,expectedDtor=1;
    LONG expectedStatus=5,expectedError=0;
    if(test==L"success") expectedStatus=3;
    else if(test==L"ctor-failure") { expectedError=41; expectedAppends=0; }
    else if(test==L"append-failure") { expectedError=44; expectedAppends=2; }
    else if(test==L"append-exception") { expectedStatus=6; expectedAppends=2; }
    else if(test==L"wrong-count") expectedError=45;
    else if(test==L"wrong-order") expectedError=47;
    else if(test==L"cycle") expectedError=48;
    else if(test==L"cleanup-leak") expectedError=49;
    else {
        expectedConstructs=expectedAppends=expectedDtor=0;
        if(test==L"gold-drift") expectedError=13;
        else if(test==L"owner-drift") expectedError=12;
        else if(test==L"rewarded-drift") expectedError=15;
        else if(test==L"bad-config") expectedError=30;
        else if(test==L"wrong-pool-capacity") expectedError=40;
        else if(test==L"cancel") expectedStatus=7;
        else return 7;
    }
    bool passed=report->status==expectedStatus && report->error==expectedError && constructs==expectedConstructs &&
        appends==expectedAppends && destructs==expectedDtor && originals==11 && argumentsOk && *slot==&original &&
        report->activeCallbacks==0 && duplicateCode==1001 &&
        (test==L"bad-config"?installCode==30:(test==L"wrong-pool-capacity"?installCode==40:installCode==0));
    if(constructs) passed=passed && report->installerThread!=report->executorThread;
    if(constructs && test!=L"cleanup-leak") passed=passed && ref<uint64_t>(p+0x30)==5 && ref<uint64_t>(h+0x30)==6;
    printf("{\"case\":\"%ls\",\"passed\":%s,\"status\":%ld,\"error\":%ld,\"constructs\":%u,\"appends\":%u,\"destructs\":%u,\"original_calls\":%u,\"arguments_preserved\":%s,\"slot_restored\":%s,\"duplicate_install_rejected\":%s}\n",
           test.c_str(),passed?"true":"false",report->status,report->error,constructs,appends,destructs,originals,
           argumentsOk?"true":"false",*slot==&original?"true":"false",duplicateCode==1001?"true":"false");
    return passed?0:1;
}
