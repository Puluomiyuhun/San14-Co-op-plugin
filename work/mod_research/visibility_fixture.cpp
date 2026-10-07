#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include "visibility_fixture_code.h"

using Visible=int(*)(const float*,const float*,float);
using Level=int(*)(int);
static void check(bool p,const char* s){if(!p)throw std::runtime_error(s);}
static void scene(Visible f,const char* name,float x,float y,float z,float w,float threshold,
                  float shift,float scale,int expected){
    alignas(16) float m[16]={},p[4]={x,y,z,w};
    m[0]=scale;m[5]=1;m[10]=1;m[15]=1;m[12]=shift;
    float oldm[16],oldp[4];std::memcpy(oldm,m,sizeof(m));std::memcpy(oldp,p,sizeof(p));
    int result=f(m,p,threshold);
    check(result==expected,"Native visibility mismatch");
    check(std::memcmp(oldm,m,sizeof(m))==0&&std::memcmp(oldp,p,sizeof(p))==0,"Native input modified");
    std::printf("{\"case\":\"%s\",\"visible\":%d,\"inputs_unchanged\":true,\"result\":\"PASS\"}\n",name,result);
}
int main(){
    unsigned char* p=nullptr;
    try{
        p=(unsigned char*)VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
        check(p!=nullptr,"Allocation failed");std::memcpy(p,fixtureCode,4096);
        // Code and data remain in this process. Toggle only the local copy of the bypass flag.
        *(unsigned*)(p+0x400)=0;
        DWORD old;check(VirtualProtect(p,4096,PAGE_EXECUTE_READWRITE,&old)!=0,"Protection failed");
        check(FlushInstructionCache(GetCurrentProcess(),p,4096)!=0,"Cache flush failed");
        Visible f=(Visible)p;
        scene(f,"center",0,0,.5f,1,1,0,1,1);
        scene(f,"right-outside",1.1f,0,.5f,1,1,0,1,0);
        scene(f,"left-outside",-1.1f,0,.5f,1,1,0,1,0);
        scene(f,"upper-outside",0,1.1f,.5f,1,1,0,1,0);
        scene(f,"lower-outside",0,-1.1f,.5f,1,1,0,1,0);
        scene(f,"near-plane",0,0,0,1,1,0,1,0);
        scene(f,"far-plane",0,0,1,1,1,0,1,0);
        scene(f,"horizontal-boundary",1,0,.5f,1,1,0,1,0);
        scene(f,"homogeneous-divide",1.5f,0,1,2,1,0,1,1);
        scene(f,"negative-depth",0,0,-.5f,1,1,0,1,0);
        scene(f,"same-world-point-before-pan",.25f,0,.5f,1,1,0,1,1);
        scene(f,"same-world-point-after-pan",.25f,0,.5f,1,1,2,1,0);
        scene(f,"same-world-point-before-scale",.3f,0,.5f,1,1,0,1,1);
        scene(f,"same-world-point-after-scale",.3f,0,.5f,1,1,0,4,0);
        scene(f,"expanded-margin",1.1f,0,.5f,1,1.2f,0,1,1);
        *(unsigned*)(p+0x400)=1;
        scene(f,"global-bypass",20,20,-5,1,1,0,1,1);
        Level level=(Level)(p+0x600);
        for(int i=0;i<=6;i++){
            int actual=level(i);check(actual==(i<=3),"Native level mismatch");
            std::printf("{\"case\":\"level-%d\",\"allowed\":%d,\"result\":\"PASS\"}\n",i,actual);
        }
        VirtualFree(p,0,MEM_RELEASE);return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"Visibility fixture failed: %s\n",e.what());
        if(p)VirtualFree(p,0,MEM_RELEASE);return 1;
    }
}
