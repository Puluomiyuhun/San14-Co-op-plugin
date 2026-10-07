#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include "checkpoint_native_input_keyboard_bridge.h"
#include "checkpoint_native_input_keyboard_archived.h"
#include <array>
#include <atomic>
#include <cstring>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace k=checkpoint_native_input_keyboard;
namespace c=checkpoint_native_input;
namespace {
void Check(bool v,const char* why){if(!v)throw std::runtime_error(why);}
template<class T> void Put(void* b,std::size_t at,T value){std::memcpy(static_cast<std::uint8_t*>(b)+at,&value,sizeof(value));}
template<class T> T Get(const void* b,std::size_t at){T v;std::memcpy(&v,static_cast<const std::uint8_t*>(b)+at,sizeof(v));return v;}
class Leaves {
public:
    Leaves(){
        page_=VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);Check(page_!=nullptr,"owned allocation");
        copy(0,k::kRelease);copy(1,k::kPress);copy(2,k::kRepeat);
        copy(3,k::kModifier11);copy(4,k::kModifierMasked);copy(5,k::kModifier22);
        DWORD old=0;Check(VirtualProtect(page_,4096,PAGE_EXECUTE_READ,&old)!=0,"owned executable protection");
        Check(FlushInstructionCache(GetCurrentProcess(),page_,4096)!=0,"owned instruction cache");
    }
    ~Leaves(){if(page_)VirtualFree(page_,0,MEM_RELEASE);}
    k::OriginalQuery at(k::Query q)const{return reinterpret_cast<k::OriginalQuery>(static_cast<std::uint8_t*>(page_)+static_cast<unsigned>(q)*128);}
private:
    template<std::size_t N> void copy(unsigned i,const std::array<std::uint8_t,N>& bytes){std::memcpy(static_cast<std::uint8_t*>(page_)+i*128,bytes.data(),N);}
    void* page_=nullptr;
};
struct Failure {const void* identity;};
struct Probe {
    Leaves* leaves=nullptr;k::Query query=k::Query::Count;k::QueryBridge* bridge=nullptr;c::Binding binding{};
    unsigned calls=0;const void* normal=nullptr;std::uint32_t argument=0,flag=0;
    bool throws=false,reenter=false,constant=false;const Failure* exception_address=nullptr;
    std::uint64_t value=0x1122334455667701ull;k::Status nested=k::Status::NotBound;
};
thread_local Probe* probe=nullptr;
std::uint64_t Target(const void* p,std::uint32_t a,std::uint32_t f){
    Check(probe!=nullptr,"probe lifetime");++probe->calls;probe->normal=p;probe->argument=a;probe->flag=f;
    if(probe->reenter){probe->reenter=false;k::Report r;
        const auto value=probe->bridge->Invoke({probe->binding,999,k::Mode::NeutralizeAuditedQuery},probe->query,p,a,f,r);
        Check(value==0,"reentrant rejected return");probe->nested=r.status;}
    if(probe->throws){try{throw Failure{probe};}catch(const Failure& failure){probe->exception_address=&failure;throw;}}
    if(probe->constant)return probe->value;
    return probe->leaves->at(probe->query)(p,a,f);
}
struct Fixture {
    std::array<std::uint8_t,c::kNormalSize+16> normal{};
    std::array<std::uint8_t,c::kMouseSize+16> mouse{};
    std::array<std::uint8_t,c::kRawKeyboardSize+16> raw{};
    c::Binding binding{};k::QueryBridge bridge;Probe own;std::uint64_t cycle=0;
    explicit Fixture(Leaves& leaves){
        normal.fill(0xA5);mouse.fill(0xB6);raw.fill(0xC7);
        Put<std::uintptr_t>(normal.data(),0,reinterpret_cast<std::uintptr_t>(raw.data()));
        Put<std::uint32_t>(normal.data(),8,0);Put<std::uint32_t>(normal.data(),12,1);
        Put<std::uint32_t>(mouse.data(),0,0);Put<std::uint32_t>(mouse.data(),4,1);
        Put<std::uint32_t>(raw.data(),0x50,0x22);Put<std::uint32_t>(raw.data(),0x54,2);
        Put<std::uint32_t>(normal.data(),0x58,0x1c);Put<std::uint32_t>(normal.data(),0x5c,0);
        binding.attempt[0]=1;binding.attachment[0]=2;binding.owner_generation=3;
        k::Targets targets{};targets.fill(&Target);
        Check(bridge.Bind(binding,{{normal.data(),normal.size()},{mouse.data(),mouse.size()},{raw.data(),raw.size()}},targets)==k::Status::Ok,"bind");
        own.leaves=&leaves;own.bridge=&bridge;own.binding=binding;probe=&own;
    }
    ~Fixture(){probe=nullptr;}
    k::Request request(k::Mode mode=k::Mode::NeutralizeAuditedQuery){return{binding,++cycle,mode};}
    std::uint64_t invoke(k::Query q,std::uint32_t a,std::uint32_t f,k::Report& r,k::Mode mode=k::Mode::NeutralizeAuditedQuery){
        own.query=q;return bridge.Invoke(request(mode),q,normal.data(),a,f,r);
    }
};
void NotAuthority(const k::Report& r){Check(!r.complete_native_input_hold&&!r.physical_release_proven&&!r.native_hook_installed,"no authority");}

