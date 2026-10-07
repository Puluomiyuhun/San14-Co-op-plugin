#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdint>
// One canonical value, copied into each retained observer before publication.
// Only the verified native slot/name mapping is supported. File bytes vary.
namespace checkpoint_dynamic_file_profile {
inline constexpr char SupportedName[]="svdexccSC03.s14";
inline constexpr std::uint32_t SupportedSlot=63;
// Match native_storage_read::Verify's bounded allocation/read contract.
inline constexpr std::uint32_t MaximumSize=16u*1024u*1024u;
inline constexpr size_t NameBytes=sizeof SupportedName;
struct Profile {
    char name[32]{};
    std::uint32_t slot=0,size=0;
    unsigned char sha256[32]{};
};
static_assert(sizeof(Profile)==72);
bool Validate(const Profile&) noexcept;
bool Capture(const Profile*,Profile&) noexcept;
bool Same(const Profile&,const Profile&) noexcept;
bool Equal(const Profile&,const Profile&) noexcept;
// Observation/data validation only. No input exclusion, native authority,
// publication, retries or lifetime management are granted by these functions.
}
