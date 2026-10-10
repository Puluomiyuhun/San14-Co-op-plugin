#pragma once
#include "reward_menu_dispatch.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

// Value publication only. No hook installation or gameplay permission.
// Begin/Publish belong to the original host thread; Read is a locked value copy.
namespace reward_menu_closed_publication {
enum class Rejection : unsigned {None, Binding, Thread, ForeignOwner, NotReturned, NotClosed, Consumed, TakeFailed};
struct Receipt {
 unsigned version=1,thread=0;
 reward_menu_handoff::Proposal proposal{};
 uint64_t dispatchEntered=0,dispatchSelected=0,storageReleased=0,cleanupBoundaries=0,dispatchReturned=0;
 bool teardown_observed=false,production_permit=false;
};
struct Report {bool bound=false,published=false,attempted=false;uint64_t rejected=0;Rejection last_rejection=Rejection::None;};
class Publication final {
public:
 bool Begin(uint64_t base,uint64_t manager,reward_menu_dispatch::Guard&,reward_menu_lifecycle::Owner&,unsigned host_thread)noexcept;
 bool Publish(reward_menu_dispatch::Guard&,reward_menu_lifecycle::Owner&)noexcept;
 bool Read(Receipt&)const noexcept;
 Report Snapshot()const noexcept;
private:
 bool reject(Rejection)noexcept;
 mutable SRWLOCK lock_=SRWLOCK_INIT;
 reward_menu_dispatch::Guard*guard_=nullptr;
 reward_menu_lifecycle::Owner*life_=nullptr;
 unsigned thread_=0;bool bindAttempted_=false;
 Receipt receipt_{};Report report_{};
};
}
