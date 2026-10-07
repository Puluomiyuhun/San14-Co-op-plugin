// Owned source adaptation, not a production validator or native body.
// Own-process composition only. Reuse the frozen complete Session fixture body;
// this shim changes wiring, never receipts or production Session behavior.
#include "checkpoint_bound_forward_admission_controller.h"
#include "checkpoint_authorized_forward_admission_controller.h"
#include "checkpoint_native_queue_adapter_core.h"
#include "checkpoint_native_queue_adapter_profile.h"
namespace realad=checkpoint_authorized_forward_admission;
namespace qa=checkpoint_native_queue_adapter;
namespace checkpoint_authorized_fixture_admission {
using Config=realad::Config;using Report=realad::Report;using Error=realad::Error;
using Event=realad::Event;using Original=realad::Original;
class Controller {
public:
 realad::Controller& inner=checkpoint_complete_live_owner::owner.admission;
 bool Initialize(const Config&) noexcept;
 bool Snapshot(Report&r)const noexcept{return inner.Snapshot(r);}
 void Stop()noexcept;
 static void Before(const CheckpointPushFrame*f,void*p)noexcept{realad::Controller::Before(f,&static_cast<Controller*>(p)->inner);}
 static void After(const CheckpointPushFrame*f,void*p)noexcept{realad::Controller::After(f,&static_cast<Controller*>(p)->inner);}
 static void UserAfter(void*p,checkpoint_forward_native_session::Session&s,const CheckpointPushFrame*f)noexcept{realad::Controller::UserAfter(&static_cast<Controller*>(p)->inner,s,f);}
};
}
#define checkpoint_bound_forward_admission checkpoint_authorized_fixture_admission
#define CheckpointBoundForwardAdmissionOriginal CheckpointAuthorizedForwardAdmissionOriginal
#define GuestSessionMenuBody PriorFixtureMenuBody
#define wmain FrozenAdmissionMain
#include "checkpoint_complete_live_owner_chain_body.inc"
#undef wmain
#undef GuestSessionMenuBody
#undef CheckpointBoundForwardAdmissionOriginal
#undef checkpoint_bound_forward_admission

