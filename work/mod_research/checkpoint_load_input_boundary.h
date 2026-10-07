#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>

// Read-only, fixed-profile boundary checks. No game calls, CAS, UI changes or
// input clearing. Passing proves the listed observations at this owned call;
// it is NOT a global input lock, full-world proof, or authorization to retry.
namespace checkpoint_load_input_boundary {
enum class Stage:unsigned { MenuAfter=1, GameBefore=2 };
struct Config {
    std::uintptr_t base=0;
    std::uintptr_t states[5]{}; // Root, Motor, Game, Strategy, User, in order
    std::uintptr_t menu=0,root=0,world=0,cache=0,keyboard=0;
    std::uint64_t attempt=0;
    std::uint32_t expectedRng=0;
    std::uint16_t year=203;
    std::uint8_t month=8,day=11,force=12;
};
struct Call {
    Stage stage=Stage::MenuAfter;
    std::uint64_t args[4]{}; // exact arguments from the transparent native bridge
    std::uint64_t callId=0,pairedCallId=0;
    std::uintptr_t callerEntryRsp=0,pairedWorker=0;
    DWORD thread=0,pairedThread=0;
    // Root records the Menu BEFORE pairing, then passes it to Menu AFTER.
    // Game BEFORE pairs to its just-captured entry. The core verifies the
    // native worker/callable/argument source chain against these values.
    bool originalReturned=false;
};
enum class Error:unsigned { None,Input,ReadFault,Mismatch,Range,NotQuiescent,InputPending,Capacity };
struct Check {
    const char* field=nullptr;
    std::uintptr_t address=0;
    std::uint64_t observed=0,expected=0;
    unsigned size=0;
    Error error=Error::None;
};
struct Report {
    bool passed=false;
    Error error=Error::None;
    DWORD exceptionCode=0;
    Stage stage=Stage::MenuAfter;
    std::uint64_t attempt=0,callId=0;
    DWORD thread=0;
    std::uintptr_t current=0,worker=0,callable=0,stack=0,list=0,dialog=0;
    std::uintptr_t stateWorkers[6]{};
    unsigned checkCount=0;
    Check checks[160]{};
    bool globalPauseProved=false,allInputChannelsProved=false;
};
// Config and Call must be immutable for this scope; Report is caller-owned.
// Caller binds a successful MenuAfter receipt and later GameBefore to ONE
// attachment/attempt; this stateless inspector does not manufacture that link.
// Source/binary profile, storage verification and durable once/CAS are outer
// responsibilities. Re-inspect GameBefore after those checks, before CAS.
bool Inspect(const Config&,const Call&,Report&) noexcept;
}
