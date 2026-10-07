#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <set>
#include <vector>
#include "combat_inputs_fixture_code.h"

// Local objects only. The fixture never obtains a handle to the game.
struct Object {uint32_t valid,force,id,unused;};
struct PointerNode {Object* object;PointerNode* next;};
struct AnnihilateNode {Object* field00;Object* field08;Object* field10;uint64_t rest[3];AnnihilateNode* next;};
struct Side {unsigned char bytes[32];};
struct Pair {Side* a;unsigned char b[32];void* effect;Pair* next;Pair* prev;};
static_assert(sizeof(Pair)==0x40 && offsetof(Pair,next)==0x30 && offsetof(AnnihilateNode,next)==0x30);
static unsigned char root[0x148];
static uint32_t pointerHandle=0,annihilateHandle=0;
static PointerNode* pointerHeads[2];static AnnihilateNode* annihilateHeads[2];
static unsigned destructorCalls=0;
static int valid(Object* o) {return o&&o->valid?1:0;}
static int force(Object* o) {if(!o)std::abort();return int(o->force);}
static void destroy(void*) {destructorCalls++;}
static void unsupported() {std::fprintf(stderr,"Unexpected facility/presentation dependency\n");std::abort();}
template<class T> static void put(void* p,size_t at,T v) {std::memcpy(static_cast<unsigned char*>(p)+at,&v,sizeof(v));}
static void check(bool b,const char* msg) {if(!b)throw std::runtime_error(msg);}
using Predicate=int(*)(Object*);
using Compare=int(*)(void*,Pair*,Pair*);
using Sort=void(*)(void*,unsigned char);

