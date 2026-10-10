#include "b_warm_chain_coordinator_native.h"
#include <cstring>
namespace {
using namespace b_warm_chain_coordinator;
SRWLOCK gate=SRWLOCK_INIT;b_warm_chain::Chain chain;Prepare bound{};
std::uint64_t banks[3]{};unsigned generation=0;bool attempted=false;
std::uint64_t birth(){FILETIME b{},e{},k{},u{};return GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u)?(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime:0;}
bool valid(const Header&h,unsigned size,unsigned op){unsigned nz=0;for(auto b:h.nonce)nz|=b;return h.magic==Magic&&h.size==size&&h.version==1&&h.operation==op&&!h.result&&nz;}
bool same(const Header&h){return generation&&bound.pid==GetCurrentProcessId()&&bound.birth==birth()&&!memcmp(h.nonce,bound.header.nonce,32);}
DWORD prepare(void*raw){auto&x=*static_cast<Prepare*>(raw);
 if(!valid(x.header,sizeof x,1))return 1;if(attempted)return x.header.result=2;attempted=true;
 if(x.reserved||x.pid!=GetCurrentProcessId()||!x.birth||x.birth!=birth()||!x.first)return x.header.result=3;
 HMODULE self=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&PrepareBWarmChainCoordinator),&self))return x.header.result=4;
 void**slots[6]{};void*originals[6]{};for(unsigned i=0;i<6;++i){slots[i]=reinterpret_cast<void**>(x.slots[i]);originals[i]=reinterpret_cast<void*>(x.originals[i]);}
 if(!chain.Bind(reinterpret_cast<HMODULE>(x.first),slots,originals,x.header.nonce))return x.header.result=5;
 bound=x;banks[0]=x.first;generation=1;return 0;
}
DWORD authorize(void*raw){auto&x=*static_cast<Authorize*>(raw);
 if(!valid(x.header,sizeof x,2))return 1;
 if(!same(x.header)||x.reserved||generation>=3||x.generation!=generation+1||!x.next)return x.header.result=2;
 Certificate c{};if(!chain.AuthorizeNext(reinterpret_cast<HMODULE>(x.next),x.generation,c))return x.header.result=3;
 banks[generation]=x.next;generation=x.generation;return 0;
}
DWORD observe(void*raw){auto&x=*static_cast<Observe*>(raw);
 if(!valid(x.header,sizeof x,3))return 1;if(!same(x.header))return x.header.result=2;
 x.currentGeneration=generation;x.reserved=0;memcpy(x.banks,banks,sizeof banks);memset(x.completed,0,sizeof x.completed);
 x.certificateCount=generation-1;for(auto&c:x.certificates)c=Certificate{};
 for(unsigned i=0;i+1<generation;++i){if(!chain.ReadCertificate(i+2,x.certificates[i]))return x.header.result=3;x.completed[i]=1;}
 x.completed[generation-1]=chain.CompletedCurrent(generation)?1:0;return 0;
}
DWORD guarded(void*raw,DWORD(*fn)(void*))noexcept{if(!raw)return 1;if(!TryAcquireSRWLockExclusive(&gate))return 10;DWORD result=99;
 __try{result=fn(raw);}__except(EXCEPTION_EXECUTE_HANDLER){result=99;}ReleaseSRWLockExclusive(&gate);return result;}
}
extern "C" DWORD WINAPI DescribeBWarmChainCoordinator(void*raw){if(!raw)return 1;__try{*static_cast<b_warm_chain_coordinator::Description*>(raw)=b_warm_chain_coordinator::Description{};return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 99;}}
extern "C" DWORD WINAPI PrepareBWarmChainCoordinator(void*raw){return guarded(raw,prepare);}
extern "C" DWORD WINAPI AuthorizeBWarmChainCoordinator(void*raw){return guarded(raw,authorize);}
extern "C" DWORD WINAPI ObserveBWarmChainCoordinator(void*raw){return guarded(raw,observe);}
