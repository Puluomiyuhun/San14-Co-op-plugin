#include "checkpoint_planning_dispatcher.h"
#include "checkpoint_planning_dispatcher_fixture_support.inc"
namespace dp=checkpoint_planning_dispatcher;
static dp::Dispatcher*dispatcher=nullptr;static RewardWorld*fixture=nullptr;static unsigned localBodies=0;
static std::uint64_t userOriginal(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){++localBodies;check(a==fixture->addr(fixture->planning.user.data())&&b==23&&c==24&&d==25,"saved original receives four registers");
 if(mode=="body-exception")throw std::runtime_error("user-original-exception");
 if(mode=="hold-during-body"){dispatcher->Request(fixture->config.binding,dp::Action::Hold,1);check(!dispatcher->Snapshot().covered_user_scope_held,"running body never acknowledged held");}
 return 0xABCDEF1234567890ull;
}
static bool source(void*p,std::uintptr_t user,dp::Source&out){auto&f=*static_cast<RewardWorld*>(p);if(user!=f.config.user)return false;out.reward=f.config;out.admission=f.planning.config;return true;}
static int rewardOriginal(ph::RewardArgs*a){auto&f=*fixture;++f.bodies;check(f.counts[f.handle]==2&&a->handle&&f.dtors+1==f.ctors,"fresh concrete list alive in synchronous callback");
 if(mode=="release-during-reward"){check(dispatcher->Request(f.config.binding,dp::Action::Release,2),"release request during native call");auto r=dispatcher->Snapshot();check(r.active==1&&!r.covered_user_scope_drained&&r.release_pending,"release remains pending in native callback");check(f.nodes.size()==2,"release revokes, never frees running list");}
 if(mode=="disconnect-during-reward"){dispatcher->Disconnect();check(f.nodes.size()==2,"disconnect retains running list");}
 if(mode=="reward-exception")throw std::runtime_error("dispatcher-reward-exception");
 return 1;
}
static std::uint64_t entry(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return dispatcher->Invoke(a,b,c,d);}
static void adoptedBefore(const CheckpointLoadWorkerFrame*f,void*p){check(CheckpointPersistentClaim(f,fixture->config.binding.native.owner_generation)==1,"outer owner claims exact frame first");dp::Dispatcher::BeforeCallback(f,p);}
static std::uint64_t invoke(){auto&f=*fixture;return CheckpointPersistentBridge0(f.addr(f.planning.user.data()),23,24,25);}
int main(int argc,char**argv){if(argc!=2)return 2;mode=argv[1];try{RewardWorld f;fixture=&f;check(RewardOwnedDestroy(f.owner),"discard fixture-only old owner");f.owner=nullptr;f.planning.config.reward=&rewardOriginal;
 dp::Dispatcher adapter;dispatcher=&adapter;dp::Config c{};c.binding=f.config.binding;c.original=&userOriginal;c.claim=&CheckpointPersistentClaim;c.current_owner=&CheckpointPersistentCurrentOwner;c.sample=&source;c.context=&f;c.mode=mode=="forward-only"?dp::Mode::ForwardOnly:dp::Mode::UserSubsetSkip;check(adapter.Initialize(c),"dispatcher initialize");
 CheckpointPersistentBridgeConfig bridge{};bridge.original=reinterpret_cast<void*>(&entry);bridge.before=mode=="existing-owner"?&adoptedBefore:&dp::Dispatcher::BeforeCallback;bridge.finally=&dp::Dispatcher::FinallyCallback;bridge.context=&adapter;check(CheckpointPersistentBridgeConfigure(0,&bridge)==1,"actual immutable bridge configured");
 const bool noInitialHold=mode=="hold-during-body"||mode=="body-exception"||mode=="open-reward";
 if(!noInitialHold)check(adapter.Request(c.binding,dp::Action::Hold,1),"request covered User hold");
 bool noJob=mode=="hold-only"||mode=="forward-only"||mode=="hold-during-body"||mode=="body-exception"||mode=="phase-reject"||mode=="menu-reject"||mode=="unowned-call";
 if(!noJob)check(adapter.Submit(c.binding,1,f.command),"queue copied command values");
 if(mode=="cancel-before")check(adapter.Request(c.binding,dp::Action::Release,2),"cancel before entry");
 if(mode=="disconnect-before")adapter.Disconnect();
 if(mode=="phase-reject")put<unsigned>(f.planning.user.data(),0x470,5);
 if(mode=="menu-reject")put<int>(f.planning.toolbar.data(),0x88,13);
 std::uint64_t value=0;bool caught=false;auto work=[&]{try{value=mode=="unowned-call"?entry(f.config.user,23,24,25):invoke();}catch(const std::runtime_error&e){caught=std::string(e.what()).find("exception")!=std::string::npos;}};
 HANDLE firstDone=CreateEventW(nullptr,TRUE,FALSE,nullptr),allowFirstExit=CreateEventW(nullptr,TRUE,FALSE,nullptr);check(firstDone&&allowFirstExit,"owned test events");
 std::thread first([&]{work();SetEvent(firstDone);if(mode=="two-workers")check(WaitForSingleObject(allowFirstExit,5000)==WAIT_OBJECT_0,"bounded first worker lifetime");});check(WaitForSingleObject(firstDone,5000)==WAIT_OBJECT_0,"first callback finished");if(mode!="two-workers")first.join();auto r=adapter.Snapshot();
 if(mode=="two-workers"){
   check(r.reward_completed==1&&f.ctors==1&&f.dtors==1,"first worker owner gone on return");const auto firstThread=r.last_executor_thread;
   f.command.nonce[0]=38;check(adapter.Submit(c.binding,2,f.command),"second scope fresh value command");std::thread second(work);second.join();r=adapter.Snapshot();check(r.reward_completed==2&&r.reward_destroyed==2&&r.context_destroyed==2&&f.ctors==2&&f.dtors==2,"each actual worker creates and frees own context/list");check(firstThread&&r.last_executor_thread&&firstThread!=r.last_executor_thread,"two simultaneously alive workers have distinct actual executor IDs");SetEvent(allowFirstExit);first.join();
 }
 CloseHandle(firstDone);CloseHandle(allowFirstExit);
 if(mode=="hold-during-body"){check(localBodies==1&&!r.covered_user_scope_held&&value==0xABCDEF1234567890ull,"inflight original forwarded and cannot count as skip");std::thread next(work);next.join();r=adapter.Snapshot();check(r.covered_user_scope_held&&r.suppressed==1,"next true suppressed scope supplies hold receipt");}
 if(mode=="body-exception"||mode=="reward-exception")check(caught&&r.stopped&&r.active==0&&!r.covered_user_scope_drained,"actual exception finally drains scope without granting held receipt");
 else if(mode=="unowned-call")check(r.stopped&&localBodies==1&&!f.bodies&&!r.covered_user_scope_held,"unowned caller cannot suppress or replay");
 else if(mode=="phase-reject"||mode=="menu-reject"||mode=="production-target-reject")check(r.stopped&&localBodies==1&&!r.covered_user_scope_held,"nonidle state forwards without business admission");
 else if(mode=="forward-only")check(localBodies==1&&r.suppressed==0&&!r.covered_user_scope_held&&value==0xABCDEF1234567890ull,"default forward never invents hold");
 else if(mode=="open-reward")check(localBodies==1&&f.bodies==1&&value==0xABCDEF1234567890ull&&!r.covered_user_scope_held,"ordinary wrapper preserves RAX and synchronously owns reward");
 else if(mode=="cancel-before"||mode=="release-during-reward")check(!r.gate_requested&&!r.release_pending&&!r.covered_user_scope_held&&r.active==0,"release only complete after actual scope finally");
 else if(mode=="disconnect-before"||mode=="disconnect-during-reward")check(r.stopped&&!r.covered_user_scope_drained&&r.active==0,"disconnect never grants full drain");
 else check(r.covered_user_scope_held&&r.covered_user_scope_drained&&(mode=="hold-during-body"?localBodies==1:!localBodies),"actual User-subset suppression and own-scope drain");
 if(mode=="drain"){
   check(adapter.Request(c.binding,dp::Action::Drain,2),"explicit drain request");check(!adapter.Submit(c.binding,2,f.command),"drain rejects later queue arrivals");check(!adapter.Snapshot().covered_user_scope_drained,"new action invalidates old receipt");std::thread next(work);next.join();r=adapter.Snapshot();check(r.covered_user_scope_drained&&r.hold_revision==r.revision,"new real scope matches drain revision");
 }
 check(!r.full_input_hold&&!r.room_ack_eligible&&!r.installed_in_game&&!r.all_game_threads_paused,"subset never promotes full authority");
 check(f.ctors==f.dtors&&f.nodes.empty(),"synchronous ownership no native list leak");
 CheckpointPersistentBridgeStats stats{};check(CheckpointPersistentBridgeSnapshot(0,&stats)==1&&stats.active==0&&stats.cleanup_faults==0,"real physical bridge finally clean");if(mode!="unowned-call")check(stats.finally_calls==r.finally_calls&&r.active==0,"all bridge scopes accounted");
 std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"physical_finally\":%llu,\"reward_scopes\":%llu,\"native_ctor\":%u,\"native_dtor\":%u,\"full_input_hold\":false,\"game_access\":false}\n",mode.c_str(),stats.finally_calls,r.reward_scopes,f.ctors,f.dtors);return 0;
}catch(const std::exception&e){std::printf("{\"result\":\"FAIL\",\"case\":\"%s\",\"reason\":\"%s\"}\n",mode.c_str(),e.what());return 1;}}
