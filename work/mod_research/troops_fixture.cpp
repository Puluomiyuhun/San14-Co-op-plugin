#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include "troops_fixture_code.h"
// Ordinary independent executable. Never opens SAN14 or installs a hook.
alignas(16) static unsigned char root[0x86000], persons[6001][0x200];
alignas(16) static unsigned char armies[501][0x200], groups[501][0x40], districts[52][0x28];
static uintptr_t personVT[4], armyVT[4], districtVT[4];
struct Node {uintptr_t value,next,previous;};
struct Relation {uintptr_t values[3],unused[3],next,previous;};
static Node nodes[2][501];
static Relation relations[501];
static uintptr_t heads[2], relationHead[1];
static uint32_t handles[3]={0,1,0};
template<class T> static void wr(void* ptr,size_t offset,T v){std::memcpy(static_cast<char*>(ptr)+offset,&v,sizeof v);}
static void check(bool value,const char* message){if(!value)throw std::runtime_error(message);}
static unsigned number(std::ifstream& input,unsigned maximum){unsigned v=0;check(bool(input>>v)&&v<=maximum,"input bounds");return v;}
static uintptr_t armyOrNull(std::ifstream& input){int i=0;check(bool(input>>i)&&i>=-1&&i<=500,"relation identity");return i<0?0:reinterpret_cast<uintptr_t>(armies[i]);}
int main(int argc,char** argv){
    unsigned char* code=nullptr;
    try{
        check(argc==2,"case file required");std::ifstream input(argv[1]);check(bool(input),"case file open");
        code=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x3000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));check(code!=nullptr,"local allocation");
        for(const auto& b:nativeBlocks)std::memcpy(code+b.offset,b.bytes,b.size);
        for(const auto& p:patches)wr(code,p.at,int32_t(p.target)-int32_t(p.next));
        wr(code,0x2000,reinterpret_cast<uintptr_t>(root));wr(code,0x2108,reinterpret_cast<uintptr_t>(code+0x300));
        wr(code,0x2208,uintptr_t(1));wr(code,0x2210,reinterpret_cast<uintptr_t>(heads));wr(code,0x2240,uint32_t(0x14000));
        wr(code,0x2290,reinterpret_cast<uintptr_t>(relationHead));wr(code,0x22C0,uint32_t(64));
        personVT[3]=reinterpret_cast<uintptr_t>(code+0x700);armyVT[3]=reinterpret_cast<uintptr_t>(code+0x800);districtVT[3]=reinterpret_cast<uintptr_t>(code+0xA00);
        DWORD old=0;check(VirtualProtect(code,0x2000,PAGE_EXECUTE_READ,&old)!=FALSE,"local protection");check(FlushInstructionCache(GetCurrentProcess(),code,0x2000)!=FALSE,"local instruction cache");
        using Getter=int(*)(void*);auto getter=reinterpret_cast<Getter>(code);
        unsigned cases=number(input,1000), checks=0;
        check(cases>0,"empty cases");
        for(unsigned c=0;c<cases;++c){
            std::memset(root,0,sizeof root);std::memset(persons,0,sizeof persons);std::memset(armies,0,sizeof armies);std::memset(districts,0,sizeof districts);
            std::memset(nodes,0,sizeof nodes);std::memset(relations,0,sizeof relations);heads[0]=heads[1]=relationHead[0]=0;
            wr(root,0x60,reinterpret_cast<uintptr_t>(&handles[0]));wr(root,0x70,reinterpret_cast<uintptr_t>(&handles[1]));wr(root,0x140,reinterpret_cast<uintptr_t>(&handles[2]));
            wr(root,0x737C0,reinterpret_cast<uintptr_t>(persons[0]));
            for(unsigned i=0;i<=6000;++i){wr(root,0x148+i*8,reinterpret_cast<uintptr_t>(persons[i]));wr(persons[i],0,reinterpret_cast<uintptr_t>(personVT));}
            unsigned people=number(input,6001);
            for(unsigned p=0;p<people;++p){unsigned slot=number(input,6000);wr(persons[slot],0x10,uint16_t(number(input,65535)));wr(persons[slot],0x118,uint8_t(number(input,255)));wr(persons[slot],0x11E,uint8_t(number(input,255)));}
            for(unsigned i=0;i<=500;++i){
                wr(root,0x7DF60+i*8,reinterpret_cast<uintptr_t>(armies[i]));wr(root,0x7F000+i*8,reinterpret_cast<uintptr_t>(groups[i]));wr(armies[i],0,reinterpret_cast<uintptr_t>(armyVT));
                wr(armies[i],0x10,uint8_t(number(input,255)));wr(armies[i],0x12,uint16_t(number(input,65535)));wr(armies[i],0x58,uint16_t(number(input,65535)));
            }
            for(unsigned i=0;i<52;++i){
                wr(root,0xDE40+i*8,reinterpret_cast<uintptr_t>(districts[i]));wr(districts[i],0,reinterpret_cast<uintptr_t>(districtVT));
                wr(districts[i],0x10,uint8_t(number(input,255)));wr(districts[i],0x11,uint8_t(number(input,255)));wr(districts[i],0x12,uint16_t(number(input,65535)));
            }
            for(unsigned list=0;list<2;++list){unsigned count=number(input,501);if(count)heads[list]=reinterpret_cast<uintptr_t>(&nodes[list][0]);
                for(unsigned i=0;i<count;++i){auto& n=nodes[list][i];n.value=reinterpret_cast<uintptr_t>(armies[number(input,500)]);n.next=i+1<count?reinterpret_cast<uintptr_t>(&nodes[list][i+1]):0;n.previous=i?reinterpret_cast<uintptr_t>(&nodes[list][i-1]):0;}}
            unsigned count=number(input,500);if(count)relationHead[0]=reinterpret_cast<uintptr_t>(&relations[0]);
            for(unsigned i=0;i<count;++i){auto& n=relations[i];for(unsigned j=0;j<3;++j)n.values[j]=armyOrNull(input);n.next=i+1<count?reinterpret_cast<uintptr_t>(&relations[i+1]):0;n.previous=i?reinterpret_cast<uintptr_t>(&relations[i-1]):0;}
            for(unsigned i=0;i<=500;++i){unsigned expected=number(input,255);int actual=getter(groups[i]);if(actual!=int(expected)){printf("{\"case\":%u,\"group\":%u,\"expected\":%u,\"actual\":%d}\n",c,i,expected,actual);throw std::runtime_error("native/Python group district mismatch");}++checks;}
        }
        std::string extra;check(!(input>>extra),"trailing case data");
        printf("{\"result\":\"PASS\",\"scenarios\":%u,\"native_getter_comparisons\":%u,\"native_blocks\":10,\"query_stubs\":0,\"game_process_access\":false}\n",cases,checks);
        VirtualFree(code,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){fprintf(stderr,"%s\n",e.what());if(code)VirtualFree(code,0,MEM_RELEASE);return 1;}
}
