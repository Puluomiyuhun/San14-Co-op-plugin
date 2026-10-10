#include "a_runtime_reward_source.h"
#include <cstring>
namespace a_runtime_reward_source {
namespace {
template<class T>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}
bool bytes(const unsigned char*p,size_t n){unsigned v=0;for(size_t i=0;i<n;++i)v|=p[i];return v!=0;}
bool binding(const ph::Binding&a,const ph::Binding&b){return a.native.attempt==b.native.attempt&&a.native.attachment==b.native.attachment&&a.native.owner_generation==b.native.owner_generation&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
bool span(uintptr_t p,size_t n,bool writable)noexcept {
 if(p<0x10000||!n||p>UINTPTR_MAX-n)return false;
 for(auto end=p+n;p<end;){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||(m.Protect&PAGE_GUARD))return false;
  auto x=m.Protect&0xff;bool write=x==PAGE_READWRITE||x==PAGE_WRITECOPY||x==PAGE_EXECUTE_READWRITE||x==PAGE_EXECUTE_WRITECOPY;
  if(writable?!write:(!write&&x!=PAGE_READONLY&&x!=PAGE_EXECUTE_READ))return false;
  auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;
 }return true;
}
}
bool SourceProvider::Initialize(const Config&c)noexcept {
 if(InterlockedCompareExchange(&state_,1,0))return false;
 if(c.base<0x10000||c.base>UINTPTR_MAX-0x2300000||c.root<0x10000||c.root>UINTPTR_MAX-0x85138||!c.world||!c.user||!c.sample_input||
 !c.year||c.year>65535||c.month<1||c.month>12||(c.day!=1&&c.day!=11&&c.day!=21)||!c.binding.period||!c.binding.epoch||!c.binding.native.owner_generation||
 !bytes(c.binding.native.attempt.data(),16)||!bytes(c.binding.native.attachment.data(),16)||!bytes(c.binding.room_input_digest.data(),32))return false;
 if(c.actors[0].force==c.actors[1].force||(c.viewer!=c.actors[0].force&&c.viewer!=c.actors[1].force))return false;
 for(const auto&a:c.actors)if(!a.force||a.force>51||!a.ruler||a.ruler>=6000||!a.district||a.district>51)return false;
 c_=c;__try {raw_=at<uintptr_t>(c.base+0x1FCA0A0);}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
 if(!identity())return false;InterlockedExchange(&state_,2);return true;
}
bool SourceProvider::identity()const noexcept {
 __try {
  if(at<uintptr_t>(c_.base+0x1FCA1E0)!=c_.root||at<uintptr_t>(c_.root+0x85130)!=c_.world||
   at<unsigned short>(c_.world+0x34)!=c_.year||at<unsigned char>(c_.world+0x36)!=c_.month||at<unsigned char>(c_.world+0x37)!=c_.day||at<unsigned char>(c_.world+0x3A)!=c_.viewer||
   at<uintptr_t>(c_.user)!=c_.base+0x12CC4A8||at<unsigned>(c_.user+0x470)!=2)return false;
  const auto manager=c_.base+0x19E7310,stack=at<uintptr_t>(manager+0x20);
  if(at<unsigned long long>(manager+0x10)!=5||!stack||at<uintptr_t>(stack+32)!=c_.user||at<unsigned long long>(manager+0x30))return false;
  for(const auto&a:c_.actors){auto force=at<uintptr_t>(c_.root+0xDCA0+a.force*8);if(!force||at<uintptr_t>(force)!=c_.base+0x129FE58||at<unsigned short>(force+0x10)!=a.ruler)return false;auto district=at<uintptr_t>(c_.root+0xDE40+a.district*8);if(!district||at<uintptr_t>(district)!=c_.base+0x129FEC8||at<unsigned char>(district+0x10)!=a.force||at<unsigned short>(district+0x12)!=a.ruler)return false;}
  return raw_&&at<uintptr_t>(c_.base+0x1FCA0A0)==raw_&&span(c_.base+0x1FCA0A0,0x78,true)&&span(c_.base+0x19E1D30,0x68,true)&&span(raw_,0x258,false);
 }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool SourceProvider::Capture(uintptr_t user,unsigned actor,ar::Source&out)noexcept {
 out={};if(InterlockedCompareExchange(&state_,0,0)!=2)return false;
 // Only the trusted serialized Owner callback may consume this provider.
 auto thread=LONG(GetCurrentThreadId());const auto prior=InterlockedCompareExchange(&thread_,thread,0);if(prior&&prior!=thread){InterlockedExchange(&state_,3);return false;}
 const Actor*a=nullptr;for(const auto&v:c_.actors)if(v.force==actor)a=&v;
 if(!a||user!=c_.user||!identity()){InterlockedExchange(&state_,3);return false;}
 __try {
  checkpoint_native_input_pending::Config pending{};
  if(!c_.sample_input(c_.input_context,pending)||pending.profile_base!=c_.base||pending.states[4]!=c_.user||
   pending.binding.attempt!=c_.binding.native.attempt||pending.binding.attachment!=c_.binding.native.attachment||pending.binding.owner_generation!=c_.binding.native.owner_generation){InterlockedExchange(&state_,3);return false;}
  ar::Source value{};value.admission.binding=c_.binding;value.admission.pending=pending;
  value.admission.buffers={{reinterpret_cast<unsigned char*>(c_.base+0x1FCA0A0),0x78},{reinterpret_cast<unsigned char*>(c_.base+0x19E1D30),0x68},{reinterpret_cast<const unsigned char*>(raw_),0x258}};
  value.admission.reward=reinterpret_cast<ph::RewardOriginal>(c_.base+0x1D6DA0);
  value.admission.sortie=reinterpret_cast<ph::SortieOriginal>(c_.base+0x1D1940);
  value.admission.mouse=reinterpret_cast<checkpoint_native_input_consumer::MouseQuery>(c_.base+0x3A2920);
  auto&r=value.reward;r.binding=c_.binding;r.base=c_.base;r.root=c_.root;r.world=c_.world;r.user=c_.user;r.authorized_force=static_cast<unsigned char>(a->force);r.authorized_ruler=static_cast<unsigned short>(a->ruler);
  r.ctor=reinterpret_cast<decltype(r.ctor)>(c_.base+0x22600);r.append=reinterpret_cast<decltype(r.append)>(c_.base+0x171B0);r.dtor=reinterpret_cast<decltype(r.dtor)>(c_.base+0x83E0);r.predicate=reinterpret_cast<decltype(r.predicate)>(c_.base+0x1D4270);
  r.validate_attachment=Validate;r.context=this;
  if(!identity()){InterlockedExchange(&state_,3);return false;}out=value;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){InterlockedExchange(&state_,3);out={};return false;}
}
bool SourceProvider::Validate(void*v,const ph::Binding&b)noexcept {
 if(!v)return false;auto&s=*static_cast<SourceProvider*>(v);
 if(InterlockedCompareExchange(&s.state_,0,0)!=2||LONG(GetCurrentThreadId())!=InterlockedCompareExchange(&s.thread_,0,0)||!binding(b,s.c_.binding)||!s.identity()){InterlockedExchange(&s.state_,3);return false;}return true;
}
bool SourceProvider::Sample(void*v,uintptr_t user,unsigned actor,ar::Source&out)noexcept {out={};return v&&static_cast<SourceProvider*>(v)->Capture(user,actor,out);}
bool SourceProvider::Failed()const noexcept{return InterlockedCompareExchange(const_cast<volatile LONG*>(&state_),0,0)!=2;}
}
