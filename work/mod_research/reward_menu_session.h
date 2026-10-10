#pragma once
#include "reward_menu_creation.h"
#include "reward_menu_closed_publication.h"
// Composition only: no source writes, installation, UI permission or reset.
// Native methods belong to the creation thread. Read copies an immutable receipt.
namespace reward_menu_session {
enum class Phase:unsigned {New,Bound,Queued,Published,Fault};
struct Report {Phase phase=Phase::New;unsigned error=0;uint64_t rejected=0;bool creation_taken=false,handoff_bound=false,production_permit=false;};
class Owner final {
public:
 bool Begin(uint64_t generation,const char*menu_id,unsigned relay_rva,unsigned district_id)noexcept;
 bool ConfirmAndQueue()noexcept;
 bool Select(uint64_t manager,uint64_t menu,uint64_t request,uint64_t end)noexcept;
 bool Finalized(uint64_t manager,uint64_t menu)noexcept;
 bool Freed(uint64_t manager,uint64_t menu)noexcept;
 bool CopiedStorageReleased(uint64_t storage)noexcept;
 bool AfterCleanup()noexcept;
 bool Returned()noexcept;
 bool Read(reward_menu_closed_publication::Receipt&)const noexcept;
 Report Snapshot()const noexcept{return report_;} // creation thread only
private:
 bool fail(unsigned)noexcept;bool current()noexcept;
 reward_menu_creation::Evidence creation_{};
 reward_menu_handoff::Binding binding_{};
 reward_menu_lifecycle::Owner life_;
 reward_menu_dispatch::Guard guard_;
 reward_menu_closed_publication::Publication publication_;
 Report report_{};bool attempted_=false;
};
}
