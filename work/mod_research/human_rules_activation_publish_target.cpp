// Own fixture starts normally; separate publisher attaches after this target prepares.
#include "human_rules_activation.h"
#include "human_ai_runtime_profile.h"
#include "human_economy_runtime_profile.h"
#include "human_economy_runtime_fixture_memory.h"
#include "human_economy_runtime_fixture_unwind.h"
#include <thread>
#include <atomic>
#include <vector>
namespace ec=san14_economy_runtime;namespace stage=human_rules_activation;
extern "C" __declspec(dllexport) std::uint64_t HumanRulesActivationDescriptorPointer=0;

using Fn=void(*)(void*,void*);using Pred=int(*)(void*);
constexpr A manager=0x73000000;volatile LONG bodies[4]{};bool raiseBody=false,holdBody=false;HANDLE bodyEvent=nullptr;
void body(unsigned n,void*m,void*o){check(m==reinterpret_cast<void*>(A(0x74000000)+n*0x100)&&o,"native body ABI");InterlockedIncrement(&bodies[n]);if(holdBody)WaitForSingleObject(bodyEvent,INFINITE);if(raiseBody)RaiseException(0xE0056001,0,0,nullptr);}
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
    auto prepare=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationPrepare");auto snapshot=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationReadReport");auto seal=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationSeal");auto revoke=api<DWORD(WINAPI*)(void*)>(module,"HumanRulesActivationRevoke");
    auto descriptor=reinterpret_cast<const human_rules_stage::Descriptor*>(GetProcAddress(module,"HumanRulesActivationDescriptor"));check(descriptor!=nullptr,"exported descriptor");
    Memory m;std::ifstream file(argv[4],std::ios::binary);check(bool(file),"archived code");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(file),{});populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));m.regions.emplace(0x75000000,std::vector<unsigned char>(0x10000));
    const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
    DWORD previous=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READWRITE,&previous)!=FALSE,"owned initialization only");
    for(const auto&row:m.regions){if(row.first==image){std::memcpy(reinterpret_cast<void*>(image+0x1000),row.second.data()+0x1000,row.second.size()-0x1000);continue;}auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned data");std::memcpy(p,row.second.data(),row.second.size());}
    put(image+0x1FD0C5C,LONG(1));put(image+0x18EB628,unsigned(1));put(world+0x34,WORD(203));put(world+0x36,BYTE(8));put(world+0x37,BYTE(11));put(world+0x40,DWORD(1));put(world+0x165D,BYTE(1));
    A graph=image+0x19E7310,stack=0x75005000;put(graph+0x10,A(5));put(graph+0x20,stack);put(graph+0x30,A(0));
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};const A vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    for(unsigned i=0;i<5;++i){A st=0x75000000+i*0x1000;put(stack+i*8,st);put(st,image+vt[i]);std::memcpy(reinterpret_cast<void*>(st+0x70),names[i],strlen(names[i])+1);}
    put(root,image+0x12AA6B0);put(world,image+0x12AA638);put(A(0x75004478),A(0x75007000));put(A(0x75007088),LONG(-1));put(A(0x75004400)+0x218,A(0x75008000));put(A(0x75002480),A(0x75009000));put(image+0x19E7510+0x13C,DWORD(1));put(image+0x201EC70,A(0));put(image+0x1A38EC8+0x28,DWORD(0));put(graph+0x38,A(0));put(graph+0x40,A(0));
    put(graph+0x48,A(0x75004000));put(A(0x75004470),DWORD(2));put(image+0x2025318,A(0x75006000));put(A(0x750063EC),LONG(-1));
    const A at[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Fn bodyFns[]={b0,b1,b2,b3};for(unsigned i=0;i<4;++i)jump(image+at[i],reinterpret_cast<void*>(bodyFns[i]));
    const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
    Pred callers[2]{};for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);callers[i]=reinterpret_cast<Pred>(image+s.call_rva-4);}
    const RUNTIME_FUNCTION functions[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
    std::memcpy(reinterpret_cast<void*>(image+0x2180000),functions,sizeof functions);
    DWORD discarded=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READ,&discarded)!=FALSE,"restore whole fixture RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());
    stage::Config config{};config.image=image;config.root=root;config.world=world;config.room[0]=1;config.epoch[0]=77;config.rules_digest[0]=7;config.force[0]=2;config.force[1]=12;config.main_district[0]=2;config.main_district[1]=11;config.viewer=12;config.year=203;config.month=8;config.day=11;config.income_key5=1;
    check(prepare(&config)==0&&descriptor->preparation_state==human_rules_stage::Prepared&&descriptor->fixture==1,"prepare frozen rule stage on MEM_IMAGE with explicit fixture type-query shim");
    stage::Seal ticket{};std::memcpy(ticket.nonce,descriptor->nonce,32);std::memcpy(ticket.room,config.room,16);std::memcpy(ticket.epoch,config.epoch,16);check(seal(&ticket)==0,"real pre-publication Seal");
    HumanRulesActivationDescriptorPointer=reinterpret_cast<A>(descriptor);
    Fn entries[4]{};for(unsigned i=0;i<4;++i)entries[i]=reinterpret_cast<Fn>(descriptor->sites[i].address);
    const A subjects[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};
    std::atomic<bool> go=false;std::atomic<unsigned> waiting=0;std::vector<std::thread> workers;
    for(unsigned t=0;t<3;++t)workers.emplace_back([&]{++waiting;while(!go.load())Sleep(1);for(unsigned n=0;n<10;++n){
      for(unsigned i=0;i<4;++i){entries[i](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(subjects[i]));
       A human=i==0?forces+2*0x1D0:i==1?district+2*0x28:i==2?army+1*0x200:group+1*0x40;
       entries[i](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(human));}
      for(auto f:callers)for(unsigned force:{2u,12u,3u})check(f(reinterpret_cast<void*>(forces+force*0x1D0))==int(rollback?force==12:force==2||force==12),"income selects both human seats only when installed");}});
    while(waiting.load()!=3)Sleep(1);
    std::printf("{\"phase\":\"prepared\",\"pid\":%lu,\"birth\":%llu,\"image\":%llu,\"descriptor\":%llu,\"nonce\":\"",GetCurrentProcessId(),descriptor->birth,descriptor->image,reinterpret_cast<A>(descriptor));
    for(auto byte:descriptor->nonce)std::printf("%02x",byte);std::printf("\",\"binding_hex\":\"");for(unsigned i=0;i<sizeof config;++i)std::printf("%02x",reinterpret_cast<unsigned char*>(&config)[i]);std::puts("\"}");std::fflush(stdout);
    check(std::getchar()=='g',"controller completed installation/detach");
    for(const auto&s:descriptor->sites)check(!std::memcmp(reinterpret_cast<void*>(s.address),rollback?s.expected:s.replacement,rollback?s.profile_size:s.patch_size),"external publisher installed or restored exact bytes");
    go=true;for(auto&w:workers)w.join();
    if(test=="native-seh"){raiseBody=true;check(exceptional(entries[0],reinterpret_cast<void*>(subjects[0])),"original exception through published rule stage");}
    stage::Report report{};snapshot(&report);
    for(unsigned i=0;i<4;++i){check(report.ai.entered[i]==(rollback?0u:60u+(test=="native-seh"&&i==0?1u:0u)),"both native and human AI calls observed");check(report.ai.bypassed[i]==(rollback?0u:30u),"actual human bypass");check(bodies[i]==(rollback?60:30)+(test=="native-seh"&&i==0?1:0),"actual native body count");}
    check(report.ai.active==0&&report.income.active==0&&report.income.entries==(rollback?0u:180u),"all callback counts settled");
    std::thread activeWorker;
    if(test=="active-native"){
      bodyEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);check(bodyEvent!=nullptr,"active native body event");holdBody=true;
      activeWorker=std::thread([&]{entries[0](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(subjects[0]));});
      for(unsigned i=0;i<100;++i){snapshot(&report);if(report.ai.active==1)break;Sleep(10);}check(report.state==stage::Sealed&&report.ai.active==1,"actual in-flight native original under Sealed");
    }
    if(test=="day-advanced")put(world+0x37,BYTE(21));
    if(test=="faulted"){
      check(revoke(&ticket)==0,"permanent real revoke");std::thread held([&]{entries[0](reinterpret_cast<void*>(manager),reinterpret_cast<void*>(subjects[0]));});held.detach();
      for(unsigned i=0;i<100;++i){snapshot(&report);if(report.blocked)break;Sleep(10);}check(report.state==stage::Faulted&&report.blocked==1,"actual call permanently retained");
    }
    std::puts("{\"phase\":\"ready_restore\"}");std::fflush(stdout);
    if(test=="active-native"){check(std::getchar()=='r',"active refusal recorded before release");SetEvent(bodyEvent);activeWorker.join();snapshot(&report);check(report.ai.active==0,"actual native body drained");std::puts("{\"phase\":\"ready_restore\"}");std::fflush(stdout);}
    check(std::getchar()=='f',"controller completed restoration/detach");
    if(test!="faulted")for(const auto&s:descriptor->sites)check(!std::memcmp(reinterpret_cast<void*>(s.address),s.expected,s.profile_size),"external restoration exact whole profiles");
    std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"actual_mem_image_stage\":true,\"game_access\":false,\"human_rules\":%s,\"fault_restart_only\":%s}\n",test.c_str(),rollback?"false":"true",test=="faulted"?"true":"false");return 0;
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
