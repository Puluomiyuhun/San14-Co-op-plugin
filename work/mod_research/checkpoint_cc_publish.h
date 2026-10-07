#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include "checkpoint_push_bridge.h"
#include "native_storage_publish_core.h"
#ifdef CHECKPOINT_CC_PUBLISH_FIXTURE
#include "native_storage_read_core.h"
#endif

constexpr std::uint64_t FILE_PROBE_MAGIC = 0x53414E1443435031ull;
enum FileProbeState : LONG {
    FP_NEW=0, FP_ARMED=1, FP_CLAIMED=2, FP_READING=3, FP_DRY_DONE=4,
    FP_MATCHED=5, FP_REJECTED=6, FP_CANCELLED=7, FP_UNCERTAIN=8
};
struct CheckpointCcPublishConfig {
    std::uint64_t magic=FILE_PROBE_MAGIC;
    std::uint32_t size=sizeof(CheckpointCcPublishConfig), version=1;
    std::uint32_t mode=0, expectedPid=0; // 0 dry, 1 publish owned staged bytes once through native FileWrite
    std::uint64_t expectedProcessBirth=0, expectedBase=0, expectedUser=0;
    wchar_t localPath[512]{}; // production exact fixed remote path/svdexccSC03.s14
    std::uint64_t reserved[4]{};
#ifdef CHECKPOINT_CC_PUBLISH_FIXTURE
    void* volatile* testSlot=nullptr;
    bool (*testGuard)(void*)=nullptr;
    void* testContext=nullptr;
    native_storage_read::Api testApi{};
    std::uint32_t testSize=0;
    unsigned char testSha256[32]{};
    void* testExpectedOriginal=nullptr;
    native_storage_publish::FileWrite testWrite=nullptr;
    wchar_t testIntentPath[512]{};
    native_storage_publish::Identity testIdentity{};
    unsigned char testOwnerBinding[32]{};
    HANDLE testPublishedEvent=nullptr,testContinueInstall=nullptr;
    std::uint32_t testFailAfterProtect=0;
#endif
};
#ifndef CHECKPOINT_CC_PUBLISH_FIXTURE
static_assert(sizeof(CheckpointCcPublishConfig)==1104);
#endif
struct PublishPart {
    std::uint32_t state=0,osError=0,exceptionCode=0,existsCalls=0,writeAttempts=0,writeReturned=0,nativeWriteReturn=0;
    std::uint32_t intentCreated=0,intentDurable=0,localPinReleased=0,sourceMatched=0,matched=0,publishAttempts=0,sizeCalls=0;
    std::uint64_t writeMethod=0;
    unsigned char sourceSha256[32]{};
    char stage[64]{};
};
static_assert(sizeof(PublishPart)==160);
struct CheckpointCcPublishReport {
    std::uint64_t magic=FILE_PROBE_MAGIC;
    std::uint32_t size=sizeof(CheckpointCcPublishReport), version=1;
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
    PublishPart publish{};
};
static_assert(sizeof(CheckpointCcPublishReport)==680);
extern "C" {
__declspec(dllexport) DWORD WINAPI InstallCheckpointCcPublishProbe(void* config);
__declspec(dllexport) DWORD WINAPI StopCheckpointCcPublishProbe(void*);
// destination must point to writable sizeof(CheckpointCcPublishReport) bytes.
// Diagnostic snapshot only; never invokes storage or modifies game memory.
__declspec(dllexport) DWORD WINAPI GetCheckpointCcPublishReport(void* destination);
}
