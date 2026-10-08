#include "a_save_action_gate.h"
#define main ActionFrozenMain
#include "a_save_user_owner_fixture.cpp"
#undef main
#include <tlhelp32.h>
namespace ag=a_save_action_gate;
static ag::Owner*input=new ag::Owner;static ag::Config ic{};static ag::Plan plan{};
static unsigned uiBodies=0,panelBodies=0,tailBodies=0,advances=0,commands=0,gameBodies=0;
extern "C" {
 uintptr_t InputFixtureUi=0,ActionPanelSnippet=0,ActionUserSnippet=0,ActionGame=0;
 std::uint64_t InputGameDispatch(uintptr_t);void InputGameReturn();void InputUiReturn();void InputGameBody();void InputUiRaw();void ActionRawUser();
 void ASaveActionTailRestoreBegin();void ASaveActionTailFlagsPush();void ASaveActionTailFlagsPop();
 void ASaveActionTailEpilogue();void ASaveActionTailPopRbp();void ASaveActionTailRet();void ASaveActionTailOriginalLoad();
}
extern "C" std::uint64_t InputUiBody(std::uint64_t a,std::uint64_t x,std::uint64_t y,std::uint64_t z){
 ++uiBodies;check(a==InputFixtureUi&&x==0x1122&&y==0x3344&&z==0x5566,"actual global UI native four registers preserved");return 0xFEDCBA9876543210ULL;
}
extern "C" void InputGameTail(){++gameBodies;if(mode=="panel-pending")put<unsigned>(b+0x2B0000+0x1B0,4);if(mode=="inflight-stop")input->Stop();}
extern "C" std::uint64_t ActionPanelBody(uintptr_t game,std::uint64_t,std::uint64_t,std::uint64_t){
 ++panelBodies;check(game==ActionGame,"panel receives exact Game argument");
 if(mode=="panel-exception")RaiseException(0xE123FA02,0,0,nullptr);
 if(get<unsigned>(b+0x2B0000+0x1B0)>1){++commands;put<unsigned>(b+0x2B0000+0x1B0,0);}return 0xAABBCCDD;
}
extern "C" void ActionInjectTail(){
 if(mode=="tail-av"){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(user),4096,PAGE_NOACCESS,&old)!=0,"make the original User load fault only AFTER native entry");}
 if(mode=="raw-command")put<int>(b+0x280000+0x88,10);
 if(mode=="raw-advance"){put<unsigned>(b+0x2B0000+0x1B0,1);put<unsigned>(ActionGame+0x47C,1);}
 if(mode=="early-bypass")++commands; // Explicit uncovered write before the cut.
}
extern "C" void ActionTailBody(uintptr_t self){
 ++tailBodies;check(self==user,"raw User action body receives actual RSI identity");
 const int menu=get<int>(b+0x280000+0x88);put<int>(b+0x280000+0x88,-1);
 if(get<unsigned>(b+0x2B0000+0x1B0)==1||get<unsigned>(ActionGame+0x47C)){
  ++advances;put<unsigned>(b+0x2B0000+0x1B0,0);put<unsigned>(ActionGame+0x47C,0);put<unsigned>(user+0x470,5);
 }else if(menu>=0)++commands;
}
static void writeCode(uintptr_t at,const void*data,size_t n){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(at),n,PAGE_READWRITE,&old)!=0,"owned source writable only in fixture preparation");memcpy(reinterpret_cast<void*>(at),data,n);check(VirtualProtect(reinterpret_cast<void*>(at),n,PAGE_EXECUTE_READ,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(at),n),"owned source RX and instruction cache restored");}
static void absCall(unsigned char*out,void*fn){out[0]=0x48;out[1]=0xB8;memcpy(out+2,&fn,8);out[10]=0xff;out[11]=0xd0;}
static void machinery(){
 DWORD old=0;VirtualProtect(reinterpret_cast<void*>(b+0x3F9000),8192,PAGE_READWRITE,&old);
 jump(b+0x3F9B00,reinterpret_cast<void*>(&ActionRawUser));jump(b+0x3F8140,reinterpret_cast<void*>(&InputGameBody));jump(b+0x1AC3C0,reinterpret_cast<void*>(&InputUiRaw));jump(b+0x3FA820,reinterpret_cast<void*>(&ActionPanelBody));
 const unsigned char panel[]={0x48,0x83,0xec,0x28,0xe8,0x15,0x22,0,0,0x48,0x83,0xc4,0x28,0xc3};writeCode(b+0x3F8602,panel,sizeof panel);
 unsigned char head[42]{};memset(head,0x90,sizeof head);const unsigned char first[]={0x48,0x83,0xec,0x28,0x90,0x90,0x90,0x48,0x8b,0x86,0x78,0x04,0,0,0x48,0x8b,0xce};memcpy(head,first,sizeof first);
 absCall(head+17,reinterpret_cast<void*>(&ActionTailBody));head[29]=0xe9;const auto rel=std::int32_t((b+0x3FA09F)-(b+0x3F9DA8+34));memcpy(head+30,&rel,4);writeCode(b+0x3F9DA8,head,sizeof head);
 const unsigned char end[]={0x48,0x83,0xc4,0x28,0xc3};writeCode(b+0x3FA09F,end,sizeof end);
 // These two owned snippets allocate 0x28. Real game routines have their own
 // unchanged PE unwind metadata; no private game code is copied into this fixture.
 const unsigned char unwind[]={1,4,1,0,4,0x42,0,0};memcpy(reinterpret_cast<void*>(b+0x2200000),unwind,sizeof unwind);
 auto*t=reinterpret_cast<RUNTIME_FUNCTION*>(b+0x2200020);t[0]={0x3F8602,0x3F8610,0x2200000};t[1]={0x3F9DA8,0x3FA0A4,0x2200000};check(RtlAddFunctionTable(t,2,b)!=0,"owned snippet unwind tables actually registered");
 VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READWRITE,&old);put<uintptr_t>(b+0x12CC9B8+0x28,b+0x3F8140);VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READONLY,&old);
 put<uintptr_t>(b+0x1297CF8+0x18,b+0x1AC3C0);put<uintptr_t>(b+0x1FC8410,b+0x1297CF8);VirtualProtect(reinterpret_cast<void*>(b+0x1297000),4096,PAGE_READONLY,&old);
 InputFixtureUi=b+0x1FC8410;ActionGame=b+0x202000;ActionPanelSnippet=b+0x3F8602;ActionUserSnippet=b+0x3F9DA8;
}
// Owned fixture-only publisher. All test-game execution is on this thread;
// crypto/runtime workers nevertheless exist, so actually suspend/inspect them.
// This is NOT an installer for an arbitrary game process.
struct StoppedThread {DWORD id=0;HANDLE handle=nullptr;bool added=false;};
static bool pauseOthers(StoppedThread(&list)[128],unsigned&count){
 for(unsigned pass=0;pass<4;++pass){HANDLE snap=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(snap==INVALID_HANDLE_VALUE)return false;
  THREADENTRY32 e{sizeof e};bool fresh=false,ok=true;if(!Thread32First(snap,&e))ok=false;
  else do{if(e.th32OwnerProcessID!=GetCurrentProcessId()||e.th32ThreadID==GetCurrentThreadId())continue;
   bool known=false;for(unsigned i=0;i<count;++i)known|=list[i].id==e.th32ThreadID;if(known)continue;
   if(count>=128){ok=false;break;}auto&t=list[count++];t.id=e.th32ThreadID;t.handle=OpenThread(THREAD_SUSPEND_RESUME|THREAD_GET_CONTEXT|THREAD_QUERY_INFORMATION,FALSE,t.id);
   if(!t.handle){ok=false;break;}const auto before=SuspendThread(t.handle);if(before==DWORD(-1)){ok=false;break;}t.added=true;
   CONTEXT context{};context.ContextFlags=CONTEXT_CONTROL;
   if(!GetThreadContext(t.handle,&context)||(context.Rip>=b+0x3F8000&&context.Rip<b+0x3FB000)){ok=false;break;}fresh=true;
  }while(Thread32Next(snap,&e));CloseHandle(snap);if(!ok)return false;if(!fresh)return true;
 }return false;
}
static void publish(){StoppedThread list[128]{};unsigned count=0;
 __try {
  check(!gameBodies&&!tailBodies&&!panelBodies,"no fixture-game execution has begun before publication");
  check(pauseOthers(list,count),"actual own-process threads paused, control contexts checked, stable enumeration confirmed");if(failed)__leave;
  for(unsigned i=0;i<2;++i){if(mode=="partial-install"&&i==1)continue;const auto&p=plan.patches[i];check(!memcmp(reinterpret_cast<void*>(p.address),p.before,p.size),"source bytes still match original before fixture patch");writeCode(p.address,p.after,p.size);}
 }__finally {for(unsigned i=count;i;--i){auto&t=list[i-1];if(t.added)check(ResumeThread(t.handle)!=DWORD(-1),"restore exactly our own thread suspension increment");if(t.handle)CloseHandle(t.handle);}}
}
static DWORD gameDispatch(){__try{return InputGameDispatch(ActionGame)==0xABCDEF1234567890ULL?0:1;}__except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}}
static void unwind(){
 alignas(16) unsigned char stack[1024]{};const auto bottom=uintptr_t(stack+256);
 const uintptr_t oldRbp=0x1234567812345678ULL,expectedReturn=0x12345000;
 put<uintptr_t>(bottom+0xF0,oldRbp);put<uintptr_t>(bottom+0xF8,expectedReturn);
 auto verify=[&](uintptr_t pc,uintptr_t rsp,uintptr_t rbp){CONTEXT context{};context.ContextFlags=CONTEXT_FULL;context.Rip=pc;context.Rsp=rsp;context.Rbp=rbp;
  DWORD64 image=0,frame=0;void*handler=nullptr;auto entry=RtlLookupFunctionEntry(pc,&image,nullptr);check(entry!=nullptr,"actual PE runtime function metadata present");if(!entry)return;
  RtlVirtualUnwind(UNW_FLAG_NHANDLER,image,pc,entry,&context,&handler,&frame,nullptr);
  check(context.Rip==expectedReturn&&context.Rsp==bottom+0x100&&context.Rbp==oldRbp,"every restored control PC recovers exact caller RSP/RBP/RIP");};
 // Includes every instruction start (and byte interior) in the fixed-frame
 // restoration body. The temporary push and legal epilogue get exact stages.
 verify(uintptr_t(&ASaveActionTailOriginalLoad),bottom,bottom+0x80);
 for(auto pc=uintptr_t(&ASaveActionTailRestoreBegin);pc<uintptr_t(&ASaveActionTailFlagsPop);++pc)verify(pc,bottom,bottom+0x80);
 verify(uintptr_t(&ASaveActionTailFlagsPop),bottom-8,bottom+0x80);
 verify(uintptr_t(&ASaveActionTailEpilogue),bottom,bottom+0x80);
 verify(uintptr_t(&ASaveActionTailPopRbp),bottom+0xF0,bottom+0x80);
 verify(uintptr_t(&ASaveActionTailRet),bottom+0xF8,oldRbp);
}
static void finish(){ag::Report r{};input->Snapshot(r);ss::Report s{};session->Snapshot(s);
 check(!r.active&&!r.bridges[0].active&&!r.bridges[1].active&&!r.bridges[2].active&&!s.active_scopes,"all actual native parent/child and save scopes drained");
 check(!r.fullInputHold&&!r.saveAuthorized&&!r.roomReady,"partial action coverage grants no full input save or Ready permit");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"ui_suppressed\":%llu,\"panel_suppressed\":%llu,\"user_tail_suppressed\":%llu,\"raw_user_native_returned\":%llu,\"tail_bodies\":%u,\"advances\":%u,\"commands\":%u,\"binds\":%u,\"queues\":%u,\"native_reads\":%u,\"error\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,r.uiSuppressed,r.panelSuppressed,r.userTailSuppressed,s.bridges[0].native_returned,tailBodies,advances,commands,binds,queues,nativeReads,unsigned(r.error));}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();
 cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;
 cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);
 check(session->Initialize(cfg)&&session->Arm(),"raw A Owner initialized BEFORE explicit User-body transform; User/Save slots unchanged afterwards");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"combined successor prepares fixed two action sources and retained relay");if(failed){finish();return 3;}
 if(mode!="no-install")publish();
 if(mode=="no-install"||mode=="partial-install"){check(!input->Arm(),"missing actual patch bytes cannot be replaced by prepared receipt");finish();return failed?1:0;}
 check(input->Arm(),"actual sources verified before Game/global UI slot CAS");if(failed){finish();return 4;}
 const bool open=mode=="open"||mode=="panel-exception"||mode=="tail-av"||mode=="unwind";
 if(!open)check(input->Hold(ic.binding,true,1),"request combined action hold");
 check(gameDispatch()==(mode=="panel-exception"?0xE123FA02u:0u),"actual Game return and native panel exception preserved");
 ag::Report r{};input->Snapshot(r);
 if(open){check(panelBodies==1&&uiBodies==1,"unheld original UI and panel truly execute");
  if(mode=="unwind")unwind();
  if(mode=="tail-av"){check(dispatch(0,user)==EXCEPTION_ACCESS_VIOLATION,"original instruction AV propagates through native A Owner rather than losing stack unwind");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(user),4096,PAGE_READWRITE,&old)!=0,"restore only owned fixture object page");
   ss::Report save{};session->Snapshot(save);check(save.bridges[0].native_started==1&&!save.bridges[0].native_returned&&save.bridges[0].abnormal_exits==1&&save.bridges[0].finally_calls==1&&!save.active_scopes,"AV ran exact outer User FINALLY without fabricating native AFTER");}
 }
 else if(mode=="inflight-stop"){check(panelBodies==1&&!r.coveredPanelHeld,"Stop within Game revokes later panel suppression");}
 else {check(r.coveredPanelHeld&&!uiBodies&&!panelBodies,"same Game scope actually suppressed global UI and direct panel source");
  if(mode=="panel-pending"){check(get<unsigned>(b+0x2B0000+0x1B0)==4&&!commands,"late panel command was neither consumed nor cleared");}
  else if(mode=="stop-held"||mode=="release"){
   if(mode=="stop-held")input->Stop();else check(input->Hold(ic.binding,false,2),"hold explicitly released");
   put<unsigned>(b+0x2B0000+0x1B0,1);put<unsigned>(ActionGame+0x47C,1);check(dispatch(0,user)==0&&tailBodies==1&&advances==1&&get<unsigned>(user+0x470)==5,"after release real User action body consumes and advances normally");
  }else if(mode=="ordinary-user"){
   check(dispatch(0,user)==0,"unclaimed native User remains transparent");input->Snapshot(r);ss::Report sr{};session->Snapshot(sr);check(r.error!=ag::Error::None&&sr.stopped&&tailBodies==1&&!r.userTailSuppressed,"an ordinary User is not mislabeled as a claimed save-lane tail");
  }else if(mode=="page-drift"){
   DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(b+0x3FA000),4096,PAGE_READONLY,&old)!=0,"cross-page User tail switched away from RX without byte changes");check(!input->Hold(ic.binding,false,2),"entire cross-page User source range must remain RX");
  }else if(mode=="source-conflict"){
   unsigned char changed=0x90;writeCode(plan.patches[0].address,&changed,1);check(!input->Hold(ic.binding,false,2),"competing source revokes admission without restoring it");check(*reinterpret_cast<unsigned char*>(plan.patches[0].address)==0x90,"foreign source byte preserved");
  }else if(mode=="raw-command"||mode=="raw-advance"||mode=="early-bypass"){
   check(session->Submit(request(1))&&dispatch(0,user)==0,"actual claimed raw User reaches early action cut");input->Snapshot(r);
   check(r.userTailSuppressed==1&&!tailBodies&&!advances&&get<unsigned>(user+0x470)==2,"User action tail held BEFORE advance phase changes");
   if(mode=="raw-command")check(get<int>(b+0x280000+0x88)==10&&!binds&&!queues&&!commands,"late menu command remains pending and fresh save rejects it before binder");
   if(mode=="raw-advance")check(get<unsigned>(b+0x2B0000+0x1B0)==1&&get<unsigned>(ActionGame+0x47C)==1&&!binds&&!queues,"both advance latches remain unchanged and save is refused");
   if(mode=="early-bypass")check(commands==1&&saveReport().status==fs::Status::Queued,"explicit earlier User write bypasses tail: no all-write exclusion claim");
  }else if(mode=="two-saves"){
   for(unsigned g=1;g<=2;++g){if(g==2)put<unsigned char>(world+0x37,21);check(session->Submit(request(g))&&dispatch(0,user)==0,"real claimed User returns after tail gate and queues save");check(saveReport().status==fs::Status::Queued,"native owner sees real return and queues once");
    put<std::uint64_t>(b+0x19E7310+0x30,0);put<std::uint64_t>(b+0x19E7310+0x10,6);put<uintptr_t>(b+0x210000+40,b+0x240000);
    for(unsigned phase=0;phase<5;++phase){check(gameDispatch()==0,"Game progress remains live during Save");check(dispatch(1,b+0x240000)==0,"unchanged raw Save phases run");}
    check(dispatch(0,user)==0,"final real User return observed with action tail held");fs::Artifact a;check(session->CopyArtifact(g,a)&&a.report.status==fs::Status::Complete,"same owner retained distinct completed generation");
   }
   input->Snapshot(r);check(r.userTailSuppressed==4&&!tailBodies&&binds==2&&queues==2&&nativeReads==4,"two actual A saves composed with all three consumer gates");
  }
 }
 finish();return failed?1:0;
}
