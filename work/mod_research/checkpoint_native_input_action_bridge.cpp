#include "checkpoint_native_input_action_bridge.h"
#include "checkpoint_native_input_action_archived.h"
#include <array>
#include <cstring>
#include <intrin.h>
#include <limits>

namespace checkpoint_native_input_action {
namespace {
static_assert(sizeof(void*)==8,"Audited Windows x64 ABI");
static_assert(kMapPointerRva==kArchivedMapPointerRva&&kActiveRva==kArchivedActiveRva&&
    kTlsIndexRva==kArchivedTlsIndexRva&&kInitGuardRva==kArchivedInitGuardRva&&kNormalRva==kArchivedNormalRva,
    "Source RVAs must match Capstone-resolved native RIP references");
thread_local ScopedRoute* route=nullptr;thread_local std::uint64_t unrouted=0;
struct Range{std::uintptr_t begin,end;};
bool Span(const void* p,std::size_t n,std::size_t minimum,Range& r) noexcept {
    const auto a=reinterpret_cast<std::uintptr_t>(p);
    if(!a||n<minimum||n>std::numeric_limits<std::uintptr_t>::max()-a)return false;
    r={a,a+n};return true;
}
bool Overlap(Range a,Range b)noexcept{return a.begin<b.end&&b.begin<a.end;}
template<class T>T Read(const void* p,std::size_t off)noexcept{T v{};std::memcpy(&v,static_cast<const std::uint8_t*>(p)+off,sizeof(v));return v;}
bool Same(const Binding&a,const Binding&b)noexcept{return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
bool Code(std::uint32_t code)noexcept{return code<=0xff||(code>=0x101&&code<=0x104);}
struct Inside {bool& flag;explicit Inside(bool& f):flag(f){flag=true;}~Inside(){flag=false;}};
struct Bundle {
    std::array<std::uint8_t,checkpoint_native_input::kNormalSize> normal{};
    std::array<std::uint8_t,checkpoint_native_input::kMouseSize> mouse{};
    std::array<std::uint8_t,checkpoint_native_input::kRawKeyboardSize> raw{};
    std::array<std::uint8_t,0x100> mapping{};
};
Bundle Capture(const Config& c)noexcept{Bundle b;
    std::memcpy(b.normal.data(),c.buffers.normal.data,b.normal.size());
    std::memcpy(b.mouse.data(),c.buffers.mouse.data,b.mouse.size());
    std::memcpy(b.raw.data(),c.buffers.raw_keyboard_source.data,b.raw.size());
    std::memcpy(b.mapping.data(),c.mapping.data,b.mapping.size());return b;}
bool Equal(const Bundle&a,const Bundle&b)noexcept{return a.normal==b.normal&&a.mouse==b.mouse&&a.raw==b.raw&&a.mapping==b.mapping;}
bool ShadowPressed(const checkpoint_native_input::RawKeyboardShadow& shadow,std::uint32_t code)noexcept{
    if(!code)return false;
    if(code<=0xff)return shadow.keys[code]!=0;
    const auto mask=0x11u<<(code-0x101);return (shadow.modifiers&mask)!=0;
}
}
const char* StatusName(Status s)noexcept{switch(s){
#define AS(x) case Status::x:return #x;
    AS(Ok) AS(NotBound) AS(AlreadyBound) AS(InvalidSpan) AS(Overlap) AS(CodeMismatch)
    AS(WrongThread) AS(StaleBinding) AS(WrongSource) AS(InvalidLayout) AS(UninitializedSingleton)
    AS(WrongTls) AS(InvalidAction) AS(UnknownMapping) AS(InvalidMode) AS(Reentrant)
    AS(PublicationRejected) AS(SourceChanged) AS(OriginalInFlight) AS(OriginalException) AS(UnexpectedOriginalResult)
#undef AS
    }return "Unknown";}
Status Bridge::Sources(const Config& c,std::uint32_t action,bool check_action,Report& r)const noexcept{
    Range image{},normal{},mouse{},raw{},mapping{},slots{},tls{},self{};
    if(c.tls_index>1023||!Span(c.image.data,c.image.size,kTlsIndexRva+4,image)||
       !Span(c.buffers.normal.data,c.buffers.normal.size,checkpoint_native_input::kNormalSize,normal)||
       !Span(c.buffers.mouse.data,c.buffers.mouse.size,checkpoint_native_input::kMouseSize,mouse)||
       !Span(c.buffers.raw_keyboard_source.data,c.buffers.raw_keyboard_source.size,checkpoint_native_input::kRawKeyboardSize,raw)||
       !Span(c.mapping.data,c.mapping.size,0x100,mapping)||
       !Span(c.tls_slots.data,c.tls_slots.size,(std::size_t(c.tls_index)+1)*8,slots)||
       !Span(c.tls_data.data,c.tls_data.size,0x14,tls)||!Span(this,sizeof(*this),sizeof(*this),self))return Status::InvalidSpan;
    const Range separate[]={normal,mouse,raw,mapping,slots,tls};
    if(Overlap(image,self))return Status::Overlap;
    for(std::size_t i=0;i<6;++i){if(Overlap(separate[i],self))return Status::Overlap;
        for(std::size_t j=i+1;j<6;++j)if(Overlap(separate[i],separate[j]))return Status::Overlap;}
    if(normal.begin!=image.begin+kNormalRva||mouse.begin!=image.begin+kMouseRva||
       Read<std::uintptr_t>(c.image.data,kMapPointerRva)!=mapping.begin||
       Read<std::uintptr_t>(c.buffers.normal.data,0)!=raw.begin)return Status::WrongSource;
    if(std::memcmp(c.image.data+kActionRva,kAction.data(),kAction.size())||
       std::memcmp(c.image.data+kSingletonRva,kSingleton.data(),kSingleton.size()))return Status::CodeMismatch;
    // Reading current-process GS is permitted only in this explicitly invoked,
    // pinned in-process adapter. Supplied extents are a host ownership contract;
    // this is not arbitrary address probing or a global native thread fence.
    if(__readgsqword(0x58)!=slots.begin||Read<std::uint32_t>(c.image.data,kTlsIndexRva)!=c.tls_index||
       Read<std::uintptr_t>(c.tls_slots.data,std::size_t(c.tls_index)*8)!=tls.begin)return Status::WrongTls;
    r.initialized_epoch=Read<std::int32_t>(c.image.data,kInitGuardRva);
    r.thread_epoch=Read<std::int32_t>(c.tls_data.data,0x10);
    if(r.initialized_epoch>=-1||r.initialized_epoch>r.thread_epoch)return Status::UninitializedSingleton;
    r.active_gate=Read<std::uint32_t>(c.image.data,kActiveRva);
    if(r.active_gate>1||Read<std::uint32_t>(c.buffers.normal.data,8)>1||Read<std::uint32_t>(c.buffers.normal.data,12)>1||
       Read<std::uint32_t>(c.buffers.mouse.data,0)>1||Read<std::uint32_t>(c.buffers.mouse.data,4)>1||
       Read<std::uint32_t>(c.buffers.raw_keyboard_source.data,0x54)>checkpoint_native_input::kRawEventCapacity)return Status::InvalidLayout;
    if(check_action){if(action>30)return Status::InvalidAction;
        r.codes[0]=Read<std::uint32_t>(c.mapping.data,8+std::size_t(action)*8);
        r.codes[1]=Read<std::uint32_t>(c.mapping.data,12+std::size_t(action)*8);
        if(!Code(r.codes[0])||!Code(r.codes[1]))return Status::UnknownMapping;}
    return Status::Ok;
}
Status Bridge::Bind(const Config& c)noexcept{
    if(bound_)return Status::AlreadyBound;Report r;const auto status=Sources(c,0,false,r);
    if(status!=Status::Ok)return status;
    if(adapter_.Bind(c.binding,c.buffers)!=checkpoint_native_input::Status::Ok)return Status::PublicationRejected;
    config_=c;owner_=std::this_thread::get_id();bound_=true;return Status::Ok;
}
std::uint32_t Bridge::Invoke(const Request& request,std::uint32_t action,Report& r){
    r=Report{};r.action=action;
    if(!bound_){r.status=Status::NotBound;return 0;}
    if(owner_!=std::this_thread::get_id()){r.status=Status::WrongThread;return 0;}
    if(!Same(config_.binding,request.binding)){r.status=Status::StaleBinding;return 0;}
    if(inside_){r.status=Status::Reentrant;return 0;}
    if(request.mode!=Mode::ForwardUntouched&&request.mode!=Mode::NeutralizeAuditedAction){r.status=Status::InvalidMode;return 0;}
    r.status=Sources(config_,action,true,r);if(r.status!=Status::Ok)return 0;
    checkpoint_native_input::RawKeyboardShadow shadow{};
    if(request.mode==Mode::NeutralizeAuditedAction){
        r.publication=adapter_.PublishNeutral(request.binding,request.publication_cycle);r.core_status=r.publication.status;
        if(r.core_status!=checkpoint_native_input::Status::Ok){r.status=Status::PublicationRejected;return 0;}
        r.core_status=adapter_.CopyRawShadow(request.binding,request.publication_cycle,shadow);
        if(r.core_status!=checkpoint_native_input::Status::Ok){r.status=Status::PublicationRejected;return 0;}
    }
    const auto before=Capture(config_);Inside guard(inside_);r.original_started=true;r.status=Status::OriginalInFlight;
    try{
        using Native=std::uint32_t(*)(std::uint32_t);
        r.original_value=reinterpret_cast<Native>(config_.image.data+kActionRva)(action);
        r.original_completed=true;r.delivered_value=r.original_value;
        Report after;const auto status=Sources(config_,action,true,after);
        r.source_bundle_unchanged=status==Status::Ok&&Equal(before,Capture(config_))&&
            r.active_gate==after.active_gate&&r.initialized_epoch==after.initialized_epoch&&r.thread_epoch==after.thread_epoch;
        if(!r.source_bundle_unchanged){r.status=Status::SourceChanged;r.delivered_value=0;return 0;}
        if(r.original_value>1){r.status=Status::UnexpectedOriginalResult;r.delivered_value=0;return 0;}
        if(request.mode==Mode::NeutralizeAuditedAction){
            r.delivered_value=r.active_gate&&(ShadowPressed(shadow,r.codes[0])||ShadowPressed(shadow,r.codes[1]));
            r.used_neutral_shadow=true;
        }
        r.status=Status::Ok;return r.delivered_value;
    }catch(...){r.status=Status::OriginalException;r.exception_rethrown=true;throw;}
}
ScopedRoute::ScopedRoute(Bridge& b,Request r)noexcept:bridge_(b),request_(r),previous_(route){route=this;}
ScopedRoute::~ScopedRoute(){route=previous_;}
std::uint32_t ActionQuery(std::uint32_t a){if(!route){++unrouted;return 0;}return route->bridge_.Invoke(route->request_,a,route->report_);}
std::uint64_t UnroutedCallCountForThisThread()noexcept{return unrouted;}
}
