#include "planning_period_session.h"
#include <bcrypt.h>
#include <cstring>
#include <vector>
namespace planning_period_session {
namespace {
void*volatile claimedSession=nullptr;
template<class T>bool nonzero(const T&v){for(auto c:v)if(c)return true;return false;}
bool date(const pp::Date&a,const pp::Date&b){return a.year==b.year&&a.month==b.month&&a.day==b.day&&a.viewer==b.viewer;}
bool valid(const Scope&s){return nonzero(s.room)&&nonzero(s.bindingEpoch)&&nonzero(s.timelineEpoch)&&nonzero(s.scopeDigest)&&
 s.period&&s.period<(1ull<<53)&&s.baseSequence<(1ull<<53)&&s.date.year&&s.date.year<=9999&&
 s.date.month>=1&&s.date.month<=12&&(s.date.day==1||s.date.day==11||s.date.day==21)&&s.date.viewer<51;}
bool same(const Scope&a,const Scope&b){return a.room==b.room&&a.bindingEpoch==b.bindingEpoch&&a.timelineEpoch==b.timelineEpoch&&
 a.scopeDigest==b.scopeDigest&&a.period==b.period&&a.baseSequence==b.baseSequence&&date(a.date,b.date);}
bool binding(const ar::ph::Binding&a,const ar::ph::Binding&b){return a.native.attempt==b.native.attempt&&a.native.attachment==b.native.attachment&&
 a.native.owner_generation==b.native.owner_generation&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
bool nextDate(const pp::Date&a,const pp::Date&b){auto n=a;if(n.day!=21)n.day+=10;else{n.day=1;if(n.month!=12)++n.month;else{n.month=1;++n.year;}}return date(n,b);}
bool healthy(const ar::Report&r){return r.bound&&!r.uncertain&&r.error==ar::Error::None&&!r.active&&!r.queued&&r.submitted==r.completed;}
bool hash(const Scope&s,std::array<unsigned char,32>&out){
 // Versioned fixed-width byte encoding; no struct padding or truncated epoch.
 std::vector<unsigned char>bytes;const char tag[]="san14.local-period-scope.v1";
 bytes.insert(bytes.end(),tag,tag+sizeof(tag)-1);
 for(const auto*p:{&s.room,&s.bindingEpoch,&s.timelineEpoch})bytes.insert(bytes.end(),p->begin(),p->end());
 bytes.insert(bytes.end(),s.scopeDigest.begin(),s.scopeDigest.end());
 auto integer=[&](std::uint64_t n,unsigned width){for(unsigned i=0;i<width;++i)bytes.push_back(static_cast<unsigned char>(n>>(8*i)));};
 integer(s.period,8);integer(s.baseSequence,8);integer(s.date.year,2);integer(s.date.month,1);integer(s.date.day,1);integer(s.date.viewer,1);
 BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE h=nullptr;DWORD size=0,returned=0;bool ok=false;
 if(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)return false;
 if(BCryptGetProperty(algorithm,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&size),sizeof size,&returned,0)>=0&&size){
  std::vector<unsigned char>object(size);
  if(BCryptCreateHash(algorithm,&h,object.data(),size,nullptr,0,0)>=0){
   ok=BCryptHashData(h,bytes.data(),static_cast<ULONG>(bytes.size()),0)>=0&&BCryptFinishHash(h,out.data(),static_cast<ULONG>(out.size()),0)>=0;
   BCryptDestroyHash(h);
  }
 }
 BCryptCloseAlgorithmProvider(algorithm,0);return ok;
}
}
bool MakeBinding(const Scope&s,const checkpoint_native_input::Binding&native,std::uint64_t epoch,ar::ph::Binding&out)noexcept {
 out={};try{if(!valid(s)||!epoch||!nonzero(native.attempt)||!nonzero(native.attachment)||!native.owner_generation)return false;
 ar::ph::Binding b{};b.native=native;b.period=s.period;b.epoch=epoch;if(!hash(s,b.room_input_digest))return false;out=b;return true;
 }catch(...){return false;}
}
bool Session::current(pp::Report&p)noexcept {
 return r_.initialized&&!r_.uncertain&&GetCurrentThreadId()==r_.thread&&pp::Snapshot(*owner_,p)&&p.tracked&&
 p.retired==r_.retired&&binding(p.binding,r_.binding)&&date(p.date,r_.scope.date)&&healthy(p.reward);
}
bool Session::Initialize(a_save_user_owner::Owner&o,a_save_upstream_gate::Owner&g,planning_input_interlock::Controller&c,
 const Scope&s,const ar::Config&config,uintptr_t base,uintptr_t root,uintptr_t world)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {if(r_.initialized||owner_||!valid(s)||s.period!=1||s.baseSequence!=0||!config.sample)__leave;
 ar::ph::Binding expected{};pp::Report p{};
 if(!MakeBinding(s,config.binding.native,1,expected)||!binding(config.binding,expected)||!pp::Snapshot(o,p)||!p.tracked||p.retired||p.serial!=1||
 !binding(p.binding,expected)||!date(p.date,s.date)||!healthy(p.reward)||p.reward.submitted||!pp::CurrentController(o,expected,&c))__leave;
 planning_input_interlock::Report observed{};c.Snapshot(observed);
 if(!observed.initialized||observed.thread!=GetCurrentThreadId()||observed.error!=planning_input_interlock::Error::None||observed.uncertain||
 !g.MatchesOwner(&o,expected.native,base,root,world))__leave;
 if(InterlockedCompareExchangePointer(&claimedSession,this,nullptr)!=nullptr)__leave;
 owner_=&o;gate_=&g;controller_=&c;config_=config;r_.initialized=true;r_.thread=GetCurrentThreadId();r_.scope=s;r_.binding=expected;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Session::Submit(const Scope&s,std::uint64_t sequence,const ar::rw::Command&command)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {pp::Report p{};if(!current(p)||r_.retired||r_.awaitingController||!same(s,r_.scope)||
 sequence>=1ull<<53||sequence!=p.reward.submitted+1||!pp::CurrentController(*owner_,r_.binding,controller_))__leave;
 ok=ar::Submit(*owner_,r_.binding,sequence,command);
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Session::Retire(const Scope&s,pp::Receipt&out)noexcept {out={};AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {pp::Report p{};if(!current(p)||r_.retired||r_.awaitingController||!same(s,r_.scope)||r_.historyCount>=16)__leave;
 pp::Receipt receipt{};if(!pp::Retire(*owner_,*gate_,*controller_,r_.binding,receipt))__leave;
 auto&h=history_[r_.historyCount++];h.scope=r_.scope;h.receipt=receipt;r_.retired=true;out=receipt;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Session::plan(const Scope&s,Next&out)noexcept {out={};pp::Report p{};
 if(!current(p)||!r_.retired||!r_.historyCount||!valid(s)||s.room!=r_.scope.room||s.bindingEpoch!=r_.scope.bindingEpoch||
 s.period!=r_.scope.period+1||!nextDate(r_.scope.date,s.date)||s.baseSequence!=p.reward.completed||r_.binding.epoch==UINT64_MAX)return false;
 for(std::uint64_t i=0;i<r_.historyCount;++i)if(history_[i].scope.timelineEpoch==s.timelineEpoch)return false;
 const auto&receipt=history_[r_.historyCount-1].receipt;
 if(p.serial!=receipt.serial||p.reward.submitted!=receipt.reward.submitted||p.reward.readyRevision!=receipt.reward.readyRevision)return false;
 Next n{};n.scope=s;n.retiredSerial=receipt.serial;if(!MakeBinding(s,r_.binding.native,r_.binding.epoch+1,n.binding))return false;out=n;return true;
}
bool Session::PlanNext(const Scope&s,Next&out)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {ok=plan(s,out);}__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Session::Rebind(const Next&next,const ar::Config&config)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {Next expected{};if(!plan(next.scope,expected)||next.retiredSerial!=expected.retiredSerial||!binding(next.binding,expected.binding)||
 !binding(config.binding,expected.binding)||config.sample!=config_.sample||config.context!=config_.context)__leave;
 if(!pp::Rebind(*owner_,*gate_,config,expected.retiredSerial))__leave;
 // Physical bridges/Save config and cumulative reward counters are untouched.
 config_=config;r_.scope=next.scope;r_.binding=next.binding;r_.retired=false;r_.awaitingController=true;controller_=nullptr;
 pp::Report p{};if(!current(p)||p.reward.completed!=next.scope.baseSequence||!p.reward.readyFence){r_.uncertain=true;__leave;}ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
bool Session::Adopt(planning_input_interlock::Controller&controller)noexcept {AcquireSRWLockExclusive(&lock_);bool ok=false;
 __try {pp::Report p{};if(!current(p)||r_.retired||!r_.awaitingController||!pp::CurrentController(*owner_,r_.binding,&controller))__leave;
 planning_input_interlock::Report c{};controller.Snapshot(c);if(!c.initialized||c.thread!=r_.thread||c.uncertain||c.error!=planning_input_interlock::Error::None||
 c.revision!=p.reward.readyRevision||!c.requested||!p.reward.readyFence)__leave;
 controller_=&controller;r_.awaitingController=false;ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock_);}return ok;
}
void Session::Snapshot(Report&out)noexcept {AcquireSRWLockShared(&lock_);out=r_;ReleaseSRWLockShared(&lock_);}
bool Session::Historical(std::uint64_t serial,Scope&scope,pp::Receipt&receipt)noexcept {scope={};receipt={};AcquireSRWLockShared(&lock_);bool ok=false;
 for(std::uint64_t i=0;i<r_.historyCount;++i)if(history_[i].receipt.serial==serial){scope=history_[i].scope;receipt=history_[i].receipt;ok=true;break;}
 ReleaseSRWLockShared(&lock_);return ok;}
}
