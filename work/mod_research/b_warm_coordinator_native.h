#pragma once
#include <Windows.h>
#include <cstdint>
// Local serialized controller ABI. No installation, file writes or room Ready.
namespace b_warm_coordinator {
inline constexpr std::uint64_t Magic=0x53414E1442433031ull;
struct Header {std::uint64_t magic=Magic;std::uint32_t size=0,version=1,operation=0,result=0;unsigned char nonce[32]{};};
struct Prepare {Header header{};std::uint32_t pid=0,reserved=0;std::uint64_t birth=0,first=0,slots[6]{},originals[6]{};};
struct Authorize {Header header{};std::uint64_t second=0;};
struct Observe {Header header{};std::uint32_t stage=0,reserved=0;std::uint64_t first=0,second=0;std::uint32_t firstCompleted=0,secondCompleted=0;};
struct Description {std::uint64_t magic=Magic;std::uint32_t size=sizeof(Description),version=1,prepareSize=sizeof(Prepare),authorizeSize=sizeof(Authorize),observeSize=sizeof(Observe),reserved=0;};
}
extern "C" __declspec(dllexport) DWORD WINAPI DescribeBWarmCoordinator(void*);
extern "C" __declspec(dllexport) DWORD WINAPI PrepareBWarmCoordinator(void*);
extern "C" __declspec(dllexport) DWORD WINAPI AuthorizeBWarmCoordinator(void*);
extern "C" __declspec(dllexport) DWORD WINAPI ObserveBWarmCoordinator(void*);
