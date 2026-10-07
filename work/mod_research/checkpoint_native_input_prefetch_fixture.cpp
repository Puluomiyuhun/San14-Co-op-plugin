#include "checkpoint_native_input_prefetch_bridge.h"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <xmmintrin.h>
namespace pending=checkpoint_native_input_pending;
namespace mid=checkpoint_native_input_prefetch;
extern "C" {
    std::uintptr_t PrefetchFixtureUser=0;
    mid::Frame PrefetchFixtureBefore{},PrefetchFixtureAfter{};
    alignas(16) std::uint8_t PrefetchFixtureSeed[256]{};
    std::int32_t PrefetchFixtureFetched=-99;
    void PrefetchFixtureSite();void PrefetchFixtureClobber();
    extern unsigned char PrefetchFixtureCallReturn,PrefetchFixtureBeforeCall,PrefetchFixtureAfterNative;
}
namespace {
void Check(bool value,const char*why){if(!value)throw std::runtime_error(why);}
template<class T>void Put(std::uint8_t*bytes,std::size_t off,T value){std::memcpy(bytes+off,&value,sizeof value);}
template<class T>T Get(const std::uint8_t*bytes,std::size_t off){T value{};std::memcpy(&value,bytes+off,sizeof value);return value;}
template<std::size_t N>pending::Span Span(const std::array<std::uint8_t,N>&a){return{a.data(),a.size()};}
enum class Mode{Normal,UiRequest,ObserverFault,NativeLoadFault,WrongSite,WrongIdentity,Reenter,NullToolbar};
struct Fixture;
#pragma warning(push)
#pragma warning(disable:4324)
struct Driver {
    Fixture*x=nullptr;Mode mode=Mode::Normal;CheckpointPushFrame call{};
    pending::Report before{},after{};mid::Report observed{};
    unsigned bodies=0,after_calls=0,probe_calls=0;
    void*fault_page=nullptr;
}driver;
#pragma warning(pop)
struct Fixture {
    std::array<std::uint8_t,0x700>user{};std::array<std::uint8_t,0x100>toolbar{};
    std::array<std::uint8_t,0x500>game{};std::array<std::uint8_t,0x200>panel{};
    std::array<std::uint8_t,0x80>manager{};std::array<std::uint8_t,0x40>stack{},queue{};
    std::array<std::uint8_t,0x440>cache{};pending::Config c{};pending::Adapter admission;
    Fixture(){
        c.binding.attempt[0]=1;c.binding.attachment[0]=2;c.binding.owner_generation=3;c.profile_base=0x400000000ull;
        c.user=Span(user);c.toolbar=Span(toolbar);c.game=Span(game);c.panel=Span(panel);
        c.manager=Span(manager);c.stack=Span(stack);c.queue=Span(queue);c.load_cache=Span(cache);
        c.states[0]=0x11110000;c.states[1]=0x22220000;c.states[2]=reinterpret_cast<std::uintptr_t>(game.data());
        c.states[3]=0x33330000;c.states[4]=reinterpret_cast<std::uintptr_t>(user.data());
        Put(user.data(),0,c.profile_base+0x12cc4a8);Put(game.data(),0,c.profile_base+0x12cc9b8);
        std::memcpy(user.data()+0x70,"CUserStrategyState",19);std::memcpy(game.data()+0x70,"CGameState",11);
        Put<std::uint32_t>(user.data(),0x470,2);Put(user.data(),0x478,reinterpret_cast<std::uintptr_t>(toolbar.data()));
        Put<std::int32_t>(toolbar.data(),0x88,-1);Put(game.data(),0x480,reinterpret_cast<std::uintptr_t>(panel.data()));
        Put<std::uint64_t>(manager.data(),0x10,5);Put(manager.data(),0x20,reinterpret_cast<std::uintptr_t>(stack.data()));
        Put<std::uint64_t>(manager.data(),0x38,4);Put(manager.data(),0x40,reinterpret_cast<std::uintptr_t>(queue.data()));
        Put(manager.data(),0x48,reinterpret_cast<std::uintptr_t>(user.data()));
        for(unsigned i=0;i<5;++i)Put(stack.data(),i*8,c.states[i]);
        Put<std::uint32_t>(cache.data(),8,1);Put<std::int32_t>(cache.data(),0x3ec,-1);
        Check(admission.Bind(c)==pending::Error::None,"bind owned pending adapter");
        driver=Driver{};driver.x=this;PrefetchFixtureUser=reinterpret_cast<std::uintptr_t>(user.data());
        PrefetchFixtureBefore=mid::Frame{};PrefetchFixtureAfter=mid::Frame{};PrefetchFixtureFetched=-99;
        for(unsigned i=0;i<256;++i)PrefetchFixtureSeed[i]=static_cast<std::uint8_t>((i*37+17)&255);
    }
    std::uint64_t Run(){return CheckpointLoadDispatchBridge0(reinterpret_cast<std::uint64_t>(user.data()),0x1122,0x3344,0x5566);}
};
void Before(const CheckpointPushFrame*f,void*)noexcept{
    driver.call=*f;driver.before=driver.x->admission.ObserveBefore(driver.x->c.binding,*f);
}
void After(const CheckpointPushFrame*f,void*)noexcept{
    ++driver.after_calls;driver.after=driver.x->admission.ObserveAfter(driver.x->c.binding,*f);
    driver.x->admission.CloseAfter(driver.x->c.binding,f->call_id);
}
void Probe(void*){
    ++driver.probe_calls;
    _mm_setcsr(_mm_getcsr()^0x6000u);
    PrefetchFixtureClobber();
    if(driver.mode==Mode::ObserverFault)RaiseException(0xE0147101,0,0,nullptr);
    if(driver.mode==Mode::Reenter)CheckpointPrefetchObserve(&PrefetchFixtureBefore);
}
std::uint64_t Original(std::uint64_t user,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    ++driver.bodies;Check(user==reinterpret_cast<std::uintptr_t>(driver.x->user.data())&&b==0x1122&&c==0x3344&&d==0x5566,"original register parameters");
    if(driver.mode==Mode::UiRequest)Put<std::int32_t>(driver.x->toolbar.data(),0x88,13);
    if(driver.mode==Mode::NullToolbar)Put<std::uintptr_t>(driver.x->user.data(),0x478,0);
    if(driver.mode==Mode::NativeLoadFault)PrefetchFixtureUser=reinterpret_cast<std::uintptr_t>(driver.fault_page);
    mid::Config config;
    config.pending=&driver.x->admission;config.binding=driver.x->c.binding;config.call_id=driver.call.call_id;
    config.user=driver.x->user.data();config.expected_call_return=reinterpret_cast<std::uintptr_t>(&PrefetchFixtureCallReturn);
    config.before_observation=Probe;
    if(driver.mode==Mode::WrongSite)++config.expected_call_return;
    if(driver.mode==Mode::WrongIdentity)++config.binding.attachment[0];
    mid::Scope scope(config);
    PrefetchFixtureSite();
    driver.observed=scope.GetReport();
    return 0xF123456789ABCDEFull;
}
DWORD RunSeh(Fixture*x)noexcept{
    __try{x->Run();return 0;}
    __except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}
}
void CpuEqualExceptNativeRax(const Fixture&x,std::uintptr_t expected_rax){
    for(unsigned i=0;i<16;++i)Check(PrefetchFixtureAfter.gpr[i]==(i==mid::Rax?expected_rax:PrefetchFixtureBefore.gpr[i]),"live integer registers and original RSP preserved");
    Check(PrefetchFixtureBefore.rflags==PrefetchFixtureAfter.rflags,"all observable RFLAGS restored including arithmetic flags and DF");
    Check(std::memcmp(PrefetchFixtureBefore.xmm,PrefetchFixtureAfter.xmm,256)==0,"all XMM0-15 bit patterns restored");
    Check(PrefetchFixtureBefore.mxcsr==PrefetchFixtureAfter.mxcsr,"MXCSR restored despite observer control change");
    Check((PrefetchFixtureBefore.gpr[mid::Rsp]&15)==0&&PrefetchFixtureBefore.gpr[mid::Rsi]==reinterpret_cast<std::uintptr_t>(x.user.data()),"owned callsite RSP alignment and RSI");
}

