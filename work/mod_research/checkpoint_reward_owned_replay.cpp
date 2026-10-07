#define CHECKPOINT_REWARD_OWNED_EXPORTS
#include "checkpoint_reward_owned_replay.h"
#include <bcrypt.h>
#include <cstring>
#include <new>
#include <vector>
#include <stdexcept>
#pragma comment(lib,"bcrypt.lib")
#include "reward_probe_fingerprints.h"
#include "reward_eligibility_fingerprints.h"
#include "reward_execution_fingerprints.h"
namespace checkpoint_reward_owned_replay {
namespace {
thread_local std::uintptr_t gameBase=0;
constexpr std::uintptr_t NODE_POOL_RVA=0x19E1BF0,HANDLE_POOL_RVA=0x19E1C38;
constexpr unsigned ELIGIBILITY_LIMIT=1024;
template<class T>T at(std::uintptr_t p){return *reinterpret_cast<const T*>(p);}
static bool reject(LONG){return false;}
#include "reward_eligibility_guard.inc"
struct ProfileScope {std::uintptr_t old;explicit ProfileScope(std::uintptr_t base):old(gameBase){gameBase=base;}~ProfileScope(){gameBase=old;}};
struct Failure {Error error;};
void need(bool b,Error error){if(!b)throw Failure{error};}
bool nonzero(const std::array<unsigned char,32>&bytes){for(auto c:bytes)if(c)return true;return false;}
using Bytes=std::vector<unsigned char>;
template<class T>void put(Bytes&b,const T&v){const auto*p=reinterpret_cast<const unsigned char*>(&v);b.insert(b.end(),p,p+sizeof v);}
void mem(Bytes&b,std::uintptr_t p,size_t n){const auto*s=reinterpret_cast<const unsigned char*>(p);b.insert(b.end(),s,s+n);}
std::array<unsigned char,32> hash(const Bytes&b){
    BCRYPT_ALG_HANDLE algorithm=nullptr;need(BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0,Error::SnapshotChanged);
    std::array<unsigned char,32>digest{};const auto status=BCryptHash(algorithm,nullptr,0,const_cast<PUCHAR>(b.data()),ULONG(b.size()),digest.data(),ULONG(digest.size()));BCryptCloseAlgorithmProvider(algorithm,0);need(status>=0,Error::SnapshotChanged);return digest;
}
bool profile(const Config&c){
#ifdef CHECKPOINT_REWARD_OWNED_FIXTURE
    return c.ctor&&c.append&&c.dtor&&c.predicate;
#else
    if(std::uintptr_t(c.ctor)!=c.base+0x22600||std::uintptr_t(c.append)!=c.base+0x171B0||std::uintptr_t(c.dtor)!=c.base+0x83E0||std::uintptr_t(c.predicate)!=c.base+0x1D4270)return false;
    for(const auto&f:REWARD_FINGERPRINTS)if(std::memcmp(reinterpret_cast<void*>(c.base+f.rva),f.bytes,sizeof f.bytes))return false;
    for(const auto&f:ELIGIBILITY_FINGERPRINTS)if(std::memcmp(reinterpret_cast<void*>(c.base+f.rva),f.bytes,f.size))return false;
    for(const auto&f:EXECUTION_FINGERPRINTS)if(std::memcmp(reinterpret_cast<void*>(c.base+f.rva),f.bytes,f.size))return false;
    return true;
#endif
}
}
struct Owner::Impl {
    Config config{};Command command{};Report report{};ph::RewardArgs args{};DWORD thread=0;bool initialized=false,constructed=false,executing=false;
    volatile LONG revoked=0;std::array<unsigned char,32> baseline{};std::uintptr_t nodes[MaxOfficers]{};std::uintptr_t ownedHandle=0,ownedHeads=0,ownedTails=0,ownedCounts=0;unsigned allocated=0;
    bool active()const noexcept{return InterlockedCompareExchange(const_cast<volatile LONG*>(&revoked),0,0)==0;}
    void valid(){
        need(initialized&&GetCurrentThreadId()==thread,Error::WrongThread);need(active(),Error::Cancelled);need(profile(config),Error::Profile);
        need(GetTickCount64()<command.expires_at_tick,Error::Expired);
        need(config.validate_attachment&&config.validate_attachment(config.context,config.binding),Error::Binding);
        need(at<std::uintptr_t>(config.base+0x1FCA1E0)==config.root&&at<std::uintptr_t>(config.root+0x85130)==config.world,Error::Binding);
        const auto manager=config.base+0x19E7310,stack=at<std::uintptr_t>(manager+0x20);
        need(at<std::uint64_t>(manager+0x10)==5&&stack&&at<std::uintptr_t>(stack+32)==config.user&&!at<std::uint64_t>(manager+0x30)&&at<std::uintptr_t>(config.user)==config.base+0x12CC4A8&&at<std::uint32_t>(config.user+0x470)==2,Error::Binding);
        need(at<std::uint16_t>(config.world+0x34)==command.year&&at<std::uint8_t>(config.world+0x36)==command.month&&at<std::uint8_t>(config.world+0x37)==command.day&&at<std::uint8_t>(config.world+0x3A)==command.viewer_force,Error::Binding);
    }
    void pool(){const auto p=config.base+NODE_POOL_RVA,h=config.base+HANDLE_POOL_RVA;
        need(at<std::uintptr_t>(p+8)&&at<std::uintptr_t>(p+0x10)&&at<std::uintptr_t>(p+0x18)&&at<std::uintptr_t>(p+0x28)&&at<unsigned>(p+0x40)==1024&&at<std::uint64_t>(h+0x38)==1024&&at<std::uint64_t>(p+0x30)<=at<std::uint64_t>(p+0x38)&&at<std::uint64_t>(h+0x30)<1024,Error::Pool);
    }
    Bytes semantic(bool list){
        valid();pool();ProfileScope scope(config.base);Bytes bytes;put(bytes,report.command_sha256);
        need(eligibilityObjectGuard(config.root),Error::Eligibility);
        const auto force=at<std::uintptr_t>(config.root+0xDCA0+command.command_force*8),district=at<std::uintptr_t>(config.root+0xDE40+command.charged_district*8);
        const auto ruler=at<std::uintptr_t>(config.root+0x148+command.ruler*8),city=at<std::uintptr_t>(config.root+0xDAA8+command.funding_city*8);
        need(at<std::uintptr_t>(force)==config.base+0x129FE58&&at<std::uint16_t>(force+0x10)==command.ruler&&at<std::uintptr_t>(ruler)==config.base+0x12A00D0&&at<std::uint16_t>(ruler+0x10)==command.ruler,Error::Permissions);
        need(at<std::uintptr_t>(city)==config.base+0x129FD10&&at<std::uint16_t>(city+0x10)==command.funding_city&&at<std::uint8_t>(city+0x30)==command.charged_district&&at<std::uintptr_t>(district)==config.base+0x129FEC8&&at<std::uint8_t>(district+0x10)==command.command_force&&at<std::uint16_t>(district+0x12)==command.ruler,Error::Permissions);
        need(at<std::uintptr_t>(config.base+0x129FD10+0x18)==config.base+0x211540&&at<std::uintptr_t>(config.base+0x129FD10+0x80)==config.base+0x209A00&&at<std::uintptr_t>(config.base+0x129FD10+0x90)==config.base+0x20C2E0,Error::Profile);
        std::uintptr_t entries[1024]{};unsigned count=0;std::uintptr_t main=0,funding=0;
        need(readList(config.root+0xC8,0x123F3F8,0x201D3A0,0x14000,entries,&count),Error::Permissions);
        for(unsigned i=0;i<count;++i){auto d=entries[i];need(at<std::uintptr_t>(d)==config.base+0x129FEC8,Error::Permissions);if(!main&&at<std::uint8_t>(d+0x10)==command.command_force&&(at<std::uint16_t>(d+0x12)==command.ruler||at<std::uint8_t>(d+0x11)==1))main=d;}
        need(main==district,Error::Permissions);
        need(readList(config.root+0x78,0x123F3B8,0x201D3A0,0x14000,entries,&count),Error::Permissions);
        for(unsigned i=0;i<count;++i){need(at<std::uintptr_t>(entries[i])==config.base+0x129FD10,Error::Permissions);if(!funding&&at<std::uint16_t>(entries[i]+0x4E)==at<std::uint16_t>(ruler+0x11A))funding=entries[i];}
        need(funding==city,Error::Permissions);
        const auto gold=at<unsigned>(city+0x34);const auto actionPoints=at<std::uint8_t>(district+0x14);
        need(gold>=command.count*100&&actionPoints>=at<unsigned>(config.base+0x18ECF30),Error::Permissions);
        put(bytes,at<unsigned>(config.base+0x18ECF30));put(bytes,at<unsigned>(config.base+0x18ECFE0));put(bytes,city);put(bytes,district);put(bytes,force);mem(bytes,city+0x10,0x50);mem(bytes,district+0x10,0x18);mem(bytes,ruler+0x10,0x190);
        for(unsigned i=0;i<command.count;++i){const auto person=at<std::uintptr_t>(config.root+0x148+command.officers[i]*8);need(at<std::uintptr_t>(person)==config.base+0x12A00D0&&at<std::uint16_t>(person+0x10)==command.officers[i],Error::Permissions);
            const auto did=at<std::uint8_t>(person+0x118);need(did&&did<=51,Error::Permissions);const auto owned=at<std::uintptr_t>(config.root+0xDE40+did*8);
            need(at<std::uintptr_t>(owned)==config.base+0x129FEC8&&at<std::uint8_t>(owned+0x10)==command.command_force,Error::Permissions);
            need(config.predicate(person)==1,Error::Eligibility);put(bytes,person);put(bytes,owned);mem(bytes,person+0x10,0x190);
        }
        if(list){need(args.vtable==config.base+0x123E210&&args.funding==city&&args.handle&&at<unsigned>(args.handle)==report.slot,Error::SnapshotChanged);
            const auto p=config.base+NODE_POOL_RVA;const auto heads=at<std::uintptr_t>(p+0x10),tails=at<std::uintptr_t>(p+0x18),counts=at<std::uintptr_t>(p+0x28);
            need(at<std::uint64_t>(counts+report.slot*8)==command.count,Error::SnapshotChanged);auto node=at<std::uintptr_t>(heads+report.slot*8);std::uintptr_t previous=0;
            put(bytes,args);put(bytes,report.slot);
            for(unsigned i=0;i<command.count;++i){need(node&&node==nodes[i]&&at<unsigned>(node)==command.officers[i]&&at<std::uintptr_t>(node+0x10)==previous,Error::SnapshotChanged);put(bytes,node);mem(bytes,node,0x18);previous=node;node=at<std::uintptr_t>(node+8);}
            need(!node&&at<std::uintptr_t>(tails+report.slot*8)==previous,Error::SnapshotChanged);
        }
        return bytes;
    }
    bool cleanup()noexcept{
        if(!constructed){report.args_released=true;return true;}
        if(GetCurrentThreadId()!=thread||executing)return false;
        try{const auto p=config.base+NODE_POOL_RVA,h=config.base+HANDLE_POOL_RVA;
            // A changed pool or corrupted linkage must not make a destructor free
            // another generation's objects. Retain this owner on uncertainty.
            need(profile(config),Error::Cleanup);
            if(ownedHandle){need(args.handle==ownedHandle&&at<unsigned>(ownedHandle)==report.slot&&at<std::uintptr_t>(p+0x10)==ownedHeads&&at<std::uintptr_t>(p+0x18)==ownedTails&&at<std::uintptr_t>(p+0x28)==ownedCounts,Error::Cleanup);
                need(at<std::uint64_t>(ownedCounts+report.slot*8)==allocated,Error::Cleanup);
                auto node=at<std::uintptr_t>(ownedHeads+report.slot*8);std::uintptr_t previous=0;
                for(unsigned i=0;i<allocated;++i){need(node==nodes[i]&&node&&at<std::uintptr_t>(node+0x10)==previous,Error::Cleanup);previous=node;node=at<std::uintptr_t>(node+8);}
                need(!node&&at<std::uintptr_t>(ownedTails+report.slot*8)==previous,Error::Cleanup);
            }else need(!args.handle,Error::Cleanup);
            ++report.dtor_calls;config.dtor(&args);
            report.args_released=args.handle==0;report.owned_slot_cleared=!ownedHandle||(report.slot<1024&&!at<std::uintptr_t>(at<std::uintptr_t>(p+0x10)+report.slot*8)&&!at<std::uintptr_t>(at<std::uintptr_t>(p+0x18)+report.slot*8)&&!at<std::uint64_t>(at<std::uintptr_t>(p+0x28)+report.slot*8));
            report.after_nodes=at<std::uint64_t>(p+0x30);report.after_handles=at<std::uint64_t>(h+0x30);
            if(!report.args_released||!report.owned_slot_cleared){report.error=Error::Cleanup;report.state=State::Fault;return false;}constructed=false;return true;
        }catch(...){report.error=Error::Cleanup;report.state=State::Fault;return false;}
    }
};
Owner::Owner():p_(new(std::nothrow)Impl){}
Owner::~Owner(){delete p_;} // Exported Destroy enforces explicit successful Close.
bool Owner::Initialize(const Config&c)noexcept{
    if(!p_||p_->initialized||!c.base||!c.root||!c.world||!c.user||!c.validate_attachment||!c.binding.native.owner_generation||!c.authorized_force||c.authorized_force>51||!c.authorized_ruler||c.authorized_ruler>=6000)return false;
    try{if(!profile(c)){p_->report.error=Error::Profile;return false;}p_->config=c;p_->thread=GetCurrentThreadId();p_->initialized=true;return true;}catch(...){p_->report.error=Error::Profile;return false;}
}
bool Owner::Prepare(const Command&c)noexcept{
    if(!p_||!p_->initialized||p_->report.state!=State::New||GetCurrentThreadId()!=p_->thread)return false;auto&s=*p_;
    try{
        const auto now=GetTickCount64();
        need(c.command_force==s.config.authorized_force&&c.ruler==s.config.authorized_ruler,Error::Permissions);
        need(nonzero(c.nonce)&&c.count&&c.count<=MaxOfficers&&c.command_force&&c.command_force<=51&&c.charged_district&&c.charged_district<=51&&c.ruler&&c.ruler<6000&&c.funding_city&&c.funding_city<63&&c.month>=1&&c.month<=12&&(c.day==1||c.day==11||c.day==21)&&c.expires_at_tick>now&&c.expires_at_tick-now<=60000,Error::Command);
        for(unsigned i=0;i<c.count;++i){need(c.officers[i]&&c.officers[i]<6000,Error::Command);for(unsigned j=0;j<i;++j)need(c.officers[j]!=c.officers[i],Error::Command);}
        s.command=c;Bytes command;put(command,s.config.binding.native.attempt);put(command,s.config.binding.native.attachment);put(command,s.config.binding.native.owner_generation);put(command,s.config.binding.period);put(command,s.config.binding.epoch);put(command,s.config.binding.room_input_digest);put(command,c.nonce);put(command,c.expires_at_tick);put(command,c.year);put(command,c.month);put(command,c.day);put(command,c.viewer_force);put(command,c.command_force);put(command,c.ruler);put(command,c.funding_city);put(command,c.charged_district);put(command,c.count);for(unsigned i=0;i<c.count;++i)put(command,c.officers[i]);s.report.command_sha256=hash(command);
        s.semantic(false);const auto p=s.config.base+NODE_POOL_RVA,h=s.config.base+HANDLE_POOL_RVA;s.report.before_nodes=at<std::uint64_t>(p+0x30);s.report.before_handles=at<std::uint64_t>(h+0x30);
        s.constructed=true;++s.report.ctor_calls;need(s.config.ctor(&s.args)==&s.args&&s.args.vtable==s.config.base+0x123E210&&s.args.handle,Error::Pool);
        s.report.slot=at<unsigned>(s.args.handle);need(s.report.slot<1024,Error::Pool);s.ownedHandle=s.args.handle;s.ownedHeads=at<std::uintptr_t>(p+0x10);s.ownedTails=at<std::uintptr_t>(p+0x18);s.ownedCounts=at<std::uintptr_t>(p+0x28);
        need(!at<std::uintptr_t>(at<std::uintptr_t>(p+0x10)+s.report.slot*8)&&!at<std::uintptr_t>(at<std::uintptr_t>(p+0x18)+s.report.slot*8)&&!at<std::uint64_t>(at<std::uintptr_t>(p+0x28)+s.report.slot*8),Error::Pool);
        s.args.funding=at<std::uintptr_t>(s.config.root+0xDAA8+c.funding_city*8);
        for(unsigned i=0;i<c.count;++i){++s.report.append_calls;s.nodes[i]=s.config.append(p,s.report.slot,1);need(s.nodes[i]!=0,Error::Pool);*reinterpret_cast<unsigned*>(s.nodes[i])=c.officers[i];++s.allocated;}
        s.baseline=hash(s.semantic(true));s.report.semantic_sha256=s.baseline;s.report.state=State::Prepared;return true;
    }catch(const Failure&f){s.report.error=f.error;}catch(...){s.report.error=Error::NativeException;}
    s.report.state=State::Fault;s.cleanup();return false;
}
bool Owner::Capture(void*p,ph::Kind kind,const void*args,int flags,ph::SemanticReceipt&out){
    auto*owner=static_cast<Owner*>(p);if(!owner||!owner->p_)return false;auto&s=*owner->p_;++s.report.capture_calls;
    if(kind!=ph::Kind::Reward||flags||args!=&s.args||!s.executing||s.report.state!=State::Executing)return false;
    try{auto digest=hash(s.semantic(true));need(digest==s.baseline,Error::SnapshotChanged);out.digest=digest;out.ownership_token=reinterpret_cast<std::uintptr_t>(owner);out.payload_epoch=1;return true;}
    catch(const Failure&f){s.report.error=f.error;return false;}catch(...){s.report.error=Error::NativeException;return false;}
}
int Owner::Execute(ph::Context*hold,std::uint64_t sequence){
    if(!p_||!hold||!sequence||p_->report.state!=State::Prepared||GetCurrentThreadId()!=p_->thread)return 0;auto&s=*p_;s.executing=true;s.report.state=State::Executing;++s.report.execute_calls;
    try{ph::Report before{},after{};need(PlanningHoldSnapshot(hold,&before),Error::Replay);const auto*t=PlanningHoldAuthorizeReward(hold,&s.config.binding,sequence,&s.args);need(t!=nullptr,Error::Replay);s.report.native_result=PlanningHoldReplayReward(hold,t,&s.args);need(PlanningHoldSnapshot(hold,&after),Error::Replay);s.report.native_returned=after.native_returns==before.native_returns+1&&after.remote_entered==before.remote_entered+1;need(s.report.native_returned&&s.report.native_result==1,Error::Replay);s.report.state=State::Consumed;s.executing=false;return s.cleanup()?s.report.native_result:0;}
    catch(const Failure&f){if(s.report.error==Error::None)s.report.error=f.error;s.report.state=State::Fault;s.executing=false;s.cleanup();return 0;}
    catch(...){s.report.error=Error::NativeException;s.report.state=State::Fault;s.executing=false;s.cleanup();throw;}
}
void Owner::Cancel()noexcept{if(p_)InterlockedExchange(&p_->revoked,1);}
bool Owner::Close()noexcept{if(!p_)return true;if(GetCurrentThreadId()!=p_->thread||p_->executing)return false;if(!p_->active()&&p_->report.state==State::Prepared)p_->report.state=State::Cancelled;return p_->cleanup();}
Report Owner::Snapshot()const noexcept{if(!p_)return{};auto r=p_->report;r.cancel_requested=!p_->active();return r;}
ph::RewardArgs*Owner::ArgsForOwnedFixture()noexcept{
#ifdef CHECKPOINT_REWARD_OWNED_FIXTURE
    return p_?&p_->args:nullptr;
#else
    return nullptr;
#endif
}
}
using namespace checkpoint_reward_owned_replay;
Owner*RewardOwnedCreate(const Config*c)noexcept{if(!c)return nullptr;auto*p=new(std::nothrow)Owner;if(!p)return nullptr;if(!p->Initialize(*c)){delete p;return nullptr;}return p;}
bool RewardOwnedDestroy(Owner*p)noexcept{if(!p)return true;if(!p->Close())return false;delete p;return true;}
bool RewardOwnedPrepare(Owner*p,const Command*c)noexcept{return p&&c&&p->Prepare(*c);}
int RewardOwnedExecute(Owner*p,checkpoint_planning_hold::Context*c,std::uint64_t s){return p?p->Execute(c,s):0;}
void RewardOwnedCancel(Owner*p)noexcept{if(p)p->Cancel();}
bool RewardOwnedSnapshot(Owner*p,Report*r)noexcept{if(!p||!r)return false;*r=p->Snapshot();return true;}
bool RewardOwnedCapture(void*p,checkpoint_planning_hold::Kind k,const void*a,int f,checkpoint_planning_hold::SemanticReceipt&r){return Owner::Capture(p,k,a,f,r);}
checkpoint_planning_hold::RewardArgs*RewardOwnedFixtureArgs(Owner*p)noexcept{return p?p->ArgsForOwnedFixture():nullptr;}
