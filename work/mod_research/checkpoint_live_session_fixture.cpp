#include "checkpoint_live_session_core.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <cstring>
#include <string>
static unsigned calls=0,failures=0;static bool shouldThrow=false;
extern "C" std::uint64_t CheckpointLiveFixtureOriginal(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" void CheckpointLiveFixtureBody(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){++calls;if(!a||b!=2||c!=3||d!=4)++failures;if(shouldThrow)RaiseException(0xE014A001,0,0,nullptr);}
static void check(bool b,const char* message){if(!b){++failures;printf("FAIL %s\n",message);}}
template<class T>static void put(std::uint64_t p,T v){memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
using Fn=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
static bool invoke(Fn fn,std::uint64_t user){__try{check(fn(user,2,3,4)==0xFEDCBA9876543210ull,"RAX result");return false;}__except(GetExceptionCode()==0xE014A001?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
int wmain(int argc,wchar_t**argv){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=3)return 2;const std::wstring scenario=argv[1];
    checkpoint_load_input_boundary_fixture::Layout layout;check(layout.initialize(),"owned layout");auto b=layout.config.base;
    put<std::uint64_t>(layout.manager+0x10,5);put<std::uint64_t>(layout.manager+0x48,layout.config.states[4]);
    put<std::uint64_t>(layout.config.root,b+0x12AA6B0);put<std::uint64_t>(layout.config.world,b+0x12AA638);
    auto slot=reinterpret_cast<void**>(b+0x12CC4A8+0x28);*slot=reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal);
    CheckpointLiveSessionConfig c{};c.pid=GetCurrentProcessId();FILETIME born{},e{},k{},u{};GetProcessTimes(GetCurrentProcess(),&born,&e,&k,&u);c.birth=(std::uint64_t(born.dwHighDateTime)<<32)|born.dwLowDateTime;
    c.base=b;c.attempt=19;memset(c.attachment,0x73,32);c.root=layout.config.root;c.world=layout.config.world;memcpy(c.states,layout.config.states,sizeof c.states);c.toolbar=layout.toolbar;c.panel=layout.panel;wcscpy_s(c.journal,argv[2]);c.reserved[0]=reinterpret_cast<std::uint64_t>(&CheckpointLiveFixtureOriginal);
    if(scenario==L"bad-birth")++c.birth;
    if(scenario==L"pending")put<LONG>(layout.toolbar+0x88,6);
    if(scenario==L"wrong-thread")c.expectedUserThread=GetCurrentThreadId()+1;
    if(scenario==L"bad-path")wcscpy_s(c.journal,L"C:\\not-authorized\\live.jsonl");
    if(scenario==L"foreign-slot")*slot=reinterpret_cast<void*>(&wmain);
    const auto install=InstallCheckpointLiveSessionObserver(&c);CheckpointLiveSessionReport r{};
    if(scenario==L"bad-birth"||scenario==L"pending"||scenario==L"bad-path"||scenario==L"foreign-slot"){
        check(install!=0,"rejection before hook");check(calls==0,"no native call on reject");
    }else {
        check(install==0,"observer installed");auto cached=reinterpret_cast<Fn>(*slot);
        if(scenario==L"exception")shouldThrow=true;
        const auto thrown=invoke(cached,c.states[4]);shouldThrow=false;check(thrown==(scenario==L"exception"),"original exception propagates");
        GetCheckpointLiveSessionReport(&r);check(r.bridgeStarted==1&&!r.active,"bridge active cleanup");check(!r.queueCalls&&!r.requestCas&&!r.loadRequested&&!r.fullInputHold&&!r.completeSessionInstalled,"observe only");
        if(scenario==L"exception")check(!r.firstPair&&r.bridgeAbnormal==1,"no forged AFTER after exception");
        else if(scenario==L"wrong-thread")check(!r.firstPair&&r.error==20,"wrong owner cannot become bootstrap");
        else {check(r.firstPair&&r.contextVerified&&r.ownerThread==GetCurrentThreadId()&&r.firstRax==0xFEDCBA9876543210ull,"first actual owned-thread pair");for(auto x:r.firstXmm0)check(x==255,"XMM0 preserved");}
        check(InstallCheckpointLiveSessionObserver(&c)!=0,"one-shot install");check(StopCheckpointLiveSessionObserver(nullptr)==0,"restore owned slot");check(*slot==reinterpret_cast<void*>(&CheckpointLiveFixtureOriginal),"original slot restored");
        check(!invoke(cached,c.states[4]),"cached old bridge forwards after stop");GetCheckpointLiveSessionReport(&r);check(r.modulePinned&&r.slotRestored&&r.protectionRestored&&r.stopped,"module retained and protection restored");check(r.bridgeStarted==2,"late cached call belongs to old bridge");
    }
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"config_size\":%zu,\"report_size\":%zu,\"install_exit\":%lu,\"original_calls\":%u,\"game_access\":false}\n",scenario.c_str(),failures?"false":"true",failures,sizeof c,sizeof r,install,calls);
    return failures?1:0;
}
