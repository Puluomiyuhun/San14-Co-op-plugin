// Reuse the frozen complete archived dispatcher fixture. Only its C++ owners
// are wrapped; the archive ranges, ASM calls and native service doubles remain.
#include "reward_menu_closed_publication.h"
#include <thread>
#include <stdexcept>

namespace pub=reward_menu_closed_publication;
static void publicationNeed(bool value,const char*why){if(!value)throw std::runtime_error(why);}
namespace reward_menu_closed_fixture_lifecycle {
using Config=reward_menu_lifecycle::Config;
using ClosedTicket=reward_menu_lifecycle::ClosedTicket;
class Owner {
public:
 reward_menu_lifecycle::Owner inner;
 pub::Publication*publication=nullptr;reward_menu_dispatch::Guard*guard=nullptr;
 bool Capture(const Config&c)noexcept{return inner.Capture(c);}
 bool CloseOnce()noexcept{return inner.CloseOnce();}
 auto Snapshot()const noexcept{return inner.Snapshot();}
 bool TakeClosed(ClosedTicket&out){
  out={};if(!publication)return inner.TakeClosed(out);
  const bool ok=publication->Publish(*guard,inner);
  if(!ok){
   pub::Receipt old{};if(publication->Read(old)){
    publicationNeed(publication->Snapshot().published&&inner.Snapshot().taken==1,"duplicate cannot consume a second ticket");
    publicationNeed(old.proposal.generation==7&&old.proposal.officers[0]==97&&!old.production_permit,"duplicate cannot replace immutable receipt");
   }
   return false;
  }
  pub::Receipt value{};publicationNeed(publication->Read(value),"published immutable value readable");
  publicationNeed(value.thread==GetCurrentThreadId()&&value.dispatchReturned==1&&value.dispatchEntered==1&&value.dispatchSelected==1&&value.storageReleased==1&&value.cleanupBoundaries==1,"receipt binds complete original-thread dispatch");
  bool foreignRead=false;std::thread reader([&]{pub::Receipt copy{};foreignRead=publication->Read(copy)&&copy.proposal.generation==value.proposal.generation&&copy.proposal.officers[0]==97&&copy.teardown_observed&&!copy.production_permit;copy.proposal.officers[0]=123;});reader.join();
  publicationNeed(foreignRead,"cross-thread read gets value copy only");
  pub::Receipt unchanged{};publicationNeed(publication->Read(unchanged)&&unchanged.proposal.officers[0]==97,"reader mutation cannot change publication");
  out.proposal=value.proposal;out.teardown_observed=value.teardown_observed;out.production_permit=value.production_permit;return true;
 }
};
}
namespace reward_menu_closed_fixture_dispatch {
class Guard {
 reward_menu_dispatch::Guard inner;
 pub::Publication publication;
 reward_menu_closed_fixture_lifecycle::Owner*life=nullptr;
public:
 bool Enter(uint64_t base,uint64_t manager,reward_menu_closed_fixture_lifecycle::Owner&owner){
  life=&owner;owner.publication=&publication;owner.guard=&inner;
  return publication.Begin(base,manager,inner,owner.inner,GetCurrentThreadId());
 }
 bool Select(uint64_t m,uint64_t menu,uint64_t q,uint64_t end)noexcept{return inner.Select(m,menu,q,end);}
 bool Finalized(uint64_t m,uint64_t menu)noexcept{return inner.Finalized(m,menu);}
 bool Freed(uint64_t m,uint64_t menu)noexcept{return inner.Freed(m,menu);}
 bool CopiedStorageReleased(uint64_t p)noexcept{return inner.CopiedStorageReleased(p);}
 bool AfterCleanup(){
  const bool ok=inner.AfterCleanup();pub::Receipt absent{};
  publicationNeed(!publication.Publish(inner,life->inner)&&!publication.Read(absent),"native cleanup is not complete dispatcher return");
  publicationNeed(life->inner.Snapshot().taken==0,"early publication never consumes lifecycle ticket");return ok;
 }
 bool Returned(){
  publicationNeed(!publication.Publish(inner,life->inner)&&life->inner.Snapshot().taken==0,"after native return but before Guard receipt cannot publish");
  const bool ok=inner.Returned();
  if(ok){
   reward_menu_dispatch::Guard foreignGuard;reward_menu_lifecycle::Owner foreignLife;
   publicationNeed(!publication.Publish(foreignGuard,life->inner)&&publication.Snapshot().last_rejection==pub::Rejection::ForeignOwner,"unrelated dispatcher rejected");
   publicationNeed(!publication.Publish(inner,foreignLife)&&publication.Snapshot().last_rejection==pub::Rejection::ForeignOwner,"unrelated lifecycle rejected");
   bool refused=false;std::thread other([&]{refused=!publication.Publish(inner,life->inner);});other.join();
   publicationNeed(refused&&publication.Snapshot().last_rejection==pub::Rejection::Thread&&life->inner.Snapshot().taken==0,"foreign thread cannot consume close ticket");
  }else{
   pub::Receipt absent{};publicationNeed(!publication.Publish(inner,life->inner)&&!publication.Read(absent)&&!publication.Snapshot().attempted,"rejected actual dispatch cannot publish");
  }
  return ok;
 }
 auto Snapshot()const noexcept{return inner.Snapshot();}
};
}
// Headers already included before the fixture-only namespace substitutions.
#define reward_menu_dispatch reward_menu_closed_fixture_dispatch
#define reward_menu_lifecycle reward_menu_closed_fixture_lifecycle
#include "reward_menu_dispatch_fixture.cpp"
