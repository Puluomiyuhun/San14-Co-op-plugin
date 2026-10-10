#include "reward_menu_creation.h"
#include <intrin.h>
#include <bcrypt.h>
#include <cstring>
#pragma comment(lib,"bcrypt.lib")
namespace {
using namespace reward_menu_creation;
SRWLOCK lock=SRWLOCK_INIT;Config c{};Report r{};bool attempted=false;DWORD nativeDepth=0;
constexpr uintptr_t sites[]={0x3FA09A,0x3FC3F3,0x3E2D80,0x50B35B};
constexpr unsigned lengths[]={5,5,5,8};
constexpr unsigned char originals[4][8]={{0xe8,0xd1,0x21,0,0},{0xe8,0xf8,0x68,0xfe,0xff},{0xe8,0x3b,0x71,0x12,0},{0x49,0x8b,0x4f,0x10,0x49,0x8b,0x47,0x20}};
template<class T>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}
bool reject(Error e){++r.rejected;if(r.error==Error::None)r.error=e;r.phase=Phase::Fault;return false;}
bool readable(uintptr_t p,size_t n){if(!p||!n||p>UINTPTR_MAX-n)return false;for(auto end=p+n;p<end;){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||(m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;auto next=uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;}return true;}
bool rx(uintptr_t p,size_t n){if(!readable(p,n))return false;MEMORY_BASIC_INFORMATION m{};if(!VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)||uintptr_t(m.AllocationBase)!=c.base||(m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY))return false;
#ifndef REWARD_MENU_CREATION_FIXTURE
 if(m.Type!=MEM_IMAGE)return false;
#endif
 return true;}
bool digest(const void*p,ULONG n,const char*expected){unsigned char hash[32]{};
 BCRYPT_ALG_HANDLE alg=nullptr;if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;
 const auto status=BCryptHash(alg,nullptr,0,const_cast<PUCHAR>(static_cast<const unsigned char*>(p)),n,hash,32);BCryptCloseAlgorithmProvider(alg,0);if(status<0)return false;
 constexpr char chars[]="0123456789abcdef";char text[65]{};for(unsigned i=0;i<32;++i){text[i*2]=chars[hash[i]>>4];text[i*2+1]=chars[hash[i]&15];}return !memcmp(text,expected,64);}
