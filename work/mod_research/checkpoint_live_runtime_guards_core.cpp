#include "checkpoint_live_runtime_guards_core.h"
#include "checkpoint_live_runtime_guards_profile.h"
#include <cstring>
#include <cwchar>
#include <limits>
namespace checkpoint_live_runtime_guards {
namespace profile=checkpoint_live_runtime_guards_profile;
namespace {
template<class T>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
LONG get(volatile LONG&v){return InterlockedCompareExchange(&v,0,0);}
bool readable(uintptr_t p,size_t n){
 if(!p||!n||p>(std::numeric_limits<uintptr_t>::max)()-n)return false;
 const auto end=p+n;while(p<end){MEMORY_BASIC_INFORMATION m{};
  if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||m.Protect&(PAGE_NOACCESS|PAGE_GUARD)||
   !(m.Protect&(PAGE_READONLY|PAGE_READWRITE|PAGE_WRITECOPY|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))return false;
  auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next;}return true;
}
bool imageAddress(uintptr_t p,uintptr_t base,bool executable){MEMORY_BASIC_INFORMATION m{};
 return VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&m.Type==MEM_IMAGE&&uintptr_t(m.AllocationBase)==base&&
  !(m.Protect&(PAGE_NOACCESS|PAGE_GUARD))&&(!executable||m.Protect&(PAGE_EXECUTE_READ|PAGE_EXECUTE_WRITECOPY|PAGE_EXECUTE_READWRITE));}
std::uint64_t birth(){FILETIME b{},e{},k{},u{};return GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u)?(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime:0;}
bool name(uintptr_t p,const char*s){auto n=strlen(s)+1;return readable(p+0x70,n)&&!memcmp(reinterpret_cast<void*>(p+0x70),s,n);}
bool sso(uintptr_t p,const char*s){if(!readable(p,32))return false;auto n=at<std::uint64_t>(p+16),cap=at<std::uint64_t>(p+24),len=strlen(s);if(n!=len||n>cap||cap>32768||(cap<16&&cap!=15))return false;auto data=cap>=16?at<uintptr_t>(p):p;return readable(data,len+1)&&!memcmp(reinterpret_cast<void*>(data),s,len+1);}
bool path(wchar_t(&out)[512],const wchar_t*in){if(!in)return false;for(unsigned i=0;i<512;++i){out[i]=in[i];if(!out[i])return i>3&&out[1]==L':'&&(out[2]==L'\\'||out[2]==L'/')&&!wcsstr(out,L"..");}return false;}
unsigned index(unsigned f,unsigned p){const unsigned offsets[]={0,6,13,18,21,27};return offsets[f]+p;}
}
bool Context::fail(Error e,DWORD exception)noexcept{AcquireSRWLockExclusive(&lock_);if(report_.first_error==Error::None)report_.first_error=e;report_.last_error=e;++report_.failures;if(exception)report_.exception=exception;ReleaseSRWLockExclusive(&lock_);return false;}
bool Context::Initialize(const Config&c)noexcept{
 if(InterlockedCompareExchange(&initialized_,1,0))return false;
 __try{
  config_=c;expected_=c.expected;unsigned owner=0;for(auto x:c.expected.owner_binding)owner|=x;
  if(!c.base||!c.pid||!c.birth||!c.owner_module||!c.current_stamp||!c.expected.attempt||!c.expected.epoch||!owner||
   !c.queue||!c.storage_valid||c.initial.base!=c.base||c.initial.attempt!=c.expected.attempt||c.initial.menu||
   !c.initial.root||!c.initial.world||!c.initial.cache||!c.initial.keyboard||
   c.initial.year!=203||c.initial.month!=8||c.initial.day!=11||c.initial.force!=12||
   memcmp(c.supported_image_sha256,profile::image_sha,32)||memcmp(c.expected.checkpoint_sha256,profile::checkpoint_sha,32)||
   !path(request_intent_,c.request_intent)||!path(identity_intent_,c.identity_intent)||!_wcsicmp(request_intent_,identity_intent_))return fail(Error::Config);
  for(auto s:c.initial.states)if(!s)return fail(Error::Config);
  for(unsigned i=0;i<6;++i)if(!c.hooks[i].slot||!c.hooks[i].original||!c.hooks[i].hook||c.hooks[i].original==c.hooks[i].hook)return fail(Error::Config);
  config_.request_intent=request_intent_;config_.identity_intent=identity_intent_;
  if(!stamp())return fail(Error::Attachment);
  AcquireSRWLockExclusive(&lock_);report_.initialized=1;ReleaseSRWLockExclusive(&lock_);InterlockedExchange(&initialized_,2);return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Context::Snapshot(Report&r)const noexcept{AcquireSRWLockShared(&lock_);r=report_;ReleaseSRWLockShared(&lock_);return get(initialized_)==2;}
bool Context::stamp()const{
 if(config_.pid!=GetCurrentProcessId()||config_.birth!=birth()||!readable(uintptr_t(config_.current_stamp),sizeof(Stamp)))return false;
 const Stamp a=*config_.current_stamp,b=*config_.current_stamp;
 return !memcmp(&a,&expected_,sizeof a)&&!memcmp(&a,&b,sizeof a);
}
bool Context::image()const{
 auto b=config_.base;
 if(b>(std::numeric_limits<uintptr_t>::max)()-0x2200000)return false;
 HMODULE owner=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
  reinterpret_cast<LPCWSTR>(&Context::SessionGuard),&owner)||uintptr_t(owner)!=config_.owner_module)return false;
#ifndef CHECKPOINT_LIVE_RUNTIME_GUARDS_FIXTURE
 if(b!=uintptr_t(GetModuleHandleW(nullptr))||!imageAddress(b,b,false)||!readable(b,4096)||at<WORD>(b)!=IMAGE_DOS_SIGNATURE)return false;
 auto off=at<LONG>(b+0x3c);if(off<0||off>0x1000||!readable(b+off,sizeof(IMAGE_NT_HEADERS64)))return false;
 const auto&pe=*reinterpret_cast<const IMAGE_NT_HEADERS64*>(b+off);
 if(pe.Signature!=IMAGE_NT_SIGNATURE||pe.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||pe.OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC||pe.OptionalHeader.SizeOfImage<=0x2025710)return false;
#endif
 for(const auto&a:CheckpointLiveSessionAnchors)if(!readable(b+a.rva,a.size)||memcmp(reinterpret_cast<void*>(b+a.rva),a.bytes,a.size))return false;
 for(const auto&a:CheckpointNativeQueueAnchors)if(!readable(b+a.rva,a.size)||memcmp(reinterpret_cast<void*>(b+a.rva),a.bytes,a.size))return false;
 return true;
}
bool Context::slots(Slots mode)const{
 for(unsigned i=0;i<6;++i){const auto&h=config_.hooks[i];const auto address=uintptr_t(h.slot);
  if(!readable(address,8))return false;
#ifndef CHECKPOINT_LIVE_RUNTIME_GUARDS_FIXTURE
  if(i<5&&(address!=config_.base+profile::slots[i]||uintptr_t(h.original)!=config_.base+profile::originals[i]))return false;
  if(!imageAddress(uintptr_t(h.hook),config_.owner_module,true)||
   (i<5&&(!imageAddress(address,config_.base,false)||!imageAddress(uintptr_t(h.original),config_.base,true))))return false;
#endif
  const auto value=*h.slot;
  if(mode==Slots::Original?value!=h.original:mode==Slots::Owned?value!=h.hook:(value!=h.original&&value!=h.hook))return false;
 }return true;
}
bool Context::common(Slots mode,bool storage)noexcept{
 __try{
  if(get(initialized_)!=2)return fail(Error::Config);
  if(!stamp())return fail(Error::Attachment);
  if(!image())return fail(Error::Image);
  if(!slots(mode))return fail(Error::Hook);
  // No report lock is held around external validation; that thunk serializes
  // only the short storage.Valid call and rejects same-thread recursion.
  if(storage&&!config_.storage_valid(config_.storage_context))return fail(Error::Storage);
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
}
bool Context::initialGraph(unsigned count,uintptr_t current,LONG pending,bool rng)const{
 const auto&c=config_.initial;auto b=config_.base,m=b+0x19e7310;
 if(!readable(m,0x50)||at<std::uint64_t>(m+0x10)!=count||at<std::uint64_t>(m+0x30))return false;
 auto stack=at<uintptr_t>(m+0x20);if(!readable(stack,count*8)||(current&&at<uintptr_t>(m+0x48)!=current))return false;
 uintptr_t menu=0;{AcquireSRWLockShared(&lock_);menu=report_.menu;ReleaseSRWLockShared(&lock_);}
 const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState","CSaveLoadState"};
 for(unsigned i=0;i<count;++i){auto s=i<5?c.states[i]:menu;if(!s||at<uintptr_t>(stack+8*i)!=s||!readable(s,0x90)||!name(s,names[i])||at<DWORD>(s+0x68))return false;}
 if(!readable(c.root,0x85138)||!readable(c.world,0x44)||!readable(c.cache,0x3f4)||
  at<uintptr_t>(b+0x1fca1e0)!=c.root||at<uintptr_t>(c.root+0x85130)!=c.world||at<uintptr_t>(b+0x2025318)!=c.cache||
  at<uintptr_t>(c.root)!=b+0x12aa6b0||at<uintptr_t>(c.world)!=b+0x12aa638||at<WORD>(c.world+0x34)!=c.year||
  at<BYTE>(c.world+0x36)!=c.month||at<BYTE>(c.world+0x37)!=c.day||at<BYTE>(c.world+0x3a)!=12||at<DWORD>(c.world+0x40)!=1||
  at<DWORD>(c.cache+8)!=0||at<DWORD>(c.cache+0x3f0)||at<LONG>(c.cache+0x3ec)!=pending)return false;
 return !rng||at<DWORD>(b+0x18eb8b0)==c.expectedRng;
}
bool Context::queuedMenu(){
 qa::Report q{};if(!config_.queue->Snapshot(q)||q.error!=qa::Error::None||q.stage!=qa::Stage::Resolved||!q.authorized||
  q.native_calls!=1||q.native_returned!=1||q.native_result_verified!=1||q.resolver_calls!=1||q.thread!=GetCurrentThreadId()||!q.call_id||!q.menu)return fail(Error::Queue);
 auto b=config_.base,m=b+0x19e7310;if(!readable(m,0x50)||at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30)!=1||
  at<uintptr_t>(m+0x48)!=config_.initial.states[4]||at<uintptr_t>(m+0x40)!=q.queue||!readable(q.queue,16)||
  at<DWORD>(q.queue)||at<uintptr_t>(q.queue+8)!=q.menu||!readable(q.menu,0x4c0)||at<uintptr_t>(q.menu)!=b+0x12db4c0||!name(q.menu,"CSaveLoadState"))return fail(Error::Queue);
 auto stack=at<uintptr_t>(m+0x20);if(!readable(stack,40))return fail(Error::Memory);
 for(unsigned i=0;i<5;++i)if(at<uintptr_t>(stack+i*8)!=config_.initial.states[i])return fail(Error::Lifetime);
 AcquireSRWLockExclusive(&lock_);bool same=!report_.menu||report_.menu==q.menu;if(same)report_.menu=q.menu;ReleaseSRWLockExclusive(&lock_);
 return same||fail(Error::Lifetime);
}
bool Context::loadGraph(uintptr_t load,uintptr_t title,bool current,bool allowCleared){
 Report prior{};Snapshot(prior);if(prior.load_retired)return fail(Error::Retired);
 auto b=config_.base,m=b+0x19e7310;if(!load||!title||(prior.load&&(load!=prior.load||title!=prior.title)))return fail(Error::Lifetime);
 if(!readable(load,0x4e0)||!readable(title,0x580)||at<uintptr_t>(load)!=b+0x12dbd68||!name(load,"CLoadState")||
  at<uintptr_t>(title)!=b+0x12daaf0||!name(title,"CTitleState")||at<LONG>(title+0x47c)!=63)return fail(Error::Lifetime);
 auto closure=at<uintptr_t>(load+0x48);if(!readable(closure,16)||at<uintptr_t>(closure)!=b+0x12ea4d0||at<uintptr_t>(closure+8)!=title||at<uintptr_t>(b+0x12ea4d0+0x10)!=b+0x4fac30)return fail(Error::Lifetime);
 auto phase=at<DWORD>(load+0x470);if(phase<1||phase>4)return fail(Error::Phase);
 if(!readable(m,0x50)||at<std::uint64_t>(m+0x10)!=4||(current&&at<uintptr_t>(m+0x48)!=load))return fail(Error::Phase);
 auto stack=at<uintptr_t>(m+0x20);if(!readable(stack,32)||at<uintptr_t>(stack)!=config_.initial.states[0]||at<uintptr_t>(stack+8)!=config_.initial.states[1]||at<uintptr_t>(stack+16)!=title||at<uintptr_t>(stack+24)!=load)return fail(Error::Lifetime);
 auto slot=at<LONG>(b+0x201ecd0);if(slot==63){if(!sso(b+0x201ece0,by::TargetName))return fail(Error::Pending);}
 else if(!allowCleared||slot!=-1||!sso(b+0x201ece0,""))return fail(Error::Pending);
 AcquireSRWLockExclusive(&lock_);report_.load=load;report_.title=title;ReleaseSRWLockExclusive(&lock_);return true;
}
bool Context::titleGraph(uintptr_t title,uintptr_t root,uintptr_t world,bool after,bool targetPair){
 Report r{};Snapshot(r);auto b=config_.base,m=b+0x19e7310;
 if(!r.load_completed||title!=r.title||!readable(title,0x580)||!readable(root,0x85138)||!readable(world,0x20ac)||
  at<uintptr_t>(b+0x1fca1e0)!=root||at<uintptr_t>(root+0x85130)!=world||at<uintptr_t>(root)!=b+0x12aa6b0||at<uintptr_t>(world)!=b+0x12aa638||
  at<uintptr_t>(title)!=b+0x12daaf0||!name(title,"CTitleState")||at<LONG>(title+0x47c)!=63)return fail(Error::Lifetime);
 auto n=at<std::uint64_t>(m+0x10),stack=at<uintptr_t>(m+0x20);if((n!=3&&n!=4)||!readable(stack,size_t(n)*8)||
  at<uintptr_t>(stack)!=config_.initial.states[0]||at<uintptr_t>(stack+8)!=config_.initial.states[1]||at<uintptr_t>(stack+16)!=title||
  (n==4&&at<uintptr_t>(stack+24)!=r.load))return fail(Error::Lifetime); // historical Load address only
 auto phase=at<DWORD>(title+0x470);if((phase!=13&&phase!=15)||(n==3&&phase!=15))return fail(Error::Phase);
 if(at<WORD>(world+0x34)!=203||at<BYTE>(world+0x36)!=8||at<BYTE>(world+0x37)!=11||at<BYTE>(world+0x3a)!=(after?2:12)||at<BYTE>(world+0x165d)!=(after?1:2))return fail(Error::Phase);
 const unsigned force=targetPair?2:12,person=targetPair?952:666;
 if(at<uintptr_t>(title+0x4a0)!=at<uintptr_t>(root+0xdca0+force*8)||at<uintptr_t>(title+0x4a8)!=at<uintptr_t>(root+0x148+person*8))return fail(Error::Phase);
 AcquireSRWLockExclusive(&lock_);report_.load_retired=1;if(after)report_.identity_returned=1;ReleaseSRWLockExclusive(&lock_);return true;
}
bool Context::planningGraph()const{
 Report r{};Snapshot(r);if(!r.identity_returned)return false;
 auto b=config_.base,m=b+0x19e7310;if(!readable(m,0x50)||at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30))return false;
 auto stack=at<uintptr_t>(m+0x20);if(!readable(stack,40)||at<uintptr_t>(stack)!=config_.initial.states[0]||at<uintptr_t>(stack+8)!=config_.initial.states[1])return false;
 const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
 for(unsigned i=0;i<5;++i){auto state=at<uintptr_t>(stack+i*8);if(!state||state==r.load||state==r.title||!readable(state,0x90)||!name(state,names[i]))return false;}
 auto user=at<uintptr_t>(stack+32),root=at<uintptr_t>(b+0x1fca1e0);if(!readable(user,0x668)||!readable(root,0x85138)||at<uintptr_t>(m+0x48)!=user||at<uintptr_t>(user)!=b+0x12cc4a8||at<DWORD>(user+0x470)!=2)return false;
 auto world=at<uintptr_t>(root+0x85130);if(!readable(world,0x1660)||at<BYTE>(world+0x3a)!=2||at<BYTE>(world+0x165d)!=1)return false;
 auto cache=at<uintptr_t>(b+0x2025318);return readable(cache,0x3f4)&&at<LONG>(cache+0x3ec)==-1&&!at<DWORD>(cache+0x3f0);
}
bool Context::body(unsigned f,unsigned p,uintptr_t a,uintptr_t b,uintptr_t c){
 if(f==0){ // Session
  if(p==0||p==1)return common(Slots::Original,true)&&(initialGraph(5,0,-1,true)||fail(Error::Lifetime));
  if(p==5)return common(Slots::Either,false); // cleanup must not dereference retired game objects
  if(!common(Slots::Owned,true))return false;
  if(p==2)return queuedMenu();
  if(p==3){ // MenuReceipt and GameBefore both map here.
   auto m=config_.base+0x19e7310;Report r{};Snapshot(r);auto current=at<uintptr_t>(m+0x48);
   return (current==r.menu||current==config_.initial.states[2])&&(initialGraph(6,current,-1,true)||fail(Error::Lifetime));
  }
  return initialGraph(6,config_.initial.states[2],63,true)||fail(Error::Pending);
 }
 if(f==1){if(!common(Slots::Owned,true))return false;Report r{};Snapshot(r);
  return initialGraph(6,p==0?r.menu:config_.initial.states[2],p==6?63:-1,true)||fail(Error::Pending);}
 if(f==2||f==3){if(!common(Slots::Owned,true))return false;
  const bool liveUpdate=f==3;const bool allowCleared=f==3&&p==2;
  if(!loadGraph(a,b,liveUpdate,allowCleared))return false;
  if((f==3&&p==0)||(f==2&&p==0)){if(at<DWORD>(a+0x470)!=1)return fail(Error::Phase);}
  if(f==3&&p==2&&at<DWORD>(a+0x470)==4&&at<DWORD>(a+8)==0x7ffffffd&&at<LONG>(config_.base+0x201ecd0)==-1){
   auto m=config_.base+0x19e7310,q=at<uintptr_t>(m+0x40);if(at<std::uint64_t>(m+0x30)!=1||!readable(q,16)||at<DWORD>(q)!=1||at<uintptr_t>(q+8))return fail(Error::Pending);
   AcquireSRWLockExclusive(&lock_);report_.load_completed=1;ReleaseSRWLockExclusive(&lock_);
  }return true;
 }
 if(f==4)return common(Slots::Owned,true)&&titleGraph(a,b,c,p==5,p>=4);
 if(f==5){if(a!=expected_.attempt||b!=expected_.epoch)return fail(Error::Attachment);return common(Slots::Owned,true)&&(planningGraph()||fail(Error::Lifetime));}
 return fail(Error::Config);
}
bool Context::check(unsigned f,unsigned p,uintptr_t a,uintptr_t b,uintptr_t c)noexcept{
 const unsigned counts[]={6,7,5,3,6,2};if(f>=6||p>=counts[f])return fail(Error::Config);auto i=index(f,p);
 AcquireSRWLockExclusive(&lock_);++report_.calls[i];ReleaseSRWLockExclusive(&lock_);
 bool ok=false;__try{ok=body(f,p,a,b,c);}__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Memory,GetExceptionCode());}
 if(ok){AcquireSRWLockExclusive(&lock_);++report_.accepted[i];ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Context::SessionGuard(void*c,ns::Point p)noexcept{return c&&static_cast<Context*>(c)->check(0,unsigned(p));}
bool Context::RequestGuard(void*c,rq::Point p)noexcept{return c&&static_cast<Context*>(c)->check(1,unsigned(p));}
bool Context::BytesGuard(void*c,by::Point p,uintptr_t l,uintptr_t t)noexcept{return c&&static_cast<Context*>(c)->check(2,unsigned(p)-1,l,t);}
bool Context::LifecycleGuard(void*c,lc::Point p,uintptr_t l,uintptr_t t)noexcept{return c&&static_cast<Context*>(c)->check(3,unsigned(p)-1,l,t);}
bool Context::IdentityGuard(void*c,ti::Point p,uintptr_t t,uintptr_t r,uintptr_t w)noexcept{return c&&static_cast<Context*>(c)->check(4,unsigned(p)-1,t,r,w);}
bool Context::PlanningGuard(void*c,pr::Point p,std::uint64_t a,std::uint64_t e)noexcept{return c&&static_cast<Context*>(c)->check(5,unsigned(p)-1,uintptr_t(a),uintptr_t(e));}
bool Context::AttachmentOnly(void*c)noexcept{return c&&static_cast<Context*>(c)->common(Slots::Either,false);}
bool Context::OwnedReadBridgeOnly(void*c)noexcept{return c&&static_cast<Context*>(c)->common(Slots::Either,false);}
bool Context::QueueGuard(void*c,qa::Point p)noexcept{
 if(!c||unsigned(p)>4)return false;auto&s=*static_cast<Context*>(c);AcquireSRWLockExclusive(&s.lock_);++s.report_.queue_calls[unsigned(p)];ReleaseSRWLockExclusive(&s.lock_);
 __try{
  if(!s.common(p==qa::Point::Initialize?Slots::Either:Slots::Owned,true))return false;
  if(p==qa::Point::Initialize)return s.initialGraph(5,0,-1,true)||s.fail(Error::Lifetime);
  if(p==qa::Point::Authorize||p==qa::Point::BeforeNative)return s.initialGraph(5,s.config_.initial.states[4],-1,true)||s.fail(Error::Lifetime);
  // The adapter itself checks actual returned vector/menu fields before/after
  // this callback. No recursion into Adapter::Snapshot or its validators.
  auto b=s.config_.base,m=b+0x19e7310,cache=s.config_.initial.cache;
  return at<std::uint64_t>(m+0x10)==5&&at<std::uint64_t>(m+0x30)==1&&at<uintptr_t>(m+0x48)==s.config_.initial.states[4]&&
   at<uintptr_t>(b+0x2025318)==cache&&at<LONG>(cache+0x3ec)==-1&&at<DWORD>(cache+8)==0&&!at<DWORD>(cache+0x3f0);
 }__except(EXCEPTION_EXECUTE_HANDLER){return s.fail(Error::Memory,GetExceptionCode());}
}
}