static std::vector<int> nativeSort(Sort sort,const std::vector<int>& order,std::array<Side,17>& sides,const std::array<Pair,17>& source) {
    std::array<Pair,17> nodes{};unsigned char container[0x40]{};
    for(size_t i=0;i<order.size();i++) {
        auto id=order[i];nodes[id]=source[id];nodes[id].a=&sides[id];
        nodes[id].prev=i?&nodes[order[i-1]]:nullptr;nodes[id].next=i+1<order.size()?&nodes[order[i+1]]:nullptr;
    }
    put<Pair*>(container,0x10,order.empty()?nullptr:&nodes[order.front()]);
    put<Pair*>(container,0x18,order.empty()?nullptr:&nodes[order.back()]);
    sort(container,0x40);
    Pair* node;std::memcpy(&node,container+0x10,8);Pair* previous=nullptr;std::vector<int> result;
    while(node) {
        check(node>=nodes.data()&&node<nodes.data()+17,"Sort produced invalid local node");
        auto id=int(node-nodes.data());check(std::find(result.begin(),result.end(),id)==result.end(),"Sort produced cycle");
        check(node->prev==previous,"Sort reverse link mismatch");result.push_back(id);previous=node;node=node->next;
    }
    check(result.size()==order.size(),"Sort lost nodes");return result;
}
int main() {
    unsigned char* local=nullptr;
    try {
        local=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));check(local,"Local allocation failed");
        std::memcpy(local,code_predicate,sizeof(code_predicate));std::memcpy(local+0x400,code_compare,sizeof(code_compare));std::memcpy(local+0x800,code_sort,sizeof(code_sort));
        uint64_t stubs[]={reinterpret_cast<uint64_t>(&valid),reinterpret_cast<uint64_t>(&force),reinterpret_cast<uint64_t>(&destroy),reinterpret_cast<uint64_t>(&unsupported)};
        for(unsigned i=0;i<4;i++) {auto t=local+0xc00+16*i;t[0]=0x48;t[1]=0xb8;std::memcpy(t+2,&stubs[i],8);t[10]=0xff;t[11]=0xe0;}
        for(auto p:codePatches) {int32_t delta=int32_t(p.target)-int32_t(p.next);put<int32_t>(local,p.at,delta);}
        for(auto s:dataSlots) {
            uint64_t value=0;
            switch(s.rva) {
                case 0x1FCA1E0:value=reinterpret_cast<uint64_t>(root);break;
                case 0x201D3A8:value=1;break;
                case 0x201D3B0:value=reinterpret_cast<uint64_t>(pointerHeads);break;
                case 0x201D3E0:value=2;break;
                case 0x1FC9770:value=reinterpret_cast<uint64_t>(annihilateHeads);break;
                case 0x1FC97A0:value=2;break;
                default:throw std::runtime_error("Unmapped RIP data");
            }
            put<uint64_t>(local,s.local,value);
        }
        DWORD old=0;check(VirtualProtect(local,0x1000,PAGE_EXECUTE_READ,&old)!=FALSE,"Protect code failed");
        check(FlushInstructionCache(GetCurrentProcess(),local,0x1000)!=FALSE,"Flush local code failed");
        auto predicate=reinterpret_cast<Predicate>(local);auto compare=reinterpret_cast<Compare>(local+0x400);auto sort=reinterpret_cast<Sort>(local+0x800);
        put<uint32_t*>(root,0x70,&pointerHandle);put<uint32_t*>(root,0x140,&annihilateHandle);
        Object target{1,12,1,0},other{1,7,2,0},source{1,3,3,0},invalid{0,7,4,0};
        const auto originalTarget=target;
        PointerNode tail{&target,nullptr},head{&other,&tail};AnnihilateNode row{};
        auto test=[&](const char* label,int expected) {int result=predicate(&target);check(result==expected,label);check(std::memcmp(&target,&originalTarget,sizeof(target))==0,"Predicate changed object record");std::printf("{\"case\":\"%s\",\"result\":\"PASS\",\"predicate\":%d}\n",label,result);};
        test("empty-lists",0);pointerHeads[0]=&head;test("root68-membership-at-tail",1);
        tail.object=&other;test("root68-other-only",0);tail.object=&target;pointerHeads[0]=nullptr;
        annihilateHeads[0]=&row;row.field00=&target;test("annihilate-first-member-valid",1);
        row.field00=&invalid;test("annihilate-first-member-other-invalid",0);
        row.field00=&other;row.field08=&source;row.field10=&target;test("annihilate-third-member-normal-force",1);
        row.field08=nullptr;test("annihilate-third-member-missing-second",0);
        row.field08=&invalid;test("annihilate-third-member-invalid-second",0);
        row.field08=&source;Object special=target;row.field10=&special;
        for(unsigned f:{46u,47u,48u,49u,50u,51u}) {
            special.force=f;
            check(predicate(&special)==0,"Special-force exclusion mismatch");
            std::printf("{\"case\":\"annihilate-special-force-%u\",\"result\":\"PASS\",\"predicate\":0}\n",f);
        }
        special.force=45;check(predicate(&special)==1,"Normal-force boundary mismatch");
        std::printf("{\"case\":\"annihilate-normal-force-45\",\"result\":\"PASS\",\"predicate\":1}\n");
        row.field00=&target;row.field08=nullptr;test("annihilate-first-independent-of-second",1);
        annihilateHeads[0]=nullptr;test("lists-cleared",0);

        std::array<Side,17> sides{};std::array<Pair,17> pairs{};
        for(unsigned i=0;i<17;i++) {std::memcpy(sides[i].bytes,realPairs[i][0],24);pairs[i].a=&sides[i];std::memcpy(pairs[i].b,realPairs[i][1],24);}
        int matrix[17][17];unsigned symmetricTrue=0;
        for(unsigned i=0;i<17;i++)for(unsigned j=0;j<17;j++)matrix[i][j]=compare(nullptr,&pairs[i],&pairs[j]);
        for(unsigned i=0;i<17;i++)for(unsigned j=i+1;j<17;j++)if(matrix[i][j]&&matrix[j][i])symmetricTrue++;
        for(unsigned i=0;i<17;i++)for(unsigned o:{2u,3u,9u}) {sides[i].bytes[o]^=0x5a;pairs[i].b[o]^=0xa5;}
        for(unsigned i=0;i<17;i++)for(unsigned j=0;j<17;j++)check(compare(nullptr,&pairs[i],&pairs[j])==matrix[i][j],"Unmapped byte changed comparator");
        std::printf("{\"case\":\"real-F-comparison-matrix-unmapped-bytes\",\"result\":\"PASS\",\"comparisons\":289,\"distinct_symmetric_true_pairs\":%u}\n",symmetricTrue);
        std::vector<int> ordered;for(int i=0;i<17;i++)ordered.push_back(i);
        auto sorted=nativeSort(sort,ordered,sides,pairs);check(sorted==ordered,"Recorded F pair order not reproduced");
        auto reversed=ordered;std::reverse(reversed.begin(),reversed.end());auto reverseSorted=nativeSort(sort,reversed,sides,pairs);
        std::set<std::vector<int>> distinctOrders{ordered,reversed};
        unsigned identical=0;auto perm=ordered;
        for(unsigned shift=0;shift<17;shift++) {std::rotate(perm.begin(),perm.begin()+1,perm.end());distinctOrders.insert(perm);if(nativeSort(sort,perm,sides,pairs)==ordered)identical++;}
        check(identical==17&&reverseSorted==ordered,"Real F set has input-order-sensitive sorting");
        check(distinctOrders.size()==18,"Unexpected distinct order count");
        std::printf("{\"case\":\"real-F-native-sort\",\"result\":\"PASS\",\"pairs\":17,\"sort_runs\":19,\"distinct_input_orders\":18,\"same_output\":true}\n");
        // Construct a tie using the same defender and attacker priority/troops, but different attacker IDs.
        sides[1]=sides[0];pairs[1]=pairs[0];pairs[1].a=&sides[1];
        put<uint32_t>(sides[0].bytes,4,27);put<uint32_t>(sides[1].bytes,4,27);
        put<uint16_t>(sides[0].bytes,0,101);put<uint16_t>(sides[1].bytes,0,102);
        check(compare(nullptr,&pairs[0],&pairs[1])==1&&compare(nullptr,&pairs[1],&pairs[0])==1,"Synthetic tie not reached");
        auto forward=nativeSort(sort,{0,1},sides,pairs);auto backward=nativeSort(sort,{1,0},sides,pairs);
        check(forward==std::vector<int>({1,0})&&backward==std::vector<int>({0,1}),"Native tie sort changed");
        std::printf("{\"case\":\"synthetic-equal-army-priorities\",\"result\":\"PASS\",\"both_directions_true\":true,\"input_0_1_output\":[1,0],\"input_1_0_output\":[0,1],\"real_game_occurrence_proven\":false}\n");
        VirtualFree(local,0,MEM_RELEASE);return 0;
    } catch(const std::exception& e) {std::fprintf(stderr,"Fixture failed: %s\n",e.what());if(local)VirtualFree(local,0,MEM_RELEASE);return 1;}
}
