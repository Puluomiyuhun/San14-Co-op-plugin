// Owned fixture loop appended after frozen world's native-data initialization.
// Python factory alone performs LoadLibrary, Prepare and Seal.
 put(world+0x3A,BYTE(12));
 std::printf("{\"event\":\"READY\",\"pid\":%lu,\"image\":%llu}\n",GetCurrentProcessId(),image);std::fflush(stdout);
 std::vector<Instance> retained;Instance* current=nullptr;
 for(;;){int command=std::getchar();check(command!=EOF,"controller disconnected");if(command=='\n'||command=='\r')continue;
  if(command=='b'){
   unsigned long long address=0;check(scanf_s("%llu",&address)==1,"actual resident address");
   Instance i;i.module=reinterpret_cast<HMODULE>(address);i.descriptor=reinterpret_cast<const human_rules_stage::Descriptor*>(GetProcAddress(i.module,"HumanRulesActivationDescriptor"));check(i.descriptor,"descriptor installed remotely");
   i.snapshot=api<DWORD(WINAPI*)(void*)>(i.module,"HumanRulesActivationReadReport");
   auto*p=reinterpret_cast<const stage::Config*>(GetProcAddress(i.module,"HumanRulesActivationBinding"));check(p,"binding");i.config=*p;
   retained.push_back(i);current=&retained.back();std::puts("{\"event\":\"BOUND\"}");std::fflush(stdout);continue;
  }
  if(command=='e'){check(current,"current");exercise(*current);continue;}
  if(command=='x'){put(A(0x75004470),DWORD(3));std::puts("{\"event\":\"NONIDLE\"}");std::fflush(stdout);continue;}
  if(command=='n'){
   check(current&&retained.size()==1,"one owned replacement");originals(*current);
   constexpr A nextWorld=0x76000000;const auto size=m.regions.at(world).size();auto*w=VirtualAlloc(reinterpret_cast<void*>(nextWorld),size,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);check(w==reinterpret_cast<void*>(nextWorld),"new world");
   std::memcpy(w,reinterpret_cast<void*>(world),size);put(nextWorld+0x37,BYTE(21));put(nextWorld+0x3A,BYTE(2));put(root+0x85130,nextWorld);
   std::puts("{\"event\":\"LOADED\",\"actual_game_load\":false}");std::fflush(stdout);continue;
  }
  if(command=='q'){
   for(auto&i:retained)originals(i);
   std::printf("{\"event\":\"FINAL\",\"resident_modules\":%llu,\"result\":\"PASS\"}\n",static_cast<unsigned long long>(retained.size()));return 0;
  }
  check(false,"unknown owned command");
 }
}catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
