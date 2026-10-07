#include "checkpoint_target_metadata_native.h"
#include <cstring>
#include <intrin.h>
namespace checkpoint_target_metadata_native { namespace {
#include "checkpoint_target_metadata_native_anchors.inc"
volatile LONG64 nextAllocationTicket=0;
template<class T>T at(std::uintptr_t p){T v{};std::memcpy(&v,reinterpret_cast<void*>(p),sizeof v);return v;}
template<class T>void put(void*p,std::size_t offset,T v){std::memcpy(static_cast<unsigned char*>(p)+offset,&v,sizeof v);}
bool span(std::uintptr_t p,std::size_t n,bool executable=false){
    if(p<0x10000||n>SIZE_MAX-p)return false;
    for(auto end=p+n;p<end;){MEMORY_BASIC_INFORMATION m{};
        if(!VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)||m.State!=MEM_COMMIT||(m.Protect&(PAGE_GUARD|PAGE_NOACCESS)))return false;
        if(executable){unsigned prot=m.Protect&0xff;if(m.Type!=MEM_IMAGE||(prot!=PAGE_EXECUTE&&prot!=PAGE_EXECUTE_READ&&prot!=PAGE_EXECUTE_READWRITE&&prot!=PAGE_EXECUTE_WRITECOPY))return false;}
        auto next=std::uintptr_t(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next;
    }return true;
}
bool exactCode(std::uintptr_t base){for(const auto&a:anchors)if(!span(base+a.rva,a.size,true)||std::memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size))return false;return true;}
bool emptyString(const Header&h){return at<std::uint64_t>(std::uintptr_t(h.bytes)+0x138)==0&&at<std::uint64_t>(std::uintptr_t(h.bytes)+0x140)==15&&h.bytes[0x128]==0;}
bool preparedHeader(const Header&h){Header expected=checkpoint_target_metadata::ExpectedParsedHeader;
    std::memcpy(expected.bytes+0x128,checkpoint_target_metadata::TargetName,13);put(expected.bytes,0x138,std::uint64_t(12));
    return !std::memcmp(&h,&expected,sizeof h);
}
bool hashMatches(const unsigned char*p,std::size_t n){unsigned char hash[32];return n==checkpoint_target_metadata::TargetSize&&native_storage_read::Sha256(p,n,hash)&&!std::memcmp(hash,checkpoint_target_metadata::TargetSha256,32);}
bool overlap(std::uintptr_t a,std::size_t an,std::uintptr_t b,std::size_t bn){return a<b+bn&&b<a+an;}
}
bool Adapter::Enter() noexcept {
    if(GetCurrentThreadId()!=report_.thread)return false;
    if(InterlockedCompareExchange(&busy_,1,0)){++report_.reentrantCalls;report_.poisoned=true;report_.stage="reentrant_leaf_rejected";return false;}return true;
}
void Adapter::Leave() noexcept {InterlockedExchange(&busy_,0);}
bool Adapter::Guard(bool allowPoison) noexcept {
    __try{
        if(!report_.bound||(!allowPoison&&report_.poisoned)||report_.reentrantCalls||GetCurrentThreadId()!=report_.thread||!access_.validateCall||!access_.privateNode||!access_.validateCall(access_.context))return false;
        if(report_.fixtureBinding)return !report_.reentrantCalls;
        auto b=report_.base;
        if(b!=std::uintptr_t(GetModuleHandleW(nullptr))||!exactCode(b))return false;
        report_.oomCallback=at<std::uintptr_t>(b+kAllocatorOomCallbackRva);report_.heapErrorHandler=at<std::uintptr_t>(b+kAllocatorHeapErrorRva);
        if((report_.oomCallback&&report_.oomCallback!=b+kAllocatorNoopOomRva)||report_.heapErrorHandler)return false;
        if(report_.oomCallback&&(!span(b+kAllocatorNoopOomRva,3,true)||std::memcmp(reinterpret_cast<void*>(b+kAllocatorNoopOomRva),"\x33\xC0\xC3",3)))return false;
        auto index=at<unsigned>(b+kAllocatorTlsIndexRva);if(index>=1088)return false;
        auto tls=std::uintptr_t(__readgsqword(0x58));if(!span(tls+std::size_t(index)*8,8))return false;
        auto local=at<std::uintptr_t>(tls+std::size_t(index)*8);if(!span(local+0x10,4))return false;
        report_.allocatorGlobalEpoch=at<std::int32_t>(b+kAllocatorEpochRva);report_.allocatorThreadEpoch=at<std::int32_t>(local+0x10);
        if(report_.allocatorGlobalEpoch==0||report_.allocatorGlobalEpoch==-1||report_.allocatorGlobalEpoch>report_.allocatorThreadEpoch)return false;
        auto allocator=b+kAllocatorRootRva;if(!span(allocator,0x90))return false;
        if(at<std::uintptr_t>(allocator)!=b+kAllocatorVtableRva||at<std::uintptr_t>(b+kAllocatorVtableRva+0x28)!=b+kAllocatorAllocateRva||at<std::uintptr_t>(b+kAllocatorVtableRva+0x58)!=b+kAllocatorFreeRva)return false;
        auto backing=at<std::uintptr_t>(allocator+0x20);if(!backing||!span(backing,16)||backing!=at<std::uintptr_t>(b+kAllocatorBackingRva))return false;
        if(report_.allocatorBacking&&report_.allocatorBacking!=backing)return false;
        report_.allocator=allocator;report_.allocatorBacking=backing;
        return !report_.reentrantCalls;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}
}
bool Adapter::BindProduction(std::uintptr_t base,DWORD thread,const Access&a) noexcept {
    if(bindAttempted_)return false;bindAttempted_=true;report_.base=base;report_.thread=thread;access_=a;
    report_.stage="bind_production_anchors_allocator";
    if(!thread||thread!=GetCurrentThreadId()||!base||!a.validateCall||!a.privateNode)return false;
    functions_={reinterpret_cast<decltype(functions_.headerCtor)>(base+0x2E32A0),reinterpret_cast<decltype(functions_.headerParse)>(base+0x2FAAD0),
        reinterpret_cast<decltype(functions_.headerCopy)>(base+0x2E2A40),reinterpret_cast<decltype(functions_.stringDtor)>(base+0x50D20),
        reinterpret_cast<decltype(functions_.allocate)>(base+0x3A5820),reinterpret_cast<decltype(functions_.free)>(base+0x3A58B0)};
    report_.bound=true;if(!Guard()){report_.bound=false;return false;}report_.stage="bound_no_native_calls";return true;
}
#ifdef CHECKPOINT_TARGET_METADATA_NATIVE_FIXTURE
bool Adapter::BindFixture(DWORD thread,const Access&a,const Functions&f) noexcept {
    if(bindAttempted_)return false;bindAttempted_=true;report_.thread=thread;access_=a;functions_=f;report_.fixtureBinding=true;
    if(!thread||thread!=GetCurrentThreadId()||!a.validateCall||!a.privateNode||!f.headerCtor||!f.headerParse||!f.headerCopy||!f.stringDtor||!f.allocate||!f.free)return false;
    report_.bound=true;if(!Guard()){report_.bound=false;return false;}report_.stage="fixture_bound";return true;
}
#endif
bool Adapter::NativeCtor(Header*p) noexcept {if(!Guard())return false;__try{++report_.headerCtorCalls;auto result=functions_.headerCtor(p);++report_.ctorReturned;return result==p&&Guard();}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}}
bool Adapter::NativeParse(Header*p,void*s,bool&ok) noexcept {if(!Guard())return false;__try{++report_.headerParserCalls;ok=functions_.headerParse(p,s);++report_.parserReturned;return Guard();}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}}
bool Adapter::NativeCopy(Header*p,const Header*s) noexcept {if(!Guard())return false;__try{++report_.headerCopyCalls;auto result=functions_.headerCopy(p,s);++report_.copyReturned;return result==p&&Guard();}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}}
bool Adapter::NativeDestroyString(void*p) noexcept {if(!Guard())return false;__try{++report_.stringDtorCalls;functions_.stringDtor(p);++report_.stringDtorReturned;return Guard();}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}}
bool Adapter::NativeAllocate(void*&p) noexcept {if(!Guard())return false;__try{++report_.allocateCalls;p=functions_.allocate(0x160);++report_.allocateReturned;return true;}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}}
bool Adapter::NativeFree(void*p) noexcept {if(!Guard())return false;__try{++report_.freeCalls;functions_.free(p);++report_.freeReturned;return Guard();}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;return false;}}

