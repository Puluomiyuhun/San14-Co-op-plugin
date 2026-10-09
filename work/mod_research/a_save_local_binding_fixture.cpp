// Owned memory only. Exercise actual Sampler + successor inspector together.
#define main frozen_inspector_fixture_main
#include "checkpoint_native_input_pending_empty_queue_fixture.cpp"
#undef main
#include "a_save_local_binding.h"
namespace local=a_save_local_binding;
int main(){
 Memory m;auto base=uintptr_t(VirtualAlloc(nullptr,0x2300000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
 auto root=uintptr_t(VirtualAlloc(nullptr,0x86000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(base&&root,"allocate own native layout");
 m.c.profile_base=base;put(m.user.data(),0,base+0x12CC4A8);put(m.game.data(),0,base+0x12CC9B8);
 put<uint64_t>(m.manager.data(),0x18,6);auto manager=reinterpret_cast<void*>(base+0x19E7310);memcpy(manager,m.manager.data(),m.manager.size());
 put(reinterpret_cast<void*>(base),0x1FCA1E0,root);put(reinterpret_cast<void*>(root),0x85130,uintptr_t(m.cache.data()));put(reinterpret_cast<void*>(base),0x2025318,uintptr_t(m.cache.data()));
 local::Config c{};c.binding=m.c.binding;c.base=base;c.root=root;c.world=uintptr_t(m.cache.data());c.cache=uintptr_t(m.cache.data());memcpy(c.states,m.c.states,sizeof c.states);
 local::Sampler sampler;need(sampler.Initialize(c)&&!sampler.Initialize(c),"single immutable initialization");
 p::Config actual{};need(sampler.Capture(actual)&&!actual.queue.data&&!actual.queue.size,"fresh native unallocated queue yields exact empty span");
 p::Adapter a;need(a.Bind(actual)==p::Error::None&&a.InspectCurrent(actual.binding).decision==p::Decision::QuiescentObserved,"actual sampler feeds original ABI inspector");
 put(manager,0x40,uintptr_t(m.queue.data()));put<uint64_t>(manager,0x38,4);
 need(a.InspectCurrent(actual.binding).error==p::Error::Pointer,"previous empty binding cannot follow reallocation");
 need(sampler.Capture(actual)&&actual.queue.data==m.queue.data()&&actual.queue.size==64,"fresh sampling observes new allocation");
 p::Adapter next;need(next.Bind(actual)==p::Error::None&&next.InspectCurrent(actual.binding).decision==p::Decision::QuiescentObserved,"new adapter sees currently allocated empty vector");
 put<uint64_t>(manager,0x30,1);need(sampler.Capture(actual),"sampler returns pending data without granting idle");
 p::Adapter pending;need(pending.Bind(actual)==p::Error::None&&pending.InspectCurrent(actual.binding).decision==p::Decision::UnownedStateQueue,"pending request still rejects idle");
 put<uint64_t>(manager,0x30,5);need(!sampler.Capture(actual)&&!actual.user.data,"bad vector clears entire output");put<uint64_t>(manager,0x30,0);
 put(manager,0x40,uintptr_t(0));need(!sampler.Capture(actual),"null pointer with nonzero capacity rejected");put<uint64_t>(manager,0x38,0);
 put<uint64_t>(manager,0x18,5);need(!sampler.Capture(actual),"stack lacks inspector's 48 byte minimum");put<uint64_t>(manager,0x18,6);
 put(reinterpret_cast<void*>(root),0x85130,uintptr_t(m.cache.data())+8);need(!sampler.Capture(actual),"world replacement rejected");put(reinterpret_cast<void*>(root),0x85130,uintptr_t(m.cache.data()));
 const auto old=m.c.states[3];put(m.stack.data(),24,old+8);need(!sampler.Capture(actual),"state replacement rejected");put(m.stack.data(),24,old);
 auto bad=uintptr_t(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_NOACCESS));need(bad!=0,"unreadable own page");put(m.user.data(),0x478,bad);need(!sampler.Capture(actual),"unreadable toolbar rejected without AV");put(m.user.data(),0x478,uintptr_t(m.toolbar.data()));
 need(sampler.Capture(actual),"normal capture restored after diagnostic changes");
 VirtualFree(reinterpret_cast<void*>(bad),0,MEM_RELEASE);VirtualFree(reinterpret_cast<void*>(root),0,MEM_RELEASE);VirtualFree(reinterpret_cast<void*>(base),0,MEM_RELEASE);
 puts("{\"sampler_and_inspector\":true,\"empty_and_allocated_queue\":true,\"stale_identity_rejected\":true,\"unreadable_span_rejected\":true,\"game_access\":false}");return 0;
}
