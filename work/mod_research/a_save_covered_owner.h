#pragma once
#include "a_save_user_owner.h"
// Diagnostic observations of the explicitly owned six-state covered-User path.
// No reset, admission, native execution or mutation API.
namespace a_save_covered_owner {
struct Report {std::uint64_t selected=0,claimed=0,returned=0,finally=0,rejected=0;};
bool Snapshot(const a_save_user_owner::Owner*,Report&)noexcept;
}
