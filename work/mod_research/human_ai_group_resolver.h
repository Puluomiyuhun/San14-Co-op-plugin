#pragma once
#include <cstddef>
#include <cstdint>
#include "human_ai_policy.h"
namespace san14_group_resolver {
using Address=std::uint64_t;
// Trusted local memory reader. Return true only after copying every byte.
// It must catch read faults itself; this resolver never dereferences game pointers.
struct Reader {void* context=nullptr;bool(*read)(void*,Address,void*,std::size_t) noexcept=nullptr;};
struct Request {Address image=0,root=0,group=0;san14_link::HumanControl humans{};};
enum class Error:unsigned {None,Config,Read,Pointer,Profile,Table,List,Unstable,Allocation};
struct Result {
 Error error=Error::None;Address first_army=0;unsigned group_id=0,first_army_id=0,members=0;
 unsigned native_district=0,force=0;san14_link::AiSubject subject{};
 san14_link::AiDecision decision=san14_link::AiDecision::Hold;
 std::uint64_t distinct_reads=0;bool repeated_reads_equal=false;
 // Repeated sampling is NOT an atomic snapshot, task fence or installed AI rule.
 bool atomic_snapshot=false,installed_in_game=false;
};
// Caller must authenticate process/build/room binding and own the safe callback
// lifetime. Reads are checked again at return; arbitrary concurrent world changes
// cannot be certified by this alone. Failure/unresolved subject always Hold.
Result Resolve(const Reader&,const Request&) noexcept;
}
