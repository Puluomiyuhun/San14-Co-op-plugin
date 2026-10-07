#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "human_economy_runtime_adapter.h"
#include "human_economy_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
namespace ec=san14_economy_runtime;
using Predicate=int(*)(void*);
static unsigned holdMode=0,holds=0,cleanup=0;
void hold(void*,const ec::HeldCall&call){
 check(call.caller==image+0x28DE76||call.caller==image+0x28DAAA,"exact real caller address");++holds;
 if(holdMode==1){*reinterpret_cast<unsigned char*>(person+2*0x200+0x11E)=1;return;}
 RaiseException(0xE0052001,0,0,nullptr);
}
bool invokeSEH(Predicate f,void*p,DWORD code){bool caught=false;__try{__try{f(p);}__finally{++cleanup;}}__except(GetExceptionCode()==code?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}return caught;}
template<class T>void put(A p,T value){std::memcpy(reinterpret_cast<void*>(p),&value,sizeof value);}
bool localRead(void*,A p,void*out,std::size_t n)noexcept{return rt::ReadLocal(nullptr,p,out,n);}
int main(int argc,char**argv){try{
 check(argc==3,"case and DLL required");std::string test=argv[1];auto dll=LoadLibraryA(argv[2]);check(dll!=nullptr,"DLL load");
 bool(*configure)(const ec::Config*)noexcept=nullptr;void(*snapshot)(ec::Report*)noexcept=nullptr;bool(*plan)(unsigned,A,A,ec::CallPatch*)noexcept=nullptr;Predicate entry=nullptr;
 auto proc=GetProcAddress(dll,"HumanEconomyConfigure");check(proc!=nullptr,"configure export");std::memcpy(&configure,&proc,sizeof proc);
 proc=GetProcAddress(dll,"HumanEconomySnapshot");check(proc!=nullptr,"snapshot export");std::memcpy(&snapshot,&proc,sizeof proc);
 proc=GetProcAddress(dll,"HumanEconomyPlanCallPatch");check(proc!=nullptr,"plan export");std::memcpy(&plan,&proc,sizeof proc);
 proc=GetProcAddress(dll,"HumanEconomyIncomePredicate");check(proc!=nullptr,"predicate export");std::memcpy(&entry,&proc,sizeof proc);
 Memory memory;populate(memory);
 for(const auto&a:ec::NativeAnchors)std::memcpy(memory.at(image+a.rva,a.size),a.bytes,a.size);
 for(const auto&s:ec::Callsites)std::memcpy(memory.at(image+s.call_rva,5),s.original,5);
 std::memcpy(memory.at(image+predicateUnwindRva,sizeof predicateUnwindBytes),predicateUnwindBytes,sizeof predicateUnwindBytes);
 for(const auto&region:memory.regions){auto*allocation=VirtualAlloc(reinterpret_cast<void*>(region.first),region.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(allocation==reinterpret_cast<void*>(region.first),"own-process fixed allocation");std::memcpy(allocation,region.second.data(),region.second.size());}
 ec::Config c{};c.reader={nullptr,localRead};c.image=image;c.root=root;c.rules={(A(1)<<2)|(A(1)<<12),7,1,true,true};c.hold=hold;
 if(test=="bad-settings"){c.rules.shared_settings_verified=false;check(!configure(&c),"settings must be verified outside adapter");}
 else if(test=="bad-site"){put(image+0x28DE71,std::uint8_t(0x90));check(!configure(&c),"reject changed income callsite");}
 else {
  check(configure(&c),"configure");check(!configure(&c),"one immutable config");
  // A replacement CALL keeps the actual native return address. These synthetic
  // caller envelopes are only in this process's new allocation, never game code.
  const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3};
  const unsigned char unwind[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),unwind,sizeof unwind);
  Predicate callers[2]{};
  for(unsigned i=0;i<2;++i){ec::CallPatch patch{};check(plan(i,image,image+0x2100000+i*0x20,&patch),"call patch recipe");check(!std::memcmp(reinterpret_cast<void*>(patch.site),patch.expected,5),"expected original CALL bytes");std::memcpy(reinterpret_cast<void*>(patch.site-4),prefix,4);std::memcpy(reinterpret_cast<void*>(patch.site),patch.replacement,5);std::memcpy(reinterpret_cast<void*>(patch.caller),suffix,5);std::memcpy(reinterpret_cast<void*>(patch.relay),patch.relay_bytes,14);callers[i]=reinterpret_cast<Predicate>(patch.site-4);}
  RUNTIME_FUNCTION functions[]={{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
  check(RtlAddFunctionTable(functions,3,image)!=FALSE,"registered native and caller unwind");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image),0x2200000,PAGE_EXECUTE_READ,&old)!=FALSE,"own code RX");check(FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),0x2200000)!=FALSE,"instruction cache");
  unsigned checks=0;
  if(test=="routing"){
   for(unsigned viewer:{2u,12u}){put(world+0x3A,std::uint8_t(viewer));for(unsigned f=1;f<=51;++f){auto*object=reinterpret_cast<void*>(forces+f*0x1D0);for(auto caller:callers){check(caller(object)==int(f==2||f==12),"both room humans income selected");++checks;}check(entry(object)==int(f==viewer),"unknown caller retains actual native UI predicate");check(reinterpret_cast<Predicate>(image+0x2110B0)(object)==int(f==viewer),"global original unchanged");checks+=2;}}
  }else if(test=="hold-repair"){holdMode=1;put(person+2*0x200+0x11E,std::uint8_t(0));check(callers[0](reinterpret_cast<void*>(forces+2*0x1D0))==1&&holds==1,"hold reparsed before return");++checks;}
  else if(test=="hold-exception"){check(invokeSEH(callers[1],reinterpret_cast<void*>(forces+52*0x1D0),0xE0052001)&&cleanup==1&&holds==1,"hold SEH through registered caller");++checks;}
  else if(test=="native-exception"){check(invokeSEH(entry,reinterpret_cast<void*>(0xDEAD),EXCEPTION_ACCESS_VIOLATION)&&cleanup==1,"actual native predicate AV unwind");++checks;}
  else if(test=="unknown-unhealthy-binding"){put(person+2*0x200+0x11E,std::uint8_t(0));check(entry(reinterpret_cast<void*>(forces+12*0x1D0))==1&&holds==0,"unknown UI caller unaffected by room faults");++checks;}
  else if(test=="plan-bounds"){ec::CallPatch patch{};check(!plan(2,image,image+0x2100000,&patch)&&!plan(0,image,0x7fff00000000ULL,&patch)&&!plan(0,image,image+0x28DE71,&patch)&&!plan(0,image,image+0x2110B0,&patch),"invalid patch recipes refused");checks+=4;}
  else check(false,"unknown case");
  ec::Report report{};snapshot(&report);check(report.configured&&!report.installed&&report.active==0&&report.entries==report.exits,"clean adapter call exits");check(report.abnormal==((test=="hold-exception"||test=="native-exception")?1u:0u),"abnormal count");
  check(!std::memcmp(reinterpret_cast<void*>(image+0x2110B0),ec::BytesPredicate,sizeof ec::BytesPredicate),"global is_player bytes unchanged");check(RtlDeleteFunctionTable(functions)!=FALSE,"fixture unwind registration retired");
  std::printf("checks=%u native=%llu human=%llu ai=%llu held=%llu\n",checks,static_cast<unsigned long long>(report.native),static_cast<unsigned long long>(report.human),static_cast<unsigned long long>(report.ai),static_cast<unsigned long long>(report.held));
 }
 std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"actual_dll_exports\":true,\"actual_return_address\":true,\"real_force_decoder\":true,\"game_access\":false,\"installed_in_game\":false}\n",test.c_str());return 0;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
