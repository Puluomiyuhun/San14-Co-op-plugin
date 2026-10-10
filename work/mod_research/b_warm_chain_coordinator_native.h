#pragma once
#include "b_warm_chain_handover.h"
namespace b_warm_chain_coordinator {
inline constexpr std::uint64_t Magic=0x53414E1442433331ull;
using Certificate=b_warm_chain::Certificate;
struct Header {std::uint64_t magic=Magic;std::uint32_t size=0,version=1,operation=0,result=0;unsigned char nonce[32]{};};
struct Prepare {Header header{};std::uint32_t pid=0,reserved=0;std::uint64_t birth=0,first=0,slots[6]{},originals[6]{};};
struct Authorize {Header header{};std::uint64_t next=0;std::uint32_t generation=0,reserved=0;};
struct Observe {Header header{};std::uint32_t currentGeneration=0,reserved=0;std::uint64_t banks[3]{};std::uint32_t completed[3]{},certificateCount=0;Certificate certificates[2]{};};
struct Description {std::uint64_t magic=Magic;std::uint32_t size=sizeof(Description),version=1,prepareSize=sizeof(Prepare),authorizeSize=sizeof(Authorize),observeSize=sizeof(Observe),certificateSize=sizeof(Certificate);};
}
extern "C" __declspec(dllexport) DWORD WINAPI DescribeBWarmChainCoordinator(void*);
extern "C" __declspec(dllexport) DWORD WINAPI PrepareBWarmChainCoordinator(void*);
extern "C" __declspec(dllexport) DWORD WINAPI AuthorizeBWarmChainCoordinator(void*);
extern "C" __declspec(dllexport) DWORD WINAPI ObserveBWarmChainCoordinator(void*);
