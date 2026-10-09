// Offline extension of the fixed basic layout. No Runtime methods are linked.
#define main ParentFailureBasicLayoutMain
#include "a_save_parent_failure_layout.cpp"
#undef main
using HookReport=checkpoint_load_hook_set::Report;
using HookEntry=checkpoint_load_hook_set::Entry;
using HookBinding=checkpoint_load_hook_set::Binding;
using Stats=CheckpointLoadWorkerBridgeStats;
int main(){
 printf("{\"OwnerReport\":{");FIELD(OR,hooks);FIELD(OR,bridges);END(OR);
 printf(",\"GateReport\":{");FIELD(GR,hooks);FIELD(GR,bridges);END(GR);
 printf(",\"Hooks\":{");FIELD(HookReport,count);FIELD(HookReport,initialized);FIELD(HookReport,entries);FIELD(HookReport,exceptionCode);END(HookReport);
 printf(",\"Entry\":{");FIELD(HookEntry,binding);FIELD(HookEntry,protection);FIELD(HookEntry,lastProtection);FIELD(HookEntry,error);FIELD(HookEntry,known);FIELD(HookEntry,dirty);FIELD(HookEntry,published);FIELD(HookEntry,restored);FIELD(HookEntry,observed);END(HookEntry);
 printf(",\"Binding\":{");FIELD(HookBinding,slot);FIELD(HookBinding,original);FIELD(HookBinding,hook);END(HookBinding);
 printf(",\"Stats\":{");FIELD(Stats,started);FIELD(Stats,native_started);FIELD(Stats,native_returned);FIELD(Stats,before_calls);FIELD(Stats,after_calls);FIELD(Stats,finally_calls);FIELD(Stats,abnormal_exits);FIELD(Stats,cleanup_faults);FIELD(Stats,scope_claims);FIELD(Stats,rejected_claims);FIELD(Stats,active);FIELD(Stats,configured);FIELD(Stats,module_pinned);END(Stats);
 printf("}\n");return 0;
}
