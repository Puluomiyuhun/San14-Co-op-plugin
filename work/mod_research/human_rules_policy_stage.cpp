#include "human_rules_policy_stage.h"
#include <cstring>
#include <intrin.h>
namespace ai=san14_ai_runtime;namespace eco=san14_economy_runtime;namespace policy=human_rules_policy;
extern "C" __declspec(align(8)) void* volatile HumanRulesPolicyIncomeTarget=nullptr;
namespace {
volatile LONG state=policy::New,active=0;DWORD error=0;
policy::Config binding{};human_rules_hook::Prepared prepared{};std::uint64_t mask=0;
HMODULE pins[2]{};
#ifdef HUMAN_RULES_POLICY_FIXTURE
SRWLOCK gate=SRWLOCK_INIT;thread_local bool lease=false;
#endif
bool currentBinding()noexcept{
 ai::Address actualRoot=0,actualWorld=0;
 return ai::ReadLocal(nullptr,binding.image+0x1FCA1E0,&actualRoot,8)&&actualRoot==binding.root&&ai::ReadLocal(nullptr,binding.root+0x85130,&actualWorld,8)&&actualWorld==binding.world;
}
bool guardedRead(void*,ai::Address address,void*out,std::size_t size)noexcept{return currentBinding()&&ai::ReadLocal(nullptr,address,out,size)&&currentBinding();}
void aiHold(void*,const ai::HeldCall&call){binding.ai_hold(binding.hold_context,call);}
void economyHold(void*,const eco::HeldCall&call){binding.income_hold(binding.hold_context,call);}
void route(unsigned index,void*manager,void*object){
 if(InterlockedCompareExchange(&state,0,0)!=policy::Prepared)__fastfail(FAST_FAIL_INVALID_ARG);
 if(!InterlockedCompareExchange(&active,0,0)){reinterpret_cast<ai::Wrapper>(prepared.ai_originals[index])(manager,object);return;}
 const ai::Wrapper entries[]={HumanAiForceEntry,HumanAiDistrictEntry,HumanAiArmyEntry,HumanAiGroupEntry};entries[index](manager,object);
}
bool bindingsMatch(){
 for(unsigned i=0;i<2;i++){ai::Address force=0;if(!guardedRead(nullptr,binding.root+0xDCA0+binding.force[i]*8,&force,8))return false;
  const auto subject=ai::ResolveSubject({nullptr,guardedRead},{binding.image,binding.root,force,mask,ai::Route::Force});
  if(subject.fault!=ai::Fault::None||subject.decision!=ai::Decision::BypassHumanDecision||subject.humans.main_district[binding.force[i]]!=binding.main_district[i])return false;
 }return true;
}
}
void HumanRulesPolicyForce(void*m,void*o){route(0,m,o);}void HumanRulesPolicyDistrict(void*m,void*o){route(1,m,o);}
void HumanRulesPolicyArmy(void*m,void*o){route(2,m,o);}void HumanRulesPolicyGroup(void*m,void*o){route(3,m,o);}
DWORD WINAPI HumanRulesPolicyPrepare(void*input){
 if(InterlockedCompareExchange(&state,policy::Preparing,policy::New)!=policy::New)return ERROR_ALREADY_INITIALIZED;
 bool ok=false;
 __try{
  const auto c=*static_cast<const policy::Config*>(input);
  if(c.version!=1||c.size!=sizeof c||!c.room_epoch||!c.ai_hold||!c.income_hold||c.force[0]<1||c.force[0]>51||c.force[1]<1||c.force[1]>51||c.force[0]==c.force[1]||c.main_district[0]<1||c.main_district[0]>51||c.main_district[1]<1||c.main_district[1]>51||c.main_district[0]==c.main_district[1]){error=ERROR_INVALID_PARAMETER;__leave;}
  bool receipt=false;for(auto b:c.settings_receipt)receipt=receipt||b!=0;if(!receipt){error=ERROR_INVALID_DATA;__leave;}
  binding=c;mask=(std::uint64_t(1)<<c.force[0])|(std::uint64_t(1)<<c.force[1]);
  if(!currentBinding()||!bindingsMatch()){error=ERROR_INVALID_DATA;__leave;}
  void*callbacks[]={reinterpret_cast<void*>(c.ai_hold),reinterpret_cast<void*>(c.income_hold)};
  for(unsigned i=0;i<2;i++)if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(callbacks[i]),&pins[i])){error=GetLastError();__leave;}
  human_rules_hook::Config hook{};hook.image=c.image;
  void*entries[]={reinterpret_cast<void*>(HumanRulesPolicyForce),reinterpret_cast<void*>(HumanRulesPolicyDistrict),reinterpret_cast<void*>(HumanRulesPolicyArmy),reinterpret_cast<void*>(HumanRulesPolicyGroup)};
  for(unsigned i=0;i<4;i++)hook.ai_entries[i]=entries[i];hook.economy_entry=reinterpret_cast<void*>(HumanRulesPolicyIncome);
  if(!human_rules_hook::Prepare(hook,prepared)){error=ERROR_INVALID_DATA;__leave;}
  ai::Config a{};a.reader={nullptr,guardedRead};a.image=c.image;a.root=c.root;a.human_mask=mask;a.hold=aiHold;
  for(unsigned i=0;i<4;i++)a.original[i]=reinterpret_cast<ai::Wrapper>(prepared.ai_originals[i]);
  if(!ai::Configure(a)){error=ERROR_INVALID_DATA;__leave;}
  eco::Config e{};e.reader={nullptr,guardedRead};e.image=c.image;e.root=c.root;e.rules={mask,c.room_epoch,1,true,true};e.hold=economyHold;
  if(!eco::Configure(e)){error=ERROR_INVALID_DATA;__leave;}
  InterlockedExchangePointer(&HumanRulesPolicyIncomeTarget,reinterpret_cast<void*>(c.image+0x2110B0));ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){error=GetExceptionCode();}
 InterlockedExchange(&state,ok?policy::Prepared:policy::Rejected);return ok?0:error?error:ERROR_INVALID_DATA;
}
void HumanRulesPolicySnapshot(policy::Report*out)noexcept{
 if(!out)return;*out={};out->state=InterlockedCompareExchange(&state,0,0);out->active=InterlockedCompareExchange(&active,0,0)!=0;
 if(out->state==policy::Prepared||out->state==policy::Rejected)out->error=error;
 if(out->state==policy::Prepared){out->room_epoch=binding.room_epoch;out->image=binding.image;out->root=binding.root;out->world=binding.world;ai::Snapshot(out->ai);eco::Snapshot(out->income);}
}
#ifdef HUMAN_RULES_POLICY_FIXTURE
bool HumanRulesPolicyFixtureEnter(){if(lease)return false;AcquireSRWLockShared(&gate);if(InterlockedCompareExchange(&state,0,0)!=policy::Prepared){ReleaseSRWLockShared(&gate);return false;}lease=true;return true;}
void HumanRulesPolicyFixtureLeave(){if(!lease)__fastfail(FAST_FAIL_INVALID_ARG);lease=false;ReleaseSRWLockShared(&gate);}
bool HumanRulesPolicyFixtureActivate(std::uint64_t epoch){
 if(lease)return false;AcquireSRWLockExclusive(&gate);bool ok=false;
 __try{if(InterlockedCompareExchange(&state,0,0)!=policy::Prepared||InterlockedCompareExchange(&active,0,0)||epoch!=binding.room_epoch||!bindingsMatch())__leave;
  InterlockedExchangePointer(&HumanRulesPolicyIncomeTarget,reinterpret_cast<void*>(HumanEconomyIncomePredicate));InterlockedExchange(&active,1);ok=true;
 }__finally{ReleaseSRWLockExclusive(&gate);}return ok;
}
#endif
