#define CHECKPOINT_LOAD_MODE_FIXTURE
#include "checkpoint_load_mode_pilot.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <stdexcept>
using Export=DWORD(WINAPI*)(void*);
using Update=uint64_t(__fastcall*)(void*,uintptr_t,uintptr_t,uintptr_t);
static uintptr_t b,user,menu,manager,stack,pending,cache,list;
static Export installFn,stopFn,getFn;
static std::wstring scenario;
static unsigned failures=0,userCalls=0,menuCalls=0,queueCalls=0,cancelCalls=0;
static constexpr uint64_t USER_RAX=0xFEDCBA9876543210ull,MENU_RAX=0xABCDEF9876543210ull;
template<class T> static T& at(uintptr_t p){return *reinterpret_cast<T*>(p);}
static void check(bool ok,const char* what){if(!ok){++failures;printf("FAIL %s\n",what);}}
static void setPop(unsigned n=1){for(unsigned i=0;i<n;++i){at<DWORD>(pending+i*16)=1;at<uintptr_t>(pending+i*16+8)=0;}at<uint64_t>(manager+0x30)=n;}
static uint64_t __fastcall originalUser(void* self,uintptr_t a,uintptr_t c,uintptr_t d){
    ++userCalls;check(uintptr_t(self)==user,"User self exact");check(a==11&&c==22&&d==33,"four register args User");
    if(scenario==L"user-original-seh")RaiseException(0xE0143001,0,0,nullptr);
    if(scenario==L"user-original-cpp")throw std::runtime_error("native User fixture C++");
    if(scenario==L"stop-during-user")stopFn(nullptr);
    if(scenario==L"user-after-drift")at<DWORD>(user+0x470)=3;
    return USER_RAX;
}
static uint64_t __fastcall originalMenu(void* self,uintptr_t a,uintptr_t c,uintptr_t d){
    ++menuCalls;check(uintptr_t(self)==menu,"menu self exact");check(a==11&&c==22&&d==33,"four register args menu");
    check(at<void*>(b+0x12DB4C0+0x28)==reinterpret_cast<void*>(&originalMenu),"menu VT restored BEFORE original");
    if(scenario==L"menu-original-seh")RaiseException(0xE0143002,0,0,nullptr);
    if(scenario==L"menu-original-cpp")throw std::runtime_error("native menu fixture C++");
    if(scenario==L"menu-after-selection")at<int32_t>(list+0x170)=34;
    if(scenario==L"menu-load-pending")at<int32_t>(cache+0x3EC)=34;
    if(scenario==L"native-cancel")setPop();
    if(scenario==L"native-double-cancel")setPop(2);
    if(scenario==L"stop-during-menu")stopFn(nullptr);
    return MENU_RAX;
}
static void __fastcall queue(void* m,const char* name,void* args,void* callback){
    ++queueCalls;check(uintptr_t(m)==manager&&!strcmp(name,"CSaveLoadState"),"native queue arguments");
    check(at<uint64_t>(uintptr_t(args))==0,"mode0 secondary0 params");
    for(unsigned i=0;i<64;++i)check(at<unsigned char>(uintptr_t(callback)+i)==0,"empty callback");
    if(scenario==L"queue-seh")RaiseException(0xE0143003,0,0,nullptr);
    at<DWORD>(cache+8)=0;
    at<uintptr_t>(menu)=b+0x12DB4C0;strcpy_s(reinterpret_cast<char*>(menu+0x70),32,"CSaveLoadState");
    at<uint64_t>(manager+0x30)=1;at<uint64_t>(manager+0x38)=64;at<uintptr_t>(manager+0x40)=pending;
    at<DWORD>(pending)=scenario==L"queue-wrong-kind"?2:0;
    at<uintptr_t>(pending+8)=scenario==L"queue-wrong-state"?user:menu;
    if(scenario==L"stop-during-queue")stopFn(nullptr);
}
static uint64_t __fastcall cancel(void* self){
    ++cancelCalls;check(uintptr_t(self)==menu,"cancel self");check(at<uint64_t>(manager+0x30)==0,"cancel requires empty queue");
    if(scenario==L"cancel-seh")RaiseException(0xE0143004,0,0,nullptr);
    setPop();if(scenario==L"cancel-wrong-kind")at<DWORD>(pending)=2;
    if(scenario==L"stop-during-cancel")stopFn(nullptr);
    return 0x9988776655443322ull;
}
static void setup(){
    b=uintptr_t(VirtualAlloc(nullptr,0x2400000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
    if(!b)ExitProcess(10);
    manager=b+0x19E7310;stack=b+0x2200000;pending=b+0x2201000;user=b+0x220A000;menu=b+0x2210000;
    cache=b+0x2310000;list=b+0x2315000;auto root=b+0x2100000,world=b+0x21F0000;
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    for(unsigned i=0;i<5;++i){auto p=i==4?user:b+0x2202000+i*0x1000;at<uintptr_t>(stack+i*8)=p;strcpy_s(reinterpret_cast<char*>(p+0x70),32,names[i]);}
    at<uint64_t>(manager+0x10)=5;at<uintptr_t>(manager+0x20)=stack;at<uint64_t>(manager+0x18)=64;
    at<uint64_t>(manager+0x38)=scenario==L"capacity-zero"?0:64;at<uintptr_t>(manager+0x40)=scenario==L"capacity-zero"?0:pending;
    auto allocator=b+0x220C000;at<uintptr_t>(allocator)=b+0x1283498;at<uintptr_t>(manager)=at<uintptr_t>(manager+0x28)=allocator;
    at<uintptr_t>(b+0x1283498+0x28)=b+0x12C840;at<uintptr_t>(b+0x1283498+0x38)=b+0x12C290;
    at<uintptr_t>(b+0x1283498+0x40)=b+0x8388D0;at<uintptr_t>(b+0x1283498+0x48)=b+0x1479B0;
    at<uintptr_t>(user)=b+0x12CC4A8;at<DWORD>(user+0x470)=2;at<uintptr_t>(user+0x618)=b+0x220E000;
    auto toolbar=b+0x220D000,panel=b+0x220E000;at<uintptr_t>(user+0x478)=toolbar;at<int32_t>(toolbar+0x88)=-1;
    at<uintptr_t>(at<uintptr_t>(stack+16)+0x480)=panel;at<DWORD>(b+0x19E7510+0x13C)=1;
    at<uintptr_t>(b+0x1FCA1E0)=root;at<uintptr_t>(root)=b+0x12AA6B0;at<uintptr_t>(root+0x85130)=world;at<uintptr_t>(world)=b+0x12AA638;
    at<uint16_t>(world+0x34)=203;at<uint8_t>(world+0x36)=8;at<uint8_t>(world+0x37)=11;at<uint8_t>(world+0x3A)=12;at<DWORD>(world+0x40)=1;
    at<DWORD>(b+0x18EB8B0)=0x12345678;at<uintptr_t>(b+0x2025318)=cache;at<DWORD>(cache+8)=1;at<int32_t>(cache+0x3EC)=-1;
    for(unsigned i=0;i<5;++i){auto owner=cache+(i?0x400+(i-1)*16:0x10),head=cache+0x1000+i*0x100;
        at<uintptr_t>(owner)=head;at<uintptr_t>(head)=at<uintptr_t>(head+8)=head;}
    // Legitimate old grouped node, not currently indexed by the table.
    auto head=at<uintptr_t>(cache+0x400),node=b+0x2320000;
    at<uintptr_t>(head)=at<uintptr_t>(head+8)=node;at<uintptr_t>(node)=at<uintptr_t>(node+8)=head;at<uint64_t>(cache+0x408)=1;
    auto force=b+0x2300000,person=force+0x400,city=force+0x800,district=force+0xC00;
    at<uintptr_t>(root+0xDCA0+12*8)=force;at<uintptr_t>(root+0x148+666*8)=person;at<uintptr_t>(root+0xDAA8+19*8)=city;at<uintptr_t>(root+0xDE40+11*8)=district;
    at<uint16_t>(force+0x10)=666;at<uint16_t>(person+0x10)=666;at<uint8_t>(person+0x118)=11;at<uint16_t>(person+0x11A)=19;
    at<uint16_t>(city+0x10)=19;at<uint8_t>(city+0x30)=11;at<DWORD>(city+0x3C)=15204;at<uint8_t>(district+0x10)=12;at<uint8_t>(district+0x14)=18;
    at<int32_t>(b+0x201ED10)=-1;at<uint64_t>(b+0x201ED18+24)=15;at<uint64_t>(b+0x201ED38+24)=15;
    strcpy_s(reinterpret_cast<char*>(b+0x12DD6E0),32,"CSaveLoadState");
    at<void*>(b+0x12CC4A8+0x28)=reinterpret_cast<void*>(&originalUser);at<void*>(b+0x12DB4C0+0x28)=reinterpret_cast<void*>(&originalMenu);
    DWORD old=0;VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READONLY,&old);VirtualProtect(reinterpret_cast<void*>(b+0x12DB000),4096,PAGE_READONLY,&old);
}
static CheckpointLoadModeReport snapshot(){CheckpointLoadModeReport r;check(getFn(&r)==0,"GetReport");return r;}
static void applyPush(){
    at<uintptr_t>(stack+40)=menu;at<uint64_t>(manager+0x10)=6;at<uint64_t>(manager+0x30)=0;
    at<uintptr_t>(menu+0x470)=list;at<uintptr_t>(menu+0x478)=list+0x1000;at<uintptr_t>(list)=b+0x12DBA18;at<int32_t>(list+0x170)=-1;
    at<DWORD>(b+0x1A38EC8+0x28)=1;at<DWORD>(b+0x19E7510+0x13C)=0;
    at<uintptr_t>(cache+0x20)=b+0x2320010; // valid group-owned index after synthetic UI initialization
}
static void applyPop(){at<uint64_t>(manager+0x10)=5;at<uint64_t>(manager+0x30)=0;at<DWORD>(b+0x1A38EC8+0x28)=0;at<DWORD>(b+0x19E7510+0x13C)=1;}
static void invoke(void* p,uintptr_t self,uint64_t value){check(reinterpret_cast<Update>(p)(reinterpret_cast<void*>(self),11,22,33)==value,"native full RAX retained");}
static void invokeSeh(void* p,uintptr_t self,uint64_t value){bool caught=false;__try{invoke(p,self,value);}__except(EXCEPTION_EXECUTE_HANDLER){caught=true;}check(caught,"original SEH propagated");}
static DWORD WINAPI invokeMenuThread(void* p){invoke(p,menu,MENU_RAX);return 0;}
static DWORD WINAPI invokeUserThread(void* p){invoke(p,user,USER_RAX);return 0;}
int wmain(int argc,wchar_t** argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    if(argc!=3)return 2;scenario=argv[1];setup();
    auto dll=LoadLibraryW(L"checkpoint_load_mode_fixture.dll");if(!dll)return 3;
    installFn=reinterpret_cast<Export>(GetProcAddress(dll,"InstallCheckpointLoadMode"));stopFn=reinterpret_cast<Export>(GetProcAddress(dll,"StopCheckpointLoadMode"));getFn=reinterpret_cast<Export>(GetProcAddress(dll,"GetCheckpointLoadModeReport"));
    CheckpointLoadModeConfig c;c.execute=scenario==L"dry"?0:1;c.expectedPid=GetCurrentProcessId();c.expectedBase=b;c.expectedUser=user;
    FILETIME born{},ex{},ke{},us{};GetProcessTimes(GetCurrentProcess(),&born,&ex,&ke,&us);c.expectedProcessBirth=(uint64_t(born.dwHighDateTime)<<32)|born.dwLowDateTime;
    wcsncpy_s(c.intentPath,argv[2],_TRUNCATE);c.testQueue=uintptr_t(&queue);c.testCancel=uintptr_t(&cancel);
    if(scenario==L"initial-mode")at<DWORD>(cache+8)=0;
    if(scenario==L"initial-pending")at<int32_t>(cache+0x3EC)=34;
    if(scenario==L"initial-selection")at<uintptr_t>(user+0x4A8)=user;
    if(scenario==L"initial-foreign-table")at<uintptr_t>(cache+0x20)=b+0x2330000;
    if(scenario==L"initial-group-cycle")at<uintptr_t>(b+0x2320000)=b+0x2320000;
    if(scenario==L"initial-group-count")at<uint64_t>(cache+0x408)=121;
    if(scenario==L"initial-head-node-overlap"){
        auto head=b+0x2320020;at<uintptr_t>(cache+0x410)=head;at<uintptr_t>(head)=at<uintptr_t>(head+8)=head;
    }
    if(scenario==L"initial-node-node-overlap"){
        auto head=at<uintptr_t>(cache+0x410),node=b+0x2320100;
        at<uintptr_t>(head)=at<uintptr_t>(head+8)=node;at<uintptr_t>(node)=at<uintptr_t>(node+8)=head;at<uint64_t>(cache+0x418)=1;
    }
    if(scenario==L"initial-head-head-overlap"){
        auto head=at<uintptr_t>(cache+0x410);at<uintptr_t>(cache+0x420)=head;
    }
    if(scenario==L"existing-journal"){auto f=CreateFileW(c.intentPath,GENERIC_WRITE,0,nullptr,CREATE_NEW,0,nullptr);check(f!=INVALID_HANDLE_VALUE,"preexisting journal fixture");if(f!=INVALID_HANDLE_VALUE)CloseHandle(f);}
    DWORD result=installFn(&c);bool initialReject=scenario.rfind(L"initial-",0)==0;
    if(initialReject){check(result!=0,"bad initial guard rejected");check(queueCalls==0,"no queue on initial reject");}
    else {
        check(result==0,"Install");auto first=at<void*>(b+0x12CC4A8+0x28);
        if(scenario==L"report-lock-seh"){
            auto fault=reinterpret_cast<Export>(GetProcAddress(dll,"CheckpointLoadModeFixtureReportFault"));
            check(fault&&fault(nullptr)==0,"SEH releases REPORT lock and permits subsequent REPORT");
            check(snapshot().exceptionCode==0xE0143005,"report available after locked SEH");
            stopFn(nullptr);
        }
        if(scenario==L"stop-before-user")stopFn(nullptr);
        if(scenario==L"user-original-seh")invokeSeh(first,user,USER_RAX);
        else if(scenario==L"user-original-cpp"){bool caught=false;try{invoke(first,user,USER_RAX);}catch(const std::exception&){caught=true;}check(caught,"User C++ propagates");}
        else invoke(first,user,USER_RAX);
        auto r=snapshot();
        if(r.state==LM_QUEUED){
            applyPush();auto entry=at<void*>(b+0x12DB4C0+0x28);
            if(scenario==L"menu-before-selection")at<int32_t>(list+0x170)=34;
            if(scenario==L"menu-wrong-top")at<uintptr_t>(stack+40)=user;
            if(scenario==L"menu-table-alias")at<uintptr_t>(cache+0x28)=at<uintptr_t>(cache+0x20);
            if(scenario==L"menu-original-seh")invokeSeh(entry,menu,MENU_RAX);
            else if(scenario==L"menu-original-cpp"){bool caught=false;try{invoke(entry,menu,MENU_RAX);}catch(const std::exception&){caught=true;}check(caught,"menu C++ propagates");}
            else if(scenario==L"menu-worker-migration"||scenario==L"both-worker-migration"){
                auto t=CreateThread(nullptr,0,invokeMenuThread,entry,0,nullptr);check(WaitForSingleObject(t,5000)==WAIT_OBJECT_0,"other menu worker complete");CloseHandle(t);
            }
            else invoke(entry,menu,MENU_RAX);
            if(scenario==L"duplicate-menu")invoke(entry,menu,MENU_RAX);
            r=snapshot();
            if(r.state==LM_CANCEL_QUEUED){
                applyPop();if(scenario==L"return-rng-drift")at<DWORD>(b+0x18EB8B0)^=1;
                auto entryUser=at<void*>(b+0x12CC4A8+0x28);
                if(scenario==L"return-worker-migration"||scenario==L"both-worker-migration"){
                    auto t=CreateThread(nullptr,0,invokeUserThread,entryUser,0,nullptr);check(WaitForSingleObject(t,5000)==WAIT_OBJECT_0,"other return worker complete");CloseHandle(t);
                }else invoke(entryUser,user,USER_RAX);
            }
        }
    }
    auto beforeStop=snapshot();const bool success=scenario==L"execute"||scenario==L"capacity-zero"||
        scenario==L"menu-worker-migration"||scenario==L"return-worker-migration"||scenario==L"both-worker-migration";
    if(success){check(beforeStop.state==LM_USER_RETURNED,"same User success");check(beforeStop.queueCalls==1&&beforeStop.cancelCalls==1,"once native operations");check(beforeStop.menuGuardBefore&&beforeStop.menuGuardAfter&&beforeStop.returnMatched,"guards complete");}
    else if(scenario==L"dry"){check(beforeStop.state==LM_DRY_DONE,"dry success");check(!queueCalls&&!cancelCalls&&!beforeStop.intentCreated,"dry no operation");}
    else check(beforeStop.state!=LM_USER_RETURNED,"negative case never PASS");
    if(scenario==L"native-cancel")check(beforeStop.nativeCancellationSeen==1&&cancelCalls==0&&at<uint64_t>(manager+0x30)==1,"native cancel never double queued");
    if(scenario==L"native-double-cancel")check(cancelCalls==0&&at<uint64_t>(manager+0x30)==2,"unknown queue never appended");
    if(scenario.rfind(L"menu-",0)==0&&!success&&scenario!=L"menu-original-seh"&&scenario!=L"menu-original-cpp")check(cancelCalls==0,"bad menu guard no cancel");
    if(scenario==L"stop-during-queue"||scenario==L"stop-during-cancel")check(beforeStop.state==LM_UNCERTAIN&&beforeStop.stopRequested,"Stop inside native operation remains UNCERTAIN");
    if(scenario==L"return-rng-drift")check(beforeStop.state==LM_UNCERTAIN&&beforeStop.error==77,"return drift explicitly refuses and cleans up");
    if(scenario==L"menu-worker-migration"||scenario==L"both-worker-migration")check(beforeStop.queueThread!=beforeStop.menuThread,"menu migration actually exercised");
    if(scenario==L"return-worker-migration"||scenario==L"both-worker-migration")check(beforeStop.queueThread!=beforeStop.returnThread,"return migration actually exercised");
    check(stopFn(nullptr)==0,"Stop cleanup");auto r=snapshot();
    check(r.callbackActive==0&&r.userBridge.active==0&&r.menuBridge.active==0,"callbacks drained");
    check(at<void*>(b+0x12CC4A8+0x28)==reinterpret_cast<void*>(&originalUser)&&at<void*>(b+0x12DB4C0+0x28)==reinterpret_cast<void*>(&originalMenu),"VT slots restored");
    MEMORY_BASIC_INFORMATION um{},mm{};VirtualQuery(reinterpret_cast<void*>(b+0x12CC4A8+0x28),&um,sizeof um);VirtualQuery(reinterpret_cast<void*>(b+0x12DB4C0+0x28),&mm,sizeof mm);
    check(um.Protect==PAGE_READONLY&&mm.Protect==PAGE_READONLY,"page protections restored");
    check(!r.nativeLoadAuthorized&&!r.customMetadataWrites&&!r.fullWorldVerified,"scope counters zero");
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"state_before_stop\":%ld,\"error\":%ld,\"queue_calls\":%u,\"cancel_calls\":%u,\"user_native_calls\":%u,\"menu_native_calls\":%u,\"callback_active\":%u,\"fixture_config_bytes\":%zu,\"report_bytes\":%zu,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,beforeStop.state,beforeStop.error,queueCalls,cancelCalls,userCalls,menuCalls,r.callbackActive,sizeof c,sizeof r);
    return failures?1:0;
}
