#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
namespace human_rules_hook {
using Address=std::uint64_t;
struct Config {Address image=0;void*ai_entries[4]{};void*economy_entry=nullptr;};
struct Prepared {void*ai_originals[4]{};void*economy_relays[2]{};void*allocation=nullptr;};
struct Report {
 bool prepared=false,installed=false,restored=false,failed=false,uncertain=false;
 bool game_publication_available=false;unsigned written_mask=0,publication_attempts=0;
 DWORD error=0;std::uint64_t registered_executions=0,active_executions=0;
};
// Known six profiles only. Prepares permanent nearby RX trampolines and registers
// actual x64 unwind metadata. Does not modify source code. One attempt, no reset.
bool Prepare(const Config&,Prepared&) noexcept;
void Snapshot(Report&) noexcept;
// REAL cooperative shared execution lease, restricted to a MEM_PRIVATE owned
// fixture image. Every test invocation must enter BEFORE any of the six sources
// and leave after all nested/native calls unwind. No bool is a publication fence.
bool EnterOwnedExecution() noexcept;
void LeaveOwnedExecution() noexcept;
// Obtains exclusive lock, drains those registered executions, then checks/writes/
// flushes/restores protection under that lock. MEM_IMAGE (game executable) is
// rejected: no claim that this cooperative test gate covers game's native jobs.
bool PublishCooperativeOwnProcess() noexcept;
bool RestoreCooperativeOwnProcess() noexcept;
}
extern "C" __declspec(dllexport) bool HumanRulesPrepare(const human_rules_hook::Config*,human_rules_hook::Prepared*) noexcept;
extern "C" __declspec(dllexport) void HumanRulesSnapshot(human_rules_hook::Report*) noexcept;
extern "C" __declspec(dllexport) bool HumanRulesEnterOwnedExecution() noexcept;
extern "C" __declspec(dllexport) void HumanRulesLeaveOwnedExecution() noexcept;
extern "C" __declspec(dllexport) bool HumanRulesPublishCooperativeOwnProcess() noexcept;
extern "C" __declspec(dllexport) bool HumanRulesRestoreCooperativeOwnProcess() noexcept;
#ifdef HUMAN_RULES_OWN_PROCESS_FIXTURE
extern "C" __declspec(dllexport) bool HumanRulesFixtureFault(unsigned slot,unsigned mode) noexcept;
#endif
