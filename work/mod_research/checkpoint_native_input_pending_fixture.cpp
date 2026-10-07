#include "checkpoint_native_input_pending_adapter.h"
#include "checkpoint_native_input_pending_archived.h"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace p=checkpoint_native_input_pending;
namespace {
void Check(bool value,const char* why){if(!value)throw std::runtime_error(why);}
template<class T>void Put(std::uint8_t* bytes,std::size_t off,T value){std::memcpy(bytes+off,&value,sizeof value);}
template<class T>T Get(const std::uint8_t* bytes,std::size_t off){T value{};std::memcpy(&value,bytes+off,sizeof value);return value;}
template<std::size_t N>p::Span Span(const std::array<std::uint8_t,N>& a){return{a.data(),a.size()};}
using Fetch=std::int32_t(*)(const void*);
class Code {
public:
    Code(){
        memory=VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);Check(memory!=nullptr,"own code allocate");
        std::memcpy(memory,p::kArchivedFetchFixture.data(),p::kArchivedFetchFixture.size());DWORD old=0;
        Check(VirtualProtect(memory,4096,PAGE_EXECUTE_READ,&old)!=0,"own code RX");
        Check(FlushInstructionCache(GetCurrentProcess(),memory,p::kArchivedFetchFixture.size())!=0,"own cache flush");
    }
    ~Code(){if(memory)VirtualFree(memory,0,MEM_RELEASE);}
    Fetch function()const{return reinterpret_cast<Fetch>(memory);}
private:void*memory=nullptr;
};
enum class Action{None,InjectMenu,Authorize,AuthorizeWrongObject,Reenter,Throw,SkipPrefetch,WrongRsi};
struct Fixture;
#pragma warning(push)
#pragma warning(disable:4324) // Preserve exact alignment of the captured bridge frame.
struct Driver {
    Fixture* fixture=nullptr;Fetch fetch=nullptr;Action action=Action::None;
    CheckpointPushFrame frame{};
    p::Report before{},prefetch{},after{},nested{};
    p::Error begin=p::Error::NoAuthorization,commit=p::Error::NoAuthorization,close=p::Error::WrongStage;
    p::Ticket ticket{};unsigned bodies=0,after_calls=0;std::int32_t fetched=-99;
    std::uint64_t args[4]{};char trace[16]{};unsigned count=0;
    void Mark(char c)noexcept{if(count<sizeof trace)trace[count++]=c;}
}driver;
#pragma warning(pop)
struct Fixture {
    std::array<std::uint8_t,0x700>user{};std::array<std::uint8_t,0x100>toolbar{};
    std::array<std::uint8_t,0x500>game{},menu{},other_menu{};std::array<std::uint8_t,0x200>panel{};
    std::array<std::uint8_t,0x80>manager{};std::array<std::uint8_t,0x40>stack{},queue{};
    std::array<std::uint8_t,0x440>cache{};
    p::Config config{};p::Adapter adapter;
    explicit Fixture(Fetch fetch){
        config.binding.attempt[0]=1;config.binding.attachment[0]=2;config.binding.owner_generation=3;
        config.profile_base=0x400000000ull;
        config.user=Span(user);config.toolbar=Span(toolbar);config.game=Span(game);config.panel=Span(panel);
        config.manager=Span(manager);config.stack=Span(stack);config.queue=Span(queue);config.load_cache=Span(cache);
        config.states[0]=0x11111000;config.states[1]=0x22222000;config.states[2]=reinterpret_cast<std::uintptr_t>(game.data());
        config.states[3]=0x33333000;config.states[4]=reinterpret_cast<std::uintptr_t>(user.data());
        Put(user.data(),0,config.profile_base+0x12CC4A8);Put(game.data(),0,config.profile_base+0x12CC9B8);
        std::memcpy(user.data()+0x70,"CUserStrategyState",19);std::memcpy(game.data()+0x70,"CGameState",11);
        Put<std::uint32_t>(user.data(),0x470,2);Put(user.data(),0x478,reinterpret_cast<std::uintptr_t>(toolbar.data()));
        Put<std::int32_t>(toolbar.data(),0x88,-1);Put(game.data(),0x480,reinterpret_cast<std::uintptr_t>(panel.data()));
        Put<std::uint64_t>(manager.data(),0x10,5);Put(manager.data(),0x20,reinterpret_cast<std::uintptr_t>(stack.data()));
        Put<std::uint64_t>(manager.data(),0x38,4);Put(manager.data(),0x40,reinterpret_cast<std::uintptr_t>(queue.data()));
        Put(manager.data(),0x48,reinterpret_cast<std::uintptr_t>(user.data()));
        for(unsigned i=0;i<5;++i)Put(stack.data(),i*8,config.states[i]);
        Put<std::uint32_t>(cache.data(),8,1);Put<std::int32_t>(cache.data(),0x3ec,-1);
        for(auto* bytes:{menu.data(),other_menu.data()}){Put(bytes,0,config.profile_base+0x12DB4C0);std::memcpy(bytes+0x70,"CSaveLoadState",15);}
        Check(adapter.Bind(config)==p::Error::None,"pending adapter bind");
        driver=Driver{};driver.fixture=this;driver.fetch=fetch;
    }
    void QueueOwnedMenu()noexcept{
        Put<std::uint32_t>(cache.data(),8,0);Put<std::uint64_t>(manager.data(),0x30,1);
        Put<std::uint32_t>(queue.data(),0,0);Put(queue.data(),8,reinterpret_cast<std::uintptr_t>(menu.data()));
    }
    std::uint64_t Run(){return CheckpointLoadDispatchBridge0(reinterpret_cast<std::uint64_t>(user.data()),0x1122334455667788ull,0x8877665544332211ull,0xaabbccddeeff0011ull);}
};
void Before(const CheckpointPushFrame*f,void*)noexcept{
    driver.Mark('B');driver.frame=*f;auto&x=*driver.fixture;driver.before=x.adapter.ObserveBefore(x.config.binding,*f);
}
void After(const CheckpointPushFrame*f,void*)noexcept{
    driver.Mark('A');++driver.after_calls;auto&x=*driver.fixture;
    driver.after=x.adapter.ObserveAfter(x.config.binding,*f);
    if(driver.action==Action::Authorize||driver.action==Action::AuthorizeWrongObject){
        driver.begin=x.adapter.BeginAuthorizedLoadPush(x.config.binding,f->call_id,driver.ticket);
        if(driver.begin==p::Error::None){
            x.QueueOwnedMenu();
            driver.commit=x.adapter.CommitAuthorizedLoadPush(driver.ticket,
                driver.action==Action::Authorize?Span(x.menu):Span(x.other_menu));
        }
    }
    driver.close=x.adapter.CloseAfter(x.config.binding,f->call_id);
}
struct OwnedFailure:std::runtime_error{OwnedFailure():std::runtime_error("owned original failure"){};};
std::uint64_t Original(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    ++driver.bodies;driver.args[0]=a;driver.args[1]=b;driver.args[2]=c;driver.args[3]=d;
    auto&x=*driver.fixture;driver.Mark('O');
    if(driver.action==Action::Throw)throw OwnedFailure();
    if(driver.action==Action::InjectMenu)Put<std::int32_t>(x.toolbar.data(),0x88,13);
    if(driver.action==Action::Reenter){auto nested=driver.frame;++nested.call_id;driver.nested=x.adapter.ObserveBefore(x.config.binding,nested);}
    if(driver.action!=Action::SkipPrefetch){
        driver.Mark('P');driver.prefetch=x.adapter.ObserveBeforeFetch(x.config.binding,driver.frame.call_id,
            driver.action==Action::WrongRsi?x.user.data()+1:x.user.data());
    }
    driver.Mark('F');driver.fetched=driver.fetch(x.user.data());
    return 0xF123456789ABCDEFULL;
}

