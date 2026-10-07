#pragma once
#include "native_storage_read_core.h"

// Fixed CC03 publication only. No process discovery, interface binding, hook,
// scheduler/fence, native save serialization, registration, or world loading.
namespace native_storage_publish {
inline constexpr char TargetName[]="svdexccSC03.s14";
inline constexpr wchar_t TargetWideName[]=L"svdexccSC03.s14";
inline constexpr std::uint32_t TargetSize=274880;
extern const unsigned char TargetSha256[32];
// Actual call3A6AB2: RCX=storage, RDX=name, R8=bytes, R9D=int32 length;
// result is AL (bool), v014 vtable+0x00.
using FileWrite=bool(__fastcall*)(void*,const char*,const void*,std::int32_t);
struct Identity {
    DWORD volume=0,indexHigh=0,indexLow=0;
    FILETIME lastWrite{};
};
struct Input {
    const wchar_t* localPath=nullptr;
    const wchar_t* intentPath=nullptr;
    Identity expectedStage{};
    // Caller-produced binding to its durable exclusive stage receipt, current
    // attachment/attempt, and the unique intent path. All-zero is rejected.
    unsigned char ownerBinding[32]{};
};
struct Api {
    native_storage_read::Api read{};
    FileWrite write=nullptr;
    // Mandatory observation-only callback. Must establish own-stage receipt,
    // exact paths/ownerBinding/current caller boundary, and unique intent path.
    // read.validate must also pin/recheck the FileWrite pointer and v014 object.
    // Neither callback creates a native fence, nor may it throw C++ exceptions.
    bool (*validateStage)(void*,const Input&)=nullptr;
    void* stageContext=nullptr;
};
enum class State:unsigned {New,Rejected,IntentDurable,WriteEntered,WrittenUnverified,Matched,Uncertain};
struct Evidence {
    State state=State::New;
    const char* stage="new";
    DWORD osError=0,exceptionCode=0;
    unsigned existsCalls=0,sizeCalls=0,writeAttempts=0,writeReturned=0,readbackAttempts=0;
    std::int32_t absentSizes[3]{};
    bool nativeWriteReturn=false,intentCreated=false,intentDurable=false;
    bool localPinReleased=false,sourceMatched=false,matched=false;
    bool nativeLoadAuthorized=false,metadataRegistered=false;
    Identity sourceIdentity{};
    unsigned char sourceSha256[32]{};
    native_storage_read::Evidence readback{};
};
// Opens only the caller's existing exact owned stage, pins and hashes it, and
// confirms native absence. CREATE_NEW+FlushFileBuffers claims one durable intent
// before releasing the local deny-write pin and entering FileWrite once.
// No automatic retry/delete/rollback, including false/exception/unknown returns.
// Success requires frozen read core's two complete reads after publication.
// Any new call using the same intent path rejects; caller must never choose a
// new intent path to retry this same stage after a possibly entered write.
bool Publish(const Input&,const Api&,Evidence&) noexcept;
}
