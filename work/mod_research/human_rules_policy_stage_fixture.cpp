#include "human_rules_policy_stage.h"
#include "human_rules_hook_transport.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
#include "human_economy_runtime_profile.h"
#include <thread>
namespace ec=san14_economy_runtime;namespace stage=human_rules_policy;
using Fn=void(*)(void*,void*);using Pred=int(*)(void*);
constexpr A manager=0x73000000;
volatile LONG bodies[4]{};bool raiseBody=false;
void body(unsigned n,void*m,void*o){check(m==reinterpret_cast<void*>(A(0x74000000)+n*0x100)&&o,"original body ABI");InterlockedIncrement(&bodies[n]);if(raiseBody)RaiseException(0xE0056001,0,0,nullptr);}
void b0(void*m,void*o){body(0,m,o);}void b1(void*m,void*o){body(1,m,o);}void b2(void*m,void*o){body(2,m,o);}void b3(void*m,void*o){body(3,m,o);}
template<class T>T api(HMODULE m,const char*n){auto p=GetProcAddress(m,n);check(p!=nullptr,n);T f{};std::memcpy(&f,&p,sizeof f);return f;}
template<class T>void put(A p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
void jump(A p,void*f){unsigned char b[14]{0xff,0x25};std::memcpy(b+6,&f,8);std::memcpy(reinterpret_cast<void*>(p),b,sizeof b);}
bool exceptional(Fn f,void*s,DWORD code=0xE0056001){__try{f(reinterpret_cast<void*>(manager),s);}__except(GetExceptionCode()==code?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}return false;}
void holdAI(void*,const san14_ai_runtime::HeldCall&){RaiseException(0xE0057001,0,0,nullptr);}
void holdIncome(void*,const san14_economy_runtime::HeldCall&){RaiseException(0xE0057002,0,0,nullptr);}
bool incomeException(Pred f,void*force){__try{f(force);}__except(GetExceptionCode()==0xE0057002?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}return false;}
int main(int argc,char**argv){try{
 check(argc==4,"case,dll,archive");std::string test=argv[1];auto module=LoadLibraryA(argv[2]);check(module!=nullptr,"OS loaded candidate DLL");
 auto prepare=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesPolicyPrepare");auto snapshot=api<void(*)(stage::Report*)noexcept>(module,"HumanRulesPolicySnapshot");
 auto publish=api<bool(*)()noexcept>(module,"HumanRulesPublishCooperativeOwnProcess");auto restore=api<bool(*)()noexcept>(module,"HumanRulesRestoreCooperativeOwnProcess");
 auto transportEnter=api<bool(*)()noexcept>(module,"HumanRulesEnterOwnedExecution");auto transportLeave=api<void(*)()noexcept>(module,"HumanRulesLeaveOwnedExecution");
    Memory m;std::ifstream file(argv[3],std::ios::binary);check(bool(file),"archived source");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(file),{});populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));
    const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
    for(const auto&row:m.regions){auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned allocations");std::memcpy(p,row.second.data(),row.second.size());}
    const A at[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Fn f[]={b0,b1,b2,b3};for(unsigned i=0;i<4;++i)jump(image+at[i],reinterpret_cast<void*>(f[i]));
    const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
    Pred callers[2]{};for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);callers[i]=reinterpret_cast<Pred>(image+s.call_rva-4);}
    RUNTIME_FUNCTION unwind[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
    check(RtlAddFunctionTable(unwind,7,image)!=FALSE,"original unwind registration");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image),m.regions[image].size(),PAGE_EXECUTE_READ,&old)!=FALSE,"source RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());

 stage::Config config{};config.image=image;config.root=root;config.world=world;config.room_epoch=77;config.force[0]=2;config.force[1]=12;config.main_district[0]=2;config.main_district[1]=11;config.settings_receipt[0]=0x71;config.ai_hold=holdAI;config.income_hold=holdIncome;
 if(test=="wrong-main")config.main_district[0]=20;
 if(test=="wrong-world")config.world=world+8;
 if(test=="missing-receipt")config.settings_receipt[0]=0;
 auto result=prepare(&config);stage::Report report{};snapshot(&report);
 if(test=="wrong-main"||test=="wrong-world"||test=="missing-receipt"){
  check(result!=0&&report.state==stage::Rejected,"invalid binding rejected");
 }else{
  check(result==0&&report.state==stage::Prepared&&!report.active&&!report.production_activation_available,"prepared inactive");
  check(publish(),"actual frozen transport source publication");
  Fn entries[4]{};for(unsigned i=0;i<4;i++)entries[i]=reinterpret_cast<Fn>(image+rt::HookSites[i].original.rva);
  const A others[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};
  // Before activation every candidate entry preserves native behavior.
  check(transportEnter(),"transport lease");for(unsigned i=0;i<4;i++)entries[i](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(others[i]));
  for(auto caller:callers)for(unsigned force:{2u,12u,3u})check(caller(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==12),"inactive income is native local viewer");transportLeave();
  snapshot(&report);for(auto n:report.ai.entered)check(n==0,"inactive AI did not enter policy");check(report.income.entries==0,"inactive tail jump did not enter policy");
  if(test=="production-disabled")check(GetProcAddress(module,"HumanRulesPolicyFixtureActivate")==nullptr,"no production activation export");
  else{
   auto enter=api<bool(*)()>(module,"HumanRulesPolicyFixtureEnter");auto leave=api<void(*)()>(module,"HumanRulesPolicyFixtureLeave");auto activate=api<bool(*)(std::uint64_t)>(module,"HumanRulesPolicyFixtureActivate");
   check(!activate(78),"wrong epoch no activation");check(enter()&&!activate(77),"cannot activate within own call lease");leave();
   check(activate(77)&&!activate(77),"one activation under actual exclusive lease");
   check(enter()&&transportEnter(),"both execution owners acquired");
   if(test=="routes"){
    const unsigned ds[]={2,11,20,21,3};
    for(unsigned viewer:{2u,12u}){put(world+0x3A,std::uint8_t(viewer));
     for(unsigned route=0;route<4;route++)for(unsigned i=0;i<5;i++){
      A object=route==0?forces+(i<2?(i==0?2:12):3)*0x1D0:route==1?district+ds[i]*0x28:route==2?army+(i+1)*0x200:group+(i+1)*0x40;
      auto before=bodies[route];entries[route](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(object));check(bodies[route]-before==(i<2?0:1),"two humans protected, delegated and AI original");
     }
     for(auto caller:callers)for(unsigned force:{2u,12u,3u})check(caller(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==2||force==12),"both audited income callers preserve actual return address and share human rule");
     auto unknown=api<Pred>(module,"HumanRulesPolicyIncome");for(unsigned force:{2u,12u,3u})check(unknown(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==viewer),"unknown caller retains native local UI");
    }
   }else if(test=="native-seh"){raiseBody=true;check(exceptional(entries[0],reinterpret_cast<void*>(others[0])),"native exception crosses actual tramp and frozen finally");}
   else if(test=="world-hold"){put(root+0x85130,world+8);check(exceptional(entries[0],reinterpret_cast<void*>(others[0]),0xE0057001),"changed world held before native AI");check(incomeException(callers[0],reinterpret_cast<void*>(forces+2*0x1D0)),"changed world held before income");put(root+0x85130,world);}
   else check(false,"unsupported case");
   transportLeave();leave();snapshot(&report);check(report.active&&report.ai.active==0&&report.income.active==0,"all cleanup drained");
   if(test=="routes"){for(unsigned i=0;i<4;i++)check(report.ai.bypassed[i]==4&&report.ai.native[i]==6,"four route decisions counted");check(report.income.human==8&&report.income.ai==4&&report.income.native==6,"income actual known/unknown caller counts");}
   if(test=="native-seh")check(report.ai.abnormal_exits==1,"native finally recorded");
   if(test=="world-hold")check(report.ai.abnormal_exits==1&&report.income.abnormal==1&&report.ai.held[0]==1&&report.income.held==1,"Hold not silently discarded");
  }
  check(restore(),"restore own source");
 }
 check(prepare(&config)==ERROR_ALREADY_INITIALIZED,"immutable preparation");
 std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"game_access\":false,\"real_memory_resolvers\":true,\"actual_native_call_sites\":%s,\"production_activation\":false}\n",test.c_str(),result==0?"true":"false");return 0;
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
