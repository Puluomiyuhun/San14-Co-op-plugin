// Archived event callback -> Reward virtual slot -> untagged pop.
// Event registration/button input and native UI services are NOT executed.
#define wmain CompletionPredecessorMain
#include "reward_menu_completion_fixture.cpp"
#undef wmain
int wmain(int argc,wchar_t**argv){if(argc!=4)return 2;try{
 World w;fixture=&w;load(w,argv[1]);const auto manager=w.b+0x19E7310;const std::wstring mode=argv[3];
 std::ifstream f(argv[2],std::ios::binary);std::vector<char> code((std::istreambuf_iterator<char>(f)),{});
 need(code.size()==14+21,"callback archive size");memcpy(w.image+0x5CC180,code.data(),14);memcpy(w.image+0x4D4AA0,code.data()+14,21);
 names[w.state]="Reward";generic(w,w.user,"User");
 const char*lower[]={"Root","Motor","Game","Strategy"};for(unsigned i=0;i<4;++i){auto p=w.alloc(0x600);generic(w,p,lower[i]);w.put(w.stack+i*8,p);}
 auto vt=at(w.state);w.put(vt,w.b+0x6115A0);w.put(vt+0x10,w.b+0x667B10);w.put(vt+0x18,w.b+0x665CD0);w.put(vt+0x20,w.b+0x665CD0);w.put(vt+0x70,w.b+0x4D4AA0);w.put<uint32_t>(w.state+0x6C,1);
 auto lv=w.alloc(0x100);w.put(w.layout,lv);w.put(lv,reinterpret_cast<uint64_t>(&deleteLayoutDouble));w.put(lv+0x40,reinterpret_cast<uint64_t>(&beforeDouble));w.put(lv+0x28,reinterpret_cast<uint64_t>(&contextDouble));
 auto allocator=w.alloc(16),av=w.alloc(0x100);w.put(allocator,av);w.put(av+0x58,reinterpret_cast<uint64_t>(&freeDouble));w.put(manager,allocator);w.put(manager+0x28,allocator);
 auto pending=w.alloc(1024);names[pending]="PendingStorage";w.put(manager+0x38,uint64_t(64));w.put(manager+0x40,pending);
 const auto callback=w.alloc(16);w.put(callback,w.b+0x1337E00);w.put(callback+8,w.state);w.put(w.b+0x1337E00+16,w.b+0x5CC180);
 need(FlushInstructionCache(GetCurrentProcess(),w.image,0x2400000)!=0,"flush");
 uint64_t payload=mode==L"zero-event"?0:100;
 auto notify=[&]{reinterpret_cast<void(*)(uint64_t,uint64_t*)>(at(at(callback)+16))(callback,&payload);};
 notify();if(mode==L"duplicate")notify();
 const auto queued=at(manager+0x30);need(queued==(mode==L"duplicate"?2u:1u),"callback queue count");
 for(uint64_t i=0;i<queued;++i)need(*reinterpret_cast<uint32_t*>(pending+i*16)==1&&at(pending+i*16+8)==0,"pop unexpectedly contains menu identity");
 need(events.size()==queued&&at(w.state+0x478)==w.layout,"notification is not native reward or completed teardown");
 if(mode==L"changed-top"){auto other=w.alloc(0x600);generic(w,other,"OtherMenu");w.put(w.stack+48,other);w.put(manager+0x10,uint64_t(7));}
 else need(mode==L"normal"||mode==L"duplicate"||mode==L"zero-event","unknown case");
 CompletionConsume(w.image+0x50A7BA,manager);
 std::vector<std::string> freed;for(const auto&e:events)if(e.event=="allocator_free_double"&&e.caller==0x50B26A)freed.push_back(e.object);
 if(mode==L"changed-top")need(freed==std::vector<std::string>{"OtherMenu"}&&at(w.state+0x478)==w.layout,"untagged cancellation foreign-top risk");
 else if(mode==L"duplicate")need(freed==std::vector<std::string>{"Reward","User"},"duplicate callback risk");
 else need(freed==std::vector<std::string>{"Reward"}&&at(w.state+0x478)==0,"callback teardown route");
 std::printf("{\"passed\":true,\"case\":\"%ls\",\"queued\":%llu,\"actual_callback_and_pop_executed\":true,\"queue_has_menu_identity\":false,\"ui_input_mapping_proven\":false,\"full_dispatcher_executed\":false,\"game_access\":false,\"production_permit\":false}\n",argv[3],queued);return 0;
 }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}}
