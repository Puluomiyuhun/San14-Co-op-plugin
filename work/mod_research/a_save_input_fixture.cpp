#include "a_save_input.h"
// Reuse the first-party frozen A fixture setup, but never execute its main.
// Its game business and storage doubles remain explicitly doubles here too.
#define main ASaveInputFrozenMain
#include "a_save_user_owner_fixture.cpp"
#undef main
namespace ai=a_save_input;
static ai::Owner*input=new ai::Owner;
static ai::Config inputConfig{};
static unsigned uiBodies=0,gameBodies=0;
extern "C" {
 uintptr_t InputFixtureUi=0;
 std::uint64_t InputGameDispatch(uintptr_t);
 void InputGameReturn();void InputUiReturn();void InputGameBody();void InputUiRaw();
}
extern "C" std::uint64_t InputUiBody(std::uint64_t a,std::uint64_t x,std::uint64_t y,std::uint64_t z){
 ++uiBodies;check(a==InputFixtureUi&&x==0x1122&&y==0x3344&&z==0x5566,"native global UI consumed exact original registers");
 if(mode=="ui-exception")RaiseException(0xE123FA01,0,0,nullptr);
 return 0xFEDCBA9876543210ULL;
}
extern "C" void InputGameTail(){++gameBodies;if(mode=="inflight-stop")input->Stop();
 if(mode=="panel-bypass")put<unsigned>(b+0x2B0000+0x1B0,4);
}
static DWORD gameDispatch(){
 __try{return InputGameDispatch(b+0x202000)==0xABCDEF1234567890ULL?0:1;}
 __except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}
}
static bool inputSampleBound(void*,ai::pending::Config&c)noexcept{return inputSample(nullptr,c);}
static void finish(){ai::Report r{};input->Snapshot(r);
 check(!r.active&&!r.bridges[0].active&&!r.bridges[1].active&&!r.bridges[0].cleanup_faults&&!r.bridges[1].cleanup_faults,"all parent and UI FINALLY scopes balanced");
 check(!r.fullInputHold&&!r.saveAuthorized&&!r.roomReady,"single consumer never certifies full input or save admission");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_calls\":%llu,\"suppressed\":%llu,\"native_ui\":%u,\"error\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,r.gameCalls,r.uiSuppressed,uiBodies,unsigned(r.error));
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();
 cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;
 cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);
 jump(b+0x3F8140,reinterpret_cast<void*>(&InputGameBody));jump(b+0x1AC3C0,reinterpret_cast<void*>(&InputUiRaw));
 DWORD old=0;VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READWRITE,&old);
 put<uintptr_t>(b+0x12CC9B8+0x28,b+0x3F8140);VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READONLY,&old);
 put<uintptr_t>(b+0x1297CF8+0x18,b+0x1AC3C0);put<uintptr_t>(b+0x1FC8410,b+0x1297CF8);InputFixtureUi=b+0x1FC8410;
 check(VirtualProtect(reinterpret_cast<void*>(b+0x1297000),4096,PAGE_READONLY,&old)!=0,"global UI source page starts read-only");
 inputConfig.base=b;inputConfig.root=root;inputConfig.world=world;inputConfig.binding=cfg.input_binding;inputConfig.sample=inputSampleBound;
 inputConfig.fixtureGameCaller=uintptr_t(&InputGameReturn);inputConfig.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(inputConfig),"independent Game and global-UI owner initialized");
 if(mode=="stop-before-arm"){input->Stop();check(!input->Arm(),"stop before publication refuses source changes");finish();return failed?1:0;}
 if(mode=="source-drift"){
  VirtualProtect(reinterpret_cast<void*>(b+0x1297000),4096,PAGE_READWRITE,&old);put<uintptr_t>(b+0x1297CF8+0x18,b+0x1AC3C1);VirtualProtect(reinterpret_cast<void*>(b+0x1297000),4096,PAGE_READONLY,&old);
  check(!input->Arm()&&get<uintptr_t>(b+0x1297CF8+0x18)==b+0x1AC3C1,"changed source never overwritten");finish();return failed?1:0;
 }
 check(input->Arm(),"actual two vtable source CAS and protection restoration");
 check(session->Initialize(cfg)&&session->Arm(),"unchanged A User/Save Owner coexists without slot collision");
 if(failed)return 3;
 const bool open=mode=="open"||mode=="ui-exception";
 if(!open)check(input->Hold(inputConfig.binding,true,1),"request independent consumer hold");
 if(mode=="pending-menu")put<int>(b+0x280000+0x88,4);
 if(mode=="wrong-world")put<uintptr_t>(root+0x85130,world+8);
 if(mode=="foreign-ui"){
  auto ui=reinterpret_cast<CheckpointLoadWorkerEntry>(get<uintptr_t>(b+0x1297CF8+0x18));
  check(ui(InputFixtureUi,0x1122,0x3344,0x5566)==0xFEDCBA9876543210ULL,"foreign caller remains native and invalidates hold");
 }
 auto result=gameDispatch();check(result==(mode=="ui-exception"?0xE123FA01u:0u),"native Game and exception preserved");ai::Report first{};input->Snapshot(first);
 const bool invalid=mode=="pending-menu"||mode=="wrong-world"||mode=="foreign-ui";
 if(invalid){check(first.error!=ai::Error::None&&!first.coveredGlobalUiHeld&&uiBodies>0,"unsafe/foreign source receives no hold receipt");check(gameDispatch()==0,"sticky fault transparently forwards later Game");}
 else if(open)check(uiBodies==1&&!first.uiSuppressed,"open parent continues native UI");
 else if(mode=="inflight-stop"){
  check(first.stopped&&!first.coveredGlobalUiHeld&&uiBodies==0,"Stop revokes even after current consumer was suppressed");
  check(gameDispatch()==0&&uiBodies==1,"next parent and UI forward after Stop");
 }else {
  check(first.coveredGlobalUiHeld&&first.uiSuppressed==1&&!uiBodies&&gameBodies==1,"actual parent ran while child UI was suppressed");
  if(mode=="stop-held"){input->Stop();check(gameDispatch()==0&&uiBodies==1,"held consumer returns to native after Stop");}
  else if(mode=="release"){
   check(input->Hold(inputConfig.binding,false,2)&&gameDispatch()==0&&uiBodies==1,"explicit release runs original consumer");
  }else if(mode=="source-conflict"){
   VirtualProtect(reinterpret_cast<void*>(b+0x1297000),4096,PAGE_READWRITE,&old);
   put<uintptr_t>(b+0x1297CF8+0x18,uintptr_t(&InputUiRaw));VirtualProtect(reinterpret_cast<void*>(b+0x1297000),4096,PAGE_READONLY,&old);
   check(gameDispatch()==0&&uiBodies==1&&get<uintptr_t>(b+0x1297CF8+0x18)==uintptr_t(&InputUiRaw),"competing source is detected without restoring or overwriting it");
   ai::Report conflict{};input->Snapshot(conflict);check(conflict.error!=ai::Error::None&&!conflict.coveredGlobalUiHeld&&!input->Hold(inputConfig.binding,false,2),"source conflict revokes later admission");
  }else if(mode=="unknown-modal"){
   put<std::uint64_t>(b+0x19E7310+0x10,6);put<uintptr_t>(b+0x210000+40,b+0x240000);put<uintptr_t>(b+0x240000,b+0x12DB4C0);
   check(gameDispatch()==0&&uiBodies==1,"unknown modal forwards and faults rather than pretending safe");
  }else if(mode=="panel-bypass"){
   check(get<unsigned>(b+0x2B0000+0x1B0)==4&&first.coveredGlobalUiHeld,"independent latched panel path is NOT covered by this UI consumer");
   check(session->Submit(request(1))&&dispatch(0,user)==0,"unchanged raw User attempts ordinary execution");
   const auto unsafe=saveReport();check(unsafe.status!=fs::Status::Complete&&unsafe.error&&!binds&&!queues,"real fresh Driver rejects pending panel rather than inventing write exclusion");
  }else if(mode=="two-saves"){
   for(unsigned generation=1;generation<=2;++generation){
    if(generation==2)put<unsigned char>(world+0x37,21);
    check(session->Submit(request(generation)),"unchanged A Owner accepts raw save request");
    check(dispatch(0,user)==0,"necessary raw User still executes while independent consumer held");auto save=saveReport();check(save.status==fs::Status::Queued,"raw User queued genuine fixture Save lifecycle");
    put<std::uint64_t>(b+0x19E7310+0x30,0);put<std::uint64_t>(b+0x19E7310+0x10,6);put<uintptr_t>(b+0x210000+40,b+0x240000);
    for(unsigned phase=0;phase<5;++phase){check(gameDispatch()==0,"parent progress continues during exact Save state");check(dispatch(1,b+0x240000)==0,"native Save phase continues");}
    check(dispatch(0,user)==0,"raw User return fixes exported bytes");fs::Artifact artifact;check(session->CopyArtifact(generation,artifact)&&artifact.report.status==fs::Status::Complete,"same A Owner completed distinct saved generation");
   }
   ai::Report end{};input->Snapshot(end);check(!uiBodies&&end.error==ai::Error::None&&binds==2&&queues==2&&nativeReads==4,"independent consumer suppression coexists with actual two-request A component");
  }
 }
 finish();return failed?1:0;
}
