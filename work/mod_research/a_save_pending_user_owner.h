#pragma once
#include "a_save_user_owner.h"
namespace a_save_pending_user {
struct Report {std::uint64_t selected=0,claimed=0,returned=0,finally=0,rejected=0;};
bool Snapshot(const a_save_user_owner::Owner*,Report&)noexcept;
}
