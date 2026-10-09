#include "b_warm_two_bank_owner.h"
#include <cstring>
#include <initializer_list>
namespace b_warm_two_bank {
namespace {
using Fn=DWORD(WINAPI*)(void*);
bool own(HMODULE m,uintptr_t p){MEMORY_BASIC_INFORMATION q{};return p&&VirtualQuery(reinterpret_cast<void*>(p),&q,sizeof q)==sizeof q&&q.Type==MEM_IMAGE&&q.AllocationBase==m&&q.State==MEM_COMMIT&&!(q.Protect&(PAGE_GUARD|PAGE_NOACCESS));}
bool call(HMODULE m,const char*n,void*out){auto f=GetProcAddress(m,n);return own(m,uintptr_t(f))&&!reinterpret_cast<Fn>(f)(out);}
bool describe(HMODULE m,b_warm_profile::Description&d){return call(m,"DescribeBWarmProfileOwner",&d)&&d.magic==b_warm_profile::Magic&&d.size==sizeof d&&d.version==1&&d.configSize==sizeof(b_warm_profile::Config)&&d.profileSize==sizeof(b_warm_profile::Profile)&&d.reportSize==sizeof(b_warm_profile::Report)&&d.bank.module==uintptr_t(m);}
}
bool Handover::Bind(HMODULE first,void**const(&slots)[6],void*const(&originals)[6])noexcept{
    if(first_||!first )return false;__try {b_warm_profile::Description d{};if(!describe(first,d))return false;
    for(unsigned i=0;i<6;++i)if(!originals[i]||!slots[i]||*slots[i]!=originals[i])return false;
    for(unsigned i=0;i<6;++i)for(unsigned j=0;j<i;++j)if(slots[i]==slots[j])return false;
    first_=first;memcpy(slots_,slots,sizeof slots_);memcpy(originals_,originals,sizeof originals_);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Handover::Completed(HMODULE bank)const noexcept{
    if(!first_||!bank)return false;__try{
    b_warm_profile::Description d{};b_warm_profile::Report p{};b_warm_retire::Report retired{};checkpoint_complete_live_owner::Report r{};
    if(!describe(bank,d)||!call(bank,"GetBWarmProfileReport",&p)||!call(bank,"GetBWarmRetireReport",&retired)||!call(bank,"GetCheckpointCompleteLiveOwnerReport",&r))return false;
    if(p.magic!=b_warm_profile::Magic||p.size!=sizeof p||p.version!=1||!p.ready||p.error||retired.version!=1||retired.size!=sizeof retired||!retired.bound||!retired.sealed||!retired.restored||retired.restoreFailed||r.magic!=checkpoint_complete_live_owner::Magic||r.size!=sizeof r||r.version!=1)return false;
    using V=checkpoint_complete_live_owner::Value;
    for(auto v:{V::OwnerError,V::SessionError,V::BytesError,V::LifecycleError,V::IdentityError,V::PlanningError,V::ActiveDispatch,V::ActiveWorker,V::ActiveRead,V::StopRequested})if(r.value[unsigned(v)])return false;
    for(auto v:{V::CasPublished,V::BytesMatched,V::LifecycleReady,V::IdentityReady,V::PlanningObserved,V::HooksRestored})if(!r.value[unsigned(v)])return false;
    if(!retired.attempt||retired.attempt!=r.attempt||retired.userCall!=r.planningUserCall||retired.identityCall!=r.planningIdentityCall||retired.loadCall!=r.planningCompletedCall||memcmp(p.profile.file.sha256,r.requestReadSha,32))return false;
    for(unsigned i=0;i<6;++i){const auto&h=r.hooks[i];const auto bridge=i<4?d.bank.dispatchBridge[i]:i==4?d.bank.workerBridge:d.bank.readBridge;MEMORY_BASIC_INFORMATION q{};
      if(h.slot!=uintptr_t(slots_[i])||h.original!=uintptr_t(originals_[i])||h.hook!=bridge||!own(bank,bridge)||*slots_[i]!=originals_[i]||h.error||!h.restored||h.dirty||VirtualQuery(slots_[i],&q,sizeof q)!=sizeof q||q.Protect!=h.protection)return false;
    }return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Handover::AuthorizeSecond(HMODULE second)noexcept{
    if(issued_||!second||second==first_)return false;__try{if(!Completed(first_))return false;
    b_warm_profile::Description a{},b{};b_warm_profile::Report p{};checkpoint_complete_live_owner::Report r{};
    if(!describe(first_,a)||!describe(second,b)||!call(second,"GetBWarmProfileReport",&p)||!call(second,"GetCheckpointCompleteLiveOwnerReport",&r)||p.magic!=b_warm_profile::Magic||p.size!=sizeof p||p.version!=1||p.configured||p.ready||p.error||r.magic!=checkpoint_complete_live_owner::Magic||r.size!=sizeof r||r.version!=1||r.value[unsigned(checkpoint_complete_live_owner::Value::OwnerState)]||r.value[unsigned(checkpoint_complete_live_owner::Value::StopRequested)]||r.value[unsigned(checkpoint_complete_live_owner::Value::OwnerError)]||r.value[unsigned(checkpoint_complete_live_owner::Value::SessionError)]||r.value[unsigned(checkpoint_complete_live_owner::Value::InstallCalls)]||r.value[unsigned(checkpoint_complete_live_owner::Value::Armed)])return false;
    for(unsigned i=0;i<4;++i)if(a.bank.dispatchBridge[i]==b.bank.dispatchBridge[i]||!own(second,b.bank.dispatchBridge[i]))return false;
    if(a.bank.workerBridge==b.bank.workerBridge||a.bank.readBridge==b.bank.readBridge||!own(second,b.bank.workerBridge)||!own(second,b.bank.readBridge))return false;
    second_=second;issued_=true;return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
}
