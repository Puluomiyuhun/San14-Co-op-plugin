#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <stdexcept>
#include "human_ai_fixture_code.h"
#include "../../outputs/san14-link/human_ai_policy.h"
using namespace san14_link;
// Isolated copied code; never opens SAN14 or executes an actual AI body.
alignas(16) static unsigned char root[0x86000], world[0x1700], forces[52][0x200];
alignas(16) static unsigned char districts[52][0x28], persons[52][0x198], armies[52][0x200], groups[52][0x60], manager[0x40];
static uintptr_t forceVtable[13];
static unsigned mains[52], owner[52], aiCalls[4], checks, holds;
static void* expectedObject;
static void* expectedContext;
static bool argsOK;
template<class T> static T rd(const void* p,size_t o){T v;std::memcpy(&v,static_cast<const char*>(p)+o,sizeof v);return v;}
template<class T> static void wr(void* p,size_t o,T v){std::memcpy(static_cast<char*>(p)+o,&v,sizeof v);}
static void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
static int forceId(void* p){return rd<int>(p,8);}
static void* mainDistrict(void* force){return districts[mains[forceId(force)]];}
static int personValid(void* p){return rd<unsigned short>(p,0x10)!=0;}
static int groupDistrict(void* p){return rd<int>(p,8);}
static void note(unsigned i,void* ctx,void* obj){++aiCalls[i];argsOK=ctx==expectedContext&&obj==expectedObject;}
static void forceAI(void* c,void* o){note(0,c,o);}
static void districtAI(void* c,void* o){note(1,c,o);}
static void armyAI(void* c,void* o){note(2,c,o);}
static void groupAI(void* c,void* o){note(3,c,o);}
using Wrapper=void(*)(void*,void*);
static Wrapper wrappers[4];
static unsigned run(unsigned route,unsigned identity){
    std::memset(aiCalls,0,sizeof aiCalls);argsOK=true;
    void* objects[]={forces[identity],districts[identity],armies[identity],groups[identity]};
    expectedObject=objects[route];expectedContext=reinterpret_cast<void*>(uintptr_t(0x10000+route*0x100));
    wrappers[route](manager,expectedObject);
    unsigned total=0;for(unsigned i=0;i<4;++i){total+=aiCalls[i];check(i==route||aiCalls[i]==0,"wrong AI destination");}
    check(total<=1&&argsOK,"incorrect argument or duplicate AI dispatch");
    return total;
}
static AiSubject subject(unsigned route,unsigned id){return {route==0?id:owner[id],route==0?0:id,true};}
static unsigned policyRun(const HumanControl& control,unsigned route,unsigned id){
    auto decision=decide_ai(control,static_cast<AiRoute>(route),subject(route,id),false);
    check(decision!=AiDecision::Hold,"valid fixture subject unexpectedly held");
    return decision==AiDecision::Native?run(route,id):0;
}
int main(int argc,char** argv){
    unsigned char* local=nullptr;
    try{
        forceVtable[12]=reinterpret_cast<uintptr_t>(&forceId);
        wr(root,0x85130,reinterpret_cast<uintptr_t>(world));
        for(unsigned i=0;i<52;++i){
            wr(root,0xdca0+i*8,reinterpret_cast<uintptr_t>(forces[i]));wr(forces[i],0,reinterpret_cast<uintptr_t>(forceVtable));wr(forces[i],8,int(i));
            wr(root,0xde40+i*8,reinterpret_cast<uintptr_t>(districts[i]));mains[i]=1;
            wr(root,0x148+i*8,reinterpret_cast<uintptr_t>(persons[i]));wr(persons[i],0x10,static_cast<unsigned short>(i));persons[i][0x118]=static_cast<unsigned char>(i);
            wr(armies[i],0x12,static_cast<unsigned short>(i));wr(groups[i],8,int(i));owner[i]=1;
        }
        mains[12]=11;mains[2]=2;owner[11]=owner[21]=12;owner[2]=owner[20]=2;
        wr(manager,0x10,uintptr_t(0x10000));wr(manager,0x18,uintptr_t(0x10100));wr(manager,0x28,uintptr_t(0x10200));wr(manager,0x20,uintptr_t(0x10300));
        local=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x3000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));check(local!=nullptr,"local allocation");
        for(const auto& block:nativeBlocks)std::memcpy(local+block.offset,block.bytes,block.size);
        const uintptr_t stubs[]={reinterpret_cast<uintptr_t>(&mainDistrict),reinterpret_cast<uintptr_t>(&personValid),reinterpret_cast<uintptr_t>(&groupDistrict),
            reinterpret_cast<uintptr_t>(&armyAI),reinterpret_cast<uintptr_t>(&districtAI),reinterpret_cast<uintptr_t>(&forceAI),reinterpret_cast<uintptr_t>(&groupAI)};
        for(unsigned i=0;i<7;++i){unsigned at=0x1000+i*0x20;local[at]=0x48;local[at+1]=0xb8;wr(local,at+2,stubs[i]);local[at+10]=0xff;local[at+11]=0xe0;}
        for(const auto& p:patches)wr(local,p.at,int32_t(p.target)-int32_t(p.next));wr(local,0x2000,reinterpret_cast<uintptr_t>(root));
        DWORD old=0;check(VirtualProtect(local,0x2000,PAGE_EXECUTE_READ,&old)!=FALSE,"local code protection");check(FlushInstructionCache(GetCurrentProcess(),local,0x2000)!=FALSE,"local cache flush");
        wrappers[0]=reinterpret_cast<Wrapper>(local+0x200);wrappers[1]=reinterpret_cast<Wrapper>(local+0x100);wrappers[2]=reinterpret_cast<Wrapper>(local);wrappers[3]=reinterpret_cast<Wrapper>(local+0x300);
        unsigned nativeChecks=0,singleChecks=0,twoChecks=0;
        for(unsigned viewer:{12u,2u})for(unsigned flag=0;flag<2;++flag){
            world[0x3a]=static_cast<unsigned char>(viewer);wr(world,0x16a8,uint32_t(flag<<8));
            for(unsigned route=0;route<4;++route)for(unsigned id=1;id<=51;++id){
                unsigned expected=flag||(route==0?id!=viewer:id!=mains[viewer]);
                check(run(route,id)==expected,"native single-player rule mismatch");++nativeChecks;
            }
        }
        wr(world,0x16a8,uint32_t(0));HumanControl control{};
        control.main_district[12]=11;control.main_district[2]=2;
        for(unsigned viewer:{12u,2u}){
            world[0x3a]=static_cast<unsigned char>(viewer);control.force_mask=uint64_t(1)<<viewer;
            for(unsigned route=0;route<4;++route)for(unsigned id=1;id<=51;++id){
                check(policyRun(control,route,id)==run(route,id),"single-human compatibility mismatch");++singleChecks;
            }
            control.force_mask=(uint64_t(1)<<12)|(uint64_t(1)<<2);
            for(unsigned route=0;route<4;++route)for(unsigned id=1;id<=51;++id){
                const unsigned f=route==0?id:owner[id];const bool human=f==2||f==12;
                const unsigned expected=!(human&&(route==0||id==mains[f]));
                check(policyRun(control,route,id)==expected,"two-human protection/delegation mismatch");
                check(world[0x3a]==viewer,"viewer identity changed");++twoChecks;
            }
        }
        auto hold=[&](HumanControl c,AiRoute route,AiSubject obj,bool flag){check(decide_ai(c,route,obj,flag)==AiDecision::Hold,"unsafe context not held");++holds;};
        hold(control,AiRoute::Army,{2,2,false},false);hold(control,AiRoute::Force,{0,0,true},false);hold(control,AiRoute::Force,{52,0,true},false);
        hold(control,AiRoute::Army,{2,0,true},false);hold(control,AiRoute::Army,{2,52,true},false);hold(control,static_cast<AiRoute>(4),{2,2,true},false);
        hold(control,AiRoute::Force,{2,0,true},true);auto bad=control;bad.force_mask=0;hold(bad,AiRoute::Force,{2,0,true},false);
        bad=control;bad.force_mask|=1;hold(bad,AiRoute::Force,{2,0,true},false);bad=control;bad.force_mask|=uint64_t(1)<<63;hold(bad,AiRoute::Force,{2,0,true},false);
        bad=control;bad.main_district[12]=0;hold(bad,AiRoute::Force,{2,0,true},false);bad=control;bad.main_district[2]=52;hold(bad,AiRoute::Force,{12,0,true},false);
        bad=control;bad.main_district[2]=11;hold(bad,AiRoute::Force,{12,0,true},false);
        unsigned liveChecks=0;
        if(argc==2){
            FILE* input=nullptr;check(fopen_s(&input,argv[1],"r")==0&&input,"live case input");
            unsigned viewer,a,am,b,bm,flag;
            check(fscanf_s(input,"%u %u %u %u %u %u",&viewer,&a,&am,&b,&bm,&flag)==6,"live header");
            check(a>=1&&a<=51&&b>=1&&b<=51&&a!=b&&am>=1&&am<=51&&bm>=1&&bm<=51&&(viewer==a||viewer==b)&&flag<=1,"live header bounds");
            control={};control.force_mask=(uint64_t(1)<<a)|(uint64_t(1)<<b);control.main_district[a]=am;control.main_district[b]=bm;mains[a]=am;mains[b]=bm;
            world[0x3a]=static_cast<unsigned char>(viewer);wr(world,0x16a8,uint32_t(flag<<8));
            for(;;){
                unsigned route,f,d,expectedNative,expectedDecision;
                int fields=fscanf_s(input,"%u %u %u %u %u",&route,&f,&d,&expectedNative,&expectedDecision);
                if(fields==EOF)break;
                check(fields==5&&route<4&&f>=1&&f<=51&&d<=51&&(route==0||d>=1)&&expectedNative<=1&&expectedDecision<=2,"live row bounds");
                unsigned id=route==0?f:d;owner[d]=f;
                check(run(route,id)==expectedNative,"live Python/native wrapper mismatch");
                auto decision=decide_ai(control,static_cast<AiRoute>(route),{f,d,true},flag!=0);
                check(static_cast<unsigned>(decision)==expectedDecision,"live Python/C++ policy mismatch");
                check(world[0x3a]==viewer,"live fixture changed viewer");++liveChecks;
                check(liveChecks<=4096,"excessive live cases");
            }
            fclose(input);check(liveChecks>0,"empty live cases");
        }else check(argc==1,"invalid fixture arguments");
        checks=nativeChecks+singleChecks+twoChecks+holds+liveChecks;
        std::printf("{\"result\":\"PASS\",\"native_rule_checks\":%u,\"single_human_compatibility\":%u,\"two_human_routing\":%u,\"hold_controls\":%u,\"copied_live_subjects\":%u,\"total\":%u,\"native_blocks\":10,\"game_access\":false,\"game_ai_executed\":false,\"movement_simulated\":false}\n",nativeChecks,singleChecks,twoChecks,holds,liveChecks,checks);
        VirtualFree(local,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){std::fprintf(stderr,"FAILED: %s\n",e.what());if(local)VirtualFree(local,0,MEM_RELEASE);return 1;}
}
