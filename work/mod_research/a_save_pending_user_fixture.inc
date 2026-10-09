#include "a_save_covered_gate.h"
#include "a_save_covered_owner.h"
#include "a_save_pending_user_owner.h"
extern "C" LONG ASaveCoveredGateFixtureWrongGeneration;
static unsigned coveredCalls=0,queuedWindows=0;
static std::wstring coveredCase;
extern "C" {std::uint64_t CoveredFixtureZeroReturn=0;}
extern "C" void coveredReturnModel(){}
static void coveredUser(){
 if(coveredCase==L"cursor-drift"&&!coveredCalls)put<unsigned short>(world+0x165A,get<unsigned short>(world+0x165A)+1);
 const auto original=ActionUserSnippet;ActionUserSnippet=reinterpret_cast<uintptr_t>(&coveredReturnModel);
 CoveredFixtureZeroReturn=1;{ScopedNativeCurrent current(user);need(FreshDispatch(0,user)==0,"covered native result is zero");}
 CoveredFixtureZeroReturn=0;ActionUserSnippet=original;++coveredCalls;
}
static void queuedGame(){
 const auto m=b+0x19E7310,queue=get<uintptr_t>(m+0x40);need(get<std::uint64_t>(m+0x10)==5&&get<std::uint64_t>(m+0x30)==1,"actual queued Save");
 if(coveredCase==L"foreign")put<unsigned>(queue,1);
 if(coveredCase==L"multi")put<std::uint64_t>(m+0x30,2);
 if(coveredCase==L"wrong-generation")InterlockedExchange(&ASaveCoveredGateFixtureWrongGeneration,1);
 need(scopedGame()==0,"queued-before-apply actual Game callbacks");ag::Report g{};input->Snapshot(g);ss::Report u{};session->Snapshot(u);++queuedWindows;
 if(coveredCase==L"normal"||coveredCase==L"cursor-drift"||coveredCase==L"user-foreign")need(g.error==ag::Error::None&&!u.stopped&&!unsigned(u.error)&&!ASaveCoveredGateFirstFailure.stage,"strict owned pending Save accepted");
 else {
  need(g.error==ag::Error::Input&&u.stopped&&!unsigned(u.error)&&ASaveCoveredGateFirstFailure.stage==4,"foreign/multiple/mismatched queue rejected at layout");
  // Restore owned test data after terminal rejection; never retry the Gate.
  put<unsigned>(queue,0);put<std::uint64_t>(m+0x30,1);InterlockedExchange(&ASaveCoveredGateFixtureWrongGeneration,0);
 }
}
static void pendingUser(){
 if(coveredCase!=L"normal"&&coveredCase!=L"cursor-drift"&&coveredCase!=L"user-foreign")return;
 const auto queue=get<uintptr_t>(b+0x19E7310+0x40);
 if(coveredCase==L"user-foreign")put<unsigned>(queue,1);
 const auto result=scopedDispatch(0,user);
 ss::Report u{};session->Snapshot(u);report::Report r{};need(report::Snapshot(session,r),"pending User report");
 printf("PENDING value=%u stopped=%u error=%u entrySuppressed=%llu revoked=%u\n",result,unsigned(u.stopped),unsigned(u.error),r.entrySuppressed,unsigned(r.revoked));fflush(stdout);
#ifdef A_SAVE_PENDING_USER_SUCCESS
 a_save_pending_user::Report p{};need(a_save_pending_user::Snapshot(session,p),"pending diagnostic");
 if(coveredCase==L"user-foreign"){
  need(u.stopped&&u.error==ss::Error::Input&&r.revoked&&r.entrySuppressed==1&&!p.selected,"foreign pending User refuses");
  put<unsigned>(queue,0); // only owned fixture restoration after terminal rejection
 }else need(!result&&!u.stopped&&u.error==ss::Error::None&&!r.revoked&&!r.entrySuppressed&&p.selected==1&&p.claimed==1&&p.returned==1&&p.finally==1&&!p.rejected,"exact pending User actual claim and return");
#else
 need(u.stopped&&u.error==ss::Error::Input&&r.revoked&&r.entrySuppressed==1,"FAIL_REPRODUCED pending User rejected before original");
#endif
}
