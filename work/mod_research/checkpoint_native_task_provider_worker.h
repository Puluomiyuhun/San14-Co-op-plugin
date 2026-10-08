#pragma once
#include "checkpoint_native_task_provider_bound.h"
// Replaces checkpoint_native_task_provider_bound.cpp with the worker successor;
// Provider ABI and previous bound-parent API stay unchanged. Never link both.
namespace checkpoint_native_task_provider_worker {
// Root/generic task entry, return, done, yield only. Atomic expected-bank record
// lookup is independent of current_ so a retained old worker can finish safely.
// This interface authenticates attribution, not Capture source or installation.
bool ObserveExpected(checkpoint_native_task_provider::Provider&,
    const checkpoint_native_task_provider_bound::Binding&,
    const checkpoint_native_task_provider::Capture&) noexcept;
}
