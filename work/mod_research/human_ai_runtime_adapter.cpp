#include "human_ai_runtime_adapter.h"
#include "human_ai_runtime_profile.h"
#include <intrin.h>
namespace san14_ai_runtime {namespace {
struct State {
 volatile LONG once=0,ready=0;Config config{};HMODULE pinned=nullptr;
 volatile LONG64 entered[4]{},native[4]{},bypassed[4]{},held[4]{},active=0,exits=0,abnormal=0;
};
State state;
LONG64 sample(volatile LONG64*p){return InterlockedCompareExchange64(p,0,0);}
void dispatch(unsigned route,void*manager,void*object){
 if(!InterlockedCompareExchange(&state.ready,0,0))__fastfail(FAST_FAIL_INVALID_ARG);
 InterlockedIncrement64(&state.entered[route]);InterlockedIncrement64(&state.active);
 bool completed=false;
 __try{
  for(;;){
   const auto subject=ResolveSubject(state.config.reader,{state.config.image,state.config.root,reinterpret_cast<Address>(object),state.config.human_mask,static_cast<Route>(route)});
   if(subject.decision==Decision::Hold){
    InterlockedIncrement64(&state.held[route]);const HeldCall call{static_cast<Route>(route),manager,object,GetCurrentThreadId(),subject};state.config.hold(state.config.hold_context,call);continue;
   }
   if(subject.decision==Decision::Native){InterlockedIncrement64(&state.native[route]);state.config.original[route](manager,object);}
   else InterlockedIncrement64(&state.bypassed[route]);
   completed=true;break;
  }
 }__finally{if(!completed)InterlockedIncrement64(&state.abnormal);InterlockedIncrement64(&state.exits);InterlockedDecrement64(&state.active);}
}
}
bool Configure(const Config&c)noexcept{
 if(InterlockedCompareExchange(&state.once,1,0))return false;
 if(!c.reader.read||!c.hold||!ValidateOuterEntries(c.reader,c.image))return false;
 const Wrapper entries[]={HumanAiForceEntry,HumanAiDistrictEntry,HumanAiArmyEntry,HumanAiGroupEntry};
 for(unsigned i=0;i<4;++i){if(!c.original[i])return false;for(unsigned j=0;j<4;++j)if(c.original[i]==entries[j]||reinterpret_cast<Address>(c.original[i])==c.image+HookSites[j].original.rva)return false;}
 // Verify both human bindings and current viewer before configuration. This is
 // validation only: later calls independently rebuild and recheck them again.
 unsigned first=0;for(unsigned i=1;i<=51;++i)if(c.human_mask&(Address(1)<<i)){first=i;break;}
 Address object=0;if(!first||!c.reader.read(c.reader.context,c.root+0xDCA0+first*8,&object,sizeof object))return false;
 const auto initial=ResolveSubject(c.reader,{c.image,c.root,object,c.human_mask,Route::Force});if(initial.fault!=Fault::None||initial.decision!=Decision::BypassHumanDecision)return false;
 if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&HumanAiForceEntry),&state.pinned))return false;
 state.config=c;InterlockedExchange(&state.ready,1);return true;
}
void Snapshot(Report&r)noexcept{r={};r.configured=InterlockedCompareExchange(&state.ready,0,0)!=0;for(unsigned i=0;i<4;++i){r.entered[i]=sample(&state.entered[i]);r.native[i]=sample(&state.native[i]);r.bypassed[i]=sample(&state.bypassed[i]);r.held[i]=sample(&state.held[i]);}r.active=sample(&state.active);r.exits=sample(&state.exits);r.abnormal_exits=sample(&state.abnormal);}
void BlockingHold::Wait(void*p,const HeldCall&){
 auto&gate=*static_cast<BlockingHold*>(p);AcquireSRWLockExclusive(&gate.lock_);const auto epoch=gate.epoch_;++gate.waiting_;
 __try{while(gate.epoch_==epoch)if(!SleepConditionVariableSRW(&gate.condition_,&gate.lock_,INFINITE,0))__fastfail(FAST_FAIL_FATAL_APP_EXIT);}
 __finally{--gate.waiting_;ReleaseSRWLockExclusive(&gate.lock_);}
}
void BlockingHold::RequestRetry()noexcept{AcquireSRWLockExclusive(&lock_);++epoch_;WakeAllConditionVariable(&condition_);ReleaseSRWLockExclusive(&lock_);}
unsigned BlockingHold::Waiting()noexcept{AcquireSRWLockShared(&lock_);auto n=waiting_;ReleaseSRWLockShared(&lock_);return n;}
}
extern "C" void HumanAiForceEntry(void*m,void*o){san14_ai_runtime::dispatch(0,m,o);}
extern "C" void HumanAiDistrictEntry(void*m,void*o){san14_ai_runtime::dispatch(1,m,o);}
extern "C" void HumanAiArmyEntry(void*m,void*o){san14_ai_runtime::dispatch(2,m,o);}
extern "C" void HumanAiGroupEntry(void*m,void*o){san14_ai_runtime::dispatch(3,m,o);}
extern "C" bool HumanAiRuntimeConfigure(const san14_ai_runtime::Config*c)noexcept{return c&&san14_ai_runtime::Configure(*c);}
extern "C" void HumanAiRuntimeSnapshot(san14_ai_runtime::Report*r)noexcept{if(r)san14_ai_runtime::Snapshot(*r);}
