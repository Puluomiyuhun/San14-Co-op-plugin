#pragma once
#include "a_save_parent_adapter.h"
namespace a_save_repeat_parent {
// Immutable local Runtime wiring only. No network/typed API accepts callbacks.
using Control=bool(*)(void*)noexcept;
bool Bind(a_save_parent_adapter::Adapter&,void*,Control before,Control after,Control cancel)noexcept;
}
