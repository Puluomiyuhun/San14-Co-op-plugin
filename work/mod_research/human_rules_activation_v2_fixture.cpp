#include "human_rules_activation_v2.h"
#include "human_rules_hook_transport.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
#include "human_economy_runtime_profile.h"
#include <thread>
namespace ec=san14_economy_runtime;namespace stage=human_rules_activation;
static_assert(sizeof(stage::Config)==136&&sizeof(stage::Seal)==72,"local loader ABI");
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
 check(argc==4||argc==5,"case,dll,archive,optional real room config");std::string test=argv[1];auto module=LoadLibraryA(argv[2]);check(module!=nullptr,"OS loaded candidate DLL");
 auto prepare=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationPrepare");auto snapshot=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationReadReport");
 auto seal=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationSeal");auto revoke=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationRevoke");auto*descriptor=reinterpret_cast<human_rules_stage::Descriptor*>(GetProcAddress(module,"HumanRulesActivationDescriptor"));check(descriptor!=nullptr,"descriptor");
 auto publish=api<bool(*)()noexcept>(module,"HumanRulesPublishCooperativeOwnProcess");auto restore=api<bool(*)()noexcept>(module,"HumanRulesRestoreCooperativeOwnProcess");
 auto transportEnter=api<bool(*)()noexcept>(module,"HumanRulesEnterOwnedExecution");auto transportLeave=api<void(*)()noexcept>(module,"HumanRulesLeaveOwnedExecution");
    Memory m;std::ifstream file(argv[3],std::ios::binary);check(bool(file),"archived source");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(file),{});populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));m.regions.emplace(0x75000000,std::vector<unsigned char>(0x10000));
    const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
    for(const auto&row:m.regions){auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned allocations");std::memcpy(p,row.second.data(),row.second.size());}
    put(image+0x1FD0C5C,LONG(1));put(image+0x18EB628,unsigned(1));put(world+0x34,WORD(203));put(world+0x36,BYTE(8));put(world+0x37,BYTE(11));put(world+0x40,DWORD(1));put(world+0x165D,BYTE(test=="liubei-idle1"?1:2));
    A graph=image+0x19E7310,stack=0x75005000;put(graph+0x10,A(5));put(graph+0x20,stack);put(graph+0x30,A(0));
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};const A vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    for(unsigned i=0;i<5;++i){A st=0x75000000+i*0x1000;put(stack+i*8,st);put(st,image+vt[i]);std::memcpy(reinterpret_cast<void*>(st+0x70),names[i],strlen(names[i])+1);}
    put(root,image+0x12AA6B0);put(world,image+0x12AA638);put(A(0x75004478),A(0x75007000));put(A(0x75007088),LONG(-1));put(A(0x75004400)+0x218,A(0x75008000));put(A(0x75002480),A(0x75009000));put(image+0x19E7510+0x13C,DWORD(1));put(image+0x201EC70,A(0));put(image+0x1A38EC8+0x28,DWORD(0));put(graph+0x38,A(0));put(graph+0x40,A(0));
    put(graph+0x48,A(0x75004000));put(A(0x75004470),DWORD(2));put(image+0x2025318,A(0x75006000));put(A(0x750063EC),LONG(-1));
    const A at[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Fn f[]={b0,b1,b2,b3};for(unsigned i=0;i<4;++i)jump(image+at[i],reinterpret_cast<void*>(f[i]));
    const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
    Pred callers[2]{};for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);callers[i]=reinterpret_cast<Pred>(image+s.call_rva-4);}
    RUNTIME_FUNCTION unwind[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
    check(RtlAddFunctionTable(unwind,7,image)!=FALSE,"original unwind registration");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image),m.regions[image].size(),PAGE_EXECUTE_READ,&old)!=FALSE,"source RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());

 stage::Config config{};config.image=image;config.root=root;config.world=world;config.room[0]=1;config.epoch[0]=77;config.rules_digest[0]=7;config.force[0]=2;config.force[1]=12;config.main_district[0]=2;config.main_district[1]=11;config.viewer=12;config.year=203;config.month=8;config.day=11;config.income_key5=1;
 if(test=="liubei-idle1"){put(world+0x3A,BYTE(2));config.viewer=2;}
 if(argc==5){std::ifstream cf(argv[4],std::ios::binary);check(bool(cf.read(reinterpret_cast<char*>(&config),sizeof config)),"actual exported room config");check(cf.peek()==EOF,"exact config length");}
 if(test=="wrong-settings")config.income_key5=2;if(test=="wrong-main")config.main_district[0]=20;
 auto result=prepare(&config);stage::Report report{};snapshot(&report);
 if(test=="wrong-settings"||test=="wrong-main"||test=="production-image-reject"){check(result!=0&&report.state==stage::Rejected,"invalid preparation denied");}
 else {
 check(result==0&&report.state==stage::Prepared,"prepared inactive with native settings/planning");
 stage::Seal q{};std::memcpy(q.nonce,descriptor->nonce,32);std::memcpy(q.room,config.room,16);std::memcpy(q.epoch,config.epoch,16);
 if(test=="wrong-epoch")q.epoch[0]^=1;
 if(test=="changed-planning")put(A(0x75004470),DWORD(3));
 if(test=="late-toolbar")put(A(0x75007088),LONG(6));
 if(test=="late-panel")put(A(0x750091B0),DWORD(1));
 if(test=="late-selection")put(A(0x750044A8),A(0x75000000));
 if(test=="transient-dispatch"){DWORD op=0;check(VirtualProtect(reinterpret_cast<void*>(graph+0x48),8,PAGE_READWRITE,&op)!=FALSE,"dispatch field write");put(graph+0x48,A(0));DWORD unused=0;check(VirtualProtect(reinterpret_cast<void*>(graph+0x48),8,op,&unused)!=FALSE,"dispatch field protection");}
 if(test=="prepublished")check(publish(),"early own-process publication");
 DWORD rc=0;
 if(test=="seal-fault-race"){
 auto pause=api<void(*)(HANDLE,HANDLE)>(module,"HumanRulesActivationFixturePauseSeal");HANDLE entered=CreateEventW(nullptr,TRUE,FALSE,nullptr),proceed=CreateEventW(nullptr,TRUE,FALSE,nullptr);check(entered&&proceed,"race events");pause(entered,proceed);
 std::thread sealing([&]{rc=seal(&q);});check(WaitForSingleObject(entered,2000)==WAIT_OBJECT_0,"Seal at final publication boundary");
 auto entry=api<Fn>(module,"HumanRulesActivationForce");std::thread violating([&]{entry(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(forces+3*0x1D0));});violating.detach();
 for(unsigned i=0;i<100;++i){snapshot(&report);if(report.blocked)break;Sleep(10);}check(report.state==stage::Faulted&&report.blocked==1,"concurrent unadmitted call faulted");SetEvent(proceed);sealing.join();snapshot(&report);check(rc==ERROR_OPERATION_ABORTED&&report.state==stage::Faulted&&bodies[0]==0,"Seal CAS cannot resurrect Faulted");CloseHandle(entered);CloseHandle(proceed);
 std::printf("{\"case\":\"seal-fault-race\",\"result\":\"PASS\",\"fault_terminal_preserved\":true}\n");return 0;
 }
 rc=seal(&q);snapshot(&report);
 if(test=="wrong-epoch"||test=="changed-planning"||test=="prepublished"||test=="late-toolbar"||test=="late-panel"||test=="late-selection") {check(rc!=0&&report.state==stage::Rejected,"seal fail terminal");if(test=="prepublished")check(restore(),"restore early fixture source");}
 else {
 check(rc==0&&report.state==stage::Sealed&&descriptor->policy_enabled==1,"production Seal available");check(seal(&q)==ERROR_INVALID_STATE,"second seal denied");check(publish(),"actual source publication");
 Fn entries[4]{};for(unsigned i=0;i<4;++i)entries[i]=reinterpret_cast<Fn>(image+rt::HookSites[i].original.rva);
 const A others[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};
 if(test=="routes"||test=="transient-dispatch"||test=="zhanglu-idle2"||test=="liubei-idle1"){
 check(transportEnter(),"own execution lease");const unsigned ds[]={2,11,20,21,3};
 for(unsigned viewer:{2u,12u}){put(world+0x3A,std::uint8_t(viewer));for(unsigned route=0;route<4;++route)for(unsigned i=0;i<5;++i){
 A object=route==0?forces+(i<2?(i==0?2:12):3)*0x1D0:route==1?district+ds[i]*0x28:route==2?army+(i+1)*0x200:group+(i+1)*0x40;auto before=bodies[route];entries[route](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(object));check(bodies[route]-before==(i<2?0:1),"actual four rules preserve delegated AI");}
 for(auto caller:callers)for(unsigned force:{2u,12u,3u})check(caller(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==2||force==12),"two exact income return PCs");
 auto unknown=api<Pred>(module,"HumanRulesActivationIncome");check(unknown(reinterpret_cast<void*>(forces+viewer*0x1D0))==1,"unknown UI caller native");}
 transportLeave();snapshot(&report);check(report.ai.active==0&&report.income.active==0,"normal cleanup");for(unsigned i=0;i<4;++i)check(report.ai.bypassed[i]==4&&report.ai.native[i]==6,"all four policies counted");
 }else if(test=="native-seh"){raiseBody=true;check(transportEnter(),"lease");check(exceptional(entries[0],reinterpret_cast<void*>(others[0])),"native SEH preserved");transportLeave();snapshot(&report);check(report.ai.abnormal_exits==1&&report.ai.active==0,"finally cleanup");}
 else if(test=="world-fatal"||test=="settings-fatal"||test=="revoked-fatal"){
 if(test=="world-fatal")put(root+0x85130,world+8);
 if(test=="settings-fatal"){DWORD op=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x18EB628),4,PAGE_READWRITE,&op)!=FALSE,"fixture settings change");put(image+0x18EB628,unsigned(2));DWORD unused=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x18EB628),4,op,&unused)!=FALSE,"restore protection");}
 if(test=="revoked-fatal"){auto bad=q;bad.epoch[0]^=1;check(revoke(&bad)!=0,"wrong revoke denied");check(revoke(&q)==0,"matching revoke persistent");}
 std::thread t([&]{entries[0](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(others[0]));});t.detach();
 std::thread u([&]{callers[0](reinterpret_cast<void*>(forces+2*0x1D0));});u.detach();
 for(unsigned i=0;i<100;++i){snapshot(&report);if(report.blocked>=2)break;Sleep(10);}check(report.state==stage::Faulted&&report.blocked==2&&bodies[0]==0,"both calls retained before native decision");
 Sleep(50);snapshot(&report);check(report.blocked==2,"no retry or timeout native fallback");
 std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"fatal_retained_calls\":2,\"recovery\":\"own process natural exit only\"}\n",test.c_str());return 0;
 }else check(false,"known case");
 check(restore(),"own source restored");
 }
 }
 check(prepare(&config)==ERROR_ALREADY_INITIALIZED,"one preparation");std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"initial_viewer\":%u,\"rank_derived_array_count\":%u,\"game_access\":false}\n",test.c_str(),config.viewer,unsigned(*reinterpret_cast<BYTE*>(world+0x165D)));return 0;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
