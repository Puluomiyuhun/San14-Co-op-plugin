#include "planning_input_boundary.h"
#ifdef PLANNING_INPUT_BOUNDARY_PERIOD_FIXTURE
#include "planning_period_owner.h"
#endif
#include "planning_input_boundary_profile.h"
#include "planning_input_boundary_base.inc"
#include <atomic>
namespace pb=planning_input_boundary;
static pb::Boundary*boundary=new pb::Boundary;
static HWND ownWindow=nullptr;
static HANDLE windowReady=nullptr;
static std::atomic<bool> windowInitialized{false},bodyIdentity{true};
static std::atomic<unsigned> bodyAudited{0},bodyUnknown{0},bodyWheel{0},bodyLifecycle{0};
static constexpr UINT Barrier=WM_APP+42,Rebind=WM_APP+43,Replace=WM_APP+44;
static pb::Boundary*replacement=nullptr;
static planning_input_interlock::Controller*windowController=&interlock;
static LRESULT CALLBACK ForeignWnd(HWND h,UINT m,WPARAM w,LPARAM l){return CallWindowProcA(reinterpret_cast<WNDPROC>(b+0x5122F0),h,m,w,l);}
// Deterministic owned-process counterexample to SetWindowLongPtr's lack of CAS.
void PlanningInputBoundaryBeforePublish(HWND h,bool retiring){
 if((retiring&&mode=="window-race-retire")||(!retiring&&mode=="window-race-install")){
  std::thread foreign([h]{SetWindowLongPtrA(h,GWLP_WNDPROC,LONG_PTR(&ForeignWnd));});foreign.join();
 }
}
static LRESULT NativeWindowBody(uintptr_t engine,HWND h,UINT m,WPARAM w,LPARAM l){
 if(engine!=b+0x19055D0)bodyIdentity=false;
 if(m==Rebind){pb::Config cc{};cc.controller=windowController;cc.base=b;cc.window=h;windowInitialized=replacement->Initialize(cc);return windowInitialized?1:0;}
 if(m==Replace){return SetWindowLongPtrA(h,GWLP_WNDPROC,LONG_PTR(&ForeignWnd))?1:0;}
 if(m==Barrier){++bodyUnknown;return LRESULT(w)^l;}
 if(m==WM_MOUSEWHEEL){++bodyWheel;return LRESULT(w)^l;}
 if(m==WM_KEYDOWN||m==WM_KEYUP||m==WM_LBUTTONDOWN||m==WM_LBUTTONUP||m==WM_MOUSEMOVE){++bodyAudited;
  if((m==WM_KEYDOWN||m==WM_KEYUP)&&w==VK_RETURN)PostMessageA(h,m==WM_KEYDOWN?WM_LBUTTONDOWN:WM_LBUTTONUP,0,0);
  return 17;
 }
 if(m==WM_DESTROY)PostQuitMessage(0);
 ++bodyLifecycle;return DefWindowProcA(h,m,w,l);
}
static DWORD WINAPI windowThread(void*){
 WNDCLASSEXA c{};c.cbSize=sizeof c;c.lpfnWndProc=reinterpret_cast<WNDPROC>(b+0x5122F0);c.hInstance=GetModuleHandleW(nullptr);c.lpszClassName="OwnedPlanningBoundaryFixture";
 if(!RegisterClassExA(&c)){SetEvent(windowReady);return 1;}
 ownWindow=CreateWindowExA(0,c.lpszClassName,"",0,0,0,0,0,HWND_MESSAGE,nullptr,c.hInstance,nullptr);
 if(!ownWindow){SetEvent(windowReady);return 2;}
 put<uintptr_t>(b+0x19055D0+0x18,uintptr_t(ownWindow));pb::Config cc{};cc.controller=windowController;cc.base=b;cc.window=ownWindow;
 windowInitialized=boundary->Initialize(cc);SetEvent(windowReady);
 MSG m{};for(;;){const auto got=GetMessageA(&m,nullptr,0,0);if(got<=0)break;TranslateMessage(&m);DispatchMessageA(&m);}return 0;
}
static bool awaitAck(pb::Boundary*value,bool retired=false){for(unsigned i=0;i<200;++i){pb::Report x{};value->Snapshot(x);if(retired?x.retirementAcknowledged:x.acknowledged)return true;if(x.error!=pb::Error::None)return false;Sleep(5);}return false;}
static int boundaryCases(){
 DWORD old=0;memcpy(reinterpret_cast<void*>(b+0x5122F0),BoundaryWndBytes,sizeof BoundaryWndBytes);jump(b+0x510BE0,reinterpret_cast<void*>(&NativeWindowBody));
 put<uintptr_t>(b+0x123C928,uintptr_t(&GetWindowLongA));
 check(VirtualProtect(reinterpret_cast<void*>(b+0x510000),0x3000,PAGE_EXECUTE_READ,&old)!=0,"archived window source RX");
 windowReady=CreateEventW(nullptr,TRUE,FALSE,nullptr);const auto thread=CreateThread(nullptr,0,windowThread,nullptr,0,nullptr);
 check(thread&&WaitForSingleObject(windowReady,5000)==WAIT_OBJECT_0,"actual window thread ready");
 if(mode=="window-race-install"){
  pb::Report x{};boundary->Snapshot(x);check(!windowInitialized&&!x.initialized&&x.uncertain&&x.publicationConflict&&x.foreignSourceMayHaveBeenReplaced&&!x.acknowledged,"actual concurrent publisher install conflict never ACKs");
  check(uintptr_t(GetWindowLongPtrA(ownWindow,GWLP_WNDPROC))!=uintptr_t(&ForeignWnd),"race counterexample: external source actually overwritten, not claimed CAS");
  check(PostMessageA(ownWindow,WM_CLOSE,0,0)&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"conflicted retained bridge forwards teardown");CloseHandle(thread);CloseHandle(windowReady);rewardSummary();return failed?1:0;
 }
 check(windowInitialized,"actual separate HWND thread installed boundary");
 if(!windowInitialized){pb::Report x{};boundary->Snapshot(x);fprintf(stderr,"boundary init error=%u\n",unsigned(x.error));if(ownWindow)PostMessageA(ownWindow,WM_CLOSE,0,0);if(thread)WaitForSingleObject(thread,5000);rewardSummary();return 1;}
 pb::Report before{},after{};boundary->Snapshot(before);check(before.windowThread!=GetCurrentThreadId()&&before.ownerThread==GetCurrentThreadId(),"distinct window and Owner threads");
 bool duplicate=false;check(requestFence(true,1,duplicate),"request Game/User fence");check(!boundary->Request(true,1,duplicate),"setter alone cannot publish HWND fence");check(observeFence(1),"actual Game/User observation");
 const bool requested=boundary->Request(true,1,duplicate);const bool ack=requested&&awaitAck(boundary);if(!ack){pb::Report z{};boundary->Snapshot(z);planning_input_interlock::Report y{};interlock.Snapshot(y);fprintf(stderr,"REQUEST=%u err=%u rev=%llu ack=%u held=%u init=%u installed=%u control=%llu ignored=%llu controller=%u observed=%u cover=%u\n",unsigned(requested),unsigned(z.error),z.revision,unsigned(z.acknowledged),unsigned(z.held),unsigned(z.initialized),unsigned(z.installed),z.controlCalls,z.ignoredControl,unsigned(y.error),unsigned(y.observed),y.coverage);}check(ack,"actual ordered window ACK");boundary->Snapshot(before);check(!before.auditedSuppressionObserved,"ACK alone not input observation");
 const auto native=bodyAudited.load();check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0x1122)==0,"actual key stopped before archived callee");
 check(SendMessageA(ownWindow,WM_MOUSEMOVE,0,0x3344)==0,"actual mouse stopped before archived callee");
 check(SendMessageA(ownWindow,Barrier,0x7654,0x1234)==(0x7654^0x1234),"unknown forwarded with exact args/return");
 check(SendMessageA(ownWindow,WM_MOUSEWHEEL,0x120,0x456)==(0x120^0x456),"uncovered wheel explicitly forwarded");
 std::thread producer([]{for(unsigned n=0;n<10;++n)PostMessageA(ownWindow,WM_KEYUP,VK_RETURN,0);PostMessageA(ownWindow,Barrier,0,0);});producer.join();
 for(unsigned i=0;i<200&&bodyUnknown.load()<2;++i)Sleep(5);
 boundary->Snapshot(after);check(after.auditedSuppressionObserved&&after.auditedSuppressed>=12&&bodyAudited.load()==native,"posted plus sent inputs truly suppressed");
 check(!after.fullWindowInputHeld&&!after.allInputHeld&&!after.physicalReleaseProven&&!after.osQueueDrained&&!after.roomReady&&!after.saveAuthorized&&!after.nativeGameplayEnabled,"no broader permit");
 check(boundary->Request(true,1,duplicate)&&duplicate,"same revision idempotent");boundary->Snapshot(before);SendMessageA(ownWindow,before.controlMessage,9999,9999);boundary->Snapshot(after);check(after.ignoredControl==before.ignoredControl+1&&after.ticket==before.ticket&&after.revision==1,"unowned control ignored");
 bool wrong=true;std::thread caller([&]{bool dup=false;wrong=boundary->Request(true,1,dup);});caller.join();check(!wrong,"foreign owner thread refused");
 if(mode=="window-foreign"){
  check(SendMessageA(ownWindow,Replace,0,0)==1,"owned fixture third party replaces WndProc");boundary->Snapshot(after);check(!after.acknowledged&&!boundary->Retire(1,duplicate),"foreign WndProc invalidates ACK and retirement");
  check(uintptr_t(GetWindowLongPtrA(ownWindow,GWLP_WNDPROC))==uintptr_t(&ForeignWnd),"unknown WndProc never overwritten");
 }else if(mode=="window-date"){
  put<unsigned char>(world+0x37,21);boundary->Snapshot(after);check(!after.acknowledged&&!boundary->Request(true,1,duplicate),"date drift invalidates boundary receipt");
 }else{
  check(requestFence(false,2,duplicate)&&boundary->Request(false,2,duplicate)&&awaitAck(boundary),"explicit release and window ACK");
  const auto count=bodyAudited.load();check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0)==17,"released archive WndProc forwards key");
  for(unsigned i=0;i<200&&bodyAudited.load()<count+2;++i)Sleep(5);check(bodyAudited.load()>=count+2,"explicit business double posted mouse now forwards");
  if(mode=="window-race-retire"){
   check(boundary->Retire(2,duplicate)&&!awaitAck(boundary,true),"retire publication race refuses ACK");boundary->Snapshot(after);
   check(after.uncertain&&after.publicationConflict&&after.foreignSourceMayHaveBeenReplaced&&!after.retirementAcknowledged&&!after.acknowledged,"retire conflict uncertainty retained");
   check(uintptr_t(GetWindowLongPtrA(ownWindow,GWLP_WNDPROC))==b+0x5122F0,"counterexample: foreign value overwritten before mismatch discovered");
  }
  if(mode=="window-retire"||mode=="window-period"){
   const auto cached=reinterpret_cast<WNDPROC>(GetWindowLongPtrA(ownWindow,GWLP_WNDPROC));
   check(boundary->Retire(2,duplicate)&&awaitAck(boundary,true),"window-thread exact original restore and retirement ACK");
   check(uintptr_t(GetWindowLongPtrA(ownWindow,GWLP_WNDPROC))==b+0x5122F0,"exact original restored");
   check(boundary->Retire(2,duplicate)&&duplicate,"retired receipt duplicate");
   // Explicit stale cached entry invocation is a fixture check, not actual OS dispatch.
   check(CallWindowProcA(cached,ownWindow,Barrier,7,3)==4,"retained retired callback forwards transparently");
   unsigned newRevision=3;
#ifdef PLANNING_INPUT_BOUNDARY_PERIOD_FIXTURE
   auto*next=new planning_input_interlock::Controller;
   planning_period_owner::Receipt receipt{};
   if(mode=="window-period"){
    check(requestFence(true,3,duplicate)&&observeFence(3),"old Controller refenced after window retirement gap");
    check(planning_period_owner::Retire(*session,*input,interlock,rd->binding,receipt),"same physical Owner formal old period retirement");
    const auto oldBinding=rd->binding;put<unsigned char>(world+0x37,21);++rd->binding.period;++rd->binding.epoch;rd->binding.room_input_digest[0]=19;
    ar::Config nextConfig{};nextConfig.binding=rd->binding;nextConfig.sample=RewardData::sample;
    check(planning_period_owner::Rebind(*session,*input,nextConfig,receipt.serial),"explicit next-period binding after fixture date change");
    planning_input_interlock::Config nc{};nc.owner=session;nc.gate=input;nc.binding=rd->binding;nc.base=b;nc.root=root;nc.world=world;
    check(next->Initialize(nc),"new Controller claims next period without physical reinstall");
    check(!interlock.Request(false,4,duplicate),"old Controller cannot release new period");
    check(!ar::ReadyFence(*session,oldBinding,false,4),"old reward binding cannot release new period");
    check(next->Request(false,4,duplicate),"new Controller explicit release before window initialize");
    windowController=next;newRevision=5;
   }
#endif
   replacement=new pb::Boundary;check(SendMessageA(ownWindow,Rebind,0,0)==1&&windowInitialized,"new instance binds on same actual window thread");
   bool observed=false;
   if(windowController==&interlock)observed=requestFence(true,newRevision,duplicate)&&observeFence(newRevision);
   else if(windowController->Request(true,newRevision,duplicate)&&windowController->BeginObservation(newRevision)){const auto code=gameDispatch()|rewardDispatch();observed=windowController->EndObservation(newRevision)&&code==0;}
   check(observed&&replacement->Request(true,newRevision,duplicate)&&awaitAck(replacement),"new instance closes later revision");
   boundary->Snapshot(before);replacement->Snapshot(after);check(before.retirementAcknowledged&&before.callbackSlot!=after.callbackSlot,"old callback identity retained independently");
   const auto current=bodyAudited.load();check(SendMessageA(ownWindow,WM_KEYDOWN,VK_RETURN,0)==0&&bodyAudited.load()==current,"new window boundary really suppresses");
  }
 }
 check(PostMessageA(ownWindow,WM_CLOSE,0,0)!=0&&WaitForSingleObject(thread,5000)==WAIT_OBJECT_0,"lifecycle close forwarded even under hold");check(bodyIdentity,"archived ABI preserves exact engine");CloseHandle(thread);CloseHandle(windowReady);
 auto*current=replacement?replacement:boundary;pb::Report final{};current->Snapshot(final);ar::Report rr{};ar::Snapshot(*session,rr);ss::Report owner{};session->Snapshot(owner);check(!rr.active&&!owner.active_scopes,"native Owner scopes drained");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"window_thread\":%lu,\"owner_thread\":%lu,\"audited_suppressed\":%llu,\"audited_forwarded\":%llu,\"lifecycle_forwarded\":%llu,\"uncovered_forwarded\":%llu,\"unclassified_forwarded\":%llu,\"control_calls\":%llu,\"finally\":%llu,\"active\":%llu,\"full_window_input_held\":false,\"all_input_held\":false,\"save_authorized\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,final.windowThread,final.ownerThread,final.auditedSuppressed,final.auditedForwarded,final.lifecycleForwarded,final.uncoveredForwarded,final.unclassifiedForwarded,final.controlCalls,final.finally,final.active);
 return failed?1:0;
}
int main(int argc,char**argv){SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();reportMachinery();upstreamMachinery();cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 RewardData data;if(mode=="worker-b")put<unsigned char>(world+0x3A,2);check(session->Initialize(cfg)&&session->Arm(),"single actual User/Save owner");ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);check(input->Initialize(ic)&&input->PreparedPlan(plan),"upstream gate");publish();check(input->Arm()&&input->Hold(ic.binding,true,1),"same existing upstream held boundary");check(gameDispatch()==0,"actual Game boundary observed before Save");ar::Config rc{};rc.binding=data.binding;rc.sample=RewardData::sample;check(ar::Bind(*session,rc),"reward lane binds exact same owner");originalViewer=get<unsigned char>(world+0x3A);planning_input_interlock::Config pc{};pc.owner=session;pc.gate=input;pc.binding=data.binding;pc.base=b;pc.root=root;pc.world=world;check(interlock.Initialize(pc),"unified exact existing Owner and Gate");return failed?1:boundaryCases();}
