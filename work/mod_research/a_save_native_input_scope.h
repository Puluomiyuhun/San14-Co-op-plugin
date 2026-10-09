#pragma once
#include "checkpoint_native_input_pending_adapter.h"
// Only the A scoped inspector calls this after all ordinary pending/layout
// checks. It authenticates current==0 at an owned CApp boundary, or current==
// Game within the already-claimed Game callback. It never changes manager+48.
namespace a_save_native_input_scope {
bool Current(const checkpoint_native_input_pending::Config&,
             checkpoint_native_input_pending::Stage,std::uintptr_t)noexcept;
}
