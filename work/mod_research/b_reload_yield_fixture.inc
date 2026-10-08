// Only owned, archived-code fixtures. Business decides when to yield; the
// actual reset, yield, parent resume and worker continuation execute natively.
static unsigned yieldCalls=0,yieldParentResumes=0;
static bool yieldUnwindRegistered=false;
static void yieldPrepare(){
 struct Span{uintptr_t rva;const unsigned char* bytes;size_t size;};
 const Span spans[]={{0x509EF0,b_reload_yield_profile::ResetBytes,sizeof b_reload_yield_profile::ResetBytes},
  {0x834820,b_reload_yield_profile::SetBytes,sizeof b_reload_yield_profile::SetBytes},
  {0x834640,b_reload_yield_profile::EventResetBytes,sizeof b_reload_yield_profile::EventResetBytes}};
 for(auto&s:spans){DWORD old=0;boundRequire(VirtualProtect(reinterpret_cast<void*>(base+s.rva),s.size,PAGE_READWRITE,&old)!=FALSE,"owned yield helper writable");memcpy(reinterpret_cast<void*>(base+s.rva),s.bytes,s.size);boundRequire(VirtualProtect(reinterpret_cast<void*>(base+s.rva),s.size,old,&old)&&FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(base+s.rva),s.size),"archived yield helper RX restored");}
 const unsigned char resetUw[]={1,6,2,0,6,0x32,2,0x30},eventUw[]={1,4,1,0,4,0x42,0,0};
 memcpy(reinterpret_cast<void*>(base+0xBC0),resetUw,sizeof resetUw);memcpy(reinterpret_cast<void*>(base+0xBE0),eventUw,sizeof eventUw);
 if(!yieldUnwindRegistered){auto*t=new RUNTIME_FUNCTION[3]{{0x509EF0,0x509F4F,0xBC0},{0x834820,0x83483C,0xBE0},{0x834640,0x83465C,0xBE0}};boundRequire(parentAddFunctions(t,3,base),"actual reset and event wrapper unwind registered");yieldUnwindRegistered=true;}
}
static void yieldBody(uintptr_t state){
 check(rootExercise&&rootExercise->task->state==state,"yield is on the actual current Root stack");auto&t=*rootExercise->task;
 check(!rootExercise->yielded&&!at<DWORD>(t.worker+0x58)&&!at<DWORD>(t.worker+0x78),"yield precedes task done and occurs once");
 hw::HardwareReceipt before{};
 const bool input=providerCase==L"nested-input-yield";
 if(input){check(admissionBundle&&hw::Snapshot(admissionBundle->hardware,before)&&before.entered&&!before.finished,"actual nested input observation stays armed during yield");}
 check(ResetEvent(t.ready)!=FALSE,"fixture removes initial ready signal before native wait");
 rootExercise->yielded=true;reinterpret_cast<void(*)(uintptr_t)>(base+0x50B690)(state);
 ++yieldCalls;
 check(!at<DWORD>(t.worker+0x78)&&!at<DWORD>(t.worker+0x58)&&at<uintptr_t>(state+0x50)==t.worker,"actual reset and resume preserve the same unfinished worker");
 rootports::Report r{};rootports::Snapshot(rootExercise->ports,r);check(r.yields==1&&r.accepted[3]==1&&r.captured==1&&r.error==rootports::Error::None,"native yield accepted before Root return");
 if(input){hw::HardwareReceipt after{};check(hw::Snapshot(admissionBundle->hardware,after)&&after.entered&&!after.finished&&after.error==hw::Error::None,"nested input scope survives native yield without false completion");}
}
static void yieldParentResume(StatePort&t){
 if(providerCase!=L"root-native-yield"&&providerCase!=L"nested-input-yield")return;
 if(!at<DWORD>(t.worker+0x78)||at<DWORD>(t.worker+0x58))return;
 auto m=base+0x19E7310;
 check(!at<uintptr_t>(m+0x48)&&at<uintptr_t>(t.state+0x50)==t.worker,"yielded parent iteration keeps unfinished task");
 b_reload_queue_parent_source::Report before{};parentSource.Snapshot(before);
 check(!before.active&&before.error==b_reload_queue_parent_source::Error::None,"first parent scope finishes before native resume");
 // Restore the same fixture scheduler isolation for the second iteration.
 // No task ticket/capture or +78 flag is manufactured here.
 for(unsigned i=0;i<parentStateCount;++i)if(parentOtherStates[i]!=t.state){auto dummy=alloc(4096);put<uintptr_t>(dummy+0x10,dummy+0x100);put<DWORD>(dummy+0x78,1);put<uintptr_t>(parentOtherStates[i]+0x50,dummy);}
 auto first=parentOtherStates[0],vt=at<uintptr_t>(first);if(!vt){vt=alloc(4096);parentTemporaryState=first;put<uintptr_t>(first,vt);}
 DWORD protection=0;boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x30),8,PAGE_READWRITE,&protection)!=FALSE,"fixture second parent status writable");put<uintptr_t>(vt+0x30,uintptr_t(&parentStatus));boundRequire(VirtualProtect(reinterpret_cast<void*>(vt+0x30),8,protection,&protection)!=FALSE,"fixture second parent status restored");
 put<std::uint64_t>(m+0x30,0);
 reinterpret_cast<void(*)(uintptr_t)>(base+0x509EF0)(t.state);
 check(!at<DWORD>(t.worker+0x78)&&WaitForSingleObject(t.done,0)==WAIT_TIMEOUT,"archived reset clears yield and resets the same completion event");
 using Native=void(*)(uintptr_t,uintptr_t,uintptr_t,uintptr_t);
 reinterpret_cast<Native>(base+0x13DC05)(m,0,0,0);
 b_reload_queue_parent_source::Report after{};parentSource.Snapshot(after);
 check(after.accepted[2]==before.accepted[2]+1&&after.accepted[0]==before.accepted[0]&&after.accepted[1]==before.accepted[1]&&after.accepted[3]==before.accepted[3]+1&&after.error==b_reload_queue_parent_source::Error::None,"native resume completes original ticket without fresh or duplicate creation");
 ++yieldParentResumes;
 printf("{\"native_yield_resume\":true,\"parent_resumes\":%u,\"native_reset\":true,\"nested_input\":%s,\"game_access\":false}\n",yieldParentResumes,providerCase==L"nested-input-yield"?"true":"false");
}
