#include "reward_menu_session.h"
#include <cstring>
namespace reward_menu_session {
namespace {template<class T>T at(uint64_t p){return *reinterpret_cast<const volatile T*>(p);}bool token(const char*s){if(!s)return false;for(unsigned i=0;i<32;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;return !s[32];}}
bool Owner::fail(unsigned e)noexcept{if(!report_.error)report_.error=e;report_.phase=Phase::Fault;++report_.rejected;return false;}
bool Owner::current()noexcept{return creation_.binding.thread==GetCurrentThreadId()||fail(2);}
bool Owner::Begin(uint64_t generation,const char*id,unsigned relay,unsigned district)noexcept{
 if(attempted_){++report_.rejected;return false;}attempted_=true;
 __try{
  if(!generation||!token(id)||district<1||district>51)return fail(1);
  // Consume provenance ourselves. A caller cannot manufacture an Evidence value.
  if(!reward_menu_creation::Take(generation,creation_))return fail(3);
  report_.creation_taken=true;const auto&c=creation_.binding;
  if(!creation_.creation_observed||!creation_.activation_observed||creation_.production_permit||!current()||at<uint64_t>(c.root+0xDE40+district*8)!=c.district)return fail(4);
  binding_.base=c.base;binding_.root=c.root;binding_.world=c.world;binding_.user=c.user;
  binding_.state=creation_.menu;binding_.layout=creation_.layout;binding_.thread=c.thread;
  binding_.relay_rva=relay;binding_.force=c.force;binding_.district=district;
  binding_.year=c.year;binding_.month=c.month;binding_.day=c.day;binding_.generation=c.generation;
  memcpy(binding_.menu_id,id,33);
  if(!reward_menu_handoff::Bind(binding_))return fail(5);
  report_.handoff_bound=true;report_.phase=Phase::Bound;return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(9);}
}
bool Owner::ConfirmAndQueue()noexcept{
 if(!current()||report_.phase!=Phase::Bound){++report_.rejected;return false;}
 const auto&c=creation_.binding;reward_menu_lifecycle::Config life{};
 life.base=c.base;life.root=c.root;life.world=c.world;life.menu=creation_.menu;life.layout=creation_.layout;
 life.thread=c.thread;life.year=c.year;life.month=c.month;life.day=c.day;life.force=c.force;life.generation=c.generation;
 memcpy(life.states,c.states,sizeof life.states);memcpy(life.menu_id,binding_.menu_id,33);
 // No native close is queued unless the exact menu's real Update has captured
 // a fresh proposal, then transferred it once through the existing handoff.
 if(!life_.Capture(life))return fail(6);
 if(!life_.CloseOnce())return fail(7);
 if(!publication_.Begin(c.base,c.base+0x19E7310,guard_,life_,c.thread))return fail(8);
 report_.phase=Phase::Queued;return true;
}
bool Owner::Select(uint64_t m,uint64_t menu,uint64_t q,uint64_t end)noexcept{return current()&&report_.phase==Phase::Queued&&guard_.Select(m,menu,q,end)||fail(10);}
bool Owner::Finalized(uint64_t m,uint64_t menu)noexcept{return current()&&report_.phase==Phase::Queued&&guard_.Finalized(m,menu)||fail(11);}
bool Owner::Freed(uint64_t m,uint64_t menu)noexcept{return current()&&report_.phase==Phase::Queued&&guard_.Freed(m,menu)||fail(12);}
bool Owner::CopiedStorageReleased(uint64_t storage)noexcept{return current()&&guard_.CopiedStorageReleased(storage)||fail(13);}
bool Owner::AfterCleanup()noexcept{return current()&&guard_.AfterCleanup()||fail(14);}
bool Owner::Returned()noexcept{
 if(!current()||!guard_.Returned())return fail(15);
 if(report_.phase!=Phase::Queued||!publication_.Publish(guard_,life_))return fail(16);
 report_.phase=Phase::Published;return true;
}
bool Owner::Read(reward_menu_closed_publication::Receipt&out)const noexcept{return publication_.Read(out);}
}
