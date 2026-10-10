#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
// Local source observer only. No publisher, UI permission or execution lease.
namespace reward_menu_creation {
enum class Phase:unsigned {New,Bound,Dispatching,Creating,Named,Queued,Activated,Taken,Fault};
enum class Error:unsigned {None,Config,Source,Thread,Identity,Order,Command,Menu,Queue,Activation,Exception,Used};
struct Config {
 uintptr_t base=0,root=0,world=0,user=0,district=0,states[5]{},relays[4]{};
 std::uint64_t generation=0;DWORD thread=0;unsigned year=0,month=0,day=0,force=0;
};
struct Report {
 Phase phase=Phase::New;Error error=Error::None;uintptr_t menu=0,layout=0;
 unsigned dispatch=0,create=0,named=0,queued=0,activated=0,taken=0,rejected=0;
 bool production_permit=false,dispatcher_window_owned=false,parent_scope_proven=false;
};
struct Evidence {Config binding{};uintptr_t menu=0,layout=0;bool creation_observed=false,activation_observed=false,production_permit=false;};
bool Bind(const Config&)noexcept; // one process-local attempt; raw sources required
Report Snapshot()noexcept;
bool Take(std::uint64_t generation,Evidence&)noexcept; // one-shot evidence, never permission
}
extern "C" void RewardMenuCreationDispatch(uintptr_t,unsigned)noexcept;
extern "C" void RewardMenuCreationCreate(uintptr_t,uintptr_t,uintptr_t,uintptr_t)noexcept;
extern "C" void RewardMenuCreationName(uintptr_t,uintptr_t,uintptr_t)noexcept;
extern "C" void RewardMenuCreationActivation();
