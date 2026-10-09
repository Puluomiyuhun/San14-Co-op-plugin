#include "player_input_owner.h"
#include "player_input_owner_profile.h"
#include "player_input_owned_base.inc"
#include <atomic>
namespace po=player_input_owner;namespace pol=player_input_policy;
static po::Owner*policyOwner=new po::Owner;
static pol::Binding policyBinding{};static DWORD executionThread=0;
static HWND ownWindow=nullptr;static HANDLE windowReady=nullptr,pauseEntered=nullptr,pauseRelease=nullptr;
static std::atomic<bool>windowInitialized{false},bodyIdentity{true};
static std::atomic<unsigned>bodyAudited{0},bodyLifecycle{0},bodyUnknown{0};
static constexpr UINT Barrier=WM_APP+42,Pause=WM_APP+43,Replace=WM_APP+44;
static LRESULT CALLBACK ForeignWnd(HWND h,UINT m,WPARAM w,LPARAM l){return CallWindowProcA(reinterpret_cast<WNDPROC>(b+0x5122F0),h,m,w,l);}
void PlayerInputBeforePublish(HWND h){if(mode=="policy-publish-race"){std::thread t([h]{SetWindowLongPtrA(h,GWLP_WNDPROC,LONG_PTR(&ForeignWnd));});t.join();}}
static LRESULT NativeWindowBody(uintptr_t engine,HWND h,UINT m,WPARAM w,LPARAM l){
 if(engine!=b+0x19055D0)bodyIdentity=false;
 if(m==Pause){SetEvent(pauseEntered);WaitForSingleObject(pauseRelease,5000);return 0;}
 if(m==Replace)return SetWindowLongPtrA(h,GWLP_WNDPROC,LONG_PTR(&ForeignWnd))?1:0;
 if(m==Barrier||m==WM_MOUSEWHEEL){++bodyUnknown;return 31;}
 if(m==WM_KEYDOWN||m==WM_KEYUP||m==WM_LBUTTONDOWN||m==WM_MOUSEMOVE){++bodyAudited;return 17;}
 if(m==WM_TIMER){++bodyLifecycle;return 23;}
 if(m==WM_DESTROY)PostQuitMessage(0);return DefWindowProcA(h,m,w,l);
}
static DWORD WINAPI windowThread(void*){
 WNDCLASSEXA c{};c.cbSize=sizeof c;c.lpfnWndProc=reinterpret_cast<WNDPROC>(b+0x5122F0);c.hInstance=GetModuleHandleW(nullptr);c.lpszClassName="OwnedPlayerInputPolicyFixture";
 if(!RegisterClassExA(&c)){SetEvent(windowReady);return 1;}
 ownWindow=CreateWindowExA(0,c.lpszClassName,"",0,0,0,0,0,HWND_MESSAGE,nullptr,c.hInstance,nullptr);
 if(!ownWindow){SetEvent(windowReady);return 2;}
 put<uintptr_t>(b+0x19055D0+0x18,uintptr_t(ownWindow));po::Config cc{};cc.base=b;cc.window=ownWindow;cc.ownerThread=executionThread;
 cc.binding=policyBinding;cc.rewardOwner=session;cc.rewardBinding=rd->binding;
 windowInitialized=policyOwner->Initialize(cc);SetEvent(windowReady);MSG m{};
 while(GetMessageA(&m,nullptr,0,0)>0){TranslateMessage(&m);DispatchMessageA(&m);}return 0;
}
static bool awaitAck(std::uint64_t revision){for(unsigned n=0;n<200;++n){po::Report r{};policyOwner->Snapshot(r);if(r.acknowledged&&r.acknowledgedRevision==revision)return true;if(r.error!=po::Error::None)return false;Sleep(5);}return false;}
static void probe(const char*what){const auto count=bodyAudited.load();check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0)==0&&bodyAudited.load()==count,what);}
static bool phase(pol::Phase value,bool ready,std::uint64_t revision){bool duplicate=false;return policyOwner->Request(policyBinding,{value,ready},revision,duplicate)&&awaitAck(revision);}
static int policyCases(){
 DWORD old=0;memcpy(reinterpret_cast<void*>(b+0x5122F0),BoundaryWndBytes,sizeof BoundaryWndBytes);jump(b+0x510BE0,reinterpret_cast<void*>(&NativeWindowBody));put<uintptr_t>(b+0x123C928,uintptr_t(&GetWindowLongA));
 check(VirtualProtect(reinterpret_cast<void*>(b+0x510000),0x3000,PAGE_EXECUTE_READ,&old)!=0,"archive WndProc RX");
 windowReady=CreateEventW(nullptr,TRUE,FALSE,nullptr);pauseEntered=CreateEventW(nullptr,TRUE,FALSE,nullptr);pauseRelease=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 executionThread=GetCurrentThreadId();policyBinding.room[0]=1;policyBinding.attachment[0]=2;policyBinding.epoch[0]=3;policyBinding.period=1;policyBinding.seat=0;
 auto thread=CreateThread(nullptr,0,windowThread,nullptr,0,nullptr);check(thread&&WaitForSingleObject(windowReady,5000)==WAIT_OBJECT_0,"real HWND thread");po::Report r{};policyOwner->Snapshot(r);
 if(mode=="policy-publish-race")check(!windowInitialized&&r.uncertain&&r.publicationConflict&&r.foreignSourceMayHaveBeenReplaced,"known non-CAS install race fails closed");
 else if(!windowInitialized){check(false,"native window policy initialize");fprintf(stderr,"init=%u\n",unsigned(r.error));}
 else {
  probe("initial pending policy does not expose audited input");
  check(phase(pol::Phase::Planning,false,1),"actual open policy ACK");
  check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0)==17,"ordinary planning actually forwards local input");
  bool duplicate=false;
  if(mode=="policy-pending"){
   check(PostMessageA(ownWindow,Pause,0,0)&&WaitForSingleObject(pauseEntered,5000)==WAIT_OBJECT_0,"actual paused window callback");
   check(policyOwner->Request(policyBinding,{pol::Phase::Planning,true},2,duplicate),"ready request queued");policyOwner->Snapshot(r);
   check(r.pending&&!r.acknowledged&&r.held&&!r.remoteExecutionPolicyOpen,"pending is no ACK/admission");
   check(!policyOwner->SubmitRemoteReward(policyBinding,2,1,rd->command(2,1)),"no remote execution before policy delivery");
   check(policyOwner->Request(policyBinding,{pol::Phase::Planning,true},2,duplicate)&&duplicate,"same pending intent is idempotent");
   check(!policyOwner->Request(policyBinding,{pol::Phase::Planning,false},2,duplicate),"same-revision conflict refused");
   SetEvent(pauseRelease);check(awaitAck(2),"actual control callback completes ACK");
  }else check(phase(pol::Phase::Planning,true,2),"local Ready applied");
  probe("local Ready actually blocks Enter");policyOwner->Snapshot(r);
  check(!r.localCommandPolicyOpen&&r.remoteMessagesAllowed&&r.remoteExecutionPolicyOpen,"local Ready does not stop remote planning lane");
  if(mode=="policy-binding"){
   auto stale=policyBinding;++stale.period;
   check(!policyOwner->Request(stale,{pol::Phase::Planning,false},3,duplicate)&&!policyOwner->SubmitRemoteReward(stale,2,1,rd->command(2,1)),"foreign period denied");
   check(!policyOwner->Request(policyBinding,{pol::Phase::Planning,false},1,duplicate)&&!policyOwner->Request(policyBinding,{pol::Phase::Planning,false},4,duplicate),"old and skipped revisions denied");
  }else if(mode=="policy-thread"){
   bool accepted=true;std::thread other([&]{bool d=false;accepted=policyOwner->Request(policyBinding,{pol::Phase::Planning,false},3,d)||policyOwner->SubmitRemoteReward(policyBinding,2,1,rd->command(2,1));});other.join();check(!accepted,"foreign thread cannot release or submit");
  }else if(mode=="policy-source"){
   check(SendMessageA(ownWindow,Replace,0,0)==1,"external source replacement");policyOwner->Snapshot(r);
   check(!r.acknowledged&&r.uncertain&&!policyOwner->SubmitRemoteReward(policyBinding,2,1,rd->command(2,1)),"foreign window source revokes evidence and remote lane");
   check(GetWindowLongPtrA(ownWindow,GWLP_WNDPROC)==LONG_PTR(&ForeignWnd),"foreign source never overwritten");
  }else if(mode=="policy-callback-source"){
   put<uintptr_t>(b+0x19055D0+0x18,uintptr_t(ownWindow)+1);probe("callback identity error preserves physical audited hold");policyOwner->Snapshot(r);
   check(r.uncertain&&!r.acknowledged&&r.held&&!policyOwner->Request(policyBinding,{pol::Phase::Planning,false},3,duplicate),"source error never releases");probe("later input remains blocked");
  }else {
   check(policyOwner->SubmitRemoteReward(policyBinding,2,1,rd->command(2,1)),"real existing Owner accepts remote reward while local Ready");
   if(mode=="policy-drain"){
    check(!policyOwner->Request(policyBinding,{pol::Phase::Save,false},3,duplicate),"queued reward denies critical-phase transition");
    policyOwner->Snapshot(r);check(r.revision==2&&r.acknowledged&&r.held,"rejected transition preserves current Ready hold and revision");
    ar::Report queued{};ar::Snapshot(*session,queued);check(queued.queued&&queued.submitted==1&&!queued.completed,"existing native request is retained, not cancelled or replayed");
   }
   check(rewardDispatch()==0,"actual User callback executes queued remote reward");
   ar::Report reward{};ar::Snapshot(*session,reward);check(reward.completed==1&&rd->bodies==1&&!reward.readyFence&&!reward.readyRevision,"no old ReadyFence or fake receipt");
   std::uint64_t revision=3;
   for(auto value:{pol::Phase::Save,pol::Phase::Load,pol::Phase::EventWait,pol::Phase::Running}){
    check(phase(value,false,revision),"phase updates real window policy");probe("phase blocks audited local commands");policyOwner->Snapshot(r);
    check(r.remoteMessagesAllowed&&!r.remoteExecutionPolicyOpen&&!policyOwner->SubmitRemoteReward(policyBinding,revision,2,rd->command(12,2)),"keep network reception but block execution during critical phase");
    check(SendMessageA(ownWindow,WM_TIMER,0,0)==23,"timer/lifecycle still progresses during critical phase");
    check(SendMessageA(ownWindow,WM_MOUSEWHEEL,0,0)==31,"uncovered wheel explicitly remains forwarded");++revision;
   }
   if(mode=="policy-terminal"){
    check(phase(pol::Phase::Terminal,false,revision),"explicit terminal policy");policyOwner->Snapshot(r);
    check(!r.remoteMessagesAllowed&&!r.remoteExecutionPolicyOpen&&!policyOwner->Request(policyBinding,{pol::Phase::Planning,false},revision+1,duplicate),"terminal cannot reopen");
   }else{
    check(phase(pol::Phase::Planning,false,revision),"explicit local release after critical phases");
    check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0)==17,"actual input restored");
    check(policyOwner->SubmitRemoteReward(policyBinding,revision,2,rd->command(12,2))&&rewardDispatch()==0,"rejections did not consume native sequence");
    ar::Snapshot(*session,reward);check(reward.completed==2&&reward.created==2&&reward.destroyed==2&&rd->bodies==2,"two actual reward lifetimes complete");
   }
  }
 }
 SetEvent(pauseRelease);if(ownWindow)check(PostMessageA(ownWindow,WM_CLOSE,0,0)&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"normal close forwards window lifecycle");
 policyOwner->Snapshot(r);check(!r.active&&r.finally&&r.publicationWrites==1&&bodyIdentity&&!r.allInputHeld&&!r.gameReportWhitelistVerified&&!r.saveAuthorized&&!r.roomReady,"finite coverage and one publication only");
 CloseHandle(thread);CloseHandle(windowReady);CloseHandle(pauseEntered);CloseHandle(pauseRelease);
 printf("{\"result\":\"%s\",\"case\":\"%s\",\"checks\":%u,\"failures\":%u,\"suppressed\":%llu,\"forwarded\":%u,\"lifecycle\":%u,\"reward_bodies\":%u,\"finally\":%llu,\"active\":%llu,\"all_input_held\":false,\"game_report_whitelist_verified\":false}\n",failed?"FAIL":"PASS",mode.c_str(),passed,failed,r.suppressed,bodyAudited.load(),bodyLifecycle.load(),rd->bodies,r.finally,r.active);return failed?1:0;
}
int main(int argc,char**argv){SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;check(session->Initialize(cfg)&&session->Arm(),"real retained User/Save owner");ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);check(input->Initialize(ic)&&input->PreparedPlan(plan),"existing upstream gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1)&&gameDispatch()==0,"actual preexisting native boundary");ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;check(ar::Bind(*session,rc),"exact native reward lane");originalViewer=get<unsigned char>(world+0x3A);return failed?1:policyCases();}
