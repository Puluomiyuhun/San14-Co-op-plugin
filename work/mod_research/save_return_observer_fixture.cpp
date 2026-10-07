#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <stdexcept>
#include "save_return_observer_profile.h"
static void need(bool b,const char* m){if(!b)throw std::runtime_error(m);}
template<class T>static void put(unsigned char* p,size_t at,T v){memcpy(p+at,&v,sizeof v);}
static void imm(std::vector<unsigned char>& v,uint64_t x){for(unsigned i=0;i<8;i++)v.push_back((unsigned char)(x>>(i*8)));}
static void rel(std::vector<unsigned char>& v,uint64_t at,uint64_t target){v.push_back(0xE9);int32_t d=int32_t(target-(at+v.size()+4));for(unsigned i=0;i<4;i++)v.push_back((unsigned char)(uint32_t(d)>>(i*8)));}
using Fn=uint64_t(*)(void*,uint64_t,uint64_t,uint64_t);
struct Work {unsigned char* image;void* user;bool special;volatile LONG* calls;};
static DWORD WINAPI run(void* arg){
 auto w=static_cast<Work*>(arg);
 for(unsigned i=0;i<4;i++){
  uint64_t a2=w->special&&i==1?1:0x2233445500000000ULL+i,a3=0x8877665544332211ULL+i,a4=0xFEDCBA9876543210ULL+i;
  auto fn=reinterpret_cast<Fn>(w->image+0x10000+i*0x100);auto result=fn(w->user,a2,a3,a4);
  uint64_t expected=uint64_t(w->user)^a2^a3^a4^(0xC0DEC0DE12345670ULL+i);
  if(!(w->special&&i==1)&&result!=expected)return 99;
  InterlockedIncrement(w->calls);
 }
 return 0;
}
int wmain(int argc,wchar_t** argv){
 try{
  need(argc==4,"ready go case");std::wstring test=argv[3];
  auto image=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2240000,MEM_COMMIT|MEM_RESERVE,PAGE_EXECUTE_READWRITE));need(image!=nullptr,"allocate");uint64_t b=uint64_t(image);
  put(image,0,uint16_t(0x5A4D));
  for(unsigned i=0;i<4;i++){
   auto p=sroPoints[i];put(image,0x12CC4A8+p.slot,b+p.entry);std::vector<unsigned char> code;
   if(i==1&&(test==L"reentry"||test==L"nested")){
    // if edx==0, branch to ordinary body. Otherwise make one nested native call.
    code={0x83,0xFA,0x00,0x74,0x19,0x48,0x83,0xEC,0x28,0x31,0xD2,0x48,0xB8};
    imm(code,b+(test==L"reentry"?p.entry:sroPoints[0].entry));
    code.insert(code.end(),{0xFF,0xD0,0x48,0x83,0xC4,0x28});rel(code,b+p.entry,b+p.ret);
    // Fix conditional jump to exact start of ordinary body.
    code[4]=(unsigned char)(code.size()-5);
   }
   if(i==1&&test==L"stall"){
    code={0x48,0x83,0xEC,0x28,0xB9,0xD0,0x07,0,0,0x48,0xB8};imm(code,uint64_t(&Sleep));code.insert(code.end(),{0xFF,0xD0,0x48,0x83,0xC4,0x28});
   }
   code.insert(code.end(),{0x49,0xBA});imm(code,0xC0DEC0DE12345670ULL+i);
   code.insert(code.end(),{0x48,0x89,0xC8,0x48,0x31,0xD0,0x4C,0x31,0xC0,0x4C,0x31,0xC8,0x4C,0x31,0xD0});
   rel(code,b+p.entry,b+p.ret);need(code.size()<p.ret-p.entry,"code size");memcpy(image+p.entry,code.data(),code.size());image[p.ret]=0xC3;
   std::vector<unsigned char> caller={0x48,0x83,0xEC,0x28,0x48,0xB8};imm(caller,b+p.entry);caller.insert(caller.end(),{0xFF,0xD0,0x48,0x83,0xC4,0x28,0xC3});memcpy(image+0x10000+i*0x100,caller.data(),caller.size());
  }
  FlushInstructionCache(GetCurrentProcess(),image,0x2240000);
  std::vector<unsigned char> root(0x85200),world(0x3000),cache(0x500),toolbar(0x300),panel(0x300),special(32);
  std::vector<std::vector<unsigned char>> states(5,std::vector<unsigned char>(0x800));std::vector<uint64_t> stack;
  const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
  for(unsigned i=0;i<5;i++){strcpy_s(reinterpret_cast<char*>(states[i].data()+0x70),64,names[i]);stack.push_back(uint64_t(states[i].data()));}
  put(states[4].data(),0,b+0x12CC4A8);put(states[4].data(),0x470,uint32_t(2));put(states[4].data(),0x478,uint64_t(toolbar.data()));put(states[2].data(),0x480,uint64_t(panel.data()));put(toolbar.data(),0x88,int32_t(-1));
  put(image,0x19E7310+0x10,uint64_t(5));put(image,0x19E7310+0x18,uint64_t(5));put(image,0x19E7310+0x20,uint64_t(stack.data()));
  put(image,0x1FCA1E0,uint64_t(root.data()));put(root.data(),0x85130,uint64_t(world.data()));put(world.data(),0,b+0x12AA638);put(world.data(),0x34,uint16_t(203));world[0x36]=8;world[0x37]=11;world[0x3A]=12;put(world.data(),0x20a8,uint32_t(1));
  put(image,0x2025318,uint64_t(cache.data()));put(cache.data(),0x3ec,int32_t(-1));put(image,0x201EC70,uint64_t(special.data()));put(image,0x19E7510+0x13c,uint32_t(1));
  put(image,0x201ED10,int32_t(-1));put(image,0x201ED18+24,uint64_t(15));put(image,0x201ED38+24,uint64_t(15));
  FILE* f=nullptr;need(!_wfopen_s(&f,argv[1],L"w"),"ready");std::fprintf(f,"{\"pid\":%lu,\"base\":%llu}\n",GetCurrentProcessId(),b);std::fclose(f);
  uint64_t deadline=GetTickCount64()+30000;while(GetFileAttributesW(argv[2])==INVALID_FILE_ATTRIBUTES&&GetTickCount64()<deadline)Sleep(10);need(GetFileAttributesW(argv[2])!=INVALID_FILE_ATTRIBUTES,"go timeout");
  volatile LONG calls=0;bool isSpecial=test==L"reentry"||test==L"nested"||test==L"stall";Work w{image,states[4].data(),isSpecial,&calls};
  if(test==L"threads"){
   HANDLE a=CreateThread(nullptr,0,run,&w,0,nullptr),c=CreateThread(nullptr,0,run,&w,0,nullptr);need(a&&c,"threads");need(WaitForSingleObject(a,15000)==WAIT_OBJECT_0&&WaitForSingleObject(c,15000)==WAIT_OBJECT_0,"join");DWORD x,y;GetExitCodeThread(a,&x);GetExitCodeThread(c,&y);need(x==0&&y==0,"register return preserved threads");CloseHandle(a);CloseHandle(c);
  }else if(test!=L"timeout"&&test!=L"cancel")need(run(&w)==0,"register return preserved");
  std::wstring done=std::wstring(argv[2])+L".done";need(!_wfopen_s(&f,done.c_str(),L"w"),"done");std::fprintf(f,"%ld",calls);std::fclose(f);
  BOOL debugger=TRUE;deadline=GetTickCount64()+15000;while(GetTickCount64()<deadline){CheckRemoteDebuggerPresent(GetCurrentProcess(),&debugger);if(!debugger)break;Sleep(10);}need(!debugger,"observer did not detach");
  // Ordinary calls after detach prove no residual debug breakpoints stop/crash execution.
  if(!isSpecial)need(run(&w)==0,"post-detach return preserved");
  std::printf("{\"result\":\"PASS\",\"calls\":%ld,\"debugger_attached\":false,\"rax_and_four_arguments_preserved\":true,\"post_detach_calls\":%s,\"game_access\":false}\n",calls,!isSpecial?"true":"false");return 0;
 }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
