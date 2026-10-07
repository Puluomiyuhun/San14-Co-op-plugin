#pragma once
#include "native_storage_read_core.h"
#include <array>
#include <string>

// Research integration core: no process discovery, addresses, DLL or installer.
// There is deliberately no production Adapter implementation and no load API.
namespace checkpoint_target_metadata {
inline constexpr char TargetName[]="mppush01.s14";
inline constexpr unsigned TargetSize=274880;
extern const unsigned char TargetSha256[32];
struct alignas(16) Header { unsigned char bytes[0x150]{}; };
extern const Header ExpectedParsedHeader;

// Acquire uses the existing complete native-read verifier. The local file pin
// and immutable matching bytes remain owned by this object until destruction.
// A released earlier read-probe report cannot be substituted for this object.
class VerifiedTarget {
public:
    // Single owner/thread; do not race Acquire/Intact/destruction. Keep this
    // object alive through Registration and its final validation boundary.
    bool Acquire(const wchar_t* path,const native_storage_read::Api&) noexcept;
    bool Intact() const noexcept;
    const unsigned char* Bytes() const noexcept { return lease_.bytes.data(); }
    std::size_t Size() const noexcept { return lease_.bytes.size(); }
    const std::wstring& Path() const noexcept { return path_; }
    const native_storage_read::Evidence& Evidence() const noexcept { return evidence_; }
private:
    native_storage_read::Lease lease_;
    native_storage_read::Evidence evidence_{};
    BY_HANDLE_FILE_INFORMATION identity_{};
    std::wstring path_;
    bool attempted_=false,verified_=false;
};

// Supplied by a reviewed native adapter while holding its serialization fence.
// Mode0 must ALREADY have been established by the native lifecycle. This core
// must not switch mode, clear metadata, stop the worker, or manufacture a fence.
struct Boundary {
    void* manager=nullptr;
    DWORD thread=0;
    std::uint64_t attachment=0,attempt=0,cacheGeneration=0,fence=0;
};
struct ParseReceipt {
    const unsigned char* source=nullptr;
    std::size_t length=0,consumed=0;
    unsigned nativeFileOpens=0; // must be 0: use precisely the leased buffer
    unsigned streamError=0;
};
struct OwnedNode {
    void* pointer=nullptr;
    std::uint64_t allocation=0; // adapter-owned allocation ticket, never guessed
};
enum class Presence {Absent,Present,Unknown};
struct Adapter {
    void* context=nullptr;
    bool (*boundary)(void*,const Boundary&)=nullptr;
    // boundary validates build/thread/attachment/generation/fence plus native
    // quiescence. It is not a substitute for owning a true serial boundary.
    // boundary/nativePresence/slotName/ownsNode are observation-only: they must
    // not publish, destroy or transfer ownership of a private allocation.
    Presence (*nativePresence)(void*,const char*)=nullptr;
    bool (*slotName)(void*,unsigned,char out[16])=nullptr;
    // Returns a normalized POD header (empty SSO filename). Adapter owns and
    // destroys any temporary native stream/header; it must never free source.
    bool (*parseVerifiedBytes)(void*,const unsigned char*,std::size_t,Header&,ParseReceipt&)=nullptr;
    // Adapter must publish allocation ticket BEFORE fallible construction; it
    // must use the native allocator/copy family. Ownership remains private.
    bool (*copyNode)(void*,void* head,void* tail,const Header&,OwnedNode&)=nullptr;
    bool (*ownsNode)(void*,const OwnedNode&)=nullptr;
    bool (*releaseNode)(void*,OwnedNode&)=nullptr;
    // All callbacks return normally; exceptions are treated as uncertainty,
    // not evidence that a native side effect did not happen.
};
struct Config {
    Boundary binding{};
    unsigned slot=63; // positive physically absent CC slots 63..109 only
    const wchar_t* intentPath=nullptr; // new scope; CREATE_NEW + FlushFileBuffers
#ifdef CHECKPOINT_TARGET_METADATA_FIXTURE
    // Own-process fault injection ONLY. Absent from production Config/code.
    int fixtureFailAfterStore=-1;
#endif
};
enum class Status {New,Rejected,Registered,Invalidated,Uncertain};
struct Report {
    Status status=Status::New;
    const char* reason="new";
    bool intentDurable=false,headerMatched=false,nodeTransferred=false;
    bool privateNodeReleased=false,leaseHeld=false;
    unsigned parserCalls=0,allocationCalls=0,registrationStores=0;
    bool commitEntered=false;
    unsigned storeAttempt=0; // 1=count,2=head.prev,3=tail.next,4=table; 0=none
    // Retained before the commit boundary, even if only a prefix is published.
    // A crash can happen between an actual store and its counter increment:
    // registrationStores is a completed milestone count, never rollback advice.
    // node identifies the candidate; nodeTransferred means all 4 stores reached
    // their completion markers, not that post-commit validation succeeded.
    std::uintptr_t node=0;
    std::uint64_t allocationTicket=0;
    // Never means ready to load: future native read bytes and the mode0/UI
    // lifecycle still need their own identity and serial-boundary proofs.
    bool loadAuthorized=false;
};
class Registration {
public:
    Registration()=default;
    Registration(const Registration&)=delete;
    Registration& operator=(const Registration&)=delete;
    Report Register(const Config&,const Adapter&,VerifiedTarget&) noexcept;
    // Read-only, sticky invalidation. Requires the SAME live lease and binding.
    // Detects native clear/rebuild, table/list/header changes and stale epoch.
    Report Validate(const Config&,const Adapter&,VerifiedTarget&) noexcept;
    const Report& GetReport() const noexcept { return report_; }
private:
    Report report_{};
    Boundary binding_{};
    unsigned slot_=0;
    std::uintptr_t head_=0,node_=0;
    std::array<unsigned char,32> graphDigest_{};
    const VerifiedTarget* target_=nullptr;
    Adapter adapter_{};
    bool attempted_=false;
};
}
