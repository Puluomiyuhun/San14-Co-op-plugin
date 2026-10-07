// Separate compile-time query mode: no construction, allocation or reward call.
// Reuses the already-tested one-shot update scheduling, not a new game thread.
#include "reward_eligibility_probe.h"
#ifndef REWARD_FIXTURE
#include "reward_eligibility_fingerprints.h"
#endif
extern "C" __declspec(dllexport) EligibilityReportData RewardEligibilityReport={0x1414E001,1};
static EligibilityPredicate eligibilityPredicate=nullptr;

#include "reward_eligibility_guard.inc"

static bool queryRewardEligibility() {
    auto root=at<uintptr_t>(gameBase+0x1FCA1E0);
    if(!eligibilityObjectGuard(root)) return false;
    uintptr_t people[ELIGIBILITY_LIMIT]{};
    uint32_t count=0;
    bool seen[6000]{};
    if(!readList(root+0xF8,0x123F448,0x201D3A0,0x14000,people,&count) || !count) return reject(60);
    // Finish validating the whole batch before making the first native call.
    for(unsigned i=0;i<count;i++) {
        auto person=people[i]; auto id=at<uint16_t>(person+0x10);
        if(at<uintptr_t>(person)!=gameBase+0x12A00D0 || !id || id>=6000 || seen[id] ||
           at<uintptr_t>(root+0x148+id*8)!=person) return reject(63);
        seen[id]=true;
        RewardEligibilityReport.rows[i].id=id;
    }
    RewardEligibilityReport.count=count;
    for(unsigned i=0;i<count;i++) {
        RewardEligibilityReport.predicateCalls++;
        int value=eligibilityPredicate(people[i]);
        if(value!=0 && value!=1) return reject(64);
        RewardEligibilityReport.rows[i].value=static_cast<uint32_t>(value);
    }
    return true;
}
