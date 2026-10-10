// Owned report double. No game/native loader implementation is linked here.
#include "b_warm_two_bank_owner.h"
#include <cstring>
using R=checkpoint_complete_live_owner::Report;
using V=checkpoint_complete_live_owner::Value;
struct Input {void**slots[6];void*originals[6];unsigned mode,fault,seed;};
static Input input{};static HMODULE self=nullptr;
BOOL WINAPI DllMain(HINSTANCE m,DWORD why,void*){if(why==DLL_PROCESS_ATTACH)self=m;return TRUE;}
static void bridge0(){} static void bridge1(){} static void bridge2(){} static void bridge3(){} static void bridge4(){} static void bridge5(){}
static uintptr_t bridge(unsigned i){static void(*p[])()={bridge0,bridge1,bridge2,bridge3,bridge4,bridge5};return reinterpret_cast<uintptr_t>(p[i]);}
extern "C" __declspec(dllexport) DWORD WINAPI FixtureSet(void*p){input=*static_cast<Input*>(p);return 0;}
extern "C" DWORD WINAPI DescribeBWarmProfileOwner(void*p){b_warm_profile::Description d{};d.reportSize=sizeof(b_warm_profile::Report);d.bank.module=uintptr_t(self);for(unsigned i=0;i<4;++i)d.bank.dispatchBridge[i]=bridge(i);d.bank.workerBridge=bridge(4);d.bank.readBridge=bridge(5);*static_cast<b_warm_profile::Description*>(p)=d;return 0;}
extern "C" DWORD WINAPI GetBWarmProfileReport(void*p){b_warm_profile::Report r{};r.configured=r.ready=input.mode==1;r.profile.file.sha256[0]=static_cast<unsigned char>(17+input.seed);*static_cast<b_warm_profile::Report*>(p)=r;return 0;}
extern "C" DWORD WINAPI GetBWarmRetireReport(void*p){b_warm_retire::Report r{};if(input.mode==1){r.bound=r.sealed=r.restored=1;r.attempt=77+input.seed;r.userCall=8+input.seed;r.identityCall=9+input.seed;r.loadCall=10+input.seed;}if(input.fault==4)++r.attempt;*static_cast<b_warm_retire::Report*>(p)=r;return 0;}
extern "C" DWORD WINAPI GetCheckpointCompleteLiveOwnerReport(void*p){R r{};if(input.mode==1){
 r.attempt=77+input.seed;r.planningUserCall=8+input.seed;r.planningIdentityCall=9+input.seed;r.planningCompletedCall=10+input.seed;r.requestReadSha[0]=static_cast<unsigned char>(17+input.seed);
 for(auto v:{V::CasPublished,V::BytesMatched,V::LifecycleReady,V::IdentityReady,V::PlanningObserved,V::HooksRestored})r.value[unsigned(v)]=1;
 for(unsigned i=0;i<6;++i){auto&h=r.hooks[i];h.slot=uintptr_t(input.slots[i]);h.original=uintptr_t(input.originals[i]);h.hook=bridge(i);h.protection=PAGE_READWRITE;h.restored=1;}
 }if(input.mode==2)r.value[unsigned(V::StopRequested)]=1;
 if(input.fault==1)r.value[unsigned(V::ActiveDispatch)]=1;
 if(input.fault==2)r.hooks[0].dirty=1;
 if(input.fault==3)r.hooks[0].protection=PAGE_READONLY;
 *static_cast<R*>(p)=r;return 0;}
