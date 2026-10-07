#include "human_ai_runtime_adapter.h"
#include "human_ai_runtime_profile.h"
#include "human_ai_runtime_fixture_memory.h"
#include <thread>
#include <atomic>
namespace rt=san14_ai_runtime;
constexpr A forces=0x72000000;
static Memory*memory=nullptr;
static void*const manager=reinterpret_cast<void*>(0x73000000);
static rt::Wrapper entries[]={HumanAiForceEntry,HumanAiDistrictEntry,HumanAiArmyEntry,HumanAiGroupEntry};
static unsigned calls[4]{},callerCleanup=0;
static bool nativeThrow=false,nested=false;
static unsigned holdMode=0;
static rt::BlockingHold holdGate;
void body(unsigned route,void*m,void*o){
 check(m==manager&&o!=nullptr,"original ABI context");++calls[route];
 if(nativeThrow)RaiseException(0xE0051001,0,0,nullptr);
 if(nested&&route==3){nested=false;entries[0](manager,reinterpret_cast<void*>(forces+3*0x1D0));}
}
void original0(void*m,void*o){body(0,m,o);}void original1(void*m,void*o){body(1,m,o);}void original2(void*m,void*o){body(2,m,o);}void original3(void*m,void*o){body(3,m,o);}
void hold(void*,const rt::HeldCall&h){
 check(h.manager==manager&&h.object!=nullptr&&h.subject.decision==rt::Decision::Hold&&h.thread==GetCurrentThreadId(),"hold call ABI");
 if(holdMode==1){memory->put(person+2*0x200+0x11E,std::uint8_t(1));return;}
 if(holdMode==2){memory->put(army+0x200+0x12,std::uint16_t(2));return;}
 if(holdMode==3)RaiseException(0xE0051002,0,0,nullptr);
 rt::BlockingHold::Wait(&holdGate,h);
}
bool invokeSEH(rt::Wrapper f,void*o,DWORD expected){bool caught=false;__try{__try{f(manager,o);}__finally{++callerCleanup;}}__except(GetExceptionCode()==expected?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}return caught;}
void populate(Memory&m){
 m.fixed();m.regions.emplace(forces,std::vector<unsigned char>(52*0x1D0));
 for(const auto&a:rt::QueryAnchors)std::memcpy(m.at(image+a.rva,a.size),a.bytes,a.size);
 for(const auto&s:rt::HookSites)std::memcpy(m.at(image+s.original.rva,s.original.size),s.original.bytes,s.original.size);
 m.put(image+0x129FEB8,image+0x20B610);m.put(image+0x129FB78,image+0x2F6330);
 for(unsigned i=0;i<52;++i){m.put(root+0xDCA0+i*8,forces+i*0x1D0);m.put(forces+i*0x1D0,image+0x129FE58);m.put(forces+i*0x1D0+0x10,std::uint16_t(i));}
 m.put(world+0x3A,std::uint8_t(12));
 const unsigned ds[]={2,11,20,21,3},fs[]={2,12,2,12,3},leaders[]={2,12,20,21,3};
 for(unsigned i=0;i<5;++i){
  m.put(district+ds[i]*0x28+0x10,std::uint8_t(fs[i]));m.put(district+ds[i]*0x28+0x11,std::uint8_t(i==2||i==3?2:1));m.put(district+ds[i]*0x28+0x12,std::uint16_t(leaders[i]));
  m.put(person+leaders[i]*0x200+0x10,std::uint16_t(leaders[i]));m.put(person+leaders[i]*0x200+0x118,std::uint8_t(ds[i]));m.put(person+leaders[i]*0x200+0x11E,std::uint8_t(1));
  m.put(army+(i+1)*0x200+0x10,std::uint8_t(1));m.put(army+(i+1)*0x200+0x12,std::uint16_t(leaders[i]));m.put(army+(i+1)*0x200+0x58,std::uint16_t(i+1));
 }
 m.list(0,{{1},{2},{3},{4},{5}});m.list(1,{});m.list(2,{});
 m.put(root+0xC8,image+0x123F3F8);m.put(root+0xD0,aux+24);m.put(aux+24,std::uint32_t(2));m.put(aux+0x110,aux+0x18000);m.put(aux+0x130,aux+0x18000+4*24);m.put(aux+0x150,A(5));
 for(unsigned i=0;i<5;++i){const A n=aux+0x18000+i*24;m.put(n,district+ds[i]*0x28);m.put(n+8,i<4?n+24:A(0));m.put(n+16,i?n-24:A(0));}
}
int main(int argc,char**argv){try{
 check(argc==3,"case and DLL required");const std::string test=argv[1];
 HMODULE dll=LoadLibraryA(argv[2]);check(dll!=nullptr,"load real adapter DLL");
 bool(*configure)(const rt::Config*)noexcept=nullptr;void(*snapshot)(rt::Report*)noexcept=nullptr;
 auto proc=GetProcAddress(dll,"HumanAiRuntimeConfigure");check(proc!=nullptr,"configure export");std::memcpy(&configure,&proc,sizeof proc);
 proc=GetProcAddress(dll,"HumanAiRuntimeSnapshot");check(proc!=nullptr,"snapshot export");std::memcpy(&snapshot,&proc,sizeof proc);
 const char* names[]={"HumanAiForceEntry","HumanAiDistrictEntry","HumanAiArmyEntry","HumanAiGroupEntry"};
 for(unsigned i=0;i<4;++i){proc=GetProcAddress(dll,names[i]);check(proc!=nullptr,"entry export");std::memcpy(&entries[i],&proc,sizeof proc);}
 Memory m;memory=&m;populate(m);
 rt::Config c{};c.reader={&m,Memory::read};c.image=image;c.root=root;c.human_mask=(A(1)<<2)|(A(1)<<12);c.hold=hold;c.original[0]=original0;c.original[1]=original1;c.original[2]=original2;c.original[3]=original3;
 if(test=="bad-binding"){m.put(forces+2*0x1D0+0x10,std::uint16_t(6001));check(!configure(&c),"reject invalid ruler binding");}
 else if(test=="bad-original"){c.original[0]=reinterpret_cast<rt::Wrapper>(image+rt::HookSites[0].original.rva);check(!configure(&c),"reject recursion original");}
 else if(test=="profile"){m.put(image+rt::HookSites[2].original.rva,std::uint8_t(0));check(!configure(&c),"reject modified outer wrapper");}
 else {
  check(configure(&c),"configure");check(!configure(&c),"configuration immutable");
  if(test=="routes"){
   const unsigned ds[]={2,11,20,21,3};for(unsigned viewer:{2u,12u}){m.put(world+0x3A,std::uint8_t(viewer));for(unsigned route=0;route<4;++route)for(unsigned i=0;i<5;++i){const A object=route==0?forces+(i<2?(i==0?2:12):3)*0x1D0:route==1?district+ds[i]*0x28:route==2?army+(i+1)*0x200:group+(i+1)*0x40;auto previous=calls[route];entries[route](manager,reinterpret_cast<void*>(object));check(calls[route]-previous==(i<2?0u:1u),"two humans and delegated routing");check(*static_cast<std::uint8_t*>(m.at(world+0x3A,1))==viewer,"local identity retained");}}
  }else if(test=="nested"){nested=true;entries[3](manager,reinterpret_cast<void*>(group+3*0x40));check(calls[3]==1&&calls[0]==1,"nested exact route");}
  else if(test=="native-exception"){nativeThrow=true;check(invokeSEH(entries[2],reinterpret_cast<void*>(army+3*0x200),0xE0051001)&&callerCleanup==1,"native unwind");}
  else if(test=="binding-repair"){holdMode=1;m.put(person+2*0x200+0x11E,std::uint8_t(0));entries[0](manager,reinterpret_cast<void*>(forces+2*0x1D0));check(calls[0]==0,"repair protects human");}
  else if(test=="army-repair"){holdMode=2;m.put(army+0x200+0x12,std::uint16_t(6001));entries[2](manager,reinterpret_cast<void*>(army+0x200));check(calls[2]==0,"unresolved army repaired before bypass");}
  else if(test=="hold-exception"){holdMode=3;check(invokeSEH(entries[3],reinterpret_cast<void*>(group+6*0x40),0xE0051002)&&callerCleanup==1&&calls[3]==0,"hold unwinds rather than silently dropping");}
  else if(test=="blocking-hold"){
   m.put(world+0x16A8,std::uint32_t(0x100));std::atomic<bool>done{false};std::thread worker([&]{entries[1](manager,reinterpret_cast<void*>(district+3*0x28));done.store(true);});
   for(unsigned i=0;i<2000&&!holdGate.Waiting();++i)Sleep(1);check(holdGate.Waiting()==1&&!done.load()&&calls[1]==0,"intercepted call actually blocked");m.put(world+0x16A8,std::uint32_t(0));holdGate.RequestRetry();worker.join();check(done.load()&&calls[1]==1,"retry rereads before original");
  }else if(test=="main-order-change"){
   // Changing a delegated district to a main-kind candidate earlier in native
   // list order changes the selected main; the adapter must not cache old IDs.
   m.put(district+20*0x28+0x11,std::uint8_t(1));m.put(aux+0x18000,district+20*0x28);m.put(aux+0x18000+2*24,district+2*0x28);entries[1](manager,reinterpret_cast<void*>(district+20*0x28));entries[1](manager,reinterpret_cast<void*>(district+2*0x28));check(calls[1]==1,"fresh ordered main district");
  }else check(false,"unknown case");
  rt::Report report{};snapshot(&report);check(report.configured&&!report.installed&&report.active==0,"cleanup/installation boundary");std::uint64_t entered=0;for(auto n:report.entered)entered+=n;check(entered==report.exits,"all entries exited");check(report.abnormal_exits==((test=="native-exception"||test=="hold-exception")?1u:0u),"abnormal bookkeeping");
 }
 std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"game_access\":false,\"game_ai_body_executed\":false,\"subject_stubs\":false,\"inline_hook_installed\":false,\"actual_dll_exports\":true}\n",test.c_str());return 0;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
