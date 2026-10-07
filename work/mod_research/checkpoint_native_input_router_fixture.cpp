#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <intrin.h>
#include "checkpoint_native_input_router_core.h"
#include "checkpoint_native_input_consumer_archived.h"
#include "checkpoint_native_input_keyboard_archived.h"
#include "checkpoint_native_input_action_archived.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

extern "C" unsigned long _tls_index;
__declspec(thread) volatile unsigned char router_fixture_tls_extent[64];
namespace r=checkpoint_native_input_router;
namespace c=checkpoint_native_input;
namespace m=checkpoint_native_input_consumer;
namespace k=checkpoint_native_input_keyboard;
namespace a=checkpoint_native_input_action;
namespace {
void Check(bool v,const char* why){if(!v)throw std::runtime_error(why);}
template<class T>void Put(void*p,std::size_t off,T v){std::memcpy(static_cast<std::uint8_t*>(p)+off,&v,sizeof(v));}
template<class T>T Get(const void*p,std::size_t off){T v;std::memcpy(&v,static_cast<const std::uint8_t*>(p)+off,sizeof(v));return v;}
constexpr std::array<std::size_t,6> KEY_RVA={0x3A2CB0,0x3A2CD0,0x3A2CF0,0x3A2D60,0x3A2D80,0x3A2DA0};
class Image {
public:
    static constexpr std::size_t size=0x2040000;
    Image(){data=static_cast<std::uint8_t*>(VirtualAlloc(nullptr,size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));Check(data!=nullptr,"own image");
        copy(0x3A2920,m::kArchivedMouseQuery);copy(KEY_RVA[0],k::kRelease);copy(KEY_RVA[1],k::kPress);copy(KEY_RVA[2],k::kRepeat);
        copy(KEY_RVA[3],k::kModifier11);copy(KEY_RVA[4],k::kModifierMasked);copy(KEY_RVA[5],k::kModifier22);
        copy(a::kActionRva,a::kAction);copy(a::kSingletonRva,a::kSingleton);
        for(auto page:{std::size_t{0x3A2000},std::size_t{0x292000}}){DWORD old=0;Check(VirtualProtect(data+page,4096,PAGE_EXECUTE_READ,&old)!=0,"own code RX");}
        Check(FlushInstructionCache(GetCurrentProcess(),data,size)!=0,"own code cache");}
    ~Image(){if(data)VirtualFree(data,0,MEM_RELEASE);}
    template<std::size_t N>void copy(std::size_t at,const std::array<std::uint8_t,N>& bytes){std::memcpy(data+at,bytes.data(),N);}
    std::uint8_t*data=nullptr;
};
struct Failure{const void*identity;};
struct Probe {
    Image* image=nullptr;r::Router*router=nullptr;c::Binding binding{};const void*normal=nullptr;
    unsigned mouse_calls=0,key_calls=0;bool throw_mouse=false,throw_key=false,reenter=false;
    const Failure*exception_address=nullptr;r::Report nested{};
};
thread_local Probe* probe=nullptr;
void MaybeThrow(bool enabled){if(enabled){try{throw Failure{probe};}catch(const Failure&e){probe->exception_address=&e;throw;}}}
std::uint32_t MouseOriginal(const void* cache,std::uint32_t button){Check(probe!=nullptr,"owned mouse probe");++probe->mouse_calls;
    if(probe->reenter){probe->reenter=false;
        probe->router->Invoke({probe->binding,100,r::Mode::NeutralizeAdmittedQuery},{r::Kind::Action,nullptr,0,0},probe->nested);}
    MaybeThrow(probe->throw_mouse);
    return reinterpret_cast<m::MouseQuery>(probe->image->data+0x3A2920)(cache,button);}
template<unsigned I>std::uint64_t KeyOriginal(const void* cache,std::uint32_t argument,std::uint32_t flag){
    Check(probe!=nullptr,"owned key probe");++probe->key_calls;MaybeThrow(probe->throw_key);
    return reinterpret_cast<k::OriginalQuery>(probe->image->data+KEY_RVA[I])(cache,argument,flag);}
struct Fixture {
    Image image;std::array<std::uint8_t,c::kRawKeyboardSize+16>raw{};std::array<std::uint8_t,0x110>mapping{};
    r::Router router;r::Config config;Probe own;std::uint64_t sequence=0;
    explicit Fixture(bool bind=true){
        router_fixture_tls_extent[63]=9;const auto slots=__readgsqword(0x58);
        const auto data=Get<std::uintptr_t>(reinterpret_cast<void*>(slots),std::size_t(_tls_index)*8);
        auto& s=config.source;s.binding.attempt[0]=1;s.binding.attachment[0]=2;s.binding.owner_generation=3;
        s.image={image.data,Image::size};s.buffers={{image.data+a::kNormalRva,c::kNormalSize},{image.data+a::kMouseRva,c::kMouseSize},{raw.data(),raw.size()}};
        s.mapping={mapping.data(),mapping.size()};s.tls_index=_tls_index;
        s.tls_slots={reinterpret_cast<std::uint8_t*>(slots),(std::size_t(_tls_index)+1)*8};s.tls_data={reinterpret_cast<std::uint8_t*>(data),0x14};
        Put<std::uint32_t>(image.data,a::kTlsIndexRva,_tls_index);
        Put<std::int32_t>(image.data,a::kInitGuardRva,std::min(std::int32_t{-2},Get<std::int32_t>(reinterpret_cast<void*>(data),0x10)));
        Put<std::uintptr_t>(image.data,a::kMapPointerRva,reinterpret_cast<std::uintptr_t>(mapping.data()));
        Put<std::uintptr_t>(image.data,a::kNormalRva,reinterpret_cast<std::uintptr_t>(raw.data()));
        Put<std::uint32_t>(image.data,a::kActiveRva,1);Put<std::uint32_t>(mapping.data(),8,0x1c);
        raw.fill(0);Put<std::uint32_t>(raw.data(),0x50,0xff);Put<std::uint32_t>(raw.data(),0x54,2);raw[0x158+0x1c]=0x80;
        std::fill(raw.begin()+c::kRawKeyboardSize,raw.end(),std::uint8_t{0xc7});
        config.mouse_original=&MouseOriginal;config.keyboard_originals={&KeyOriginal<0>,&KeyOriginal<1>,&KeyOriginal<2>,&KeyOriginal<3>,&KeyOriginal<4>,&KeyOriginal<5>};
        own.image=&image;own.router=&router;own.binding=s.binding;own.normal=s.buffers.normal.data;probe=&own;
        seed(r::Kind::KeyPress);if(bind)Check(router.Bind(config).status==r::Status::Ok,"all frozen bridges share one binding");
    }
    ~Fixture(){probe=nullptr;}
    void seed(r::Kind kind){auto*n=config.source.buffers.normal.data;auto*m=config.source.buffers.mouse.data;
        Put<std::uint32_t>(n,8,0);Put<std::uint32_t>(n,12,1);n[0x20]=1;n[0x64]=1;
        Put<std::uint32_t>(n,0x58,kind==r::Kind::KeyRelease?0u:0x1cu);Put<std::uint32_t>(n,0x5c,kind==r::Kind::KeyRelease?0x1cu:0u);
        Put<std::uint32_t>(m,0,0);Put<std::uint32_t>(m,4,1);Put<std::uint32_t>(m,0x10,1);}
    r::Request request(r::Mode mode=r::Mode::ForwardUntouched){return{config.source.binding,++sequence,mode};}
    r::Call call(r::Kind kind)const{r::Call call;call.kind=kind;
        call.observed_cache=kind==r::Kind::Mouse?config.source.buffers.mouse.data:kind==r::Kind::Action?nullptr:config.source.buffers.normal.data;
        if(kind==r::Kind::Mouse)call.argument=1;
        else if(kind>=r::Kind::KeyRelease&&kind<=r::Kind::KeyRepeat){call.argument=0x1c;call.flag=kind==r::Kind::KeyRepeat?1u:0u;}
        else if(kind==r::Kind::ModifierMasked){call.argument=0x11;call.flag=1;}
        return call;}
    std::uint64_t entry(r::Kind kind){const auto q=call(kind);switch(kind){
        case r::Kind::Mouse:return r::Mouse(q.observed_cache,q.argument);
        case r::Kind::KeyRelease:return r::KeyRelease(q.observed_cache,q.argument);
        case r::Kind::KeyPress:return r::KeyPress(q.observed_cache,q.argument);
        case r::Kind::KeyRepeat:return r::KeyRepeat(q.observed_cache,q.argument,q.flag);
        case r::Kind::Modifier11:return r::Modifier11(q.observed_cache);
        case r::Kind::ModifierMasked:return r::ModifierMasked(q.observed_cache,q.argument,q.flag);
        case r::Kind::Modifier22:return r::Modifier22(q.observed_cache);
        case r::Kind::Action:return r::Action(q.argument);
        default:throw std::runtime_error("fixture route");}}
};
constexpr r::Kind KINDS[]={r::Kind::Mouse,r::Kind::Modifier22,r::Kind::Action,r::Kind::KeyPress,
    r::Kind::ModifierMasked,r::Kind::KeyRelease,r::Kind::KeyRepeat,r::Kind::Modifier11};
void NoAuthority(const r::Report&v){Check(!v.complete_native_input_hold&&!v.native_hook_installed&&!v.physical_release_proven&&!v.authorize_release,"no release authority");}
void Forward(){Fixture f;for(auto kind:KINDS){f.seed(kind);const auto physical=f.raw;r::Request request;request.binding=f.config.source.binding;request.cycle=++f.sequence;
    r::ScopedRoute route(f.router,request);const auto result=f.entry(kind);const auto&v=route.report();
    Check(v.status==r::Status::Ok&&v.original_completed&&v.delegated&&v.cycle_consumed,"actual original delegated");
    Check((result&0xff)==1&&result==v.original_return&&f.raw==physical,"default forwards native result and preserves physical source");
    Check(v.previous_cycle+1==v.cycle,"global sequence across all routes");NoAuthority(v);}
    Check(f.own.mouse_calls==1&&f.own.key_calls==6,"one native leaf invocation per routed callback; action native direct");}
void Neutral(){Fixture f;for(unsigned round=0;round<2;++round)for(auto kind:KINDS){f.seed(kind);const auto physical=f.raw;
    r::ScopedRoute route(f.router,f.request(r::Mode::NeutralizeAdmittedQuery));const auto result=f.entry(kind);const auto&v=route.report();
    Check(v.status==r::Status::Ok&&v.original_completed&&(result&0xff)==0,"all admitted queries neutral via their real bridge");
    Check(v.previous_cycle+1==v.cycle&&f.raw==physical,"interleaved publication never changes physical keys");
    if(kind==r::Kind::Action)Check(v.action.original_value==1&&v.action.source_bundle_unchanged,"actual action body and getter executed");
    if(kind>=r::Kind::Modifier11&&kind<=r::Kind::Modifier22)Check((v.original_return&0xff)==1&&(result&~0xffull)==(v.original_return&~0xffull),"modifier only AL substituted");NoAuthority(v);}}
void CrossRouteReplay(){Fixture f;r::Report out;const auto first=f.request();f.router.Invoke(first,f.call(r::Kind::Mouse),out);
    Check(out.status==r::Status::Ok,"first mouse");f.router.Invoke(first,f.call(r::Kind::Modifier22),out);
    Check(out.status==r::Status::StaleCycle&&!out.delegated&&!out.cycle_consumed,"replay cannot move to other bridge");
    auto zero=f.request();zero.cycle=0;f.router.Invoke(zero,f.call(r::Kind::Action),out);Check(out.status==r::Status::StaleCycle,"zero cycle refused");
    f.router.Invoke(f.request(),f.call(r::Kind::Action),out);Check(out.status==r::Status::Ok,"sequence gap allowed");}
void StaleIdentity(){Fixture f;r::Report out;for(unsigned field=0;field<3;++field){auto request=f.request();
    if(field==0)request.binding.attempt[0]++;else if(field==1)request.binding.attachment[0]++;else request.binding.owner_generation++;
    for(auto kind:KINDS){f.router.Invoke(request,f.call(kind),out);Check(out.status==r::Status::StaleBinding&&!out.cycle_consumed&&!out.delegated,"each identity part checked on every route");}}
    Check(f.own.mouse_calls==0&&f.own.key_calls==0,"no original for stale identities");}
void WrongThread(){Fixture f;r::Report out;const auto request=f.request();std::thread t([&]{f.router.Invoke(request,f.call(r::Kind::Action),out);});t.join();
    Check(out.status==r::Status::WrongThread&&!out.delegated&&!out.cycle_consumed,"wrong thread refused before native TLS access");}
void InvalidRoutes(){Fixture f;r::Report out;auto request=f.request();const r::Call bad[]={
    {r::Kind::Count,nullptr,0,0},{r::Kind::Mouse,f.config.source.buffers.mouse.data,3,0},
    {r::Kind::KeyPress,f.config.source.buffers.normal.data,0x100,0},
    {r::Kind::ModifierMasked,f.config.source.buffers.normal.data,0x33,0},
    {r::Kind::KeyRepeat,f.config.source.buffers.normal.data,0x1c,2},{r::Kind::Action,nullptr,31,0}};
    for(const auto&call:bad){f.router.Invoke(request,call,out);Check((out.status==r::Status::UnknownRoute||out.status==r::Status::InvalidArguments)&&!out.cycle_consumed&&!out.delegated,"unknown values refused before claim");}
    auto mode=request;mode.mode=static_cast<r::Mode>(9);f.router.Invoke(mode,f.call(r::Kind::Mouse),out);Check(out.status==r::Status::InvalidMode,"unknown mode");
    f.router.Invoke(request,f.call(r::Kind::Mouse),out);Check(out.status==r::Status::Ok,"invalid requests did not consume sequence");}
void WrongSources(){Fixture f;r::Report out;auto request=f.request();for(auto kind:{r::Kind::Mouse,r::Kind::KeyPress,r::Kind::Action}){
    auto call=f.call(kind);call.observed_cache=kind==r::Kind::KeyPress?f.config.source.buffers.mouse.data:f.config.source.buffers.normal.data;
    f.router.Invoke(request,call,out);Check(out.status==r::Status::WrongSource&&!out.cycle_consumed&&!out.delegated,"wrong actual native pointer");}}
void LayoutGuards(){Fixture f;r::Report out;auto request=f.request();auto*n=f.config.source.buffers.normal.data;auto*m=f.config.source.buffers.mouse.data;
    Put<std::uint32_t>(m,0,0xffffffffu);f.router.Invoke(request,f.call(r::Kind::Mouse),out);Check(out.status==r::Status::InvalidSourceLayout&&!out.delegated,"forwarding also bounds native mouse indices");
    f.seed(r::Kind::Mouse);Put<std::uintptr_t>(n,0,0);f.router.Invoke(request,f.call(r::Kind::Mouse),out);Check(out.status==r::Status::InvalidSourceLayout,"shared raw binding guarded even on mouse");
    Put<std::uintptr_t>(n,0,reinterpret_cast<std::uintptr_t>(f.raw.data()));Put<std::uint32_t>(f.raw.data(),0x54,127);
    f.router.Invoke(request,f.call(r::Kind::Modifier22),out);Check(out.status==r::Status::InvalidSourceLayout&&!out.cycle_consumed,"queue extent drift");}
void DelegateFailure(){Fixture f;r::Report out;const auto request=f.request();const auto map=Get<std::uintptr_t>(f.image.data,a::kMapPointerRva);
    Put<std::uintptr_t>(f.image.data,a::kMapPointerRva,map+8);f.router.Invoke(request,f.call(r::Kind::Action),out);
    Check(out.status==r::Status::DelegateRejected&&out.action.status==a::Status::WrongSource&&out.cycle_consumed&&!out.original_started,"child diagnostics preserved and failed cycle consumed");
    Put<std::uintptr_t>(f.image.data,a::kMapPointerRva,map);f.router.Invoke(request,f.call(r::Kind::Mouse),out);Check(out.status==r::Status::StaleCycle,"failed delegated cycle never reused cross-route");
    f.router.Invoke(f.request(),f.call(r::Kind::Action),out);Check(out.status==r::Status::Ok,"subsequent explicit cycle remains possible");}
void Exceptions(){Fixture f;for(auto mode:{r::Mode::ForwardUntouched,r::Mode::NeutralizeAdmittedQuery})for(auto kind:{r::Kind::Mouse,r::Kind::KeyPress}){
    f.seed(kind);f.own.throw_mouse=kind==r::Kind::Mouse;f.own.throw_key=kind==r::Kind::KeyPress;
    const auto physical=f.raw;auto request=f.request(mode);bool caught=false;
    {r::ScopedRoute route(f.router,request);try{f.entry(kind);}catch(const Failure&e){caught=true;Check(&e==f.own.exception_address&&e.identity==&f.own,"original C++ exception object preserved");}
        const auto&v=route.report();Check(caught&&v.status==r::Status::OriginalException&&v.original_started&&!v.original_completed&&v.cycle_consumed,"exception no fake completion, claim retained");
        Check(f.raw==physical,"exception after neutral publication does not clear held input");}
    f.own.throw_mouse=false;f.own.throw_key=false;r::Report out;f.router.Invoke(request,f.call(r::Kind::Action),out);Check(out.status==r::Status::StaleCycle,"exception replay rejected");
    f.router.Invoke(f.request(),f.call(r::Kind::Action),out);Check(out.status==r::Status::Ok,"router and child in-flight flags cleaned by C++ unwind");}}
void Reentrant(){Fixture f;f.own.reenter=true;r::Report out;f.router.Invoke(f.request(),f.call(r::Kind::Mouse),out);
    Check(out.status==r::Status::Ok&&f.own.nested.status==r::Status::Reentrant&&!f.own.nested.delegated&&!f.own.nested.cycle_consumed,"cross-family reentry blocked");
    auto next=f.request();f.router.Invoke(next,f.call(r::Kind::Action),out);Check(out.status==r::Status::Ok&&out.previous_cycle==1,"reentry did not skip sequence to 100");}
void FailedBind(){Fixture f(false);const auto guard=Get<std::int32_t>(f.image.data,a::kInitGuardRva);Put<std::int32_t>(f.image.data,a::kInitGuardRva,0);
    auto report=f.router.Bind(f.config);Check(report.status==r::Status::BindRejected&&report.mouse==m::Status::Ok&&report.keyboard==k::Status::Ok&&report.action==a::Status::UninitializedSingleton,"partial bind diagnosed");
    r::Report out;f.router.Invoke(f.request(),f.call(r::Kind::Mouse),out);Check(out.status==r::Status::NotBound&&!out.delegated,"partial configuration cannot execute anything");
    Put<std::int32_t>(f.image.data,a::kInitGuardRva,guard);Check(f.router.Bind(f.config).status==r::Status::BindAlreadyAttempted,"failed router cannot be rebound silently");}
void OwnEntryTarget(){Fixture f(false);auto config=f.config;config.mouse_original=&r::Mouse;Check(f.router.Bind(config).status==r::Status::InvalidTarget,"router cannot be its own original");
    r::Router second;config=f.config;config.keyboard_originals[0]=reinterpret_cast<k::OriginalQuery>(&r::Modifier22);Check(second.Bind(config).status==r::Status::InvalidTarget,"router key original cycle rejected");}
void ScopedSequenceAndProgress(){Fixture f;std::atomic<unsigned> worker{0};unsigned updates=0;std::thread task([&]{for(unsigned i=0;i<300;++i)++worker;});
    {r::ScopedRoute outer(f.router,f.request());Check((f.entry(r::Kind::Modifier22)&0xff)==1,"outer default forward");
        {r::ScopedRoute inner(f.router,f.request(r::Mode::NeutralizeAdmittedQuery));Check(f.entry(r::Kind::Action)==0,"inner neutral");}
        f.entry(r::Kind::Mouse);Check(outer.report().status==r::Status::StaleCycle,"restored consumed outer route cannot replay");++updates;}
    task.join();const auto n=r::UnroutedCallCountForThisThread();Check(r::Action(0)==0&&r::UnroutedCallCountForThisThread()==n+1,"missing route diagnostic");
    {r::ScopedRoute next(f.router,f.request());Check(r::Action(0)==1&&next.report().status==r::Status::Ok,"fresh explicit route still works");}
    Check(updates==1&&worker==300,"owned work continues, no native scheduling claim");}
}
int main(int argc,char**argv){if(argc!=2)return 2;struct Case{const char*name;void(*run)();};
    const Case cases[]={{"interleaved_default_forward_actual_leaves",Forward},{"interleaved_neutral_actual_leaves",Neutral},
        {"cross_route_cycle_replay",CrossRouteReplay},{"all_identity_components_every_route",StaleIdentity},{"cross_thread_rejection",WrongThread},
        {"unknown_route_arguments_mode",InvalidRoutes},{"incoming_cache_identity",WrongSources},{"shared_source_layout",LayoutGuards},
        {"delegate_failure_keeps_claim_and_diagnostics",DelegateFailure},{"mouse_keyboard_exception_identity",Exceptions},
        {"cross_family_reentrancy",Reentrant},{"partial_binding_never_runs",FailedBind},{"self_original_refused",OwnEntryTarget},
        {"scoped_sequence_and_owned_progress",ScopedSequenceAndProgress}};
    std::vector<std::string> passed;std::string failed;for(const auto&item:cases){try{item.run();passed.emplace_back(item.name);}catch(const std::exception&e){failed=std::string(item.name)+": "+e.what();break;}}
    std::ofstream file(argv[1]);file<<"{\"schema\":\"san14.native-input-router-fixture.v1\",\"result\":\""<<(failed.empty()?"PASS":"FAIL")<<"\",\"cases\":"<<passed.size()<<",\"passed\":[";
    for(std::size_t i=0;i<passed.size();++i){if(i)file<<',';file<<'"'<<passed[i]<<'"';}
    file<<"],\"failure\":\""<<failed<<"\",\"game_accessed\":false,\"device_accessed\":false,\"native_query_bodies_stubbed\":false,\"exception_injection\":\"owned C++ wrappers around mouse/key leaf\",\"full_input_hold\":false,\"authorize_release\":false}";
    std::cout<<(failed.empty()?"PASS":"FAIL")<<" "<<passed.size()<<" cases "<<failed<<'\n';return failed.empty()?0:1;}
