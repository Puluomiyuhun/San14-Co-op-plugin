#pragma once
#include "checkpoint_session_generation_bank.h"
namespace checkpoint_session_generation {
enum class Error:unsigned {None,Thread,Busy,Capacity,Binding,Module,Duplicate,Initialize,Describe,NotNext,Active,Published,Abnormal,MenuOutstanding,Restore,Arm,Memory};
enum class State:unsigned {Empty,Prepared,Driving,StoppedRetained,Restored,Failed};
struct EntryReport {Identity identity{};State state=State::Empty;std::uintptr_t module=0;bool pinned=false;ns::Report session{};};
struct Report {
    unsigned count=0;int driving=-1;Error lastError=Error::None;DWORD exception=0;
    EntryReport entries[Capacity]{};
    bool schedulerFenceProven=false,admissionAuthorized=false,postCasRotationSupported=false;
};
// Fixed two-bank owner. All APIs belong to one controller thread; callbacks do
// not consult a mutable "current owner". Their immutable DLL entry addresses
// retain their original Session forever. No destructor unloads/reclaims banks.
// This solves routing isolation and pre-CAS slot ownership only. It DOES NOT
// establish a native scheduling fence or permit consecutive post-load periods.
class Owner final {
public:
    Owner() noexcept:thread_(GetCurrentThreadId()){}
    Owner(const Owner&)=delete;
    bool Prepare(HMODULE,const Identity&,const ns::Config&) noexcept;
    bool Activate(unsigned index) noexcept;
    bool StopRetaining(unsigned index) noexcept;
    bool Snapshot(Report&) noexcept;
private:
    struct Bank {HMODULE module=nullptr;const BankApi* api=nullptr;Description description{};State state=State::Empty;bool pinned=false;};
    Bank banks_[Capacity]{};DWORD thread_;volatile LONG busy_=0;unsigned count_=0;int driving_=-1;
    Error error_=Error::None;DWORD exception_=0;
    bool enter() noexcept;void leave() noexcept;
    bool fail(Error) noexcept;
    bool prepare(HMODULE,const Identity&,const ns::Config&);
    bool activate(unsigned);
    bool stop(unsigned);
};
}
