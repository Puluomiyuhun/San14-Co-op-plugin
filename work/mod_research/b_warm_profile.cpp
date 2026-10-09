#include "b_warm_profile.h"
#include <cstring>
namespace b_warm_profile {
namespace {SRWLOCK lock=SRWLOCK_INIT;volatile LONG once=0,ready=0;Profile profile{};unsigned error=0;}
bool Validate(const Profile&p) noexcept {
    auto date=[](Date d){return d.year>=1&&d.year<=9999&&d.month>=1&&d.month<=12&&(d.day==1||d.day==11||d.day==21);};
    auto identity=[](Identity i){return i.force>0&&i.force<52&&i.ruler>0&&i.ruler<6000&&i.district>0&&i.district<52;};
    if(!checkpoint_dynamic_file_profile::Validate(p.file)||!date(p.before)||!date(p.loaded)||!identity(p.source)||!identity(p.target)||
       !p.currentForce||p.currentForce>=52||p.source.force==p.target.force||p.source.ruler==p.target.ruler||p.source.district==p.target.district)return false;
    for(auto c:p.reserved)if(c)return false;return true;
}
bool Capture(const Profile&input) noexcept {
    if(InterlockedCompareExchange(&once,1,0))return false;
    AcquireSRWLockExclusive(&lock);bool ok=false;
    __try {__try {Profile a=input;MemoryBarrier();Profile b=input;if(memcmp(&a,&b,sizeof a)||!Validate(a)){error=1;__leave;}profile=a;InterlockedExchange(&ready,1);ok=true;}
    __except(EXCEPTION_EXECUTE_HANDLER){error=2;}}
    __finally {ReleaseSRWLockExclusive(&lock);}return ok;
}
bool Ready() noexcept {return InterlockedCompareExchange(&ready,0,0)==1;}
const Profile& Get() noexcept {return profile;}
void Snapshot(Report&r) noexcept {AcquireSRWLockShared(&lock);r=Report{};r.configured=InterlockedCompareExchange(&once,0,0)?1u:0u;r.ready=Ready()?1u:0u;r.error=error;r.profile=profile;ReleaseSRWLockShared(&lock);}
}
extern "C" DWORD WINAPI GetBWarmProfileReport(void*p){__try{if(!p)return 1;b_warm_profile::Snapshot(*static_cast<b_warm_profile::Report*>(p));return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 2;}}
extern "C" DWORD WINAPI DescribeBWarmProfileOwner(void*p){__try{if(!p)return 1;b_warm_profile::Description d{};d.reportSize=sizeof(b_warm_profile::Report);if(DescribeCheckpointCompleteLiveOwner(&d.bank))return 2;*static_cast<b_warm_profile::Description*>(p)=d;return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 3;}}
extern "C" DWORD WINAPI InstallBWarmProfileOwner(void*p){
    __try {if(!p)return 1;const auto c=*static_cast<const b_warm_profile::Config*>(p);if(c.magic!=b_warm_profile::Magic||c.size!=sizeof c||c.version!=1||!b_warm_profile::Capture(c.profile))return 2;return InstallCheckpointCompleteLiveOwner(const_cast<checkpoint_complete_live_owner::Config*>(&c.owner));}
    __except(EXCEPTION_EXECUTE_HANDLER){return 3;}
}
