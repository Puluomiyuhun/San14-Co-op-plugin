#include "checkpoint_live_session_core.h"
#include "checkpoint_load_hook_set.h"
#include <cstring>
#include <cwchar>
#include <cstdio>
#include "checkpoint_live_session_profile.h"
namespace {
CheckpointLiveSessionConfig config{};CheckpointLiveSessionReport report{};
checkpoint_load_hook_set::Set hooks;SRWLOCK lock=SRWLOCK_INIT;
volatile LONG once=0,stopped=0;HANDLE journal=INVALID_HANDLE_VALUE;
CheckpointPushFrame firstFrame{};bool firstInFlight=false;
template<class T>T at(std::uint64_t p){return *reinterpret_cast<const T*>(p);}
std::uint64_t born(){FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
void error(unsigned e,DWORD exception=0)noexcept{AcquireSRWLockExclusive(&lock);if(!report.error)report.error=e;if(exception)report.exception=exception;ReleaseSRWLockExclusive(&lock);}
bool journalPath(){
    if(!config.journal[0]||config.journal[511]||wcsstr(config.journal,L".."))return false;
    const wchar_t* prefix=L"C:\\Users\\52708\\Documents\\Codex\\2026-10-04\\ni-li\\work\\mod_research\\checkpoint_live_session_";
    const auto n=wcslen(prefix);if(wcsncmp(config.journal,prefix,n))return false;
    const auto suffix=config.journal+n;if(!*suffix)return false;
    for(const auto*p=suffix;*p;++p)if(!((*p>=L'a'&&*p<=L'z')||(*p>=L'A'&&*p<=L'Z')||(*p>=L'0'&&*p<=L'9')||*p==L'_'||*p==L'-'||*p==L'.'))return false;
    return true;
}
// Caller owns report lock; only bounded first/install/stop events touch disk.
bool log(const char* event){
    char text[640]{};const int n=sprintf_s(text,"{\"event\":\"%s\",\"pid\":%u,\"attempt\":\"%llu\",\"thread\":%u,\"call\":\"%llu\",\"before\":\"%llu\",\"after\":\"%llu\",\"queue_calls\":0,\"request_cas\":0,\"load_requested\":false}\n",event,report.pid,report.attempt,report.ownerThread,report.firstCall,report.before,report.after);
    DWORD wrote=0;const bool ok=n>0&&journal!=INVALID_HANDLE_VALUE&&WriteFile(journal,text,DWORD(n),&wrote,nullptr)&&wrote==DWORD(n)&&FlushFileBuffers(journal);
    if(ok)report.journalFlushed=1;else if(!report.error)report.error=10;return ok;
}
bool context(){
    const auto b=config.base,m=b+0x19E7310;
    if(at<std::uint64_t>(b+0x1FCA1E0)!=config.root||at<std::uint64_t>(config.root+0x85130)!=config.world||
       at<std::uint64_t>(config.root)!=b+0x12AA6B0||at<std::uint64_t>(config.world)!=b+0x12AA638||at<DWORD>(config.world+0x40)!=1)return false;
    if(at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30)!=0||at<std::uint64_t>(m+0x48)!=config.states[4])return false;
    const auto stack=at<std::uint64_t>(m+0x20);if(!stack)return false;
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
    for(unsigned i=0;i<5;++i)if(at<std::uint64_t>(stack+i*8)!=config.states[i]||memcmp(reinterpret_cast<void*>(config.states[i]+0x70),names[i],strlen(names[i])+1)||at<DWORD>(config.states[i]+0x68))return false;
    const auto user=config.states[4],game=config.states[2];
    return at<std::uint64_t>(user)==b+0x12CC4A8&&at<std::uint64_t>(game)==b+0x12CC9B8&&
        at<DWORD>(user+0x470)==2&&!at<DWORD>(user+0x660)&&at<std::uint64_t>(user+0x478)==config.toolbar&&at<LONG>(config.toolbar+0x88)==-1&&
        !at<std::uint64_t>(user+0x4A8)&&!at<std::uint64_t>(user+0x4B0)&&!at<std::uint64_t>(user+0x4B8)&&
        !at<DWORD>(game+0x474)&&!at<DWORD>(game+0x478)&&!at<DWORD>(game+0x47C)&&
        at<std::uint64_t>(game+0x480)==config.panel&&!at<DWORD>(config.panel+0x1B0);
}
void before(const CheckpointPushFrame*f,void*)noexcept{
    AcquireSRWLockExclusive(&lock);
    __try {__try {
        ++report.before;report.lastCall=f->call_id;
        if(InterlockedCompareExchange(&stopped,0,0))__leave;
        if(f->args[0]!=config.states[4]){++report.otherUser;__leave;}
        ++report.matchingBefore;
        if(f->thread_id!=GetCurrentThreadId()||(config.expectedUserThread&&f->thread_id!=config.expectedUserThread)){if(!report.error)report.error=20;__leave;}
        if(report.ownerThread&&report.ownerThread!=f->thread_id){if(!report.error)report.error=21;__leave;}
        report.ownerThread=f->thread_id;
        const auto caller=at<std::uint64_t>(f->caller_entry_rsp);report.lastCaller=caller;
#ifndef CHECKPOINT_LIVE_SESSION_FIXTURE
        if(caller!=config.base+0x50B785){if(!report.error)report.error=22;__leave;}
#endif
        if(!report.firstCall){
            if(!context()){if(!report.error)report.error=23;__leave;}
            report.contextVerified=1;report.firstCall=f->call_id;report.firstCaller=caller;
            memcpy(report.firstArgs,f->args,sizeof report.firstArgs);firstFrame=*f;firstInFlight=true;
            log("first_real_user_before");
        }
    }__except(EXCEPTION_EXECUTE_HANDLER){if(!report.error)report.error=24;report.exception=GetExceptionCode();}}
    __finally{ReleaseSRWLockExclusive(&lock);}
}
void after(const CheckpointPushFrame*f,void*)noexcept{
    AcquireSRWLockExclusive(&lock);
    __try {__try {
        ++report.after;if(f->args[0]==config.states[4])++report.matchingAfter;
        if(!firstInFlight||f->call_id!=firstFrame.call_id)__leave;
        if(f->thread_id!=firstFrame.thread_id||f->caller_entry_rsp!=firstFrame.caller_entry_rsp||memcmp(f->args,firstFrame.args,sizeof f->args)){++report.unpaired;if(!report.error)report.error=25;__leave;}
        report.firstRax=f->result_rax;memcpy(report.firstXmm0,f->result_xmm0,16);report.firstPair=1;firstInFlight=false;log("first_real_user_after");
    }__except(EXCEPTION_EXECUTE_HANDLER){if(!report.error)report.error=26;report.exception=GetExceptionCode();}}
    __finally{ReleaseSRWLockExclusive(&lock);}
}
}
extern "C" __declspec(dllexport) DWORD WINAPI InstallCheckpointLiveSessionObserver(void* input){
    if(InterlockedCompareExchange(&once,1,0))return 1;
    __try {
        if(!input)return 2;config=*static_cast<const CheckpointLiveSessionConfig*>(input);
        if(config.magic!=CheckpointLiveSessionMagic||config.size!=sizeof config||config.version!=1||config.flags||config.reserved32||config.pid!=GetCurrentProcessId()||config.birth!=born()||!config.attempt||!journalPath())return 3;
        unsigned token=0;for(auto byte:config.attachment)token|=byte;if(!token)return 3;
        for(unsigned i=1;i<4;++i)if(config.reserved[i])return 3;
        if(!config.base||!config.root||!config.world||!config.toolbar||!config.panel)return 4;for(auto state:config.states)if(!state)return 4;
        auto original=reinterpret_cast<void*>(config.base+0x3F9B00);
#ifndef CHECKPOINT_LIVE_SESSION_FIXTURE
        if(config.reserved[0]||config.base!=reinterpret_cast<std::uint64_t>(GetModuleHandleW(nullptr)))return 5;
        for(const auto& anchor:CheckpointLiveSessionAnchors)if(memcmp(reinterpret_cast<void*>(config.base+anchor.rva),anchor.bytes,anchor.size))return 6;
#else
        original=reinterpret_cast<void*>(config.reserved[0]);if(!original)return 5;
#endif
        if(!context())return 7;
        auto slot=reinterpret_cast<void*volatile*>(config.base+0x12CC4A8+0x28);if(*slot!=original)return 8;
        HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&InstallCheckpointLiveSessionObserver),&pinned))return 9;
        report.pid=config.pid;report.birth=config.birth;report.base=config.base;report.attempt=config.attempt;report.user=config.states[4];report.slot=reinterpret_cast<std::uint64_t>(slot);report.original=reinterpret_cast<std::uint64_t>(original);report.hook=reinterpret_cast<std::uint64_t>(&CheckpointPushBridge0);report.modulePinned=1;
        journal=CreateFileW(config.journal,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);if(journal==INVALID_HANDLE_VALUE)return 10;report.journalCreated=1;
        if(!log("install_intent_observe_only"))return 10;
        CheckpointPushBridgeConfig bridge{};bridge.original=original;bridge.before=before;bridge.after=after;
        checkpoint_load_hook_set::Binding binding{slot,original,reinterpret_cast<void*>(&CheckpointPushBridge0)};
        if(!CheckpointPushBridgeConfigure(0,&bridge)||!hooks.Initialize(&binding,1))return 11;
        if(!context()||!hooks.Publish(0)){hooks.RestoreAll();return 12;}
        AcquireSRWLockExclusive(&lock);report.installed=1;log("slot_published_observe_only");ReleaseSRWLockExclusive(&lock);return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){error(30,GetExceptionCode());hooks.RestoreAll();return 30;}
}
extern "C" __declspec(dllexport) DWORD WINAPI GetCheckpointLiveSessionReport(void* output){
    if(!output)return 1;
    __try {
        CheckpointLiveSessionReport r{};AcquireSRWLockShared(&lock);r=report;ReleaseSRWLockShared(&lock);
        CheckpointPushBridgeStats b{};CheckpointPushBridgeSnapshot(0,&b);r.active=static_cast<unsigned>(b.active);r.bridgeStarted=b.started;r.bridgeReturned=b.native_returned;r.bridgeAbnormal=b.abnormal_exits;
        checkpoint_load_hook_set::Report h{};hooks.Snapshot(h);if(h.count){r.slotRestored=h.entries[0].restored;r.protectionRestored=h.entries[0].lastProtection==h.entries[0].protection&&!h.entries[0].dirty;}
        *static_cast<CheckpointLiveSessionReport*>(output)=r;return 0;
    }__except(EXCEPTION_EXECUTE_HANDLER){return 2;}
}
extern "C" __declspec(dllexport) DWORD WINAPI StopCheckpointLiveSessionObserver(void*){
    InterlockedExchange(&stopped,1);const bool ok=hooks.RestoreAll();
    AcquireSRWLockExclusive(&lock);report.stopped=1;log("stop_restore_owned_slot_module_retained");ReleaseSRWLockExclusive(&lock);return ok?0:1;
}
