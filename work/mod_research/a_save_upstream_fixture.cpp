#include "a_save_report_owner.h"
#define FixtureUserBody ReportLegacyUserBody
#define FixtureSaveBody ReportLegacySaveBody
#define ActionInjectTail ReportLegacyInjectTail
#include "a_save_upstream_action_fixture.inc"
#undef FixtureUserBody
#undef FixtureSaveBody
#undef ActionInjectTail

namespace report=a_save_report_owner;
static unsigned reportFlushes=0,existsCalls=0,selectionBodies=0,upstreamCalls=0,updaterCalls=0,upstreamWrites=0;
static uintptr_t reportHead=0;
extern "C" void EarlySelectionDouble(){++selectionBodies;}
static void reportPending(bool flag,bool queue){
 put<unsigned>(user+0x660,flag?1:0);put<std::uint64_t>(b+0x1FC98B8,queue?1:0);
 for(unsigned i=0;i<3;++i)put<uintptr_t>(reportHead+i*8,queue?reportHead+0x100:reportHead);
}
// Explicit business double, NOT execution of archived 2A1EC0 or 835800.
// The 19-byte User branch/call/clear around this double is actual known code.
extern "C" void ReportFlushDouble(){
 ++reportFlushes;if(mode!="external-aba")put<unsigned short>(world+0x165A,get<unsigned short>(world+0x165A)+1);
 reportPending(true,false);
}
extern "C" std::uint64_t FixtureUserBody(std::uint64_t self,std::uint64_t a,std::uint64_t c,std::uint64_t d){return ReportLegacyUserBody(self,a,c,d);}
extern "C" void ActionInjectTail(){
 ReportLegacyInjectTail();
 if(mode=="late-flag")reportPending(true,false);
 if(mode=="late-queue")reportPending(false,true);
 if(mode=="consumed"||mode=="local-aba-blocked"||mode=="external-aba")reportPending(true,true);
 if(mode=="external-aba"){ReportFlushDouble();put<unsigned>(user+0x660,0);} // Explicit producer/consumer outside the covered User branch.
}
extern "C" std::uint64_t FixtureSaveBody(std::uint64_t self,std::uint64_t a,std::uint64_t c,std::uint64_t d){
 auto phase=get<unsigned>(self+0x470);auto value=ReportLegacySaveBody(self,a,c,d);
 if(mode=="during-save"&&phase==2)reportPending(false,true);return value;
}
__declspec(noinline) static bool __fastcall reportExists(void*object,const char*name){
 ++existsCalls;const auto result=exists(object,name);if(mode=="storage-append"&&existsCalls==1)reportPending(false,true);return result;
}
static void reportMachinery(){
 reportHead=b+0x2D0000;put<uintptr_t>(b+0x1FC98B0,reportHead);put<unsigned char>(reportHead+0x19,1);reportPending(false,false);
 // One owned User snippet now contains the original report cmp/call/clear,
 // explicit selection double, old action snippet and the original-shaped exit.
 // No separate invocation can consume reports before the early Gate.
 unsigned char branch[64]{};memset(branch,0x90,sizeof branch);
 const unsigned char first[]={0x48,0x83,0xec,0x28,0x39,0xae,0x60,0x06,0,0,0x74,0x0b,0xe8,0x0b,0x83,0xea,0xff,0x89,0xae,0x60,0x06,0,0};
 memcpy(branch,first,sizeof first);absCall(branch+23,reinterpret_cast<void*>(&EarlySelectionDouble));
 branch[35]=0xe9;const auto rel=std::int32_t((b+0x3F9DAF)-(b+0x3F9BA4+40));memcpy(branch+36,&rel,4);
 writeCode(b+0x3F9BA4,branch,sizeof branch);ActionUserSnippet=b+0x3F9BA4;
 const unsigned char cursor[]={0x66,0x89,0xb9,0x5a,0x16,0,0},clear[]={0x48,0xc7,0x05,0xeb,0x94,0xd8,0x01,0,0,0,0};
 writeCode(b+0x835C2C,cursor,sizeof cursor);writeCode(b+0x2403C2,clear,sizeof clear);
 DWORD old=0;VirtualProtect(reinterpret_cast<void*>(b+0x2A1000),4096,PAGE_READWRITE,&old);jump(b+0x2A1EC0,reinterpret_cast<void*>(&ReportFlushDouble));
 VirtualProtect(reinterpret_cast<void*>(b+0x2A1000),4096,PAGE_EXECUTE_READ,&old);
 const unsigned char uw[]={1,4,1,0,4,0x42,0,0};memcpy(reinterpret_cast<void*>(b+0x2200040),uw,sizeof uw);
 auto*t=new RUNTIME_FUNCTION{0x3F9BA4,0x3FA0A4,0x2200040};check(RtlAddFunctionTable(t,1,b)!=0,"single actual early User snippet unwind registered");
 DWORD64 image=0;check(RtlLookupFunctionEntry(b+0x3F9BAD,&image,nullptr)==t&&RtlLookupFunctionEntry(b+0x3FA09F,&image,nullptr)==t,"early call and original-shaped epilogue use same unwind entry");
}
extern "C" void UpstreamBeforeCut(){ActionInjectTail();}
extern "C" uintptr_t UpstreamSingletonDouble(uintptr_t a,uintptr_t x,uintptr_t y,uintptr_t z){
 ++upstreamCalls;check(a==user&&x==0x1122&&y==0x3344&&z==0x5566,"transparent tail jump preserves four original native inputs");
 if(mode=="upstream-exception")RaiseException(0xE014A701,0,0,nullptr);return b+0x1A38840;
}
extern "C" void UpstreamUpdaterDouble(uintptr_t self){
 ++updaterCalls;check(self==b+0x1A38840,"native singleton RAX flows into actual next updater call");
 if(mode=="updater-write"||mode=="release-updater"){++upstreamWrites;reportPending(true,true);}
}
static void upstreamMachinery(){
 unsigned char code[32]{};memset(code,0x90,sizeof code);
 const unsigned char first[]={0x48,0x83,0xec,0x28,0xe8,0x05,0x5f,0xd6,0xff,0x48,0x8b,0xc8,0xe8};memcpy(code,first,sizeof first);
 const auto call=std::int32_t((b+0x16C5F0)-(b+0x3F9B23));memcpy(code+13,&call,4);code[17]=0xe9;
 const auto next=std::int32_t((b+0x3F9BA8)-(b+0x3F9B12+22));memcpy(code+18,&next,4);writeCode(b+0x3F9B12,code,sizeof code);
 DWORD old=0;VirtualProtect(reinterpret_cast<void*>(b+0x15F000),4096,PAGE_READWRITE,&old);jump(b+0x15FA20,reinterpret_cast<void*>(&UpstreamSingletonDouble));VirtualProtect(reinterpret_cast<void*>(b+0x15F000),4096,PAGE_EXECUTE_READ,&old);
 VirtualProtect(reinterpret_cast<void*>(b+0x16C000),4096,PAGE_READWRITE,&old);jump(b+0x16C5F0,reinterpret_cast<void*>(&UpstreamUpdaterDouble));VirtualProtect(reinterpret_cast<void*>(b+0x16C000),4096,PAGE_EXECUTE_READ,&old);
 const unsigned char end[]={0x48,0x83,0xc4,0x28,0xc3};writeCode(b+0x3FA0AE,end,sizeof end);ActionUserSnippet=b+0x3F9B12;
 const unsigned char uw[]={1,4,1,0,4,0x42,0,0};memcpy(reinterpret_cast<void*>(b+0x2200060),uw,sizeof uw);
 auto*t=new RUNTIME_FUNCTION[2]{{0x3F9B12,0x3F9B32,0x2200060},{0x3FA0AE,0x3FA0B3,0x2200060}};
 check(RtlAddFunctionTable(t,1,b)&&RtlAddFunctionTable(t+1,1,b),"independent upstream and short exit unwind records, no overlapping table envelope");
 DWORD64 image=0;check(RtlLookupFunctionEntry(b+0x3F9B1B,&image,nullptr)==t,"actual upstream source native return unwinds correct snippet");
}
static void completeSave(){
 put<std::uint64_t>(b+0x19E7310+0x30,0);put<std::uint64_t>(b+0x19E7310+0x10,6);put<uintptr_t>(b+0x210000+40,b+0x340000);
 for(unsigned i=0;i<5;++i){
  fs::Artifact pending{};check(!session->CopyArtifact(saveReport().generation,pending)&&pending.bytes.empty(),"IPC-style Copy poll in actual six-state Save returns NotReady");
  if(mode!="during-save"){report::Report rr{};ss::Report sr{};session->Snapshot(sr);check(report::Snapshot(session,rr)&&!rr.revoked&&sr.error==ss::Error::None&&!sr.stopped,"normal poll does not revoke or stop in-progress Save");}
  check(dispatch(1,b+0x340000)==0,"actual original Save callback returns through Owner");
 }
 check(get<std::uint64_t>(b+0x19E7310+0x10)==5,"Save double leaves actual planning layout");
 fs::Artifact pending{};check(!session->CopyArtifact(saveReport().generation,pending),"finalized but not returned User remains ordinary NotReady");
 check(dispatch(0,user)==0,"actual original post-save User callback returned");
}
static void summary(){
 report::Report rr{};check(report::Snapshot(session,rr),"successor report attached to this exact Owner");ss::Report sr{};session->Snapshot(sr);ag::Report ar{};input->Snapshot(ar);
 check(!sr.active_scopes&&!sr.save.active&&!sr.bridges[0].active&&!sr.bridges[1].active&&!ar.active,"all actual callbacks and finally scopes drained");
 check(!rr.fullInputHold&&!rr.reportWriteExclusion&&!rr.saveAuthorized&&!rr.roomReady&&!ar.fullInputHold&&!sr.all_input_held,"negative admission never grants complete exclusion or Ready");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"binds\":%u,\"queues\":%u,\"native_reads\":%u,\"report_flush_doubles\":%u,\"selection_doubles\":%u,\"singleton_doubles\":%u,\"updater_doubles\":%u,\"upstream_writes\":%u,\"user_early_suppressed\":%llu,\"submit_rejected\":%llu,\"entry_suppressed\":%llu,\"after_rejected\":%llu,\"storage_rejected\":%llu,\"revoked\":%s,\"native_user_returned\":%llu,\"save_native_returned\":%llu,\"save_status\":%u,\"full_input_held\":false,\"save_authorized\":false,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,binds,queues,nativeReads,reportFlushes,selectionBodies,upstreamCalls,updaterCalls,upstreamWrites,ar.userTailSuppressed,rr.submitRejected,rr.entrySuppressed,rr.afterRejected,rr.storageRejected,rr.revoked?"true":"false",sr.bridges[0].native_returned,sr.bridges[1].native_returned,unsigned(sr.save.status));
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();reportMachinery();upstreamMachinery();
 cfg.base=b;cfg.binder=uintptr_t(&binder);cfg.queue=uintptr_t(&queue);cfg.caller=uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;
 cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);
 cfg.storage.exists=endpoint(reinterpret_cast<void*>(&reportExists));storageVtable[0x68/8]=uintptr_t(&reportExists);
 if(mode=="competing-initialize"){
  auto*other=new ss::Owner;bool first=false,second=false;
  std::thread one([&]{first=session->Initialize(cfg);}),two([&]{second=other->Initialize(cfg);});one.join();two.join();
  check(first!=second,"concurrent independent Owner initializers cannot share the sidecar");
  auto*loser=first?other:session;if(second)session=other;
  report::Report rr{};check(!report::Snapshot(loser,rr)&&!loser->Initialize(cfg),"failed competing owner cannot inspect or reset the retained winner");
  reportPending(true,false);fs::Artifact artifact{};check(!loser->CopyArtifact(0,artifact)&&report::Snapshot(session,rr)&&!rr.revoked,"loser cannot drive or revoke the winner sidecar through CopyArtifact");reportPending(false,false);summary();return failed?1:0;
 }
 check(session->Initialize(cfg)&&session->Arm(),"actual report Owner replacement publishes existing User/Save slots");
 ic.base=b;ic.root=root;ic.world=world;ic.saveOwner=session;ic.binding=cfg.input_binding;ic.sample=inputSample;ic.fixtureGameCaller=uintptr_t(&InputGameReturn);ic.fixtureUiCaller=uintptr_t(&InputUiReturn);
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"upstream Gate and exact prefix Owner successors compose");const unsigned char oldTail[]={0x48,0x8b,0x86,0x78,0x04,0,0};check(plan.patches[1].address==b+0x3F9B16&&plan.patches[1].size==5&&!memcmp(reinterpret_cast<void*>(b+0x3F9DAF),oldTail,sizeof oldTail),"exactly two owned patches, old User cut stays original");if(failed){summary();return 3;}if(mode!="no-install")publish();if(mode=="no-install"||mode=="partial-install"){check(!input->Arm(),"missing owned patch bytes deny publication");summary();return failed?1:0;}check(input->Arm()&&input->Hold(ic.binding,true,1),"actual action source publication and hold");check(gameDispatch()==0,"actual Game scoped global UI/panel isolation");
 if(mode=="unwind"){unwind();summary();return failed?1:0;}
 if(mode=="source-conflict"||mode=="suffix-drift"||mode=="prefix-drift"){
  const auto at=mode=="source-conflict"?plan.patches[1].address:mode=="prefix-drift"?b+0x3F9B0F:b+0x3F9BB5;const unsigned char changed=0x90;writeCode(at,&changed,1);
  check(!session->Submit(request(1))&&!binds&&!queues,"owned early source or untouched report suffix drift rejects before Driver");
  check(get<unsigned char>(at)==0x90,"foreign source is preserved, never silently repaired");summary();return failed?1:0;
 }
 if(mode=="release-report"||mode=="release-quiet"||mode=="release-updater"||mode=="tail-av"||mode=="upstream-exception"){
  input->Stop();if(mode=="release-report")reportPending(true,true);
  if(mode=="upstream-exception"){
   check(dispatch(0,user)==0xE014A701u,"transparent native singleton exception crosses real User FINALLY");ss::Report sr{};session->Snapshot(sr);check(sr.bridges[0].native_started==1&&!sr.bridges[0].native_returned&&sr.bridges[0].finally_calls==1&&sr.bridges[0].abnormal_exits==1&&!sr.active_scopes,"tail-forward exception never fabricates native AFTER");
  }else if(mode=="tail-av"){
   check(dispatch(0,user)==EXCEPTION_ACCESS_VIOLATION,"original CMP AV follows exact PE and User FINALLY");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(user),4096,PAGE_READWRITE,&old)!=0,"restore owned User page after fault");
   ss::Report sr{};session->Snapshot(sr);check(sr.bridges[0].native_started==1&&!sr.bridges[0].native_returned&&sr.bridges[0].finally_calls==1&&sr.bridges[0].abnormal_exits==1&&!sr.active_scopes,"original CMP fault does not manufacture AFTER");
  }else{
   check(dispatch(0,user)==0,"released User executes original report compare and downstream paths");
   check(reportFlushes==unsigned(mode=="release-report"||mode=="release-updater")&&selectionBodies==1&&tailBodies==1&&!get<unsigned>(user+0x660)&&!get<std::uint64_t>(b+0x1FC98B8),"actual CMP flags choose quiet/pending branch and preserve normal consumption");
  }check(upstreamCalls==1&&(mode=="upstream-exception"?updaterCalls==0:updaterCalls==1),"released original singleton/updater execution order retained");summary();return failed?1:0;
 }
 if(mode=="submit-unreadable"){
  DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>((world+0x165A)&~uintptr_t(4095)),4096,PAGE_NOACCESS,&old)!=0,"actual owned report cursor page unavailable before Submit");
  check(!session->Submit(request(1)),"SEH contains report cursor read failure before Driver consumes request");
  DWORD ignored=0;check(VirtualProtect(reinterpret_cast<void*>((world+0x165A)&~uintptr_t(4095)),4096,old,&ignored)!=0,"restore only owned fixture cursor page");
  ss::Report sr{};session->Snapshot(sr);check(sr.stopped&&!sr.save.generation&&!sr.save.entries&&!binds&&!queues,"unreadable cursor stops without binding or generation consumption");summary();return failed?1:0;
 }
 if(mode=="pending-flag"||mode=="pending-queue"){
  const bool flag=mode=="pending-flag";reportPending(flag,!flag);check(!session->Submit(request(1)),"pending reports deny request without consuming generation");
  check(!saveReport().entries&&!binds&&!queues&&!reportFlushes,"denial does not call native User or discard report");
  check(get<unsigned>(user+0x660)==unsigned(flag)&&get<std::uint64_t>(b+0x1FC98B8)==unsigned(!flag),"pending fields unchanged by owner");
  // Test business explicitly settles reports; this is not Owner auto-draining.
  reportPending(false,false);
 }
 check(session->Submit(request(1)),"first actual save accepted after negative checks");
 if(mode=="entry-flag"||mode=="entry-queue"){
  const bool flag=mode=="entry-flag";reportPending(flag,!flag);check(FreshDispatch(0,user)==0,"late entry hazard suppresses exactly this unclaimed callback");
  auto r=saveReport();ss::Report sr{};session->Snapshot(sr);check(sr.stopped&&!r.entries&&!r.original_returned&&!binds&&!queues&&!sr.bridges[0].native_returned,"cancelled admission manufactures no native return");
  check(get<unsigned>(user+0x660)==unsigned(flag)&&get<std::uint64_t>(b+0x1FC98B8)==unsigned(!flag),"cancelled entry preserves pending report");
  input->Stop();check(dispatch(0,user)==0,"explicit cancellation releases original processing on next call");
  check(saveReport().status==fs::Status::Cancelled,"driver request reaches actual cancellation state");summary();return failed?1:0;
 }
 check(dispatch(0,user)==0,"real raw User ran through successor and action gate");
 const bool beforeBind=mode=="late-flag"||mode=="late-queue"||mode=="consumed"||mode=="local-aba-blocked"||mode=="storage-append";
 if(beforeBind){if(mode!="storage-append"){check(!reportFlushes&&!selectionBodies&&!tailBodies,"early cut bypasses actual report consumer and downstream selection/action doubles");check(get<unsigned>(user+0x660)||get<std::uint64_t>(b+0x1FC98B8),"late pending report survives exact native return");}fs::Artifact a{};check(!binds&&!queues&&!session->CopyArtifact(1,a),"observed late report prevents binder/queue/artifact");summary();return failed?1:0;}
 if(mode=="early-bypass"){check(commands==1&&!reportFlushes&&!selectionBodies&&!tailBodies&&saveReport().status==fs::Status::Queued,"earlier updater double still writes despite actual downstream gate");summary();return failed?1:0;}
 check(saveReport().status==fs::Status::Queued&&binds==1&&queues==1,"first native binder and queue are actual calls");completeSave();
 fs::Artifact first{};
 if(mode=="copy-flag"||mode=="copy-cursor"){
  check(saveReport().status==fs::Status::Complete,"native save completed before copy-time hazard");
  if(mode=="copy-flag")reportPending(true,false);else put<unsigned short>(world+0x165A,get<unsigned short>(world+0x165A)+1);
  check(!session->CopyArtifact(1,first)&&first.bytes.empty(),"completed receipt alone cannot bypass current report export guard");
  ss::Report sr{};session->Snapshot(sr);check(sr.error==ss::Error::Input&&sr.stopped&&!session->Submit(request(2)),"Copy hazard is ordinary Owner terminal failure and refuses next Submit");summary();return failed?1:0;
 }
 if(mode=="during-save"){check(!session->CopyArtifact(1,first)&&binds==1&&queues==1,"committed save drains but changed reports cannot export bytes");summary();return failed?1:0;}
 check(session->CopyArtifact(1,first)&&!first.bytes.empty(),"CopyArtifact comes from same actual Owner native readback");packet(first,"first.packet");
 if(mode=="external-aba"){
  check(reportFlushes==2&&get<unsigned>(user+0x660)==0&&get<std::uint64_t>(b+0x1FC98B8)==0,"explicit remaining ABA bypass: external producer/consumer double outside covered report cut");
  // This demonstrates the boundary, NOT complete report write exclusion.
  summary();return failed?1:0;
 }
 put<unsigned char>(world+0x37,21);put<unsigned short>(world+0x165A,1);check(session->Submit(request(2)),"same retained Owner accepts distinct second request with its own report baseline");
 fs::Artifact old{};check(!session->CopyArtifact(1,old)&&old.bytes.empty(),"second admission cannot let new cursor attest old-generation artifact");report::Report rr{};check(report::Snapshot(session,rr)&&!rr.revoked,"stale copy request does not cancel the second generation");
 check(dispatch(0,user)==0,"second actual User enqueue");completeSave();fs::Artifact second{};
 check(session->CopyArtifact(2,second)&&first.bytes!=second.bytes&&binds==2&&queues==2&&nativeReads==4,"same real Owner completes two distinct file/readback generations");packet(second,"second.packet");
 check(!reportFlushes&&!selectionBodies&&!tailBodies&&!upstreamCalls&&!updaterCalls&&!upstreamWrites,"both saves bypass known singleton/updater and all covered downstream consumers");ag::Report ar{};input->Snapshot(ar);check(ar.userTailSuppressed==4,"four real User calls choose original-shaped exit through early bridge");
 check(!session->Submit(request(3)),"bounded owner does not create third request");summary();return failed?1:0;
}
