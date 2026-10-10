#include "reward_menu_lifecycle.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstring>
namespace reward_menu_lifecycle {
namespace {template<class T>T at(uint64_t p){return *reinterpret_cast<const volatile T*>(p);}}
bool Owner::thread()const noexcept{return c_.thread==GetCurrentThreadId();}
bool Owner::fail(unsigned error)noexcept{if(!r_.error)r_.error=error;r_.phase=Phase::Fault;return false;}
bool Owner::identity()const{return thread()&&at<uint64_t>(c_.base+0x1FCA1E0)==c_.root&&at<uint64_t>(c_.root+0x85130)==c_.world&&at<uint16_t>(c_.world+0x34)==c_.year&&at<uint8_t>(c_.world+0x36)==c_.month&&at<uint8_t>(c_.world+0x37)==c_.day&&at<uint8_t>(c_.world+0x3A)==c_.force;}
bool Owner::empty()const{auto m=c_.base+0x19E7310;return at<uint64_t>(m+0x30)==0;}
bool Owner::shape(unsigned count,bool inspectMenu)const{
 auto m=c_.base+0x19E7310;if(at<uint64_t>(m+0x10)!=count)return false;auto stack=at<uint64_t>(m+0x20);if(!stack)return false;
 for(unsigned i=0;i<5;++i)if(at<uint64_t>(stack+i*8)!=c_.states[i])return false;
 if(at<unsigned>(c_.states[4]+0x470)!=2)return false;
 return count==5||(!inspectMenu?at<uint64_t>(stack+40)==c_.menu:at<uint64_t>(stack+40)==c_.menu&&at<uint64_t>(c_.menu+0x478)==c_.layout);
}
bool Owner::Capture(const Config&c)noexcept{
 if(attempted_){++r_.rejected;return false;}attempted_=true;c_=c;
 __try{
  if(!c.base||!c.root||!c.world||!c.menu||!c.layout||!c.generation||!identity()||!shape(6,true)||!empty())return fail(1);
  for(auto p:c.states)if(!p||p==c.menu)return fail(1);
  if(!reward_menu_handoff::TakeProposal(c.menu_id,c.generation,p_)||p_.force!=c.force)return fail(2);
  // Retire never closes the menu; it retains interception and rejects any new take.
  reward_menu_handoff::Retire();r_.phase=Phase::Captured;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
bool Owner::CloseOnce()noexcept{
 if(r_.phase!=Phase::Captured){++r_.rejected;return false;}
 __try{
  if(!identity()||!shape(6,true)||!empty())return fail(3);
  // Claim before entering native code: an exception or reentry cannot enqueue again.
  r_.phase=Phase::Queued;++r_.queued;reinterpret_cast<void(*)(uint64_t)>(c_.base+0x10A60)(c_.base+0x19E7310);
  auto m=c_.base+0x19E7310,q=at<uint64_t>(m+0x40);
  if(!identity()||!shape(6,true)||at<uint64_t>(m+0x30)!=1||!q||at<unsigned>(q)!=1||at<uint64_t>(q+8)!=0)return fail(3);
  return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
bool Owner::BeforeConsume(uint64_t manager,uint64_t top,uint64_t request,uint64_t end)noexcept{
 __try{
  if(r_.phase!=Phase::Queued||!identity()||manager!=c_.base+0x19E7310||top!=c_.menu||!shape(6,true)||!empty()||
   at<uint64_t>(manager+0x38)||at<uint64_t>(manager+0x40)||!request||end<request||end-request!=16||at<unsigned>(request)!=1||at<uint64_t>(request+8))return fail(4);
  ++r_.selected;r_.phase=Phase::Consuming;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
bool Owner::AfterFinalize(uint64_t manager,uint64_t top)noexcept{
 __try{
  if(r_.phase!=Phase::Consuming||!identity()||manager!=c_.base+0x19E7310||top!=c_.menu||!shape(6,false)||!empty()||at<uint64_t>(c_.menu+0x478))return fail(5);
  ++r_.finalized;r_.phase=Phase::Finalized;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
bool Owner::AfterAllocator(uint64_t manager,uint64_t old_top)noexcept{
 __try{
  // The allocator has returned. Only compare the saved numeric menu address.
  if(r_.phase!=Phase::Finalized||!identity()||manager!=c_.base+0x19E7310||old_top!=c_.menu||!shape(5,false)||!empty())return fail(6);
  ++r_.closed;r_.phase=Phase::Closed;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
bool Owner::TakeClosed(ClosedTicket&out)noexcept{
 out={};if(r_.phase!=Phase::Closed){++r_.rejected;return false;}
 __try{if(!identity()||!shape(5,false)||!empty())return fail(7);out.proposal=p_;out.teardown_observed=true;++r_.taken;r_.phase=Phase::Taken;return true;}
 __except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
}
