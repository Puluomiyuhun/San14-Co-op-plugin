// Owned executable only: compile-time layout, never linked into the game DLL.
#include <windows.h>
#include <cstddef>
#include <cstdio>
#define private public
#include "a_save_local_runtime.h"
#undef private
using R=a_save_local_runtime::Runtime;
using C=planning_input_interlock::Controller;
using CR=planning_input_interlock::Report;
using RR=a_reward_save_owner::Report;
using OR=a_save_user_owner::Report;
using GR=a_save_upstream_gate::Report;
using H=a_save_dispatch_host::Host;
using HR=a_save_dispatch_host::Report;
#define FIELD(T,F) printf("\"" #F "\":{\"offset\":%zu,\"size\":%zu},",offsetof(T,F),sizeof(((T*)0)->F))
#define END(T) printf("\"_size\":%zu}",sizeof(T))
int main(){
 printf("{\"Runtime\":{");FIELD(R,c_);FIELD(R,owner_);FIELD(R,gate_);FIELD(R,controller_);FIELD(R,mailbox_);FIELD(R,host_);FIELD(R,parent_);END(R);
 printf(",\"Controller\":{");FIELD(C,c_);FIELD(C,r_);END(C);
 printf(",\"ControllerReport\":{");FIELD(CR,error);FIELD(CR,thread);FIELD(CR,revision);FIELD(CR,gateRevision);FIELD(CR,initialized);FIELD(CR,requested);FIELD(CR,observing);FIELD(CR,observed);FIELD(CR,uncertain);FIELD(CR,reward);FIELD(CR,owner);FIELD(CR,gate);END(CR);
 printf(",\"RewardReport\":{");FIELD(RR,error);FIELD(RR,bound);FIELD(RR,readyFence);FIELD(RR,readyRevision);FIELD(RR,active);FIELD(RR,queued);FIELD(RR,uncertain);END(RR);
 printf(",\"OwnerReport\":{");FIELD(OR,error);FIELD(OR,armed);FIELD(OR,stopped);FIELD(OR,active_scopes);FIELD(OR,save_lane);FIELD(OR,user_hold_requested);END(OR);
 printf(",\"GateReport\":{");FIELD(GR,error);FIELD(GR,armed);FIELD(GR,stopped);FIELD(GR,active);FIELD(GR,requested);FIELD(GR,revision);END(GR);
 printf(",\"Host\":{");FIELD(H,r_);END(H);
 printf(",\"HostReport\":{");FIELD(HR,state);FIELD(HR,thread);FIELD(HR,initialized);FIELD(HR,lease);FIELD(HR,frame);END(HR);
 printf("}\n");return 0;
}
