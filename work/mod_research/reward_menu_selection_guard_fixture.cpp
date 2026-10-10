#include "reward_menu_selection_guard.h"
// Frozen fixture supplies the actual archive loader and named service doubles.
#define wmain FrozenSelectionMain
#include "reward_menu_selection_fixture.cpp"
#undef wmain
namespace sg=reward_menu_selection_guard;
static sg::Guard selectionGuard;
static std::wstring guardCase;
extern "C" void SelectionGuardEventBridge();
static __declspec(noinline) unsigned selectionInvoke(uintptr_t descriptor){
 const auto pc=uintptr_t(_ReturnAddress());selectionGuard.BeginCall(descriptor,pc);
 const auto result=reinterpret_cast<unsigned(*)(uintptr_t)>(w->b+0x21ED10)(descriptor);
 selectionGuard.CallReturned(result,pc);return result;
}
static __declspec(noinline) uintptr_t selectionCtor(uintptr_t object,uintptr_t parameters){
 const auto pc=uintptr_t(_ReturnAddress());const auto value=reinterpret_cast<uintptr_t(*)(uintptr_t,uintptr_t)>(w->b+0x22C450)(object,parameters);
 selectionGuard.Created(value,parameters,pc);return value;
}
static __declspec(noinline) void selectionWait(uintptr_t reward){
 const auto pc=uintptr_t(_ReturnAddress());selectionGuard.BeforeWait(reward,pc);
 reinterpret_cast<void(*)(uintptr_t)>(w->b+0x50B690)(reward);
 selectionGuard.WaitReturned(reward,pc);
}
extern "C" __declspec(noinline) void SelectionGuardEvent(uintptr_t reward,uintptr_t event,uintptr_t pc){
 if(guardCase==L"wrong-selection")put(w->manager+0x48,w->alloc(0x100));
 selectionGuard.Event(reward,event,pc);
 // Observation rejection is not a claimed safe fault continuation. The owned
 // fixture deliberately executes the old handler to expose stale-result risk.
 reinterpret_cast<void(*)(uintptr_t,uintptr_t)>(w->b+0x509F50)(reward,event);
}
static unsigned noCallbackWait(uintptr_t handle,int timeout){
 need(handle==0x123456&&timeout==-1&&at(w->manager+0x30)==1,"missing-callback scenario reaches real task wait call");
 ++w->waits;put<uint64_t>(w->manager+0x30,0);return 0;
}
static void installOwnedProbes(const sg::Config&c){
 const uintptr_t sites[]={0x68F9FB,0x21F028,0x21EDBF,0x4FABD7};
 for(unsigned i=0;i<4;++i){jump(c.relays[i],reinterpret_cast<void*>(c.entries[i]));put<unsigned char>(w->b+sites[i],0xE8);put<int32_t>(w->b+sites[i]+1,int32_t(c.relays[i]-(w->b+sites[i]+5)));}
 put<unsigned char>(w->b+0x4FABDC,0xC3);FlushInstructionCache(GetCurrentProcess(),w->image,0x2400000);
}
int wmain(int argc,wchar_t**argv){if(argc!=3)return 2;try{
 World owned;w=&owned;guardCase=argv[2];const auto veh=AddVectoredExceptionHandler(1,failure);need(veh!=nullptr,"owned exception trace");load(argv[1]);
 if(guardCase==L"cancel-result")w->code=0x7FFFFFFE;
 else if(guardCase==L"unknown-result")w->code=0x1234;
 else if(guardCase==L"taskless"){w->taskless=true;put<uintptr_t>(w->reward+0x50,0);put<unsigned>(w->reward+0x58,1);}
 else if(guardCase==L"missing-callback"){put(w->b+0x123C1E0,uintptr_t(&noCallbackWait));put<unsigned>(w->reward+0x58,1);}
 else need(guardCase==L"accept-result"||guardCase==L"foreign-source"||guardCase==L"wrong-selection","bounded known case");
 sg::Config c{};c.base=w->b;c.reward=w->reward;c.layout=w->layout;c.task=at(w->reward+0x50);c.thread=GetCurrentThreadId();c.generation=7;memset(c.menu_id,'a',32);
 for(unsigned i=0;i<5;++i)c.states[i]=at(w->stack+i*8);
 c.entries[0]=uintptr_t(&selectionInvoke);c.entries[1]=uintptr_t(&selectionCtor);c.entries[2]=uintptr_t(&selectionWait);c.entries[3]=uintptr_t(&SelectionGuardEventBridge);
 for(unsigned i=0;i<4;++i)c.relays[i]=w->b+0x900000+i*32;
 const bool bound=selectionGuard.Bind(c);need(bound==(guardCase!=L"taskless"),"no task cannot bind a successful wait observation");installOwnedProbes(c);
 if(guardCase==L"foreign-source")need(!selectionGuard.BeginCall(0,w->b+0x68FA01)&&selectionGuard.Snapshot().error==sg::Error::Source,"foreign source PC rejected before descriptor read");
 reinterpret_cast<void(*)(uintptr_t)>(w->b+0x68F760)(w->reward);
 const bool good=guardCase==L"accept-result"||guardCase==L"cancel-result";
 need(selectionGuard.Finish()==good,"only actual known event plus original complete return accepted");
 sg::Receipt receipt{};need(selectionGuard.Take(receipt)==good,"terminal event/source failures never yield a receipt");
 if(good){need(receipt.generation==7&&receipt.thread==GetCurrentThreadId()&&receipt.eventCode==w->code&&receipt.accepted==(guardCase==L"accept-result")&&receipt.selection_return_observed&&!receipt.production_permit&&!receipt.native_suspend_proven&&!memcmp(receipt.menu_id,c.menu_id,33),"exact pure-ID selection receipt");need(!selectionGuard.Take(receipt),"one-shot receipt");}
 else need(!receipt.selection_return_observed&&!receipt.production_permit,"failure output stays empty");
 auto r=selectionGuard.Snapshot();need(r.completed==(good?1u:0u)&&r.taken==(good?1u:0u),"completion cannot be inferred from old nonzero result");
 if(guardCase==L"missing-callback")need(w->events==0&&at<unsigned>(w->reward+0x58)==1&&w->appendCalls==1&&r.events==0,"old success result really flowed through original caller but guard refused it");
 if(guardCase==L"unknown-result")need(at<unsigned>(w->reward+0x58)==7&&w->appendCalls==1&&r.error==sg::Error::Event,"unknown event retains old result yet produces no receipt");
 if(guardCase==L"taskless")need(w->waits==0&&at(w->manager+0x30)==1&&r.error==sg::Error::Task,"actual taskless native return leaves queue and no completion");
 if(guardCase==L"wrong-selection")need(r.error==sg::Error::Selection,"foreign active selection rejected");
 printf("{\"passed\":true,\"case\":\"%ls\",\"phase\":%u,\"error\":%u,\"created\":%u,\"waited\":%u,\"events\":%u,\"wait_returned\":%u,\"call_returned\":%u,\"completed\":%u,\"taken\":%u,\"native_result_value\":%u,\"native_event_callbacks\":%u,\"actual_archived_chain\":true,\"original_return_pc_probes\":true,\"task_services_double\":true,\"activation_double\":true,\"native_suspend_proven\":false,\"production_permit\":false,\"game_access\":false}\n",guardCase.c_str(),unsigned(r.phase),unsigned(r.error),r.created,r.waited,r.events,r.waitReturned,r.callReturned,r.completed,r.taken,at<unsigned>(w->reward+0x58),w->events);
 RemoveVectoredExceptionHandler(veh);return 0;
 }catch(const std::exception&e){fprintf(stderr,"selection guard fixture: %s\n",e.what());return 1;}}
