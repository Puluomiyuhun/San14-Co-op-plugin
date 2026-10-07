// Normally loaded DLL, owned buffers, real typed calls, archived menu fetch.
#include "checkpoint_planning_hold_adapter.h"
#include "checkpoint_native_input_pending_archived.h"
#include <array>
#include <cstring>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <thread>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
#ifdef CHECKPOINT_PLANNING_HOLD_OWNED_DRY
#include "checkpoint_planning_hold_user_dry.h"
#include "checkpoint_persistent_bridge.h"
#endif
namespace ph=checkpoint_planning_hold;
static void check(bool b,const char*s){if(!b)throw std::runtime_error(s);}
template<class T>static void put(void*p,size_t off,T value){std::memcpy(static_cast<unsigned char*>(p)+off,&value,sizeof value);}
template<class T>static T get(const void*p,size_t off){T value{};std::memcpy(&value,static_cast<const unsigned char*>(p)+off,sizeof value);return value;}
static ph::Context* current=nullptr;static ph::Binding currentBinding{};
static std::uintptr_t rewardHandle=0;
static unsigned rewards=0,sorties=0,mice=0,nestedBlocked=0;static std::string mode;
static int reward(ph::RewardArgs*a){
    ++rewards;check(a&&a->handle==rewardHandle,"Exact reward args");
    if(mode=="nested-replay")nestedBlocked+=PlanningHoldLocalReward(current,a)==0;
    if(mode=="cpp-exception")throw std::runtime_error("exact-original-exception");
    if(mode=="seh-exception")RaiseException(0xE0421377,0,0,nullptr);
    if(mode=="hold-inflight"){
        std::thread t([]{check(PlanningHoldRequest(current,&currentBinding,unsigned(ph::Operation::Hold),1)==unsigned(ph::Status::Ok),"Concurrent hold request");});t.join();
        ph::Report r{};check(PlanningHoldSnapshot(current,&r)&&r.local_inflight==1&&r.covered_local_gate_closed&&!r.covered_local_drained,"Hold cannot drain running original");
    }
    if(mode=="disconnect-inflight"){std::thread t([]{PlanningHoldDisconnect(current);});t.join();}
    return 0x13572468;
}
static void* sortie(std::uint32_t*a,int flags){++sorties;check(a&&a[0]==666&&flags==1,"Exact sortie args and EDX");a[25]+=1;return a;}
static std::uint32_t mouse(const void*p,std::uint32_t b){++mice;check(b==2,"Exact mouse EDX");return get<std::uint32_t>(p,8);}
struct Fixture {
    std::array<unsigned char,0x700>user{};std::array<unsigned char,0x100>toolbar{};
    std::array<unsigned char,0x500>game{};std::array<unsigned char,0x200>panel{};
    std::array<unsigned char,0x80>manager{};std::array<unsigned char,0x40>stack{},queue{};
    std::array<unsigned char,0x440>cache{};
    std::array<unsigned char,0x78>normal{};std::array<unsigned char,0x68>mouseCache{};std::array<unsigned char,0x258>raw{};
    ph::Config config{};ph::Context*context=nullptr;void*code=nullptr;std::uint64_t call=0;
    ph::RewardArgs args{0x11223344,0x22334455,0x33445566};std::uint32_t words[26]{};
    std::array<std::uint32_t,4>ownedOfficers{3,97,759,904};std::array<std::uint32_t,3>ownedFunding{19,12,83308};
    static bool capture(void*p,ph::Kind kind,const void*a,int flags,ph::SemanticReceipt&out){
        auto&f=*static_cast<Fixture*>(p);unsigned char data[160]{};ULONG count=0;
        if(kind==ph::Kind::Reward){
            if(a!=&f.args||f.args.handle!=reinterpret_cast<std::uintptr_t>(f.ownedOfficers.data())||f.args.funding!=reinterpret_cast<std::uintptr_t>(f.ownedFunding.data())||f.ownedOfficers[0]!=3||flags)return false;
            // Fixture-owned deep source, NOT SAN14's pooled-list representation.
            std::memcpy(data,f.ownedOfficers.data(),sizeof f.ownedOfficers);count=sizeof f.ownedOfficers;
            std::memcpy(data+count,f.ownedFunding.data(),sizeof f.ownedFunding);count+=sizeof f.ownedFunding;
        }else {if(a!=f.words||flags!=1)return false;std::memcpy(data,f.words,sizeof f.words);count=sizeof f.words;}
        BCRYPT_ALG_HANDLE algorithm=nullptr;if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;
        const auto status=BCryptHash(algorithm,nullptr,0,data,count,out.digest.data(),ULONG(out.digest.size()));BCryptCloseAlgorithmProvider(algorithm,0);
        out.ownership_token=reinterpret_cast<std::uintptr_t>(&f);out.payload_epoch=1;return status>=0;
    }
    Fixture(){
        auto&b=config.binding;b.native.attempt[0]=1;b.native.attachment[0]=2;b.native.owner_generation=3;b.period=4;b.epoch=5;b.room_input_digest[0]=6;
        auto&p=config.pending;p.binding=b.native;p.profile_base=0x400000000ull;
        p.user={user.data(),user.size()};p.toolbar={toolbar.data(),toolbar.size()};p.game={game.data(),game.size()};p.panel={panel.data(),panel.size()};p.manager={manager.data(),manager.size()};p.stack={stack.data(),stack.size()};p.queue={queue.data(),queue.size()};p.load_cache={cache.data(),cache.size()};
        p.states[0]=0x11111000;p.states[1]=0x22222000;p.states[2]=reinterpret_cast<std::uintptr_t>(game.data());p.states[3]=0x33333000;p.states[4]=reinterpret_cast<std::uintptr_t>(user.data());
        put(user.data(),0,p.profile_base+0x12CC4A8);put(game.data(),0,p.profile_base+0x12CC9B8);
        std::memcpy(user.data()+0x70,"CUserStrategyState",19);std::memcpy(game.data()+0x70,"CGameState",11);
        put<std::uint32_t>(user.data(),0x470,2);put(user.data(),0x478,reinterpret_cast<std::uintptr_t>(toolbar.data()));
        put<std::int32_t>(toolbar.data(),0x88,-1);put(game.data(),0x480,reinterpret_cast<std::uintptr_t>(panel.data()));
        put<std::uint64_t>(manager.data(),0x10,5);put(manager.data(),0x20,reinterpret_cast<std::uintptr_t>(stack.data()));
        put<std::uint64_t>(manager.data(),0x38,4);put(manager.data(),0x40,reinterpret_cast<std::uintptr_t>(queue.data()));put(manager.data(),0x48,p.states[4]);
        for(unsigned i=0;i<5;++i)put(stack.data(),i*8,p.states[i]);put<std::uint32_t>(cache.data(),8,1);put<std::int32_t>(cache.data(),0x3ec,-1);
        put(normal.data(),0,reinterpret_cast<std::uintptr_t>(raw.data()));put<std::uint32_t>(raw.data(),0x50,0x11);raw[0x158+32]=1;
        config.buffers={{normal.data(),normal.size()},{mouseCache.data(),mouseCache.size()},{raw.data(),raw.size()}};
        args.handle=reinterpret_cast<std::uintptr_t>(ownedOfficers.data());args.funding=reinterpret_cast<std::uintptr_t>(ownedFunding.data());rewardHandle=args.handle;
        config.reward=&reward;config.sortie=&sortie;config.mouse=&mouse;words[0]=666;words[2]=1300;
        if(mode!="missing-deep-provider"){config.capture_owned_command=&capture;config.replay_source_context=this;}
        context=PlanningHoldCreate(&config);check(context!=nullptr,"Actual DLL context bind");current=context;currentBinding=b;
        code=VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);check(code!=nullptr,"Owned code allocation");
        std::memcpy(code,ph::pd::kArchivedFetchFixture.data(),ph::pd::kArchivedFetchFixture.size());DWORD old=0;
        check(VirtualProtect(code,4096,PAGE_EXECUTE_READ,&old)!=FALSE,"Owned archived code RX");check(FlushInstructionCache(GetCurrentProcess(),code,4096)!=FALSE,"Owned cache flush");
    }
    ~Fixture(){PlanningHoldDestroy(context);if(code)VirtualFree(code,0,MEM_RELEASE);current=nullptr;}
    ph::Report report(){ph::Report r{};check(PlanningHoldSnapshot(context,&r),"DLL snapshot");check(!r.input_held&&!r.full_input_hold&&!r.room_ack_eligible&&!r.installed_in_game&&!r.game_threads_paused&&!r.physical_release_proven,"No invented full authority");return r;}
    void request(ph::Operation op,std::uint64_t gen){check(PlanningHoldRequest(context,&config.binding,unsigned(op),gen)==unsigned(ph::Status::Ok),"DLL request");}
    std::int32_t boundary(bool prefetch=true,bool late=false){
        CheckpointPushFrame f{};f.args[0]=config.pending.states[4];f.thread_id=GetCurrentThreadId();f.call_id=++call;f.caller_entry_rsp=reinterpret_cast<std::uintptr_t>(&f);
        PlanningHoldBefore(context,&f);if(prefetch)PlanningHoldPrefetch(context,f.call_id,user.data());
        auto fetch=reinterpret_cast<std::int32_t(*)(const void*)>(code);const auto fetched=fetch(user.data());
        if(late)put<std::int32_t>(toolbar.data(),0x88,13);
        f.result_rax=0xF123456789ABCDEF;PlanningHoldAfter(context,&f);return fetched;
    }
    void hold(){request(ph::Operation::Hold,1);boundary();auto r=report();check(r.phase==ph::Phase::Held&&r.covered_operation_completed&&r.covered_local_drained&&r.paired_planning_boundary,"Actual hold subset boundary");}
};
static void seh_case(Fixture&f){
    bool caught=false;
    __try{PlanningHoldLocalReward(f.context,&f.args);}
    __except(GetExceptionCode()==0xE0421377?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}
    check(caught,"Original SEH identity propagated");
}
#ifdef CHECKPOINT_PLANNING_HOLD_OWNED_DRY
namespace ud=checkpoint_planning_hold_user_dry;
static ud::Adapter*dryAdapter=nullptr;static unsigned dryBodies=0,dryAfters=0,dryFinals=0;
static std::uint64_t dryBody(std::uint64_t,std::uint64_t b,std::uint64_t c,std::uint64_t d){++dryBodies;check(b==0x1122334455667788&&c==0x8877665544332211&&d==0xAABBCCDDEEFF0011,"Four-register User ABI");return 0xF123456789ABCDEF;}
static std::uint64_t dryEntry(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return dryAdapter->Invoke(a,b,c,d);}
static void dryAfter(const CheckpointLoadWorkerFrame*,void*)noexcept{++dryAfters;}
static void dryFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*)noexcept{++dryFinals;}
static void dryPump(void*p){auto&f=*static_cast<Fixture*>(p);auto*t=PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args);check(t&&PlanningHoldReplayReward(f.context,t,&f.args)==0x13572468,"Held User skip still pumps private remote replay");}
static void runDry(){
    Fixture f;f.hold();ud::Adapter adapter;dryAdapter=&adapter;
    ud::Config c{};c.hold=f.context;c.original=&dryBody;c.request_owned_dry_skip=true;c.owned_replay_pump=&dryPump;c.context=&f;
    check(adapter.Initialize(c),"Own-process skip adapter initialize");
    CheckpointPersistentBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(&dryEntry);bridge.after=&dryAfter;bridge.finally=&dryFinally;
    check(CheckpointPersistentBridgeConfigure(0,&bridge)==1,"Real six-slot bridge configure");
    if(mode=="dry-wrong-phase")put<std::uint32_t>(f.user.data(),0x470,5);
    auto result=CheckpointPersistentBridge0(f.config.pending.states[4],0x1122334455667788,0x8877665544332211,0xAABBCCDDEEFF0011);
    auto report=adapter.Snapshot();CheckpointPersistentBridgeStats stats{};check(CheckpointPersistentBridgeSnapshot(0,&stats)!=0,"Actual bridge stats");
    check(stats.active==0&&stats.finally_calls==1&&stats.native_returned==1&&dryFinals==1&&dryAfters==1,"Outer bridge normal cleanup preserves real finally");
    if(mode=="dry-held")check(result==0&&report.skipped==1&&!dryBodies&&!report.body_returned&&!report.native_body_returned_last&&rewards==1,"Body genuinely skipped, remote body executed");
    else check(result==0xF123456789ABCDEF&&report.forwarded==1&&dryBodies==1&&report.body_returned==1&&!rewards,"Unknown phase forwards original, not globally frozen");
    std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"actual_os_worker_thread\":%lu,\"body_calls\":%u,\"native_body_skipped\":%llu,\"outer_bridge_finally\":%u,\"full_input_hold\":false,\"room_ack_eligible\":false,\"game_access\":false}\n",mode.c_str(),GetCurrentThreadId(),dryBodies,report.skipped,dryFinals);
}
#endif
int main(int argc,char**argv){
    if(argc!=2)return 2;mode=argv[1];
#ifdef CHECKPOINT_PLANNING_HOLD_OWNED_DRY
    if(mode=="dry-held"||mode=="dry-wrong-phase"){
        std::exception_ptr failure;std::thread worker([&]{try{runDry();}catch(...){failure=std::current_exception();}});worker.join();
        if(failure){try{std::rethrow_exception(failure);}catch(const std::exception&e){std::printf("{\"result\":\"FAIL\",\"reason\":\"%s\"}\n",e.what());return 1;}}return 0;
    }
#endif
    try {Fixture f;
        if(mode=="open-forward"){
            check(PlanningHoldLocalReward(f.context,&f.args)==0x13572468,"EAX result");
            check(PlanningHoldLocalSortie(f.context,f.words,1)==f.words&&f.words[25]==1,"RAX and body");
            put<std::uint32_t>(f.mouseCache.data(),8,0xF1234567);check(PlanningHoldMouse(f.context,f.mouseCache.data(),2)==0xF1234567,"Full EAX mouse");
        }else if(mode=="hold-replay"||mode=="nested-replay"){
            f.hold();const auto originalRaw=f.raw;
            check(PlanningHoldLocalReward(f.context,&f.args)==0&&rewards==0,"Ready blocks local reward body");check(!PlanningHoldLocalSortie(f.context,f.words,1)&&sorties==0,"Ready blocks local sortie body");
            put<std::uint32_t>(f.mouseCache.data(),8,0xF1234567);check(PlanningHoldMouse(f.context,f.mouseCache.data(),2)==0&&f.raw==originalRaw,"Real neutral core mouse with raw physical state preserved");
            auto*t=PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args);check(t!=nullptr,"Private replay ticket");
            check(PlanningHoldReplayReward(f.context,t,&f.args)==0x13572468&&rewards==1,"Ready allows authorized remote reward");
            check(PlanningHoldReplayReward(f.context,t,&f.args)==0&&rewards==1,"Replay once");
            if(mode=="nested-replay")check(nestedBlocked==1,"Replay does not authorize nested local call");
            auto*s=PlanningHoldAuthorizeSortie(f.context,&f.config.binding,2,f.words,1);check(s!=nullptr&&PlanningHoldReplaySortie(f.context,s,f.words,1)==f.words,"Remote sortie allowed while local held");
            f.request(ph::Operation::Drain,2);f.boundary();check(f.report().covered_replays_drained&&f.report().covered_operation_completed,"Covered final drain");
        }else if(mode=="cancel"){
            f.hold();auto*t=PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args);f.request(ph::Operation::Release,2);
            check(!PlanningHoldReplayReward(f.context,t,&f.args)&&!PlanningHoldLocalReward(f.context,&f.args)&&!f.report().covered_operation_completed,"Revoke before release boundary");
            f.boundary();check(f.report().phase==ph::Phase::Open&&PlanningHoldLocalReward(f.context,&f.args)==0x13572468,"Later clean release");
        }else if(mode=="drain-ticket"){
            f.hold();auto*t=PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args);f.request(ph::Operation::Drain,2);f.boundary();check(f.report().phase==ph::Phase::DrainPending&&!f.report().covered_operation_completed,"Outstanding replay ticket prevents drain");
            check(PlanningHoldReplayReward(f.context,t,&f.args)!=0,"Remote after Ready Drain request remains admitted");f.boundary();check(f.report().phase==ph::Phase::Held&&f.report().covered_replays_drained,"Later final drain after remote");
        }else if(mode=="stale-binding"){
            auto b=f.config.binding;++b.epoch;check(PlanningHoldRequest(f.context,&b,unsigned(ph::Operation::Hold),1)==unsigned(ph::Status::Binding),"Wrong epoch rejected");
            b=f.config.binding;b.native.attachment[1]=7;check(!PlanningHoldAuthorizeReward(f.context,&b,1,&f.args),"Wrong attachment rejected");f.hold();check(PlanningHoldRequest(f.context,&f.config.binding,unsigned(ph::Operation::Release),1)==unsigned(ph::Status::StaleAction),"Stale action rejected");
        }else if(mode=="modified-ticket"){
            f.hold();auto*t=PlanningHoldAuthorizeSortie(f.context,&f.config.binding,1,f.words,1);++f.words[2];check(!PlanningHoldReplaySortie(f.context,t,f.words,1)&&sorties==0,"Mutable command mismatch rejected");
            check(!PlanningHoldReplayReward(f.context,reinterpret_cast<const ph::ReplayTicket*>(0x1234),&f.args),"Foreign ticket never dereferenced");
        }else if(mode=="indirect-mutation"){
            f.hold();auto*t=PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args);check(t!=nullptr,"Deep reward grant");++f.ownedOfficers[1];
            check(!PlanningHoldReplayReward(f.context,t,&f.args)&&rewards==0,"Unchanged shell but changed indirect IDs rejects");
            t=PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args);check(t!=nullptr,"Fresh recapture");++f.ownedFunding[2];
            check(!PlanningHoldReplayReward(f.context,t,&f.args)&&rewards==0,"Unchanged shell but changed funding rejects");
        }else if(mode=="missing-deep-provider"){
            f.hold();check(!PlanningHoldAuthorizeReward(f.context,&f.config.binding,1,&f.args)&&!PlanningHoldAuthorizeSortie(f.context,&f.config.binding,1,f.words,1),"Default replay admission refuses absent real ownership provider");
        }else if(mode=="wrong-thread"){
            int result=1;std::thread t([&]{result=PlanningHoldLocalReward(f.context,&f.args);});t.join();check(!result&&rewards==0,"Foreign thread cannot dispatch");
        }else if(mode=="cpp-exception"||mode=="seh-exception"){
            if(mode=="seh-exception")seh_case(f);else {bool caught=false;try{PlanningHoldLocalReward(f.context,&f.args);}catch(const std::runtime_error&e){caught=std::string(e.what())=="exact-original-exception";}check(caught,"C++ exception identity");}
            auto r=f.report();check(r.phase==ph::Phase::FailStop&&r.local_inflight==0&&r.exceptions==1,"Abnormal lease closes but gate failstops");
        }else if(mode=="late-pending"){
            f.request(ph::Operation::Hold,1);f.boundary(true,true);check(!f.report().covered_operation_completed&&get<std::int32_t>(f.toolbar.data(),0x88)==13,"Late native command not cleared or acknowledged");
            check(f.boundary()==13&&!f.report().covered_operation_completed,"Native fetch consumes; dirty entry cannot become clean same call");f.boundary();check(f.report().phase==ph::Phase::Held,"Fresh later clean boundary");
        }else if(mode=="missing-prefetch"){
            f.request(ph::Operation::Hold,1);f.boundary(false);check(!f.report().covered_operation_completed,"No prefetch no receipt");
        }else if(mode=="hold-inflight"){
            check(PlanningHoldLocalReward(f.context,&f.args)==0x13572468,"Original returns during requested hold");f.boundary();check(f.report().phase==ph::Phase::Held&&f.report().local_inflight==0,"Drain after true native return");
        }else if(mode=="disconnect-inflight"){
            check(PlanningHoldLocalReward(f.context,&f.args)==0x13572468,"Disconnect does not fake cancel executing command");check(f.report().phase==ph::Phase::FailStop&&f.report().local_inflight==0&&!PlanningHoldLocalReward(f.context,&f.args),"Disconnect terminal gate");
        }else throw std::runtime_error("Unknown test");
        auto r=f.report();std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"phase\":%u,\"rewards\":%u,\"sorties\":%u,\"mouse_calls\":%u,\"covered_operation_completed\":%s,\"full_input_hold\":false,\"room_ack_eligible\":false,\"game_access\":false}\n",mode.c_str(),unsigned(r.phase),rewards,sorties,mice,r.covered_operation_completed?"true":"false");return 0;
    }catch(const std::exception&e){std::printf("{\"result\":\"FAIL\",\"reason\":\"%s\"}\n",e.what());return 1;}
}
