// Include the frozen owned-process fixture, not its main entry. It provides
// real pending-core/neutral-core ABI boundary and archived menu-fetch bytes.
#define main frozen_planning_fixture_main
#include "checkpoint_planning_hold_fixture.cpp"
#undef main
#include "checkpoint_reward_owned_replay.h"
#include <vector>
namespace rw=checkpoint_reward_owned_replay;
struct RewardWorld;
static RewardWorld* worldFixture=nullptr;
struct RewardWorld {
    std::vector<unsigned char> image=std::vector<unsigned char>(0x2040000),root=std::vector<unsigned char>(0x85300);
    std::array<unsigned char,0x100>world{},tasks{},unit{},force{},district{},city{},otherDistrict{},otherForce{};
    std::array<unsigned char,0x1a0>ruler{},p1{},p2{};
    std::vector<std::uintptr_t> heads=std::vector<std::uintptr_t>(1024),tails=heads,counts=heads;
    std::vector<std::uintptr_t> pheads=std::vector<std::uintptr_t>(0x14000),ptails=pheads,pcounts=pheads;
    std::array<std::uintptr_t,3>districtNode{},cityNode{};
    unsigned districtSlot=1,citySlot=2,handle=20;
    std::vector<std::array<std::uintptr_t,3>*> nodes;
    Fixture planning;rw::Owner* owner=nullptr;rw::Config config{};rw::Command command{};
    unsigned ctors=0,dtors=0,bodies=0,appends=0,captures=0;bool attachment=true,inside=false;int failAppend=-1;
    std::uintptr_t base()const{return reinterpret_cast<std::uintptr_t>(image.data());}
    std::uintptr_t addr(const void*p){return reinterpret_cast<std::uintptr_t>(p);}
    template<class T>void imagePut(size_t off,T v){put(image.data(),off,v);}
    static ph::RewardArgs* ctor(ph::RewardArgs*a){auto&f=*worldFixture;++f.ctors;a->vtable=f.base()+0x123e210;a->handle=f.addr(&f.handle);f.imagePut<std::uint64_t>(0x19e1c38+0x30,1);return a;}
    static std::uintptr_t append(std::uintptr_t pool,std::uint32_t slot,std::uint8_t flag){auto&f=*worldFixture;check(pool==f.base()+0x19e1bf0&&slot==f.handle&&flag==1,"native append ABI");if(int(f.appends++)==f.failAppend)return 0;
        auto*n=new std::array<std::uintptr_t,3>{};(*n)[2]=f.tails[slot];if(f.tails[slot])put(reinterpret_cast<void*>(f.tails[slot]),8,f.addr(n));else f.heads[slot]=f.addr(n);f.tails[slot]=f.addr(n);++f.counts[slot];f.nodes.push_back(n);f.imagePut<std::uint64_t>(0x19e1bf0+0x30,f.nodes.size());return f.addr(n);}
    static void dtor(ph::RewardArgs*a){auto&f=*worldFixture;check(!f.inside,"not destroyed before original returns");++f.dtors;for(auto*p:f.nodes)delete p;f.nodes.clear();f.heads[f.handle]=f.tails[f.handle]=f.counts[f.handle]=0;a->handle=0;f.imagePut<std::uint64_t>(0x19e1c38+0x30,0);f.imagePut<std::uint64_t>(0x19e1bf0+0x30,0);}
    static int predicate(std::uintptr_t person){return get<unsigned char>(reinterpret_cast<void*>(person),0x120)<100?1:0;}
    static bool validate(void*p,const ph::Binding&b){auto&f=*static_cast<RewardWorld*>(p);return f.attachment&&b.native.attempt==f.config.binding.native.attempt&&b.native.attachment==f.config.binding.native.attachment&&b.native.owner_generation==f.config.binding.native.owner_generation&&b.period==f.config.binding.period&&b.epoch==f.config.binding.epoch&&b.room_input_digest==f.config.binding.room_input_digest;}
    static bool capture(void*p,ph::Kind k,const void*a,int flags,ph::SemanticReceipt&out){auto&f=*worldFixture;bool ok=RewardOwnedCapture(p,k,a,flags,out);if(++f.captures==1&&ok){if(mode=="consume-change")put<unsigned>(reinterpret_cast<void*>(f.heads[f.handle]),0,904);if(mode=="consume-cancel")RewardOwnedCancel(f.owner);}return ok;}
    static int original(ph::RewardArgs*a){auto&f=*worldFixture;++f.bodies;f.inside=true;check(a->handle==f.addr(&f.handle)&&a->funding==f.addr(f.city.data())&&f.counts[f.handle]==2&&!f.dtors,"deep list lives in original");
        check(get<unsigned>(reinterpret_cast<void*>(f.heads[f.handle]),0)==97&&get<unsigned>(reinterpret_cast<void*>(f.tails[f.handle]),0)==759,"exact native list ids");
        if(mode=="cancel-during"){std::thread t([&]{RewardOwnedCancel(f.owner);check(!RewardOwnedDestroy(f.owner),"cross thread destroy denied");});t.join();check(!f.dtors&&a->handle,"cancel never destroys executing list");}
        if(mode=="exception"){f.inside=false;throw std::runtime_error("reward-original-exception");}
        if(mode=="seh-exception"){f.inside=false;RaiseException(0xE0421377,0,0,nullptr);}
        if(mode=="zero-result"){f.inside=false;return 0;}
        put<unsigned>(f.city.data(),0x34,get<unsigned>(f.city.data(),0x34)-200);put<unsigned char>(f.district.data(),0x14,17);put<unsigned char>(f.p1.data(),0x120,100);put<unsigned char>(f.p2.data(),0x120,100);f.inside=false;return 1;
    }
    RewardWorld(){worldFixture=this;const auto b=base();
        imagePut(0x1fca1e0,addr(root.data()));put(root.data(),0x85130,addr(world.data()));put(root.data(),0x85128,addr(tasks.data()));put(tasks.data(),0x10,b+0x129bb28);
        put<std::uint16_t>(world.data(),0x34,203);put<unsigned char>(world.data(),0x36,8);put<unsigned char>(world.data(),0x37,11);put<unsigned char>(world.data(),0x3a,12);
        put(unit.data(),0,b+0x123e288);put(otherDistrict.data(),0,b+0x129fec8);put(otherForce.data(),0,b+0x129fe58);
        for(unsigned i=0;i<=500;++i)put(root.data(),0x7df60+i*8,addr(unit.data()));for(unsigned i=0;i<=51;++i){put(root.data(),0xde40+i*8,addr(otherDistrict.data()));put(root.data(),0xdca0+i*8,addr(otherForce.data()));}
        put(force.data(),0,b+0x129fe58);put<std::uint16_t>(force.data(),0x10,666);put(root.data(),0xdca0+12*8,addr(force.data()));
        put(district.data(),0,b+0x129fec8);put<unsigned char>(district.data(),0x10,12);put<unsigned char>(district.data(),0x11,1);put<std::uint16_t>(district.data(),0x12,666);put<unsigned char>(district.data(),0x14,18);put(root.data(),0xde40+11*8,addr(district.data()));
        put(city.data(),0,b+0x129fd10);put<std::uint16_t>(city.data(),0x10,19);put<unsigned char>(city.data(),0x30,11);put<unsigned>(city.data(),0x34,83308);put<std::uint16_t>(city.data(),0x4e,19);put(root.data(),0xdaa8+19*8,addr(city.data()));
        for(auto pair:{std::make_pair(&ruler,666u),std::make_pair(&p1,97u),std::make_pair(&p2,759u)}){auto&p=*pair.first;put(p.data(),0,b+0x12a00d0);put<std::uint16_t>(p.data(),0x10,std::uint16_t(pair.second));put<unsigned char>(p.data(),0x118,11);put<std::uint16_t>(p.data(),0x11a,19);put<unsigned char>(p.data(),0x120,90);put(root.data(),0x148+pair.second*8,addr(p.data()));}
        for(auto pair:{std::make_pair(0x123e288+0x18,0x211420),std::make_pair(0x12a00d0+0x18,0x2119f0),std::make_pair(0x129fec8+0x18,0x211610),std::make_pair(0x129fe58+0x60,0x20b610),std::make_pair(0x129fd10+0x18,0x211540),std::make_pair(0x129fd10+0x80,0x209a00),std::make_pair(0x129fd10+0x90,0x20c2e0)})imagePut(pair.first,b+pair.second);
        imagePut<unsigned>(0x18ecf30,1);
        for(auto pair:{std::make_pair(0x19e1bf0,1024u),std::make_pair(0x201d3a0,0x14000u)}){const bool integer=pair.second==1024;imagePut(pair.first+8,addr(integer?heads.data():pheads.data()));imagePut(pair.first+0x10,addr(integer?heads.data():pheads.data()));imagePut(pair.first+0x18,addr(integer?tails.data():ptails.data()));imagePut(pair.first+0x28,addr(integer?counts.data():pcounts.data()));imagePut<unsigned>(pair.first+0x40,pair.second);imagePut<std::uint64_t>(pair.first+0x38,10000);}
        imagePut<std::uint64_t>(0x19e1c38+0x38,1024);
        districtNode[0]=addr(district.data());cityNode[0]=addr(city.data());pheads[1]=ptails[1]=addr(districtNode.data());pheads[2]=ptails[2]=addr(cityNode.data());pcounts[1]=pcounts[2]=1;
        put(root.data(),0xc8,b+0x123f3f8);put(root.data(),0xd0,addr(&districtSlot));put(root.data(),0x78,b+0x123f3b8);put(root.data(),0x80,addr(&citySlot));
        auto&f=planning;PlanningHoldDestroy(f.context);f.context=nullptr;f.config.pending.profile_base=b;put(f.user.data(),0,b+0x12cc4a8);put(f.game.data(),0,b+0x12cc9b8);
        std::memcpy(image.data()+0x19e7310,f.manager.data(),f.manager.size());
        config.binding=f.config.binding;config.base=b;config.root=addr(root.data());config.world=addr(world.data());config.user=addr(f.user.data());config.authorized_force=12;config.authorized_ruler=666;config.ctor=&ctor;config.append=&append;config.dtor=&dtor;config.predicate=&predicate;config.validate_attachment=&validate;config.context=this;
        if(mode=="remote-force-while-local-held"){config.authorized_force=2;put<unsigned char>(district.data(),0x10,2);put(root.data(),0xdca0+2*8,addr(force.data()));}
        owner=RewardOwnedCreate(&config);check(owner!=nullptr,"concrete DLL provider create");f.config.reward=&original;f.config.capture_owned_command=&capture;f.config.replay_source_context=owner;f.context=PlanningHoldCreate(&f.config);check(f.context!=nullptr,"frozen adapter actual callback integration");f.hold();
        command.nonce[0]=37;command.year=203;command.month=8;command.day=11;command.viewer_force=12;command.command_force=config.authorized_force;command.charged_district=11;command.ruler=666;command.funding_city=19;command.count=2;command.officers[0]=97;command.officers[1]=759;command.expires_at_tick=GetTickCount64()+30000;
    }
    ~RewardWorld(){if(owner)check(RewardOwnedDestroy(owner),"destroy only after released");worldFixture=nullptr;}
};
static bool invokeSEH(RewardWorld&f){bool caught=false;__try{RewardOwnedExecute(f.owner,f.planning.context,1);}__except(GetExceptionCode()==0xE0421377?EXCEPTION_EXECUTE_HANDLER:EXCEPTION_CONTINUE_SEARCH){caught=true;}return caught;}
int main(int argc,char**argv){if(argc!=2)return 2;mode=argv[1];try{RewardWorld f;
    if(mode=="production-refuses-fixture"){auto dll=LoadLibraryW(L"checkpoint_reward_owned_replay.dll");check(dll!=nullptr,"production DLL normally loaded");auto create=reinterpret_cast<rw::Owner*(*)(const rw::Config*)noexcept>(GetProcAddress(dll,"RewardOwnedCreate"));check(create&&create(&f.config)==nullptr,"production rejects test helper targets");FreeLibrary(dll);std::puts("{\"result\":\"PASS\",\"case\":\"production-refuses-fixture\",\"game_access\":false}");return 0;}
    if(mode=="cross-force-command")f.command.command_force=2;
    if(mode=="append-failure")f.failAppend=1;
    if(mode=="expired")f.command.expires_at_tick=GetTickCount64()-1;
    if(mode=="expires-after-prepare")f.command.expires_at_tick=GetTickCount64()+100;
    bool prepared=RewardOwnedPrepare(f.owner,&f.command);
    if(mode=="cross-force-command"||mode=="append-failure"||mode=="expired"){check(!prepared&&!f.bodies,"bad preparation cannot execute");}
    else{check(prepared,"native list prepared");
        if(mode=="expires-after-prepare")Sleep(120);
        if(mode=="pool-replaced")f.imagePut(0x19e1bf0+0x10,f.addr(f.pheads.data()));
        if(mode=="links-corrupted")put(reinterpret_cast<void*>(f.tails[f.handle]),8,f.heads[f.handle]);
        if(mode=="node-change")put<unsigned>(reinterpret_cast<void*>(f.heads[f.handle]),0,904);
        if(mode=="funding-change")put<unsigned>(f.city.data(),0x34,83000);
        if(mode=="cost-change")f.imagePut<unsigned>(0x18ecf30,2);
        if(mode=="officer-change")put<unsigned char>(f.p1.data(),0x120,95);
        if(mode=="cross-force-officer")put<unsigned char>(f.otherDistrict.data(),0x10,2),put<unsigned char>(f.p1.data(),0x118,2);
        if(mode=="attachment-change")f.attachment=false;
        if(mode=="date-change")put<unsigned char>(f.world.data(),0x37,21);
        if(mode=="cancel")RewardOwnedCancel(f.owner);
        if(mode=="foreign-close"){bool destroyed=true;std::thread t([&]{destroyed=RewardOwnedDestroy(f.owner);});t.join();check(!destroyed&&!f.dtors,"foreign close cannot free list");}
        int result=0;bool caught=false;try{if(mode=="seh-exception")caught=invokeSEH(f);else result=RewardOwnedExecute(f.owner,f.planning.context,1);}catch(const std::runtime_error&e){caught=std::string(e.what())=="reward-original-exception";}
        if(mode=="pool-replaced"||mode=="links-corrupted"){rw::Report retained{};check(RewardOwnedSnapshot(f.owner,&retained)&&result==0&&!f.bodies&&!f.dtors&&!retained.args_released&&retained.error==rw::Error::Cleanup,"uncertain cleanup retains original owner without freeing alien list");check(!RewardOwnedDestroy(f.owner),"destroy refused while native cleanup unproven");if(mode=="pool-replaced")f.imagePut(0x19e1bf0+0x10,f.addr(f.heads.data()));else put<std::uintptr_t>(reinterpret_cast<void*>(f.tails[f.handle]),8,0);check(RewardOwnedDestroy(f.owner)&&f.dtors==1&&f.nodes.empty(),"only restored exact owned layout permits cleanup");f.owner=nullptr;std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"retained_on_uncertainty\":true,\"game_access\":false}\n",mode.c_str());return 0;}
        bool accepted=mode=="success"||mode=="cancel-during"||mode=="foreign-close"||mode=="remote-force-while-local-held";
        if(accepted)check(result==1&&f.bodies==1&&get<unsigned>(f.city.data(),0x34)==83108,"reward body actual effects");
        else if(mode=="exception"||mode=="seh-exception")check(caught&&f.bodies==1,"native exception rethrown after cleanup");
        else if(mode=="zero-result")check(result==0&&f.bodies==1,"zero native result fails closed");
        else check(result==0&&!f.bodies,"changed indirect input rejected before original");
        check(!RewardOwnedExecute(f.owner,f.planning.context,2)&&f.bodies==(accepted||mode=="exception"||mode=="seh-exception"||mode=="zero-result"?1u:0u),"once owner never replayed twice");
    }
    rw::Report r{};check(RewardOwnedSnapshot(f.owner,&r),"snapshot");check(r.args_released&&!r.game_hook_installed&&!r.full_input_hold&&!r.world_thread_fence_proven,"release and honest scope");
    if(prepared||mode=="append-failure")check(f.dtors==1&&f.nodes.empty()&&r.owned_slot_cleared&&r.after_nodes==r.before_nodes&&r.after_handles==r.before_handles,"actual native list resources restored");
    if(mode=="success")check(r.capture_calls==2&&r.native_returned&&r.state==rw::State::Consumed,"fresh deep capture both auth and consumption");
    if(mode=="zero-result")check(r.native_returned,"return zero still proves returned");
    std::printf("{\"result\":\"PASS\",\"case\":\"%s\",\"native_body_calls\":%u,\"ctor\":%u,\"dtor\":%u,\"deep_captures\":%u,\"game_access\":false}\n",mode.c_str(),f.bodies,f.ctors,f.dtors,r.capture_calls);return 0;
}catch(const std::exception&e){std::printf("{\"result\":\"FAIL\",\"case\":\"%s\",\"reason\":\"%s\"}\n",mode.c_str(),e.what());return 1;}}
