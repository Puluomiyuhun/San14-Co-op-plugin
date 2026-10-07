#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <cstring>
#include <limits>
#include "human_economy_runtime_adapter.h"
#include "human_economy_runtime_profile.h"
#pragma intrinsic(_ReturnAddress)
namespace san14_economy_runtime {namespace {
using Predicate=int(*)(void*);
struct State {volatile LONG once=0,ready=0;Config config{};HMODULE pin=nullptr;volatile LONG64 entries=0,native=0,human=0,ai=0,held=0,active=0,exits=0,abnormal=0;} state;
bool pointer(Address p){return p>=0x10000&&p<0x7fffffffffffULL;}
bool bytes(const Reader&r,Address address,const unsigned char*expected,std::size_t n){unsigned char buf[256]{},again[256]{};return n<=sizeof buf&&r.read(r.context,address,buf,n)&&r.read(r.context,address,again,n)&&!std::memcmp(buf,expected,n)&&!std::memcmp(buf,again,n);}
int dispatch(void*force,Address caller){
 if(!InterlockedCompareExchange(&state.ready,0,0))__fastfail(FAST_FAIL_INVALID_ARG);
 InterlockedIncrement64(&state.entries);InterlockedIncrement64(&state.active);bool complete=false;int result=0;
 __try{
  const Address image=state.config.image;unsigned rva=0;for(const auto&site:Callsites)if(caller==image+site.return_rva)rva=site.return_rva;
  if(!rva){InterlockedIncrement64(&state.native);result=reinterpret_cast<Predicate>(image+0x2110B0)(force);complete=true;}
  else for(;;){
   const auto subject=san14_ai_runtime::ResolveSubject(state.config.reader,{image,state.config.root,reinterpret_cast<Address>(force),state.config.rules.human_force_mask,san14_ai_runtime::Route::Force});
   const san14_link::EconomySubject identity{subject.identity.force,subject.viewer,state.config.rules.binding_epoch,subject.fault==san14_ai_runtime::Fault::None&&subject.repeated_reads_equal&&subject.identity.identity_verified};
   const auto decision=san14_link::economy_predicate(state.config.rules,rva,identity);
   if(decision==san14_link::EconomyPredicate::Hold){InterlockedIncrement64(&state.held);const HeldCall call{force,caller,subject};state.config.hold(state.config.hold_context,call);continue;}
   if(decision==san14_link::EconomyPredicate::RoomHuman){InterlockedIncrement64(&state.human);result=1;}
   else if(decision==san14_link::EconomyPredicate::RoomAI){InterlockedIncrement64(&state.ai);result=0;}
   else {InterlockedIncrement64(&state.native);result=reinterpret_cast<Predicate>(image+0x2110B0)(force);}
   complete=true;break;
  }
 }__finally{if(!complete)InterlockedIncrement64(&state.abnormal);InterlockedIncrement64(&state.exits);InterlockedDecrement64(&state.active);}
 return result;
}
}
bool Configure(const Config&c)noexcept{
 if(InterlockedCompareExchange(&state.once,1,0))return false;
 if(!c.reader.read||!c.hold||!pointer(c.image)||c.image>=0x7fffffffffffULL-0x2200000||!pointer(c.root))return false;
 for(const auto&a:NativeAnchors)if(!bytes(c.reader,c.image+a.rva,a.bytes,a.size))return false;
 for(const auto&s:Callsites)if(!bytes(c.reader,c.image+s.call_rva,s.original,sizeof s.original))return false;
 unsigned first=0;for(unsigned f=1;f<=51;++f)if(c.rules.human_force_mask&(Address(1)<<f)){first=f;break;}
 Address obj=0;if(!first||!c.reader.read(c.reader.context,c.root+0xDCA0+first*8,&obj,sizeof obj))return false;
 const auto subject=san14_ai_runtime::ResolveSubject(c.reader,{c.image,c.root,obj,c.rules.human_force_mask,san14_ai_runtime::Route::Force});
 const san14_link::EconomySubject identity{subject.identity.force,subject.viewer,c.rules.binding_epoch,subject.fault==san14_ai_runtime::Fault::None&&subject.repeated_reads_equal&&subject.identity.identity_verified};
 if(san14_link::economy_predicate(c.rules,Callsites[0].return_rva,identity)!=san14_link::EconomyPredicate::RoomHuman)return false;
 if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&HumanEconomyIncomePredicate),&state.pin))return false;
 state.config=c;InterlockedExchange(&state.ready,1);return true;
}
void Snapshot(Report&r)noexcept{r={};r.configured=InterlockedCompareExchange(&state.ready,0,0)!=0;
#define COPY(field) r.field=InterlockedCompareExchange64(&state.field,0,0)
 COPY(entries);COPY(native);COPY(human);COPY(ai);COPY(held);COPY(active);COPY(exits);COPY(abnormal);
#undef COPY
}
bool PlanCallPatch(unsigned i,Address image,Address relay,CallPatch&out)noexcept{
 out={};if(i>=2||!pointer(image)||image>=0x7fffffffffffULL-0x2200000||!pointer(relay)||relay>0x7fffffffffffULL-14)return false;
 const auto site=image+Callsites[i].call_rva,caller=image+Callsites[i].return_rva;const auto delta=static_cast<std::int64_t>(relay)-static_cast<std::int64_t>(caller);
 if(delta<(std::numeric_limits<std::int32_t>::min)()||delta>(std::numeric_limits<std::int32_t>::max)())return false;
 // Do not allow either relay to overwrite either call or the native predicate.
 for(const auto&s:Callsites)if(relay<image+s.return_rva&&relay+14>image+s.call_rva)return false;
 if(relay<image+0x211109&&relay+14>image+0x2110B0)return false;
 out.site=site;out.caller=caller;out.relay=relay;std::memcpy(out.expected,Callsites[i].original,5);out.replacement[0]=0xE8;const auto disp=static_cast<std::int32_t>(delta);std::memcpy(out.replacement+1,&disp,4);
 out.relay_bytes[0]=0xFF;out.relay_bytes[1]=0x25;const Address entry=reinterpret_cast<Address>(&HumanEconomyIncomePredicate);std::memcpy(out.relay_bytes+6,&entry,8);return true;
}
}
extern "C" __declspec(noinline) int HumanEconomyIncomePredicate(void*force){const auto caller=reinterpret_cast<san14_economy_runtime::Address>(_ReturnAddress());return san14_economy_runtime::dispatch(force,caller);}
extern "C" bool HumanEconomyConfigure(const san14_economy_runtime::Config*c)noexcept{return c&&san14_economy_runtime::Configure(*c);}
extern "C" void HumanEconomySnapshot(san14_economy_runtime::Report*r)noexcept{if(r)san14_economy_runtime::Snapshot(*r);}
extern "C" bool HumanEconomyPlanCallPatch(unsigned i,san14_economy_runtime::Address image,san14_economy_runtime::Address relay,san14_economy_runtime::CallPatch*p)noexcept{return p&&san14_economy_runtime::PlanCallPatch(i,image,relay,*p);}
