#include "reward_menu_selection_guard.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstring>
namespace reward_menu_selection_guard {
namespace {template<class T=uintptr_t>T at(uintptr_t p){return *reinterpret_cast<const volatile T*>(p);}constexpr uintptr_t sites[]={0x68F9FB,0x21F028,0x21EDBF,0x4FABD7};constexpr uintptr_t targets[]={0x21ED10,0x22C450,0x50B690,0x509F50};}
bool Guard::fail(Error e)noexcept{if(r_.error==Error::None)r_.error=e;r_.phase=Phase::Fault;return false;}
bool Guard::thread()const noexcept{return c_.thread==GetCurrentThreadId();}
bool Guard::source(bool installed)const{
 const unsigned char prefix[]={0x48,0x8B,0x12,0x48,0x8B,0x49,0x08};
 if(memcmp(reinterpret_cast<void*>(c_.base+0x4FABD0),prefix,sizeof prefix))return false;
 if(at(c_.base+0x12A7010)!=c_.base+0x2D0350||at(c_.base+0x12A7020)!=c_.base+0x4FABD0||at(c_.base+0x12A7030)!=c_.base+0x4F9D30)return false;
 for(unsigned i=0;i<4;++i){const auto site=c_.base+sites[i];if(at<unsigned char>(site)!=(installed||i<3?0xE8:0xE9))return false;
  const auto target=site+5+at<int32_t>(site+1);if(target!=(installed?c_.relays[i]:c_.base+targets[i]))return false;
  if(installed){const unsigned char j[]={0xFF,0x25,0,0,0,0};if(memcmp(reinterpret_cast<void*>(c_.relays[i]),j,6)||at(c_.relays[i]+6)!=c_.entries[i])return false;}
 }
 return !installed||at<unsigned char>(c_.base+0x4FABDC)==0xC3;
}
bool Guard::identity()const{return at(c_.reward+0x478)==c_.layout&&at(c_.reward+0x50)==c_.task&&c_.task;}
bool Guard::shape(unsigned count)const{
 const auto m=c_.base+0x19E7310,stack=at(m+0x20);if(!stack||at<uint64_t>(m+0x10)!=count)return false;
 for(unsigned i=0;i<5;++i)if(at(stack+i*8)!=c_.states[i])return false;
 return at(stack+40)==c_.reward&&at(m+0x48)==(count==7?selection_:c_.reward)&&(count!=7||at(stack+48)==selection_);
}
bool Guard::callback()const{return selection_&&at(selection_)==c_.base+0x12A6458&&at(selection_+0x10)==c_.base+0x12A7010&&at(selection_+0x18)==c_.reward&&at(selection_+0x48)==selection_+0x10&&at(selection_+0x4A8)==c_.reward+0x480;}
bool Guard::Bind(const Config&c)noexcept{
 if(once_)return fail(Error::Order);once_=true;c_=c;
 __try{
  if(!thread())return fail(Error::Thread);
  if(!c.base||!c.reward||!c.layout||!c.generation||c.menu_id[32])return fail(Error::Identity);
  for(unsigned i=0;i<32;++i)if(!((c.menu_id[i]>='0'&&c.menu_id[i]<='9')||(c.menu_id[i]>='a'&&c.menu_id[i]<='f')))return fail(Error::Identity);
  for(auto p:c.states)if(!p||p==c.reward)return fail(Error::Identity);
  for(unsigned i=0;i<4;++i)if(c.relays[i]<c.base+0x1000||c.relays[i]>=c.base+0x2400000-14||!c.entries[i])return fail(Error::Source);
  if(!c.task||at(c.reward+0x50)!=c.task)return fail(Error::Task);
  if(!identity()||!shape(6)||at<uint64_t>(c.base+0x19E7310+0x30))return fail(Error::Identity);
  if(!source(false))return fail(Error::Source);r_.phase=Phase::Bound;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}
}
bool Guard::BeginCall(uintptr_t descriptor,uintptr_t pc)noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::Bound)return fail(Error::Order);
 if(pc!=c_.base+0x68FA00||!source(true))return fail(Error::Source);
 if(!identity()||!shape(6)||!descriptor||at(descriptor+0x30)!=c_.reward+0x480)return fail(Error::Identity);
 r_.phase=Phase::Calling;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::Created(uintptr_t s,uintptr_t parameters,uintptr_t pc)noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::Calling)return fail(Error::Order);
 if(pc!=c_.base+0x21F02D||!source(true))return fail(Error::Source);
 if(!identity()||!shape(6)||!s||s==c_.reward||!parameters||at(parameters+0x30)!=c_.reward+0x480||at(s+0x4A8)!=c_.reward+0x480)return fail(Error::Selection);
 selection_=s;++r_.created;r_.phase=Phase::Created;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::BeforeWait(uintptr_t reward,uintptr_t pc)noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::Created)return fail(Error::Order);
 if(pc!=c_.base+0x21EDC4||!source(true))return fail(Error::Source);
 const auto m=c_.base+0x19E7310,q=at(m+0x40);
 if(reward!=c_.reward||!identity()||!shape(6)||!callback()||at<uint64_t>(m+0x30)!=1||!q||at<unsigned>(q)!=0||at(q+8)!=selection_)return fail(Error::Selection);
 ++r_.waited;r_.phase=Phase::Waiting;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::Event(uintptr_t reward,uintptr_t event,uintptr_t pc)noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::Waiting)return fail(Error::Order);
 if(pc!=c_.base+0x4FABDC||!source(true))return fail(Error::Source);
 if(reward!=c_.reward||!identity()||!shape(7)||!callback()||at<uint64_t>(c_.base+0x19E7310+0x30)||!event)return fail(Error::Selection);
 if(at<unsigned>(c_.task+0x78)!=1)return fail(Error::Task);
 const auto code=at<unsigned>(event+8);if(code!=0x7FFFFFFD&&code!=0x7FFFFFFE)return fail(Error::Event);
 r_.eventCode=code;++r_.events;r_.phase=Phase::Event;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::WaitReturned(uintptr_t reward,uintptr_t pc)noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::Event||r_.events!=1)return fail(Error::Order);
 if(pc!=c_.base+0x21EDC4||!source(true))return fail(Error::Source);
 if(reward!=c_.reward||!identity()||!shape(6)||at<uint64_t>(c_.base+0x19E7310+0x30))return fail(Error::Identity);
 if(at<unsigned>(c_.reward+0x58)!=(r_.eventCode==0x7FFFFFFD?1u:0u)||at<unsigned>(c_.task+0x78))return fail(Error::Result);
 ++r_.waitReturned;r_.phase=Phase::WaitReturned;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::CallReturned(unsigned value,uintptr_t pc)noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::WaitReturned)return fail(Error::Order);
 if(pc!=c_.base+0x68FA00||!source(true))return fail(Error::Source);
 if(!identity()||!shape(6)||value!=(r_.eventCode==0x7FFFFFFD?1u:0u))return fail(Error::Result);
 ++r_.callReturned;r_.phase=Phase::CallReturned;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::Finish()noexcept{__try{
 if(!thread())return fail(Error::Thread);if(r_.phase!=Phase::CallReturned)return fail(Error::Order);
 if(!source(true))return fail(Error::Source);
 if(!identity()||!shape(6)||at<uint64_t>(c_.base+0x19E7310+0x30)||at<unsigned>(c_.layout+0x170)||at<unsigned>(c_.reward+0x58)!=(r_.eventCode==0x7FFFFFFD?1u:0u))return fail(Error::Result);
 ++r_.completed;r_.phase=Phase::Complete;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception);}}
bool Guard::Take(Receipt&out)noexcept{out={};if(!thread())return false;if(r_.phase!=Phase::Complete||r_.error!=Error::None||r_.events!=1||r_.completed!=1||r_.taken)return false;
 out.generation=c_.generation;out.thread=c_.thread;out.eventCode=r_.eventCode;memcpy(out.menu_id,c_.menu_id,sizeof out.menu_id);out.accepted=r_.eventCode==0x7FFFFFFD;out.selection_return_observed=true;++r_.taken;r_.phase=Phase::Taken;return true;
}
}
