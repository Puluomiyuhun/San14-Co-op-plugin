#include "checkpoint_native_input_router_core.h"
#include <cstring>

namespace checkpoint_native_input_router {
namespace {
namespace mouse=checkpoint_native_input_consumer;
namespace key=checkpoint_native_input_keyboard;
namespace action=checkpoint_native_input_action;
thread_local ScopedRoute* route=nullptr;thread_local std::uint64_t unrouted=0;
bool Same(const Binding&a,const Binding&b)noexcept{return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
template<class T>T Read(const void* p,std::size_t at)noexcept{T v{};std::memcpy(&v,static_cast<const std::uint8_t*>(p)+at,sizeof(v));return v;}
bool Sources(const checkpoint_native_input::Buffers& b)noexcept{
    return Read<std::uintptr_t>(b.normal.data,0)==reinterpret_cast<std::uintptr_t>(b.raw_keyboard_source.data)&&
        Read<std::uint32_t>(b.normal.data,8)<=1&&Read<std::uint32_t>(b.normal.data,12)<=1&&
        Read<std::uint32_t>(b.mouse.data,0)<=1&&Read<std::uint32_t>(b.mouse.data,4)<=1&&
        Read<std::uint32_t>(b.raw_keyboard_source.data,0x54)<=checkpoint_native_input::kRawEventCapacity;
}
bool IsOwnEntry(std::uintptr_t p)noexcept{return
    p==reinterpret_cast<std::uintptr_t>(&Mouse)||p==reinterpret_cast<std::uintptr_t>(&KeyRelease)||
    p==reinterpret_cast<std::uintptr_t>(&KeyPress)||p==reinterpret_cast<std::uintptr_t>(&KeyRepeat)||
    p==reinterpret_cast<std::uintptr_t>(&Modifier11)||p==reinterpret_cast<std::uintptr_t>(&Modifier22)||
    p==reinterpret_cast<std::uintptr_t>(&ModifierMasked)||p==reinterpret_cast<std::uintptr_t>(&Action);}
bool KeyCode(std::uint32_t k)noexcept{return(k>=1&&k<=0xff)||(k>=0x101&&k<=0x104);}
bool Mask(std::uint32_t k)noexcept{return k==0x11||k==0x22||k==0x44||k==0x88;}
bool IsKey(Kind k)noexcept{return k>=Kind::KeyRelease&&k<=Kind::Modifier22;}
key::Query KeyKind(Kind k)noexcept{switch(k){
    case Kind::KeyRelease:return key::Query::Release;case Kind::KeyPress:return key::Query::Press;
    case Kind::KeyRepeat:return key::Query::Repeat;case Kind::Modifier11:return key::Query::Modifier11;
    case Kind::ModifierMasked:return key::Query::ModifierMasked;case Kind::Modifier22:return key::Query::Modifier22;
    default:return key::Query::Count;}}
struct Inside {bool& flag;explicit Inside(bool& f):flag(f){flag=true;}~Inside(){flag=false;}};
bool Arguments(const Call& c)noexcept{switch(c.kind){
    case Kind::Mouse:return c.argument<=2&&c.flag==0;
    case Kind::KeyRelease:case Kind::KeyPress:return KeyCode(c.argument)&&c.flag==0;
    case Kind::KeyRepeat:return KeyCode(c.argument)&&c.flag<=1;
    case Kind::Modifier11:case Kind::Modifier22:return c.argument==0&&c.flag==0;
    case Kind::ModifierMasked:return Mask(c.argument)&&c.flag<=1;
    case Kind::Action:return c.argument<=30&&c.flag==0;
    default:return false;}}
bool Capture(Report& r)noexcept{
    if(r.kind==Kind::Mouse){r.original_started=r.mouse.original_started;r.original_completed=r.mouse.original_completed;
        r.original_return=r.mouse.original_return;r.exception_rethrown=r.mouse.exception_rethrown;
        return r.mouse.status==mouse::Status::Ok;}
    if(IsKey(r.kind)){r.original_started=r.keyboard.original_started;r.original_completed=r.keyboard.original_completed;
        r.original_return=r.keyboard.original_rax;r.exception_rethrown=r.keyboard.exception_rethrown;
        return r.keyboard.status==key::Status::Ok;}
    r.original_started=r.action.original_started;r.original_completed=r.action.original_completed;
    r.original_return=r.action.original_value;r.exception_rethrown=r.action.exception_rethrown;
    return r.action.status==action::Status::Ok;
}
}
const char* StatusName(Status s)noexcept{switch(s){
#define RS(x) case Status::x:return #x;
    RS(Ok) RS(NotBound) RS(BindAlreadyAttempted) RS(InvalidTarget) RS(BindRejected) RS(WrongThread)
    RS(StaleBinding) RS(InvalidMode) RS(UnknownRoute) RS(InvalidArguments) RS(WrongSource)
    RS(InvalidSourceLayout) RS(StaleCycle) RS(Reentrant) RS(OriginalInFlight) RS(DelegateRejected) RS(OriginalException)
#undef RS
    }return "Unknown";}
BindReport Router::Bind(const Config& c)noexcept{
    BindReport r;if(bind_attempted_){r.status=Status::BindAlreadyAttempted;return r;}bind_attempted_=true;
    if(!c.mouse_original||IsOwnEntry(reinterpret_cast<std::uintptr_t>(c.mouse_original))){r.status=Status::InvalidTarget;return r;}
    for(auto p:c.keyboard_originals)if(!p||IsOwnEntry(reinterpret_cast<std::uintptr_t>(p))){r.status=Status::InvalidTarget;return r;}
    // All child adapters receive the identical canonical identity and buffers.
    r.mouse=mouse_.Bind(c.source.binding,c.source.buffers,c.mouse_original);
    if(r.mouse!=mouse::Status::Ok){r.status=Status::BindRejected;return r;}
    r.keyboard=keyboard_.Bind(c.source.binding,c.source.buffers,c.keyboard_originals);
    if(r.keyboard!=key::Status::Ok){r.status=Status::BindRejected;return r;}
    r.action=action_.Bind(c.source);
    if(r.action!=action::Status::Ok){r.status=Status::BindRejected;return r;}
    binding_=c.source.binding;normal_=c.source.buffers.normal.data;mouse_cache_=c.source.buffers.mouse.data;
    buffers_=c.source.buffers;
    owner_=std::this_thread::get_id();bound_=true;r.status=Status::Ok;return r;
}
std::uint64_t Router::Invoke(const Request& request,const Call& call,Report& r){
    r=Report{};r.kind=call.kind;r.cycle=request.cycle;
    if(!bound_){r.status=Status::NotBound;return 0;}
    if(owner_!=std::this_thread::get_id()){r.status=Status::WrongThread;return 0;}
    r.previous_cycle=last_cycle_;
    if(!Same(binding_,request.binding)){r.status=Status::StaleBinding;return 0;}
    if(inside_){r.status=Status::Reentrant;return 0;}
    if(request.mode!=Mode::ForwardUntouched&&request.mode!=Mode::NeutralizeAdmittedQuery){r.status=Status::InvalidMode;return 0;}
    if(call.kind>=Kind::Count){r.status=Status::UnknownRoute;return 0;}
    if(!Arguments(call)){r.status=Status::InvalidArguments;return 0;}
    const auto expected=call.kind==Kind::Mouse?mouse_cache_:call.kind==Kind::Action?nullptr:normal_;
    if(call.observed_cache!=expected){r.status=Status::WrongSource;return 0;}
    if(!Sources(buffers_)){r.status=Status::InvalidSourceLayout;return 0;}
    if(!request.cycle||request.cycle<=last_cycle_){r.status=Status::StaleCycle;return 0;}
    last_cycle_=request.cycle;r.cycle_consumed=true;r.delegated=true;r.status=Status::OriginalInFlight;
    const bool neutral=request.mode==Mode::NeutralizeAdmittedQuery;Inside guard(inside_);
    try{
        if(call.kind==Kind::Mouse){
            r.delivered_return=mouse_.Invoke({request.binding,request.cycle,
                neutral?mouse::Mode::NeutralizeThenForward:mouse::Mode::ForwardUntouched},
                call.observed_cache,call.argument,r.mouse);
        }else if(IsKey(call.kind)){
            r.delivered_return=keyboard_.Invoke({request.binding,request.cycle,
                neutral?key::Mode::NeutralizeAuditedQuery:key::Mode::ForwardUntouched},
                KeyKind(call.kind),call.observed_cache,call.argument,call.flag,r.keyboard);
        }else{
            r.delivered_return=action_.Invoke({request.binding,request.cycle,
                neutral?action::Mode::NeutralizeAuditedAction:action::Mode::ForwardUntouched},
                call.argument,r.action);
        }
        r.status=Capture(r)&&r.original_completed?Status::Ok:Status::DelegateRejected;
        return r.delivered_return;
    }catch(...){Capture(r);r.status=Status::OriginalException;r.exception_rethrown=true;throw;}
}
ScopedRoute::ScopedRoute(Router& r,Request q)noexcept:router_(r),request_(q),previous_(route){route=this;}
ScopedRoute::~ScopedRoute(){route=previous_;}
std::uint64_t UnroutedCallCountForThisThread()noexcept{return unrouted;}
std::uint64_t Routed(const Call& c){if(!route){++unrouted;return 0;}return route->router_.Invoke(route->request_,c,route->report_);}
std::uint32_t Mouse(const void*p,std::uint32_t b){return static_cast<std::uint32_t>(Routed({Kind::Mouse,p,b,0}));}
std::uint64_t KeyRelease(const void*p,std::uint32_t k){return Routed({Kind::KeyRelease,p,k,0});}
std::uint64_t KeyPress(const void*p,std::uint32_t k){return Routed({Kind::KeyPress,p,k,0});}
std::uint64_t KeyRepeat(const void*p,std::uint32_t k,std::uint32_t f){return Routed({Kind::KeyRepeat,p,k,f});}
std::uint64_t Modifier11(const void*p){return Routed({Kind::Modifier11,p,0,0});}
std::uint64_t Modifier22(const void*p){return Routed({Kind::Modifier22,p,0,0});}
std::uint64_t ModifierMasked(const void*p,std::uint32_t m,std::uint32_t f){return Routed({Kind::ModifierMasked,p,m,f});}
std::uint32_t Action(std::uint32_t a){return static_cast<std::uint32_t>(Routed({Kind::Action,nullptr,a,0}));}
}
