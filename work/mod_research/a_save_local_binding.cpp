#include "a_save_local_binding.h"
#include <cstring>
namespace a_save_local_binding {
namespace {
bool readable(uintptr_t p,size_t n)noexcept {
 if(p<0x10000||!n||p>UINTPTR_MAX-n)return false;
 const auto end=p+n;
 while(p<end){MEMORY_BASIC_INFORMATION m{};
  if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||(m.Protect&PAGE_GUARD))return false;
  const auto protection=m.Protect&0xff;
  if(protection!=PAGE_READONLY&&protection!=PAGE_READWRITE&&protection!=PAGE_WRITECOPY&&
     protection!=PAGE_EXECUTE_READ&&protection!=PAGE_EXECUTE_READWRITE&&protection!=PAGE_EXECUTE_WRITECOPY)return false;
  const auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;
 }return true;
}
template<class T>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}
bool token(const checkpoint_native_input::Identity&t){for(auto v:t)if(v)return true;return false;}
}
bool Sampler::Initialize(const Config&c)noexcept {
 if(InterlockedCompareExchange(&initialized_,1,0))return false;
 if(!token(c.binding.attempt)||!token(c.binding.attachment)||!c.binding.owner_generation||c.base<0x10000||
    c.base>UINTPTR_MAX-0x2300000||c.root<0x10000||c.root>UINTPTR_MAX-0x85138||!c.world||!c.cache)return false;
 for(auto state:c.states)if(!state)return false;
 c_=c;InterlockedExchange(&initialized_,2);return true;
}
bool Sampler::Capture(pending::Config&out)const noexcept {
 out={};if(InterlockedCompareExchange(const_cast<volatile LONG*>(&initialized_),0,0)!=2)return false;
 __try {
  const auto&c=c_;const auto manager=c.base+0x19E7310;
  if(!readable(c.base+0x1FCA1E0,8)||!readable(c.root+0x85130,8)||!readable(c.base+0x2025318,8)||
     at<uintptr_t>(c.base+0x1FCA1E0)!=c.root||at<uintptr_t>(c.root+0x85130)!=c.world||at<uintptr_t>(c.base+0x2025318)!=c.cache||!readable(manager,0x50))return false;
  const auto count=at<uint64_t>(manager+0x10),capacity=at<uint64_t>(manager+0x18),stack=at<uintptr_t>(manager+0x20);
  const auto qcount=at<uint64_t>(manager+0x30),qcapacity=at<uint64_t>(manager+0x38),queue=at<uintptr_t>(manager+0x40);
  if((count!=5&&count!=6)||capacity<count||capacity<6||capacity>4096||!readable(stack,size_t(capacity)*8)||qcapacity>4096||qcount>qcapacity||bool(queue)!=bool(qcapacity))return false;
  for(unsigned i=0;i<5;++i)if(at<uintptr_t>(stack+i*8)!=c.states[i])return false;
  if(!readable(c.states[4],0x668)||!readable(c.states[2],0x488)||!readable(c.cache,0x3f4))return false;
  const auto toolbar=at<uintptr_t>(c.states[4]+0x478),panel=at<uintptr_t>(c.states[2]+0x480);
  if(!readable(toolbar,0x8c)||!readable(panel,0x1f8)||(queue&&!readable(queue,size_t(qcapacity)*16)))return false;
  auto span=[](uintptr_t p,size_t n){return pending::Span{reinterpret_cast<const unsigned char*>(p),n};};
  pending::Config v{};v.binding=c.binding;v.profile_base=c.base;
  v.user=span(c.states[4],0x668);v.game=span(c.states[2],0x488);v.toolbar=span(toolbar,0x8c);v.panel=span(panel,0x1f8);
  v.manager=span(manager,0x50);v.stack=span(stack,size_t(capacity)*8);v.queue=queue?span(queue,size_t(qcapacity)*16):pending::Span{};v.load_cache=span(c.cache,0x3f4);
  memcpy(v.states,c.states,sizeof v.states);
  // Double reads detect observed churn. They are not a lock against future
  // writes; the caller must consume these spans in its verified native scope.
  if(at<uintptr_t>(c.base+0x1FCA1E0)!=c.root||at<uintptr_t>(c.root+0x85130)!=c.world||at<uintptr_t>(c.base+0x2025318)!=c.cache||
     at<uint64_t>(manager+0x10)!=count||at<uint64_t>(manager+0x18)!=capacity||at<uintptr_t>(manager+0x20)!=stack||
     at<uint64_t>(manager+0x30)!=qcount||at<uint64_t>(manager+0x38)!=qcapacity||at<uintptr_t>(manager+0x40)!=queue||
     at<uintptr_t>(c.states[4]+0x478)!=toolbar||at<uintptr_t>(c.states[2]+0x480)!=panel)return false;
  for(unsigned i=0;i<5;++i)if(at<uintptr_t>(stack+i*8)!=c.states[i])return false;
  out=v;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){out={};return false;}
}
bool Sampler::Sample(void*context,pending::Config&out)noexcept {
 if(!context){out={};return false;}return static_cast<Sampler*>(context)->Capture(out);
}
}
