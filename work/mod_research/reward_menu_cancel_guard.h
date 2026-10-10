#pragma once
#include "reward_menu_creation.h"
#include "reward_menu_closed_publication.h"
#include <atomic>
// Explicit successor to reward_menu_session: one creation claim, one mutually
// exclusive confirm/cancel choice. Do not layer both owners on the same menu.
// No installer, UI event mapping, parent lease or production permission.
namespace reward_menu_cancel_guard {
enum class Phase:unsigned {New,Bound,Queued,Consuming,Finalized,Closed,Published,Fault};
enum class Choice:unsigned {None,Confirm,Cancel};
struct Report {Phase phase=Phase::New;Choice choice=Choice::None;unsigned error=0;uint64_t rejected=0,foreignRejected=0,notifications=0,entered=0,selected=0,finalized=0,closed=0,storageReleased=0,boundaries=0,returned=0;bool active=false,production_permit=false;};
struct CancelReceipt {unsigned version=1,thread=0,year=0,month=0,day=0,force=0;uint64_t generation=0,world=0,user=0,menu=0;bool cancelled=false,teardown_observed=false,proposal_created=false,production_permit=false;};
class Owner final {
public:
 bool Begin(uint64_t generation,const char*menu_id,unsigned relay_rva,unsigned district_id,uint64_t callback)noexcept;
 bool ConfirmAndQueue()noexcept;
 // An explicitly invoked notification source; payload is forwarded unchanged.
 // Original code ignores it. This API does not authenticate a physical button.
 bool CancelNotify(uint64_t generation,uint64_t callback,uint64_t payload)noexcept;
 bool Enter()noexcept; // cancellation dispatcher boundary, before native 509FE0
 bool Select(uint64_t manager,uint64_t menu,uint64_t request,uint64_t end)noexcept;
 bool Finalized(uint64_t manager,uint64_t menu)noexcept;
 bool Freed(uint64_t manager,uint64_t menu)noexcept;
 bool CopiedStorageReleased(uint64_t storage)noexcept;
 bool AfterCleanup()noexcept;
 bool Returned()noexcept;
 bool ReadCancel(CancelReceipt&)const noexcept;
 bool ReadConfirmed(reward_menu_closed_publication::Receipt&)const noexcept;
 Report Snapshot()const noexcept{auto value=r_;value.foreignRejected=foreignRejected_.load();return value;} // same native thread only
private:
 bool fail(unsigned)noexcept;bool reject()noexcept;bool thread()const noexcept;bool onThread()noexcept;
 bool identity()const;bool shape(unsigned,bool)const;bool empty()const;bool source()const;bool graph()const;
 bool guarded()noexcept;
 reward_menu_creation::Evidence creation_{};reward_menu_handoff::Binding binding_{};
 reward_menu_lifecycle::Owner confirmation_;reward_menu_dispatch::Guard confirmationGuard_;
 reward_menu_closed_publication::Publication confirmationPublication_;
 Report r_{};uint64_t callback_=0,copied_=0;bool cancelPublished_=false;
 std::atomic<bool> attempted_{false};std::atomic<DWORD> nativeThread_{0};std::atomic<uint64_t> foreignRejected_{0};
 mutable SRWLOCK receiptLock_=SRWLOCK_INIT;CancelReceipt receipt_{};
};
}
