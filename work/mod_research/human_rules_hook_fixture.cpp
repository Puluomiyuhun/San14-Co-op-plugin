#include "human_rules_hook_transport.h"
#include "human_rules_hook_unwind.h"
#include "human_ai_runtime_adapter.h"
#include "human_economy_runtime_adapter.h"
#include "human_economy_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
#include <thread>
#include <atomic>
namespace hook=human_rules_hook;namespace ec=san14_economy_runtime;
using Wrapper=void(*)(void*,void*);using Predicate=int(*)(void*);
static bool(*enter)()noexcept=nullptr;static void(*leave)()noexcept=nullptr;
static unsigned bodyCalls[4]{},callerCleanup=0;static bool bodyThrow=false;
static std::atomic<bool>bodyEntered{false},bodyRelease{true};
constexpr A manager=0x73000000;
template<class T> T function(HMODULE module,const char*name){auto p=GetProcAddress(module,name);check(p!=nullptr,name);T f{};static_assert(sizeof f==sizeof p);std::memcpy(&f,&p,sizeof f);return f;}
void body(unsigned route,void*c,void*object){check(c==reinterpret_cast<void*>(A(0x74000000)+route*0x100)&&object!=nullptr,"native body exact manager child/object ABI");++bodyCalls[route];bodyEntered=true;while(!bodyRelease.load())Sleep(1);if(bodyThrow)RaiseException(0xE0053001,0,0,nullptr);}
void body0(void*c,void*o){body(0,c,o);}void body1(void*c,void*o){body(1,c,o);}void body2(void*c,void*o){body(2,c,o);}void body3(void*c,void*o){body(3,c,o);}
void aiHold(void*,const rt::HeldCall&){RaiseException(0xE0053002,0,0,nullptr);}void economyHold(void*,const ec::HeldCall&){RaiseException(0xE0053003,0,0,nullptr);}
bool localRead(void*,A p,void*out,std::size_t n)noexcept{__try{std::memcpy(out,reinterpret_cast<void*>(p),n);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
template<class T>void put(A p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
void jump(A at,void*target){unsigned char b[14]{0xFF,0x25};std::memcpy(b+6,&target,8);std::memcpy(reinterpret_cast<void*>(at),b,sizeof b);}
void invoke(Wrapper f,void*object){check(enter(),"execution lease");__try{f(reinterpret_cast<void*>(manager),object);}__finally{++callerCleanup;leave();}}
int predicate(Predicate f,void*object){check(enter(),"predicate lease");int result=0;__try{result=f(object);}__finally{++callerCleanup;leave();}return result;}
bool exceptional(Wrapper f,void*object,DWORD code){bool caught=false;__try{invoke(f,object);}__except(GetExceptionCode()==code?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}return caught;}
void unwindChecks(const hook::Prepared&p,unsigned&checks){
 for(unsigned slot=0;slot<4;++slot){const unsigned pointsForce[]={0,5,6,10,13,16,26};const unsigned pointsOther[]={0,5,10,11,15,25};const auto*points=slot==0?pointsForce:pointsOther;unsigned count=slot==0?7:6;
  for(unsigned k=0;k<count;++k){unsigned pc=points[k];alignas(16) unsigned char stack[0x800]{};A entrySP=reinterpret_cast<A>(stack+0x400);put(entrySP,A(0x12345000));const A bx=0x11111111,si=0x22222222,di=0x33333333;
   CONTEXT c{};c.ContextFlags=CONTEXT_FULL;c.Rip=reinterpret_cast<A>(p.ai_originals[slot])+pc;c.Rsp=entrySP;c.Rbx=bx;c.Rsi=si;c.Rdi=di;
   if(pc>=5)put(entrySP+8,bx);if(slot!=0&&pc>=10)put(entrySP+16,si);
   const unsigned pushed=slot==0?6:11,allocated=slot==0?10:15;if(pc>=pushed){c.Rsp-=8;put(c.Rsp,di);}if(pc>=allocated)c.Rsp-=0x20;
   if(slot==0&&pc>=13)c.Rdi=0x44444444;if(slot==0&&pc>=16)c.Rbx=0x55555555;
   DWORD64 base=0;auto*rf=RtlLookupFunctionEntry(c.Rip,&base,nullptr);check(rf!=nullptr,"trampoline registered function entry");PVOID handler=nullptr;DWORD64 frame=0;RtlVirtualUnwind(UNW_FLAG_NHANDLER,base,c.Rip,rf,&c,&handler,&frame,nullptr);
   if(c.Rip!=0x12345000||c.Rsp!=entrySP+8||c.Rbx!=bx||c.Rsi!=si||c.Rdi!=di){std::printf("unwind slot=%u pc=%u rip=%llx rsp_delta=%lld rbx=%llx rsi=%llx rdi=%llx\n",slot,pc,c.Rip,static_cast<long long>(c.Rsp-entrySP),c.Rbx,c.Rsi,c.Rdi);check(false,"partial/full trampoline unwind");}++checks;
  }
 }
}
int main(int argc,char**argv){try{
 check(argc==6,"case, AI DLL, economy DLL, transport DLL, archived image required");std::string test=argv[1];bool completedPublish=false;auto ai=LoadLibraryA(argv[2]),eco=LoadLibraryA(argv[3]),transport=LoadLibraryA(argv[4]);check(ai&&eco&&transport,"load three actual DLLs");
 auto prepare=function<bool(*)(const hook::Config*,hook::Prepared*)noexcept>(transport,"HumanRulesPrepare");auto publish=function<bool(*)()noexcept>(transport,"HumanRulesPublishCooperativeOwnProcess");auto restore=function<bool(*)()noexcept>(transport,"HumanRulesRestoreCooperativeOwnProcess");auto snapshot=function<void(*)(hook::Report*)noexcept>(transport,"HumanRulesSnapshot");bool(*fault)(unsigned,unsigned)noexcept=nullptr;auto optionalFault=GetProcAddress(transport,"HumanRulesFixtureFault");std::memcpy(&fault,&optionalFault,sizeof fault);enter=function<bool(*)()noexcept>(transport,"HumanRulesEnterOwnedExecution");leave=function<void(*)()noexcept>(transport,"HumanRulesLeaveOwnedExecution");
 auto aiConfigure=function<bool(*)(const rt::Config*)noexcept>(ai,"HumanAiRuntimeConfigure");auto aiSnapshot=function<void(*)(rt::Report*)noexcept>(ai,"HumanAiRuntimeSnapshot");auto ecConfigure=function<bool(*)(const ec::Config*)noexcept>(eco,"HumanEconomyConfigure");auto ecSnapshot=function<void(*)(ec::Report*)noexcept>(eco,"HumanEconomySnapshot");
 Memory m;std::ifstream source(argv[5],std::ios::binary);check(bool(source),"archived image");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(source),{});check(m.regions[image].size()>=0x2200000,"archived image extent");populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));
 const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
 for(const auto&row:m.regions){auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned image/data allocations");std::memcpy(p,row.second.data(),row.second.size());}
 const A bodies[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Wrapper bodyFns[]={body0,body1,body2,body3};for(unsigned i=0;i<4;++i)jump(image+bodies[i],reinterpret_cast<void*>(bodyFns[i]));
 // Income envelopes preserve native return RVAs and supply caller unwind data.
 const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
 Predicate income[2]{};for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);income[i]=reinterpret_cast<Predicate>(image+s.call_rva-4);}
 RUNTIME_FUNCTION originals[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
 check(RtlAddFunctionTable(originals,7,image)!=FALSE,"own original/caller unwind");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image),m.regions[image].size(),PAGE_EXECUTE_READ,&old)!=FALSE,"source image RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());
 hook::Config hc{};hc.image=image;const char*names[]={"HumanAiForceEntry","HumanAiDistrictEntry","HumanAiArmyEntry","HumanAiGroupEntry"};for(unsigned i=0;i<4;++i)hc.ai_entries[i]=reinterpret_cast<void*>(function<Wrapper>(ai,names[i]));hc.economy_entry=reinterpret_cast<void*>(function<Predicate>(eco,"HumanEconomyIncomePredicate"));hook::Prepared prepared{};check(prepare(&hc,&prepared),"prepare native trampolines");unsigned unwindCount=0;unwindChecks(prepared,unwindCount);
 rt::Config ac{};ac.reader={nullptr,localRead};ac.image=image;ac.root=root;ac.human_mask=(A(1)<<2)|(A(1)<<12);ac.hold=aiHold;for(unsigned i=0;i<4;++i)ac.original[i]=reinterpret_cast<Wrapper>(prepared.ai_originals[i]);check(aiConfigure(&ac),"configure real AI with prepared original trampolines");
 ec::Config ecfg{};ecfg.reader={nullptr,localRead};ecfg.image=image;ecfg.root=root;ecfg.rules={(A(1)<<2)|(A(1)<<12),7,1,true,true};ecfg.hold=economyHold;check(ecConfigure(&ecfg),"configure real economy before CALL publication");
 Wrapper entries[4]{};for(unsigned i=0;i<4;++i)entries[i]=reinterpret_cast<Wrapper>(image+rt::HookSites[i].original.rva);
 if(test.rfind("rollback-",0)==0||test=="uncertain"){
  check(fault!=nullptr&&fault(test=="uncertain"?3:unsigned(test.back()-'0'),test=="uncertain"?2:1),"one fault configured");check(!publish(),"partial publication rejected");hook::Report r{};snapshot(&r);check(r.failed&&!r.installed&&r.uncertain==(test=="uncertain"),"partial failure state");if(test!="uncertain"){check(r.written_mask==0,"all written sites rolled back");for(unsigned i=0;i<4;++i)check(!std::memcmp(reinterpret_cast<void*>(image+rt::HookSites[i].original.rva),rt::HookSites[i].original.bytes,rt::HookSites[i].original.size),"exact original AI restored");}else check(r.written_mask!=0,"foreign changed patch remains owned/uncertain");check(!publish()&&!enter(),"no automatic retry or execution after failure");
 }else if(test=="preimage-drift"||test=="protection-drift"){
  auto at=image+rt::HookSites[2].original.rva;DWORD protection=0;check(VirtualProtect(reinterpret_cast<void*>(at),1,PAGE_EXECUTE_READWRITE,&protection)!=FALSE,"own drift fixture protection");if(test=="preimage-drift"){put(at,std::uint8_t(0xCC));VirtualProtect(reinterpret_cast<void*>(at),1,protection,&protection);}
  check(!publish(),"foreign source drift rejected");hook::Report r{};snapshot(&r);check(r.failed&&!r.installed&&!r.uncertain&&r.written_mask==0,"foreign preimage never overwritten");
 }else{
  check(enter(),"owned execution before publish");check(!publish(),"cannot publish while own thread in execution");check(!enter(),"nonrecursive execution lease");leave();
  if(test=="drain"){
   bodyRelease=false;std::thread execution([&]{invoke(entries[0],reinterpret_cast<void*>(forces+3*0x1D0));});for(unsigned n=0;n<2000&&!bodyEntered;++n)Sleep(1);check(bodyEntered,"old execution entered original before publication");std::atomic<bool>done{false};bool published=false;std::thread publisher([&]{published=publish();done=true;});Sleep(30);check(!done,"exclusive publication really waits for executing caller");bodyRelease=true;execution.join();publisher.join();check(published,"publish after old call drained");completedPublish=published;
  }else {completedPublish=publish();check(completedPublish,"publish six hooks under exclusive gate");}
  if(test=="routes"||test=="drain"){
   const unsigned districts[]={2,11,20,21,3};for(unsigned viewer:{2u,12u}){put(world+0x3A,std::uint8_t(viewer));for(unsigned route=0;route<4;++route)for(unsigned k=0;k<5;++k){const A object=route==0?forces+(k<2?(k==0?2:12):3)*0x1D0:route==1?district+districts[k]*0x28:route==2?army+(k+1)*0x200:group+(k+1)*0x40;auto n=bodyCalls[route];invoke(entries[route],reinterpret_cast<void*>(object));check(bodyCalls[route]-n==(k<2?0u:1u),"actual patched four wrappers protect both humans and retain delegated AI");}for(auto call:income)for(unsigned f:{2u,12u,3u})check(predicate(call,reinterpret_cast<void*>(forces+f*0x1D0))==int(f!=3),"actual two CALL relays preserve original return address");}
  }else if(test=="native-seh"){bodyThrow=true;check(exceptional(entries[0],reinterpret_cast<void*>(forces+3*0x1D0),0xE0053001),"body SEH through original wrapper and DLL");}
  else if(test=="trampoline-seh"){
   const A objects[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};for(unsigned i=0;i<4;++i){auto at=reinterpret_cast<A>(prepared.ai_originals[i])+rt::HookSites[i].instruction_prefix;unsigned char saved[2]{};std::memcpy(saved,reinterpret_cast<void*>(at),2);DWORD protection=0;VirtualProtect(reinterpret_cast<void*>(at),2,PAGE_EXECUTE_READWRITE,&protection);put(at,std::uint16_t(0x0B0F));FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(at),2);VirtualProtect(reinterpret_cast<void*>(at),2,protection,&protection);check(exceptional(entries[i],reinterpret_cast<void*>(objects[i]),EXCEPTION_ILLEGAL_INSTRUCTION),"real exception in allocated trampoline continuation");VirtualProtect(reinterpret_cast<void*>(at),2,PAGE_EXECUTE_READWRITE,&protection);std::memcpy(reinterpret_cast<void*>(at),saved,2);FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(at),2);VirtualProtect(reinterpret_cast<void*>(at),2,protection,&protection);}
  }else check(false,"unknown case");
  check(restore(),"restore all six original sites under exclusive gate");hook::Report report{};snapshot(&report);check(report.restored&&!report.installed&&!report.uncertain&&report.written_mask==0&&report.active_executions==0,"transport final state");check(!publish(),"no republish/reset");rt::Report ar{};aiSnapshot(&ar);ec::Report er{};ecSnapshot(&er);check(ar.active==0&&er.active==0&&er.entries==er.exits,"adapter finally cleanup");
 }
 check(!std::memcmp(reinterpret_cast<void*>(image+0x2110B0),ec::BytesPredicate,sizeof ec::BytesPredicate),"global is_player never patched");check(RtlDeleteFunctionTable(originals)!=FALSE,"fixture original table removed");
 std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"rtl_virtual_unwind_checks\":%u,\"game_access\":false,\"own_process_code_only\":true,\"actual_six_site_publication_completed\":%s,\"game_publication_available\":false}\n",test.c_str(),unwindCount,completedPublish?"true":"false");return 0;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
