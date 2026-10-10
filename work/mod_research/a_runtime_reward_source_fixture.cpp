// Own memory only; no SAN14 discovery. Native function pointers are inspected,
// never invoked by this source-builder test.
#define main old_pending_fixture_main
#include "checkpoint_native_input_pending_empty_queue_fixture.cpp"
#undef main
#include "a_runtime_reward_source.h"
#include "a_save_local_binding.h"
#include <thread>
namespace rs=a_runtime_reward_source;
struct Fixture {
 Memory m;uintptr_t base=0,root=0;std::array<unsigned char,0x258>raw{};
 std::array<unsigned char,0x80>forces[2]{},districts[2]{};
 a_save_local_binding::Sampler sampler;rs::Config config{};
 Fixture(){
  base=uintptr_t(VirtualAlloc(nullptr,0x2300000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));root=uintptr_t(VirtualAlloc(nullptr,0x86000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(base&&root,"owned allocation");
  put(m.user.data(),0,base+0x12CC4A8);put(m.game.data(),0,base+0x12CC9B8);put<uint64_t>(m.manager.data(),0x18,6);memcpy(reinterpret_cast<void*>(base+0x19E7310),m.manager.data(),m.manager.size());
  put(reinterpret_cast<void*>(base),0x1FCA1E0,root);put(reinterpret_cast<void*>(root),0x85130,uintptr_t(m.cache.data()));put(reinterpret_cast<void*>(base),0x2025318,uintptr_t(m.cache.data()));put(reinterpret_cast<void*>(base),0x1FCA0A0,uintptr_t(raw.data()));
  put<unsigned short>(m.cache.data(),0x34,203);put<unsigned char>(m.cache.data(),0x36,8);put<unsigned char>(m.cache.data(),0x37,11);put<unsigned char>(m.cache.data(),0x3A,12);
  config.base=base;config.root=root;config.world=uintptr_t(m.cache.data());config.user=uintptr_t(m.user.data());config.year=203;config.month=8;config.day=11;config.viewer=12;
  config.actors[0]={12,666,11};config.actors[1]={2,952,2};config.binding.native=m.c.binding;config.binding.period=1;config.binding.epoch=8;config.binding.room_input_digest[0]=7;
  for(unsigned i=0;i<2;++i){auto a=config.actors[i];put(reinterpret_cast<void*>(root),0xDCA0+a.force*8,uintptr_t(forces[i].data()));put(forces[i].data(),0,base+0x129FE58);put<unsigned short>(forces[i].data(),0x10,static_cast<unsigned short>(a.ruler));
   put(reinterpret_cast<void*>(root),0xDE40+a.district*8,uintptr_t(districts[i].data()));put(districts[i].data(),0,base+0x129FEC8);put<unsigned char>(districts[i].data(),0x10,static_cast<unsigned char>(a.force));put<unsigned short>(districts[i].data(),0x12,static_cast<unsigned short>(a.ruler));}
  a_save_local_binding::Config c{};c.base=base;c.root=root;c.world=config.world;c.cache=config.world;c.binding=m.c.binding;memcpy(c.states,m.c.states,sizeof c.states);need(sampler.Initialize(c),"actual pending source initialized");config.sample_input=a_save_local_binding::Sampler::Sample;config.input_context=&sampler;
 }
 ~Fixture(){VirtualFree(reinterpret_cast<void*>(root),0,MEM_RELEASE);VirtualFree(reinterpret_cast<void*>(base),0,MEM_RELEASE);}
};
int main(){
 unsigned checks=0;
 {Fixture f;rs::SourceProvider source;need(source.Initialize(f.config)&&!source.Initialize(f.config),"immutable provider");a_reward_save_owner::Source out{};
  for(unsigned force:{12u,2u}){need(source.Capture(f.config.user,force,out),"both authorized actors");need(out.reward.authorized_force==force&&out.reward.authorized_ruler==(force==12?666:952),"actor ruler is local binding");
   need(uintptr_t(out.reward.ctor)==f.base+0x22600&&uintptr_t(out.reward.append)==f.base+0x171B0&&uintptr_t(out.reward.dtor)==f.base+0x83E0&&uintptr_t(out.reward.predicate)==f.base+0x1D4270,"fixed native entries");
   need(uintptr_t(out.admission.reward)==f.base+0x1D6DA0&&uintptr_t(out.admission.sortie)==f.base+0x1D1940&&uintptr_t(out.admission.mouse)==f.base+0x3A2920,"fixed admission entries");
   p::Adapter pending;need(pending.Bind(out.admission.pending)==p::Error::None&&pending.InspectCurrent(out.admission.pending.binding).decision==p::Decision::QuiescentObserved,"real pending inspector");
   checkpoint_native_input::Adapter neutral;need(neutral.Bind(out.admission.binding.native,out.admission.buffers)==checkpoint_native_input::Status::Ok,"real input buffer layout");
   need(out.reward.validate_attachment(out.reward.context,out.reward.binding),"owned attachment validation");checks+=7;
  }
  auto changed=out.reward.binding;++changed.epoch;need(!out.reward.validate_attachment(out.reward.context,changed)&&source.Failed(),"mismatched binding terminal");need(!source.Capture(f.config.user,12,out)&&!out.reward.ctor,"no replay after fault");checks+=3;
 }
 for(unsigned fault=0;fault<6;++fault){Fixture f;rs::SourceProvider source;need(source.Initialize(f.config),"valid start");a_reward_save_owner::Source out{};need(source.Capture(f.config.user,12,out),"initial capture");
  if(fault==0)put<unsigned char>(f.m.cache.data(),0x37,21);
  if(fault==1)put(reinterpret_cast<void*>(f.root),0x85130,f.config.world+8);
  if(fault==2)put<unsigned short>(f.forces[1].data(),0x10,951);
  if(fault==3)put<unsigned char>(f.districts[1].data(),0x10,3);
  if(fault==4)put(reinterpret_cast<void*>(f.base),0x1FCA0A0,uintptr_t(f.raw.data()+8));
  bool captured=false;if(fault==5){std::thread t([&]{captured=source.Capture(f.config.user,12,out);});t.join();}else captured=source.Capture(f.config.user,12,out);
  need(!captured&&source.Failed()&&!out.reward.ctor,"drift clears source and permanently retires");checks+=3;
 }
 {Fixture f;rs::SourceProvider source;need(source.Initialize(f.config),"valid unauthorized test");a_reward_save_owner::Source out{};need(!source.Capture(f.config.user,3,out)&&source.Failed(),"third force denied");checks+=2;}
 {Fixture f;DWORD old=0;need(VirtualProtect(reinterpret_cast<void*>(f.base+0x1FCA000),0x1000,PAGE_READONLY,&old)!=FALSE,"readonly input page");rs::SourceProvider source;need(!source.Initialize(f.config),"read-only mutable cache refused");checks+=2;}
 printf("{\"result\":\"PASS\",\"checks\":%u,\"actual_pending_sampler\":true,\"native_functions_called\":false,\"game_access\":false}\n",checks);return 0;
}
