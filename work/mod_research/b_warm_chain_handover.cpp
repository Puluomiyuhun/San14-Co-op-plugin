#include "b_warm_chain_handover.h"
#include <cstring>
namespace b_warm_chain {
namespace {
using Fn=DWORD(WINAPI*)(void*);
std::uint64_t birth(){FILETIME b{},e{},k{},u{};return GetProcessTimes(GetCurrentProcess(),&b,&e,&k,&u)?(std::uint64_t(b.dwHighDateTime)<<32)|b.dwLowDateTime:0;}
bool pin(HMODULE m){HMODULE actual=nullptr;return m&&GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(m),&actual)&&actual==m;}
bool proof(HMODULE module,Certificate&out){
 auto pf=reinterpret_cast<Fn>(GetProcAddress(module,"GetBWarmProfileReport"));
 auto rf=reinterpret_cast<Fn>(GetProcAddress(module,"GetBWarmRetireReport"));
 if(!pf||!rf)return false;b_warm_profile::Report p{};b_warm_retire::Report r{};
 if(pf(&p)||rf(&r)||!r.attempt||!r.sealed||!r.restored||r.restoreFailed||!p.ready||p.error)return false;
 out.attempt=r.attempt;out.userCall=r.userCall;out.identityCall=r.identityCall;out.loadCall=r.loadCall;
 memcpy(out.fileSha256,p.profile.file.sha256,32);return true;
}
}
bool Chain::current()const noexcept{return generation_&&pid_==GetCurrentProcessId()&&birth_==birth();}
bool Chain::Bind(HMODULE first,void**const(&slots)[6],void*const(&originals)[6],const unsigned char(&nonce)[32])noexcept{
 AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {__try {unsigned nz=0;for(auto b:nonce)nz|=b;if(generation_||!nz||!birth()||!pin(first))__leave;
 if(!edges_[0].Bind(first,slots,originals))__leave;
 edgeBound_[0]=true;banks_[0]=first;memcpy(slots_,slots,sizeof slots_);memcpy(originals_,originals,sizeof originals_);
 memcpy(nonce_,nonce,32);pid_=GetCurrentProcessId();birth_=birth();generation_=1;ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){ok=false;}}__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Chain::AuthorizeNext(HMODULE next,unsigned generation,Certificate&out)noexcept{
 out={};AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {__try {
 if(!current()||generation_>=3||generation!=generation_+1||!next)__leave;
 for(unsigned i=0;i<generation_;++i)if(next==banks_[i])__leave;
 const auto edge=generation_-1;const auto prior=banks_[generation_-1];
 // The second edge binds the completed second module; no old edge is reset.
 if(!edgeBound_[edge]){
  if(!edges_[0].Completed(prior)||!edges_[edge].Bind(prior,slots_,originals_))__leave;
  edgeBound_[edge]=true;
 }
 if(!edges_[edge].Completed(prior))__leave;
 Certificate before{},after{};
 if(!proof(prior,before)||!edges_[edge].Completed(prior)||!proof(prior,after)||memcmp(&before,&after,sizeof before))__leave;
 if(!pin(next)||!edges_[edge].AuthorizeSecond(next))__leave;
 after.pid=pid_;after.birth=birth_;after.generation=generation;after.previous=uintptr_t(prior);after.next=uintptr_t(next);memcpy(after.nonce,nonce_,32);
 // Current one-based generation is the next bank's zero-based index.
 certificates_[edge]=after;banks_[generation_]=next;generation_=generation;out=after;ok=true;
 }__except(EXCEPTION_EXECUTE_HANDLER){ok=false;}}__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Chain::ReadCertificate(unsigned generation,Certificate&out)noexcept{
 out={};AcquireSRWLockShared(&lock_);bool ok=current()&&generation>=2&&generation<=generation_;
 if(ok)out=certificates_[generation-2];ReleaseSRWLockShared(&lock_);return ok;
}
bool Chain::CompletedCurrent(unsigned generation)noexcept{
 AcquireSRWLockExclusive(&lock_);bool ok=current()&&generation==generation_&&edges_[generation_==1?0:generation_-2].Completed(banks_[generation_-1]);
 ReleaseSRWLockExclusive(&lock_);return ok;
}
}
