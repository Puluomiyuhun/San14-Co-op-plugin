#pragma once
#include "human_ai_group_resolver.h"
namespace san14_ai_runtime {
using Address=san14_group_resolver::Address;
using Reader=san14_group_resolver::Reader;
using Route=san14_link::AiRoute;
using Decision=san14_link::AiDecision;
enum class Fault:unsigned {None,Configuration,Read,Pointer,Profile,Table,List,HumanBinding,Unstable,Allocation,Group};
struct Request {Address image=0,root=0,object=0;std::uint64_t human_mask=0;Route route=Route::Force;};
struct Subject {
 Fault fault=Fault::None;san14_group_resolver::Error group_fault=san14_group_resolver::Error::None;
 san14_link::HumanControl humans{};san14_link::AiSubject identity{};
 Decision decision=Decision::Hold;unsigned viewer=0;bool option=false,repeated_reads_equal=false;
 std::uint64_t distinct_reads=0;
};
// Rebuild both human main-district identities from the native district list,
// then decode the exact incoming object. No caller-supplied subject identity.
// Equality on a second read is evidence of sampling only, never an atomic fence.
Subject ResolveSubject(const Reader&,const Request&) noexcept;
bool ValidateOuterEntries(const Reader&,Address image) noexcept;
// Local implementation catches SEH read faults. It does not open another process.
bool ReadLocal(void*,Address,void*,std::size_t) noexcept;
}
