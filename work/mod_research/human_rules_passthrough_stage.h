#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
namespace human_rules_stage {
constexpr std::uint64_t Magic=0x31544753524C5548ULL;
struct Config {std::uint64_t magic=Magic;std::uint32_t version=1,size=sizeof(Config);std::uint64_t image=0;};
struct Site {
    std::uint64_t address=0,destination=0,original_target=0;
    std::uint32_t patch_size=0,profile_size=0,protection=0,reserved=0;
    unsigned char expected[128]{},replacement[16]{};
};
struct Descriptor {
    std::uint64_t magic=Magic;std::uint32_t version=1,size=sizeof(Descriptor);
    std::uint32_t pid=0,fixture=0;std::uint64_t birth=0,image=0,module=0,allocation=0;
    unsigned char nonce[32]{};Site sites[6]{};
    // Immutable after state becomes Prepared. Preparing does not publish hooks.
    std::uint32_t site_count=6,policy_enabled=0;
    // External RPM users must see Prepared before AND after copying this
    // descriptor, bind nonce/process/module, and independently check profiles.
    // Magic/nonce alone never means preparation has finished.
    volatile LONG preparation_state=0;std::uint32_t reserved=0;
};
struct Counters {std::uint64_t entered[6]{},exited[6]{},active=0,abnormal=0,unexpected_income_caller=0;};
enum State:LONG {New,Preparing,Prepared,Rejected};
struct Report {LONG state=New;DWORD error=0;Counters counters{};};
}
// Code and trampoline lifetime is resident. No unload, release, reset, native
// business policy, source patching, or permission to run a multiplayer session.
extern "C" __declspec(dllexport) human_rules_stage::Descriptor HumanRulesStageDescriptor;
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesStagePrepare(void*);
extern "C" __declspec(dllexport) void HumanRulesStageSnapshot(human_rules_stage::Report*) noexcept;
extern "C" __declspec(dllexport) void HumanRulesStageForce(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesStageDistrict(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesStageArmy(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesStageGroup(void*,void*);
extern "C" __declspec(dllexport) int HumanRulesStageIncome(void*);
