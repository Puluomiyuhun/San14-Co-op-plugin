#include "checkpoint_native_queue_adapter_core.h"
#include "checkpoint_native_queue_adapter_profile.h"
#include <array>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
namespace q=checkpoint_native_queue_adapter;
namespace p=checkpoint_bound_input_pending;
namespace {
void check(bool v,const char* why){if(!v)throw std::runtime_error(why);}
template<class T>void put(void* p,std::size_t o,T v){std::memcpy(static_cast<unsigned char*>(p)+o,&v,sizeof v);}
template<class T>T get(const void*p,std::size_t o){T v{};std::memcpy(&v,static_cast<const unsigned char*>(p)+o,sizeof v);return v;}
template<std::size_t N>p::Span span(const std::array<unsigned char,N>&a){return{a.data(),a.size()};}
enum class Action{Normal,CppException,SehException,WrongKind,WrongClosure,WrongMode,WrongCapacity,NullMenu,StopNative,GuardedQueue,HeaderDrift,ResolveDrift,StopResolve};
struct Fixture;thread_local Fixture* current=nullptr;
#pragma warning(push)
#pragma warning(disable:4324) // Captured production bridge frame has exact 16-byte alignment.
struct Fixture {
    unsigned char* image=nullptr;std::uintptr_t base=0;
    std::array<unsigned char,0x700>user{};
    std::array<unsigned char,0x100>toolbar{};
    std::array<unsigned char,0x500>game{};
    std::array<unsigned char,0x200>panel{};
    std::array<unsigned char,0x80>stack{};
    std::array<unsigned char,0x440>cache{};
    std::array<unsigned char,0x4c0>menu{};
    std::array<unsigned char,1024>queue{},otherQueue{};
    unsigned char* manager=nullptr;void* guarded=nullptr;
    q::Adapter adapter;p::Adapter pending;q::Config config{};
    p::Ticket ticket{};CheckpointPushFrame frame{};std::uintptr_t caller=0;
    unsigned nativeCalls=0;bool argsValid=false;Action action=Action::Normal;
    int owner=7;bool existing=false;bool denyBefore=false;
    static bool external(void*c,q::Point point)noexcept{
        auto&x=*static_cast<Fixture*>(c);
        if(point==q::Point::BeforeNative&&x.denyBefore)return false;
        if(point==q::Point::AfterNative&&x.action==Action::HeaderDrift){
            std::memcpy(x.otherQueue.data(),x.queue.data(),x.queue.size());
            put(x.manager,0x40,reinterpret_cast<std::uintptr_t>(x.otherQueue.data()));
        }
        if(point==q::Point::Resolve&&x.action==Action::ResolveDrift)put<std::uint64_t>(x.manager,0x38,63);
        if(point==q::Point::Resolve&&x.action==Action::StopResolve)x.adapter.Stop();
        return true;
    }
    static void native(void*manager,const char* name,void*mode,void*closure){
        auto&x=*current;++x.nativeCalls;
        unsigned char zero[64]{};
        x.argsValid=manager==x.manager&&name==reinterpret_cast<char*>(x.base+0x12dd6e0)&&
            !std::memcmp(name,"CSaveLoadState",15)&&get<DWORD>(mode,0)==0&&get<DWORD>(mode,4)==0&&!std::memcmp(closure,zero,64);
        if(x.action==Action::CppException)throw std::runtime_error("owned native body exception");
        if(x.action==Action::SehException)RaiseException(0xe1404119,0,0,nullptr);
        put(x.menu.data(),0,x.base+0x12db4c0);std::memcpy(x.menu.data()+0x70,"CSaveLoadState",15);
        put<DWORD>(x.cache.data(),8,0);put<DWORD>(x.cache.data(),0x3f0,0);
        auto*target=x.queue.data();
        if(x.action==Action::GuardedQueue){
            x.guarded=VirtualAlloc(nullptr,8192,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
            check(x.guarded!=nullptr,"guarded region allocation");DWORD old=0;
            check(VirtualProtect(static_cast<unsigned char*>(x.guarded)+4096,4096,PAGE_NOACCESS,&old)!=0,"guarded region protection");
            target=static_cast<unsigned char*>(x.guarded)+4096-16;
        }
        put<DWORD>(target,0,x.action==Action::WrongKind?1:0);
        put(target,8,x.action==Action::NullMenu?std::uintptr_t(0):reinterpret_cast<std::uintptr_t>(x.menu.data()));
        put<std::uint64_t>(x.manager,0x30,1);put<std::uint64_t>(x.manager,0x38,x.action==Action::WrongCapacity?63:64);
        put(x.manager,0x40,reinterpret_cast<std::uintptr_t>(target));
        if(x.action==Action::WrongClosure)put<std::uintptr_t>(x.menu.data(),0x48,1);
        if(x.action==Action::WrongMode)put<DWORD>(x.cache.data(),8,1);
        if(x.action==Action::StopNative)x.adapter.Stop();
    }
    explicit Fixture(bool hasQueue=false):existing(hasQueue){
        image=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2200000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
        check(image!=nullptr,"owned image allocation");base=reinterpret_cast<std::uintptr_t>(image);manager=image+0x19e7310;
        for(const auto&a:CheckpointNativeQueueAnchors)std::memcpy(image+a.rva,a.bytes,a.size);
        auto&c=config.pending;c.binding.attempt[0]=1;c.binding.attachment[0]=2;c.binding.owner_generation=3;c.profile_base=base;
        c.user=span(user);c.toolbar=span(toolbar);c.game=span(game);c.panel=span(panel);c.stack=span(stack);c.load_cache=span(cache);c.manager={manager,0x50};
        c.expected_initial_cache_mode=0;c.resolve_created_queue=q::Adapter::ResolveCallback;c.queue_resolver_context=&adapter;
        c.states[0]=base+0x1000;c.states[1]=base+0x2000;c.states[2]=reinterpret_cast<std::uintptr_t>(game.data());c.states[3]=base+0x3000;c.states[4]=reinterpret_cast<std::uintptr_t>(user.data());
        put(user.data(),0,base+0x12cc4a8);std::memcpy(user.data()+0x70,"CUserStrategyState",19);
        put<DWORD>(user.data(),0x470,2);put(user.data(),0x478,reinterpret_cast<std::uintptr_t>(toolbar.data()));put<LONG>(toolbar.data(),0x88,-1);
        put(game.data(),0,base+0x12cc9b8);std::memcpy(game.data()+0x70,"CGameState",11);put(game.data(),0x480,reinterpret_cast<std::uintptr_t>(panel.data()));
        put<std::uint64_t>(manager,0x10,5);put<std::uint64_t>(manager,0x18,16);put(manager,0x20,reinterpret_cast<std::uintptr_t>(stack.data()));put(manager,0x48,c.states[4]);
        for(unsigned i=0;i<5;++i)put(stack.data(),8*i,c.states[i]);
        put<LONG>(cache.data(),0x3ec,-1);put(image,0x2025318,reinterpret_cast<std::uintptr_t>(cache.data()));
        if(existing){c.queue=span(queue);put<std::uint64_t>(manager,0x38,64);put(manager,0x40,reinterpret_cast<std::uintptr_t>(queue.data()));}
        config.controller_identity=&owner;config.cache=reinterpret_cast<std::uintptr_t>(cache.data());config.validate_external=external;config.external_context=this;config.fixture_native=native;
        caller=base+0x50b785;frame.slot=0;frame.thread_id=GetCurrentThreadId();frame.call_id=41;frame.args[0]=c.states[4];frame.caller_entry_rsp=reinterpret_cast<std::uintptr_t>(&caller);
        current=this;
    }
    ~Fixture(){current=nullptr;if(guarded)VirtualFree(guarded,0,MEM_RELEASE);if(image)VirtualFree(image,0,MEM_RELEASE);}
    void init(){check(adapter.Initialize(config),"queue adapter initialize");}
    void obtainTicket(){
        auto&c=config.pending;check(pending.Bind(c)==p::Error::None,"actual pending bind");
        check(pending.ObserveBefore(c.binding,frame).decision==p::Decision::QuiescentObserved,"actual pending before");
        check(pending.ObserveBeforeFetch(c.binding,frame.call_id,user.data()).pending_admission_candidate,"actual pending prefetch observation");
        check(pending.ObserveAfter(c.binding,frame).pending_admission_candidate,"actual pending after");
        check(pending.BeginAuthorizedLoadPush(c.binding,frame.call_id,ticket)==p::Error::None,"real private pending ticket");
    }
    void authorize(){init();obtainTicket();check(adapter.Authorize(ticket,frame,&owner),"capability authorization");}
    q::Report report(){q::Report r{};check(adapter.Snapshot(r),"report snapshot");return r;}
};
#pragma warning(pop)
bool sehPropagates(q::Adapter*adapter){__try{adapter->Queue();return false;}__except(GetExceptionCode()==0xe1404119?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}}
void run(const std::string&which){
    if(which=="empty-success"||which=="existing-success"){
        Fixture x(which=="existing-success");x.authorize();auto menu=x.adapter.Queue();
        check(menu.data==x.menu.data()&&menu.size==0x4c0&&x.argsValid&&x.nativeCalls==1,"exact native recipe and returned menu");
        check(x.pending.CommitAuthorizedLoadPush(x.ticket,menu)==p::Error::None,"actual pending commit with production resolver");
        auto r=x.report();check(r.error==q::Error::None&&r.native_result_verified==1&&r.resolver_calls==(x.existing?0u:1u)&&r.may_have_queued&&!r.world_ready&&!r.private_ticket_authenticated_by_adapter,"bounded evidence");
        check(x.pending.CloseAfter(x.config.pending.binding,x.frame.call_id)==p::Error::None,"paired scope close");
    }else if(which=="no-authorization"){
        Fixture x;x.init();check(!x.adapter.Queue().data&&x.nativeCalls==0,"no ticket no invocation");
    }else if(which=="wrong-controller"||which=="wrong-ticket"||which=="wrong-caller"||which=="wrong-thread"){
        Fixture x;x.init();x.obtainTicket();bool allowed=false;
        if(which=="wrong-controller")allowed=x.adapter.Authorize(x.ticket,x.frame,&x);
        if(which=="wrong-ticket"){++x.ticket.binding.owner_generation;allowed=x.adapter.Authorize(x.ticket,x.frame,&x.owner);}
        if(which=="wrong-caller"){++x.caller;allowed=x.adapter.Authorize(x.ticket,x.frame,&x.owner);}
        if(which=="wrong-thread"){std::thread worker([&]{allowed=x.adapter.Authorize(x.ticket,x.frame,&x.owner);});worker.join();}
        check(!allowed&&!x.adapter.Queue().data&&x.nativeCalls==0,"mismatched capability denied");
    }else if(which=="stop-before-queue"||which=="header-drift-before"||which=="external-refusal"){
        Fixture x(which=="header-drift-before");x.authorize();
        if(which=="stop-before-queue")x.adapter.Stop();
        if(which=="header-drift-before")put<std::uint64_t>(x.manager,0x38,32);
        if(which=="external-refusal")x.denyBefore=true;
        check(!x.adapter.Queue().data&&x.nativeCalls==0,"final pre-native refusal");
    }else if(which=="native-cpp-exception"||which=="native-seh-exception"){
        Fixture x;x.authorize();bool caught=false;
        if(which=="native-cpp-exception"){x.action=Action::CppException;try{x.adapter.Queue();}catch(const std::runtime_error&){caught=true;}}
        else{x.action=Action::SehException;caught=sehPropagates(&x.adapter);}
        auto r=x.report();check(caught&&r.error==q::Error::NativeException&&r.stage==q::Stage::Uncertain&&r.may_have_queued&&r.native_calls==1&&r.native_returned==0,"original exception rethrown with consumed uncertain capability");
        check(!x.adapter.Queue().data&&x.nativeCalls==1,"native exception never retry");
    }else if(which=="invalid-native-results"){
        for(auto action:{Action::WrongKind,Action::WrongClosure,Action::WrongMode,Action::WrongCapacity,Action::NullMenu}){
            Fixture x;x.authorize();x.action=action;check(!x.adapter.Queue().data&&x.nativeCalls==1&&x.report().stage==q::Stage::Uncertain,"native bad result retained, not undone");
        }
    }else if(which=="full-span-noaccess"){
        Fixture x;x.authorize();x.action=Action::GuardedQueue;check(!x.adapter.Queue().data&&x.nativeCalls==1&&x.report().error!=q::Error::None,"whole vector extent checked beyond readable head");
    }else if(which=="header-drift-after"){
        Fixture x;x.authorize();x.action=Action::HeaderDrift;check(!x.adapter.Queue().data&&x.nativeCalls==1,"returned header frozen across external guard");
    }else if(which=="stop-in-native"){
        Fixture x;x.authorize();x.action=Action::StopNative;check(!x.adapter.Queue().data&&x.nativeCalls==1&&x.report().stopped&&x.report().may_have_queued,"inflight stop cannot claim cancellation");
    }else if(which=="resolver-exact-once"){
        Fixture x;x.authorize();check(x.adapter.Queue().data!=nullptr,"queue succeeds");
        check(!x.adapter.Resolve(reinterpret_cast<std::uintptr_t>(x.queue.data()),1023).data,"short requested extent denied");
        check(!x.adapter.Resolve(reinterpret_cast<std::uintptr_t>(x.queue.data()),1024).data,"resolver rejected ticket consumed");
        check(x.nativeCalls==1,"resolver never creates queue");
    }else if(which=="resolver-header-stop"){
        for(auto action:{Action::ResolveDrift,Action::StopResolve}){Fixture x;x.authorize();check(x.adapter.Queue().data!=nullptr,"queue succeeds");x.action=action;
            check(x.pending.CommitAuthorizedLoadPush(x.ticket,span(x.menu))!=p::Error::None&&x.report().stage==q::Stage::Uncertain,"resolver drift/stop refuses real pending commit");}
    }else if(which=="repeat-queue-authorization"){
        Fixture x;x.authorize();check(x.adapter.Queue().data!=nullptr,"queue succeeds");
        check(!x.adapter.Queue().data&&!x.adapter.Authorize(x.ticket,x.frame,&x.owner)&&x.nativeCalls==1,"one capability cannot be reauthorized or invoke twice");
    }else if(which=="profile-drift"){
        Fixture x;x.image[0x411980]^=1;check(!x.adapter.Initialize(x.config)&&x.nativeCalls==0,"exact archived native bytes required");
    }else throw std::runtime_error("unknown owned fixture case");
}
}
int main(int argc,char**argv){
    if(argc!=2)return 2;
    try{run(argv[1]);std::cout<<"{\"case\":\""<<argv[1]<<"\",\"passed\":true,\"game_access\":false,\"native_body\":\"owned_double\"}\n";return 0;}
    catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 1;}
}
