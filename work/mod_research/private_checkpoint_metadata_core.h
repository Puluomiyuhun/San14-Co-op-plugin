#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstddef>
// Integration core only: no injector, no debugger, no live native-address adapter.
// A reviewed caller must provide exact-build native functions and a strict
// CUserStrategy Update boundary guard. The standalone fixture supplies stubs.
struct PCMString {char data[16];uint64_t size,capacity;};
struct alignas(16) PCMHeader {unsigned char bytes[0x150];};
struct PCMNative {
    void* context;
    bool (*stablePlanning)(void*); // Must re-read full strict state/identity/build/thread guard.
    bool (*fileExists)(void*,const char*);
    const char* (*slotName)(uint32_t,uint32_t,uint32_t);
    void* (*auxCtor)(void*);           // 3A5120, object size 0x38
    void (*auxDtor)(void*);           // 3A56A0
    void* (*streamCtor)(void*,int);   // 3A4FC0, object size 0x98
    void (*streamDtor)(void*);        // 3A55D0
    bool (*open)(void*,const PCMString*,int,int,int,int,int); // 3A90C0
    void (*read)(void*,void*,size_t); // 3A9330
    void (*version)(void*,uint32_t);  // 3A97F0
    bool (*headerRead)(PCMHeader*,void*); // 2FAAD0; true iff stream+50==0
    void (*close)(void*);            // 3A6340
    PCMHeader* (*headerCtor)(PCMHeader*); // 2E32A0
    void (*stringAssign)(void*,const char*,size_t); // 511D0
    void (*stringDtor)(void*);        // 50D20
    void* (*nodeCopy)(void*,void*,void*,const PCMHeader*); // 2E0E80
    void (*heapFree)(void*);          // 3A58B0, same allocator family as native list clear
};
struct PCMConfig {
    bool execute=false;
    uint32_t slot=0; // Only reserved, physically absent CC slots 63..109 are eligible.
    void* manager=nullptr;
    const wchar_t* remoteDirectory=nullptr;
    const wchar_t* targetPath=nullptr;
    const wchar_t* oncePath=nullptr;
    unsigned char expectedSha256[32]{};
    uint64_t expectedSize=0;
    // Snapshot must come from offline native parsing of the SAME pinned SHA.
    // Equality is a header check, never a proof of complete Steam file identity.
    const PCMHeader* expectedParsedHeader=nullptr;
    uint16_t year=203;uint8_t month=8,day=11;
};
enum class PCMStatus {Rejected=1,Dry=2,Registered=3,Uncertain=4};
struct PCMReport {
    PCMStatus status=PCMStatus::Rejected;
    const char* reason="not_started";
    bool intentCreated=false,nodeGameOwned=false;
    bool parsedHeaderSnapshotMatched=false;
    uint64_t node=0;
    unsigned nativeCalls=0;
    unsigned registrationStores=0;
};
PCMReport preparePrivateCheckpointMetadata(const PCMConfig&,const PCMNative&);
