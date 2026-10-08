#include "a_save_report_owner.h"
#define FixtureUserBody ReportLegacyUserBody
#define FixtureSaveBody ReportLegacySaveBody
#define ActionInjectTail ReportLegacyInjectTail
#include "a_save_report_action_fixture.inc"
#undef FixtureUserBody
#undef FixtureSaveBody
#undef ActionInjectTail

namespace report=a_save_report_owner;
static unsigned reportFlushes=0,existsCalls=0;
static uintptr_t reportHead=0;
extern "C" {uintptr_t ReportEarlySnippet=0;void ReportEarlyInvoke(uintptr_t);}
static void reportPending(bool flag,bool queue){
 put<unsigned>(user+0x660,flag?1:0);put<std::uint64_t>(b+0x1FC98B8,queue?1:0);
 for(unsigned i=0;i<3;++i)put<uintptr_t>(reportHead+i*8,queue?reportHead+0x100:reportHead);
}
// Explicit business double, NOT execution of archived 2A1EC0 or 835800.
// The 19-byte User branch/call/clear around this double is actual known code.
extern "C" void ReportFlushDouble(){
 ++reportFlushes;if(mode!="aba-no-index")put<unsigned short>(world+0x165A,get<unsigned short>(world+0x165A)+1);
 reportPending(true,false);
}
extern "C" std::uint64_t FixtureUserBody(std::uint64_t self,std::uint64_t a,std::uint64_t c,std::uint64_t d){return ReportLegacyUserBody(self,a,c,d);}
extern "C" void ActionInjectTail(){
 ReportLegacyInjectTail();
 if(mode=="late-flag")reportPending(true,false);
 if(mode=="late-queue")reportPending(false,true);
 if(mode=="consumed"||mode=="aba-no-index")reportPending(true,true);
 ReportEarlyInvoke(user);
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
 const unsigned char branch[]={0x48,0x83,0xec,0x28,0x39,0xae,0x60,0x06,0,0,0x74,0x0b,0xe8,0x0b,0x83,0xea,0xff,0x89,0xae,0x60,0x06,0,0,0x48,0x83,0xc4,0x28,0xc3};
 writeCode(b+0x3F9BA4,branch,sizeof branch);ReportEarlySnippet=b+0x3F9BA4;
 const unsigned char cursor[]={0x66,0x89,0xb9,0x5a,0x16,0,0},clear[]={0x48,0xc7,0x05,0xeb,0x94,0xd8,0x01,0,0,0,0};
 writeCode(b+0x835C2C,cursor,sizeof cursor);writeCode(b+0x2403C2,clear,sizeof clear);
 DWORD old=0;VirtualProtect(reinterpret_cast<void*>(b+0x2A1000),4096,PAGE_READWRITE,&old);jump(b+0x2A1EC0,reinterpret_cast<void*>(&ReportFlushDouble));
 const unsigned char uw[]={1,4,1,0,4,0x42,0,0};memcpy(reinterpret_cast<void*>(b+0x2200040),uw,sizeof uw);
 // Single-function range avoids the multi-table envelope collision found in B.
 auto*t=new RUNTIME_FUNCTION{0x3F9BA4,0x3F9BC0,0x2200040};check(RtlAddFunctionTable(t,1,b)!=0,"actual report snippet unwind registered");
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
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"binds\":%u,\"queues\":%u,\"native_reads\":%u,\"report_flush_doubles\":%u,\"submit_rejected\":%llu,\"entry_suppressed\":%llu,\"after_rejected\":%llu,\"storage_rejected\":%llu,\"revoked\":%s,\"native_user_returned\":%llu,\"save_native_returned\":%llu,\"save_status\":%u,\"full_input_held\":false,\"save_authorized\":false,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,binds,queues,nativeReads,reportFlushes,rr.submitRejected,rr.entrySuppressed,rr.afterRejected,rr.storageRejected,rr.revoked?"true":"false",sr.bridges[0].native_returned,sr.bridges[1].native_returned,unsigned(sr.save.status));
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=4)return 2;mode=argv[1];setup();machinery();reportMachinery();
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
 check(input->Initialize(ic)&&input->PreparedPlan(plan),"unchanged action gate composes with successor Owner ABI");if(failed){summary();return 3;}publish();check(input->Arm()&&input->Hold(ic.binding,true,1),"actual action source publication and hold");check(gameDispatch()==0,"actual Game scoped global UI/panel isolation");
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
 const bool beforeBind=mode=="late-flag"||mode=="late-queue"||mode=="consumed"||mode=="storage-append";
 if(beforeBind){fs::Artifact a{};check(!binds&&!queues&&!session->CopyArtifact(1,a),"observed late report prevents binder/queue/artifact");summary();return failed?1:0;}
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
 if(mode=="aba-no-index"){
  check(reportFlushes==2&&get<unsigned>(user+0x660)==0&&get<std::uint64_t>(b+0x1FC98B8)==0,"explicit remaining ABA bypass: report produced/consumed inside each native User");
  // This demonstrates the boundary, NOT complete report write exclusion.
  summary();return failed?1:0;
 }
 put<unsigned char>(world+0x37,21);put<unsigned short>(world+0x165A,1);check(session->Submit(request(2)),"same retained Owner accepts distinct second request with its own report baseline");
 fs::Artifact old{};check(!session->CopyArtifact(1,old)&&old.bytes.empty(),"second admission cannot let new cursor attest old-generation artifact");report::Report rr{};check(report::Snapshot(session,rr)&&!rr.revoked,"stale copy request does not cancel the second generation");
 check(dispatch(0,user)==0,"second actual User enqueue");completeSave();fs::Artifact second{};
 check(session->CopyArtifact(2,second)&&first.bytes!=second.bytes&&binds==2&&queues==2&&nativeReads==4,"same real Owner completes two distinct file/readback generations");packet(second,"second.packet");
 check(!session->Submit(request(3)),"bounded owner does not create third request");summary();return failed?1:0;
}