static qa::Adapter& queueAdapter=checkpoint_complete_live_owner::owner.queue;
static std::wstring focusedCase;
static pd::Ticket handedTicket{};
static CheckpointPushFrame handedFrame{};
static const void* handedController=nullptr;
static unsigned authorizationCalls=0,authorizationExact=0;
static uintptr_t originalList=0,originalDialog=0;
static bool foreignAuthorizationResult=false;
static bool queueGuard(void*,qa::Point)noexcept{
 return base==layout.config.base&&cache==layout.config.cache&&
  at<uintptr_t>(base+0x2025318)==cache&&at<uintptr_t>(base+0x1FCA1E0)==root&&
  at<uintptr_t>(root+0x85130)==world&&at<WORD>(world+0x34)==203&&
  at<BYTE>(world+0x3A)==12;
}
static DWORD WINAPI foreignAuthorization(void*){
 foreignAuthorizationResult=queueAdapter.Authorize(handedTicket,handedFrame,handedController);
 return 0;
}
static bool authorizeActual(void*,const pd::Ticket&t,const CheckpointPushFrame&f,const void*who)noexcept{
 ++authorizationCalls;handedTicket=t;handedFrame=f;handedController=who;
 const bool exact=t.serial&&t.call_id==f.call_id&&who==&admission.inner&&
  f.call_id==capturedAdmissionFrame.call_id&&f.thread_id==GetCurrentThreadId()&&
  f.caller_entry_rsp==capturedAdmissionFrame.caller_entry_rsp&&
  !memcmp(f.args,capturedAdmissionFrame.args,sizeof f.args);
 check(exact,"private ticket and original frame arrive directly from actual controller");
 if(exact)++authorizationExact;
 if(focusedCase==L"authorize-denied")return false;
 if(focusedCase==L"wrong-call-authorize"){auto bad=f;++bad.call_id;return queueAdapter.Authorize(t,bad,who);}
 if(focusedCase==L"wrong-owner-authorize")return queueAdapter.Authorize(t,f,reinterpret_cast<const char*>(who)+1);
 if(focusedCase==L"wrong-thread-authorize"){
  auto h=CreateThread(nullptr,0,foreignAuthorization,nullptr,0,nullptr);
  if(!h)return false;
  check(WaitForSingleObject(h,5000)==WAIT_OBJECT_0,"foreign authorization worker joined");
  CloseHandle(h);return foreignAuthorizationResult;
 }
 const bool ok=queueAdapter.Authorize(t,f,who);
 if(ok&&focusedCase==L"stop-after-authorize")admission.Stop();
 if(ok&&focusedCase==L"block-after-authorize")wrongThreadAfter();
 return ok;
}
static void authorizedTrace(void*,ad::Event event)noexcept{
 admissionEvent(nullptr,event);
 if(event==ad::Event::Close){ad::Report r{};admission.Snapshot(r);if(r.blocked||r.stopped)queueAdapter.Stop();}
}
static pd::Span resolvedActual(void*,uintptr_t address,size_t bytes)noexcept{
 ++resolvedQueues;return queueAdapter.Resolve(address,bytes);
}
static void queueNativeOwned(void*manager,const char*name,void*mode,void*closureBytes){
 check(uintptr_t(manager)==base+0x19E7310&&uintptr_t(name)==base+0x12DD6E0&&
  !strcmp(name,"CSaveLoadState"),"real queue adapter four native arguments");
 const DWORD* values=static_cast<const DWORD*>(mode);
 check(values[0]==0&&values[1]==0,"type0 load-menu mode");
 for(unsigned i=0;i<64;++i)check(!static_cast<const unsigned char*>(closureBytes)[i],"empty native callback storage");
 nativeQueueDouble(nullptr); // Original owned body writes the queue, never an observer receipt.
 put<std::uint64_t>(base+0x19E7310+0x38,64);
 // Native constructor leaves these empty; original Menu Update creates its UI later.
 for(auto off:{0x48,0x50,0x68,0x470,0x478})put<uintptr_t>(layout.config.menu+off,0);
}
extern "C" void GuestSessionMenuBody(std::uint64_t self,std::uint64_t a,std::uint64_t b,std::uint64_t c){
 put<uintptr_t>(self+0x470,originalList);put<uintptr_t>(self+0x478,originalDialog);
 PriorFixtureMenuBody(self,a,b,c);
}
bool checkpoint_authorized_fixture_admission::Controller::Initialize(const Config&old)noexcept{
 auto c=old;
 for(const auto&anchor:CheckpointNativeQueueAnchors)memcpy(reinterpret_cast<void*>(base+anchor.rva),anchor.bytes,anchor.size);
 put<std::uint64_t>(base+0x19E7310+0x18,16);c.pending.stack.size=16*8;
 originalList=at<uintptr_t>(layout.config.menu+0x470);originalDialog=at<uintptr_t>(layout.config.menu+0x478);
 c.pending.resolve_created_queue=resolvedActual;c.pending.queue_resolver_context=nullptr;
 qa::Config q{};q.pending=c.pending;q.controller_identity=&inner;q.cache=cache;
 q.validate_external=queueGuard;q.fixture_native=queueNativeOwned;
 q.fixture_user_caller=uintptr_t(&GuestSessionUserReturn);
 check(queueAdapter.Initialize(q),"actual queue capability adapter initialized");
 c.authorize_queue=authorizeActual;c.authorize_queue_context=nullptr;
 c.queue=qa::Adapter::QueueCallback;c.queue_context=&queueAdapter;c.trace=authorizedTrace;
 if(focusedCase==L"missing-authorizer")c.authorize_queue=nullptr;
 return inner.Initialize(c);
}
void checkpoint_authorized_fixture_admission::Controller::Stop()noexcept{StopCheckpointCompleteLiveOwner(nullptr);}

