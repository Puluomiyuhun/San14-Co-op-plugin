#include "checkpoint_native_input_pending_adapter.h"
#include <array>
#include <cstdio>
#include <cstring>
#include <cstdlib>
namespace p=checkpoint_native_input_pending;
template<class T>static void put(void* a,size_t off,T v){memcpy(static_cast<unsigned char*>(a)+off,&v,sizeof v);}
template<size_t N>static p::Span span(const std::array<unsigned char,N>&a){return{a.data(),N};}
static void need(bool ok,const char*why){if(!ok){fprintf(stderr,"FAIL %s\n",why);exit(1);}}
struct Memory {
 std::array<unsigned char,0x668>user{};std::array<unsigned char,0x8c>toolbar{};
 std::array<unsigned char,0x488>game{};std::array<unsigned char,0x1f8>panel{};
 std::array<unsigned char,0x50>manager{};std::array<unsigned char,0x30>stack{};
 std::array<unsigned char,0x40>queue{};std::array<unsigned char,0x3f4>cache{};
 p::Config c{};
 Memory(){c.profile_base=0x140000000;c.binding.attempt[0]=1;c.binding.attachment[0]=2;c.binding.owner_generation=3;
  c.user=span(user);c.toolbar=span(toolbar);c.game=span(game);c.panel=span(panel);c.manager=span(manager);c.stack=span(stack);c.load_cache=span(cache);
  c.states[0]=0x11110000;c.states[1]=0x22220000;c.states[2]=uintptr_t(game.data());c.states[3]=0x33330000;c.states[4]=uintptr_t(user.data());
  put(user.data(),0,c.profile_base+0x12CC4A8);put(game.data(),0,c.profile_base+0x12CC9B8);
  memcpy(user.data()+0x70,"CUserStrategyState",19);memcpy(game.data()+0x70,"CGameState",11);
  put<unsigned>(user.data(),0x470,2);put(user.data(),0x478,uintptr_t(toolbar.data()));put<int>(toolbar.data(),0x88,-1);
  put(game.data(),0x480,uintptr_t(panel.data()));put<uint64_t>(manager.data(),0x10,5);put(manager.data(),0x20,uintptr_t(stack.data()));put(manager.data(),0x48,uintptr_t(user.data()));
  for(unsigned i=0;i<5;++i)put(stack.data(),i*8,c.states[i]);put<unsigned>(cache.data(),8,1);put<int>(cache.data(),0x3ec,-1);
 }
 void allocate(){c.queue=span(queue);put(manager.data(),0x40,uintptr_t(queue.data()));put<uint64_t>(manager.data(),0x38,4);}
};
int main(int argc,char**argv){
 const bool baseline=argc==2&&!strcmp(argv[1],"baseline");Memory m;p::Adapter a;
 auto bound=a.Bind(m.c);
 if(baseline){need(bound==p::Error::Span,"frozen inspector reproduces actual null-vector rejection");puts("{\"baseline_rejects_empty_vector\":true}");return 0;}
 need(bound==p::Error::None,"exact empty vector can bind");auto original=m;
 auto r=a.InspectCurrent(m.c.binding);need(r.error==p::Error::None&&r.decision==p::Decision::QuiescentObserved,"empty vector inspected without reads from null");
 need(!memcmp(&m,&original,sizeof m),"read-only inspection preserves all supplied memory");
 CheckpointPushFrame frame{};frame.slot=0;frame.thread_id=GetCurrentThreadId();frame.call_id=1;frame.args[0]=uintptr_t(m.user.data());frame.caller_entry_rsp=0x55550000;
 need(a.ObserveBefore(m.c.binding,frame).error==p::Error::None,"actual before on empty queue");
 need(a.ObserveBeforeFetch(m.c.binding,1,m.user.data()).pending_admission_candidate,"paired empty queue prefetch");
 need(a.ObserveAfter(m.c.binding,frame).pending_admission_candidate,"paired after remains observed");p::Ticket ticket{};
 need(a.BeginAuthorizedLoadPush(m.c.binding,1,ticket)==p::Error::NoAuthorization,"same ABI cannot authorize an unbound new queue");
 need(a.CloseAfter(m.c.binding,1)==p::Error::None,"close without mutation");
 put<uint64_t>(m.manager.data(),0x30,1);need(a.InspectCurrent(m.c.binding).error==p::Error::Layout,"nonzero count at zero capacity rejects");put<uint64_t>(m.manager.data(),0x30,0);
 m.allocate();need(a.InspectCurrent(m.c.binding).error==p::Error::Pointer,"old binding refuses newly allocated native queue");
 p::Adapter fresh;need(fresh.Bind(m.c)==p::Error::None&&fresh.InspectCurrent(m.c.binding).decision==p::Decision::QuiescentObserved,"fresh span can inspect allocated queue");
 put<uint64_t>(m.manager.data(),0x30,1);need(fresh.InspectCurrent(m.c.binding).decision==p::Decision::UnownedStateQueue,"pending native request is never called idle");
 put<uint64_t>(m.manager.data(),0x30,5);need(fresh.InspectCurrent(m.c.binding).error==p::Error::Layout,"count beyond capacity rejects");
 put<uint64_t>(m.manager.data(),0x30,0);put<uint64_t>(m.manager.data(),0x38,0);need(fresh.InspectCurrent(m.c.binding).error==p::Error::Layout,"allocated pointer plus zero capacity rejects");
 m.c.queue={nullptr,16};p::Adapter bad;need(bad.Bind(m.c)==p::Error::Span,"partial null span rejects");
 m.c.queue={m.queue.data(),0};p::Adapter bad2;need(bad2.Bind(m.c)==p::Error::Span,"partial zero span rejects");
 puts("{\"empty_vector_inspected\":true,\"new_queue_requires_fresh_binding\":true,\"empty_vector_load_authorized\":false,\"game_access\":false}");return 0;
}
