#pragma once
#include "checkpoint_complete_live_owner.h"
#include "checkpoint_dynamic_file_profile.h"
// One immutable profile per resident warm bank. Native slot63/name mapping is
// retained; accepted bytes, dates and the current/source/target identities vary.
namespace b_warm_profile {
inline constexpr std::uint64_t Magic=0x53414E1457504631ull;
struct Date {std::uint16_t year=0;std::uint8_t month=0,day=0;};
struct Identity {std::uint16_t ruler=0;std::uint8_t force=0,district=0;};
struct Profile {
    checkpoint_dynamic_file_profile::Profile file{};
    Date before{},loaded{};Identity source{},target{};
    std::uint8_t currentForce=0,reserved[7]{};
};
static_assert(sizeof(Profile)==96);
struct Config {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Config),version=1;
    Profile profile{};checkpoint_complete_live_owner::Config owner{};
};
struct Description {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Description),version=1;
    std::uint32_t configSize=sizeof(Config),profileSize=sizeof(Profile),reportSize=0,reserved=0;
    checkpoint_complete_live_owner::Description bank{};
};
struct Report {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Report),version=1;
    std::uint32_t configured=0,ready=0,error=0,reserved=0;Profile profile{};
};
bool Validate(const Profile&) noexcept;
bool Capture(const Profile&) noexcept; // setup once; failed attempt is terminal
bool Ready() noexcept;
const Profile& Get() noexcept; // process-lifetime immutable, only after Ready
void Snapshot(Report&) noexcept;
}
extern "C" __declspec(dllexport) DWORD WINAPI DescribeBWarmProfileOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI InstallBWarmProfileOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI GetBWarmProfileReport(void*);
