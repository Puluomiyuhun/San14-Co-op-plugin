#include "checkpoint_ready_input_gate.h"
#include "checkpoint_planning_dispatcher_fixture_support.inc"
namespace dp=checkpoint_planning_dispatcher;namespace ri=checkpoint_ready_input;
extern "C" {std::uintptr_t ReadyFixtureUi=0,ReadyFixtureGame=0;
std::uint64_t ReadyFixtureGameBody(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
void ReadyFixtureGlobalReturn();void ReadyFixturePanelReturn();}
static RewardWorld*fxt=nullptr;static dp::Dispatcher*ud=nullptr;static ri::Gate*gate=nullptr;
static unsigned uiBodies=0,panelBodies=0,menuEffects=0,userBodies=0;
static std::uint64_t originalUi(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){++uiBodies;check(a==ReadyFixtureUi&&b==0x12345678&&c==0x23456789&&d==0x3456789a,"global UI exact opaque integer args");if(mode=="ui-exception")throw std::runtime_error("ui-original-exception");if(mode=="ui-posts-panel")put<unsigned>(fxt->planning.panel.data(),0x1b0,4);return 0xFEDCBA9876543210ull;}
static std::uint64_t originalPanel(std::uint64_t a,std::uint64_t,std::uint64_t,std::uint64_t){++panelBodies;check(a==ReadyFixtureGame,"actual parent game object");if(get<unsigned>(fxt->planning.panel.data(),0x1b0)){++menuEffects;put<unsigned>(fxt->planning.panel.data(),0x1b0,0);}return 0xFEDCBA9876543210ull;}
static std::uint64_t originalUser(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){++userBodies;return 0x13572468;}
static int originalReward(ph::RewardArgs*a){++fxt->bodies;check(a->funding==fxt->addr(fxt->city.data())&&fxt->counts[fxt->handle]==2&&fxt->nodes.size()==2,"real RewardOwned callback retains list");return 1;}
static bool sampleUser(void*p,std::uintptr_t user,dp::Source&out){auto&f=*static_cast<RewardWorld*>(p);if(user!=f.config.user)return false;out.reward=f.config;out.admission=f.planning.config;return true;}
static bool sampleGate(void*p,dp::Source&out){return sampleUser(p,static_cast<RewardWorld*>(p)->config.user,out);}
static std::uint64_t gameEntry(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return gate->Game(a,b,c,d);}
static std::uint64_t userEntry(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return ud->Invoke(a,b,c,d);}
static auto gameCall(){return CheckpointPersistentBridge2(ReadyFixtureGame,0,0,0);}
static auto userCall(){return CheckpointPersistentBridge0(fxt->config.user,0,0,0);}
int main(int argc,char**argv){if(argc!=2)return 2;mode=argv[1];try{RewardWorld f;fxt=&f;check(RewardOwnedDestroy(f.owner),"release setup-only owner");f.owner=nullptr;f.planning.config.reward=&originalReward;
 ReadyFixtureUi=f.base()+0x1fc8410;ReadyFixtureGame=f.addr(f.planning.game.data());put(reinterpret_cast<void*>(ReadyFixtureUi),0,f.base()+0x1297cf8);
 dp::Dispatcher dispatcher;ud=&dispatcher;dp::Config dc{};dc.binding=f.config.binding;dc.original=&originalUser;dc.mode=dp::Mode::UserSubsetSkip;dc.claim=&CheckpointPersistentClaim;dc.current_owner=&CheckpointPersistentCurrentOwner;dc.sample=&sampleUser;dc.context=&f;check(dispatcher.Initialize(dc),"actual frozen dispatcher initialize");
 ri::Gate input;gate=&input;check(ri::ConfigureFallbacks(&originalUi,&originalPanel),"immutable raw originals configured before entries");ri::Config gc{};gc.binding=dc.binding;gc.base=f.base();gc.user=&dispatcher;gc.game=&ReadyFixtureGameBody;gc.global_ui=&originalUi;gc.panel=&originalPanel;gc.claim=&CheckpointPersistentClaim;gc.current_owner=&CheckpointPersistentCurrentOwner;gc.sample=&sampleGate;gc.context=&f;
#ifdef CHECKPOINT_READY_INPUT_OWNED_FIXTURE
 gc.fixture_global_return=reinterpret_cast<std::uintptr_t>(&ReadyFixtureGlobalReturn);gc.fixture_panel_return=reinterpret_cast<std::uintptr_t>(&ReadyFixturePanelReturn);
#endif
 if(mode=="production-reject"){check(!input.Initialize(gc),"production rejects fixture body addresses");std::puts("{\"result\":\"PASS\",\"case\":\"production-reject\",\"game_access\":false}");return 0;}check(input.Initialize(gc),"parent input gate initialize");
 CheckpointPersistentBridgeConfig bc{};bc.original=reinterpret_cast<void*>(&gameEntry);bc.before=&ri::Gate::BeforeCallback;bc.finally=&ri::Gate::FinallyCallback;bc.context=&input;check(CheckpointPersistentBridgeConfigure(2,&bc)==1,"real parent Game bridge");bc.original=reinterpret_cast<void*>(&userEntry);bc.before=&dp::Dispatcher::BeforeCallback;bc.finally=&dp::Dispatcher::FinallyCallback;bc.context=&dispatcher;check(CheckpointPersistentBridgeConfigure(0,&bc)==1,"real User bridge");
 bool open=mode=="open"||mode=="ui-posts-panel"||mode=="ui-exception";if(!open)check(input.Request(dc.binding,dp::Action::Hold,1),"single Hold closes all three scoped consumers");
 if(mode=="held-reward")check(dispatcher.Submit(dc.binding,1,f.command),"queue remote reward while local held");
 if(mode=="disconnect")input.Disconnect();
 if(mode=="phase-drift")put<unsigned>(f.planning.user.data(),0x470,5);
 if(mode=="menu-pending")put<int>(f.planning.toolbar.data(),0x88,13);
 if(mode=="late-panel")put<unsigned>(f.planning.panel.data(),0x1b0,4);
 if(mode=="wrong-binding"){auto wrong=dc.binding;++wrong.period;check(!input.Request(wrong,dp::Action::Drain,2),"foreign round refused");}
 bool caught=false;try{check(gameCall()==0xABCDEF1234567890ull,"Game body always runs and full RAX retained");}catch(const std::runtime_error&e){caught=std::string(e.what())=="ui-original-exception";}
 if(!caught)userCall();auto r=input.Snapshot();auto u=dispatcher.Snapshot();
 if(mode=="ui-exception")check(caught&&r.stopped&&r.game_finally==1&&r.active_game==0,"parent actual exception FINALLY");
 else if(mode=="phase-drift"||mode=="menu-pending"||mode=="late-panel")check(r.stopped&&u.stopped&&uiBodies==1&&panelBodies==1&&!r.room_ready_eligible,"unknown/modal drift invalidates admission while preserving native handler");
 else if(open)check(uiBodies==1&&panelBodies==1&&userBodies==1&&r.ui_suppressed==0,"open retains parent UI and User");
 else check(uiBodies==0&&panelBodies==0&&userBodies==0&&r.ui_suppressed==1&&r.panel_suppressed==1,"all three audited local paths actually skipped");
 if(mode=="ui-posts-panel")check(menuEffects==1,"proven fixture parent bypass can post and consume without User");
 if(mode=="held-reward")check(f.bodies==1&&f.ctors==1&&f.dtors==1&&u.reward_completed==1,"User hold permits concrete trusted remote reward");
 if(mode=="release"){
 check(input.Request(dc.binding,dp::Action::Release,2),"release starts User cancellation first");gameCall();check(input.Snapshot().requested,"parent remains held before actual User release boundary");userCall();check(!dispatcher.Snapshot().gate_requested&&input.Snapshot().requested,"actual User finally first");gameCall();check(!input.Snapshot().requested,"parent finally then releases its gate");gameCall();userCall();check(uiBodies==1&&panelBodies==1&&userBodies==1,"only later originals resume");}
 r=input.Snapshot();u=dispatcher.Snapshot();check(!r.full_input_hold&&!r.room_ready_eligible&&!r.all_gameplay_consumers_covered&&!r.installed&&!u.room_ack_eligible,"no false complete Ready or install claims");CheckpointPersistentBridgeStats gameStats{},userStats{};check(CheckpointPersistentBridgeSnapshot(2,&gameStats)&&CheckpointPersistentBridgeSnapshot(0,&userStats)&&!gameStats.active&&!userStats.active&&!gameStats.cleanup_faults&&!userStats.cleanup_faults,"both actual bridge FINALLY scopes clean");
 std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"game_finally\":%llu,\"user_finally\":%llu,\"ui_suppressed\":%llu,\"panel_suppressed\":%llu,\"room_ready_eligible\":false,\"game_access\":false}\n",mode.c_str(),gameStats.finally_calls,userStats.finally_calls,r.ui_suppressed,r.panel_suppressed);return 0;
}catch(const std::exception&e){std::printf("{\"result\":\"FAIL\",\"case\":\"%s\",\"reason\":\"%s\"}\n",mode.c_str(),e.what());return 1;}}
