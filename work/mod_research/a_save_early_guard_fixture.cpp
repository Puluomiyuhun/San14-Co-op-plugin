#include "a_save_early_guard.h"
#include <cstdio>
#include <cstring>
namespace eg=a_save_early_guard;
static unsigned checks=0,failures=0;
static void check(bool yes,const char*why){++checks;if(!yes){++failures;fprintf(stderr,"FAIL %s\n",why);}}
template<class T>void put(uintptr_t at,T value){*reinterpret_cast<T*>(at)=value;}
static void code(uintptr_t at,const void*bytes,size_t n){memcpy(reinterpret_cast<void*>(at),bytes,n);DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(at),n,PAGE_EXECUTE_READ,&old)!=0,"owned fingerprint RX");}
struct Mutation {const char*mode=nullptr;uintptr_t user=0;eg::Guard*guard=nullptr;};
static void mutate(void*p)noexcept{auto&m=*static_cast<Mutation*>(p);if(!strcmp(m.mode,"drift"))put<unsigned>(m.user+0x660,1);if(!strcmp(m.mode,"retire-during"))m.guard->Retire();}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);if(argc!=2)return 2;const auto mode=argv[1];
 const auto b=uintptr_t(VirtualAlloc(nullptr,0x2200000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));const auto root=uintptr_t(VirtualAlloc(nullptr,0x100000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));if(!b||!root)return 3;
 const auto world=root+0x86000,user=b+0x204000,stack=b+0x210000,head=b+0x2D0000;
 const unsigned char branch[]={0x39,0xae,0x60,0x06,0,0,0x74,0x0b,0xe8,0x0b,0x83,0xea,0xff,0x89,0xae,0x60,0x06,0,0};
 const unsigned char cursor[]={0x66,0x89,0xb9,0x5a,0x16,0,0},clear[]={0x48,0xc7,0x05,0xeb,0x94,0xd8,0x01,0,0,0,0};
 code(b+0x3F9BA8,branch,sizeof branch);code(b+0x835C2C,cursor,sizeof cursor);code(b+0x2403C2,clear,sizeof clear);
 put<uintptr_t>(b+0x1FCA1E0,root);put<uintptr_t>(root+0x85130,world);put<uintptr_t>(root,b+0x12AA6B0);put<uintptr_t>(world,b+0x12AA638);
 put<uintptr_t>(user,b+0x12CC4A8);put<unsigned>(user+0x470,2);put<std::uint64_t>(b+0x19E7310+0x10,5);put<uintptr_t>(b+0x19E7310+0x20,stack);put<uintptr_t>(stack+32,user);
 put<uintptr_t>(b+0x1FC98B0,head);for(unsigned i=0;i<3;++i)put<uintptr_t>(head+i*8,head);put<unsigned char>(head+0x19,1);
 eg::Guard guard;eg::Config c{};c.base=b;c.root=root;c.world=world;c.user=user;c.binding.attempt[0]=3;c.binding.attachment[0]=4;c.binding.owner_generation=5;
 Mutation change{mode,user,&guard};c.betweenSamples=mutate;c.context=&change;
 check(guard.Initialize(c),"read-only guard initialized using own fixed source anchors");check(!guard.Initialize(c),"same guard cannot be rebound");
 auto binding=c.binding;auto want=eg::Decision::QuietReportsObserved;DWORD old=0;
 if(!strcmp(mode,"flag")){put<unsigned>(user+0x660,1);want=eg::Decision::PendingUserReport;}
 if(!strcmp(mode,"queue")){put<std::uint64_t>(b+0x1FC98B8,1);want=eg::Decision::PendingReportQueue;}
 if(!strcmp(mode,"shape")){put<uintptr_t>(head+8,head+0x100);want=eg::Decision::QueueShape;}
 if(!strcmp(mode,"phase")){put<unsigned>(user+0x470,5);want=eg::Decision::Phase;}
 if(!strcmp(mode,"world")){put<uintptr_t>(root+0x85130,world+8);want=eg::Decision::Identity;}
 if(!strcmp(mode,"user")){put<uintptr_t>(stack+32,user+8);want=eg::Decision::Identity;}
 if(!strcmp(mode,"source")){VirtualProtect(reinterpret_cast<void*>(b+0x3F9BA8),19,PAGE_READWRITE,&old);put<unsigned char>(b+0x3F9BA8,0x90);VirtualProtect(reinterpret_cast<void*>(b+0x3F9BA8),19,PAGE_EXECUTE_READ,&old);want=eg::Decision::Source;}
 if(!strcmp(mode,"writable")){VirtualProtect(reinterpret_cast<void*>(b+0x835C2C),7,PAGE_EXECUTE_READWRITE,&old);want=eg::Decision::Source;}
 if(!strcmp(mode,"noaccess")){VirtualProtect(reinterpret_cast<void*>(user),4096,PAGE_NOACCESS,&old);want=eg::Decision::Unreadable;}
 if(!strcmp(mode,"binding")){++binding.owner_generation;want=eg::Decision::Binding;}
 if(!strcmp(mode,"retired")){guard.Retire();want=eg::Decision::Retired;}
 if(!strcmp(mode,"drift"))want=eg::Decision::Drift;
 if(!strcmp(mode,"retire-during"))want=eg::Decision::Retired;
 const auto result=guard.Observe(binding);check(result.decision==want,"precise admission refusal/observation reason");
 check(!result.fullWriteExclusion&&!result.saveAuthorized&&!result.roomReady,"quiet report observation NEVER becomes production permit");
 if(want==eg::Decision::QuietReportsObserved)check(result.sourceChecked&&result.twoSamplesEqual,"quiet is backed by two actual field samples and source checks");
 if(!strcmp(mode,"flag"))check(*reinterpret_cast<unsigned*>(user+0x660)==1,"guard does not flush or clear pending User report");
 if(!strcmp(mode,"queue"))check(*reinterpret_cast<std::uint64_t*>(b+0x1FC98B8)==1,"guard does not consume queued report");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"decision\":%u,\"user_flag\":%u,\"queued_reports\":%llu,\"game_access\":false}\n",mode,failures?"FAIL":"PASS",checks,failures,unsigned(result.decision),result.userFlag,result.queuedReports);
 return failures?1:0;
}
