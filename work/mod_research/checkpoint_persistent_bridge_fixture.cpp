#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include "checkpoint_persistent_bridge.h"
extern "C" {
std::uint64_t CheckpointPersistentFixtureArgs[6][4]{};
std::uint64_t CheckpointPersistentFixtureModulo[6]{};
std::uint64_t CheckpointPersistentFixtureNativeCalls[6]{};
alignas(16) unsigned char CheckpointPersistentFixtureNvPattern[10][16]{};
alignas(16) unsigned char CheckpointPersistentFixtureReturnPattern[6][16]{};
void CheckpointPersistentFixtureBefore(const CheckpointLoadWorkerFrame*,void*);
void CheckpointPersistentFixtureAfter(const CheckpointLoadWorkerFrame*,void*);
void CheckpointPersistentFixtureFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
void CheckpointPersistentFixtureOriginal0();
void CheckpointPersistentFixtureOriginal1();
void CheckpointPersistentFixtureOriginal2();
void CheckpointPersistentFixtureOriginal3();
void CheckpointPersistentFixtureOriginal4();
void CheckpointPersistentFixtureOriginal5();
void CheckpointPersistentBridgeCallOriginal(void*,CheckpointLoadWorkerFrame*);
void CheckpointPersistentBridgeInvoke(unsigned,CheckpointLoadWorkerFrame*);
}
struct alignas(16) Capture {
    std::uint64_t rax,pad;unsigned char xmm0[16];std::uint64_t rsp_before,rsp_after;
    std::uint64_t nv[8];unsigned char xmm_nv[10][16];
};
static_assert(sizeof(Capture)==0x110);
extern "C" void CheckpointPersistentFixtureRun(CheckpointLoadWorkerEntry,Capture*);
enum Mode {Normal,NativeSeh,NativeCpp,AfterSeh,AfterCpp,BeforeSeh,FinallySeh,
    FinallyDuringNativeSeh,NestedNormal,NestedCaught,NestedEscaped,RecursiveBefore,NestedSameSlot,CrossThread};
static thread_local Mode mode=Normal;
static thread_local unsigned faultSlot=1;
static thread_local unsigned seenBefore[6]{},seenAfter[6]{},seenFinally[6]{};
static thread_local CheckpointLoadWorkerFrame beforeFrame[6]{},afterFrame[6]{};
static thread_local CheckpointLoadWorkerExit finalExit[6]{};
static thread_local std::uint64_t token=0xC0FFEE14;
static volatile LONG failures=0,checks=0,entered=0;
static HANDLE allEntered=nullptr,releaseThreads=nullptr;
static constexpr DWORD NativeCode=0xE0144101,AfterCode=0xE0144102,BeforeCode=0xE0144103,CleanupCode=0xE0144104;
static const std::uint64_t args[4]={0x1020304050607080ull,0x90A0B0C0D0E0F001ull,0xF123456789ABCDEFull,0xFEDCBA9876543210ull};
static const std::uint64_t nv[8]={0x1111111122222222ull,0x2222222233333333ull,0x3333333344444444ull,0x4444444455555555ull,
    0x5555555566666666ull,0x6666666677777777ull,0x7777777788888888ull,0x8888888899999999ull};
