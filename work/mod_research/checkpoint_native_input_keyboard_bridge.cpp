#include "checkpoint_native_input_keyboard_bridge.h"
#include <cstring>

namespace checkpoint_native_input_keyboard {
namespace {
thread_local ScopedRoute* route = nullptr;
thread_local std::uint64_t unrouted = 0;
bool Same(const Binding& a,const Binding& b) noexcept {
    return a.attempt==b.attempt && a.attachment==b.attachment && a.owner_generation==b.owner_generation;
}
template<class T> T Read(const void* p,std::size_t at) noexcept {
    T value{};std::memcpy(&value,static_cast<const std::uint8_t*>(p)+at,sizeof(value));return value;
}
bool Mask(std::uint32_t m) noexcept { return m==0x11 || m==0x22 || m==0x44 || m==0x88; }
bool Key(std::uint32_t k) noexcept { return (k>=1 && k<=0xff) || (k>=0x101 && k<=0x104); }
struct Inside { bool& value;explicit Inside(bool& v):value(v){value=true;}~Inside(){value=false;} };
}
const char* StatusName(Status s) noexcept {
    switch(s) {
#define KSTATUS(x) case Status::x:return #x;
        KSTATUS(Ok) KSTATUS(NotBound) KSTATUS(AlreadyBound) KSTATUS(InvalidTarget)
        KSTATUS(WrongThread) KSTATUS(StaleBinding) KSTATUS(UnexpectedCache) KSTATUS(InvalidLayout)
        KSTATUS(InvalidMode) KSTATUS(InvalidQuery) KSTATUS(ReentrantCall) KSTATUS(PublicationRejected)
        KSTATUS(OriginalException) KSTATUS(UnexpectedOriginalResult)
#undef KSTATUS
    } return "Unknown";
}
Status QueryBridge::Bind(const Binding& b,Buffers buffers,Targets targets) noexcept {
    if(bound_)return Status::AlreadyBound;
    bool any=false;
    for(auto target:targets) {
        if(!target)continue;
        const auto address=reinterpret_cast<std::uintptr_t>(target);
        if(address==reinterpret_cast<std::uintptr_t>(&Release) || address==reinterpret_cast<std::uintptr_t>(&Press) ||
           address==reinterpret_cast<std::uintptr_t>(&Repeat) || address==reinterpret_cast<std::uintptr_t>(&Modifier11) ||
           address==reinterpret_cast<std::uintptr_t>(&Modifier22) || address==reinterpret_cast<std::uintptr_t>(&ModifierMasked))
            return Status::InvalidTarget;
        any=true;
    }
    if(!any)return Status::InvalidTarget;
    if(adapter_.Bind(b,buffers)!=checkpoint_native_input::Status::Ok)return Status::PublicationRejected;
    binding_=b;buffers_=buffers;targets_=targets;owner_=std::this_thread::get_id();bound_=true;return Status::Ok;
}
std::uint64_t QueryBridge::Invoke(const Request& r,Query q,const void* normal,
                                 std::uint32_t argument,std::uint32_t flag,Report& out) {
    out=Report{};out.query=q;
    if(!bound_){out.status=Status::NotBound;return 0;}
    if(owner_!=std::this_thread::get_id()){out.status=Status::WrongThread;return 0;}
    if(!Same(binding_,r.binding)){out.status=Status::StaleBinding;return 0;}
    if(normal!=buffers_.normal.data){out.status=Status::UnexpectedCache;return 0;}
    if(inside_){out.status=Status::ReentrantCall;return 0;}
    if(r.mode!=Mode::ForwardUntouched && r.mode!=Mode::NeutralizeAuditedQuery){out.status=Status::InvalidMode;return 0;}
    const auto index=static_cast<std::size_t>(q);
    if(index>=targets_.size()){out.status=Status::InvalidQuery;return 0;}
    if(!targets_[index]){out.status=Status::InvalidTarget;return 0;}
    const bool modifier=q==Query::Modifier11 || q==Query::Modifier22 || q==Query::ModifierMasked;
    const std::uint32_t mask=q==Query::Modifier11 ? 0x11 : q==Query::Modifier22 ? 0x22 : argument;
    if((modifier && (!Mask(mask) || (q==Query::ModifierMasked && flag>1))) ||
       (!modifier && (!Key(argument) || (q==Query::Repeat && flag>1)))) {
        out.status=Status::InvalidQuery;return 0;
    }
    // Revalidate even untouched forwarding: the native leaf must never follow
    // a replaced raw pointer or index outside the two bound cache banks.
    if(Read<std::uintptr_t>(normal,0)!=reinterpret_cast<std::uintptr_t>(buffers_.raw_keyboard_source.data) ||
       Read<std::uint32_t>(normal,8)>1 || Read<std::uint32_t>(normal,12)>1) {
        out.status=Status::InvalidLayout;return 0;
    }
    checkpoint_native_input::RawKeyboardShadow shadow{};
    if(r.mode==Mode::NeutralizeAuditedQuery) {
        out.publication=adapter_.PublishNeutral(r.binding,r.publication_cycle);
        out.core_status=out.publication.status;
        if(out.core_status!=checkpoint_native_input::Status::Ok){out.status=Status::PublicationRejected;return 0;}
        if(modifier) {
            out.core_status=adapter_.CopyRawShadow(r.binding,r.publication_cycle,shadow);
            if(out.core_status!=checkpoint_native_input::Status::Ok){out.status=Status::PublicationRejected;return 0;}
        }
    }
    Inside guard(inside_);
    out.original_cache=normal;out.argument=argument;out.flag=flag;out.original_started=true;
    try {
        const auto original=targets_[index](normal,argument,flag);
        out.original_rax=original;out.original_completed=true;out.delivered_rax=original;
        if(r.mode==Mode::NeutralizeAuditedQuery && modifier) {
            const bool neutral=q==Query::ModifierMasked && flag
                ? (shadow.modifiers & mask)==mask : (shadow.modifiers & mask)!=0;
            out.delivered_rax=(original & ~std::uint64_t{0xff}) | std::uint64_t{neutral};
            out.used_neutral_shadow=true;
        } else if(r.mode==Mode::NeutralizeAuditedQuery && (original & 0xff)!=0) {
            // The audited pure key leaf must see zeroed banks. A nonzero result
            // is uncertainty, never proof that the intended boundary held.
            out.status=Status::UnexpectedOriginalResult;
            out.delivered_rax=original & ~std::uint64_t{0xff};return out.delivered_rax;
        }
        out.status=Status::Ok;return out.delivered_rax;
    } catch(...) {out.exception_rethrown=true;out.status=Status::OriginalException;throw;}
}
ScopedRoute::ScopedRoute(QueryBridge& b,Request r) noexcept:bridge_(b),request_(r),previous_(route){route=this;}
ScopedRoute::~ScopedRoute(){route=previous_;}
std::uint64_t UnroutedCallCountForThisThread() noexcept{return unrouted;}
std::uint64_t Routed(Query q,const void* p,std::uint32_t a,std::uint32_t f) {
    if(!route){++unrouted;return 0;}
    return route->bridge_.Invoke(route->request_,q,p,a,f,route->report_);
}
std::uint64_t Release(const void* p,std::uint32_t k){return Routed(Query::Release,p,k,0);}
std::uint64_t Press(const void* p,std::uint32_t k){return Routed(Query::Press,p,k,0);}
std::uint64_t Repeat(const void* p,std::uint32_t k,std::uint32_t f){return Routed(Query::Repeat,p,k,f);}
std::uint64_t Modifier11(const void* p){return Routed(Query::Modifier11,p,0,0);}
std::uint64_t Modifier22(const void* p){return Routed(Query::Modifier22,p,0,0);}
std::uint64_t ModifierMasked(const void* p,std::uint32_t m,std::uint32_t f){return Routed(Query::ModifierMasked,p,m,f);}
}
