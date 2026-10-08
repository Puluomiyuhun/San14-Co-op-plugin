#pragma once
#include "a_save_user_owner.h"
#include "a_save_early_guard.h"

// ABI-compatible implementation successor: link a_save_report_owner.cpp INSTEAD
// OF a_save_user_owner.cpp. Reuses the immutable User/Save bridge bank and can be
// bound by a_save_action_gate. Never link both Owner implementations.
// CopyArtifact exports only the latest successfully Submitted generation;
// previously copied bytes stay with their caller but older generations cannot
// be copied again under a newer report baseline.
namespace a_save_report_owner {
enum class Boundary:LONG {None,Submit,Entry,After,Storage,Copy};
struct Report {
 bool attached=false;
 std::uint64_t submitRejected=0,entrySuppressed=0,afterRejected=0,storageRejected=0,copyRejected=0;
 Boundary lastBoundary=Boundary::None;
 a_save_early_guard::Decision lastDecision=a_save_early_guard::Decision::NotInitialized;
 bool revoked=false;
 bool fullInputHold=false,reportWriteExclusion=false,saveAuthorized=false,roomReady=false;
};
// The Owner, immutable identities and storage callbacks must remain alive.
// No retry/reset/permission method; this only reports actual negative checks.
bool Snapshot(const a_save_user_owner::Owner*,Report&)noexcept;
}