static bool configureFocused(wchar_t**argv){
#include "checkpoint_authorized_forward_admission_setup.inc"
}
static int reportAuthorization(int priorResult){
 ad::Report a{};admission.Snapshot(a);qa::Report q{};queueAdapter.Snapshot(q);ns::Report s{};session.Snapshot(s);
 check(!q.private_ticket_authenticated_by_adapter&&!q.world_ready&&!a.full_input_hold,"no invented private ticket authentication or readiness");
 if(focusedCase==L"late-replay"){
  check(!queueAdapter.Authorize(handedTicket,handedFrame,handedController),"old ticket cannot authorize twice");
  check(!queueAdapter.Queue().data,"old capability cannot run queue again");
  qa::Report after{};queueAdapter.Snapshot(after);check(after.native_calls==1,"late replay retains one original native queue");
 }
 printf("{\"authorization_case\":\"%ls\",\"passed\":%s,\"failures\":%u,\"prior_exit\":%d,\"authorization_calls\":%u,\"exact_ticket_frame\":%u,\"controller_authorize_calls\":%u,\"controller_authorized\":%u,\"adapter_authorized\":%u,\"adapter_native_calls\":%u,\"adapter_native_returned\":%u,\"adapter_result_verified\":%u,\"adapter_resolver\":%u,\"adapter_error\":%u,\"adapter_stopped\":%s,\"admission_queue\":%u,\"cas\":%u,\"identity\":%u,\"game_access\":false,\"native_queue_is_owned_double\":true}\n",
  focusedCase.c_str(),!failures&&!priorResult?"true":"false",failures,priorResult,authorizationCalls,authorizationExact,a.queue_authorize_calls,a.queue_authorized,q.authorized,q.native_calls,q.native_returned,q.native_result_verified,q.resolver_calls,unsigned(q.error),q.stopped?"true":"false",a.queue_calls,s.casPublished,s.identity.receiptReady);
 return failures||priorResult?1:0;
}
int CompleteOwnerChainMain(int argc,wchar_t**argv){
 if(argc!=5)return 2;focusedCase=argv[1];
 const bool denial=focusedCase==L"authorize-denied"||focusedCase==L"wrong-call-authorize"||
  focusedCase==L"wrong-owner-authorize"||focusedCase==L"wrong-thread-authorize"||
  focusedCase==L"stop-after-authorize"||focusedCase==L"block-after-authorize";
 if(!denial&&focusedCase!=L"missing-authorizer"){
  wchar_t success[]=L"success-early";auto arg=argv[1];if(focusedCase==L"late-replay")argv[1]=success;
  const int result=FrozenAdmissionMain(argc,argv);argv[1]=arg;return reportAuthorization(result);
 }
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);scenario=L"success-early";setup();
 if(focusedCase==L"missing-authorizer"){
  // Minimal structurally valid controller config reaches the mandatory callback check.
  realad::Config c{};c.session=&session;c.attempt=1;c.original=&GuestSessionUserOriginal;c.expected_prefetch_site=uintptr_t(&HwbpFixtureBeforeCall);
  c.queue=qa::Adapter::QueueCallback;c.pending.states[4]=layout.config.states[4];
  hw::Config h{};h.binding.attempt.fill(0xA1);h.binding.attachment.fill(0xB2);h.binding.owner_generation=1;h.site_rip=uintptr_t(&HwbpFixtureBeforeCall);
  check(hw::Initialize(hardwareContext,h),"valid provider for mandatory-callback rejection");c.prefetch_provider=hw::MakeProvider(hardwareContext);
  check(!admission.inner.Initialize(c),"missing mandatory authorizer rejected before publication");
  check(!queueBodies&&!userBodies,"missing authorizer cannot run originals or queue");return reportAuthorization(0);
 }
 check(configureFocused(argv),"configure focused real Session/admission chain");
 check(!invokeInitialUser(),"authorization rejection still returns actual native original");
 ad::Report a{};admission.Snapshot(a);qa::Report q{};queueAdapter.Snapshot(q);ns::Report s{};session.Snapshot(s);
 check(authorizationCalls==1&&authorizationExact==1&&a.queue_authorize_calls==1,"one authentic direct ticket handoff");
 check(a.blocked&&!a.queue_calls&&!q.native_calls&&!queueBodies&&!s.casPublished&&userBodies==1&&a.closed==1&&!a.active,"authorization failure cannot queue/CAS or swallow original");
 if(focusedCase==L"stop-after-authorize"||focusedCase==L"block-after-authorize")check(q.authorized==1&&q.stopped&&a.queue_authorized==1,"cancelled minted capability revoked by owner close");
 else check(!q.authorized&&!a.queue_authorized,"denied capability never authorizes controller queue");
 check(session.RestoreBeforeCommit(),"rejected pre-CAS hooks restore");return reportAuthorization(0);
}
