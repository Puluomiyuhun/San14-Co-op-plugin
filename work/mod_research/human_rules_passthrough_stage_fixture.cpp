#include "human_rules_passthrough_stage.h"
#include "human_rules_hook_transport.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
#include "human_economy_runtime_profile.h"
#include <thread>
namespace ec=san14_economy_runtime;namespace stage=human_rules_stage;
using Fn=void(*)(void*,void*);using Pred=int(*)(void*);
constexpr A manager=0x73000000;
volatile LONG bodies[4]{};bool raiseBody=false;
void body(unsigned n,void*m,void*o){check(m==reinterpret_cast<void*>(A(0x74000000)+n*0x100)&&o,"original body ABI");InterlockedIncrement(&bodies[n]);if(raiseBody)RaiseException(0xE0056001,0,0,nullptr);}
void b0(void*m,void*o){body(0,m,o);}void b1(void*m,void*o){body(1,m,o);}void b2(void*m,void*o){body(2,m,o);}void b3(void*m,void*o){body(3,m,o);}
template<class T>T api(HMODULE m,const char*n){auto p=GetProcAddress(m,n);check(p!=nullptr,n);T f{};std::memcpy(&f,&p,sizeof f);return f;}
template<class T>void put(A p,T v){std::memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
void jump(A p,void*f){unsigned char b[14]{0xff,0x25};std::memcpy(b+6,&f,8);std::memcpy(reinterpret_cast<void*>(p),b,sizeof b);}
bool exceptional(Fn f,void*s){__try{f(reinterpret_cast<void*>(manager),s);}__except(GetExceptionCode()==0xE0056001?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){return true;}return false;}
int main(int argc,char**argv){try{
    check(argc==4,"case,dll,archived image");std::string test=argv[1];auto module=LoadLibraryA(argv[2]);check(module!=nullptr,"normal OS DLL load");
    auto prepare=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesStagePrepare");auto snapshot=api<void(*)(stage::Report*)noexcept>(module,"HumanRulesStageSnapshot");
    auto descriptor=reinterpret_cast<const stage::Descriptor*>(GetProcAddress(module,"HumanRulesStageDescriptor"));check(descriptor!=nullptr,"descriptor export");
    auto publish=api<bool(*)()noexcept>(module,"HumanRulesPublishCooperativeOwnProcess");auto restore=api<bool(*)()noexcept>(module,"HumanRulesRestoreCooperativeOwnProcess");
    auto enter=api<bool(*)()noexcept>(module,"HumanRulesEnterOwnedExecution");auto leave=api<void(*)()noexcept>(module,"HumanRulesLeaveOwnedExecution");
    Memory m;std::ifstream file(argv[3],std::ios::binary);check(bool(file),"archived source");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(file),{});populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));
    const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
    for(const auto&row:m.regions){auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned allocations");std::memcpy(p,row.second.data(),row.second.size());}
    const A at[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Fn f[]={b0,b1,b2,b3};for(unsigned i=0;i<4;++i)jump(image+at[i],reinterpret_cast<void*>(f[i]));
    const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
    Pred callers[2]{};for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);callers[i]=reinterpret_cast<Pred>(image+s.call_rva-4);}
    RUNTIME_FUNCTION unwind[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
    check(RtlAddFunctionTable(unwind,7,image)!=FALSE,"original unwind registration");DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image),m.regions[image].size(),PAGE_EXECUTE_READ,&old)!=FALSE,"source RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());
    if(test=="bad-profile"){DWORD saved=0;VirtualProtect(reinterpret_cast<void*>(image+0x2110B0),1,PAGE_EXECUTE_READWRITE,&saved);put(image+0x2110B0,std::uint8_t(0xCC));VirtualProtect(reinterpret_cast<void*>(image+0x2110B0),1,saved,&saved);}
    stage::Config config{};config.image=image;auto code=prepare(&config);stage::Report report{};snapshot(&report);
    if(test=="production-refuses-private"||test=="bad-profile"){
        check(code!=0&&report.state==stage::Rejected&&descriptor->preparation_state==stage::Rejected&&!publish(),"terminal rejection, no publication");
        check(!std::memcmp(reinterpret_cast<void*>(image+rt::HookSites[0].original.rva),rt::HookSites[0].original.bytes,rt::HookSites[0].original.size),"AI source untouched on rejection");
    }else{
        check(code==0&&report.state==stage::Prepared&&descriptor->preparation_state==stage::Prepared&&descriptor->fixture==1&&descriptor->policy_enabled==0,"prepared passive fixture");
        check(descriptor->pid==GetCurrentProcessId()&&descriptor->birth&&descriptor->module==reinterpret_cast<A>(module)&&descriptor->image==image&&descriptor->allocation,"actual descriptor identity");
        bool nonce=false;for(auto b:descriptor->nonce)nonce=nonce||b!=0;check(nonce,"fresh nonce");
        for(unsigned i=0;i<6;++i){const auto&s=descriptor->sites[i];check(s.patch_size==(i==0?16u:i<4?15u:5u)&&s.protection==PAGE_EXECUTE_READ,"known six source lengths/protection");check(!std::memcmp(reinterpret_cast<void*>(s.address),s.expected,s.profile_size),"stage did not change sources");MEMORY_BASIC_INFORMATION mb{};VirtualQuery(reinterpret_cast<void*>(s.destination),&mb,sizeof mb);check(mb.Protect==PAGE_EXECUTE_READ,"target executable");}
        check(publish(),"own-process publication through unchanged frozen transport");
        for(const auto&s:descriptor->sites)check(!std::memcmp(reinterpret_cast<void*>(s.address),s.replacement,s.patch_size),"descriptor exactly matches publisher patches");
        Fn entries[4]{};for(unsigned i=0;i<4;++i)entries[i]=reinterpret_cast<Fn>(descriptor->sites[i].address);
        const A subjects[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};
        if(test=="seh"){
            raiseBody=true;check(enter(),"lease");check(exceptional(entries[0],reinterpret_cast<void*>(subjects[0])),"original exception preserved through wrapper");leave();snapshot(&report);check(report.counters.abnormal==1&&report.counters.active==0&&report.counters.entered[0]==1&&report.counters.exited[0]==1,"finally counters");
        }else if(test=="forward"){
            for(unsigned v:{2u,12u}){put(world+0x3A,std::uint8_t(v));for(unsigned i=0;i<4;++i){check(enter(),"lease");entries[i](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(subjects[i]));leave();}
                for(unsigned i=0;i<2;++i)for(unsigned force:{2u,12u,3u}){check(enter(),"lease");int value=callers[i](reinterpret_cast<void*>(forces+force*0x1D0));leave();check(value==int(force==v),"unchanged local-viewer income predicate");}}
            snapshot(&report);for(unsigned i=0;i<6;++i)check(report.counters.entered[i]==(i<4?2u:6u)&&report.counters.exited[i]==report.counters.entered[i],"all six captured calls balanced");for(auto n:bodies)check(n==2,"all original AI bodies forwarded");check(report.counters.active==0&&!report.counters.abnormal&&!report.counters.unexpected_income_caller,"clean counters");
        }else check(false,"unknown case");
        check(restore(),"restore own source");for(const auto&s:descriptor->sites)check(!std::memcmp(reinterpret_cast<void*>(s.address),s.expected,s.profile_size),"exact originals restored");
        check(prepare(&config)==ERROR_ALREADY_INITIALIZED,"no reset");
    }
    std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"game_access\":false,\"policy_enabled\":false,\"real_cpu_original_wrappers\":%s}\n",test.c_str(),test=="forward"||test=="seh"?"true":"false");return 0;
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