void Modifiers(Leaves& leaves){Fixture f(leaves);k::Report r;
    for(auto q:{k::Query::Modifier11,k::Query::Modifier22}){
        Put<std::uint32_t>(f.raw.data(),0x50,0xff);const auto raw=f.raw;
        f.own.query=q;std::uint64_t original=0;
        {k::ScopedRoute route(f.bridge,f.request(k::Mode::ForwardUntouched));
            original=q==k::Query::Modifier11?k::Modifier11(f.normal.data()):k::Modifier22(f.normal.data());}
        Check((original&0xff)==1,"real modifier true");
        const auto neutral=f.invoke(q,0,0,r);Check((neutral&0xff)==0&&r.status==k::Status::Ok,"modifier neutral");
        Check(r.original_rax==original&&(neutral&~0xffull)==(original&~0xffull),"opaque RAX preserved except AL");
        Check(r.used_neutral_shadow&&f.raw==raw&&r.original_cache==f.normal.data(),"raw held source preserved");NotAuthority(r);
    }Check(f.own.calls==4,"one original per query");}
void AnyAll(Leaves& leaves){Fixture f(leaves);k::Report r;Put<std::uint32_t>(f.raw.data(),0x50,0x01);
    f.own.query=k::Query::ModifierMasked;
    {k::ScopedRoute route(f.bridge,f.request(k::Mode::ForwardUntouched));
        Check((k::ModifierMasked(f.normal.data(),0x11,0)&0xff)==1,"any native bit through exact entry");}
    Check((f.invoke(k::Query::ModifierMasked,0x11,1,r,k::Mode::ForwardUntouched)&0xff)==0,"all native bits");
    for(auto mask:{0x11u,0x22u,0x44u,0x88u})for(auto all:{0u,1u}){
        Put<std::uint32_t>(f.raw.data(),0x50,mask);const auto source=f.raw;
        Check((f.invoke(k::Query::ModifierMasked,mask,all,r)&0xff)==0,"all known masks neutral");
        Check((r.original_rax&0xff)==1&&f.own.argument==mask&&f.own.flag==all&&f.raw==source,"exact native masked args");
    }}
void KeyLeaves(Leaves& leaves){Fixture f(leaves);k::Report r;
    for(auto q:{k::Query::Release,k::Query::Press,k::Query::Repeat}){
        Put<std::uint32_t>(f.normal.data(),0x58,q==k::Query::Release?0u:0x1cu);
        Put<std::uint32_t>(f.normal.data(),0x5c,q==k::Query::Release?0x1cu:0u);f.normal[0x20]=1;f.normal[0x64]=1;
        f.own.query=q;
        {k::ScopedRoute route(f.bridge,f.request(k::Mode::ForwardUntouched));
            const auto original=q==k::Query::Release?k::Release(f.normal.data(),0x1c):
                q==k::Query::Press?k::Press(f.normal.data(),0x1c):k::Repeat(f.normal.data(),0x1c,1);
            Check((original&0xff)==1,"archived keyboard edge/repeat true through exact entry");}
        const auto source=f.raw;Check((f.invoke(q,0x1c,1,r)&0xff)==0&&r.status==k::Status::Ok,"neutral before real key leaf");
        Check(!r.used_neutral_shadow&&f.raw==source&&r.original_completed,"key original normally executed");NotAuthority(r);
    }}
void SpecialKeys(Leaves& leaves){Fixture f(leaves);k::Report r;
    for(std::uint32_t key=0x101;key<=0x104;++key){Put<std::uint32_t>(f.normal.data(),0x58,key);Put<std::uint32_t>(f.normal.data(),0x5c,0);
        Check((f.invoke(k::Query::Press,key,0,r,k::Mode::ForwardUntouched)&0xff)==1,"special native cache key");
        Check((f.invoke(k::Query::Press,key,0,r)&0xff)==0&&r.status==k::Status::Ok,"known special neutral");}}
