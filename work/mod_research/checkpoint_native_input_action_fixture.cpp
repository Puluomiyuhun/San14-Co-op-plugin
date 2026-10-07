#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <intrin.h>
#include "checkpoint_native_input_action_bridge.h"
#include "checkpoint_native_input_action_archived.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

// This fixture's own module supplies an actual native static TLS block. Nothing
// is installed in a game or another process, and GS or TLS pointers are not set.
extern "C" unsigned long _tls_index;
__declspec(thread) volatile unsigned char action_fixture_tls_extent[64];
namespace a=checkpoint_native_input_action;
namespace c=checkpoint_native_input;
namespace {
void Check(bool b,const char* why){if(!b)throw std::runtime_error(why);}
template<class T>void Put(void* p,std::size_t at,T v){std::memcpy(static_cast<std::uint8_t*>(p)+at,&v,sizeof(v));}
template<class T>T Get(const void*p,std::size_t at){T v;std::memcpy(&v,static_cast<const std::uint8_t*>(p)+at,sizeof(v));return v;}
class Image {
public:
    static constexpr std::size_t size=0x2040000;
    Image(){data=static_cast<std::uint8_t*>(VirtualAlloc(nullptr,size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));Check(data!=nullptr,"own image allocation");
        std::memcpy(data+a::kActionRva,a::kAction.data(),a::kAction.size());
        std::memcpy(data+a::kSingletonRva,a::kSingleton.data(),a::kSingleton.size());
        protect(a::kActionRva,PAGE_EXECUTE_READ);protect(a::kSingletonRva,PAGE_EXECUTE_READ);
        Check(FlushInstructionCache(GetCurrentProcess(),data,size)!=0,"own cache flush");}
    ~Image(){if(data)VirtualFree(data,0,MEM_RELEASE);}
    void corrupt(std::size_t rva){protect(rva,PAGE_READWRITE);data[rva]^=1;protect(rva,PAGE_EXECUTE_READ);}
    void protect(std::size_t rva,DWORD mode){DWORD old=0;Check(VirtualProtect(data+(rva&~std::size_t{4095}),4096,mode,&old)!=0,"owned code page protection");}
    std::uint8_t* data=nullptr;
};
struct Fixture {
    Image image;
    std::array<std::uint8_t,c::kRawKeyboardSize+16> raw{};
    std::array<std::uint8_t,0x110> mapping{};
    a::Config config;a::Bridge bridge;std::uint64_t cycle=0;
    Fixture(){
        action_fixture_tls_extent[63]=7;
        const auto slots=__readgsqword(0x58);
        const auto tls=Get<std::uintptr_t>(reinterpret_cast<void*>(slots),std::size_t(_tls_index)*8);
        // The module contains a 64-byte TLS object. +10 belongs to its valid
        // native block; read it, but do not overwrite any CRT/static TLS bytes.
        const auto epoch=Get<std::int32_t>(reinterpret_cast<void*>(tls),0x10);
        config.binding.attempt[0]=1;config.binding.attachment[0]=2;config.binding.owner_generation=3;
        config.image={image.data,Image::size};
        config.buffers={{image.data+a::kNormalRva,c::kNormalSize},{image.data+a::kMouseRva,c::kMouseSize},{raw.data(),raw.size()}};
        config.mapping={mapping.data(),mapping.size()};config.tls_index=_tls_index;
        config.tls_slots={reinterpret_cast<std::uint8_t*>(slots),(std::size_t(_tls_index)+1)*8};
        config.tls_data={reinterpret_cast<std::uint8_t*>(tls),0x14};
        Put<std::uint32_t>(image.data,a::kTlsIndexRva,_tls_index);
        Put<std::int32_t>(image.data,a::kInitGuardRva,std::min(std::int32_t{-2},epoch));
        Put<std::uintptr_t>(image.data,a::kMapPointerRva,reinterpret_cast<std::uintptr_t>(mapping.data()));
        Put<std::uintptr_t>(image.data,a::kNormalRva,reinterpret_cast<std::uintptr_t>(raw.data()));
        Put<std::uint32_t>(image.data,a::kNormalRva+8,0);Put<std::uint32_t>(image.data,a::kNormalRva+12,1);
        Put<std::uint32_t>(image.data,a::kMouseRva,0);Put<std::uint32_t>(image.data,a::kMouseRva+4,1);
        Put<std::uint32_t>(image.data,a::kActiveRva,1);Put<std::uint32_t>(raw.data(),0x54,2);
        std::fill(raw.begin()+c::kRawKeyboardSize,raw.end(),std::uint8_t{0xC7});
        std::fill(mapping.begin()+0x100,mapping.end(),std::uint8_t{0xD8});
        Check(bridge.Bind(config)==a::Status::Ok,"strict native source bind");
    }
    void keys(std::uint32_t action,std::uint32_t first,std::uint32_t second){Put<std::uint32_t>(mapping.data(),8+action*8,first);Put<std::uint32_t>(mapping.data(),12+action*8,second);}
    a::Request request(a::Mode mode=a::Mode::NeutralizeAuditedAction){return{config.binding,++cycle,mode};}
    std::uint32_t call(std::uint32_t action,a::Report& r,a::Mode mode=a::Mode::NeutralizeAuditedAction){return bridge.Invoke(request(mode),action,r);}
};
void NoAuthority(const a::Report&r){Check(!r.native_hook_installed&&!r.complete_native_input_hold&&!r.physical_release_proven,"no native authority inferred");}
void OriginalChain(){Fixture f;f.keys(0,0x1c,0);f.raw[0x158+0x1c]=0x80;
    const auto raw=f.raw;const auto map=f.mapping;std::vector<std::uint8_t> image(f.image.data,f.image.data+Image::size);
    a::ScopedRoute route(f.bridge,f.request(a::Mode::ForwardUntouched));
    Check(a::ActionQuery(0)==1,"actual action plus singleton TLS returns held key");
    const auto&r=route.report();Check(r.status==a::Status::Ok&&r.original_completed&&r.source_bundle_unchanged,"whole original query normally returned");
    Check(f.raw==raw&&f.mapping==map&&std::memcmp(image.data(),f.image.data,image.size())==0,"full owned image and sources unchanged by real native chain");NoAuthority(r);}
void NeutralPhysical(){Fixture f;f.keys(1,0x1c,0);f.raw[0x158+0x1c]=0x80;const auto raw=f.raw;const auto map=f.mapping;a::Report r;
    Check(f.call(1,r)==0&&r.original_value==1&&r.used_neutral_shadow&&r.status==a::Status::Ok,"native result recorded then neutralized by shadow");
    Check(f.raw==raw&&f.mapping==map&&r.source_bundle_unchanged,"held/event/mapping source retained");
    Check(f.call(1,r,a::Mode::ForwardUntouched)==1&&!r.used_neutral_shadow,"held physical input still forwards afterward");NoAuthority(r);}
void SecondMaximum(){Fixture f;f.keys(30,0,0xff);f.raw[0x257]=1;a::Report r;
    Check(f.call(30,r,a::Mode::ForwardUntouched)==1&&r.codes[1]==0xff,"last action second binding last raw key");
    Check(f.call(30,r)==0&&r.original_value==1,"maximum bounded key neutral");}
void ModifierMappings(){Fixture f;a::Report r;
    for(std::uint32_t code=0x101;code<=0x104;++code){f.keys(2,code,0);Put<std::uint32_t>(f.raw.data(),0x50,1u<<(code-0x101));
        Check(f.call(2,r,a::Mode::ForwardUntouched)==1,"native special mask uses any side");
        const auto raw=f.raw;Check(f.call(2,r)==0&&r.original_value==1&&f.raw==raw,"modifier action shadow with original held state");}}
void InactiveAndDisabled(){Fixture f;f.keys(3,0x20,0);f.raw[0x178]=1;Put<std::uint32_t>(f.image.data,a::kActiveRva,0);a::Report r;
    Check(f.call(3,r,a::Mode::ForwardUntouched)==0&&r.status==a::Status::Ok,"native inactive gate obeyed");
    Put<std::uint32_t>(f.image.data,a::kActiveRva,1);f.keys(3,0,0);
    Check(f.call(3,r,a::Mode::ForwardUntouched)==0&&r.status==a::Status::Ok,"disabled bindings return false");}
void InvalidAction(){Fixture f;a::Report r;const auto raw=f.raw;const auto map=f.mapping;
    for(auto action:{31u,0xffffffffu})Check(f.call(action,r)==0&&r.status==a::Status::InvalidAction&&!r.original_started,"invalid action never invokes singleton");
    Check(f.raw==raw&&f.mapping==map,"bad action writes nothing");}
void UnknownMapping(){Fixture f;a::Report r;for(auto code:{0x100u,0x105u,0xffffffffu}){
    f.keys(4,code,0);const auto raw=f.raw;Check(f.call(4,r)==0&&r.status==a::Status::UnknownMapping&&!r.original_started&&f.raw==raw,"unsupported mapping rejected before native call");}}
void SlowInitialization(){Fixture f;a::Report r;const auto ready=Get<std::int32_t>(f.image.data,a::kInitGuardRva);
    for(auto state:{0,-1}){Put<std::int32_t>(f.image.data,a::kInitGuardRva,state);
        Check(f.call(0,r)==0&&r.status==a::Status::UninitializedSingleton&&!r.original_started,"lazy creation branch never called");}
    Put<std::int32_t>(f.image.data,a::kInitGuardRva,ready);Check(f.call(0,r)==0&&r.status==a::Status::Ok,"initialized original usable after rejection");}
void TlsAndThread(){Fixture f;a::Report r;Put<std::uint32_t>(f.image.data,a::kTlsIndexRva,f.config.tls_index+1);
    Check(f.call(0,r)==0&&r.status==a::Status::WrongTls&&!r.original_started,"unexpected module TLS index blocked");
    Put<std::uint32_t>(f.image.data,a::kTlsIndexRva,f.config.tls_index);auto req=f.request();
    std::thread t([&]{f.bridge.Invoke(req,0,r);});t.join();Check(r.status==a::Status::WrongThread&&!r.original_started,"different owner never reads another thread TLS");}
void CodeGuards(){for(auto at:{a::kActionRva,a::kSingletonRva}){Fixture f;f.image.corrupt(at);a::Report r;
    Check(f.call(0,r)==0&&r.status==a::Status::CodeMismatch&&!r.original_started,"actual code drift rejected");}}
void PointerAndGate(){Fixture f;a::Report r;const auto rawptr=Get<std::uintptr_t>(f.image.data,a::kNormalRva);
    Put<std::uintptr_t>(f.image.data,a::kNormalRva,0);Check(f.call(0,r)==0&&r.status==a::Status::WrongSource&&!r.original_started,"raw pointer drift");
    Put<std::uintptr_t>(f.image.data,a::kNormalRva,rawptr);const auto map=Get<std::uintptr_t>(f.image.data,a::kMapPointerRva);
    Put<std::uintptr_t>(f.image.data,a::kMapPointerRva,map+8);Check(f.call(0,r)==0&&r.status==a::Status::WrongSource&&!r.original_started,"mapping pointer drift");
    Put<std::uintptr_t>(f.image.data,a::kMapPointerRva,map);Put<std::uint32_t>(f.image.data,a::kActiveRva,2);
    Check(f.call(0,r)==0&&r.status==a::Status::InvalidLayout&&!r.original_started,"unknown active gate");}
void BindingAndCycle(){Fixture f;a::Report r;auto req=f.request();req.binding.attachment[0]++;
    Check(f.bridge.Invoke(req,0,r)==0&&r.status==a::Status::StaleBinding&&!r.original_started,"stale attachment");
    req=f.request();f.bridge.Invoke(req,0,r);Check(r.status==a::Status::Ok,"initial neutral publication");
    f.bridge.Invoke(req,0,r);Check(r.status==a::Status::PublicationRejected&&!r.original_started,"duplicate cycle no action");}
void ExtentsAndAlias(){Fixture f;auto cfg=f.config;a::Bridge short_view;cfg.mapping.size=255;
    Check(short_view.Bind(cfg)==a::Status::InvalidSpan,"short map refused");a::Bridge alias;cfg=f.config;cfg.mapping={f.raw.data(),f.raw.size()};
    Check(alias.Bind(cfg)==a::Status::Overlap,"overlapping source views refused");a::Bridge badtls;cfg=f.config;cfg.tls_slots.size=0;
    Check(badtls.Bind(cfg)==a::Status::InvalidSpan,"short TLS slots refused before access");}
void RouteAndProgress(){Fixture f;f.keys(0,1,0);f.raw[0x159]=1;std::atomic<unsigned> worker{0};unsigned updates=0;
    std::thread task([&]{for(unsigned i=0;i<300;++i)++worker;});
    {a::ScopedRoute outer(f.bridge,f.request(a::Mode::ForwardUntouched));Check(a::ActionQuery(0)==1,"outer forward");
        {a::ScopedRoute inner(f.bridge,f.request());Check(a::ActionQuery(0)==0,"inner shadow");}
        Check(a::ActionQuery(0)==1,"outer restored");++updates;}
    task.join();const auto n=a::UnroutedCallCountForThisThread();Check(a::ActionQuery(0)==0&&a::UnroutedCallCountForThisThread()==n+1,"missing route tracked");
    Check(updates==1&&worker==300,"owned engine and worker continue, not native scheduling proof");}
}
int main(int argc,char**argv){if(argc!=2)return 2;
    struct Case{const char*name;void(*run)();};
    const Case cases[]={{"actual_action_and_tls_singleton",OriginalChain},{"neutral_preserves_physical_source",NeutralPhysical},
        {"second_binding_last_action_key",SecondMaximum},{"four_native_modifier_mappings",ModifierMappings},{"inactive_disabled",InactiveAndDisabled},
        {"invalid_action",InvalidAction},{"unknown_mapping",UnknownMapping},{"lazy_initialization_refused",SlowInitialization},
        {"module_tls_and_owner_thread",TlsAndThread},{"actual_code_guard",CodeGuards},{"source_pointer_and_gate",PointerAndGate},
        {"binding_and_cycle",BindingAndCycle},{"extent_and_alias",ExtentsAndAlias},{"explicit_route_and_progress",RouteAndProgress}};
    std::vector<std::string> passed;std::string failed;
    for(const auto&item:cases){try{item.run();passed.emplace_back(item.name);}catch(const std::exception&e){failed=std::string(item.name)+": "+e.what();break;}}
    std::ofstream file(argv[1]);file<<"{\"schema\":\"san14.native-input-action-fixture.v1\",\"result\":\""<<(failed.empty()?"PASS":"FAIL")<<"\",\"cases\":"<<passed.size()<<",\"passed\":[";
    for(std::size_t i=0;i<passed.size();++i){if(i)file<<',';file<<'"'<<passed[i]<<'"';}
    file<<"],\"failure\":\""<<failed<<"\",\"native_action_stubbed\":false,\"native_singleton_stubbed\":false,\"game_accessed\":false,\"physical_input_accessed\":false,\"full_input_hold\":false}";
    std::cout<<(failed.empty()?"PASS":"FAIL")<<" "<<passed.size()<<" cases "<<failed<<'\n';return failed.empty()?0:1;}
