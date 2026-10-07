#define PILOT_FIXTURE
#include "autonomous_pilot.h"
#include <cstdio>
#include <cstring>
#include <string>

static uintptr_t fakeBase=0,root=0,city=0,person=0,district=0,state=0;
static unsigned originalCount=0, submitCount=0;
static bool argsOk=true;
template<class T> static void put(uintptr_t a,T v) { *reinterpret_cast<T*>(a)=v; }
static void __fastcall original(void* self,uintptr_t a2,uintptr_t a3,uintptr_t a4) {
    originalCount++;
    if(uintptr_t(self)!=state || a2!=0x112233 || a3!=0x445566 || a4!=0x778899) argsOk=false;
}
static uintptr_t __fastcall submit(const uint32_t* w,uint32_t flags) {
    submitCount++;
    if(flags!=1 || memcmp(w,RECORDED_COMMAND,104)) argsOk=false;
    put<uint32_t>(city+0x3C,13904); put<uint8_t>(district+0x14,17);
    auto unit=root+0x90000+29*0x200;
    put<uint8_t>(unit+0x10,1); put<uint16_t>(unit+0x12,666);
    put<uint16_t>(unit+0x16,1300); put<uint8_t>(unit+0x1B,4); put<uint8_t>(unit+0x1C,11);
    put<uint8_t>(unit+0x38,5); put<uint16_t>(unit+0x3A,20);
    return unit;
}
static DWORD WINAPI tick(void*) {
    for(int i=0;i<11;i++) {
        auto vtable=*reinterpret_cast<uintptr_t*>(state);
        auto function=*reinterpret_cast<UpdateFunction*>(vtable+0x28);
        function(reinterpret_cast<void*>(state),0x112233,0x445566,0x778899);
    }
    return 0;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=3) return 2;
    std::wstring test=argv[2];
    fakeBase=reinterpret_cast<uintptr_t>(VirtualAlloc(nullptr,0x2100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    root=reinterpret_cast<uintptr_t>(VirtualAlloc(nullptr,0x100000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!fakeBase || !root) return 3;
    city=root+0x88000; person=root+0x89000; district=root+0x8A000; state=fakeBase+0x200000;
    auto world=root+0x87000;
    put<uintptr_t>(fakeBase+0x1FCA1E0,root); put<uintptr_t>(root+0x85130,world);
    put<uint16_t>(world+0x34,203); put<uint8_t>(world+0x36,8); put<uint8_t>(world+0x37,11); put<uint8_t>(world+0x3A,12);
    put<uintptr_t>(root+0xDAA8+19*8,city); put<uintptr_t>(root+0x148+666*8,person);
    put<uintptr_t>(root+0xDE40+12*8,district);
    put<uint16_t>(city+0x10,19); put<uint8_t>(city+0x30,12); put<uint32_t>(city+0x3C,15204); put<uint16_t>(city+0x4E,19);
    put<uint16_t>(person+0x10,666); put<uint8_t>(person+0x118,12); put<uint16_t>(person+0x11A,19);
    put<uint8_t>(district+0x10,12); put<uint8_t>(district+0x14,18);
    for(int i=0;i<=500;i++) {
        auto unit=root+0x90000+i*0x200;
        put<uintptr_t>(root+0x7DF60+i*8,unit);
        if(i>0 && i<=57 && i!=29) { put<uint8_t>(unit+0x10,1); put<uint16_t>(unit+0x12,static_cast<uint16_t>(i+100)); }
    }
    auto stack=fakeBase+0x210000;
    put<uint64_t>(fakeBase+0x19E7310+0x10,5); put<uintptr_t>(fakeBase+0x19E7310+0x20,stack); put<uintptr_t>(stack+32,state);
    put<uintptr_t>(state,fakeBase+0x12CC4A8); put<uint32_t>(state+0x470,2);
    auto slot=reinterpret_cast<UpdateFunction*>(fakeBase+0x12CC4A8+0x28); *slot=&original;
    HMODULE dll=LoadLibraryW(argv[1]); if(!dll) return 4;
    auto install=reinterpret_cast<InstallFunction>(GetProcAddress(dll,"InstallPilot"));
    auto cancel=reinterpret_cast<InstallFunction>(GetProcAddress(dll,"CancelPilot"));
    auto report=reinterpret_cast<PilotReportData*>(GetProcAddress(dll,"PilotReport"));
    if(!install || !cancel || !report) return 5;
    PilotConfig input{PILOT_MAGIC,1,test==L"dry"?0U:1U};
    memcpy(input.words,RECORDED_COMMAND,104); input.testBase=fakeBase; input.testSubmit=reinterpret_cast<uintptr_t>(&submit);
    if(test==L"wrong-command") input.words[2]=999;
    DWORD installedResult=install(&input);
    DWORD duplicateResult=install(&input);
    if(test==L"resource-drift") put<uint32_t>(city+0x3C,15000);
    if(test==L"wrong-owner") put<uint8_t>(district+0x10,11);
    if(test==L"cancel") cancel(nullptr);
    HANDLE thread=CreateThread(nullptr,0,tick,nullptr,0,nullptr);
    if(!thread || WaitForSingleObject(thread,10000)!=WAIT_OBJECT_0) return 6;
    CloseHandle(thread);
    bool shouldExecute=test==L"execute";
    LONG status=shouldExecute?4:(test==L"dry"?3:(test==L"cancel"?7:5));
    bool passed=(report->status==status && submitCount==(shouldExecute?1U:0U) && originalCount==11 && argsOk &&
                 *slot==&original && report->activeCallbacks==0 && duplicateResult==1001 &&
                 (test==L"wrong-command"?installedResult==30:installedResult==0));
    if(test==L"execute" || test==L"dry") passed=passed && report->installerThread!=report->executorThread;
    printf("{\"case\":\"%ls\",\"passed\":%s,\"status\":%ld,\"error\":%ld,\"original_calls\":%u,\"submit_calls\":%u,\"arguments_preserved\":%s,\"slot_restored\":%s,\"no_active_callback\":%s,\"duplicate_install_rejected\":%s}\n",
           test.c_str(),passed?"true":"false",report->status,report->error,originalCount,submitCount,argsOk?"true":"false",
           *slot==&original?"true":"false",report->activeCallbacks==0?"true":"false",duplicateResult==1001?"true":"false");
    // Deliberately keep the DLL loaded until process exit; no unload/callback race.
    return passed?0:1;
}
