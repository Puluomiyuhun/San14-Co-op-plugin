#include "checkpoint_bound_input_pending_adapter.h"
#include "checkpoint_native_input_pending_archived.h"
#include <array>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace p=checkpoint_bound_input_pending;
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
        std::memcpy(memory,checkpoint_native_input_pending::kArchivedFetchFixture.data(),checkpoint_native_input_pending::kArchivedFetchFixture.size());DWORD old=0;
        Check(VirtualProtect(memory,4096,PAGE_EXECUTE_READ,&old)!=0,"own code RX");
        Check(FlushInstructionCache(GetCurrentProcess(),memory,checkpoint_native_input_pending::kArchivedFetchFixture.size())!=0,"own cache flush");
    }
    ~Code(){if(memory)VirtualFree(memory,0,MEM_RELEASE);}
    Fetch function()const{return reinterpret_cast<Fetch>(memory);}
private:void*memory=nullptr;
};
enum class Action{None,InjectMenu,Authorize,AuthorizeWrongObject,Reenter,Throw,SkipPrefetch,WrongRsi,ChangeMode};
enum class ResolveCase { Normal,WrongAddress,Small,Large,AliasCache,AliasMenuHead,AliasMenuInterior,AliasMenuTail,MutatePointer,MutateCapacity,MutateCount };
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
    std::array<std::uint8_t,0x80>created_queue{};
    p::Config config{};p::Adapter adapter;
    ResolveCase resolver_case=ResolveCase::Normal;unsigned resolver_calls=0;bool allocate_on_queue=false,resolver_request_ok=true;
    std::size_t menu_span_size=0x500;std::uint8_t*created_target=nullptr;std::size_t created_capacity=4;
    static p::Span Resolve(void* context,std::uintptr_t address,std::size_t bytes)noexcept{
        auto& x=*static_cast<Fixture*>(context);++x.resolver_calls;
        x.resolver_request_ok=x.resolver_request_ok&&address==reinterpret_cast<std::uintptr_t>(x.created_target)&&bytes==x.created_capacity*16;
        p::Span result{x.created_target,bytes};
        if(x.resolver_case==ResolveCase::WrongAddress)++result.data;
        if(x.resolver_case==ResolveCase::Small)--result.size;
        if(x.resolver_case==ResolveCase::Large)++result.size;
        if(x.resolver_case==ResolveCase::MutatePointer)Put(x.manager.data(),0x40,reinterpret_cast<std::uintptr_t>(x.queue.data()));
        if(x.resolver_case==ResolveCase::MutateCapacity)Put<std::uint64_t>(x.manager.data(),0x38,x.created_capacity+1);
        if(x.resolver_case==ResolveCase::MutateCount)Put<std::uint64_t>(x.manager.data(),0x30,2);
        return result;
    }
    void Empty(unsigned mode,ResolveCase how=ResolveCase::Normal){
        config.expected_initial_cache_mode=mode;Put<std::uint32_t>(cache.data(),8,mode);
        config.queue={};Put<std::uint64_t>(manager.data(),0x30,0);Put<std::uint64_t>(manager.data(),0x38,0);Put<std::uintptr_t>(manager.data(),0x40,0);
        config.resolve_created_queue=Resolve;config.queue_resolver_context=this;allocate_on_queue=true;resolver_case=how;created_target=created_queue.data();
        if(how==ResolveCase::AliasCache)created_target=cache.data()+0x100;
        if(how==ResolveCase::AliasMenuHead){created_target=menu.data();created_capacity=1;}
        if(how==ResolveCase::AliasMenuInterior){created_target=menu.data()+0x100;created_capacity=1;}
        if(how==ResolveCase::AliasMenuTail){created_target=menu.data()+0x478;created_capacity=1;menu_span_size=0x480;}
    }
    explicit Fixture(Fetch fetch,bool bind=true){
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
        if(bind)Check(adapter.Bind(config)==p::Error::None,"pending adapter bind");
        driver=Driver{};driver.fixture=this;driver.fetch=fetch;
    }
    void QueueOwnedMenu()noexcept{
        Put<std::uint32_t>(cache.data(),8,0);Put<std::uint64_t>(manager.data(),0x30,1);
        auto* target=queue.data();
        if(allocate_on_queue){target=created_target;Put(manager.data(),0x40,reinterpret_cast<std::uintptr_t>(target));Put<std::uint64_t>(manager.data(),0x38,created_capacity);}
        if(resolver_case!=ResolveCase::AliasMenuHead){Put<std::uint32_t>(target,0,0);Put(target,8,reinterpret_cast<std::uintptr_t>(menu.data()));}
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
                driver.action==Action::Authorize?p::Span{x.menu.data(),x.menu_span_size}:Span(x.other_menu));
        }
    }
    driver.close=x.adapter.CloseAfter(x.config.binding,f->call_id);
}
struct OwnedFailure:std::runtime_error{OwnedFailure():std::runtime_error("owned original failure"){};};
std::uint64_t Original(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){
    ++driver.bodies;driver.args[0]=a;driver.args[1]=b;driver.args[2]=c;driver.args[3]=d;
    auto&x=*driver.fixture;driver.Mark('O');
    if(driver.action==Action::Throw)throw OwnedFailure();
    if(driver.action==Action::ChangeMode)Put<std::uint32_t>(x.cache.data(),8,x.config.expected_initial_cache_mode?0:1);
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
void Mode0PinnedExistingQueue(Fetch fetch){
    Fixture x(fetch,false);x.config.expected_initial_cache_mode=0;Put<std::uint32_t>(x.cache.data(),8,0);
    Check(x.adapter.Bind(x.config)==p::Error::None,"mode0 bind");driver.action=Action::Authorize;x.Run();
    Check(driver.after.pending_admission_candidate&&driver.commit==p::Error::None&&!x.resolver_calls,"mode0 exact pin permits existing clean queue and normal commit");
}
void Mode0EmptyQueueAllocation(Fetch fetch){
    Fixture x(fetch,false);x.Empty(0);Check(x.adapter.Bind(x.config)==p::Error::None,"empty mode0 bind");
    driver.action=Action::Authorize;x.Run();
    Check(driver.before.decision==p::Decision::QuiescentObserved&&driver.prefetch.pending_admission_candidate&&driver.after.pending_admission_candidate,"empty native vector is observed without invented pointer");
    Check(driver.begin==p::Error::None&&driver.commit==p::Error::None&&x.resolver_calls==1&&x.resolver_request_ok,"one consumed ticket validates precise new native queue span");
    Check(x.adapter.InspectCurrent(x.config.binding).decision==p::Decision::AuthorizedLoadQueued,"validated allocation becomes exact owned queue");
    const auto bytes=x.created_queue;Check(x.adapter.CommitAuthorizedLoadPush(driver.ticket,Span(x.menu))==p::Error::WrongStage&&x.resolver_calls==1&&x.created_queue==bytes,"replay neither resolves nor writes native allocation");
}
void EmptyQueueRequiresResolver(Fetch fetch){
    Fixture x(fetch,false);x.Empty(0);x.config.resolve_created_queue=nullptr;
    Check(x.adapter.Bind(x.config)==p::Error::Span&&!x.resolver_calls,"unknown future allocation has no permission without resolver");
}
void ResolverExtentMustBeExact(Fetch fetch){
    for(auto how:{ResolveCase::WrongAddress,ResolveCase::Small,ResolveCase::Large}){
        Fixture x(fetch,false);x.Empty(0,how);Check(x.adapter.Bind(x.config)==p::Error::None,"negative resolver setup");driver.action=Action::Authorize;x.Run();
        Check(driver.begin==p::Error::None&&driver.commit==p::Error::Span&&x.resolver_calls==1&&x.resolver_request_ok,"wrong address or inexact resolved extent refused");
        Check(x.adapter.InspectCurrent(x.config.binding).error==p::Error::Pointer,"rejected span never adopted");
    }
}
void ResolverAliasesRefused(Fetch fetch){
    for(auto how:{ResolveCase::AliasCache,ResolveCase::AliasMenuHead,ResolveCase::AliasMenuInterior,ResolveCase::AliasMenuTail}){
        Fixture x(fetch,false);x.Empty(0,how);Check(x.adapter.Bind(x.config)==p::Error::None,"alias setup binds only original safe buffers");driver.action=Action::Authorize;x.Run();
        Check(driver.commit==p::Error::Alias&&x.resolver_calls==1,"new queue alias of cache or menu head/interior/partial tail refused");
        Check(x.adapter.InspectCurrent(x.config.binding).error==p::Error::Pointer,"aliased queue never adopted");
    }
}
void ResolverChangedHeaderRefused(Fetch fetch){
    for(auto how:{ResolveCase::MutatePointer,ResolveCase::MutateCapacity,ResolveCase::MutateCount}){
        Fixture x(fetch,false);x.Empty(0,how);Check(x.adapter.Bind(x.config)==p::Error::None,"header race setup");driver.action=Action::Authorize;x.Run();
        Check(driver.commit==p::Error::Pointer&&x.resolver_calls==1,"re-read rejects changed pointer/capacity/count after resolution");
    }
}
void InvalidOrChangedInitialModeRefused(Fetch fetch){
    {Fixture x(fetch,false);x.config.expected_initial_cache_mode=2;Check(x.adapter.Bind(x.config)==p::Error::Layout,"unknown configured mode refused");}
    for(unsigned mode:{0u,1u}){
        {Fixture x(fetch,false);x.config.expected_initial_cache_mode=mode;Put<std::uint32_t>(x.cache.data(),8,mode?0:1);Check(x.adapter.Bind(x.config)==p::Error::None,"mode config bound without guessing sampled value");x.Run();Check(driver.before.decision==p::Decision::StateTransition&&!driver.after.pending_admission_candidate,"wrong initial actual mode denied");}
        {Fixture x(fetch,false);x.config.expected_initial_cache_mode=mode;Put<std::uint32_t>(x.cache.data(),8,mode);Check(x.adapter.Bind(x.config)==p::Error::None,"pinned mode binds");driver.action=Action::ChangeMode;x.Run();Check(driver.before.decision==p::Decision::QuiescentObserved&&!driver.prefetch.pending_admission_candidate&&!driver.after.pending_admission_candidate,"mode drift inside original remains denied");}
    }
}
void UnauthorizedAllocationNotFollowed(Fetch fetch){
    Fixture x(fetch,false);x.Empty(0);Check(x.adapter.Bind(x.config)==p::Error::None,"unowned expansion setup");x.QueueOwnedMenu();
    Check(x.adapter.InspectCurrent(x.config.binding).error==p::Error::Pointer&&x.resolver_calls==0,"standalone never resolves unexpected native pointer");
    driver.action=Action::Authorize;x.Run();
    Check(driver.begin!=p::Error::None&&x.resolver_calls==0,"preexisting allocation cannot acquire native queue authorization");
    p::Ticket fake{};fake.binding=x.config.binding;fake.serial=1;fake.call_id=driver.frame.call_id;
    Check(x.adapter.CommitAuthorizedLoadPush(fake,Span(x.menu))==p::Error::WrongStage&&!x.resolver_calls,"invented ticket cannot trigger queue resolution");
}
void ExistingQueueExpansionNotFollowed(Fetch fetch){
    Fixture x(fetch);x.config.resolve_created_queue=Fixture::Resolve; // Config copy cannot mutate already bound adapter.
    Put(x.manager.data(),0x40,reinterpret_cast<std::uintptr_t>(x.created_queue.data()));Put<std::uint64_t>(x.manager.data(),0x38,8);
    x.Run();Check(driver.before.error==p::Error::Pointer&&!driver.after.pending_admission_candidate&&!x.resolver_calls,"nonempty attachment cannot silently follow reallocated vector");
}

}
int main(int argc,char**argv){
    Code code;CheckpointLoadDispatchBridgeConfig c{};c.original=reinterpret_cast<void*>(&Original);c.before=Before;c.after=After;
    if(!CheckpointLoadDispatchBridgeConfigure(0,&c))return 2;
    struct Case{const char*id;void(*run)(Fetch);};
    const std::array<Case,20> cases{{
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
        {"mode0_existing_queue_exact_pin",Mode0PinnedExistingQueue},
        {"mode0_empty_queue_authorized_allocation",Mode0EmptyQueueAllocation},
        {"empty_queue_requires_resolver",EmptyQueueRequiresResolver},
        {"resolved_span_exact_address_and_length",ResolverExtentMustBeExact},
        {"new_queue_alias_cache_menu_head_interior_tail",ResolverAliasesRefused},
        {"resolved_queue_header_rechecked",ResolverChangedHeaderRefused},
        {"initial_mode_invalid_mismatch_or_drift",InvalidOrChangedInitialModeRefused},
        {"unauthorized_allocation_never_resolved",UnauthorizedAllocationNotFollowed},
        {"existing_queue_reallocation_not_adopted",ExistingQueueExpansionNotFollowed},
    }};
    std::vector<std::string>passed,failed;
    for(auto&item:cases){try{item.run(code.function());passed.emplace_back(item.id);std::cout<<"PASS "<<item.id<<'\n';}
        catch(const std::exception&e){failed.emplace_back(item.id);std::cerr<<"FAIL "<<item.id<<": "<<e.what()<<'\n';}}
    if(argc==2){std::ofstream out(argv[1],std::ios::binary|std::ios::trunc);if(!out)return 3;
        out<<"{\n  \"schema\":\"checkpoint-bound-input-pending-fixture/v1\",\n  \"scope\":\"owned_buffers_frozen_dispatch_bridge_archived_fetch_block\",\n"
           <<"  \"game_accessed\":false,\n  \"native_hook_installed\":false,\n  \"global_hold_proven\":false,\n  \"cases\":[\n";
        for(std::size_t i=0;i<cases.size();++i){bool ok=false;for(const auto&id:passed)if(id==cases[i].id)ok=true;
            out<<"    {\"id\":\""<<cases[i].id<<"\",\"passed\":"<<(ok?"true":"false")<<"}"<<(i+1<cases.size()?",":"")<<'\n';}
        out<<"  ],\n  \"passed\":"<<passed.size()<<",\n  \"failed\":"<<failed.size()<<"\n}\n";}
    std::cout<<passed.size()<<'/'<<cases.size()<<" pending admission fixtures passed\n";return failed.empty()?0:1;
}
