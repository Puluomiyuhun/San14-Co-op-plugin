"""Scaffold the bounded pilot from the tested one-shot container scheduler."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
h=(ROOT/'reward_container_probe.h').read_text()
h=h.replace('0x53414E1452435031ULL','0x53414E1452455831ULL').replace('0x1414C001','0x1414D001')
h=h.replace('{166,496,769}','{97,759,904}').replace('{94,98,96}','{90,94,92}')
h=h.replace('version,reserved','version,execute').replace('#ifdef REWARD_ELIGIBILITY\n    uintptr_t testPredicate;\n#endif','    uintptr_t testPredicate,testSubmit;')
h=h.replace('5 rejected','4 executed, 5 rejected')
h=h.replace('DWORD readbackIds[3],reserved;', 'DWORD readbackIds[3],reserved;')
# Keep common lifecycle report binary layout; separate execution report below.
h+='''
constexpr uint32_t ELIGIBILITY_LIMIT=1024;
using EligibilityPredicate=int(__fastcall*)(uintptr_t);
using RewardSubmit=int(__fastcall*)(RewardArgs*);
struct RewardExecutionData {
    uint32_t magic,version,execute,predicateCalls,submitCalls,submitReturned,submitResult,postconditions;
    uint32_t loyaltyBefore[3],loyaltyAfter[3],goldBefore,goldAfter,actionsBefore,actionsAfter;
};
static_assert(sizeof(RewardExecutionData)==72);
'''
(ROOT/'reward_execution_pilot.h').write_text(h)
s=(ROOT/'reward_container_probe.cpp').read_text()
s=s.replace('#include "reward_container_probe.h"','#include "reward_execution_pilot.h"')
s=s.replace('RewardProbeReport.error=e;', 'if(!RewardProbeReport.error) RewardProbeReport.error=e;')
s=s.replace('// No order-submit function or network interface. The normal build rehearses one\n// list lifecycle; REWARD_ELIGIBILITY instead calls only the person predicate.', '// Fixed three-person test on checkpoint34 only. No arbitrary command or network interface.')
s=s.replace('#include "reward_probe_fingerprints.h"','#include "reward_probe_fingerprints.h"\n#include "reward_eligibility_fingerprints.h"\n#include "reward_execution_fingerprints.h"')
s=s.replace('static DWORD initialProtection=0;', '''static DWORD initialProtection=0;
static EligibilityPredicate eligibilityPredicate=nullptr;
static RewardSubmit submitReward=nullptr;
static uint32_t executeMode=0;
extern "C" __declspec(dllexport) RewardExecutionData RewardExecutionReport={0x1414D002,1};''')
start=s.index('static bool guard(');end=s.index('static bool poolGuard()')
s=s[:start]+'''#include "reward_eligibility_guard.inc"
#include "reward_execution_guard.inc"

'''+s[end:]
s=s.replace('static bool roundtrip()', 'static bool roundtrip(void* self)')
s=s.replace('    __try { passed=constructAndRead(&args); }', '''    __try {
        passed=constructAndRead(&args);
        // Check the same immutable baseline after allocation, on this callback.
        if(passed) passed=guard(self) && nativePreflight();
        if(passed && executeMode) {
            RewardExecutionReport.submitCalls++;
            int value=submitReward(&args);
            RewardExecutionReport.submitResult=value;
            RewardExecutionReport.submitReturned=1;
            passed=value==1;
            if(!passed) reject(73);
        }
    }''')
start=s.index('#ifdef REWARD_ELIGIBILITY\n#include');end=s.index('static bool restoreSlot()',start)
s=s[:start]+s[end:]
start=s.index('#ifdef REWARD_ELIGIBILITY\n                bool passed=');end=s.index('            }\n        } __except',start)
s=s[:start]+'''                bool passed=nativePreflight() && roundtrip(self);
                bool after=executeMode && RewardExecutionReport.submitCalls?postcheck():guard(self);
                RewardProbeReport.worldGuardUnchanged=executeMode?0:after;
                RewardProbeReport.status=passed && after?(executeMode?4:3):5;
'''+s[end:]
s=s.replace('config.reserved','config.execute>1')
s=s.replace('        hookSlot=reinterpret_cast', '        executeMode=config.execute; RewardExecutionReport.execute=executeMode;\n        hookSlot=reinterpret_cast')
s=s.replace('#ifdef REWARD_ELIGIBILITY\n        eligibilityPredicate=reinterpret_cast<EligibilityPredicate>(config.testPredicate);\n#endif','        eligibilityPredicate=reinterpret_cast<EligibilityPredicate>(config.testPredicate);\n        submitReward=reinterpret_cast<RewardSubmit>(config.testSubmit);')
s=s.replace('#ifdef REWARD_ELIGIBILITY\n        for(const auto& fingerprint:ELIGIBILITY_FINGERPRINTS)', '        for(const auto& fingerprint:ELIGIBILITY_FINGERPRINTS)')
s=s.replace('        eligibilityPredicate=reinterpret_cast<EligibilityPredicate>(gameBase+0x1D4270);\n#endif', '''        for(const auto& fingerprint:EXECUTION_FINGERPRINTS) {
            if(memcmp(reinterpret_cast<void*>(gameBase+fingerprint.rva),fingerprint.bytes,fingerprint.size)) {
                reject(32); RewardProbeReport.status=5; return 32;
            }
        }
        eligibilityPredicate=reinterpret_cast<EligibilityPredicate>(gameBase+0x1D4270);
        submitReward=reinterpret_cast<RewardSubmit>(gameBase+0x1D6DA0);''')
(ROOT/'reward_execution_pilot.cpp').write_text(s)
