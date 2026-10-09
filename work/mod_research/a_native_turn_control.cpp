#include "a_native_turn_control.h"
namespace a_native_turn {
namespace {a_save_user_owner::Owner*owner=nullptr;a_save_upstream_gate::Owner*gate=nullptr;
 void*oc=nullptr,*gc=nullptr;detail::Invoke of=nullptr,gf=nullptr;volatile LONG running=0;}
namespace detail {
bool RegisterOwner(a_save_user_owner::Owner*o,void*c,Invoke f)noexcept {if(owner||!o||!c||!f)return false;owner=o;oc=c;of=f;return true;}
bool RegisterGate(a_save_upstream_gate::Owner*g,void*c,Invoke f)noexcept {if(gate||!g||!c||!f)return false;gate=g;gc=c;gf=f;return true;}
bool OwnerCall(a_save_user_owner::Owner*o,const Call&c)noexcept{return o==owner&&of&&of(oc,c);}
}
bool Running()noexcept{return InterlockedCompareExchange(&running,0,0)!=0;}
bool Transition(a_save_upstream_gate::Owner&g,const Call&c)noexcept {
 if(&g!=gate||!gf||!c.serial)return false;
 if(c.action==Action::Begin){if(Running())return false;}
 else if(!Running())return false;
 if(!gf(gc,c))return false;
 if(c.action==Action::Begin)InterlockedExchange(&running,1);
 else if(c.action==Action::End)InterlockedExchange(&running,0);
 return true;
}
}
