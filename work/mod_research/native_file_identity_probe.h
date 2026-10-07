#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include "checkpoint_push_bridge.h"
#ifdef NATIVE_FILE_IDENTITY_FIXTURE
#include "native_storage_read_core.h"
#endif

constexpr std::uint64_t FILE_PROBE_MAGIC = 0x53414E1446494431ull;
enum FileProbeState : LONG {
    FP_NEW=0, FP_ARMED=1, FP_CLAIMED=2, FP_READING=3, FP_DRY_DONE=4,
    FP_MATCHED=5, FP_REJECTED=6, FP_CANCELLED=7, FP_UNCERTAIN=8
};
struct NativeFileIdentityConfig {
    std::uint64_t magic=FILE_PROBE_MAGIC;
    std::uint32_t size=sizeof(NativeFileIdentityConfig), version=1;
    std::uint32_t mode=0, expectedPid=0; // default dry; mode1 = one Verify attempt
    std::uint64_t expectedProcessBirth=0, expectedBase=0, expectedUser=0;
    wchar_t localPath[512]{}; // production exact fixed remote path/mppush01.s14
    std::uint64_t reserved[4]{};
#ifdef NATIVE_FILE_IDENTITY_FIXTURE
    void* volatile* testSlot=nullptr;
    bool (*testGuard)(void*)=nullptr;
    void* testContext=nullptr;
    native_storage_read::Api testApi{};
    std::uint32_t testSize=0;
    unsigned char testSha256[32]{};
    void* testExpectedOriginal=nullptr;
    HANDLE testPublishedEvent=nullptr,testContinueInstall=nullptr;
    std::uint32_t testFailAfterProtect=0;
#endif
};
#ifndef NATIVE_FILE_IDENTITY_FIXTURE
static_assert(sizeof(NativeFileIdentityConfig)==1104);
#endif
struct NativeFileIdentityReport {
    std::uint64_t magic=FILE_PROBE_MAGIC;
    std::uint32_t size=sizeof(NativeFileIdentityReport), version=1;
    std::int32_t state=FP_NEW, error=0;
    std::uint32_t mode=0, stopRequested=0, exceptionCode=0, osError=0;
    std::uint64_t base=0, user=0, slot=0, original=0, hook=0;
    std::uint64_t claimCallId=0, caller=0, originalRax=0;
    std::uint32_t installerThread=0, executorThread=0, originalReturned=0, verifyAttempts=0;
    std::uint32_t slotRestored=0, protectionRestored=0, initialProtection=0, observedProtection=0;
    std::uint64_t observedSlot=0;
    std::uint32_t contextCalls=0, existsCalls=0, sizeCalls=0, readCalls=0;
    std::int32_t sizes[3]{}, readReturns[2]{};
    std::uint32_t expectedSize=0, verifiedSize=0, identityMatched=0;
    std::uint32_t localPinReleased=0, callbackActive=0, callbackFaults=0, reentrantClaims=0;
    std::uint64_t storage=0, storageVtable=0, existsMethod=0, sizeMethod=0, readMethod=0;
    unsigned char expectedSha256[32]{}, localSha256[32]{}, nativeSha256[2][32]{};
    char stage[64]{};
    CheckpointPushBridgeStats bridge{};
    std::uint32_t bridgeDrainedSnapshot=0, modulePinned=0;
    std::uint32_t nativeLoadAuthorized=0, fullWorldVerified=0;
};
static_assert(sizeof(NativeFileIdentityReport)==520);
extern "C" {
__declspec(dllexport) DWORD WINAPI InstallNativeFileIdentityProbe(void* config);
__declspec(dllexport) DWORD WINAPI StopNativeFileIdentityProbe(void*);
// destination must point to writable sizeof(NativeFileIdentityReport) bytes.
// Diagnostic snapshot only; never invokes storage or modifies game memory.
__declspec(dllexport) DWORD WINAPI GetNativeFileIdentityReport(void* destination);
}
