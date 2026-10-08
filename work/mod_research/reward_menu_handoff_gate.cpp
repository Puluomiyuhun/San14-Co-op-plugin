// Successor at the UI's call to 626050, not at the already-executing 1D6DA0.
// This file deliberately has no source-writing/remote-install function.
#include "reward_menu_handoff_gate.h"
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <array>
#include <cstring>
#include <mutex>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
static uint64_t selectedUser=0;
static void readExact(HANDLE p,uint64_t a,void* out,size_t n){SIZE_T got=0;
    if(!ReadProcessMemory(p,reinterpret_cast<const void*>(a),out,n,&got)||got!=n)throw std::runtime_error("read failed");}
template<class T>static T rd(HANDLE p,uint64_t a){T value{};readExact(p,a,&value,sizeof value);return value;}
#include "reward_menu_observation_decode.inc"
namespace {
using namespace reward_menu_handoff;
std::mutex lock;
Binding binding;
Report report;
Proposal frozen;
bool everBound=false;
bool token(const char* v){if(!v)return false;for(size_t i=0;i<32;++i)
    if(!((v[i]>='0'&&v[i]<='9')||(v[i]>='a'&&v[i]<='f')))return false;return v[32]==0;}
void fail(Error e){report.phase=Phase::fault;report.error=e;}
void reject(Error e){report.last_rejection=e;++report.rejections;}
bool same(const MenuDraft& d,const Proposal& p){if(d.force!=p.force||d.district!=p.district||d.city!=p.funding_city||d.officers.size()!=p.count)return false;
    for(size_t i=0;i<d.officers.size();++i)if(d.officers[i]!=p.officers[i])return false;return true;}
bool identities(const MenuDraft& d){return d.root==binding.root&&d.world==binding.world&&d.state==binding.state
    &&d.force==binding.force&&d.district==binding.district&&d.viewer==binding.force&&d.year==binding.year
    &&d.month==binding.month&&d.day==binding.day
    &&rd<uint64_t>(GetCurrentProcess(),binding.state+0x478)==binding.layout;}
bool source(){
    // Verify the exact local 5-byte call AND the 12-byte relay to this entry.
    std::array<unsigned char,5> call{};std::array<unsigned char,12> relay{};
    readExact(GetCurrentProcess(),binding.base+0x67A993,call.data(),call.size());
    readExact(GetCurrentProcess(),binding.base+binding.relay_rva,relay.data(),relay.size());
    int32_t displacement=0;memcpy(&displacement,call.data()+1,4);
    uint64_t target=0;memcpy(&target,relay.data()+2,8);
    return call[0]==0xE8&&int64_t(0x67A998)+displacement==binding.relay_rva
        &&relay[0]==0x48&&relay[1]==0xB8&&relay[10]==0xFF&&relay[11]==0xE0
        &&target==reinterpret_cast<uint64_t>(&RewardMenuHandoffGate_Entry);
}
MenuDraft fresh(){auto d=decodeMenu(GetCurrentProcess(),binding.base,binding.state);
    if(!identities(d)){fail(Error::identity);throw std::runtime_error("identity changed");}
    if(d.event!=2||d.officers.empty()||d.officers.size()>16){fail(Error::draft);throw std::runtime_error("draft changed");}
    return d;
}
}
namespace reward_menu_handoff {
bool Bind(const Binding& b) noexcept {std::lock_guard<std::mutex> guard(lock);
    if(everBound){reject(Error::already_bound);return false;}
    // A failed first bind is terminal: no hidden reset/reuse of an old source.
    everBound=true;
    try {
        if(!b.base||!b.root||!b.world||!b.user||!b.state||!b.layout||!b.generation||!token(b.menu_id)
            ||b.thread!=GetCurrentThreadId()||b.relay_rva<0x1000||b.relay_rva>=0x2400000-12
            ||(b.relay_rva>=0x67A930&&b.relay_rva<0x67A9C1)) {fail(Error::bad_config);return false;}
        constexpr unsigned char original[]={0xE8,0xB8,0xB6,0xFA,0xFF};unsigned char got[5];
        readExact(GetCurrentProcess(),b.base+0x67A993,got,sizeof got);
        if(memcmp(original,got,sizeof got)){fail(Error::source);return false;}
        binding=b;selectedUser=b.user;
        const auto d=decodeMenu(GetCurrentProcess(),b.base,b.state);
        if(!identities(d)){fail(Error::identity);return false;}
        report.phase=Phase::bound;return true;
    }catch(...){if(report.phase!=Phase::fault)fail(Error::decode);return false;}
}
bool TakeProposal(const char* menu_id,uint64_t generation,Proposal& out) noexcept {
    std::lock_guard<std::mutex> guard(lock);out=Proposal{};
    if(!token(menu_id)||generation!=binding.generation||memcmp(menu_id,binding.menu_id,33)){
        reject(Error::wrong_claim);return false;}
    if(report.phase!=Phase::pending){reject(report.phase==Phase::retired?Error::retired:Error::consumed);return false;}
    try{
        if(GetCurrentThreadId()!=binding.thread){fail(Error::thread);return false;}
        if(!source()){fail(Error::source);return false;}
        const auto d=fresh();if(!same(d,frozen)){fail(Error::draft);return false;}
        out=frozen;report.phase=Phase::taken;report.proposal_was_taken=true;++report.takes;return true;
    }catch(...){if(report.phase!=Phase::fault)fail(Error::decode);return false;}
}
void Retire() noexcept {std::lock_guard<std::mutex> guard(lock);report.phase=Phase::retired;report.error=Error::retired;}
Report Inspect() noexcept {std::lock_guard<std::mutex> guard(lock);return report;}
}
extern "C" __declspec(noinline) int RewardMenuHandoffGate_Entry(uint64_t state) noexcept {
    const auto caller=reinterpret_cast<uint64_t>(_ReturnAddress());
    std::lock_guard<std::mutex> guard(lock);++report.calls;
    // All paths return wrapper-false. Never execute the original wrapper or common handler.
    if(report.phase==Phase::fault||report.phase==Phase::retired)return 0;
    try{
        if(report.phase==Phase::unbound||caller!=binding.base+0x67A998||!source()){fail(Error::source);return 0;}
        if(GetCurrentThreadId()!=binding.thread){fail(Error::thread);return 0;}
        if(state!=binding.state){fail(Error::identity);return 0;}
        const auto d=fresh();
        if(report.phase==Phase::bound){
            frozen.force=d.force;frozen.district=d.district;frozen.funding_city=d.city;frozen.count=static_cast<uint32_t>(d.officers.size());
            for(size_t i=0;i<d.officers.size();++i)frozen.officers[i]=d.officers[i];
            frozen.generation=binding.generation;memcpy(frozen.menu_id,binding.menu_id,33);
            ++report.captures;report.phase=Phase::pending;
        }else if(!same(d,frozen))fail(Error::draft);
    }catch(...){if(report.phase!=Phase::fault)fail(Error::decode);}
    return 0;
}
