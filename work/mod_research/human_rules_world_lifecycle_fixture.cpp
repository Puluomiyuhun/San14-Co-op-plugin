// Two distinct resident activation_v2 instances; only own-process data and image.
// Frozen helpers are reused without calling/changing the original fixture main.
#define main FrozenSingleWorldMain
#include "human_rules_activation_publish_v2_target.cpp"
#undef main
struct Instance {
 HMODULE module=nullptr;
 const human_rules_stage::Descriptor* descriptor=nullptr;
 stage::Config config{};
 DWORD(WINAPI*snapshot)(void*)=nullptr;
 DWORD(WINAPI*revoke)(void*)=nullptr;
};
Instance prepareInstance(const char* path,A currentWorld,unsigned generation){
 Instance i;i.module=LoadLibraryA(path);check(i.module!=nullptr,"fresh resident module");
 auto prepare=api<DWORD(WINAPI*)(void*)>(i.module,"HumanRulesActivationPrepare");
 auto seal=api<DWORD(WINAPI*)(void*)>(i.module,"HumanRulesActivationSeal");
 i.snapshot=api<DWORD(WINAPI*)(void*)>(i.module,"HumanRulesActivationReadReport");
 i.revoke=api<DWORD(WINAPI*)(void*)>(i.module,"HumanRulesActivationRevoke");
 i.descriptor=reinterpret_cast<const human_rules_stage::Descriptor*>(GetProcAddress(i.module,"HumanRulesActivationDescriptor"));check(i.descriptor,"descriptor");
 auto& c=i.config;c.image=image;c.root=root;c.world=currentWorld;c.room[0]=1;c.epoch[0]=BYTE(76+generation);c.rules_digest[0]=7;
 c.force[0]=2;c.force[1]=12;c.main_district[0]=2;c.main_district[1]=11;c.viewer=12;c.year=203;c.month=8;c.day=generation==1?11:21;c.income_key5=1;
 check(prepare(&c)==0,"Prepare fresh instance");
 stage::Seal ticket{};std::memcpy(ticket.nonce,i.descriptor->nonce,32);std::memcpy(ticket.room,c.room,16);std::memcpy(ticket.epoch,c.epoch,16);
 check(seal(&ticket)==0,"Seal fresh instance");
 check(prepare(&c)==ERROR_ALREADY_INITIALIZED,"same instance cannot reset Prepare");
 std::printf("{\"event\":\"PREPARED\",\"generation\":%u,\"pid\":%lu,\"birth\":%llu,\"module\":%llu,\"descriptor\":%llu,\"binding_hex\":\"",generation,GetCurrentProcessId(),i.descriptor->birth,reinterpret_cast<A>(i.module),reinterpret_cast<A>(i.descriptor));
 for(unsigned n=0;n<sizeof c;++n)std::printf("%02x",reinterpret_cast<unsigned char*>(&c)[n]);
 std::printf("\",\"nonce\":\"");for(auto b:i.descriptor->nonce)std::printf("%02x",b);std::puts("\",\"game_access\":false}");std::fflush(stdout);return i;
}
void originals(const Instance& i){
 for(const auto&s:i.descriptor->sites)check(!memcmp(reinterpret_cast<void*>(s.address),s.expected,s.profile_size),"all six original profiles restored");
 stage::Report r{};i.snapshot(&r);check(r.ai.active==0&&r.income.active==0,"old instance has no active callbacks");
}
void exercise(Instance&i){
 const A native[]={forces+3*0x1D0,district+3*0x28,army+5*0x200,group+5*0x40};
 const A human[]={forces+2*0x1D0,district+2*0x28,army+1*0x200,group+1*0x40};
 for(unsigned n=0;n<4;++n){auto f=reinterpret_cast<Fn>(i.descriptor->sites[n].address);f(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(native[n]));f(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(human[n]));}
 for(unsigned n=4;n<6;++n){auto f=reinterpret_cast<Pred>(i.descriptor->sites[n].address-4);for(unsigned force:{2u,12u,3u})check(f(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==2||force==12),"both human incomes after rebind");}
 stage::Report r{};i.snapshot(&r);for(unsigned n=0;n<4;++n)check(r.ai.entered[n]==2&&r.ai.native[n]==1&&r.ai.bypassed[n]==1,"AI routes in this generation");
 check(r.ai.active==0&&r.income.active==0&&r.income.entries==6,"generation drained");
 std::puts("{\"event\":\"EXERCISED\",\"ai_entries\":8,\"ai_bypassed\":4,\"income_entries\":6,\"active\":0}");std::fflush(stdout);
}
int main(int argc,char**argv){try{
 check(argc==5,"stage1 stage2 owned-image archive");
 auto mapped=LoadLibraryA(argv[3]);check(reinterpret_cast<A>(mapped)==image,"owned image at preferred base");
    Memory m;std::ifstream file(argv[4],std::ios::binary);check(bool(file),"archived code");m.regions[image]=std::vector<unsigned char>(std::istreambuf_iterator<char>(file),{});populate(m);m.regions.emplace(manager,std::vector<unsigned char>(0x100));m.regions.emplace(0x75000000,std::vector<unsigned char>(0x10000));
    const unsigned offsets[]={0x10,0x18,0x28,0x20};for(unsigned i=0;i<4;++i)m.put(manager+offsets[i],A(0x74000000+i*0x100));
    DWORD previous=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READWRITE,&previous)!=FALSE,"owned initialization only");
    for(const auto&row:m.regions){if(row.first==image){std::memcpy(reinterpret_cast<void*>(image+0x1000),row.second.data()+0x1000,row.second.size()-0x1000);continue;}auto*p=VirtualAlloc(reinterpret_cast<void*>(row.first),row.second.size(),MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(p==reinterpret_cast<void*>(row.first),"owned data");std::memcpy(p,row.second.data(),row.second.size());}
    put(image+0x1FD0C5C,LONG(1));put(image+0x18EB628,unsigned(1));put(world+0x34,WORD(203));put(world+0x36,BYTE(8));put(world+0x37,BYTE(11));put(world+0x40,DWORD(1));put(world+0x165D,BYTE(2));
    A graph=image+0x19E7310,stack=0x75005000;put(graph+0x10,A(5));put(graph+0x20,stack);put(graph+0x30,A(0));
    const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};const A vt[]={0,0x12F22D8,0x12CC9B8,0x12CD400,0x12CC4A8};
    for(unsigned i=0;i<5;++i){A st=0x75000000+i*0x1000;put(stack+i*8,st);put(st,image+vt[i]);std::memcpy(reinterpret_cast<void*>(st+0x70),names[i],strlen(names[i])+1);}
    put(root,image+0x12AA6B0);put(world,image+0x12AA638);put(A(0x75004478),A(0x75007000));put(A(0x75007088),LONG(-1));put(A(0x75004400)+0x218,A(0x75008000));put(A(0x75002480),A(0x75009000));put(image+0x19E7510+0x13C,DWORD(1));put(image+0x201EC70,A(0));put(image+0x1A38EC8+0x28,DWORD(0));put(graph+0x38,A(0));put(graph+0x40,A(0));
    put(graph+0x48,A(0x75004000));put(A(0x75004470),DWORD(2));put(image+0x2025318,A(0x75006000));put(A(0x750063EC),LONG(-1));
    const A at[]={0xA9160,0xA8E50,0xA8CF0,0xA9220};Fn bodyFns[]={b0,b1,b2,b3};for(unsigned i=0;i<4;++i)jump(image+at[i],reinterpret_cast<void*>(bodyFns[i]));
    const unsigned char prefix[]={0x48,0x83,0xEC,0x28},suffix[]={0x48,0x83,0xC4,0x28,0xC3},uw[]={1,4,1,0,4,0x42,0,0};std::memcpy(reinterpret_cast<void*>(image+0x2170000),uw,sizeof uw);
    for(unsigned i=0;i<2;++i){auto&s=ec::Callsites[i];std::memcpy(reinterpret_cast<void*>(image+s.call_rva-4),prefix,4);std::memcpy(reinterpret_cast<void*>(image+s.return_rva),suffix,5);}
    const RUNTIME_FUNCTION functions[]={{0xC6580,0xC65E3,0x1778018},{0xC65F0,0xC6653,0x1778018},{0xC6660,0xC669C,0x17AB260},{0xC66A0,0xC6703,0x1778018},{0x2110B0,0x211109,predicateUnwindRva},{0x28DAA1,0x28DAAF,0x2170000},{0x28DE6D,0x28DE7B,0x2170000}};
    std::memcpy(reinterpret_cast<void*>(image+0x2180000),functions,sizeof functions);
    DWORD discarded=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READ,&discarded)!=FALSE,"restore whole fixture RX");FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());

 Instance first=prepareInstance(argv[1],world,1),second{};Instance* current=&first;
 std::thread active;bool inFlight=false;unsigned worldsLoaded=0;
 for(;;){int command=std::getchar();check(command!=EOF,"controller disconnected");
 if(command=='e'){exercise(*current);continue;}
 if(command=='d'){put(current->config.world+0x37,BYTE(21));std::puts("{\"event\":\"DATE_ADVANCED\"}");std::fflush(stdout);continue;}
 if(command=='a'){
  check(!inFlight,"only one held native call");bodyEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);check(bodyEvent!=nullptr,"active event");holdBody=true;inFlight=true;
  active=std::thread([&]{reinterpret_cast<Fn>(current->descriptor->sites[0].address)(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(forces+3*0x1D0));});
  stage::Report r{};for(unsigned n=0;n<100;++n){current->snapshot(&r);if(r.ai.active==1)break;Sleep(10);}check(r.ai.active==1,"actual native active");
  std::puts("{\"event\":\"ACTIVE\",\"active\":1}");std::fflush(stdout);continue;
 }
 if(command=='r'){check(inFlight,"release held native");SetEvent(bodyEvent);active.join();holdBody=false;CloseHandle(bodyEvent);inFlight=false;std::puts("{\"event\":\"DRAINED\",\"active\":0}");std::fflush(stdout);continue;}
 if(command=='n'){
  check(current==&first&&!inFlight,"one transition under fixture execution fence");originals(first);
  constexpr A nextWorld=0x76000000;const auto size=m.regions.at(world).size();auto*w=VirtualAlloc(reinterpret_cast<void*>(nextWorld),size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(w==reinterpret_cast<void*>(nextWorld),"distinct next world");
  std::memcpy(w,reinterpret_cast<void*>(world),size);put(nextWorld+0x37,BYTE(21));put(root+0x85130,nextWorld);++worldsLoaded;
  std::puts("{\"event\":\"LOADED\",\"generation\":2,\"actual_game_load\":false}");std::fflush(stdout);continue;
 }
 if(command=='p'){
  check(worldsLoaded==1&&current==&first&&!second.module,"prepare only after replacement");
  A actualWorld=0;std::memcpy(&actualWorld,reinterpret_cast<void*>(root+0x85130),8);
  second=prepareInstance(argv[2],actualWorld,2);check(second.module!=first.module,"independent resident instance");current=&second;continue;
 }
 if(command=='q'){
  check(!inFlight,"no active thread at exit");originals(*current);stage::Report old{};first.snapshot(&old);check(old.ai.active==0&&old.income.active==0,"retained old calls settled");
  std::printf("{\"event\":\"FINAL\",\"result\":\"PASS\",\"worlds_loaded\":%u,\"resident_modules\":%u,\"active\":0,\"game_access\":false,\"actual_game_load\":false}\n",worldsLoaded,second.module?2:1);return 0;
 }
 check(false,"unknown fixture command");
 }
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
