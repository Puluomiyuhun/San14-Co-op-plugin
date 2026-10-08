#pragma once
#include <windows.h>
#include <cstdint>
// Bootstrap metadata is not room authorization or a scheduler permit. A runtime
// must independently validate the primary thread and its own supported image.
struct BReloadLifecycleBootstrapInfo {
 std::uint32_t size=sizeof(BReloadLifecycleBootstrapInfo),version=1,pid=0,primaryThread=0;
 std::uint64_t imageBase=0,entryPoint=0;std::uint32_t entryByte=0,reserved=0;
};
inline constexpr DWORD BReloadLifecycleBootstrapSuccess=0xB14C0001;
