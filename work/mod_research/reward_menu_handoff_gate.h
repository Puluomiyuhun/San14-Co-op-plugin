// Local native source component only. No installer, process lookup or permit.
#pragma once
#include <cstdint>
namespace reward_menu_handoff {
enum class Phase : uint32_t { unbound, bound, pending, taken, fault, retired };
enum class Error : uint32_t { none, bad_config, already_bound, source, thread, identity, draft, decode, wrong_claim, consumed, retired };
struct Binding {
    uint64_t base=0, root=0, world=0, user=0, state=0, layout=0;
    uint32_t thread=0, relay_rva=0, force=0, district=0, year=0, month=0, day=0;
    uint64_t generation=0;
    char menu_id[33]{};
};
struct Proposal {
    uint32_t version=1, force=0, district=0, funding_city=0, count=0;
    uint32_t officers[16]{};
    uint64_t generation=0;
    char menu_id[33]{};
};
struct Report {
    Phase phase=Phase::unbound;Error error=Error::none;
    Error last_rejection=Error::none;uint64_t rejections=0;
    uint64_t calls=0, captures=0, takes=0;
    bool proposal_was_taken=false;
    // Intentionally false: this component has no production lifetime/install owner.
    bool production_permit=false;
};
bool Bind(const Binding&) noexcept;
bool TakeProposal(const char* menu_id,uint64_t generation,Proposal&) noexcept;
void Retire() noexcept; // Leaves call suppression in place. Never closes/unhooks UI.
Report Inspect() noexcept;
}
extern "C" int RewardMenuHandoffGate_Entry(uint64_t state) noexcept;