bool Adapter::ParseVerifiedBytes(const unsigned char*source,std::size_t size,Header&out,ParseReceipt&receipt) noexcept {
    if(!Enter())return false;bool success=false;
    __try{
        if(parseAttempted_){report_.stage="parser_attempt_used";__leave;}parseAttempted_=true;++report_.parseAttempts;receipt={};out={};
        report_.stage="parser_input_identity";if(!Guard()||!span(std::uintptr_t(source),size)||!hashMatches(source,size))__leave;
        report_.fullBufferMatched=true;Header header{};alignas(16) unsigned char stream[0x98]{};
        if(!NativeCtor(&header)||!emptyString(header)){report_.poisoned=true;__leave;}
        put(stream,0x20,unsigned(1));put(stream,0x30,std::uintptr_t(source+4));put(stream,0x38,std::uintptr_t(source+size));put(stream,0x88,unsigned(92));
        unsigned char initial[0x98];std::memcpy(initial,stream,sizeof stream);bool parsed=false;
        report_.stage="borrowed_pod_parser";if(!NativeParse(&header,stream,parsed)){report_.poisoned=true;__leave;}
        auto cursor=at<std::uintptr_t>(std::uintptr_t(stream)+0x30);auto error=at<unsigned>(std::uintptr_t(stream)+0x50);
        receipt={source,size,cursor>=std::uintptr_t(source)&&cursor<=std::uintptr_t(source+size)?std::size_t(cursor-std::uintptr_t(source)):SIZE_MAX,0,error};
        std::memcpy(initial+0x30,stream+0x30,8);std::memcpy(initial+0x50,stream+0x50,4);
        report_.borrowedStreamIntact=!std::memcmp(initial,stream,sizeof stream);
        report_.sourceUnchanged=hashMatches(source,size);
        if(!report_.borrowedStreamIntact||!report_.sourceUnchanged||!emptyString(header)){report_.poisoned=true;__leave;}
        bool matches=parsed&&!error&&receipt.consumed==294&&!std::memcmp(&header,&checkpoint_target_metadata::ExpectedParsedHeader,sizeof header);
        // The borrowed POD has no owner lifetime at all. Only the native header
        // string is destroyed, and only after confirming it is the empty SSO.
        report_.stage="destroy_empty_header_sso";if(!NativeDestroyString(header.bytes+0x128)){report_.poisoned=true;__leave;}
        if(!matches){report_.stage="parsed_header_rejected";__leave;}
        out=header;success=true;report_.stage="parsed_same_buffer_no_stream_owner";
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;report_.stage="parser_exception_no_owner_cleanup";}
    Leave();return success;
}
bool Adapter::CopyNode(void*head,void*tail,const Header&source,OwnedNode&out) noexcept {
    if(!Enter())return false;bool success=false;
    __try{
        if(copyAttempted_){report_.stage="copy_attempt_used";__leave;}copyAttempted_=true;++report_.copyAttempts;
        report_.stage="copy_input";if(out.pointer||out.allocation||!Guard()||!preparedHeader(source)||!span(std::uintptr_t(head),16)||!span(std::uintptr_t(tail),16))__leave;
        void*node=nullptr;report_.stage="allocate_native_160";
        if(!NativeAllocate(node)){report_.nodeState=NodeState::Uncertain;__leave;}
        if(!node){report_.stage="native_allocation_null_no_copy";__leave;}
        // Publish identity immediately after allocator returns, BEFORE Guard,
        // zeroing, link writes, or fallible native payload construction.
        report_.node=std::uintptr_t(node);report_.allocationTicket=std::uint64_t(InterlockedIncrement64(&nextAllocationTicket));report_.nodeState=NodeState::Allocated;out={node,report_.allocationTicket};
        if(!Guard()||!span(report_.node,0x160)||overlap(report_.node,0x160,std::uintptr_t(head),16)||overlap(report_.node,0x160,std::uintptr_t(tail),16)||!access_.privateNode(access_.context,out)){report_.poisoned=true;report_.nodeState=NodeState::Uncertain;__leave;}
        std::memset(node,0,0x160);put(node,0,std::uintptr_t(head));put(node,8,std::uintptr_t(tail));
        report_.nodeState=NodeState::Constructing;report_.stage="native_payload_copy";
        if(!NativeCopy(reinterpret_cast<Header*>(static_cast<unsigned char*>(node)+16),&source)){report_.poisoned=true;report_.nodeState=NodeState::Uncertain;__leave;}
        if(std::memcmp(static_cast<unsigned char*>(node)+16,&source,sizeof source)||at<std::uintptr_t>(report_.node)!=std::uintptr_t(head)||at<std::uintptr_t>(report_.node+8)!=std::uintptr_t(tail)||!Guard()||!access_.privateNode(access_.context,out)){report_.poisoned=true;report_.nodeState=NodeState::Uncertain;__leave;}
        report_.nodeState=NodeState::Private;report_.stage="private_node_ready_unpublished";success=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;report_.nodeState=NodeState::Uncertain;report_.stage="copy_exception_preserve_ticket";}
    Leave();return success;
}
bool Adapter::OwnsNode(const OwnedNode&node) noexcept {
    if(report_.nodeState!=NodeState::Private||node.pointer!=reinterpret_cast<void*>(report_.node)||node.allocation!=report_.allocationTicket||!Enter())return false;
    bool owned=false;
    __try{owned=Guard()&&access_.privateNode(access_.context,node);}__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;}
    Leave();return owned;
}
bool Adapter::ReleaseNode(OwnedNode&node) noexcept {
    if(!OwnsNode(node)||!Enter())return false;bool success=false;
    __try{
        if(releaseAttempted_)__leave;releaseAttempted_=true;++report_.releaseAttempts;
        report_.stage="private_release_validate";if(!Guard()||!access_.privateNode(access_.context,node))__leave;
        auto header=reinterpret_cast<const Header*>(static_cast<unsigned char*>(node.pointer)+16);
        if(!preparedHeader(*header)){report_.poisoned=true;report_.nodeState=NodeState::Uncertain;__leave;}
        report_.nodeState=NodeState::Releasing;
        if(!NativeDestroyString(static_cast<unsigned char*>(node.pointer)+0x138)||!NativeFree(node.pointer)){report_.poisoned=true;report_.nodeState=NodeState::Uncertain;__leave;}
        report_.nodeState=NodeState::Released;node={};report_.stage="private_node_native_released";success=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.poisoned=true;report_.nodeState=NodeState::Uncertain;report_.stage="release_exception_no_retry";}
    Leave();return success;
}
checkpoint_target_metadata::Adapter Adapter::LeafCallbacks() noexcept {
    checkpoint_target_metadata::Adapter result{};result.context=this;
    result.parseVerifiedBytes=[](void*c,const unsigned char*p,std::size_t n,Header&h,ParseReceipt&r){return static_cast<Adapter*>(c)->ParseVerifiedBytes(p,n,h,r);};
    result.copyNode=[](void*c,void*h,void*t,const Header&s,OwnedNode&n){return static_cast<Adapter*>(c)->CopyNode(h,t,s,n);};
    result.ownsNode=[](void*c,const OwnedNode&n){return static_cast<Adapter*>(c)->OwnsNode(n);};
    result.releaseNode=[](void*c,OwnedNode&n){return static_cast<Adapter*>(c)->ReleaseNode(n);};return result;
}
}