void InvalidQueries(Leaves& leaves){Fixture f(leaves);k::Report r;const auto normal=f.normal;const auto mouse=f.mouse;const auto raw=f.raw;
    for(auto mask:{0u,1u,0x33u,0x100u,0xffffffffu}){Check(f.invoke(k::Query::ModifierMasked,mask,0,r)==0&&r.status==k::Status::InvalidQuery,"unknown mask refused");}
    for(auto key:{0u,0x100u,0x105u,0xffffffffu}){Check(f.invoke(k::Query::Press,key,0,r)==0&&r.status==k::Status::InvalidQuery,"unknown key refused");}
    Check(f.invoke(k::Query::Repeat,0x1c,2,r)==0&&r.status==k::Status::InvalidQuery,"unknown repeat flag");
    Check(f.invoke(k::Query::ModifierMasked,0x22,2,r)==0&&r.status==k::Status::InvalidQuery,"unknown all flag");
    Check(f.invoke(k::Query::Count,0,0,r)==0&&r.status==k::Status::InvalidQuery,"unknown query");
    Check(f.normal==normal&&f.mouse==mouse&&f.raw==raw&&f.own.calls==0,"reject before all writes and original");}
void BindingGuards(Leaves& leaves){Fixture f(leaves);k::Report r;auto req=f.request();req.binding.owner_generation++;
    Check(f.bridge.Invoke(req,k::Query::Modifier22,f.normal.data(),0,0,r)==0&&r.status==k::Status::StaleBinding,"stale binding");
    req=f.request();Check(f.bridge.Invoke(req,k::Query::Modifier22,f.mouse.data(),0,0,r)==0&&r.status==k::Status::UnexpectedCache,"wrong cache");
    std::thread t([&]{Check(f.bridge.Invoke(req,k::Query::Modifier22,f.normal.data(),0,0,r)==0&&r.status==k::Status::WrongThread,"wrong owner thread");});t.join();
    Check(f.own.calls==0,"no calls on rejected binding");}
void LayoutGuards(Leaves& leaves){Fixture f(leaves);k::Report r;
    Put<std::uint32_t>(f.normal.data(),8,2);Check(f.invoke(k::Query::Press,0x1c,0,r)==0&&r.status==k::Status::InvalidLayout,"invalid bank index");
    Put<std::uint32_t>(f.normal.data(),8,0);Put<std::uintptr_t>(f.normal.data(),0,reinterpret_cast<std::uintptr_t>(f.mouse.data()));
    Check(f.invoke(k::Query::Modifier22,0,0,r,k::Mode::ForwardUntouched)==0&&r.status==k::Status::InvalidLayout,"changed raw pointer");
    Check(f.own.calls==0,"invalid layout no call");}
void RepeatCycle(Leaves& leaves){Fixture f(leaves);k::Report r;f.own.query=k::Query::Modifier22;auto req=f.request();
    f.bridge.Invoke(req,k::Query::Modifier22,f.normal.data(),0,0,r);Check(r.status==k::Status::Ok,"first cycle");
    const auto raw=f.raw;f.bridge.Invoke(req,k::Query::Modifier22,f.normal.data(),0,0,r);
    Check(r.status==k::Status::PublicationRejected&&r.core_status==c::Status::InvalidCycle&&f.own.calls==1&&f.raw==raw,"duplicate cycle no original");}
void PhysicalAndCanaries(Leaves& leaves){Fixture f(leaves);k::Report r;const auto raw=f.raw;
    f.invoke(k::Query::Modifier22,0,0,r);
    Check(f.raw==raw&&Get<std::uintptr_t>(f.normal.data(),0)==reinterpret_cast<std::uintptr_t>(f.raw.data()),"physical events keys policy and pointer retained");
    for(std::size_t i=c::kNormalSize;i<f.normal.size();++i)Check(f.normal[i]==0xa5,"normal canary");
    for(std::size_t i=c::kMouseSize;i<f.mouse.size();++i)Check(f.mouse[i]==0xb6,"mouse canary");
    Put<std::uint32_t>(f.raw.data(),0x50,0);f.invoke(k::Query::Modifier22,0,0,r);Check((r.original_rax&0xff)==0,"subsequent owned source release observed normally");
    Put<std::uint32_t>(f.raw.data(),0x50,0x22);f.invoke(k::Query::Modifier22,0,0,r);Check((r.original_rax&0xff)==1,"subsequent held state not destroyed");}
void ExactReturn(Leaves& leaves){Fixture f(leaves);k::Report r;f.own.constant=true;
    auto value=f.invoke(k::Query::Modifier22,0,0,r,k::Mode::ForwardUntouched);Check(value==f.own.value&&r.original_rax==value,"forward all original RAX bits");
    value=f.invoke(k::Query::Modifier22,0,0,r);Check(value==(f.own.value&~0xffull)&&r.original_rax==f.own.value,"neutral only AL");
    f.invoke(k::Query::Press,0x1c,0,r);Check(r.status==k::Status::UnexpectedOriginalResult,"wrong key leaf does not fake success");}
