#include "reward_menu_cancel_guard.h"
#include <bcrypt.h>
#include <cstring>
#pragma comment(lib,"bcrypt.lib")
namespace reward_menu_cancel_guard {
namespace {
template<class T>T at(uint64_t p){return *reinterpret_cast<const volatile T*>(p);}
bool token(const char*s){if(!s)return false;for(unsigned i=0;i<32;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;return !s[32];}
bool digest(uint64_t p,ULONG size,const char*expected){BCRYPT_ALG_HANDLE alg=nullptr;unsigned char hash[32]{};if(BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;auto status=BCryptHash(alg,nullptr,0,reinterpret_cast<PUCHAR>(p),size,hash,32);BCryptCloseAlgorithmProvider(alg,0);if(status<0)return false;constexpr char chars[]="0123456789abcdef";char text[65]{};for(unsigned i=0;i<32;++i){text[2*i]=chars[hash[i]>>4];text[2*i+1]=chars[hash[i]&15];}return !memcmp(text,expected,64);}
}
bool Owner::reject()noexcept{++r_.rejected;return false;}
bool Owner::fail(unsigned e)noexcept{if(!r_.error)r_.error=e;r_.phase=Phase::Fault;return reject();}
bool Owner::thread()const noexcept{return nativeThread_.load(std::memory_order_acquire)==GetCurrentThreadId();}
bool Owner::onThread()noexcept{if(thread())return true;foreignRejected_.fetch_add(1,std::memory_order_relaxed);return false;}
bool Owner::identity()const{const auto&c=creation_.binding;return thread()&&at<uint64_t>(c.base+0x1FCA1E0)==c.root&&at<uint64_t>(c.root+0x85130)==c.world&&at<unsigned short>(c.world+0x34)==c.year&&at<unsigned char>(c.world+0x36)==c.month&&at<unsigned char>(c.world+0x37)==c.day&&at<unsigned char>(c.world+0x3A)==c.force;}
bool Owner::shape(unsigned count,bool inspect)const{const auto&c=creation_.binding;auto m=c.base+0x19E7310;if(at<uint64_t>(m+0x10)!=count)return false;auto stack=at<uint64_t>(m+0x20);if(!stack)return false;for(unsigned i=0;i<5;++i)if(at<uint64_t>(stack+i*8)!=c.states[i])return false;return at<unsigned>(c.user+0x470)==2&&(count==5||(at<uint64_t>(stack+40)==creation_.menu&&(!inspect||at<uint64_t>(creation_.menu+0x478)==creation_.layout)));}
bool Owner::empty()const{return at<uint64_t>(creation_.binding.base+0x19E7340)==0;}
bool Owner::source()const{const auto b=creation_.binding.base;return digest(b+0x5CC180,14,"ae14e0835cd49fc022f740e426687b5e39ab694f93cb70ccd585a18bd3305987")&&digest(b+0x4D4AA0,21,"975d27dcceb6332abd5cf31e1e352158294f3363f9bb52e5eaf3b1dde4c8242b")&&digest(b+0x10A60,138,"ce8928a2355c587bc1e999d630485e99a3527d570804453e5ace4682b93b4409");}
bool Owner::graph()const{const auto b=creation_.binding.base;return callback_&&at<uint64_t>(callback_)==b+0x1337E00&&at<uint64_t>(callback_+8)==creation_.menu&&at<uint64_t>(b+0x1337E00+16)==b+0x5CC180&&at<uint64_t>(creation_.menu)==b+0x1331078&&at<uint64_t>(b+0x1331078+0x70)==b+0x4D4AA0;}
bool Owner::Begin(uint64_t generation,const char*id,unsigned relay,unsigned district,uint64_t callback)noexcept{
 if(attempted_.exchange(true)){if(!onThread())return false;return reject();}
 __try{if(!generation||!token(id)||district<1||district>51||!callback)return fail(1);
  if(!reward_menu_creation::Take(generation,creation_))return fail(2);
  const auto&c=creation_.binding;nativeThread_.store(c.thread,std::memory_order_release);callback_=callback;
  if(!creation_.creation_observed||!creation_.activation_observed||creation_.production_permit||!identity()||!shape(6,true)||!empty()||at<uint64_t>(c.root+0xDE40+district*8)!=c.district||!source()||!graph())return fail(3);
  binding_.base=c.base;binding_.root=c.root;binding_.world=c.world;binding_.user=c.user;binding_.state=creation_.menu;binding_.layout=creation_.layout;binding_.thread=c.thread;binding_.relay_rva=relay;binding_.force=c.force;binding_.district=district;binding_.year=c.year;binding_.month=c.month;binding_.day=c.day;binding_.generation=c.generation;memcpy(binding_.menu_id,id,33);
  if(!reward_menu_handoff::Bind(binding_))return fail(4);r_.phase=Phase::Bound;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::ConfirmAndQueue()noexcept{
 if(!onThread())return false;if(r_.phase!=Phase::Bound||r_.choice!=Choice::None)return reject();r_.choice=Choice::Confirm;
 const auto&c=creation_.binding;reward_menu_lifecycle::Config life{};life.base=c.base;life.root=c.root;life.world=c.world;life.menu=creation_.menu;life.layout=creation_.layout;life.thread=c.thread;life.year=c.year;life.month=c.month;life.day=c.day;life.force=c.force;life.generation=c.generation;memcpy(life.states,c.states,sizeof life.states);memcpy(life.menu_id,binding_.menu_id,33);
 if(!confirmation_.Capture(life)||!confirmation_.CloseOnce()||!confirmationPublication_.Begin(c.base,c.base+0x19E7310,confirmationGuard_,confirmation_,c.thread))return fail(6);
 r_.phase=Phase::Queued;return true;
}
bool Owner::CancelNotify(uint64_t generation,uint64_t callback,uint64_t payload)noexcept{
 if(!onThread())return false;if(r_.phase!=Phase::Bound||r_.choice!=Choice::None)return reject();
 __try{
  const auto handoff=reward_menu_handoff::Inspect();
  if(generation!=creation_.binding.generation||callback!=callback_||!identity()||!shape(6,true)||!empty()||!source()||!graph()||handoff.phase!=reward_menu_handoff::Phase::bound||handoff.captures||handoff.takes)return fail(7);
  // Claim before native code. Retirement suppresses later Update calls, but is
  // neither a fabricated capture nor a request to execute a reward.
  r_.choice=Choice::Cancel;r_.phase=Phase::Queued;++r_.notifications;reward_menu_handoff::Retire();
  reinterpret_cast<void(*)(uint64_t,uint64_t*)>(creation_.binding.base+0x5CC180)(callback_,&payload);
  const auto m=creation_.binding.base+0x19E7310,q=at<uint64_t>(m+0x40);
  if(!identity()||!shape(6,true)||!source()||!graph()||at<uint64_t>(m+0x30)!=1||!q||at<unsigned>(q)!=1||at<uint64_t>(q+8))return fail(8);
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::Enter()noexcept{
 if(!onThread())return false;if(r_.choice!=Choice::Cancel||r_.phase!=Phase::Queued||r_.entered)return reject();
 __try{if(!identity()||!shape(6,true))return fail(9);r_.entered=1;r_.active=true;return true;}__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::guarded()noexcept{return thread()&&r_.choice==Choice::Cancel&&r_.active||fail(10);}
bool Owner::Select(uint64_t m,uint64_t menu,uint64_t q,uint64_t end)noexcept{
 if(!onThread())return false;
 if(r_.choice==Choice::Confirm)return thread()&&confirmationGuard_.Select(m,menu,q,end)||fail(11);
 if(!guarded())return false;
 __try{if(r_.phase!=Phase::Queued||copied_||m!=creation_.binding.base+0x19E7310||!q||end<q)return fail(12);
  // Retain the actual copied buffer even if its semantic contents/top are
  // rejected, so the original dispatch can still prove its cleanup on failure.
  copied_=q;++r_.selected;
  if(!identity()||menu!=creation_.menu||!shape(6,true)||!empty()||at<uint64_t>(m+0x38)||at<uint64_t>(m+0x40)||end-q!=16||at<unsigned>(q)!=1||at<uint64_t>(q+8))return fail(12);
  r_.phase=Phase::Consuming;return true;}__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::Finalized(uint64_t m,uint64_t menu)noexcept{
 if(!onThread())return false;
 if(r_.choice==Choice::Confirm)return thread()&&confirmationGuard_.Finalized(m,menu)||fail(13);
 if(!guarded())return false;__try{if(r_.phase!=Phase::Consuming||!identity()||m!=creation_.binding.base+0x19E7310||menu!=creation_.menu||!shape(6,false)||!empty()||at<uint64_t>(creation_.menu+0x478))return fail(14);++r_.finalized;r_.phase=Phase::Finalized;return true;}__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::Freed(uint64_t m,uint64_t menu)noexcept{
 if(!onThread())return false;
 if(r_.choice==Choice::Confirm)return thread()&&confirmationGuard_.Freed(m,menu)||fail(15);
 // menu may already be unmapped; compare only its retained numeric identity.
 if(!guarded())return false;__try{if(r_.phase!=Phase::Finalized||!identity()||m!=creation_.binding.base+0x19E7310||menu!=creation_.menu||!shape(5,false)||!empty())return fail(16);++r_.closed;r_.phase=Phase::Closed;return true;}__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::CopiedStorageReleased(uint64_t p)noexcept{
 if(!onThread())return false;
 if(r_.choice==Choice::Confirm)return thread()&&confirmationGuard_.CopiedStorageReleased(p)||fail(17);
 if(!guarded()||!copied_||p!=copied_||r_.storageReleased)return fail(18);++r_.storageReleased;return true;
}
bool Owner::AfterCleanup()noexcept{
 if(!onThread())return false;
 if(r_.choice==Choice::Confirm)return thread()&&confirmationGuard_.AfterCleanup()||fail(19);
 if(!guarded()||!copied_||r_.storageReleased!=1||r_.boundaries)return fail(20);++r_.boundaries;return r_.phase!=Phase::Fault;
}
bool Owner::Returned()noexcept{
 if(!onThread())return false;
 if(r_.choice==Choice::Confirm){if(!confirmationGuard_.Returned()||!confirmationPublication_.Publish(confirmationGuard_,confirmation_))return fail(21);r_.phase=Phase::Published;return true;}
 if(!guarded()||r_.boundaries!=1||r_.storageReleased!=1)return fail(22);r_.active=false;++r_.returned;
 __try{if(r_.phase!=Phase::Closed||r_.error||r_.notifications!=1||r_.selected!=1||r_.finalized!=1||r_.closed!=1||!identity()||!shape(5,false)||!empty())return fail(23);
  CancelReceipt value{};const auto&c=creation_.binding;value.thread=c.thread;value.year=c.year;value.month=c.month;value.day=c.day;value.force=c.force;value.generation=c.generation;value.world=c.world;value.user=c.user;value.menu=creation_.menu;value.cancelled=value.teardown_observed=true;
  AcquireSRWLockExclusive(&receiptLock_);receipt_=value;cancelPublished_=true;ReleaseSRWLockExclusive(&receiptLock_);r_.phase=Phase::Published;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(99);}
}
bool Owner::ReadCancel(CancelReceipt&out)const noexcept{AcquireSRWLockShared(&receiptLock_);out={};const bool ready=cancelPublished_;if(ready)out=receipt_;ReleaseSRWLockShared(&receiptLock_);return ready;}
bool Owner::ReadConfirmed(reward_menu_closed_publication::Receipt&out)const noexcept{return confirmationPublication_.Read(out);}
}
