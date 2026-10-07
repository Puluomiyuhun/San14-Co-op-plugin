// Created by the paired publisher only. No process lookup or game access.
#include "human_rules_passthrough_stage.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
#include <thread>
#include <atomic>
#include <vector>
namespace ec=san14_economy_runtime;namespace stage=human_rules_stage;
extern "C" __declspec(dllexport) std::uint64_t HumanRulesStageDescriptorPointer=0;
extern "C" __declspec(dllexport) void HumanRulesStageDebugBreak();
using Fn=void(*)(void*,void*);using Pred=int(*)(void*);
constexpr A manager=0x73000000;volatile LONG bodies[4]{};bool raiseBody=false;
void body(unsigned n,void*m,void*o){check(m==reinterpret_cast<void*>(A(0x74000000)+n*0x100)&&o,"native body ABI");InterlockedIncrement(&bodies[n]);if(raiseBody)RaiseException(0xE0056001,0,0,nullptr);}
void b0(void*m,void*o){body(0,m,o);}void b1(void*m,void*o){body(1,m,o);}void b2(void*m,void*o){body(2,m,o);}void b3(void*m,void*o){body(3,m,o);}
template<class T>T api(HMODULE m,const char*n){auto p=GetProcAddress(m,n);check(p!=nullptr,n);T f{};std::memcpy(&f,&p,sizeof f);return f;}
template<class T>void put(A p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
void jump(A p,void*f){unsigned char b[14]{0xff,0x25};std::memcpy(b+6,&f,8);std::memcpy(reinterpret_cast<void*>(p),b,sizeof b);}
bool exceptional(Fn f,void*s){__try{f(reinterpret_cast<void*>(manager),s);}__except(GetExceptionCode()==0xE0056001?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}return false;}
int main(int argc,char**argv){try{
    check(argc==5,"case,stage,image,archive");std::string test=argv[1];
    const bool rollback=test.size()==10&&test.rfind("rollback-",0)==0&&test[9]>='0'&&test[9]<='5';
    auto module=LoadLibraryA(argv[2]),mapped=LoadLibraryA(argv[3]);check(module&&reinterpret_cast<A>(mapped)==image,"owned fixture PE at preferred base");
    MEMORY_BASIC_INFORMATION info{};check(VirtualQuery(reinterpret_cast<void*>(image+0xC6660),&info,sizeof info)==sizeof info&&info.Type==MEM_IMAGE,"real OS MEM_IMAGE mapping");
    auto prepare=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesStagePrepare");auto snapshot=api<void(*)(stage::Report*)noexcept>(module,"HumanRulesStageSnapshot");
    auto descriptor=reinterpret_cast<const stage::Descriptor*>(GetProcAddress(module,"HumanRulesStageDescriptor"));check(descriptor!=nullptr,"exported descriptor");
    Memory m;std::ifstream file(argv[4],std::ios::binary);check(bool(file),"archived code");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(file),{});populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));
    const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
    DWORD previous=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READWRITE,&previous)!=FALSE,"owned initialization only");
    for(const auto&row:m.regions){if(row.first==image){std::memcpy(reinterpret_cast<void*>(image+0x1000),row.second.data()+0x1000,row.second.size()-0x1000);continue;}auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned data");std::memcpy(p,row.second.data(),row.second.size());}
    const A at[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Fn bodyFns[]={b0,b1,b2,b3};for(unsigned i=0;i<4;++i)jump(image+at[i],reinterpret_cast<void*>(bodyFns[i]));
    const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
    Pred callers[2]{};for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);callers[i]=reinterpret_cast<Pred>(image+s.call_rva-4);}
    const RUNTIME_FUNCTION functions[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
    std::memcpy(reinterpret_cast<void*>(image+0x2180000),functions,sizeof functions);
    DWORD discarded=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READ,&discarded)!=FALSE,"restore whole fixture RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());
    stage::Config config{};config.image=image;check(prepare(&config)==0&&descriptor->preparation_state==stage::Prepared&&descriptor->fixture==1,"prepare real stage on MEM_IMAGE");
    HumanRulesStageDescriptorPointer=reinterpret_cast<A>(descriptor);
    Fn entries[4]{};for(unsigned i=0;i<4;++i)entries[i]=reinterpret_cast<Fn>(descriptor->sites[i].address);
    const A subjects[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};
    std::atomic<bool> go=false;std::atomic<unsigned> waiting=0;std::vector<std::thread> workers;
    for(unsigned t=0;t<3;++t)workers.emplace_back([&]{++waiting;while(!go.load())Sleep(1);for(unsigned n=0;n<10;++n){for(unsigned i=0;i<4;++i)entries[i](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(subjects[i]));for(auto f:callers)for(unsigned force:{2u,12u,3u})check(f(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==12),"income unchanged");}});
    while(waiting.load()!=3)Sleep(1);
    HumanRulesStageDebugBreak(); // Publisher owns this event; no source writes in child.
    for(const auto&s:descriptor->sites)check(!std::memcmp(reinterpret_cast<void*>(s.address),rollback?s.expected:s.replacement,rollback?s.profile_size:s.patch_size),"external publisher installed or restored exact bytes");
    go=true;for(auto&w:workers)w.join();
    if(test=="native-seh"){raiseBody=true;check(exceptional(entries[0],reinterpret_cast<void*>(subjects[0])),"original exception through published stage");}
    else check(test=="success"||rollback,"supported case");
    stage::Report report{};snapshot(&report);
    for(unsigned i=0;i<6;++i){const std::uint64_t expected=rollback?0:(i<4?30u:90u)+(test=="native-seh"&&i==0?1u:0u);check(report.counters.entered[i]==expected&&report.counters.exited[i]==expected,"all native calls observed");}
    for(unsigned i=0;i<4;++i)check(bodies[i]==(test=="native-seh"&&i==0?31:30),"original bodies executed even after rollback");
    check(report.counters.active==0&&report.counters.abnormal==(test=="native-seh"?1u:0u)&&report.counters.unexpected_income_caller==0,"stage final cleanup");
    HumanRulesStageDebugBreak(); // All test calls have returned before source restoration.
    for(const auto&s:descriptor->sites)check(!std::memcmp(reinterpret_cast<void*>(s.address),s.expected,s.profile_size),"external restoration exact whole profiles");
    std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"actual_mem_image_stage\":true,\"four_ai_calls\":%u,\"two_income_calls\":180,\"stage_hook_calls\":%u,\"game_access\":false,\"policy_enabled\":false}\n",test.c_str(),test=="native-seh"?121:120,rollback?0:test=="native-seh"?301:300);return 0;
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
