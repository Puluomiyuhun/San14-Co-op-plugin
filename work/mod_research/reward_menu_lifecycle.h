#pragma once
#include "reward_menu_handoff_gate.h"
#include <cstdint>
// No publisher, detour, fault jump or gameplay permission is supplied here.
// A future dispatcher Owner must retain and enforce the complete native window.
namespace reward_menu_lifecycle {
enum class Phase:unsigned {New,Captured,Queued,Consuming,Finalized,Closed,Taken,Fault};
struct Config {
 uint64_t base=0,root=0,world=0,menu=0,layout=0,states[5]{},generation=0;
 unsigned thread=0,year=0,month=0,day=0,force=0;char menu_id[33]{};
};
struct Report {
 Phase phase=Phase::New;unsigned error=0;uint64_t queued=0,selected=0,finalized=0,closed=0,taken=0,rejected=0;
 bool production_permit=false,dispatcher_window_owned=false;
};
struct ClosedTicket {reward_menu_handoff::Proposal proposal{};bool teardown_observed=false;bool production_permit=false;};
class Owner final {
public:
 bool Capture(const Config&)noexcept; // consumes actual handoff TakeProposal once
 bool CloseOnce()noexcept; // invokes only the fixed native untagged enqueue routine
 bool BeforeConsume(uint64_t manager,uint64_t top,uint64_t request,uint64_t end)noexcept;
 bool AfterFinalize(uint64_t manager,uint64_t top)noexcept;
 bool AfterAllocator(uint64_t manager,uint64_t old_top)noexcept; // never reads old_top
 bool TakeClosed(ClosedTicket&)noexcept;
 Report Snapshot()const noexcept{return r_;} // same bound native thread only
private:
 Config c_{};reward_menu_handoff::Proposal p_{};Report r_{};bool attempted_=false;
 bool identity()const;bool shape(unsigned,bool)const;bool empty()const;
 bool fail(unsigned)noexcept;bool thread()const noexcept;
};
}
