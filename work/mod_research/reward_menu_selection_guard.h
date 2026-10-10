#pragma once
#include <cstdint>
// Same-host-thread source observer. No installer, continuation or suspend claim.
// The enclosing owner supplies immutable, approved probe addresses and actual
// return PCs captured by those probes, never caller-provided gameplay authority.
namespace reward_menu_selection_guard {
enum class Phase:unsigned {New,Bound,Calling,Created,Waiting,Event,WaitReturned,CallReturned,Complete,Taken,Fault};
enum class Error:unsigned {None,Order,Thread,Source,Identity,Task,Selection,Event,Result,Exception};
struct Config {
 uintptr_t base=0,reward=0,layout=0,states[5]{},task=0;
 uintptr_t relays[4]{},entries[4]{};
 uint64_t generation=0;unsigned thread=0;char menu_id[33]{};
};
struct Report {Phase phase=Phase::New;Error error=Error::None;unsigned created=0,waited=0,events=0,waitReturned=0,callReturned=0,completed=0,taken=0,eventCode=0;bool production_permit=false,native_suspend_proven=false;};
struct Receipt {uint64_t generation=0;unsigned thread=0,eventCode=0;char menu_id[33]{};bool accepted=false,selection_return_observed=false,production_permit=false,native_suspend_proven=false;};
class Guard final {
public:
 bool Bind(const Config&)noexcept;
 bool BeginCall(uintptr_t descriptor,uintptr_t return_pc)noexcept;
 bool Created(uintptr_t selection,uintptr_t parameters,uintptr_t return_pc)noexcept;
 bool BeforeWait(uintptr_t reward,uintptr_t return_pc)noexcept;
 bool Event(uintptr_t reward,uintptr_t event,uintptr_t return_pc)noexcept;
 bool WaitReturned(uintptr_t reward,uintptr_t return_pc)noexcept;
 bool CallReturned(unsigned result,uintptr_t return_pc)noexcept;
 bool Finish()noexcept;
 bool Take(Receipt&)noexcept;
 Report Snapshot()const noexcept{return r_;} // bound host thread only
private:
 bool fail(Error)noexcept;bool thread()const noexcept;bool source(bool installed)const;
 bool shape(unsigned)const;bool identity()const;bool callback()const;
 Config c_{};Report r_{};bool once_=false;uintptr_t selection_=0;
};
}
