#include "planning_input_resident.h"
#include "planning_period_session.h"
#include "planning_input_resident_profile.h"
#include "planning_input_resident_base.inc"
#include <atomic>
namespace pb=planning_input_resident;namespace pp=planning_period_owner;
namespace ps=planning_period_session;
static ps::Session*localSession=new ps::Session;static ps::Scope localScope{};
static pb::Boundary*resident=new pb::Boundary;
static HWND ownWindow=nullptr;static HANDLE windowReady=nullptr,pauseEntered=nullptr,pauseRelease=nullptr;
static std::atomic<bool> windowInitialized{false},bodyIdentity{true};
static std::atomic<unsigned> bodyAudited{0};
static constexpr UINT Barrier=WM_APP+42,Pause=WM_APP+43,Replace=WM_APP+44;
static LRESULT CALLBACK ForeignWnd(HWND h,UINT m,WPARAM w,LPARAM l){return CallWindowProcA(reinterpret_cast<WNDPROC>(b+0x5122F0),h,m,w,l);}
void PlanningInputResidentBeforePublish(HWND h,bool retiring){(void)retiring;if(mode=="resident-race-install"){std::thread t([h]{SetWindowLongPtrA(h,GWLP_WNDPROC,LONG_PTR(&ForeignWnd));});t.join();}}
static LRESULT NativeWindowBody(uintptr_t engine,HWND h,UINT m,WPARAM w,LPARAM l){
 if(engine!=b+0x19055D0)bodyIdentity=false;
 if(m==Pause){SetEvent(pauseEntered);WaitForSingleObject(pauseRelease,5000);return 0;}
 if(m==Replace)return SetWindowLongPtrA(h,GWLP_WNDPROC,LONG_PTR(&ForeignWnd))?1:0;
 if(m==Barrier)return LRESULT(w)^l;
 if(m==WM_KEYDOWN||m==WM_KEYUP||m==WM_MOUSEMOVE){++bodyAudited;return 17;}
 if(m==WM_DESTROY)PostQuitMessage(0);return DefWindowProcA(h,m,w,l);
}
static DWORD WINAPI windowThread(void*){
 WNDCLASSEXA c{};c.cbSize=sizeof c;c.lpfnWndProc=reinterpret_cast<WNDPROC>(b+0x5122F0);c.hInstance=GetModuleHandleW(nullptr);c.lpszClassName="OwnedPlanningResidentFixture";
 if(!RegisterClassExA(&c)){SetEvent(windowReady);return 1;}
 ownWindow=CreateWindowExA(0,c.lpszClassName,"",0,0,0,0,0,HWND_MESSAGE,nullptr,c.hInstance,nullptr);
 if(!ownWindow){SetEvent(windowReady);return 2;}
 put<uintptr_t>(b+0x19055D0+0x18,uintptr_t(ownWindow));pb::Config cc{};cc.controller=&interlock;cc.owner=session;cc.binding=rd->binding;cc.base=b;cc.window=ownWindow;
 windowInitialized=resident->Initialize(cc);SetEvent(windowReady);MSG m{};while(GetMessageA(&m,nullptr,0,0)>0){TranslateMessage(&m);DispatchMessageA(&m);}return 0;
}
static bool awaitAck(){for(unsigned n=0;n<200;++n){pb::Report r{};resident->Snapshot(r);if(r.acknowledged)return true;if(r.error!=pb::Error::None)return false;Sleep(5);}return false;}
static void probe(const char*what){const auto count=bodyAudited.load();check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0)==0&&bodyAudited.load()==count,what);}
static int residentCases(){
 DWORD old=0;memcpy(reinterpret_cast<void*>(b+0x5122F0),BoundaryWndBytes,sizeof BoundaryWndBytes);jump(b+0x510BE0,reinterpret_cast<void*>(&NativeWindowBody));put<uintptr_t>(b+0x123C928,uintptr_t(&GetWindowLongA));
 check(VirtualProtect(reinterpret_cast<void*>(b+0x510000),0x3000,PAGE_EXECUTE_READ,&old)!=0,"archived WndProc RX");
 windowReady=CreateEventW(nullptr,TRUE,FALSE,nullptr);pauseEntered=CreateEventW(nullptr,TRUE,FALSE,nullptr);pauseRelease=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 auto thread=CreateThread(nullptr,0,windowThread,nullptr,0,nullptr);check(thread&&WaitForSingleObject(windowReady,5000)==WAIT_OBJECT_0,"real separate window thread ready");pb::Report before{},after{};resident->Snapshot(before);
 if(mode=="resident-race-install"){
  check(!windowInitialized&&before.publicationConflict&&before.foreignSourceMayHaveBeenReplaced&&before.uncertain&&!before.acknowledged,"actual initial publisher race stays uncertain");
 }else if(!windowInitialized){check(false,"resident initialize");fprintf(stderr,"init error=%u\n",unsigned(before.error));}
 else {
  bool duplicate=false;check(requestFence(true,1,duplicate)&&!resident->Request(true,1,duplicate),"setter alone not window evidence");check(observeFence(1)&&resident->Request(true,1,duplicate)&&awaitAck(),"initial actual Game User and window ACK");
  probe("old period audited input held");resident->Snapshot(before);const auto physical=GetWindowLongPtrA(ownWindow,GWLP_WNDPROC);const auto oldBinding=rd->binding;
  auto*next=new planning_input_interlock::Controller;pp::Receipt retired{};
  if(mode=="resident-callback-source"){
   put<uintptr_t>(b+0x19055D0+0x18,uintptr_t(ownWindow)+1);
   probe("actual callback source failure does not release established audited hold");
   resident->Snapshot(after);check(after.error==pb::Error::Identity&&after.uncertain&&after.held&&!after.residentHold&&!after.acknowledged,"identity error invalidates evidence without clearing held bit");
   probe("subsequent audited key still stopped after error");check(!resident->Request(false,2,duplicate),"failed boundary cannot accept release request");
  }else if(mode=="resident-unretired"){
   check(!resident->Handoff(interlock,oldBinding,1,1,duplicate),"unretired same Controller cannot handoff");probe("unretired refusal keeps input held");
  }else{
   check(mode=="resident-session"?localSession->Retire(localScope,retired):pp::Retire(*session,*input,interlock,oldBinding,retired),"formal old period retirement under held window");
   resident->Snapshot(after);check(!after.acknowledged&&after.residentHold&&after.held,"retired Controller invalid receipt never releases physical hold");probe("actual message held between retire and rebind");
   check(!resident->Request(false,2,duplicate)&&!interlock.Request(false,2,duplicate),"retired old Controller cannot release");
   ps::Next mapped{};
   if(mode=="resident-session"){auto nextScope=localScope;nextScope.period=2;nextScope.timelineEpoch[15]=2;nextScope.scopeDigest[31]=19;nextScope.date.day=21;check(localSession->PlanNext(nextScope,mapped),"trusted local session plans next native binding");rd->binding=mapped.binding;}
   else {++rd->binding.period;++rd->binding.epoch;rd->binding.room_input_digest[0]=19;}
   put<unsigned char>(world+0x37,mode=="resident-date"?1:21);
   ar::Config nc{};nc.binding=rd->binding;nc.sample=RewardData::sample;
   if(mode=="resident-date"){
    check(!pp::Rebind(*session,*input,nc,retired.serial)&&!resident->Handoff(*next,rd->binding,retired.serial,2,duplicate),"wrong date never handoffs");probe("wrong date leaves old audited hold");
   }else{
    check(mode=="resident-session"?localSession->Rebind(mapped,nc):pp::Rebind(*session,*input,nc,retired.serial),"formal next period rebind without window release");
    planning_input_interlock::Config cc{};cc.owner=session;cc.gate=input;cc.binding=rd->binding;cc.base=b;cc.root=root;cc.world=world;check(next->Initialize(cc),"new Controller claims current period");if(mode=="resident-session")check(localSession->Adopt(*next),"trusted session adopts actual next Controller");probe("actual held input after Rebind before new observation");
    check(next->Request(true,2,duplicate),"new Controller holds at cumulative revision two");
    if(mode=="resident-unobserved"){
     check(!resident->Handoff(*next,rd->binding,retired.serial,2,duplicate),"unobserved setter refuses handoff");probe("missing observation keeps physical hold");
    }else{
     check(next->BeginObservation(2),"new Controller observation begins");check(gameDispatch()==0&&rewardDispatch()==0,"actual new period Game and User callbacks");check(next->EndObservation(2),"actual new Controller observation completes");
     if(mode=="resident-binding"){
      auto wrong=rd->binding;++wrong.native.owner_generation;check(!resident->Handoff(*next,wrong,retired.serial,2,duplicate),"wrong binding refuses handoff");probe("wrong binding does not release");
     }else if(mode=="resident-old-controller"){
      check(!resident->Handoff(interlock,rd->binding,retired.serial,2,duplicate),"old Controller cannot claim new binding");probe("old Controller rejection keeps hold");
     }else if(mode=="resident-source"){
      check(SendMessageA(ownWindow,Replace,0,0)==1,"fixture foreign publisher really changed WndProc");check(!resident->Handoff(*next,rd->binding,retired.serial,2,duplicate),"unknown source rejects handoff without Set");resident->Snapshot(after);check(!after.residentHold&&!after.acknowledged&&GetWindowLongPtrA(ownWindow,GWLP_WNDPROC)==LONG_PTR(&ForeignWnd),"unknown source no receipt and not overwritten");
     }else{
      // Pause inside a real owned callback: queued Handoff cannot falsely ACK.
      check(PostMessageA(ownWindow,Pause,0,0)&&WaitForSingleObject(pauseEntered,5000)==WAIT_OBJECT_0,"window callback paused before control delivery");
      check(resident->Handoff(*next,rd->binding,retired.serial,2,duplicate)&&!duplicate,"handoff queued once");resident->Snapshot(after);
      check(after.handoffPending&&!after.acknowledged&&after.handoffsAccepted==1&&!after.handoffsAcknowledged&&after.held,"setter has no window ACK while callback blocked");
      check(resident->Handoff(*next,rd->binding,retired.serial,2,duplicate)&&duplicate,"pending duplicate does not repost");
      SetEvent(pauseRelease);check(awaitAck(),"actual same resident window callback acknowledges new binding");probe("new period actual input held with no release/reinstall");resident->Snapshot(after);
      check(after.serial==2&&after.period==2&&after.epoch==rd->binding.epoch&&after.revision==2&&after.handoffsAcknowledged==1&&after.publicationWrites==1&&after.callbackSlot==before.callbackSlot&&GetWindowLongPtrA(ownWindow,GWLP_WNDPROC)==physical,"one physical window bridge spans two formal periods");
      check(resident->Handoff(*next,rd->binding,retired.serial,2,duplicate)&&duplicate,"completed duplicate keeps cumulative identity");
      check(!resident->Handoff(*next,oldBinding,retired.serial,2,duplicate)&&!resident->Handoff(*next,rd->binding,retired.serial,1,duplicate),"old binding and late revision rejected");
      bool accepted=true;std::thread wrongThread([&]{bool d=false;accepted=resident->Handoff(*next,rd->binding,retired.serial,2,d);});wrongThread.join();check(!accepted,"wrong execution thread denied");
     }
    }
   }
  }
  resident->Snapshot(after);check(after.publicationWrites==1&&!after.allInputHeld&&!after.fullWindowInputHeld&&!after.roomReady&&!after.saveAuthorized&&!after.nativeGameplayEnabled&&!after.physicalReleaseProven&&!after.osQueueDrained,"no reinstall or full-input permit");
 }
 SetEvent(pauseRelease);if(ownWindow)check(PostMessageA(ownWindow,WM_CLOSE,0,0)&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"normal lifecycle teardown");check(bodyIdentity,"real archive preserves engine ABI");
 resident->Snapshot(after);check(!after.active&&after.finally>0&&after.handoffsAccepted==((mode=="resident-normal"||mode=="resident-session")?1u:0u)&&after.handoffsAcknowledged==((mode=="resident-normal"||mode=="resident-session")?1u:0u),"no active scope or extra handoff after normal close");CloseHandle(thread);CloseHandle(windowReady);CloseHandle(pauseEntered);CloseHandle(pauseRelease);
 printf("{\"result\":\"%s\",\"case\":\"%s\",\"checks\":%u,\"failures\":%u,\"publication_writes\":%llu,\"handoffs_accepted\":%llu,\"handoffs_acknowledged\":%llu,\"audited_suppressed\":%llu,\"audited_forwarded\":%llu,\"body_audited\":%u,\"finally\":%llu,\"active\":%llu,\"all_input_held\":false,\"save_authorized\":false}\n",failed?"FAIL":"PASS",mode.c_str(),passed,failed,after.publicationWrites,after.handoffsAccepted,after.handoffsAcknowledged,after.auditedSuppressed,after.auditedForwarded,bodyAudited.load(),after.finally,after.active);return failed?1:0;
}
int main(int argc,char**argv){SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;if(mode=="resident-session"){
  localScope.room[0]=1;localScope.bindingEpoch[0]=2;localScope.timelineEpoch[15]=1;localScope.scopeDigest[31]=18;localScope.period=1;localScope.date={203,8,11,12};
  check(ps::MakeBinding(localScope,cfg.input_binding,1,data.binding),"explicit fixture scope maps full native binding");
 }if(mode=="worker-b")put<unsigned char>(world+0x3A,2);check(session->Initialize(cfg)&&session->Arm(),"single actual User/Save owner");ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);check(input->Initialize(ic)&&input->PreparedPlan(plan),"upstream gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1),"same existing upstream held boundary");check(gameDispatch()==0,"actual Game boundary observed before Save");ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;check(ar::Bind(*session,rc),"reward lane binds exact same owner");originalViewer=get<unsigned char>(world+0x3A);planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;check(interlock.Initialize(pc),"unified exact existing Owner and Gate");if(mode=="resident-session")check(localSession->Initialize(*session,*input,interlock,localScope,rc,b,root,world),"trusted session binds actual physical Owner before window init");return failed?1:residentCases();}
