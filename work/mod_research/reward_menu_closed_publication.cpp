#include "reward_menu_closed_publication.h"
namespace reward_menu_closed_publication {
bool Publication::reject(Rejection r)noexcept{++report_.rejected;report_.last_rejection=r;return false;}
bool Publication::Begin(uint64_t base,uint64_t manager,reward_menu_dispatch::Guard&g,reward_menu_lifecycle::Owner&l,unsigned host)noexcept{
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try{
  if(bindAttempted_){reject(Rejection::Binding);__leave;}bindAttempted_=true;
  if(!host||host!=GetCurrentThreadId()){reject(Rejection::Thread);__leave;}
  // Establish the association ourselves, rather than accepting two unrelated
  // successful reports supplied after their respective dispatches.
  if(!g.Enter(base,manager,l)){reject(Rejection::Binding);__leave;}
  const auto d=g.Snapshot();const auto s=l.Snapshot();
  if(d.entered!=1||!d.active||d.error||d.rejected||d.selected||d.returned||d.production_permit||
     s.phase!=reward_menu_lifecycle::Phase::Queued||s.error||s.queued!=1||s.selected||s.taken||s.production_permit){reject(Rejection::Binding);__leave;}
  guard_=&g;life_=&l;thread_=host;report_.bound=true;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Publication::Publish(reward_menu_dispatch::Guard&g,reward_menu_lifecycle::Owner&l)noexcept{
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try{
  if(!report_.bound){reject(Rejection::Binding);__leave;}
  // Do not read the same-thread-only Guard/Owner from a foreign thread.
  if(GetCurrentThreadId()!=thread_){reject(Rejection::Thread);__leave;}
  if(&g!=guard_||&l!=life_){reject(Rejection::ForeignOwner);__leave;}
  if(report_.attempted){reject(Rejection::Consumed);__leave;}
  const auto d=g.Snapshot();
  if(d.active||d.error||d.rejected||d.entered!=1||d.selected!=1||d.storageReleased!=1||d.boundaries!=1||d.returned!=1||d.production_permit){reject(Rejection::NotReturned);__leave;}
  const auto s=l.Snapshot();
  if(s.phase!=reward_menu_lifecycle::Phase::Closed||s.error||s.queued!=1||s.selected!=1||s.finalized!=1||s.closed!=1||s.taken||s.production_permit){reject(Rejection::NotClosed);__leave;}
  // Claim before the one consuming call. A failed freshness check is terminal.
  report_.attempted=true;reward_menu_lifecycle::ClosedTicket ticket{};
  if(!l.TakeClosed(ticket)||!ticket.teardown_observed||ticket.production_permit){reject(Rejection::TakeFailed);__leave;}
  Receipt value{};value.thread=thread_;value.proposal=ticket.proposal;value.dispatchEntered=d.entered;
  value.dispatchSelected=d.selected;value.storageReleased=d.storageReleased;value.cleanupBoundaries=d.boundaries;
  value.dispatchReturned=d.returned;value.teardown_observed=true;
  receipt_=value;report_.published=true;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Publication::Read(Receipt&out)const noexcept{
 AcquireSRWLockShared(&lock_);out=Receipt{};const bool ready=report_.published;if(ready)out=receipt_;ReleaseSRWLockShared(&lock_);return ready;
}
Report Publication::Snapshot()const noexcept{AcquireSRWLockShared(&lock_);const auto out=report_;ReleaseSRWLockShared(&lock_);return out;}
}
