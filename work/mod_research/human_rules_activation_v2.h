#pragma once
#include "human_rules_passthrough_stage.h"
#include "human_ai_runtime_adapter.h"
#include "human_economy_runtime_adapter.h"
namespace human_rules_activation {
enum State:LONG {New,Preparing,Prepared,Sealing,Sealed,Rejected,Faulted};
struct Config {
 unsigned version=1,size=sizeof(Config);std::uint64_t image=0,root=0,world=0;
 unsigned char room[16]{},epoch[16]{},rules_digest[32]{};
 unsigned force[2]{},main_district[2]{};
 unsigned viewer=0,year=0,month=0,day=0;
 // Exact audited native settings, not a receipt or a complete game settings map.
 unsigned income_key5=0,world_option8=0;
};
struct Seal {unsigned version=1,size=sizeof(Seal);unsigned char nonce[32]{},room[16]{},epoch[16]{};};
struct Report {
 LONG state=New;DWORD error=0;std::uint64_t blocked=0;DWORD first_fault_thread=0;
 Config binding{};san14_ai_runtime::Report ai{};san14_economy_runtime::Report income{};
};
}
// Trusted local loader API. Never expose Prepare/Seal/Revoke as room RPCs.
// Prepared sources remain original. Seal is one-time, pre-publication only.
// A separate exclusive OS publisher must recheck this descriptor and the idle
// world before writing the group. Seal itself is NOT a thread/scheduler fence.
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesActivationPrepare(void*);
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesActivationSeal(void*);
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesActivationRevoke(void*);
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesActivationReadReport(void*);
extern "C" __declspec(dllexport) human_rules_stage::Descriptor HumanRulesActivationDescriptor;
extern "C" __declspec(dllexport) void HumanRulesActivationForce(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesActivationDistrict(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesActivationArmy(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesActivationGroup(void*,void*);
extern "C" __declspec(dllexport) int HumanRulesActivationIncome(void*);

// Read-only external installer evidence. Bind module/process/nonce first, then
// require State==Sealed before and after copying Binding + Descriptor under its
// own uncontinued debug event. Faulted revokes installation admission.
extern "C" __declspec(dllexport) volatile LONG HumanRulesActivationState;
extern "C" __declspec(dllexport) human_rules_activation::Config HumanRulesActivationBinding;
