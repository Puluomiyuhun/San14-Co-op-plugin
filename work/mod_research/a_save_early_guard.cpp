#include "a_save_early_guard.h"
#include <cstring>
namespace a_save_early_guard {
namespace {
bool same(const Binding&a,const Binding&b){return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
bool range(uintptr_t p,size_t n,bool code,uintptr_t allocation=0)noexcept{
 if(p<0x10000||!n||p>UINTPTR_MAX-n)return false;const auto end=p+n;
 for(auto at=p;at<end;){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(at),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
   (m.Protect&(PAGE_GUARD|PAGE_NOACCESS))||!(m.Protect&(PAGE_READONLY|PAGE_READWRITE|PAGE_WRITECOPY|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))return false;
  if(code){if(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY)return false;
   if(uintptr_t(m.AllocationBase)!=allocation)return false;
#ifndef A_SAVE_EARLY_FIXTURE
   if(m.Type!=MEM_IMAGE)return false;
#endif
  }
  const auto limit=uintptr_t(m.BaseAddress)+m.RegionSize;if(limit<=at)return false;at=limit<end?limit:end;
 }return true;
}
template<class T>bool read(uintptr_t at,T&out)noexcept{if(!range(at,sizeof(T),false))return false;__try{memcpy(&out,reinterpret_cast<const void*>(at),sizeof out);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
struct View {uintptr_t root=0,world=0,user=0,stack=0,head=0,links[3]{};std::uint64_t count=0,stackCount=0,commands=0;unsigned flag=0,phase=0;unsigned char nil=0;};
bool sameView(const View&a,const View&b)noexcept{
 return a.root==b.root&&a.world==b.world&&a.user==b.user&&a.stack==b.stack&&a.head==b.head&&
  a.links[0]==b.links[0]&&a.links[1]==b.links[1]&&a.links[2]==b.links[2]&&a.count==b.count&&
  a.stackCount==b.stackCount&&a.commands==b.commands&&a.flag==b.flag&&a.phase==b.phase&&a.nil==b.nil;
}
Decision sample(const Config&c,View&v)noexcept{
 uintptr_t rootVt=0,worldVt=0,userVt=0;
 if(!read(c.base+0x1FCA1E0,v.root)||!read(c.root+0x85130,v.world)||!read(c.root,rootVt)||!read(c.world,worldVt)||
    !read(c.base+0x19E7310+0x10,v.stackCount)||!read(c.base+0x19E7310+0x20,v.stack)||!read(c.base+0x19E7310+0x30,v.commands)||
    !read(v.stack+32,v.user)||!read(c.user,userVt)||!read(c.user+0x470,v.phase)||!read(c.user+0x660,v.flag)||
    !read(c.base+0x1FC98B0,v.head)||!read(c.base+0x1FC98B8,v.count))return Decision::Unreadable;
 if(v.root!=c.root||v.world!=c.world||v.user!=c.user||rootVt!=c.base+0x12AA6B0||worldVt!=c.base+0x12AA638||userVt!=c.base+0x12CC4A8)return Decision::Identity;
 if(v.phase!=2||v.stackCount!=5||v.commands)return Decision::Phase;
 if(v.flag)return Decision::PendingUserReport;
 if(v.count)return Decision::PendingReportQueue;
 for(unsigned i=0;i<3;++i)if(!read(v.head+i*8,v.links[i]))return Decision::Unreadable;
 if(!read(v.head+0x19,v.nil))return Decision::Unreadable;
 if(v.links[0]!=v.head||v.links[1]!=v.head||v.links[2]!=v.head||v.nil!=1)return Decision::QueueShape;
 return Decision::QuietReportsObserved;
}
}
bool Guard::sources()const noexcept {__try {
 struct Source {uintptr_t rva;unsigned n;unsigned char bytes[19];};
 // Exact guard/call/clear sequence, world report cursor store, and queue count
 // clear. Compatible with the separately owned action-tail patch at 3F9DAF.
 constexpr Source source[]={
  {0x3F9BA8,19,{0x39,0xae,0x60,0x06,0,0,0x74,0x0b,0xe8,0x0b,0x83,0xea,0xff,0x89,0xae,0x60,0x06,0,0}},
  {0x835C2C,7,{0x66,0x89,0xb9,0x5a,0x16,0,0}},
  {0x2403C2,11,{0x48,0xc7,0x05,0xeb,0x94,0xd8,0x01,0,0,0,0}}};
 for(const auto&s:source)if(!range(c_.base+s.rva,s.n,true,c_.base)||memcmp(reinterpret_cast<const void*>(c_.base+s.rva),s.bytes,s.n))return false;
 return true;
}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool Guard::Initialize(const Config&c)noexcept{
 if(InterlockedCompareExchange(&used_,1,0))return false;unsigned a=0,b=0;for(auto n:c.binding.attempt)a|=n;for(auto n:c.binding.attachment)b|=n;
 if(!c.base||c.base>UINTPTR_MAX-0x2200000||!c.root||!c.world||!c.user||!a||!b||!c.binding.owner_generation||InterlockedCompareExchange(&retired_,0,0))return false;
 c_=c;if(!sources())return false;InterlockedExchange(&initialized_,1);return true;
}
Report Guard::Observe(const Binding&binding)noexcept{
 Report r{};if(!InterlockedCompareExchange(&initialized_,0,0))return r;
 if(InterlockedCompareExchange(&retired_,0,0)){r.decision=Decision::Retired;return r;}
 if(!same(binding,c_.binding)){r.decision=Decision::Binding;return r;}
 if(!sources()){r.decision=Decision::Source;return r;}r.sourceChecked=true;
 View first{},second{};r.decision=sample(c_,first);r.userFlag=first.flag;r.queuedReports=first.count;
 if(r.decision!=Decision::QuietReportsObserved)return r;
#ifdef A_SAVE_EARLY_FIXTURE
 if(c_.betweenSamples)c_.betweenSamples(c_.context);
#endif
 const auto next=sample(c_,second);
 if(next!=Decision::QuietReportsObserved||!sameView(first,second)){r.decision=Decision::Drift;return r;}
 if(InterlockedCompareExchange(&retired_,0,0)){r.decision=Decision::Retired;return r;}
 if(!sources()){r.decision=Decision::Source;return r;}
 r.twoSamplesEqual=true;return r;
}
void Guard::Retire()noexcept{InterlockedExchange(&retired_,1);}
}
