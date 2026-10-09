#pragma once
#include "native_storage_read_core.h"

// Explicit overwrite successor of native_storage_publish_core. No discovery,
// Steam import, hook, thread scheduling, target-file lease, or load permission.
namespace b_warm_storage_refresh {
using FileWrite = bool(__fastcall*)(void*, const char*, const void*, std::int32_t);
struct Identity { DWORD volume=0,indexHigh=0,indexLow=0; FILETIME lastWrite{}; };
struct Input {
    // An owned PRIVATE copy with the same basename as the native destination.
    // It MUST NOT be the native destination or a hardlink to it. validateOwner
    // establishes that mapping and the caller's permitted publication boundary.
    const wchar_t* sourcePath=nullptr;
    const wchar_t* intentPath=nullptr;
    const char* basename=nullptr; // Must be exactly svdexccSC03.s14.
    std::uint32_t size=0,previousSize=0;
    unsigned char sha256[32]{},previousSha256[32]{},ownerBinding[32]{};
    Identity sourceIdentity{};
};
struct Api {
    native_storage_read::Api read{};
    FileWrite write=nullptr;
    // Observation-only, no C++ exceptions. Recheck owned namespace, input,
    // exclusive caller/attempt, source != destination, and live write binding.
    // read.validate must also pin FileWrite and storage identity. Neither
    // callback is a fence merely because it returns true.
    bool (*validateOwner)(void*,const Input&)=nullptr;
    void* ownerContext=nullptr;
};
enum class State:unsigned {New,Rejected,IntentDurable,WriteEntered,WrittenUnverified,Matched,Uncertain};
struct Evidence {
    State state=State::New;
    const char* stage="new";
    DWORD osError=0,exceptionCode=0;
    unsigned previousReads=0,writeAttempts=0,writeReturned=0;
    std::int32_t previousSizes[3]{},previousReturns[2]{};
    unsigned char previousHashes[2][32]{},sourceSha256[32]{};
    bool intentCreated=false,intentDurable=false,nativeWriteReturn=false,matched=false;
    bool sourcePinHeldAtWrite=false,nativeLoadAuthorized=false;
    native_storage_read::Evidence readback{};
};
// Existing native destination only: exact old size/hash is required, never
// absence or arbitrary overwrite. Durable CREATE_NEW intent before one write.
// No retry/rollback; uncertain output retains the intent. Caller must not use
// a fresh intent to retry this same attempt. Source remains pinned throughout.
bool Refresh(const Input&,const Api&,Evidence&) noexcept;
}