bool source(bool raw){
 const uintptr_t entries[]={uintptr_t(&RewardMenuCreationDispatch),uintptr_t(&RewardMenuCreationCreate),uintptr_t(&RewardMenuCreationName),uintptr_t(&RewardMenuCreationActivation)};
 for(unsigned i=0;i<4;++i){const auto p=c.base+sites[i];if(!rx(p,lengths[i]))return false;if(raw){if(memcmp(reinterpret_cast<void*>(p),originals[i],lengths[i]))return false;}else{
  const auto relay=c.relays[i];if(!rx(relay,14)||at<unsigned char>(p)!=0xe8||p+5+at<std::int32_t>(p+1)!=relay)return false;
  const unsigned char jump[]={0xff,0x25,0,0,0,0};if(memcmp(reinterpret_cast<void*>(relay),jump,6)||at<uintptr_t>(relay+6)!=entries[i])return false;
  for(unsigned j=5;j<lengths[i];++j)if(at<unsigned char>(p+j)!=0x90)return false;
 }}
 struct Body{uintptr_t start;ULONG size;const char*sha;};const Body bodies[]={
 {0x3FC270,0x7BF,"38ffd51bf190b79bc23cca7139c1ad3a38fb1c8d34b340133d5c519215e4b219"},
 {0x3E2CF0,0x169,"11ab030760cd89d5d905bc27010b2fb3afe8bd9f0c2b489ecf8f9f86908b3100"},
 {0x509EC0,0x22,"ed7c2ab603241e21dba34a1aed3b20c02dff82075cfff5806f69272e2e48067d"},
 {0x6082E0,0xC5,"3808f291ce6860ecb21d62141feabd05e263f3eedcfe4b9f942d3de9c4da6c57"},
 {0x50A7BA,0xBFC,"b09efc7911b9863eeaac12b753cd1a23093b46425101c5d36484be65ef6f3ccf"}};
 unsigned char copy[0xC00]{};for(const auto&b:bodies){if(!rx(c.base+b.start,b.size))return false;memcpy(copy,reinterpret_cast<void*>(c.base+b.start),b.size);if(!raw)for(unsigned i=0;i<4;++i)if(sites[i]>=b.start&&sites[i]+lengths[i]<=b.start+b.size)memcpy(copy+sites[i]-b.start,originals[i],lengths[i]);if(!digest(copy,b.size,b.sha))return false;}
 if(at<unsigned>(c.base+0x3FCA30+11*4)!=0x3FC3B0||memcmp(reinterpret_cast<void*>(c.base+0x12CDB40),"CStrategyRewardState",21))return false;return true;
}
bool identity(){return c.thread==GetCurrentThreadId()&&at<uintptr_t>(c.base+0x1FCA1E0)==c.root&&at<uintptr_t>(c.root+0x85130)==c.world&&at<unsigned short>(c.world+0x34)==c.year&&at<unsigned char>(c.world+0x36)==c.month&&at<unsigned char>(c.world+0x37)==c.day&&at<unsigned char>(c.world+0x3A)==c.force;}
bool shape(unsigned count){auto m=c.base+0x19E7310,s=at<uintptr_t>(m+0x20);if(at<std::uint64_t>(m+0x10)!=count||!readable(s,count*8))return false;for(unsigned i=0;i<5;++i)if(at<uintptr_t>(s+i*8)!=c.states[i])return false;return at<uintptr_t>(c.user)==c.base+0x12CC4A8&&at<unsigned>(c.user+0x470)==2&&(count==5||at<uintptr_t>(s+40)==r.menu);}
bool menu(){return r.menu&&at<uintptr_t>(r.menu)==c.base+0x1331078&&at<uintptr_t>(r.menu+0x470)==c.district&&!memcmp(reinterpret_cast<void*>(r.menu+0x70),"CStrategyRewardState",21);}
}
namespace reward_menu_creation {
bool Bind(const Config&cfg)noexcept {AcquireSRWLockExclusive(&lock);bool ok=false;__try{__try{if(attempted){++r.rejected;__leave;}attempted=true;c=cfg;if(!c.base||!c.root||!c.world||!c.user||!c.district||!c.generation||c.thread!=GetCurrentThreadId()||c.states[4]!=c.user){reject(Error::Config);__leave;}for(unsigned i=0;i<5;++i){if(!c.states[i]){reject(Error::Config);__leave;}for(unsigned j=0;j<i;++j)if(c.states[i]==c.states[j]){reject(Error::Config);__leave;}}for(auto relay:c.relays)if(relay<c.base+0x1000||relay>c.base+0x2400000-14){reject(Error::Config);__leave;}if(!source(true)){reject(Error::Source);__leave;}if(!identity()||!shape(5)||at<std::uint64_t>(c.base+0x19E7340)){reject(Error::Identity);__leave;}r.phase=Phase::Bound;ok=true;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{ReleaseSRWLockExclusive(&lock);}return ok;}
Report Snapshot()noexcept{AcquireSRWLockShared(&lock);auto result=r;ReleaseSRWLockShared(&lock);return result;}
bool Take(std::uint64_t generation,Evidence&out)noexcept{out={};AcquireSRWLockExclusive(&lock);bool ok=false;__try{__try{if(r.phase!=Phase::Activated||generation!=c.generation){++r.rejected;__leave;}if(!identity()||!source(false)||!shape(6)||!menu()||at<std::uint64_t>(c.base+0x19E7340)||at<unsigned>(r.menu+0x6c)!=1||at<uintptr_t>(r.menu+0x478)!=r.layout){reject(Error::Activation);__leave;}out.binding=c;out.menu=r.menu;out.layout=r.layout;out.creation_observed=out.activation_observed=true;r.phase=Phase::Taken;++r.taken;ok=true;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{ReleaseSRWLockExclusive(&lock);}return ok;}
}
extern "C" void RewardMenuCreationDispatch(uintptr_t user,unsigned command)noexcept {
 const auto caller=uintptr_t(_ReturnAddress());bool run=false;AcquireSRWLockExclusive(&lock);__try{__try{if(c.thread!=GetCurrentThreadId()){reject(Error::Thread);__leave;}if(r.phase!=Phase::Bound||nativeDepth||caller!=c.base+0x3FA09F){reject(Error::Order);__leave;}if(command!=21){reject(Error::Command);__leave;}if(user!=c.user||!identity()||!shape(5)||at<uintptr_t>(c.base+0x19E7358)!=user||at<std::uint64_t>(c.base+0x19E7340)||!source(false)){reject(Error::Identity);__leave;}nativeDepth=1;r.phase=Phase::Dispatching;++r.dispatch;run=true;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{ReleaseSRWLockExclusive(&lock);}
 if(!run)return;__try{reinterpret_cast<void(*)(uintptr_t,unsigned)>(c.base+0x3FC270)(user,command);}__except(EXCEPTION_EXECUTE_HANDLER){AcquireSRWLockExclusive(&lock);reject(Error::Exception);ReleaseSRWLockExclusive(&lock);}AcquireSRWLockExclusive(&lock);if(r.phase!=Phase::Queued&&r.phase!=Phase::Fault)reject(Error::Order);nativeDepth=0;ReleaseSRWLockExclusive(&lock);
}
extern "C" void RewardMenuCreationCreate(uintptr_t manager,uintptr_t name,uintptr_t args,uintptr_t callback)noexcept {
 const auto caller=uintptr_t(_ReturnAddress());bool run=false;AcquireSRWLockExclusive(&lock);__try{__try{if(!identity()||nativeDepth!=1||r.phase!=Phase::Dispatching||caller!=c.base+0x3FC3F8||manager!=c.base+0x19E7310||name!=c.base+0x12CDB40||!args||at<uintptr_t>(args)!=c.district||!callback||!source(false)){reject(Error::Order);__leave;}nativeDepth=2;r.phase=Phase::Creating;++r.create;run=true;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{ReleaseSRWLockExclusive(&lock);}if(!run)return;
 __try{reinterpret_cast<void(*)(uintptr_t,uintptr_t,uintptr_t,uintptr_t)>(c.base+0x3E2CF0)(manager,name,args,callback);}__except(EXCEPTION_EXECUTE_HANDLER){AcquireSRWLockExclusive(&lock);reject(Error::Exception);ReleaseSRWLockExclusive(&lock);}
 AcquireSRWLockExclusive(&lock);__try{__try{if(r.phase==Phase::Fault)__leave;const auto q=at<uintptr_t>(manager+0x40);if(r.phase!=Phase::Named||!identity()||!shape(5)||!menu()||at<std::uint64_t>(manager+0x30)!=1||!readable(q,16)||at<unsigned>(q)!=0||at<uintptr_t>(q+8)!=r.menu||!source(false)){reject(Error::Queue);__leave;}r.phase=Phase::Queued;++r.queued;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{nativeDepth=1;ReleaseSRWLockExclusive(&lock);}
}
extern "C" void RewardMenuCreationName(uintptr_t manager,uintptr_t state,uintptr_t name)noexcept {
 const auto caller=uintptr_t(_ReturnAddress());AcquireSRWLockExclusive(&lock);__try{__try{if(!identity()||nativeDepth!=2||r.phase!=Phase::Creating||caller!=c.base+0x3E2D85||manager!=c.base+0x19E7310||name!=c.base+0x12CDB40||!state||at<uintptr_t>(state)!=c.base+0x1331078||at<uintptr_t>(state+0x470)!=c.district||!source(false)){reject(Error::Menu);__leave;}
 reinterpret_cast<void(*)(uintptr_t,uintptr_t,uintptr_t)>(c.base+0x509EC0)(manager,state,name);r.menu=state;if(!menu()){reject(Error::Menu);__leave;}r.phase=Phase::Named;++r.named;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{ReleaseSRWLockExclusive(&lock);}
}
extern "C" void RewardMenuCreationActivated(uintptr_t manager,uintptr_t state,uintptr_t caller)noexcept {
 AcquireSRWLockExclusive(&lock);__try{__try{if(!identity()||nativeDepth||r.phase!=Phase::Queued||caller!=c.base+0x50B360||manager!=c.base+0x19E7310||state!=r.menu||!shape(6)||!menu()||at<std::uint64_t>(manager+0x30)||at<std::uint64_t>(manager+0x38)||at<uintptr_t>(manager+0x40)||!source(false)){reject(Error::Activation);__leave;}r.layout=at<uintptr_t>(state+0x478);if(!r.layout){reject(Error::Activation);__leave;}r.phase=Phase::Activated;++r.activated;}__except(EXCEPTION_EXECUTE_HANDLER){reject(Error::Exception);}}__finally{ReleaseSRWLockExclusive(&lock);}
}
