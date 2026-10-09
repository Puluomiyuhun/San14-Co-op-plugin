// Own process only: original six rules native callbacks plus seven A source
// stand-ins. A Runtime/Save is not linked in this test; Python labels it.
 put(world+0x3A,BYTE(12));
 const A keyboard=0x7500A000,head=0x7500B000;
 DWORD initProtect=0;check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READWRITE,&initProtect)!=FALSE,"owned setup");
 put(graph+0x18,A(16));put(graph+0x48,A(0));put(image+0x1FCA0A0,keyboard);
 put(image+0x1FC98B0,head);put(image+0x1FC98B8,A(0));for(unsigned i=0;i<3;++i)put(head+i*8,head);put(head+0x19,BYTE(1));
 const A slots[]={0x12CC4D0,0x12DC620,0x12CC9E0,0x1297D10};
 const A inlines[]={0x3F8606,0x3F9B16,0x13DC09};
 A oldSlots[4]{};BYTE oldCalls[3][5]{};
 for(unsigned i=0;i<4;++i){std::memcpy(&oldSlots[i],reinterpret_cast<void*>(image+slots[i]),8);put(image+slots[i],image+0x2170100);}
 put(image+0x2170100,BYTE(0xC3));
 for(unsigned i=0;i<3;++i){std::memcpy(oldCalls[i],reinterpret_cast<void*>(image+inlines[i]),5);put(image+inlines[i],BYTE(0xE8));put(image+inlines[i]+1,LONG(0x2170100-inlines[i]-5));}
 check(VirtualProtect(reinterpret_cast<void*>(image+0x1000),m.regions[image].size()-0x1000,PAGE_EXECUTE_READ,&discarded)!=FALSE,"owned RX");
 FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());
 std::printf("{\"event\":\"READY\",\"pid\":%lu}\n",GetCurrentProcessId());std::fflush(stdout);
 std::vector<Instance> retained;Instance* current=nullptr;bool saveRestored=false,inFlight=false;std::thread active;
 for(;;){int command=std::getchar();check(command!=EOF,"controller disconnected");if(command=='\n'||command=='\r')continue;
  if(command=='b'){
   unsigned long long address=0;check(scanf_s("%llu",&address)==1,"resident address");
   Instance i;i.module=reinterpret_cast<HMODULE>(address);i.descriptor=reinterpret_cast<const human_rules_stage::Descriptor*>(GetProcAddress(i.module,"HumanRulesActivationDescriptor"));check(i.descriptor,"descriptor");
   i.snapshot=api<DWORD(WINAPI*)(void*)>(i.module,"HumanRulesActivationReadReport");i.config=*reinterpret_cast<const stage::Config*>(GetProcAddress(i.module,"HumanRulesActivationBinding"));
   retained.push_back(i);current=&retained.back();std::puts("{\"event\":\"BOUND\"}");std::fflush(stdout);continue;
  }
  if(command=='e'){
   check(current,"bound");stage::Report before{},after{};current->snapshot(&before);
   const unsigned ds[]={2,11,20,21,3};
   for(unsigned route=0;route<4;++route)for(unsigned i=0;i<5;++i){
    const A object=route==0?forces+(i<2?(i==0?2:12):3)*0x1D0:route==1?district+ds[i]*0x28:route==2?army+(i+1)*0x200:group+(i+1)*0x40;
    const LONG previousCalls=bodies[route];reinterpret_cast<Fn>(current->descriptor->sites[route].address)(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(object));
    check(bodies[route]-previousCalls==(i<2?0:1),"two humans and delegated districts retain routes");
   }
   for(unsigned n=4;n<6;++n)for(unsigned force:{2u,12u,3u})check(reinterpret_cast<Pred>(current->descriptor->sites[n].address-4)(reinterpret_cast<void*>(forces+force*0x1D0))==int(force==2||force==12),"both human income predicates");
   current->snapshot(&after);for(unsigned n=0;n<4;++n)check(after.ai.entered[n]-before.ai.entered[n]==5&&after.ai.native[n]-before.ai.native[n]==3&&after.ai.bypassed[n]-before.ai.bypassed[n]==2,"actual counters");
   check(!after.ai.active&&!after.income.active&&after.income.entries-before.income.entries==6,"actual drained");
   std::puts("{\"event\":\"EXERCISED\",\"ai_entries\":20,\"bypassed\":8,\"native\":12,\"income_entries\":6,\"active\":0}");std::fflush(stdout);continue;
  }
  if(command=='t'){
   check(current,"installed before turn");constexpr A newStates=0x76000000;check(VirtualAlloc(reinterpret_cast<void*>(newStates),0x2000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE)==reinterpret_cast<void*>(newStates),"new planning states");
   std::memcpy(reinterpret_cast<void*>(newStates),reinterpret_cast<void*>(A(0x75003000)),0x2000);
   put(stack+3*8,newStates);put(stack+4*8,newStates+0x1000);put(world+0x37,BYTE(21));
   check(VirtualProtect(reinterpret_cast<void*>(A(0x75003000)),0x2000,PAGE_NOACCESS,&discarded)!=FALSE,"old states inaccessible");
   std::puts("{\"event\":\"TURN\",\"old_user\":1962950656,\"new_user\":1979715584,\"world_replaced\":false}");std::fflush(stdout);continue;
  }
  if(command=='a'){
   check(current&&!inFlight,"one native call");bodyEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);check(bodyEvent,"event");holdBody=true;inFlight=true;
   active=std::thread([&]{reinterpret_cast<Fn>(current->descriptor->sites[0].address)(reinterpret_cast<void*>(manager),reinterpret_cast<void*>(forces+3*0x1D0));});
   stage::Report r{};for(unsigned n=0;n<100;++n){current->snapshot(&r);if(r.ai.active==1)break;Sleep(10);}check(r.ai.active==1,"active callback");std::puts("{\"event\":\"ACTIVE\"}");std::fflush(stdout);continue;
  }
  if(command=='r'){check(inFlight,"release");SetEvent(bodyEvent);active.join();holdBody=false;CloseHandle(bodyEvent);inFlight=false;std::puts("{\"event\":\"DRAINED\"}");std::fflush(stdout);continue;}
  if(command=='x'){put(A(0x75004470),DWORD(3));std::puts("{\"event\":\"NONIDLE\"}");std::fflush(stdout);continue;}
  if(command=='s'){
   check(!inFlight,"drained");for(auto&i:retained)originals(i);
   for(unsigned i=0;i<4;++i){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image+slots[i]),8,PAGE_READWRITE,&old)!=FALSE,"slot restore");put(image+slots[i],oldSlots[i]);check(VirtualProtect(reinterpret_cast<void*>(image+slots[i]),8,old,&discarded)!=FALSE,"slot protection");}
   for(unsigned i=0;i<3;++i){DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(image+inlines[i]),5,PAGE_EXECUTE_READWRITE,&old)!=FALSE,"call restore");std::memcpy(reinterpret_cast<void*>(image+inlines[i]),oldCalls[i],5);check(VirtualProtect(reinterpret_cast<void*>(image+inlines[i]),5,old,&discarded)!=FALSE,"call protection");}
   FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(image),m.regions[image].size());saveRestored=true;std::puts("{\"event\":\"SOURCES_RESTORED\",\"mask\":127}");std::fflush(stdout);continue;
  }
  if(command=='q'){
   check(!inFlight&&saveRestored,"all callbacks and source stand-ins restored");for(auto&i:retained)originals(i);
   std::printf("{\"event\":\"FINAL\",\"resident_modules\":%llu,\"result\":\"PASS\"}\n",static_cast<unsigned long long>(retained.size()));return 0;
  }
  check(false,"unknown command");
 }
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
