#pragma once
#include "human_ai_runtime_adapter.h"
#include "human_economy_runtime_adapter.h"
#include "human_rules_hook_transport.h"
namespace human_rules_policy {
struct Config {
 unsigned version=1,size=sizeof(Config);
 std::uint64_t image=0,root=0,world=0,room_epoch=0;
 unsigned force[2]{},main_district[2]{};
 // Trusted local caller supplies an already verified room settings receipt.
 // Nonzero digest is binding data, NOT proof of its external provenance.
 unsigned char settings_receipt[32]{};
 san14_ai_runtime::HoldHandler ai_hold=nullptr;
 san14_economy_runtime::HoldHandler income_hold=nullptr;
 void* hold_context=nullptr;
};
enum State:LONG {New,Preparing,Prepared,Rejected};
struct Report {
 LONG state=New;bool active=false,production_activation_available=false;
 DWORD error=0;std::uint64_t room_epoch=0,image=0,root=0,world=0;
 san14_ai_runtime::Report ai{};san14_economy_runtime::Report income{};
};
}
extern "C" __declspec(dllexport) DWORD WINAPI HumanRulesPolicyPrepare(void*);
extern "C" __declspec(dllexport) void HumanRulesPolicySnapshot(human_rules_policy::Report*) noexcept;
extern "C" __declspec(dllexport) void HumanRulesPolicyForce(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesPolicyDistrict(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesPolicyArmy(void*,void*);
extern "C" __declspec(dllexport) void HumanRulesPolicyGroup(void*,void*);
extern "C" __declspec(dllexport) int HumanRulesPolicyIncome(void*);
#ifdef HUMAN_RULES_POLICY_FIXTURE
// All own-process calls must hold the real shared execution lease. Activation
// obtains its exclusive counterpart. None of these exports exists in production.
extern "C" __declspec(dllexport) bool HumanRulesPolicyFixtureEnter();
extern "C" __declspec(dllexport) void HumanRulesPolicyFixtureLeave();
extern "C" __declspec(dllexport) bool HumanRulesPolicyFixtureActivate(std::uint64_t);
#endif
