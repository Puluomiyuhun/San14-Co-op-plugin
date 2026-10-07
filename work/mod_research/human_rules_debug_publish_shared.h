#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
struct Manifest {
 std::uint64_t magic, owned_break, sites[6], hooks[6], counter, running, busy;
};
constexpr std::uint64_t Magic=0x504255444c555248;
