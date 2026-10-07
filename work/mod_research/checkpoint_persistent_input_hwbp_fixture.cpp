#include "checkpoint_persistent_input_hwbp.h"
// Read-only reuse of predecessor's actual hardware/owned-memory test driver.
// Only provider namespace changes; no receipt or native site is replaced.
#define checkpoint_native_input_hwbp checkpoint_persistent_input_hwbp
#define wmain FrozenHardwareMain
#include "checkpoint_native_input_hwbp_fixture.cpp"
#undef wmain
#undef checkpoint_native_input_hwbp

namespace {
hw::Context contexts[2]{};hw::Config hardware[2]{};
pd::Adapter adapters[2]{};pd::Config bindings[2]{};
CheckpointPushFrame frames[2]{};hw::HardwareReceipt reports[2]{};
pd::Report pendingAfter[2]{};bool started[2]{},initializeResults[2]{};
unsigned counts[2]{};checkpoint_load_input_boundary_fixture::Layout repeatedLayout;
pd::Report repeatedObserve(void* p,const hw::Binding& b,std::uint64_t call,const void* user) noexcept {
    auto i=static_cast<unsigned>(reinterpret_cast<uintptr_t>(p));++counts[i];return adapters[i].ObserveBeforeFetch(b,call,user);
}
void repeatedBefore(const CheckpointPushFrame* f,void*) noexcept {
    auto i=static_cast<unsigned>(f->args[1]);frames[i]=*f;
    check(adapters[i].Bind(bindings[i])==pd::Error::None,"fresh pending adapter binds actual callback thread");
    auto r=adapters[i].ObserveBefore(bindings[i].binding,*f);check(r.error==pd::Error::None,"actual BEFORE pending observation");
}
void repeatedAfter(const CheckpointPushFrame* f,void*) noexcept {
    auto i=static_cast<unsigned>(f->args[1]);pendingAfter[i]=adapters[i].ObserveAfter(bindings[i].binding,*f);
    adapters[i].CloseAfter(bindings[i].binding,f->call_id);
}
std::uint64_t repeatedNative(std::uint64_t user,std::uint64_t index,std::uint64_t mode,std::uint64_t){
    auto i=static_cast<unsigned>(index);
    started[i]=hw::Begin(contexts[i],repeatedObserve,reinterpret_cast<void*>(uintptr_t(i)),bindings[i].binding,frames[i].call_id,reinterpret_cast<void*>(user));
    try {
        HwbpFixtureSite();
        if(mode==1)RaiseException(0xE0810001,0,0,nullptr);
        if(mode==2)debug(2);
    }catch(...){hw::Finish(contexts[i]);hw::Snapshot(contexts[i],reports[i]);throw;}
    hw::Finish(contexts[i]);hw::Snapshot(contexts[i],reports[i]);return 0x123456789ABCDEF0ull;
}
DWORD repeatedInvoke(unsigned i,unsigned mode=0){
    __try {check(CheckpointLoadDispatchBridge0(bindings[i].states[4],i,mode,4)==0x123456789ABCDEF0ull,"unchanged owned original return");return 0;}
    __except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}
}
DWORD WINAPI initializeThread(void* p){auto i=static_cast<unsigned>(reinterpret_cast<uintptr_t>(p));initializeResults[i]=hw::Initialize(contexts[i],hardware[i]);return 0;}
void setupRepeated(){
    check(repeatedLayout.initialize(),"repeated owned layout");auto& l=repeatedLayout;
    const auto span=[](uintptr_t a,size_t n){return pd::Span{reinterpret_cast<const std::uint8_t*>(a),n};};
    for(unsigned i=0;i<2;i++){
        auto& c=bindings[i];c.binding.attempt[0]=static_cast<unsigned char>(1+i);c.binding.attachment[0]=2;c.binding.owner_generation=30+i;c.profile_base=l.config.base;
        memcpy(c.states,l.config.states,sizeof c.states);c.user=span(l.config.states[4],0x700);c.toolbar=span(l.toolbar,0x100);
        c.game=span(l.config.states[2],0x500);c.panel=span(l.panel,0x200);c.manager=span(l.manager,0x80);
        c.stack=span(l.stack,0x40);c.queue=span(l.stack+0x100,0x40);c.load_cache=span(l.config.cache,0x440);
        hardware[i].binding=c.binding;hardware[i].site_rip=reinterpret_cast<uintptr_t>(&HwbpFixtureBeforeCall);
    }
    put<std::uint64_t>(l.manager+0x10,5);put<uintptr_t>(l.manager+0x48,l.config.states[4]);
    put<uintptr_t>(l.manager+0x40,reinterpret_cast<uintptr_t>(bindings[0].queue.data));put<std::uint64_t>(l.manager+0x38,4);put<DWORD>(l.config.cache+8,1);
    HwbpFixtureUser=l.config.states[4];for(unsigned i=0;i<256;i++)HwbpFixtureSeed[i]=static_cast<unsigned char>((i*37+17)&255);
    CheckpointLoadDispatchBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(&repeatedNative);bridge.before=repeatedBefore;bridge.after=repeatedAfter;
    check(CheckpointLoadDispatchBridgeConfigure(0,&bridge)==1,"real native dispatch configured once");
}
bool newCase(const std::wstring& s){return s==L"two-contexts"||s==L"native-exception-two-contexts"||s==L"repeat-context-initialize"||
    s==L"concurrent-initialize"||s==L"copied-context-refused"||s==L"restore-conflict-blocks-next"||s==L"deadline-blocks-next"||s==L"failed-context-terminal";}
}
int wmain(int argc,wchar_t** argv){
    if(argc!=2)return 2;const std::wstring name=argv[1];if(!newCase(name))return FrozenHardwareMain(argc,argv);
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);scenario=name;setupRepeated();
    if(name==L"failed-context-terminal"){
        auto bad=hardware[0];++bad.site_rip;check(!hw::Initialize(contexts[0],bad),"invalid context refuses");
        check(!hw::Initialize(contexts[0],hardware[0]),"failed context cannot retry");check(hw::Initialize(contexts[1],hardware[1]),"independent fresh context permitted");
        check(!hw::Snapshot(contexts[0],reports[0]),"failed reservation not a State pointer");check(repeatedInvoke(1)==0&&started[1],"independent second provider captured");
    }else {
        if(name==L"deadline-blocks-next")hardware[0].helper_deadline_ms=1;
        if(name==L"concurrent-initialize"){
            HANDLE hs[2]{};for(unsigned i=0;i<2;i++)hs[i]=CreateThread(nullptr,0,initializeThread,reinterpret_cast<void*>(uintptr_t(i)),0,nullptr);
            for(unsigned i=0;i<2;i++){check(hs[i]&&WaitForSingleObject(hs[i],5000)==WAIT_OBJECT_0,"concurrent init joined");if(hs[i])CloseHandle(hs[i]);check(initializeResults[i],"concurrent distinct state initialized");}
        }else for(unsigned i=0;i<2;i++)check(hw::Initialize(contexts[i],hardware[i]),"fresh generation Context initialized");
        if(name==L"repeat-context-initialize"){hw::HardwareReceipt beforeInit{},afterInit{};hw::Snapshot(contexts[0],beforeInit);check(!hw::Initialize(contexts[0],hardware[1]),"same Context cannot reconfigure");hw::Snapshot(contexts[0],afterInit);check(!memcmp(&beforeInit,&afterInit,sizeof beforeInit),"duplicate init leaves original receipt unchanged");}
        if(name==L"copied-context-refused"){
            auto copied=contexts[0];hw::HardwareReceipt r{};
            check(!hw::Snapshot(copied,r)&&!hw::Begin(copied,repeatedObserve,nullptr,bindings[0].binding,333,reinterpret_cast<void*>(HwbpFixtureUser)),"copied opaque pointer is not new handle");
            hw::Finish(copied);check(!hw::Initialize(copied,hardware[1]),"copied Context cannot initialize");
        }
        if(name==L"deadline-blocks-next")hw::FixtureHelperDelay(30);
        const auto firstMode=name==L"native-exception-two-contexts"?1u:name==L"restore-conflict-blocks-next"?2u:0u;
        const auto exception=repeatedInvoke(0,firstMode);check(exception==(firstMode==1?0xE0810001u:0u),"native exception preserved exactly");
        const auto frozen=reports[0];
        check(repeatedInvoke(1)==0,"second original still forwards");
        hw::HardwareReceipt old{};check(hw::Snapshot(contexts[0],old)&&!memcmp(&old,&frozen,sizeof old),"old generation report unchanged after new generation");
        const bool uncertain=name==L"restore-conflict-blocks-next"||name==L"deadline-blocks-next";
        if(uncertain){
            check(reports[0].restore_uncertain&&reports[0].finished,"first receipt explicitly uncertain");
            check(!started[1]&&reports[1].error==hw::Error::AlreadyUsed&&!reports[1].entered&&!reports[1].captured&&!counts[1],"retained old TLS blocks new generation hardware arming");
        }else {
            for(unsigned i=0;i<2;i++)check(started[i]&&reports[i].error==hw::Error::None&&reports[i].capture_kind==hw::CaptureKind::HardwareExecuteContext&&reports[i].entered&&reports[i].captured&&reports[i].restored&&reports[i].finished&&!reports[i].restore_uncertain&&reports[i].observer_calls==1&&counts[i]==1&&!memcmp(reports[i].original_dr,reports[i].restored_dr,sizeof reports[i].original_dr),"each actual hardware generation restores exact DR state");
            check(reports[0].binding.owner_generation==30&&reports[1].binding.owner_generation==31&&reports[0].binding.attempt!=reports[1].binding.attempt,"separate immutable generation binding");
            check(pendingAfter[1].pending_admission_candidate,"second actual before/site/after pending path works");
        }
    }
    hw::RuntimeReport runtime{};hw::SnapshotRuntime(runtime);
    check(runtime.ready&&runtime.modulePinned&&runtime.initializeAttempts==1&&runtime.handlerRegistrations==1&&!runtime.failed,"one permanent VEH/runtime across fresh contexts");
    check(runtime.allocatedContexts==(name==L"failed-context-terminal"?1u:2u)&&!runtime.productionAdmission&&!runtime.nativeSchedulerFence,"no scheduler or game authority");
    printf("{\"case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"registrations\":%u,\"contexts\":%llu,\"first_captured\":%u,\"second_captured\":%u,\"first_restored\":%u,\"second_restored\":%u,\"first_error\":%u,\"second_error\":%u,\"game_access\":false,\"native_scheduler_fence\":false}\n",name.c_str(),failures?"false":"true",failures,runtime.handlerRegistrations,runtime.allocatedContexts,reports[0].captured,reports[1].captured,reports[0].restored,reports[1].restored,unsigned(reports[0].error),unsigned(reports[1].error));
    return failures?1:0;
}
