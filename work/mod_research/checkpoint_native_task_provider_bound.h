#pragma once
#include "checkpoint_native_task_provider.h"

// Link checkpoint_native_task_provider_bound.cpp INSTEAD OF the frozen
// checkpoint_native_task_provider.cpp. Provider's public ABI/layout is unchanged.
// This is a data observation API, not a hook installer or a scheduler/input lock.
namespace checkpoint_native_task_provider_bound {
struct Binding {std::uint64_t generation=0,attempt=0,epoch=0;};
// Only parent fresh/create/resume/complete points are accepted. Binding, current
// bank, open/error state and processing are checked under the same Provider lock.
// A newer selected bank causes refusal, never fallback or bank reselection.
// Capture authenticity still belongs to the independently validated source.
bool ObserveExpected(checkpoint_native_task_provider::Provider&,const Binding&,
                     const checkpoint_native_task_provider::Capture&) noexcept;
}