void CleanOrderAndExactOriginal(Fetch fetch){
    Fixture x(fetch);const auto user=x.user;const auto game=x.game;const auto toolbar=x.toolbar;
    Check(x.Run()==0xF123456789ABCDEFULL,"full original RAX preserved");
    Check(std::string(driver.trace,driver.count)=="BOPFA","actual BEFORE/prefetch/native fragment/AFTER order");
    Check(driver.args[0]==reinterpret_cast<std::uint64_t>(x.user.data())&&driver.args[1]==0x1122334455667788ull&&
          driver.args[2]==0x8877665544332211ull&&driver.args[3]==0xaabbccddeeff0011ull,"all four original register arguments preserved");
    Check(!driver.before.pending_admission_candidate&&driver.prefetch.pending_admission_candidate&&driver.after.pending_admission_candidate,
          "entry only precheck; owned prefetch/after candidate explicit");
    Check(x.user==user&&x.game==game&&x.toolbar==toolbar&&driver.fetched==-1,"adapter and empty native fetch preserve bytes");
}
void PlayerPendingNeverErasedByAdapter(Fetch fetch){
    Fixture x(fetch);Put<std::int32_t>(x.toolbar.data(),0x88,6);
    auto r=x.adapter.InspectCurrent(x.config.binding);
    Check(r.decision==p::Decision::PlayerMenuPending&&Get<std::int32_t>(x.toolbar.data(),0x88)==6,"inspect refuses without clearing player command");
    x.Run();Check(driver.before.menu_command==6&&driver.prefetch.menu_command==6&&driver.fetched==6,"exact original fetch sees pending command after admission refusal");
    Check(Get<std::int32_t>(x.toolbar.data(),0x88)==-1&&driver.bodies==1&&driver.after_calls==1,"only original native fragment performs documented clear; engine continues");
    Check(!driver.after.pending_admission_candidate,"consumed player request cannot become clean same-call admission");
}
void NewRequestBetweenEntryAndFetch(Fetch fetch){
    Fixture x(fetch);driver.action=Action::InjectMenu;x.Run();
    Check(driver.before.decision==p::Decision::QuiescentObserved&&driver.prefetch.decision==p::Decision::PlayerMenuPending&&
          driver.fetched==13&&!driver.after.pending_admission_candidate,"fresh prefetch catches command produced by intervening UI callback");
}
void AdvanceAndTransitions(Fetch fetch){
    for(unsigned mode=0;mode<7;++mode){Fixture x(fetch);
        if(mode==0)Put<std::uint32_t>(x.game.data(),0x47c,1);
        if(mode==1)Put<std::uint32_t>(x.panel.data(),0x1b0,1);
        if(mode==2)Put<std::uint32_t>(x.user.data(),0x470,5);
        if(mode==3)Put<std::uint32_t>(x.game.data(),0x474,1);
        if(mode==4)Put<std::uint32_t>(x.game.data(),0x478,1);
        if(mode==5)Put<std::uint32_t>(x.user.data(),0x660,1);
        if(mode==6)Put<std::uintptr_t>(x.user.data(),0x4a8,0x12340000);
        const auto game=x.game;const auto panel=x.panel;const auto user=x.user;x.Run();
        const auto expected=mode<2?p::Decision::AdvancePending:(mode==6?p::Decision::SelectionPending:p::Decision::StateTransition);
        Check(driver.before.decision==expected&&!driver.prefetch.pending_admission_candidate&&driver.bodies==1,"queued transition denies admission without suppressing original");
        Check(x.game==game&&x.panel==panel&&x.user==user,"adapter never clears advance or transition state");
    }
}
void AuthorizedExactLoadQueue(Fetch fetch){
    Fixture x(fetch);driver.action=Action::Authorize;x.Run();
    Check(driver.begin==p::Error::None&&driver.commit==p::Error::None,"paired clean scope authorizes exact created menu");
    auto r=x.adapter.InspectCurrent(x.config.binding);Check(r.decision==p::Decision::AuthorizedLoadQueued&&!r.pending_admission_candidate,"authorized queue is a continuation, not new hold admission");
    Put<std::uint64_t>(x.manager.data(),0x30,0);Put<std::uint64_t>(x.manager.data(),0x10,6);
    Put(x.stack.data(),40,reinterpret_cast<std::uintptr_t>(x.menu.data()));Put(x.manager.data(),0x48,reinterpret_cast<std::uintptr_t>(x.menu.data()));
    r=x.adapter.InspectCurrent(x.config.binding);Check(r.decision==p::Decision::AuthorizedLoadActive&&!r.full_input_hold,"only same authorized menu remains recognized after push");
    Check(x.adapter.CommitAuthorizedLoadPush(driver.ticket,Span(x.menu))==p::Error::WrongStage,"ticket cannot be replayed outside paired AFTER scope");
    Put<std::int32_t>(x.toolbar.data(),0x88,6);
    Check(x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::PlayerMenuPending,"authorized menu never launders pending toolbar command");
    Put<std::int32_t>(x.toolbar.data(),0x88,-1);Put<std::uint64_t>(x.manager.data(),0x10,5);
    Put(x.manager.data(),0x48,reinterpret_cast<std::uintptr_t>(x.user.data()));x.QueueOwnedMenu();
    Check(x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::UnownedStateQueue,"active menu cannot regress to an authorized queue push");
    Put<std::uint64_t>(x.manager.data(),0x30,0);Put<std::uint32_t>(x.cache.data(),8,1);
    Check(x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::StateTransition,"leaving owned menu retires authorization");
    x.QueueOwnedMenu();Check(x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::UnownedStateQueue,"same pointer reused after retirement stays unowned");
}
void PreexistingMenuCannotGainAuthorization(Fetch fetch){
    Fixture x(fetch);x.QueueOwnedMenu();driver.action=Action::Authorize;x.Run();
    Check(driver.before.decision==p::Decision::UnownedStateQueue&&driver.begin==p::Error::NoCleanPrefetch,
          "already queued same-class load menu remains unowned");
    Put<std::uint64_t>(x.manager.data(),0x30,0);Put<std::uint64_t>(x.manager.data(),0x10,6);
    Put(x.stack.data(),40,reinterpret_cast<std::uintptr_t>(x.menu.data()));Put(x.manager.data(),0x48,reinterpret_cast<std::uintptr_t>(x.menu.data()));
    Check(x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::UnownedLoadMenu,"matching class/name alone cannot authorize player menu");
}
void WrongExactMenuIsRejected(Fetch fetch){
    Fixture x(fetch);driver.action=Action::AuthorizeWrongObject;x.Run();
    Check(driver.begin==p::Error::None&&driver.commit==p::Error::NoAuthorization&&
          x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::UnownedStateQueue,
          "ticket cannot authorize different same-class menu pointer");
}
void ThreadIdentityAndSpanBinding(Fetch fetch){
    Fixture x(fetch);auto wrong=x.config.binding;++wrong.attachment[0];
    Check(x.adapter.InspectCurrent(wrong).error==p::Error::Identity,"foreign attachment refused");
    p::Report foreign;std::thread worker([&]{foreign=x.adapter.InspectCurrent(x.config.binding);});worker.join();
    Check(foreign.error==p::Error::WrongThread,"wrong owner thread refused");
    auto bad=x.config;bad.panel.size=1;p::Adapter short_span;Check(short_span.Bind(bad)==p::Error::Span,"short later span rejected");
    bad=x.config;bad.toolbar=bad.user;p::Adapter alias;Check(alias.Bind(bad)==p::Error::Alias,"aliased bound spans rejected");
    Put<std::uintptr_t>(x.user.data(),0x478,0xBADBADBADull);
    Check(x.adapter.InspectCurrent(x.config.binding).error==p::Error::Pointer,"foreign toolbar pointer never followed");
}
void ReentryWrongRsiAndMissingPrefetch(Fetch fetch){
    {Fixture x(fetch);driver.action=Action::Reenter;x.Run();Check(driver.nested.error==p::Error::Reentrant&&driver.close==p::Error::None,"reentrant admission denied without corrupting outer pairing");}
    {Fixture x(fetch);driver.action=Action::WrongRsi;x.Run();Check(driver.prefetch.error==p::Error::CallPair&&driver.after.error==p::Error::NoCleanPrefetch&&!driver.after.pending_admission_candidate,"wrong prefetch RSI cannot count as boundary evidence");}
    {Fixture x(fetch);driver.action=Action::SkipPrefetch;x.Run();Check(driver.after.error==p::Error::NoCleanPrefetch&&!driver.after.pending_admission_candidate,"entry/after-only observations do not fabricate midfunction boundary");}
}
void NativeExceptionNeverFabricatesAfter(Fetch fetch){
    Fixture x(fetch);driver.action=Action::Throw;bool caught=false;
    try{x.Run();}catch(const OwnedFailure&e){caught=std::string(e.what())=="owned original failure";}
    Check(caught&&driver.after_calls==0,"original C++ exception propagates and AFTER absent");
    auto f=driver.frame;++f.call_id;
    Check(x.adapter.ObserveBefore(x.config.binding,f).error==p::Error::Reentrant,"incomplete original remains inadmissible, not guessed clean");
    CheckpointLoadDispatchBridgeStats stats{};CheckpointLoadDispatchBridgeSnapshot(0,&stats);
    Check(stats.active==0&&stats.abnormal_exits>=1,"frozen bridge cleans its active count on exceptional exit");
}
void NoGlobalHoldOrWrites(Fetch fetch){
    Fixture x(fetch);const auto user=x.user;const auto toolbar=x.toolbar;const auto game=x.game;const auto queue=x.queue;
    const auto r=x.adapter.InspectCurrent(x.config.binding);
    Check(r.read_only&&!r.native_hook_installed&&!r.all_pending_sources_covered&&!r.full_input_hold&&!r.pending_admission_candidate,
          "standalone snapshot is not installed hold receipt");
    Check(x.user==user&&x.toolbar==toolbar&&x.game==game&&x.queue==queue,"all inspected business buffers unchanged");
}
}
int main(int argc,char**argv){
    Code code;CheckpointLoadDispatchBridgeConfig c{};c.original=reinterpret_cast<void*>(&Original);c.before=Before;c.after=After;
    if(!CheckpointLoadDispatchBridgeConfigure(0,&c))return 2;
    struct Case{const char*id;void(*run)(Fetch);};
    const std::array<Case,11> cases{{
        {"real_dispatch_before_prefetch_original_after",CleanOrderAndExactOriginal},
        {"pending_denied_original_alone_consumes",PlayerPendingNeverErasedByAdapter},
        {"intervening_ui_request_caught_before_fetch",NewRequestBetweenEntryAndFetch},
        {"advance_transition_selection_refused_readonly",AdvanceAndTransitions},
        {"exact_authorized_queue_and_active_menu",AuthorizedExactLoadQueue},
        {"preexisting_load_menu_cannot_be_laundered",PreexistingMenuCannotGainAuthorization},
        {"wrong_exact_menu_object_refused",WrongExactMenuIsRejected},
        {"thread_identity_span_pointer_binding",ThreadIdentityAndSpanBinding},
        {"reentry_rsi_and_missing_prefetch_refused",ReentryWrongRsiAndMissingPrefetch},
        {"exception_has_no_fabricated_after",NativeExceptionNeverFabricatesAfter},
        {"no_native_writes_or_global_hold_claim",NoGlobalHoldOrWrites},
    }};
    std::vector<std::string>passed,failed;
    for(auto&item:cases){try{item.run(code.function());passed.emplace_back(item.id);std::cout<<"PASS "<<item.id<<'\n';}
        catch(const std::exception&e){failed.emplace_back(item.id);std::cerr<<"FAIL "<<item.id<<": "<<e.what()<<'\n';}}
    if(argc==2){std::ofstream out(argv[1],std::ios::binary|std::ios::trunc);if(!out)return 3;
        out<<"{\n  \"schema\":\"checkpoint-native-input-pending-fixture/v1\",\n  \"scope\":\"owned_buffers_frozen_dispatch_bridge_archived_fetch_block\",\n"
           <<"  \"game_accessed\":false,\n  \"native_hook_installed\":false,\n  \"global_hold_proven\":false,\n  \"cases\":[\n";
        for(std::size_t i=0;i<cases.size();++i){bool ok=false;for(const auto&id:passed)if(id==cases[i].id)ok=true;
            out<<"    {\"id\":\""<<cases[i].id<<"\",\"passed\":"<<(ok?"true":"false")<<"}"<<(i+1<cases.size()?",":"")<<'\n';}
        out<<"  ],\n  \"passed\":"<<passed.size()<<",\n  \"failed\":"<<failed.size()<<"\n}\n";}
    std::cout<<passed.size()<<'/'<<cases.size()<<" pending admission fixtures passed\n";return failed.empty()?0:1;
}
