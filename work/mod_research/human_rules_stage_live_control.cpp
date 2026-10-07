#include "human_rules_passthrough_stage.h"
#include <cstddef>

// Thread-compatible reporting exports only. The frozen stage continues to own
// preparation, forwarding, counters and lifetime. This file patches no source.
struct LiveInfo {
    std::uint64_t magic = human_rules_stage::Magic;
    std::uint32_t version = 1, size = sizeof(LiveInfo);
    std::uint32_t config_size = sizeof(human_rules_stage::Config);
    std::uint32_t descriptor_size = sizeof(human_rules_stage::Descriptor);
    std::uint32_t report_size = sizeof(human_rules_stage::Report);
    std::uint32_t prepared_offset = offsetof(human_rules_stage::Descriptor, preparation_state);
    std::uint64_t descriptor = reinterpret_cast<std::uint64_t>(&HumanRulesStageDescriptor);
    std::uint64_t prepare = reinterpret_cast<std::uint64_t>(&HumanRulesStagePrepare);
};
static_assert(sizeof(human_rules_stage::Config) == 24);
static_assert(sizeof(human_rules_stage::Descriptor) == 1208);
static_assert(sizeof(human_rules_stage::Report) == 128);
static_assert(sizeof(LiveInfo) == 48);

extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesStageReadReport(void* output) {
    if (!output) return ERROR_INVALID_PARAMETER;
    __try { HumanRulesStageSnapshot(static_cast<human_rules_stage::Report*>(output)); }
    __except(EXCEPTION_EXECUTE_HANDLER) { return GetExceptionCode(); }
    return ERROR_SUCCESS;
}
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesStageDescribeLive(void* output) {
    if (!output) return ERROR_INVALID_PARAMETER;
    __try { *static_cast<LiveInfo*>(output) = LiveInfo{}; }
    __except(EXCEPTION_EXECUTE_HANDLER) { return GetExceptionCode(); }
    return ERROR_SUCCESS;
}
