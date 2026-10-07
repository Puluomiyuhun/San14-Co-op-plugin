#pragma once
#include <cstdint>

// Candidate routing for two audited income-calculation calls to 2110B0.
// No hook is installed by this header. Hold means the future adapter must
// stop before calculation, not silently substitute zero or the native result.
namespace san14_link {
enum class EconomyPredicate : unsigned { NativeLocal, RoomHuman, RoomAI, Hold };
struct EconomyRules {
    std::uint64_t human_force_mask;
    std::uint64_t binding_epoch;
    unsigned version;
    bool shared_settings_verified;
    bool native_profile_verified;
};
struct EconomySubject {
    unsigned force_id;
    unsigned local_viewer_id;
    std::uint64_t binding_epoch;
    bool identity_verified;
};
inline EconomyPredicate economy_predicate(const EconomyRules& rules,
                                          std::uint32_t caller_return_rva,
                                          EconomySubject subject) {
    // Unknown callers retain the original local-player predicate. They are
    // unadapted, not certified economic paths. In particular, keep UI local.
    if (caller_return_rva != 0x28DE76 && caller_return_rva != 0x28DAAA)
        return EconomyPredicate::NativeLocal;
    constexpr std::uint64_t valid = ((std::uint64_t(1) << 52) - 1) & ~std::uint64_t(1);
    unsigned players = 0;
    for (auto bits = rules.human_force_mask; bits; bits &= bits - 1) ++players;
    if (rules.version != 1 || !rules.binding_epoch ||
        rules.binding_epoch != subject.binding_epoch ||
        !rules.shared_settings_verified || !rules.native_profile_verified ||
        (rules.human_force_mask & ~valid) || players != 2 ||
        !subject.identity_verified || subject.force_id < 1 || subject.force_id > 51 ||
        subject.local_viewer_id < 1 || subject.local_viewer_id > 51 ||
        !(rules.human_force_mask & (std::uint64_t(1) << subject.local_viewer_id)))
        return EconomyPredicate::Hold;
    return (rules.human_force_mask & (std::uint64_t(1) << subject.force_id))
        ? EconomyPredicate::RoomHuman : EconomyPredicate::RoomAI;
}
}