void Exceptions(Leaves& leaves){Fixture f(leaves);f.own.query=k::Query::Modifier22;f.own.throws=true;bool caught=false;
    {k::ScopedRoute route(f.bridge,f.request());try{k::Modifier22(f.normal.data());}catch(const Failure& failure){caught=true;Check(&failure==f.own.exception_address&&failure.identity==&f.own,"same exception object");}
        Check(route.report().status==k::Status::OriginalException&&route.report().exception_rethrown&&!route.report().original_completed,"exception report");}
    Check(caught,"exception escaped original");const auto count=k::UnroutedCallCountForThisThread();Check(k::Modifier22(f.normal.data())==0&&k::UnroutedCallCountForThisThread()==count+1,"route lifetime ended");
    f.own.throws=false;k::Report r;f.invoke(k::Query::Modifier22,0,0,r);Check(r.status==k::Status::Ok,"exception restored reentry flag");}
void Reentrant(Leaves& leaves){Fixture f(leaves);k::Report r;f.own.reenter=true;f.invoke(k::Query::Modifier22,0,0,r);
    Check(r.status==k::Status::Ok&&f.own.calls==1&&f.own.nested==k::Status::ReentrantCall,"nested target rejected before write");
    f.invoke(k::Query::Modifier22,0,0,r);Check(r.status==k::Status::Ok&&f.own.calls==2,"outer flag cleaned");}
void RouteAndPump(Leaves& leaves){Fixture f(leaves);f.own.query=k::Query::Modifier22;std::atomic<unsigned> updates{0},worker{0};
    std::thread task([&]{for(unsigned i=0;i<200;++i)++worker;});
    {k::ScopedRoute outer(f.bridge,f.request(k::Mode::ForwardUntouched));Check((k::Modifier22(f.normal.data())&0xff)==1,"outer forward");
        {k::ScopedRoute inner(f.bridge,f.request());Check((k::Modifier22(f.normal.data())&0xff)==0,"inner neutral");}
        Check((k::Modifier22(f.normal.data())&0xff)==1,"restored outer route");++updates;}
    task.join();Check(worker==200&&updates==1,"owned engine/worker work proceeds; no native proof");}
void Disabled(Leaves& leaves){Fixture f(leaves);k::Report r;auto req=f.request();req.mode=static_cast<k::Mode>(9);
    Check(f.bridge.Invoke(req,k::Query::Modifier22,f.normal.data(),0,0,r)==0&&r.status==k::Status::InvalidMode,"invalid mode");
    k::QueryBridge empty;k::Targets t{};Check(empty.Bind(f.binding,{},t)==k::Status::InvalidTarget,"no implicit target discovery");
    t[0]=reinterpret_cast<k::OriginalQuery>(&k::Release);Check(empty.Bind(f.binding,{},t)==k::Status::InvalidTarget,"direct self target rejected");
    Check(f.own.calls==0,"no original on disabled route");}
}
int main(int argc,char** argv){
    if(argc!=2)return 2;
    struct Case {const char* name;void(*run)(Leaves&);};
    const Case cases[]={{"fixed_modifiers",Modifiers},{"masked_any_all",AnyAll},{"native_key_leaves",KeyLeaves},
        {"known_special_keys",SpecialKeys},{"unknown_query_rejection",InvalidQueries},{"binding_thread_cache",BindingGuards},
        {"layout_drift",LayoutGuards},{"duplicate_cycle",RepeatCycle},{"physical_source_and_canaries",PhysicalAndCanaries},
        {"original_rax_and_uncertainty",ExactReturn},{"exception_identity_cleanup",Exceptions},{"reentrant_original",Reentrant},
        {"explicit_route_and_owned_pump",RouteAndPump},{"disabled_and_self_targets",Disabled}};
    std::vector<std::string> passed;std::string failed;
    try{Leaves leaves;for(const auto& item:cases){try{item.run(leaves);passed.emplace_back(item.name);}catch(const std::exception& e){failed=std::string(item.name)+": "+e.what();break;}}}
    catch(const std::exception& e){failed=e.what();}
    std::ofstream file(argv[1]);file<<"{\"schema\":\"san14.native-input-keyboard-fixture.v1\",\"result\":\""<<(failed.empty()?"PASS":"FAIL")<<"\",\"cases\":"<<passed.size()<<",\"passed\":[";
    for(std::size_t i=0;i<passed.size();++i){if(i)file<<',';file<<'"'<<passed[i]<<'"';}
    file<<"],\"failure\":\""<<failed<<"\",\"game_accessed\":false,\"steam_accessed\":false,\"physical_input_accessed\":false,\"native_installation_proven\":false,\"full_input_hold_proven\":false}";
    std::cout<<(failed.empty()?"PASS":"FAIL")<<" "<<passed.size()<<" cases "<<failed<<'\n';return failed.empty()?0:1;
}
