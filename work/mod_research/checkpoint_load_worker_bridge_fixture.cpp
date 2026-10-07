#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include "checkpoint_load_worker_bridge.h"
extern "C" {
std::uint64_t CheckpointLoadWorkerFixtureArgs[2][4]{};
std::uint64_t CheckpointLoadWorkerFixtureModulo[2]{};
std::uint64_t CheckpointLoadWorkerFixtureNativeCalls[2]{};
alignas(16) unsigned char CheckpointLoadWorkerFixtureNvPattern[10][16]{};
alignas(16) unsigned char CheckpointLoadWorkerFixtureReturnPattern[2][16]{};
void CheckpointLoadWorkerFixtureBefore(const CheckpointLoadWorkerFrame*,void*);
void CheckpointLoadWorkerFixtureAfter(const CheckpointLoadWorkerFrame*,void*);
void CheckpointLoadWorkerFixtureFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*);
void CheckpointLoadWorkerFixtureOriginal0();
void CheckpointLoadWorkerFixtureOriginal1();
void CheckpointLoadWorkerBridgeCallOriginal(void*,CheckpointLoadWorkerFrame*);
void CheckpointLoadWorkerBridgeInvoke(unsigned,CheckpointLoadWorkerFrame*);
}
struct alignas(16) Capture {
    std::uint64_t rax,pad;unsigned char xmm0[16];std::uint64_t rsp_before,rsp_after;
    std::uint64_t nv[8];unsigned char xmm_nv[10][16];
};
static_assert(sizeof(Capture)==0x110);
extern "C" void CheckpointLoadWorkerFixtureRun(CheckpointLoadWorkerEntry,Capture*);
enum Mode {Normal,NativeSeh,NativeCpp,AfterSeh,AfterCpp,BeforeSeh,FinallySeh,
    FinallyDuringNativeSeh,NestedNormal,NestedCaught,NestedEscaped,RecursiveBefore,NestedSameSlot,CrossThread};
static thread_local Mode mode=Normal;
static thread_local unsigned seenBefore[2]{},seenAfter[2]{},seenFinally[2]{};
static thread_local CheckpointLoadWorkerFrame beforeFrame[2]{},afterFrame[2]{};
static thread_local CheckpointLoadWorkerExit finalExit[2]{};
static thread_local std::uint64_t token=0xC0FFEE14;
static volatile LONG failures=0,checks=0,entered=0;
static HANDLE allEntered=nullptr,releaseThreads=nullptr;
static constexpr DWORD NativeCode=0xE0144101,AfterCode=0xE0144102,BeforeCode=0xE0144103,CleanupCode=0xE0144104;
static const std::uint64_t args[4]={0x1020304050607080ull,0x90A0B0C0D0E0F001ull,0xF123456789ABCDEFull,0xFEDCBA9876543210ull};
static const std::uint64_t nv[8]={0x1111111122222222ull,0x2222222233333333ull,0x3333333344444444ull,0x4444444455555555ull,
    0x5555555566666666ull,0x6666666677777777ull,0x7777777788888888ull,0x8888888899999999ull};
