#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>

// A finite atomic pointer-pair commit, not a game installer or identity API.
// Caller must prove the exact owned Title worker BEFORE boundary, matched world
// bytes, native load success/join, supported profile, rebuilt person indexes,
// source/target eligibility and same live load transaction in validate().
// Only title+4A0/+4A8 are changed; no game initializer is called by this module.
namespace checkpoint_identity_pair_commit {
struct Pair {std::uint64_t force=0,person=0;};
static_assert(sizeof(Pair)==16);
enum class Point:unsigned {Preflight,BeforeIntent,BeforeCompareExchange,AfterCompareExchange};
struct Input {
    Pair* destination=nullptr;
    Pair source{},target{};
    std::uint64_t attempt=0,callId=0;
    DWORD thread=0;
    const wchar_t* intentPath=nullptr; // nonempty <=1023 UTF-16 units, copied inside SEH
    unsigned char ownerBinding[32]{};
};
struct Access {
    void* context=nullptr;
    bool (*validate)(void*,Point,const Input&)=nullptr;
};
enum class State:unsigned {New,Rejected,IntentDurable,NotApplied,PairCommitted,Uncertain};
struct Report {
    State state=State::New;
    unsigned invocations=0,casAttempts=0,casApplied=0;
    bool intentCreated=false,intentDurable=false,postGuard=false;
    DWORD exceptionCode=0,osError=0;
    Pair observed{};
    const char* stage="new";
    bool worldInitialized=false,planningReady=false;
};
class Committer {
public:
    // Once per object, and unique CREATE_NEW intent even across process runs.
    // Guard or CAS failure never retries or attempts pointer rollback.
    bool Commit(const Input&,const Access&) noexcept;
    // Only after the accepted Commit call returns. Not a concurrent snapshot.
    const Report& GetReport() const noexcept {return report_;}
private:
    volatile LONG entered_=0;
    Report report_{};
};
}
