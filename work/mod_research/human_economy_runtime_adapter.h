#pragma once
#include "human_ai_runtime_subject.h"
#include "../../outputs/san14-link/human_economy_policy.h"
namespace san14_economy_runtime {
using Address=san14_ai_runtime::Address;
using Reader=san14_ai_runtime::Reader;
struct HeldCall {void* force=nullptr;Address caller=0;san14_ai_runtime::Subject subject{};};
using HoldHandler=void(*)(void*,const HeldCall&);
struct Config {
 Reader reader{};Address image=0,root=0;san14_link::EconomyRules rules{};
 HoldHandler hold=nullptr;void*hold_context=nullptr;
};
struct Report {bool configured=false,installed=false;std::uint64_t entries=0,native=0,human=0,ai=0,held=0,active=0,exits=0,abnormal=0;};
// One immutable setup before publishing either CALL replacement. The original
// 0x2110B0 remains completely unmodified and is called directly for other callers.
bool Configure(const Config&) noexcept;
void Snapshot(Report&) noexcept;
// Byte recipe only, NOT a publisher. relay must be a permanent nearby RX leaf
// `jmp [rip+0]` relay within rel32 reach. Native caller's return address is kept.
struct CallPatch {Address site=0,caller=0,relay=0;unsigned char expected[5]{},replacement[5]{},relay_bytes[14]{};};
bool PlanCallPatch(unsigned index,Address image,Address relay,CallPatch&) noexcept;
}
extern "C" __declspec(dllexport) int HumanEconomyIncomePredicate(void*force);
extern "C" __declspec(dllexport) bool HumanEconomyConfigure(const san14_economy_runtime::Config*) noexcept;
extern "C" __declspec(dllexport) void HumanEconomySnapshot(san14_economy_runtime::Report*) noexcept;
extern "C" __declspec(dllexport) bool HumanEconomyPlanCallPatch(unsigned,san14_economy_runtime::Address,san14_economy_runtime::Address,san14_economy_runtime::CallPatch*) noexcept;
