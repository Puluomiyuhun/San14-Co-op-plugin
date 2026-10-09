#include "a_save_covered_gate.h"
#include "a_save_covered_owner.h"
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
 if(coveredCase==L"normal"||coveredCase==L"cursor-drift")need(g.error==ag::Error::None&&!u.stopped&&!unsigned(u.error)&&!ASaveCoveredGateFirstFailure.stage,"strict owned pending Save accepted");
 else {
  need(g.error==ag::Error::Input&&u.stopped&&!unsigned(u.error)&&ASaveCoveredGateFirstFailure.stage==4,"foreign/multiple/mismatched queue rejected at layout");
  // Restore owned test data after terminal rejection; never retry the Gate.
  put<unsigned>(queue,0);put<std::uint64_t>(m+0x30,1);InterlockedExchange(&ASaveCoveredGateFixtureWrongGeneration,0);
 }
}