void LiveCpuAndActualPair(){
    Fixture x;Check(x.Run()==0xF123456789ABCDEFull,"full original RAX passed through outer dispatch");
    CpuEqualExceptNativeRax(x,reinterpret_cast<std::uintptr_t>(x.toolbar.data()));
    Check(driver.observed.status==mid::Status::Observed&&driver.observed.pending.pending_admission_candidate&&
          driver.after.pending_admission_candidate,"real mid-function helper belongs to actual BEFORE/AFTER call");
    for(unsigned i=0;i<16;++i)Check(driver.observed.captured.gpr[i]==PrefetchFixtureBefore.gpr[i],"observer captured original live registers before replay");
    Check(driver.observed.captured.return_address==reinterpret_cast<std::uintptr_t>(&PrefetchFixtureCallReturn),"actual mid-call return address verified");
    Check(PrefetchFixtureFetched==-1&&driver.probe_calls==1,"empty original native consumer completed");
}
void ExistingPlayerRequestContinues(){
    Fixture x;Put<std::int32_t>(x.toolbar.data(),0x88,6);x.Run();
    Check(driver.observed.pending.decision==pending::Decision::PlayerMenuPending&&!driver.observed.pending.pending_admission_candidate,
          "pending admission denied at actual prefetched CPU boundary");
    Check(PrefetchFixtureFetched==6&&Get<std::int32_t>(x.toolbar.data(),0x88)==-1&&driver.after_calls==1,
          "refusal still executes actual native read-and-clear; no swallowed player command");
    CpuEqualExceptNativeRax(x,reinterpret_cast<std::uintptr_t>(x.toolbar.data()));
}
void UiBetweenEntryAndFetch(){
    Fixture x;driver.mode=Mode::UiRequest;x.Run();
    Check(driver.before.decision==pending::Decision::QuiescentObserved&&driver.observed.pending.menu_command==13&&
          PrefetchFixtureFetched==13&&!driver.after.pending_admission_candidate,"mid bridge catches newly queued request despite clean function entry");
}
void ObserverFaultNoFakeReceipt(){
    Fixture x;driver.mode=Mode::ObserverFault;Put<std::int32_t>(x.toolbar.data(),0x88,9);x.Run();
    Check(driver.observed.status==mid::Status::ObserverFault&&driver.observed.exception_code==0xE0147101&&
          driver.after.error==pending::Error::NoCleanPrefetch&&!driver.after.pending_admission_candidate,"observer fault contained, no invented prefetch evidence");
    Check(PrefetchFixtureFetched==9&&driver.after_calls==1,"observer exception does not suppress native menu handling");
    CpuEqualExceptNativeRax(x,reinterpret_cast<std::uintptr_t>(x.toolbar.data()));
}
void OriginalLoadFaultUnwinds(){
    Fixture x;driver.mode=Mode::NativeLoadFault;
    driver.fault_page=VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_NOACCESS);
    Check(driver.fault_page!=nullptr,"allocate owned inaccessible source");
    const auto code=RunSeh(&x);
    VirtualFree(driver.fault_page,0,MEM_RELEASE);driver.fault_page=nullptr;
    Check(code==EXCEPTION_ACCESS_VIOLATION&&driver.after_calls==0&&PrefetchFixtureFetched==-99,
          "actual relocated original load fault propagates through bridge/site unwind, no AFTER fabricated");
    CheckpointLoadDispatchBridgeStats stats{};CheckpointLoadDispatchBridgeSnapshot(0,&stats);
    Check(stats.active==0&&stats.abnormal_exits>=1,"outer native dispatch finally paired cleanup survived mid-function fault");
    auto next=driver.call;++next.call_id;
    Check(x.admission.ObserveBefore(x.c.binding,next).error==pending::Error::Reentrant,"abnormal original cannot become clean pending admission");
}
void BindingAndReentryFailures(){
    {Fixture x;driver.mode=Mode::WrongSite;x.Run();Check(driver.observed.status==mid::Status::WrongSite&&driver.after.error==pending::Error::NoCleanPrefetch,"wrong continuation address refused");}
    {Fixture x;driver.mode=Mode::WrongIdentity;x.Run();Check(driver.observed.status==mid::Status::PendingRejected&&driver.after.error==pending::Error::NoCleanPrefetch,"stale attachment refused");}
    {Fixture x;driver.mode=Mode::Reenter;x.Run();Check(driver.observed.status==mid::Status::Reentrant&&driver.after.error==pending::Error::NoCleanPrefetch,"reentrant observer does not become success afterward");}
}
void NativeNullBranchAndUnwindMetadata(){
    {Fixture x;driver.mode=Mode::NullToolbar;x.Run();
     Check(PrefetchFixtureFetched==-1&&driver.observed.status==mid::Status::PendingRejected,"original JE null branch lands at native fragment end");
     CpuEqualExceptNativeRax(x,0);}
    DWORD64 base=0;const auto r=RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(&CheckpointPrefetchReplayLoad),&base,nullptr);
    Check(r!=nullptr,"OS-loaded PE has replay-load unwind metadata");
    const auto*info=reinterpret_cast<const std::uint8_t*>(base+r->UnwindData);
    Check((info[0]&7)==1&&(info[3]&15)==5&&(info[3]>>4)==0,"bridge unwind uses stable RBP frame, including flags restore push/pop");
    DWORD64 body_base=0;const auto body=RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(&CheckpointPrefetchMidBody),&body_base,nullptr);
    Check(body&&body_base==base&&body->BeginAddress==r->BeginAddress,"observer body and original replay share complete unwind range");
    DWORD64 site_base=0;Check(RtlLookupFunctionEntry(reinterpret_cast<DWORD64>(&PrefetchFixtureBeforeCall),&site_base,nullptr)!=nullptr,"owned host callsite also has native unwind data");
    MEMORY_BASIC_INFORMATION page{};Check(VirtualQuery(reinterpret_cast<const void*>(&CheckpointPrefetchReplayLoad),&page,sizeof page)==sizeof page&&page.Type==MEM_IMAGE&&
          (page.Protect&(PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)),"only normally loaded own PE executable page used");
}
void NoInstallerOrFullHold(){
    Fixture x;x.Run();
    Check(!driver.observed.installed_in_game&&!driver.observed.global_hold_proven&&!driver.observed.pending.full_input_hold&&
          !driver.observed.pending.native_hook_installed&&!driver.observed.pending.all_pending_sources_covered,"local bridge result never upgrades native installation or global hold");
}
}
int main(int argc,char**argv){
    CheckpointLoadDispatchBridgeConfig c{};c.original=reinterpret_cast<void*>(&Original);c.before=Before;c.after=After;
    if(!CheckpointLoadDispatchBridgeConfigure(0,&c))return 2;
    struct Case{const char*id;void(*run)();};
    const std::array<Case,8>cases{{
        {"all_gpr_rflags_xmm_mxcsr_actual_mid_pair",LiveCpuAndActualPair},
        {"reject_still_runs_native_player_consumer",ExistingPlayerRequestContinues},
        {"new_ui_request_detected_mid_function",UiBetweenEntryAndFetch},
        {"observer_exception_has_no_fake_prefetch",ObserverFaultNoFakeReceipt},
        {"original_load_fault_unwinds_without_after",OriginalLoadFaultUnwinds},
        {"site_identity_and_reentry_refused",BindingAndReentryFailures},
        {"native_relative_branch_and_os_unwind_metadata",NativeNullBranchAndUnwindMetadata},
        {"no_installer_or_global_hold_claim",NoInstallerOrFullHold},
    }};
    std::vector<std::string>passed,failed;
    for(auto&item:cases){try{item.run();passed.emplace_back(item.id);std::cout<<"PASS "<<item.id<<'\n';}
        catch(const std::exception&e){failed.emplace_back(item.id);std::cerr<<"FAIL "<<item.id<<": "<<e.what()<<'\n';}}
    if(argc==2){std::ofstream out(argv[1],std::ios::binary|std::ios::trunc);if(!out)return 3;
        out<<"{\n  \"schema\":\"checkpoint-native-input-prefetch-fixture/v1\",\n  \"scope\":\"owned_PE_RX_mid_bridge_with_archive_bytes\",\n"
           <<"  \"game_accessed\":false,\n  \"installed_in_game\":false,\n  \"global_hold_proven\":false,\n  \"cases\":[\n";
        for(std::size_t i=0;i<cases.size();++i){bool ok=false;for(const auto&id:passed)if(id==cases[i].id)ok=true;
            out<<"    {\"id\":\""<<cases[i].id<<"\",\"passed\":"<<(ok?"true":"false")<<"}"<<(i+1<cases.size()?",":"")<<'\n';}
        out<<"  ],\n  \"passed\":"<<passed.size()<<",\n  \"failed\":"<<failed.size()<<"\n}\n";}
    std::cout<<passed.size()<<'/'<<cases.size()<<" owned mid-function fixtures passed\n";return failed.empty()?0:1;
}
