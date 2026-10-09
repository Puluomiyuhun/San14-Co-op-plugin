#include <cstdio>
// Test-only access to exact production planningGraph predicate. The surrounding
// common()/source/stamp checks are not claimed by this isolated regression.
extern "C" __declspec(dllexport) bool BankPlanningGraphRegression(uintptr_t base,uintptr_t rootState,uintptr_t motorState){
    using namespace checkpoint_live_runtime_guards_v2;
    Context c;c.config_.base=base;c.config_.initial.states[0]=rootState;c.config_.initial.states[1]=motorState;
    c.report_.identity_returned=1;c.report_.load_completed=1;c.report_.load_retired=1;
    auto root=*reinterpret_cast<uintptr_t*>(base+0x1fca1e0);auto world=*reinterpret_cast<uintptr_t*>(root+0x85130);
    const auto force=*reinterpret_cast<BYTE*>(world+0x3a);
    if(c.planningGraphLegacy()!=(force==2))return false;
    if(force!=b_warm_profile::Get().target.force||!c.planningGraph())return false;
    *reinterpret_cast<BYTE*>(world+0x3a)=force==2?9:2;
    bool rejected=!c.planningGraph();*reinterpret_cast<BYTE*>(world+0x3a)=force;
    printf("GUARD target=%u corrected_accept=1 other_force_reject=%u legacy_accept=%u\n",unsigned(force),unsigned(rejected),unsigned(c.planningGraphLegacy()));
    return rejected&&c.planningGraph();
}
