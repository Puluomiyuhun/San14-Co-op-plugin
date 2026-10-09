#include "b_warm_coordinator_native.h"
#include "b_warm_two_bank_owner.h"
#include <cstring>
namespace {
SRWLOCK gate=SRWLOCK_INIT;
b_warm_two_bank::Handover handover;
b_warm_coordinator::Prepare bound{};
HMODULE nextModule=nullptr;
unsigned stage=0;
bool attempted=false;
std::uint64_t birth(){FILETIME b{},e{},k{},u{};if(!GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u))return 0;return(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime;}
bool nonzero(const unsigned char* p){unsigned n=0;for(unsigned i=0;i<32;++i)n|=p[i];return n!=0;}
bool valid(const b_warm_coordinator::Header& h,unsigned size,unsigned op){return h.magic==b_warm_coordinator::Magic&&h.size==size&&h.version==1&&h.operation==op&&!h.result&&nonzero(h.nonce);}
bool same(const b_warm_coordinator::Header& h){return !memcmp(h.nonce,bound.header.nonce,32);}
DWORD prepare(void* raw){
 auto& x=*static_cast<b_warm_coordinator::Prepare*>(raw);
 if(!valid(x.header,sizeof x,1))return 1;
 if(attempted)return x.header.result=2;
 attempted=true; // A valid-shaped preparation is one shot, including rejection.
 if(x.reserved||x.pid!=GetCurrentProcessId()||x.birth!=birth()||!x.first)return x.header.result=3;
 HMODULE self=nullptr;
 if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&PrepareBWarmCoordinator),&self))return x.header.result=4;
 void** slots[6]{};void* originals[6]{};
 for(unsigned i=0;i<6;++i){slots[i]=reinterpret_cast<void**>(x.slots[i]);originals[i]=reinterpret_cast<void*>(x.originals[i]);}
 if(!handover.Bind(reinterpret_cast<HMODULE>(x.first),slots,originals))return x.header.result=5;
 bound=x;stage=1;return 0;
}
DWORD authorize(void* raw){
 auto& x=*static_cast<b_warm_coordinator::Authorize*>(raw);
 if(!valid(x.header,sizeof x,2))return 1;
 if(stage!=1||!same(x.header)||!x.second)return x.header.result=2;
 if(!handover.AuthorizeSecond(reinterpret_cast<HMODULE>(x.second)))return x.header.result=3;
 nextModule=reinterpret_cast<HMODULE>(x.second);stage=2;return 0;
}
DWORD observe(void* raw){
 auto& x=*static_cast<b_warm_coordinator::Observe*>(raw);
 if(!valid(x.header,sizeof x,3))return 1;
 if(!stage||!same(x.header))return x.header.result=2;
 x.first=bound.first;x.second=reinterpret_cast<std::uint64_t>(nextModule);x.reserved=0;
 // After authorization, original first completion is frozen; second hooks may
 // temporarily occupy the shared sources, so do not re-query first as current.
 x.firstCompleted=stage>=2||handover.Completed(reinterpret_cast<HMODULE>(bound.first));
 x.secondCompleted=nextModule&&handover.Completed(nextModule);
 if(x.secondCompleted)stage=3;
 x.stage=stage;return 0;
}
DWORD guarded(void* raw,DWORD(*fn)(void*))noexcept{
 if(!raw)return 1;
 if(!TryAcquireSRWLockExclusive(&gate))return 10;
 DWORD result=99;
 __try{result=fn(raw);}__except(EXCEPTION_EXECUTE_HANDLER){result=99;}
 ReleaseSRWLockExclusive(&gate);return result;
}
}
extern "C" DWORD WINAPI DescribeBWarmCoordinator(void* raw){if(!raw)return 1;__try{*static_cast<b_warm_coordinator::Description*>(raw)=b_warm_coordinator::Description{};return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 99;}}
extern "C" DWORD WINAPI PrepareBWarmCoordinator(void* raw){return guarded(raw,prepare);}
extern "C" DWORD WINAPI AuthorizeBWarmCoordinator(void* raw){return guarded(raw,authorize);}
extern "C" DWORD WINAPI ObserveBWarmCoordinator(void* raw){return guarded(raw,observe);}
