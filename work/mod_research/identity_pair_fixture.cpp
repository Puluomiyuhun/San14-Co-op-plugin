#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <stdexcept>
#include <vector>
#include "identity_pair_fixture_code.h"
// This executable never opens the game. Every write targets its own buffers.
alignas(16) static unsigned char root[0x86000],world[0x1700],people[6001][0x200];
alignas(16) static unsigned char forces[52][0x1D0],districts[52][0x28],cities[52][0x168],objects[52][0x20];
alignas(16) static unsigned char ranks[13][0xB8];
static uintptr_t personVT[4],forceVT[13],districtVT[4],cityVT[24],objectVT[4],rankVT[4],worldVT[4];
struct Node {uintptr_t value,next,previous;};
struct Command {uintptr_t vtable,handle,city;};
static Node districtNodes[52],rewardNodes[2][3];
static uintptr_t districtHeads[1],rewardHeads[2];
static uint64_t rewardCounts[2]={3,3};
static uint32_t handles[2]={0,1},filterState[4],contextDummy,policyCalls;
static unsigned char* code;
static const unsigned rewardIds[2][3]={{97,759,904},{101,264,411}};
template<class T> static T rd(const void* p,size_t at){T v;std::memcpy(&v,static_cast<const char*>(p)+at,sizeof v);return v;}
template<class T> static void wr(void* p,size_t at,T v){std::memcpy(static_cast<char*>(p)+at,&v,sizeof v);}
static void check(bool v,const char* message){if(!v)throw std::runtime_error(message);}
static unsigned integer(std::ifstream& f,unsigned limit){uint32_t v=0;check(bool(f.read(reinterpret_cast<char*>(&v),4))&&v<=limit,"input integer");return v;}
static void readBytes(std::ifstream& f,void* p,size_t bytes){check(bool(f.read(static_cast<char*>(p),bytes)),"truncated input");}
static unsigned slot(unsigned rva){for(const auto& s:dataSlots)if(s.rva==rva)return s.offset;throw std::runtime_error("unknown relocated global");}
static int policyEffect(void*,int identity){check(identity==32,"unexpected policy effect");++policyCalls;return 0;}
static void installVT(){
    personVT[3]=uintptr_t(code+fn_person_valid);forceVT[3]=uintptr_t(code+fn_force_valid);forceVT[12]=uintptr_t(code+fn_force_id);
    districtVT[3]=uintptr_t(code+fn_district_valid);objectVT[3]=uintptr_t(code+fn_object_valid);
    cityVT[3]=uintptr_t(code+fn_city_valid);cityVT[16]=uintptr_t(code+fn_city_district);cityVT[18]=uintptr_t(code+fn_money);
    cityVT[19]=uintptr_t(code+fn_set_money);cityVT[22]=uintptr_t(code+fn_city_force_id);cityVT[23]=uintptr_t(code+fn_money_cap);
    rankVT[3]=uintptr_t(code+fn_rank_valid);worldVT[3]=uintptr_t(code+fn_world_valid);wr(world,0,uintptr_t(worldVT));
    for(unsigned i=0;i<13;++i){wr(root,0x77BB8+i*8,uintptr_t(ranks[i]));wr(ranks[i],0,uintptr_t(rankVT));}
    for(unsigned i=0;i<=6000;++i){wr(root,0x148+i*8,uintptr_t(people[i]));wr(people[i],0,uintptr_t(personVT));}
    wr(root,0x737C0,uintptr_t(people[0]));wr(root,0x85130,uintptr_t(world));
    for(unsigned i=0;i<52;++i){
        wr(root,0xDCA0+i*8,uintptr_t(forces[i]));wr(forces[i],0,uintptr_t(forceVT));
        wr(root,0xDE40+i*8,uintptr_t(districts[i]));wr(districts[i],0,uintptr_t(districtVT));
        wr(root,0xDAA8+i*8,uintptr_t(cities[i]));wr(cities[i],0,uintptr_t(cityVT));
        wr(root,0x6D808+i*8,uintptr_t(objects[i]));wr(objects[i],0,uintptr_t(objectVT));
    }
}
static void dump(std::ofstream& out,const std::vector<unsigned>& ids){
    auto normalizedWorld=std::vector<unsigned char>(world,world+sizeof world);normalizedWorld[0x3A]=0;
    std::memset(normalizedWorld.data(),0,8); // Reconstructed local vtable pointer.
    out.write(reinterpret_cast<const char*>(normalizedWorld.data()),normalizedWorld.size());
    // Omit the vtable pointer replaced with a process-local address. Retain all other sampled bytes.
    for(unsigned id:ids)out.write(reinterpret_cast<char*>(people[id]+8),0x1F8);
    for(auto& row:forces)out.write(reinterpret_cast<char*>(row+8),sizeof row-8);
    for(auto& row:districts)out.write(reinterpret_cast<char*>(row+8),sizeof row-8);
    for(auto& row:cities)out.write(reinterpret_cast<char*>(row+8),sizeof row-8);
    for(auto& row:objects)out.write(reinterpret_cast<char*>(row+8),sizeof row-8);
}
int main(int argc,char** argv){
 try{
    check(argc==6,"input viewer mode sequence output arguments required");
    unsigned viewer=unsigned(std::stoul(argv[2]));check(viewer==12||viewer==2,"viewer bounds");
    std::string mode=argv[3],sequence=argv[4];check(mode=="normal"||mode=="counter"||mode=="native_init","mode");
    check(!sequence.empty()&&sequence.size()<=3,"sequence length");
    std::ifstream input(argv[1],std::ios::binary);check(bool(input),"input file");check(integer(input,0x1414FACE)==0x1414FACE,"input magic");
    readBytes(input,world,sizeof world);std::vector<unsigned> ids;unsigned count=integer(input,6001);
    for(unsigned i=0;i<count;++i){unsigned id=integer(input,6000);ids.push_back(id);readBytes(input,people[id],0x200);}
    readBytes(input,forces,sizeof forces);readBytes(input,districts,sizeof districts);readBytes(input,cities,sizeof cities);readBytes(input,objects,sizeof objects);
    readBytes(input,ranks,sizeof ranks);
    unsigned n=integer(input,52);check(n>0,"empty district list");
    for(unsigned i=0;i<n;++i){unsigned id=integer(input,51);districtNodes[i]={uintptr_t(districts[id]),i+1<n?uintptr_t(&districtNodes[i+1]):0,i?uintptr_t(&districtNodes[i-1]):0};}
    check(input.peek()==EOF,"extra input data");check(world[0xBC]==255,"source mode not current planning baseline");
    if(mode!="native_init")world[0x3A]=static_cast<unsigned char>(viewer);if(mode=="counter")world[0xBC]=0;
    code=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x10000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));check(code!=nullptr,"local code allocation");
    for(const auto& b:nativeBlocks)std::memcpy(code+b.offset,b.bytes,b.size);
    for(const auto& p:patches)wr(code,p.at,int32_t(p.target)-int32_t(p.next));
    for(const auto& s:dataSlots)std::memcpy(code+s.offset,s.bytes,8);
    code[0xB000]=0x48;code[0xB001]=0xB8;wr(code,0xB002,uintptr_t(&policyEffect));code[0xB00A]=0xFF;code[0xB00B]=0xE0;
    code[0xB020]=code[0xB040]=0x0F;code[0xB021]=code[0xB041]=0x0B; // Unsupported branches trap.
    installVT();districtHeads[0]=uintptr_t(districtNodes);wr(root,0xD0,uintptr_t(&handles[0]));
    wr(code,slot(0x1FCA1E0),uintptr_t(root));wr(code,slot(0x201D3A8),uintptr_t(1));
    wr(code,slot(0x201D3B0),uintptr_t(districtHeads));wr(code,slot(0x201D3E0),uint32_t(0x14000));
    wr(code,slot(0x129FB70)+8,uintptr_t(code+fn_district_member));wr(code,slot(0x1FC8488),uintptr_t(&contextDummy));
    wr(code,slot(0x201EC70),uintptr_t(filterState));
    wr(code,slot(0x19E1C00),uintptr_t(rewardHeads));wr(code,slot(0x19E1C18),uintptr_t(rewardCounts));wr(code,slot(0x19E1C30),uint32_t(0x400));
    for(unsigned faction=0;faction<2;++faction){rewardHeads[faction]=uintptr_t(&rewardNodes[faction][0]);
        for(unsigned i=0;i<3;++i)rewardNodes[faction][i]={rewardIds[faction][i],i<2?uintptr_t(&rewardNodes[faction][i+1]):0,i?uintptr_t(&rewardNodes[faction][i-1]):0};}
    DWORD old=0;check(VirtualProtect(code,0xC000,PAGE_EXECUTE_READ,&old)!=FALSE,"local code protection");check(FlushInstructionCache(GetCurrentProcess(),code,0xC000)!=FALSE,"local cache flush");
    unsigned initializerWrites=0;
    if(mode=="native_init"){
        check(rd<uint32_t>(world,0x40)==1,"initializer mode not captured normal game");
        unsigned char previous[sizeof world];std::memcpy(previous,world,sizeof world);
        auto initialize=reinterpret_cast<void(*)(void*)>(code+fn_initialize_player);
        initialize(people[viewer==12?666:952]);
        for(unsigned i=0;i<sizeof world;++i)if(previous[i]!=world[i]){check(i==0x3A||i==0x165D,"unexpected initializer world write");++initializerWrites;}
        check(world[0x3A]==viewer&&world[0x165D]==(viewer==12?2:1),"native initializer identity/rank fields");
    }
    auto playerForce=reinterpret_cast<void*(*)(void*)>(code+fn_player_force);
    auto mainDistrict=reinterpret_cast<void*(*)(void*)>(code+fn_player_main);
    auto isPlayer=reinterpret_cast<int(*)(void*)>(code+fn_is_player);
    auto currentForce=reinterpret_cast<unsigned char*>(playerForce(world));auto currentDistrict=reinterpret_cast<unsigned char*>(mainDistrict(world));
    check(currentForce==forces[viewer],"native local force mismatch");unsigned main=unsigned((currentDistrict-districts[0])/0x28);
    check(main==(viewer==12?11u:2u),"native main district mismatch");check(isPlayer(forces[12])==int(viewer==12)&&isPlayer(forces[2])==int(viewer==2),"native local ownership mismatch");
    auto submit=reinterpret_cast<int(*)(void*)>(code+fn_reward);
    auto cap=reinterpret_cast<int(*)(void*)>(code+fn_money_cap);
    check(cap(cities[13])==100000&&cap(cities[19])==100000,"unexpected native gold cap");
    unsigned beforePolicy=policyCalls,submitted=0;unsigned beforeCounter=rd<uint32_t>(world,0x80);
    for(char c:sequence){check(c=='A'||c=='B',"command actor");unsigned which=c=='B';Command command{0,uintptr_t(&handles[which]),uintptr_t(cities[which?13:19])};
        check(submit(&command)==1,"native reward rejected");++submitted;
        check(world[0x3A]==viewer&&mainDistrict(world)==currentDistrict,"command changed local identity");}
    // A controlled counterexample: this predicate depends on local identity
    // when its outer special-filter path is enabled. This is not a battle run.
    alignas(8) unsigned char attacker[24]{},pair[32]{};wr(attacker,16,uint32_t(12));wr(pair,0,uintptr_t(attacker));wr(pair,8,uint16_t(5));wr(pair,12,uint32_t(6));
    auto filter=reinterpret_cast<int(*)(void*)>(code+fn_combat_filter);int gateAllowed=filter(pair);wr(pair,12,uint32_t(27));int armyAllowed=filter(pair);
    check(gateAllowed==int(viewer!=12)&&armyAllowed==1,"native identity-sensitive control mismatch");
    std::ofstream output(argv[5],std::ios::binary);check(bool(output),"output open");dump(output,ids);check(bool(output),"output write");output.close();
    printf("{\"result\":\"PASS\",\"pid\":%lu,\"viewer\":%u,\"main_district\":%u,\"sequence\":\"%s\",\"mode\":\"%s\",\"initializer_changed_world_bytes\":%u,\"rank_derived_field\":%u,\"native_reward_calls\":%u,\"policy_effect_stub_calls\":%u,\"local_identity_preserved\":true,\"gold_A\":%u,\"gold_B\":%u,\"actions_A\":%u,\"actions_B\":%u,\"loyalty_A\":[%u,%u,%u],\"loyalty_B\":[%u,%u,%u],\"flags_A\":[%u,%u,%u],\"flags_B\":[%u,%u,%u],\"counter_delta\":%u,\"special_filter_gate_allowed\":%d,\"special_filter_army_allowed\":%d,\"game_process_access\":false}\n",
        GetCurrentProcessId(),viewer,main,sequence.c_str(),mode.c_str(),initializerWrites,world[0x165D],submitted,policyCalls-beforePolicy,
        rd<uint32_t>(cities[19],0x34),rd<uint32_t>(cities[13],0x34),districts[11][0x14],districts[2][0x14],
        people[97][0x120],people[759][0x120],people[904][0x120],people[101][0x120],people[264][0x120],people[411][0x120],
        rd<uint16_t>(people[97],0x196),rd<uint16_t>(people[759],0x196),rd<uint16_t>(people[904],0x196),
        rd<uint16_t>(people[101],0x196),rd<uint16_t>(people[264],0x196),rd<uint16_t>(people[411],0x196),rd<uint32_t>(world,0x80)-beforeCounter,gateAllowed,armyAllowed);
    VirtualFree(code,0,MEM_RELEASE);return 0;
 }catch(const std::exception& e){fprintf(stderr,"%s\n",e.what());if(code)VirtualFree(code,0,MEM_RELEASE);return 1;}
}
