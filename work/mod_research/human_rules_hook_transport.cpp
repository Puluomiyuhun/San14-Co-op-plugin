#include "human_rules_hook_transport.h"
#include "human_rules_hook_unwind.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_profile.h"
#include <cstring>
#include <limits>
#include <intrin.h>
namespace human_rules_hook {namespace {
struct Site {Address address=0;unsigned prefix=0,size=0;unsigned char original[128]{},patch[16]{};DWORD protection=0;};
struct State {
 volatile LONG once=0;SRWLOCK gate=SRWLOCK_INIT;Config config{};Prepared prepared{};Report report{};
 Site sites[6]{};RUNTIME_FUNCTION functions[4]{};HMODULE pinned[6]{};
 volatile LONG64 entered=0,active=0;
#ifdef HUMAN_RULES_OWN_PROCESS_FIXTURE
 unsigned fault_slot=99,fault_mode=0;
#endif
}state;
thread_local bool executionLease=false;
bool copy(void*out,const void*source,std::size_t n)noexcept{__try{std::memcpy(out,source,n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){state.report.error=GetExceptionCode();return false;}}
bool same(Address address,const unsigned char*expected,unsigned n){unsigned char data[128]{};return n<=sizeof data&&copy(data,reinterpret_cast<void*>(address),n)&&!std::memcmp(data,expected,n);}
bool region(Address address,unsigned length,MEMORY_BASIC_INFORMATION&m){return VirtualQuery(reinterpret_cast<void*>(address),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&address+length>address&&address+length<=reinterpret_cast<Address>(m.BaseAddress)+m.RegionSize;}
bool executable(DWORD p){return p==PAGE_EXECUTE_READ||p==PAGE_EXECUTE_READWRITE||p==PAGE_EXECUTE_WRITECOPY;}
bool originalUnwind(){for(const auto&p:Unwinds){DWORD64 base=0;auto*found=RtlLookupFunctionEntry(state.config.image+p.start,&base,nullptr);RUNTIME_FUNCTION entry{};if(!found||base!=state.config.image||!copy(&entry,found,sizeof entry)||entry.BeginAddress!=p.start||entry.EndAddress!=p.end||entry.UnwindData!=p.rva||!same(base+p.rva,p.bytes,p.size))return false;}return true;}
bool owned(){for(const auto&s:state.sites){MEMORY_BASIC_INFORMATION m{};if(!region(s.address,s.size,m)||m.Type!=MEM_PRIVATE||reinterpret_cast<Address>(m.AllocationBase)!=state.config.image)return false;}return true;}
bool current(bool installed){for(const auto&s:state.sites){MEMORY_BASIC_INFORMATION m{};if(!region(s.address,s.size,m)||m.Protect!=s.protection||!same(s.address,installed?s.patch:s.original,s.prefix)||!same(s.address+s.prefix,s.original+s.prefix,s.size-s.prefix))return false;}return originalUnwind();}
void* nearAllocation(Address image){
 SYSTEM_INFO info{};GetSystemInfo(&info);const Address gran=info.dwAllocationGranularity,low=image>0x70000000?image-0x70000000:0x10000,high=image+0x70000000;
 for(Address at=(low+gran-1)&~(gran-1);at<high;){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(at),&m,sizeof m)!=sizeof m)break;const Address end=reinterpret_cast<Address>(m.BaseAddress)+m.RegionSize;
  if(m.State==MEM_FREE){Address candidate=(at+gran-1)&~(gran-1);if(candidate+0x10000<=end&&candidate+0x10000<high)if(auto*p=VirtualAlloc(reinterpret_cast<void*>(candidate),0x10000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE))return p;}
  if(end<=at)break;at=(end+gran-1)&~(gran-1);
 }return nullptr;
}
void absoluteJump(unsigned char*out,Address target){out[0]=0xFF;out[1]=0x25;std::memset(out+2,0,4);std::memcpy(out+6,&target,8);}
// R11-register jump cannot be mistaken for a standard x64 tail-call epilogue
// while the copied native prologue's stack frame remains live.
void continuation(unsigned char*out,Address target){out[0]=0x49;out[1]=0xBB;std::memcpy(out+2,&target,8);out[10]=0x41;out[11]=0xFF;out[12]=0xE3;}
bool writeSite(unsigned index,bool restore){
 auto&s=state.sites[index];DWORD previous=0;auto*address=reinterpret_cast<void*>(s.address);
 if(!VirtualProtect(address,s.prefix,PAGE_EXECUTE_READWRITE,&previous)){state.report.error=GetLastError();return false;}
 if(!restore)state.report.written_mask|=1u<<index;
 bool written=copy(address,restore?s.original:s.patch,s.prefix);if(written&&restore)state.report.written_mask&=~(1u<<index);
 bool flushed=FlushInstructionCache(GetCurrentProcess(),address,s.prefix)!=FALSE;if(!flushed)state.report.error=GetLastError();
 DWORD discarded=0;const bool protectedAgain=VirtualProtect(address,s.prefix,s.protection,&discarded)!=FALSE;if(!protectedAgain)state.report.error=GetLastError();
 return written&&flushed&&protectedAgain&&same(s.address,restore?s.original:s.patch,s.prefix);
}
bool rollback(){bool ok=true;for(unsigned n=6;n;--n){unsigned i=n-1;auto&s=state.sites[i];if(!(state.report.written_mask&(1u<<i)))continue;if(!same(s.address,s.patch,s.prefix)){ok=false;continue;}if(!writeSite(i,true))ok=false;}return ok&&current(false);}
}
bool Prepare(const Config&c,Prepared&out)noexcept{
 out={};if(InterlockedCompareExchange(&state.once,1,0))return false;AcquireSRWLockExclusive(&state.gate);bool ok=false;
 __try{
  if(c.image<0x10000||c.image>0x7fffffffffffULL-0x2238000)__leave;state.config=c;
  void*targets[6]={c.ai_entries[0],c.ai_entries[1],c.ai_entries[2],c.ai_entries[3],c.economy_entry,reinterpret_cast<void*>(&HumanRulesPrepare)};
  for(unsigned i=0;i<6;++i){MEMORY_BASIC_INFORMATION targetMemory{};if(!targets[i]||(reinterpret_cast<Address>(targets[i])>=c.image&&reinterpret_cast<Address>(targets[i])<c.image+0x2238000)||!region(reinterpret_cast<Address>(targets[i]),1,targetMemory)||!executable(targetMemory.Protect)||!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(targets[i]),&state.pinned[i]))__leave;}
  for(unsigned i=0;i<6;++i){auto&s=state.sites[i];if(i<4){const auto&p=san14_ai_runtime::HookSites[i];s.address=c.image+p.original.rva;s.prefix=p.instruction_prefix;s.size=unsigned(p.original.size);std::memcpy(s.original,p.original.bytes,s.size);}else{const auto&p=san14_economy_runtime::Callsites[i-4];s.address=c.image+p.call_rva;s.prefix=s.size=5;std::memcpy(s.original,p.original,5);}
   MEMORY_BASIC_INFORMATION m{};if(!region(s.address,s.size,m)||!executable(m.Protect)||!same(s.address,s.original,s.size))__leave;s.protection=m.Protect;
  }
  if(!originalUnwind())__leave;auto*block=static_cast<unsigned char*>(nearAllocation(c.image));if(!block)__leave;state.prepared.allocation=block;
  for(unsigned i=0;i<4;++i){auto&s=state.sites[i];const unsigned off=i*0x100;std::memcpy(block+off,s.original,s.prefix);continuation(block+off+s.prefix,s.address+s.prefix);std::memcpy(block+off+0x40,Unwinds[i].bytes,Unwinds[i].size);state.functions[i]={off,off+s.prefix+13,off+0x40};state.prepared.ai_originals[i]=block+off;std::memset(s.patch,0x90,s.prefix);absoluteJump(s.patch,reinterpret_cast<Address>(c.ai_entries[i]));}
  for(unsigned i=0;i<2;++i){auto&s=state.sites[i+4];auto*relay=block+0x400+i*0x20;absoluteJump(relay,reinterpret_cast<Address>(c.economy_entry));const auto delta=reinterpret_cast<Address>(relay)-(s.address+5);const auto signedDelta=static_cast<std::int64_t>(delta);if(signedDelta<(std::numeric_limits<std::int32_t>::min)()||signedDelta>(std::numeric_limits<std::int32_t>::max)())__leave;s.patch[0]=0xE8;const auto rel=static_cast<std::int32_t>(signedDelta);std::memcpy(s.patch+1,&rel,4);state.prepared.economy_relays[i]=relay;}
  if(!RtlAddFunctionTable(state.functions,4,reinterpret_cast<DWORD64>(block)))__leave;DWORD previous=0;if(!VirtualProtect(block,0x10000,PAGE_EXECUTE_READ,&previous)||!FlushInstructionCache(GetCurrentProcess(),block,0x10000))__leave;
  out=state.prepared;state.report.prepared=true;ok=true;
 }__finally{if(!ok)state.report.failed=true;ReleaseSRWLockExclusive(&state.gate);}return ok;
}
bool EnterOwnedExecution()noexcept{if(executionLease)return false;AcquireSRWLockShared(&state.gate);if(!state.report.prepared||state.report.failed||state.report.uncertain||!owned()){ReleaseSRWLockShared(&state.gate);return false;}executionLease=true;InterlockedIncrement64(&state.entered);InterlockedIncrement64(&state.active);return true;}
void LeaveOwnedExecution()noexcept{if(!executionLease)__fastfail(FAST_FAIL_INVALID_ARG);executionLease=false;InterlockedDecrement64(&state.active);ReleaseSRWLockShared(&state.gate);}
bool PublishCooperativeOwnProcess()noexcept{
 if(executionLease)return false;AcquireSRWLockExclusive(&state.gate);bool ok=false;
 __try{
  if(!state.report.prepared||state.report.failed||state.report.installed||state.report.restored||!owned())__leave;++state.report.publication_attempts;
  if(!current(false)){state.report.failed=true;state.report.error=ERROR_INVALID_DATA;__leave;}
  for(unsigned i=0;i<6;++i){bool good=writeSite(i,false);
#ifdef HUMAN_RULES_OWN_PROCESS_FIXTURE
   if(i==state.fault_slot){good=false;if(state.fault_mode==2){DWORD old=0;VirtualProtect(reinterpret_cast<void*>(state.sites[i].address),1,PAGE_EXECUTE_READWRITE,&old);*reinterpret_cast<unsigned char*>(state.sites[i].address)=0xCC;VirtualProtect(reinterpret_cast<void*>(state.sites[i].address),1,old,&old);}state.fault_slot=99;}
#endif
   if(!good){state.report.failed=true;state.report.uncertain=!rollback();__leave;}
  }
  if(!current(true)){state.report.failed=true;state.report.uncertain=!rollback();__leave;}state.report.installed=true;ok=true;
 }__finally{ReleaseSRWLockExclusive(&state.gate);}return ok;
}
bool RestoreCooperativeOwnProcess()noexcept{if(executionLease)return false;AcquireSRWLockExclusive(&state.gate);bool ok=false;__try{if(!state.report.installed||state.report.uncertain||!owned())__leave;if(!current(true)){state.report.failed=true;state.report.uncertain=true;__leave;}ok=rollback();state.report.uncertain=!ok;state.report.failed=!ok;state.report.installed=!ok;state.report.restored=ok;}__finally{ReleaseSRWLockExclusive(&state.gate);}return ok;}
void Snapshot(Report&r)noexcept{if(!executionLease)AcquireSRWLockShared(&state.gate);r=state.report;r.registered_executions=InterlockedCompareExchange64(&state.entered,0,0);r.active_executions=InterlockedCompareExchange64(&state.active,0,0);if(!executionLease)ReleaseSRWLockShared(&state.gate);}
}
extern "C" bool HumanRulesPrepare(const human_rules_hook::Config*c,human_rules_hook::Prepared*p)noexcept{return c&&p&&human_rules_hook::Prepare(*c,*p);}
extern "C" void HumanRulesSnapshot(human_rules_hook::Report*r)noexcept{if(r)human_rules_hook::Snapshot(*r);}
extern "C" bool HumanRulesEnterOwnedExecution()noexcept{return human_rules_hook::EnterOwnedExecution();}
extern "C" void HumanRulesLeaveOwnedExecution()noexcept{human_rules_hook::LeaveOwnedExecution();}
extern "C" bool HumanRulesPublishCooperativeOwnProcess()noexcept{return human_rules_hook::PublishCooperativeOwnProcess();}
extern "C" bool HumanRulesRestoreCooperativeOwnProcess()noexcept{return human_rules_hook::RestoreCooperativeOwnProcess();}
#ifdef HUMAN_RULES_OWN_PROCESS_FIXTURE
extern "C" bool HumanRulesFixtureFault(unsigned slot,unsigned mode)noexcept{using namespace human_rules_hook;if(slot>=6||(mode!=1&&mode!=2))return false;AcquireSRWLockExclusive(&state.gate);const bool ok=state.report.prepared&&!state.report.publication_attempts;if(ok){state.fault_slot=slot;state.fault_mode=mode;}ReleaseSRWLockExclusive(&state.gate);return ok;}
#endif
