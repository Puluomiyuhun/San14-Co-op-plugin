#pragma once
#include "b_warm_profile.h"
#include "b_warm_storage_refresh_core.h"
#include "checkpoint_live_storage_binding.h"

namespace b_warm_refresh {
inline constexpr std::uint64_t Magic=0x53414E1457524631ull;
struct Config {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Config),version=1;
    b_warm_profile::Config warm{};
    checkpoint_live_storage_binding::Endpoint write{};
    std::uint32_t previousSize=0,reserved=0;
    unsigned char previousSha256[32]{};
    b_warm_storage_refresh::Identity sourceIdentity{},previousTargetIdentity{};
    wchar_t targetPath[512]{},backupPath[512]{},refreshIntent[512]{};
};
enum class State:unsigned {New,Captured,Executing,Matched,Released,Failed};
enum class Error:unsigned {None,AlreadyUsed,Config,Install,Scope,File,WriteBinding,Refresh,TargetReadback,Release,Exception};
struct Report {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Report),version=1;
    std::uint32_t state=0,error=0,captured=0,executeCalls=0,writeAttempts=0,writeReturned=0;
    std::uint32_t intentCreated=0,intentDurable=0,matched=0,leaseHeld=0,leaseReleased=0,releaseCalls=0;
    std::uint32_t previousSize=0,newSize=0,osError=0,exceptionCode=0,previousReads=0,newReads=0;
    unsigned char previousSha256[32]{},newSha256[32]{};
    char stage[64]{},firstFailure[64]{};
    std::uint64_t attempt=0,epoch=0,generation=0;
};
struct Description {
    std::uint64_t magic=Magic;std::uint32_t size=sizeof(Description),version=1;
    std::uint32_t configSize=sizeof(Config),reportSize=sizeof(Report);
    b_warm_profile::Description warm{};
};
// Only the successor CommitGameBefore supplies this API. Its validate callback
// must remain the real scoped guard+Inspector; no remote callback is accepted.
bool Execute(const native_storage_read::Api& authenticated) noexcept;
// Native composition entry; same once-only capture used by the export. It
// neither initializes the warm profile nor installs hooks or authorizes IO.
bool Capture(const Config&) noexcept;
// Only the paired actual retirement path, after sealing and successful six-slot
// restoration, may call this. It does not itself attest those native receipts.
bool ReleaseAfterRetirement() noexcept;
void Snapshot(Report&) noexcept;
}
extern "C" __declspec(dllexport) DWORD WINAPI InstallBWarmRefreshOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI DescribeBWarmRefreshOwner(void*);
extern "C" __declspec(dllexport) DWORD WINAPI GetBWarmRefreshReport(void*);
