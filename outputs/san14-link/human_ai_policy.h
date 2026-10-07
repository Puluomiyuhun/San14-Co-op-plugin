#pragma once
#include <cstdint>

// Candidate policy for the four audited outer AI dispatch wrappers only.
// This header does not install hooks, change player identity, or advance time.
// Hold requires the future adapter to pause progression; never silently drop it.
namespace san14_link {
enum class AiRoute : unsigned { Force, District, Army, ArmyGroup };
enum class AiDecision : unsigned { Native, BypassHumanDecision, Hold };
struct HumanControl {
    std::uint64_t force_mask;
    unsigned main_district[52];
};
struct AiSubject {
    unsigned force;
    unsigned district;
    bool identity_verified;
};
inline AiDecision decide_ai(const HumanControl& control, AiRoute route,
                            AiSubject subject, bool world_bit_16a8_8) {
    constexpr std::uint64_t valid_mask = ((std::uint64_t(1) << 52) - 1) & ~std::uint64_t(1);
    if (!control.force_mask || (control.force_mask & ~valid_mask) ||
        !subject.identity_verified || subject.force < 1 || subject.force > 51 ||
        static_cast<unsigned>(route) > static_cast<unsigned>(AiRoute::ArmyGroup) ||
        world_bit_16a8_8)
        return AiDecision::Hold;
    std::uint64_t main_mask = 0;
    for (unsigned force = 1; force <= 51; ++force) {
        if (control.force_mask & (std::uint64_t(1) << force)) {
            const unsigned district = control.main_district[force];
            if (district < 1 || district > 51 || (main_mask & (std::uint64_t(1) << district)))
                return AiDecision::Hold;
            main_mask |= std::uint64_t(1) << district;
        }
    }
    if (route != AiRoute::Force && (subject.district < 1 || subject.district > 51))
        return AiDecision::Hold;
    if (!(control.force_mask & (std::uint64_t(1) << subject.force)))
        return AiDecision::Native;
    if (route == AiRoute::Force || subject.district == control.main_district[subject.force])
        return AiDecision::BypassHumanDecision;
    // Preserve the native distinction between a player's main and delegated districts.
    return AiDecision::Native;
}
}