static void check(bool ok,const char* label){InterlockedIncrement(&checks);if(!ok){InterlockedIncrement(&failures);printf("FAIL %s\n",label);}}
static void raise(DWORD code){const ULONG_PTR p[]={0x1122334455667788ull,0x8877665544332211ull};RaiseException(code,0,2,p);}
static const CheckpointLoadWorkerEntry entries[]={CheckpointPersistentBridge0,CheckpointPersistentBridge1,CheckpointPersistentBridge2,CheckpointPersistentBridge3,CheckpointPersistentBridge4,CheckpointPersistentBridge5};
static std::uint64_t invoke(unsigned s){auto fn=entries[s];return fn(args[0],args[1],args[6],args[3]);}
static CheckpointLoadWorkerOwner owner(){CheckpointLoadWorkerOwner out{};check(CheckpointPersistentCurrentOwner(&out)==1,"owned scope visible");return out;}
static void empty(){CheckpointLoadWorkerOwner out{};check(CheckpointPersistentCurrentOwner(&out)==0&&out.token==0,"TLS empty after exit");}
static int filter(EXCEPTION_POINTERS* ex,DWORD expected,bool* caught){
    auto* e=ex->ExceptionRecord;
    if(e->ExceptionCode!=expected)return EXCEPTION_CONTINUE_SEARCH;
    *caught=e->NumberParameters==2&&e->ExceptionInformation[0]==0x1122334455667788ull&&e->ExceptionInformation[1]==0x8877665544332211ull;
    return EXCEPTION_EXECUTE_HANDLER;
}
static void expectSeh(unsigned slot,DWORD expected){bool caught=false;__try{invoke(slot);}__except(filter(GetExceptionInformation(),expected,&caught)){}check(caught,"original SEH code+parameters propagated");}
extern "C" void CheckpointPersistentFixtureBeforeRecord(const CheckpointLoadWorkerFrame* f,void* context){
    check(context==reinterpret_cast<void*>(std::uintptr_t(f->slot+1)),"configured context");
    ++seenBefore[f->slot];beforeFrame[f->slot]=*f;
    CheckpointLoadWorkerOwner previous{};const bool inherited=CheckpointPersistentCurrentOwner(&previous)==1;
    check(CheckpointPersistentClaim(f,token)==(inherited?0:1),"BEFORE claim only without owned ancestor");
    auto current=owner();check(current.token==token&&current.thread_id==GetCurrentThreadId(),"thread owner identity");
    if(inherited)check(current.call_id==previous.call_id&&current.slot==previous.slot&&current.owner_depth<current.current_depth,"nested ownership unchanged");
    check(CheckpointPersistentClaim(f,token+1)==0,"duplicate takeover rejected");
    if(mode==BeforeSeh&&f->slot==faultSlot)raise(BeforeCode);
    if(mode==RecursiveBefore&&f->slot==0&&current.current_depth==1){
        invoke(1);auto back=owner();check(back.call_id==current.call_id&&back.current_depth==1,"recursive BEFORE restores outer owner");
    }
}
extern "C" void CheckpointPersistentFixtureAfterRecord(const CheckpointLoadWorkerFrame* f,void*){
    ++seenAfter[f->slot];afterFrame[f->slot]=*f;
    auto o=owner();check(o.token==token&&o.current_depth>=o.owner_depth,"AFTER still owns scope");
    check(CheckpointPersistentClaim(f,token+1)==0,"AFTER cannot claim");
    if(mode==AfterSeh&&f->slot==faultSlot)raise(AfterCode);
    if(mode==AfterCpp&&f->slot==faultSlot)throw std::runtime_error("after-fixture-exception");
}
extern "C" void CheckpointPersistentFixtureFinallyRecord(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* ex,void*){
    ++seenFinally[f->slot];finalExit[f->slot]=*ex;
    auto o=owner();check(o.token==token&&o.current_depth==ex->depth,"FINALLY sees owned TLS before pop");
    if(ex->claimed)check(ex->token==token&&o.call_id==f->call_id,"FINALLY bound to owner frame");
    else check(ex->token==0&&o.owner_depth<ex->depth,"unclaimed nested FINALLY inherits outer");
    check(CheckpointPersistentClaim(f,token+1)==0,"FINALLY cannot claim");
    if(mode==FinallySeh||mode==FinallyDuringNativeSeh)raise(CleanupCode);
}
extern "C" __declspec(noinline) void CheckpointPersistentFixtureMaybeThrow(unsigned slot){
    auto o=owner();check(o.token==token,"original has BEFORE owner");
    if(slot==faultSlot&&(mode==NativeSeh||mode==FinallyDuringNativeSeh||mode==NestedEscaped||mode==NestedCaught))raise(NativeCode);
    if(slot==faultSlot&&mode==NativeCpp)throw std::runtime_error("native-fixture-exception");
    if(slot==0&&o.current_depth==1){
        if(mode==NestedNormal||mode==NestedEscaped)invoke(1);
        if(mode==NestedSameSlot)invoke(0);
        if(mode==NestedCaught)expectSeh(1,NativeCode);
        if(mode==NestedNormal||mode==NestedSameSlot||mode==NestedCaught){
            auto back=owner();check(back.call_id==o.call_id&&back.current_depth==1,"inner finally restores live outer scope");
        }
    }
    if(mode==CrossThread){
        if(InterlockedIncrement(&entered)==4)SetEvent(allEntered);
        check(WaitForSingleObject(releaseThreads,5000)==WAIT_OBJECT_0,"thread barrier released");
        check(owner().token==token,"other thread cannot overwrite TLS");
    }
}
static void captureCheck(const Capture& c){
    check(c.rsp_before==c.rsp_after&&(c.rsp_before&15)==0,"caller RSP preserved/aligned");
    check(!memcmp(c.nv,nv,sizeof nv),"all nonvolatile GPRs preserved");
    check(!memcmp(c.xmm_nv,CheckpointPersistentFixtureNvPattern,sizeof c.xmm_nv),"XMM6..XMM15 preserved");
}
static bool unwind(void* p){DWORD64 b=0;return RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(p),&b,nullptr)!=nullptr;}
static CheckpointPersistentBridgeStats snap(unsigned s){CheckpointPersistentBridgeStats r{};check(CheckpointPersistentBridgeSnapshot(s,&r)==1,"stats snapshot");return r;}
static void normal(unsigned s){
    Capture c{};CheckpointPersistentFixtureRun(entries[s],&c);captureCheck(c);
    check(c.rax==0xFEDCBA9876543210ull+s,"full RAX normal");
    check(!memcmp(c.xmm0,CheckpointPersistentFixtureReturnPattern[s],16),"full XMM0 normal");
    check(!memcmp(CheckpointPersistentFixtureArgs[s],args,sizeof args),"four original args");
    check(!memcmp(beforeFrame[s].args,args,sizeof args)&&!memcmp(afterFrame[s].args,args,sizeof args),"four observer args");
    check(CheckpointPersistentFixtureModulo[s]==8&&(beforeFrame[s].caller_entry_rsp&15)==8,"native/bridge entry RSP aligned");
    check(afterFrame[s].result_rax==c.rax&&!memcmp(afterFrame[s].result_xmm0,c.xmm0,16),"AFTER result survives volatile clobber");
    check(finalExit[s].abnormal==0&&finalExit[s].stage==unsigned(CheckpointLoadWorkerStage::Done),"normal FINALLY stage");empty();
}
static DWORD WINAPI runThread(void*){
    mode=CrossThread;token=0xF000000000000000ull+GetCurrentThreadId();empty();
    Capture c{};CheckpointPersistentFixtureRun(CheckpointPersistentBridge0,&c);captureCheck(c);
    check(c.rax==0xFEDCBA9876543210ull,"concurrent native RAX");
    check(!memcmp(c.xmm0,CheckpointPersistentFixtureReturnPattern[0],16),"concurrent native XMM0");
    check(seenBefore[0]==1&&seenAfter[0]==1&&seenFinally[0]==1,"each thread callbacks once");empty();return 0;
}
int main(){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    for(unsigned i=0;i<10;++i)for(unsigned j=0;j<16;++j)CheckpointPersistentFixtureNvPattern[i][j]=static_cast<unsigned char>(i*17+j);
    for(unsigned i=0;i<6;++i)for(unsigned j=0;j<16;++j)CheckpointPersistentFixtureReturnPattern[i][j]=static_cast<unsigned char>(0x40+i*31+j);
    void* originals[]={reinterpret_cast<void*>(&CheckpointPersistentFixtureOriginal0),reinterpret_cast<void*>(&CheckpointPersistentFixtureOriginal1),reinterpret_cast<void*>(&CheckpointPersistentFixtureOriginal2),reinterpret_cast<void*>(&CheckpointPersistentFixtureOriginal3),reinterpret_cast<void*>(&CheckpointPersistentFixtureOriginal4),reinterpret_cast<void*>(&CheckpointPersistentFixtureOriginal5)};
    {CheckpointPersistentBridgeConfig bad;bad.original=originals[0];bad.before=CheckpointPersistentFixtureBefore;
      check(!CheckpointPersistentBridgeConfigure(0,&bad),"observer without finally refused before publication");
      bad.before=nullptr;check(!CheckpointPersistentBridgeConfigure(6,&bad),"physical slot6 refused");
      for(auto entry:entries){bad.original=reinterpret_cast<void*>(entry);check(!CheckpointPersistentBridgeConfigure(0,&bad),"all six recursive originals refused");}}
    for(unsigned s=0;s<6;++s){CheckpointPersistentBridgeConfig c;
        c.original=originals[s];
        c.before=CheckpointPersistentFixtureBefore;c.after=CheckpointPersistentFixtureAfter;c.finally=CheckpointPersistentFixtureFinally;c.context=reinterpret_cast<void*>(std::uintptr_t(s+1));
        check(CheckpointPersistentBridgeConfigure(s,&c)==1,"configure once");check(!CheckpointPersistentBridgeConfigure(s,&c),"reject reconfigure");}
    for(auto p:{reinterpret_cast<void*>(&CheckpointPersistentBridge0),reinterpret_cast<void*>(&CheckpointPersistentBridge1),
        reinterpret_cast<void*>(&CheckpointPersistentBridgeCallOriginal),reinterpret_cast<void*>(&CheckpointPersistentBridgeInvoke),reinterpret_cast<void*>(&CheckpointPersistentFixtureRun)})
        check(unwind(p),"native PE unwind entry present");
    empty();check(!CheckpointPersistentClaim(nullptr,1),"claim outside BEFORE rejected");for(unsigned s=0;s<6;++s)normal(s);
    auto b=snap(1);mode=NativeSeh;expectSeh(1,NativeCode);empty();auto a=snap(1);
    check(a.native_started==b.native_started+1&&a.native_returned==b.native_returned&&a.after_calls==b.after_calls&&a.finally_calls==b.finally_calls+1,"native SEH skips AFTER, runs FINALLY");
    check(finalExit[1].abnormal==1&&finalExit[1].stage==unsigned(CheckpointLoadWorkerStage::Native),"native SEH phase");
    b=a;mode=AfterSeh;expectSeh(1,AfterCode);empty();a=snap(1);
    check(a.native_returned==b.native_returned+1&&a.after_calls==b.after_calls+1&&a.finally_calls==b.finally_calls+1,"AFTER SEH still runs FINALLY");
    check(finalExit[1].abnormal==1&&finalExit[1].stage==unsigned(CheckpointLoadWorkerStage::After),"AFTER SEH phase");
    b=a;mode=BeforeSeh;expectSeh(1,BeforeCode);empty();a=snap(1);
    check(a.native_started==b.native_started&&a.after_calls==b.after_calls&&a.finally_calls==b.finally_calls+1,"BEFORE SEH cleans claimed TLS without original");
    check(finalExit[1].stage==unsigned(CheckpointLoadWorkerStage::Before),"BEFORE SEH phase");
    for(Mode m:{NativeCpp,AfterCpp}){mode=m;bool caught=false;try{invoke(1);}catch(const std::runtime_error& e){caught=!strcmp(e.what(),m==NativeCpp?"native-fixture-exception":"after-fixture-exception");}check(caught,"exact C++ exception preserved");empty();}
    b=snap(1);mode=FinallySeh;normal(1);a=snap(1);check(a.cleanup_faults==b.cleanup_faults+1&&a.abnormal_exits==b.abnormal_exits,"cleanup SEH contained, original return preserved");
    b=a;mode=FinallyDuringNativeSeh;expectSeh(1,NativeCode);empty();a=snap(1);
    check(a.cleanup_faults==b.cleanup_faults+1&&a.abnormal_exits==b.abnormal_exits+1,"cleanup SEH cannot replace in-flight native SEH");
    for(Mode m:{NestedNormal,NestedCaught,RecursiveBefore,NestedSameSlot}){mode=m;invoke(0);empty();}
    mode=NestedEscaped;expectSeh(0,NativeCode);empty();
    check(finalExit[0].abnormal==1&&finalExit[1].abnormal==1,"nested unhandled SEH unwinds both owners");
    mode=Normal;normal(0); // proves no stale scope after all exceptional cases
    allEntered=CreateEventW(nullptr,TRUE,FALSE,nullptr);releaseThreads=CreateEventW(nullptr,TRUE,FALSE,nullptr);
    HANDLE threads[4]{};check(allEntered&&releaseThreads,"own process thread events");
    for(unsigned i=0;i<4;++i)threads[i]=CreateThread(nullptr,0,runThread,nullptr,0,nullptr);
    check(WaitForSingleObject(allEntered,5000)==WAIT_OBJECT_0,"four threads concurrently in native original");
    check(snap(0).active==4,"four independent active TLS scopes");empty();SetEvent(releaseThreads);
    check(WaitForMultipleObjects(4,threads,TRUE,5000)==WAIT_OBJECT_0,"all fixture threads joined");
    for(auto h:threads)CloseHandle(h);CloseHandle(allEntered);CloseHandle(releaseThreads);empty();
    for(unsigned s=0;s<6;++s){
        faultSlot=s;mode=NativeSeh;auto prev=snap(s);expectSeh(s,NativeCode);empty();auto next=snap(s);
        check(next.native_started==prev.native_started+1&&next.native_returned==prev.native_returned&&next.finally_calls==prev.finally_calls+1,"each physical slot native SEH finalized");
        mode=BeforeSeh;prev=next;expectSeh(s,BeforeCode);empty();next=snap(s);
        check(next.native_started==prev.native_started&&next.finally_calls==prev.finally_calls+1,"each physical slot BEFORE SEH finalized without original");
    }
    faultSlot=1;mode=Normal;
    for(unsigned s=0;s<6;++s){
        auto v=snap(s);check(v.started==v.finally_calls&&!v.active,"all six physical entries drained exactly once");
        check(v.native_started==CheckpointPersistentFixtureNativeCalls[s],"each physical original count exact");
        check(unwind(reinterpret_cast<void*>(entries[s])),"six entries have unwind metadata");}
    const auto s0=snap(0),s1=snap(1);
    check(s0.active==0&&s1.active==0,"all scopes drained");
    check(s0.started==s0.finally_calls&&s1.started==s1.finally_calls,"FINALLY exactly once per entry");
    check(s0.native_started==CheckpointPersistentFixtureNativeCalls[0]&&s1.native_started==CheckpointPersistentFixtureNativeCalls[1],"all original calls exactly once");
    check(s0.module_pinned&&s1.module_pinned,"own PE module pinned");
    printf("{\"schema\":\"san14.persistent-six-bridge-fixture.v1\",\"result\":\"%s\",\"checks\":%ld,\"failures\":%ld,\"scenarios\":29,\"physical_slots\":6,\"slot0_calls\":%llu,\"slot1_calls\":%llu,\"cleanup_faults\":%llu,\"game_access\":false,\"scope\":\"Own EXE; native ABI/unwind/TLS finally and Windows threads, no game hook\"}\n",
        failures?"FAIL":"PASS",checks,failures,s0.started,s1.started,s0.cleanup_faults+s1.cleanup_faults);
    return failures?1:0;
}
