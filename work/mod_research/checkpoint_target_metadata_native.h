#pragma once
#include "checkpoint_target_metadata_core.h"

// Leaf adapter only. No hooks, entry points, mode changes, cache registration,
// pending writes, stream ownership, native file opening, or load permission.
namespace checkpoint_target_metadata_native {
using Header=checkpoint_target_metadata::Header;
using OwnedNode=checkpoint_target_metadata::OwnedNode;
using ParseReceipt=checkpoint_target_metadata::ParseReceipt;
struct Access {
    void* context=nullptr;
    // Supplied by caller: currently permitted native callback/thread/build and
    // stable read/allocator boundary. Must independently verify the full EXE
    // hash in the generated profile; this adapter checks exact code fragments.
    // This adapter creates no fence or epoch. Callbacks are observation-only.
    bool (*validateCall)(void*)=nullptr;
    // Must verify candidate remains unpublished/private. May inspect the native
    // ownership graph under the caller's boundary, but must not mutate it.
    bool (*privateNode)(void*,const OwnedNode&)=nullptr;
};
enum class NodeState:unsigned {None,Allocated,Constructing,Private,Releasing,Released,Uncertain};
struct Report {
    bool bound=false,fixtureBinding=false,poisoned=false;
    unsigned parseAttempts=0,copyAttempts=0,releaseAttempts=0,reentrantCalls=0;
    unsigned headerCtorCalls=0,headerParserCalls=0,stringDtorCalls=0,allocateCalls=0,headerCopyCalls=0,freeCalls=0;
    unsigned ctorReturned=0,parserReturned=0,stringDtorReturned=0,allocateReturned=0,copyReturned=0,freeReturned=0;
    DWORD exceptionCode=0,thread=0;
    std::uintptr_t base=0,allocator=0,node=0;
    std::uint64_t allocationTicket=0;
    std::int32_t allocatorGlobalEpoch=0,allocatorThreadEpoch=0;
    std::uintptr_t allocatorBacking=0,oomCallback=0,heapErrorHandler=0;
    NodeState nodeState=NodeState::None;
    const char* stage="new";
    bool fullBufferMatched=false,sourceUnchanged=false,borrowedStreamIntact=false;
    bool nativeLoadAuthorized=false,metadataRegistered=false;
};
struct Functions {
    Header* (__fastcall*headerCtor)(Header*)=nullptr;         // 2E32A0
    bool (__fastcall*headerParse)(Header*,void*)=nullptr;    // 2FAAD0
    Header* (__fastcall*headerCopy)(Header*,const Header*)=nullptr; // 2E2A40
    void (__fastcall*stringDtor)(void*)=nullptr;             // 50D20
    void* (__fastcall*allocate)(std::size_t)=nullptr;        // 3A5820
    void (__fastcall*free)(void*)=nullptr;                  // 3A58B0
};
class Adapter {
public:
    Adapter()=default;
    Adapter(const Adapter&)=delete;
    Adapter& operator=(const Adapter&)=delete;
    // No native calls during Bind. Validates supported EXE/code anchors,
    // pre-initialized allocator identity and OOM callback at+18EB960 (NULL or
    // exact anchored no-op328D20 only); heap error handler+2025F40 must be NULL.
    // Bind and leaf calls must run on nativeThread; one instance/attempt only.
    bool BindProduction(std::uintptr_t base,DWORD nativeThread,const Access&) noexcept;
#ifdef CHECKPOINT_TARGET_METADATA_NATIVE_FIXTURE
    bool BindFixture(DWORD nativeThread,const Access&,const Functions&) noexcept;
#endif
    bool ParseVerifiedBytes(const unsigned char*,std::size_t,Header&,ParseReceipt&) noexcept;
    bool CopyNode(void* head,void* tail,const Header&,OwnedNode&) noexcept;
    bool OwnsNode(const OwnedNode&) noexcept;
    bool ReleaseNode(OwnedNode&) noexcept;
    const Report& GetReport() const noexcept {return report_;}
    // Optional bridge into the frozen core's callback context. Other Adapter
    // callbacks remain null and must be supplied by a separately reviewed caller.
    checkpoint_target_metadata::Adapter LeafCallbacks() noexcept;
    void* CallerContext() const noexcept {return access_.context;}
    // Destructor intentionally does not call native free. Once uncertain or
    // published, only a separately established owner can resolve the node.
private:
    Report report_{};Access access_{};Functions functions_{};
    bool bindAttempted_=false,parseAttempted_=false,copyAttempted_=false,releaseAttempted_=false;
    volatile LONG busy_=0;
    std::uintptr_t allocatorVtable_=0,allocatorAllocate_=0,allocatorFree_=0;
    bool Enter() noexcept;void Leave() noexcept;bool Guard(bool allowPoison=false) noexcept;
    bool NativeCtor(Header*) noexcept;bool NativeParse(Header*,void*,bool&) noexcept;
    bool NativeCopy(Header*,const Header*) noexcept;bool NativeDestroyString(void*) noexcept;
    bool NativeAllocate(void*&) noexcept;bool NativeFree(void*) noexcept;
};
}