static void check(bool ok,const char* label){InterlockedIncrement(&checks);if(!ok){InterlockedIncrement(&failures);printf("FAIL %s\n",label);}}
static void raise(DWORD code){const ULONG_PTR p[]={0x1122334455667788ull,0x8877665544332211ull};RaiseException(code,0,2,p);}
static std::uint64_t invoke(unsigned s){auto fn=s?CheckpointLoadWorkerBridge1:CheckpointLoadWorkerBridge0;return fn(args[0],args[1],args[2],args[3]);}
static CheckpointLoadWorkerOwner owner(){CheckpointLoadWorkerOwner out{};check(CheckpointLoadWorkerCurrentOwner(&out)==1,"owned scope visible");return out;}
static void empty(){CheckpointLoadWorkerOwner out{};check(CheckpointLoadWorkerCurrentOwner(&out)==0&&out.token==0,"TLS empty after exit");}
static int filter(EXCEPTION_POINTERS* ex,DWORD expected,bool* caught){
    auto* e=ex->ExceptionRecord;
    if(e->ExceptionCode!=expected)return EXCEPTION_CONTINUE_SEARCH;
    *caught=e->NumberParameters==2&&e->ExceptionInformation[0]==0x1122334455667788ull&&e->ExceptionInformation[1]==0x8877665544332211ull;
    return EXCEPTION_EXECUTE_HANDLER;
}
static void expectSeh(unsigned slot,DWORD expected){bool caught=false;__try{invoke(slot);}__except(filter(GetExceptionInformation(),expected,&caught)){}check(caught,"original SEH code+parameters propagated");}
extern "C" void CheckpointLoadWorkerFixtureBeforeRecord(const CheckpointLoadWorkerFrame* f,void* context){
    check(context==reinterpret_cast<void*>(std::uintptr_t(f->slot+1)),"configured context");
    ++seenBefore[f->slot];beforeFrame[f->slot]=*f;
    CheckpointLoadWorkerOwner previous{};const bool inherited=CheckpointLoadWorkerCurrentOwner(&previous)==1;
    check(CheckpointLoadWorkerClaim(f,token)==(inherited?0:1),"BEFORE claim only without owned ancestor");
    auto current=owner();check(current.token==token&&current.thread_id==GetCurrentThreadId(),"thread owner identity");
    if(inherited)check(current.call_id==previous.call_id&&current.slot==previous.slot&&current.owner_depth<current.current_depth,"nested ownership unchanged");
    check(CheckpointLoadWorkerClaim(f,token+1)==0,"duplicate takeover rejected");
    if(mode==BeforeSeh&&f->slot==1)raise(BeforeCode);
    if(mode==RecursiveBefore&&f->slot==0&&current.current_depth==1){
        invoke(1);auto back=owner();check(back.call_id==current.call_id&&back.current_depth==1,"recursive BEFORE restores outer owner");
    }
}
extern "C" void CheckpointLoadWorkerFixtureAfterRecord(const CheckpointLoadWorkerFrame* f,void*){
    ++seenAfter[f->slot];afterFrame[f->slot]=*f;
    auto o=owner();check(o.token==token&&o.current_depth>=o.owner_depth,"AFTER still owns scope");
    check(CheckpointLoadWorkerClaim(f,token+1)==0,"AFTER cannot claim");
    if(mode==AfterSeh&&f->slot==1)raise(AfterCode);
    if(mode==AfterCpp&&f->slot==1)throw std::runtime_error("after-fixture-exception");
}
extern "C" void CheckpointLoadWorkerFixtureFinallyRecord(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* ex,void*){
    ++seenFinally[f->slot];finalExit[f->slot]=*ex;
    auto o=owner();check(o.token==token&&o.current_depth==ex->depth,"FINALLY sees owned TLS before pop");
    if(ex->claimed)check(ex->token==token&&o.call_id==f->call_id,"FINALLY bound to owner frame");
    else check(ex->token==0&&o.owner_depth<ex->depth,"unclaimed nested FINALLY inherits outer");
    check(CheckpointLoadWorkerClaim(f,token+1)==0,"FINALLY cannot claim");
    if(mode==FinallySeh||mode==FinallyDuringNativeSeh)raise(CleanupCode);
}
extern "C" __declspec(noinline) void CheckpointLoadWorkerFixtureMaybeThrow(unsigned slot){
    auto o=owner();check(o.token==token,"original has BEFORE owner");
    if(slot==1&&(mode==NativeSeh||mode==FinallyDuringNativeSeh||mode==NestedEscaped||mode==NestedCaught))raise(NativeCode);
    if(slot==1&&mode==NativeCpp)throw std::runtime_error("native-fixture-exception");
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
    check(!memcmp(c.xmm_nv,CheckpointLoadWorkerFixtureNvPattern,sizeof c.xmm_nv),"XMM6..XMM15 preserved");
}
static bool unwind(void* p){DWORD64 b=0;return RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(p),&b,nullptr)!=nullptr;}
static CheckpointLoadWorkerBridgeStats snap(unsigned s){CheckpointLoadWorkerBridgeStats r{};check(CheckpointLoadWorkerBridgeSnapshot(s,&r)==1,"stats snapshot");return r;}
static void normal(unsigned s){
    Capture c{};CheckpointLoadWorkerFixtureRun(s?CheckpointLoadWorkerBridge1:CheckpointLoadWorkerBridge0,&c);captureCheck(c);
    check(c.rax==0xFEDCBA9876543210ull+s,"full RAX normal");
    check(!memcmp(c.xmm0,CheckpointLoadWorkerFixtureReturnPattern[s],16),"full XMM0 normal");
    check(!memcmp(CheckpointLoadWorkerFixtureArgs[s],args,sizeof args),"four original args");
    check(!memcmp(beforeFrame[s].args,args,sizeof args)&&!memcmp(afterFrame[s].args,args,sizeof args),"four observer args");
    check(CheckpointLoadWorkerFixtureModulo[s]==8&&(beforeFrame[s].caller_entry_rsp&15)==8,"native/bridge entry RSP aligned");
    check(afterFrame[s].result_rax==c.rax&&!memcmp(afterFrame[s].result_xmm0,c.xmm0,16),"AFTER result survives volatile clobber");
    check(finalExit[s].abnormal==0&&finalExit[s].stage==unsigned(CheckpointLoadWorkerStage::Done),"normal FINALLY stage");empty();
}
static DWORD WINAPI runThread(void*){
    mode=CrossThread;token=0xF000000000000000ull+GetCurrentThreadId();empty();
    Capture c{};CheckpointLoadWorkerFixtureRun(CheckpointLoadWorkerBridge0,&c);captureCheck(c);
    check(c.rax==0xFEDCBA9876543210ull,"concurrent native RAX");
    check(!memcmp(c.xmm0,CheckpointLoadWorkerFixtureReturnPattern[0],16),"concurrent native XMM0");
    check(seenBefore[0]==1&&seenAfter[0]==1&&seenFinally[0]==1,"each thread callbacks once");empty();return 0;
}
int main(){
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    for(unsigned i=0;i<10;++i)for(unsigned j=0;j<16;++j)CheckpointLoadWorkerFixtureNvPattern[i][j]=static_cast<unsigned char>(i*17+j);
    for(unsigned i=0;i<2;++i)for(unsigned j=0;j<16;++j)CheckpointLoadWorkerFixtureReturnPattern[i][j]=static_cast<unsigned char>(0x40+i*31+j);
    for(unsigned s=0;s<2;++s){CheckpointLoadWorkerBridgeConfig c;
        c.original=s?reinterpret_cast<void*>(&CheckpointLoadWorkerFixtureOriginal1):reinterpret_cast<void*>(&CheckpointLoadWorkerFixtureOriginal0);
        c.before=CheckpointLoadWorkerFixtureBefore;c.after=CheckpointLoadWorkerFixtureAfter;c.finally=CheckpointLoadWorkerFixtureFinally;c.context=reinterpret_cast<void*>(std::uintptr_t(s+1));
        check(CheckpointLoadWorkerBridgeConfigure(s,&c)==1,"configure once");check(!CheckpointLoadWorkerBridgeConfigure(s,&c),"reject reconfigure");}
    for(auto p:{reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1),
        reinterpret_cast<void*>(&CheckpointLoadWorkerBridgeCallOriginal),reinterpret_cast<void*>(&CheckpointLoadWorkerBridgeInvoke),reinterpret_cast<void*>(&CheckpointLoadWorkerFixtureRun)})
        check(unwind(p),"native PE unwind entry present");
    empty();check(!CheckpointLoadWorkerClaim(nullptr,1),"claim outside BEFORE rejected");normal(0);normal(1);
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
    const auto s0=snap(0),s1=snap(1);
    check(s0.active==0&&s1.active==0,"all scopes drained");
    check(s0.started==s0.finally_calls&&s1.started==s1.finally_calls,"FINALLY exactly once per entry");
    check(s0.native_started==CheckpointLoadWorkerFixtureNativeCalls[0]&&s1.native_started==CheckpointLoadWorkerFixtureNativeCalls[1],"all original calls exactly once");
    check(s0.module_pinned&&s1.module_pinned,"own PE module pinned");
    printf("{\"schema\":\"san14.checkpoint-load-worker-bridge-fixture.v1\",\"result\":\"%s\",\"checks\":%ld,\"failures\":%ld,\"scenarios\":17,\"slot0_calls\":%llu,\"slot1_calls\":%llu,\"cleanup_faults\":%llu,\"game_access\":false,\"scope\":\"Own EXE; native ABI/unwind/TLS finally and Windows threads, no game hook\"}\n",
        failures?"FAIL":"PASS",checks,failures,s0.started,s1.started,s0.cleanup_faults+s1.cleanup_faults);
    return failures?1:0;
}
