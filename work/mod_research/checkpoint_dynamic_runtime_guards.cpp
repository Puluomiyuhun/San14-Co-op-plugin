#include "checkpoint_dynamic_runtime_guards.h"
#include "checkpoint_live_runtime_guards_profile.h"
#include <cstring>
#include <cwchar>
#include <limits>
namespace checkpoint_dynamic_runtime_guards {
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
bool dateValid(unsigned y,unsigned m,unsigned d){return y&&y<=65535&&m>=1&&m<=12&&(d==1||d==11||d==21);}
bool identityValid(const ti::Identity&i){return i.force&&i.force<52&&i.district&&i.district<52&&i.ruler&&i.ruler<6000;}
bool worldValid(const ti::WorldProfile&w){return dateValid(w.year,w.month,w.day)&&identityValid(w.source)&&identityValid(w.target)&&w.source.force!=w.target.force&&w.source.ruler!=w.target.ruler&&w.source.district!=w.target.district;}
unsigned index(unsigned f,unsigned p){const unsigned offsets[]={0,6,13,18,21,27};return offsets[f]+p;}
}
bool Context::fail(Error e,DWORD exception)noexcept{AcquireSRWLockExclusive(&lock_);if(report_.first_error==Error::None)report_.first_error=e;report_.last_error=e;++report_.failures;if(exception)report_.exception=exception;ReleaseSRWLockExclusive(&lock_);return false;}
bool Context::Initialize(const Config&c)noexcept{
 if(InterlockedCompareExchange(&initialized_,1,0))return false;
 __try{
  config_=c;expected_=c.expected;unsigned owner=0;for(auto x:c.expected.owner_binding)owner|=x;
  if(!c.base||!c.pid||!c.birth||!c.owner_module||!c.current_stamp||!c.expected.attempt||!c.expected.epoch||!c.expected.generation||!owner||
   !c.queue||!c.storage_valid||c.initial.base!=c.base||c.initial.attempt!=c.expected.attempt||c.initial.menu||
   !c.initial.root||!c.initial.world||!c.initial.cache||!c.initial.keyboard||
   !dateValid(c.initial.year,c.initial.month,c.initial.day)||!identityValid(c.initialIdentity)||c.initial.force!=c.initialIdentity.force||
   !worldValid(c.worldProfile)||!fp::Validate(c.fileProfile)||
   memcmp(c.supported_image_sha256,profile::image_sha,32)||memcmp(c.expected.checkpoint_sha256,c.fileProfile.sha256,32)||
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
#ifndef CHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE
 if(b!=uintptr_t(GetModuleHandleW(nullptr))||!imageAddress(b,b,false)||!readable(b,4096)||at<WORD>(b)!=IMAGE_DOS_SIGNATURE)return false;
 auto off=at<LONG>(b+0x3c);if(off<0||off>0x1000||!readable(b+off,sizeof(IMAGE_NT_HEADERS64)))return false;
 const auto&pe=*reinterpret_cast<const IMAGE_NT_HEADERS64*>(b+off);
 if(pe.Signature!=IMAGE_NT_SIGNATURE||pe.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||pe.OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR64_MAGIC||pe.OptionalHeader.SizeOfImage<=0x2025710)return false;
#endif
 for(const auto&a:CheckpointLiveSessionAnchors)if(!readable(b+a.rva,a.size)||memcmp(reinterpret_cast<void*>(b+a.rva),a.bytes,a.size))return false;
 for(const auto&a:CheckpointNativeQueueAnchors)if(!readable(b+a.rva,a.size)||memcmp(reinterpret_cast<void*>(b+a.rva),a.bytes,a.size))return false;
 return true;
}
bool Context::slots(Slots)const{
 const uintptr_t entries[]={uintptr_t(&CheckpointPersistentBridge0),uintptr_t(&CheckpointPersistentBridge1),uintptr_t(&CheckpointPersistentBridge2),uintptr_t(&CheckpointPersistentBridge3),uintptr_t(&CheckpointPersistentBridge4),uintptr_t(&CheckpointPersistentBridge5)};
 for(unsigned i=0;i<6;++i){const auto&h=config_.hooks[i];const auto address=uintptr_t(h.slot);
  if(!readable(address,8)||uintptr_t(h.hook)!=entries[i])return false;
  CheckpointPersistentBridgeStats state{};
  if(!CheckpointPersistentBridgeSnapshot(i,&state)||state.configured!=1||state.module_pinned!=1)return false;
#ifndef CHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE
  if(i<5&&(address!=config_.base+profile::slots[i]||uintptr_t(h.original)!=config_.base+profile::originals[i]))return false;
  if(!imageAddress(uintptr_t(h.hook),config_.owner_module,true)||
   (i<5&&(!imageAddress(address,config_.base,false)||!imageAddress(uintptr_t(h.original),config_.base,true))))return false;
#endif
  const auto value=*h.slot;
  if(value!=h.hook)return false;
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

bool Context::identity(uintptr_t root,const ti::Identity&i)const{
 if(!identityValid(i)||!readable(root,0xe000))return false;auto b=config_.base;
 auto force=at<uintptr_t>(root+0xdca0+i.force*8),person=at<uintptr_t>(root+0x148+i.ruler*8),district=at<uintptr_t>(root+0xde40+i.district*8);
 return readable(force,0x48)&&readable(person,0x119)&&readable(district,0x14)&&
  at<uintptr_t>(force)==b+0x129fe58&&at<WORD>(force+0x10)==i.ruler&&
  at<uintptr_t>(person)==b+0x12a00d0&&at<WORD>(person+0x10)==i.ruler&&at<BYTE>(person+0x118)==i.district&&
  at<uintptr_t>(district)==b+0x129fec8&&at<BYTE>(district+0x10)==i.force&&at<BYTE>(district+0x11)&&at<WORD>(district+0x12)==i.ruler;
}
bool Context::mapping(unsigned physical,unsigned stage,uintptr_t self,const void*exactFrame)const{
 namespace la=checkpoint_persistent_logical_adapter;la::Mapping m{};
 if(!la::CurrentMapping(&m)||physical>=6||m.generation!=expected_.generation||m.physicalSlot!=physical||m.logicalSlot!=(physical<4?physical:physical-4)||
  m.thread!=GetCurrentThreadId()||m.stage!=stage||!m.call||!m.logicalFrame||!m.physicalFrame||(exactFrame&&exactFrame!=m.logicalFrame))return false;
 if(!readable(uintptr_t(m.logicalFrame),sizeof(CheckpointLoadWorkerFrame))||!readable(uintptr_t(m.physicalFrame),sizeof(CheckpointLoadWorkerFrame)))return false;
 const auto&l=*static_cast<const CheckpointLoadWorkerFrame*>(m.logicalFrame);const auto&p=*static_cast<const CheckpointLoadWorkerFrame*>(m.physicalFrame);
 if(l.slot!=m.logicalSlot||p.slot!=physical||l.call_id!=m.call||p.call_id!=m.call||l.thread_id!=m.thread||p.thread_id!=m.thread||
  l.caller_entry_rsp!=p.caller_entry_rsp||memcmp(l.args,p.args,sizeof l.args)||(self&&l.args[0]!=self)||!readable(l.caller_entry_rsp,8))return false;
 uintptr_t expected=physical<4?config_.base+0x50b785:physical==4?config_.base+0x834d9b:config_.base+0x3a9227;
#ifdef CHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE
 if(config_.fixtureCallers[physical])expected=config_.fixtureCallers[physical];
#endif
 return at<uintptr_t>(l.caller_entry_rsp)==expected;
}
bool Context::callback(unsigned f,unsigned p,uintptr_t a,uintptr_t b)const{
 Report r{};Snapshot(r);const auto&initial=config_.initial;
 if((f==2||f==3)&&r.load_retired)return false; // Never read a retired Load.
 if(f==0){if(p==0||p==1||p==5)return true;
  if(p==2)return mapping(0,3,initial.states[4]);
  if(p==3)return mapping(1,3,r.menu)||mapping(2,1,initial.states[2]);
  return mapping(2,1,initial.states[2]);}
 if(f==1)return p==0?mapping(1,3,r.menu):mapping(2,1,initial.states[2]);
 if(f==3||(f==2&&p==0))return mapping(3,(f==3&&p==2)?3:1,a);
 if(f==2){if(p==1||p==2){
    if(!readable(a+0x478+0x48,8))return false;auto callable=at<uintptr_t>(a+0x478+0x48);
    if(!readable(callable,16)||at<uintptr_t>(callable)!=config_.base+0x138e8c0||at<uintptr_t>(callable+8)!=config_.base+0x508b40)return false;
    return mapping(4,p==1?1:3,callable);}
  return mapping(5,p==3?1:3);}
 if(f==4){if(!readable(a+0x520+0x48,8))return false;auto callable=at<uintptr_t>(a+0x520+0x48);
   return readable(callable,16)&&at<uintptr_t>(callable)==config_.base+0x138e8c0&&at<uintptr_t>(callable+8)==config_.base+0x4da390&&mapping(4,p==5?3:1,callable);}
 if(f==5){(void)b;return mapping(0,p==0?1:3);}
 return false;
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
  at<BYTE>(c.world+0x36)!=c.month||at<BYTE>(c.world+0x37)!=c.day||at<BYTE>(c.world+0x3a)!=c.force||at<DWORD>(c.world+0x40)!=1||
  at<DWORD>(c.cache+8)!=0||at<DWORD>(c.cache+0x3f0)||at<LONG>(c.cache+0x3ec)!=pending)return false;
 return identity(c.root,config_.initialIdentity)&&at<BYTE>(c.world+0x165d)==1&&(!rng||at<DWORD>(b+0x18eb8b0)==c.expectedRng);
}
bool Context::queuedMenu(){
 checkpoint_persistent_logical_adapter::Mapping mapping{};Report own{};Snapshot(own);
 if(!checkpoint_persistent_logical_adapter::CurrentMapping(&mapping)||!own.queue_call||mapping.call!=own.queue_call||mapping.thread!=own.queue_thread)return fail(Error::Callback);
 qa::Report q{};if(!config_.queue->Snapshot(q)||q.error!=qa::Error::None||q.stage!=qa::Stage::Resolved||!q.authorized||
  q.native_calls!=1||q.native_returned!=1||q.native_result_verified!=1||q.resolver_calls!=1||q.thread!=GetCurrentThreadId()||q.call_id!=mapping.call||q.user!=config_.initial.states[4]||!q.menu)return fail(Error::Queue);
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
  at<uintptr_t>(title)!=b+0x12daaf0||!name(title,"CTitleState")||at<LONG>(title+0x47c)!=LONG(config_.fileProfile.slot))return fail(Error::Lifetime);
 auto closure=at<uintptr_t>(load+0x48);if(!readable(closure,16)||at<uintptr_t>(closure)!=b+0x12ea4d0||at<uintptr_t>(closure+8)!=title||at<uintptr_t>(b+0x12ea4d0+0x10)!=b+0x4fac30)return fail(Error::Lifetime);
 auto phase=at<DWORD>(load+0x470);if(phase<1||phase>4)return fail(Error::Phase);
 if(!readable(m,0x50)||at<std::uint64_t>(m+0x10)!=4||(current&&at<uintptr_t>(m+0x48)!=load))return fail(Error::Phase);
 auto stack=at<uintptr_t>(m+0x20);if(!readable(stack,32)||at<uintptr_t>(stack)!=config_.initial.states[0]||at<uintptr_t>(stack+8)!=config_.initial.states[1]||at<uintptr_t>(stack+16)!=title||at<uintptr_t>(stack+24)!=load)return fail(Error::Lifetime);
 auto slot=at<LONG>(b+0x201ecd0);if(slot==LONG(config_.fileProfile.slot)){if(!sso(b+0x201ece0,config_.fileProfile.name))return fail(Error::Pending);}
 else if(!allowCleared||slot!=-1||!sso(b+0x201ece0,""))return fail(Error::Pending);
 AcquireSRWLockExclusive(&lock_);report_.load=load;report_.title=title;ReleaseSRWLockExclusive(&lock_);return true;
}
bool Context::titleGraph(uintptr_t title,uintptr_t root,uintptr_t world,bool after,bool targetPair){
 Report r{};Snapshot(r);auto b=config_.base,m=b+0x19e7310;
 if(!r.load_completed||title!=r.title||!readable(title,0x580)||!readable(root,0x85138)||!readable(world,0x20ac)||
  at<uintptr_t>(b+0x1fca1e0)!=root||at<uintptr_t>(root+0x85130)!=world||at<uintptr_t>(root)!=b+0x12aa6b0||at<uintptr_t>(world)!=b+0x12aa638||
  at<uintptr_t>(title)!=b+0x12daaf0||!name(title,"CTitleState")||at<LONG>(title+0x47c)!=LONG(config_.fileProfile.slot))return fail(Error::Lifetime);
 auto n=at<std::uint64_t>(m+0x10),stack=at<uintptr_t>(m+0x20);if((n!=3&&n!=4)||!readable(stack,size_t(n)*8)||
  at<uintptr_t>(stack)!=config_.initial.states[0]||at<uintptr_t>(stack+8)!=config_.initial.states[1]||at<uintptr_t>(stack+16)!=title||
  (n==4&&at<uintptr_t>(stack+24)!=r.load))return fail(Error::Lifetime); // historical Load address only
 auto phase=at<DWORD>(title+0x470);if((phase!=13&&phase!=15)||(n==3&&phase!=15))return fail(Error::Phase);
 if(at<WORD>(world+0x34)!=config_.worldProfile.year||at<BYTE>(world+0x36)!=config_.worldProfile.month||at<BYTE>(world+0x37)!=config_.worldProfile.day||at<BYTE>(world+0x3a)!=(after?config_.worldProfile.target.force:config_.worldProfile.source.force)||at<BYTE>(world+0x165d)!=(after?1:2))return fail(Error::Phase);
 const auto&who=targetPair?config_.worldProfile.target:config_.worldProfile.source;
 const unsigned force=who.force,person=who.ruler;
 if(!identity(root,config_.worldProfile.source)||!identity(root,config_.worldProfile.target))return fail(Error::Phase);
 if(at<uintptr_t>(title+0x4a0)!=at<uintptr_t>(root+0xdca0+force*8)||at<uintptr_t>(title+0x4a8)!=at<uintptr_t>(root+0x148+person*8))return fail(Error::Phase);
 AcquireSRWLockExclusive(&lock_);report_.load_retired=1;if(after)report_.identity_returned=1;ReleaseSRWLockExclusive(&lock_);return true;
}
bool Context::planningGraph()const{
 Report r{};Snapshot(r);if(!r.identity_returned||!r.load_completed||!r.load_retired)return false;
 auto b=config_.base,m=b+0x19e7310;if(!readable(m,0x50)||at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30))return false;
 auto stack=at<uintptr_t>(m+0x20);if(!readable(stack,40)||at<uintptr_t>(stack)!=config_.initial.states[0]||at<uintptr_t>(stack+8)!=config_.initial.states[1])return false;
 const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
 // A current formal object can occupy a retired Load/Title allocation. Its
 // current stack provenance/type, not its numerical address history, owns the
 // following reads. Old live Load/Title types cannot satisfy this chain.
 const uintptr_t vt[]={0,0x12f22d8,0x12cc9b8,0x12cd400,0x12cc4a8};
 uintptr_t states[5]{};
 for(unsigned i=0;i<5;++i){auto state=at<uintptr_t>(stack+i*8);states[i]=state;
  if(!state||!readable(state,0x90)||!name(state,names[i])||at<DWORD>(state+0x68)||
   (i&&at<uintptr_t>(state)!=b+vt[i])||(i!=4&&at<uintptr_t>(state+0x50)))return false;
  for(unsigned j=0;j<i;++j)if(states[j]==state)return false;
 }
 auto user=at<uintptr_t>(stack+32),root=at<uintptr_t>(b+0x1fca1e0);if(!readable(user,0x668)||!readable(root,0x85138)||at<uintptr_t>(m+0x48)!=user||at<uintptr_t>(user)!=b+0x12cc4a8||at<DWORD>(user+0x470)!=2)return false;
 auto world=at<uintptr_t>(root+0x85130);if(!readable(world,0x1660)||at<WORD>(world+0x34)!=config_.worldProfile.year||at<BYTE>(world+0x36)!=config_.worldProfile.month||at<BYTE>(world+0x37)!=config_.worldProfile.day||at<BYTE>(world+0x3a)!=config_.worldProfile.target.force||at<BYTE>(world+0x165d)!=1||!identity(root,config_.worldProfile.target))return false;
 auto cache=at<uintptr_t>(b+0x2025318);return readable(cache,0x3f4)&&at<LONG>(cache+0x3ec)==-1&&!at<DWORD>(cache+0x3f0);
}
bool Context::body(unsigned f,unsigned p,uintptr_t a,uintptr_t b,uintptr_t c){
 if(!callback(f,p,a,b))return fail(Error::Callback);
 if(f==0){ // Session
  if(p==0||p==1)return common(Slots::Owned,true)&&(initialGraph(5,0,-1,true)||fail(Error::Lifetime));
  if(p==5)return common(Slots::Owned,false); // cleanup must not dereference retired game objects
  if(!common(Slots::Owned,true))return false;
  if(p==2)return queuedMenu();
  if(p==3){ // MenuReceipt and GameBefore both map here.
   auto m=config_.base+0x19e7310;Report r{};Snapshot(r);auto current=at<uintptr_t>(m+0x48);
   return (current==r.menu||current==config_.initial.states[2])&&(initialGraph(6,current,-1,true)||fail(Error::Lifetime));
  }
  return initialGraph(6,config_.initial.states[2],LONG(config_.fileProfile.slot),true)||fail(Error::Pending);
 }
 if(f==1){if(!common(Slots::Owned,true))return false;Report r{};Snapshot(r);
  return initialGraph(6,p==0?r.menu:config_.initial.states[2],p==6?LONG(config_.fileProfile.slot):-1,true)||fail(Error::Pending);}
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
bool Context::PlanningGuard(void*c,pr::Point p,const CheckpointPushFrame&f,std::uint64_t a,std::uint64_t e,std::uint64_t generation)noexcept{
 if(!c)return false;auto&s=*static_cast<Context*>(c);
 __try{if(generation!=s.expected_.generation||!s.mapping(0,p==pr::Point::Before?1:3,f.args[0],&f))return s.fail(Error::Callback);}
 __except(EXCEPTION_EXECUTE_HANDLER){return s.fail(Error::Memory,GetExceptionCode());}
 return s.check(5,unsigned(p)-1,uintptr_t(a),uintptr_t(e));
}
bool Context::AttachmentOnly(void*c)noexcept{return c&&static_cast<Context*>(c)->common(Slots::Owned,false);}
bool Context::OwnedReadBridgeOnly(void*c)noexcept{return c&&static_cast<Context*>(c)->common(Slots::Owned,false);}
bool Context::QueueGuard(void*c,qa::Point p)noexcept{
 if(!c||unsigned(p)>4)return false;auto&s=*static_cast<Context*>(c);AcquireSRWLockExclusive(&s.lock_);++s.report_.queue_calls[unsigned(p)];ReleaseSRWLockExclusive(&s.lock_);
 __try{
  if(p!=qa::Point::Initialize&&!s.mapping(0,3,s.config_.initial.states[4]))return s.fail(Error::Callback);
  if(!s.common(Slots::Owned,true))return false;
  if(p==qa::Point::Initialize)return s.initialGraph(5,0,-1,true)||s.fail(Error::Lifetime);
  checkpoint_persistent_logical_adapter::Mapping mapping{};
  if(!checkpoint_persistent_logical_adapter::CurrentMapping(&mapping))return s.fail(Error::Callback);
  if(p==qa::Point::Authorize){
   if(!s.initialGraph(5,s.config_.initial.states[4],-1,true))return s.fail(Error::Lifetime);
   AcquireSRWLockExclusive(&s.lock_);const bool fresh=!s.report_.queue_call;
   if(fresh){s.report_.queue_call=mapping.call;s.report_.queue_thread=mapping.thread;}
   ReleaseSRWLockExclusive(&s.lock_);return fresh||s.fail(Error::Callback);
  }
  Report prior{};s.Snapshot(prior);
  if(!prior.queue_call||prior.queue_call!=mapping.call||prior.queue_thread!=mapping.thread)return s.fail(Error::Callback);
  if(p==qa::Point::BeforeNative)return s.initialGraph(5,s.config_.initial.states[4],-1,true)||s.fail(Error::Lifetime);
  // The adapter itself checks actual returned vector/menu fields before/after
  // this callback. No recursion into Adapter::Snapshot or its validators.
  auto b=s.config_.base,m=b+0x19e7310,cache=s.config_.initial.cache;
  return at<std::uint64_t>(m+0x10)==5&&at<std::uint64_t>(m+0x30)==1&&at<uintptr_t>(m+0x48)==s.config_.initial.states[4]&&
   at<uintptr_t>(b+0x2025318)==cache&&at<LONG>(cache+0x3ec)==-1&&at<DWORD>(cache+8)==0&&!at<DWORD>(cache+0x3f0);
 }__except(EXCEPTION_EXECUTE_HANDLER){return s.fail(Error::Memory,GetExceptionCode());}
}
}

