#pragma once
#include <cstdint>
constexpr uint32_t ELIGIBILITY_LIMIT=1024;
struct EligibilityRow { uint32_t id,value; };
struct EligibilityReportData {
    uint32_t magic,version,count,predicateCalls;
    EligibilityRow rows[ELIGIBILITY_LIMIT];
};
static_assert(sizeof(EligibilityReportData)==8208);
using EligibilityPredicate=int(__fastcall*)(uintptr_t);
