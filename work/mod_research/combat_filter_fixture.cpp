#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <stdexcept>
#include "combat_filter_fixture_code.h"

// Local buffers only. No OpenProcess, injection or native game calls.
alignas(16) static unsigned char root[0x86000],world[0x1700],forces[52][0x200],filterState[16];
static uintptr_t forceVtable[13];
template<class T> T rd(const void* p,size_t off){T x;std::memcpy(&x,static_cast<const char*>(p)+off,sizeof x);return x;}
template<class T> void wr(void* p,size_t off,T x){std::memcpy(static_cast<char*>(p)+off,&x,sizeof x);}
static int forceId(void* p){return rd<int>(p,8);}
static int valid(void* p){return p && forceId(p)>0 && forceId(p)<52;}
static void check(bool x,const char* why){if(!x)throw std::runtime_error(why);}
struct Pair {uintptr_t attacker;unsigned char target[24];};
using Filter=int(*)(void*);
using Relation=int(*)(int,int);

int main(){
    unsigned char* local=nullptr;
    try {
        forceVtable[12]=reinterpret_cast<uintptr_t>(&forceId);
        wr(root,0x85130,reinterpret_cast<uintptr_t>(world));world[0x3a]=12;
        for(unsigned i=0;i<52;i++){
            wr(root,0xdca0+i*8,reinterpret_cast<uintptr_t>(forces[i]));
            wr(forces[i],0,reinterpret_cast<uintptr_t>(forceVtable));
            wr(forces[i],8,int(i));forces[i][0x12]=originalForceFlags[i];
        }
        local=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x3000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));
        check(local!=nullptr,"Local allocation failed");
        std::memcpy(local,code_filter,sizeof code_filter);
        std::memcpy(local+0x200,code_is_player,sizeof code_is_player);
        std::memcpy(local+0x400,code_player_force,sizeof code_player_force);
        std::memcpy(local+0x600,code_relation,sizeof code_relation);
        auto p=reinterpret_cast<uintptr_t>(&valid);
        local[0x1000]=0x48;local[0x1001]=0xb8;wr(local,0x1002,p);local[0x100a]=0xff;local[0x100b]=0xe0;
        for(const auto& patch:patches)wr(local,patch.at,int32_t(patch.target)-int32_t(patch.next));
        for(const auto& slot:slots)wr(local,slot.offset,reinterpret_cast<uintptr_t>(slot.rva==0x1fca1e0?root:filterState));
        DWORD old=0;check(VirtualProtect(local,0x2000,PAGE_EXECUTE_READ,&old)!=FALSE,"Code protection");
        check(FlushInstructionCache(GetCurrentProcess(),local,0x2000)!=FALSE,"Instruction cache");
        auto filter=reinterpret_cast<Filter>(local);auto relation=reinterpret_cast<Relation>(local+0x600);
        unsigned allow=0;
        for(unsigned i=0;i<17;i++){
            Pair pair{};pair.attacker=reinterpret_cast<uintptr_t>(realPairs[i][0]);std::memcpy(pair.target,realPairs[i][1],24);
            int result=filter(&pair);check(result==1,"Recorded pair unexpectedly filtered");allow+=result!=0;
            std::printf("{\"case\":\"F-first-pair\",\"index\":%u,\"source_kind\":%u,\"source_id\":%u,\"source_force\":%u,\"target_kind\":%u,\"target_id\":%u,\"allowed\":%d}\n",
                i,rd<uint32_t>(realPairs[i][0],4),rd<uint16_t>(realPairs[i][0],0),rd<uint32_t>(realPairs[i][0],16),
                rd<uint32_t>(pair.target,4),rd<uint16_t>(pair.target,0),result);
        }
        unsigned playerSweep=0,minAllowed=17;
        for(unsigned player=0;player<52;player++){
            world[0x3a]=static_cast<unsigned char>(player);unsigned accepted=0;
            for(unsigned i=0;i<17;i++){
                Pair pair{};pair.attacker=reinterpret_cast<uintptr_t>(realPairs[i][0]);std::memcpy(pair.target,realPairs[i][1],24);
                int result=filter(&pair);accepted+=result!=0;playerSweep++;
                if(rd<uint32_t>(pair.target,4)==27)check(result==1,"Army target must pass special filter");
            }
            if(accepted<minAllowed)minAllowed=accepted;
        }
        check(minAllowed==15,"Unexpected minimum accepted pairs in player sweep");world[0x3a]=12;
        // Positive and negative controls prove the fixture is not just an always-true stub.
        unsigned char attacker[24]{};wr(attacker,16,uint32_t(12));Pair pair{};pair.attacker=reinterpret_cast<uintptr_t>(attacker);
        auto control=[&](const char* name,unsigned source,unsigned kind,unsigned id,unsigned mode,int expected){
            wr(attacker,16,uint32_t(source));wr(pair.target,4,uint32_t(kind));wr(pair.target,0,uint16_t(id));wr(filterState,4,uint32_t(mode));
            int result=filter(&pair);check(result==expected,"Filter branch control failed");
            std::printf("{\"case\":\"%s\",\"allowed\":%d,\"passed\":true}\n",name,result);
        };
        control("player-army-target",12,27,57,0,1);
        control("player-gate-target-blocked",12,6,5,0,0);
        control("nonplayer-gate-target-allowed",11,6,5,0,1);
        control("player-city7-allowed",12,5,7,0,1);
        control("player-city5-mode0-blocked",12,5,5,0,0);
        control("player-city5-mode3-allowed",12,5,5,3,1);
        control("player-other-city-blocked",12,5,14,3,0);
        unsigned comparisons=0;
        for(int a=0;a<52;a++)for(int b=0;b<52;b++){
            world[0x165c]=0;int off=relation(a,b);world[0x165c]=1;int on=relation(a,b);
            check(on==off,"Global world flag changed relation with force flags zero");comparisons++;
        }
        forces[1][0x12]=forces[2][0x12]=2;
        world[0x165c]=0;check(relation(1,2)==1,"Two-force control off");
        world[0x165c]=1;check(relation(1,2)==0,"Two-force control on");
        forces[2][0x12]=0;check(relation(1,2)==1,"Single-force flag must not block");
        forces[1][0x12]=0;world[0x165c]=0;
        unsigned char oldSample1[0x30],oldSample2[0x30];
        std::memcpy(oldSample1,forces[1]+0x10,0x30);std::memcpy(oldSample2,forces[2]+0x10,0x30);
        check(relation(1,2)==1,"Relationship initial control");
        forces[1][0xea+2]=1;check(relation(1,2)==0,"Directional relationship byte must reject");forces[1][0xea+2]=0;
        forces[1][0x194]=2;check(relation(1,2)==0,"Source relationship owner must reject");forces[1][0x194]=0;
        forces[2][0x194]=1;check(relation(1,2)==0,"Target relationship owner must reject");forces[2][0x194]=0;
        check(!std::memcmp(oldSample1,forces[1]+0x10,0x30)&&!std::memcmp(oldSample2,forces[2]+0x10,0x30),"Old sampled fields changed");
        std::printf("{\"case\":\"summary\",\"result\":\"PASS\",\"recorded_pairs_allowed\":%u,\"player_pair_tests\":%u,\"minimum_pairs_allowed_any_player\":%u,\"filter_controls\":7,\"world_flag_pair_comparisons\":%u,\"world_flag_controls\":3,\"hidden_relation_controls\":3,\"old_force_sample_unchanged\":true,\"game_access\":false}\n",allow,playerSweep,minAllowed,comparisons);
        VirtualFree(local,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"FAILED: %s\n",e.what());if(local)VirtualFree(local,0,MEM_RELEASE);return 1;}
}
