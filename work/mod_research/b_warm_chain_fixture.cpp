#include "b_warm_chain_handover.h"
#include <cstdio>
#include <cstring>
using Fn=DWORD(WINAPI*)(void*);
struct Input {void**slots[6];void*originals[6];unsigned mode,fault,seed;};
static unsigned checks=0;
static void need(bool ok,const char*why){++checks;if(!ok){printf("FAIL %s\n",why);ExitProcess(2);}}
static void original(){}
static void set(HMODULE m,const Input&in){auto f=reinterpret_cast<Fn>(GetProcAddress(m,"FixtureSet"));need(f&&!f(const_cast<Input*>(&in)),"owned report setup");}
int wmain(int argc,wchar_t**argv){
 if(argc!=4)return 2;HMODULE banks[3]{};for(unsigned i=0;i<3;++i){banks[i]=LoadLibraryW(argv[i+1]);need(banks[i]!=nullptr,"distinct loaded fixture DLL");}
 auto slots=static_cast<void**>(VirtualAlloc(nullptr,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(slots!=nullptr,"owned slots");
 Input data{};for(unsigned i=0;i<6;++i){slots[i]=reinterpret_cast<void*>(&original);data.slots[i]=slots+i;data.originals[i]=slots[i];}
 for(auto b:banks)set(b,data);unsigned char nonce[32]{};nonce[0]=0x7e;b_warm_chain::Chain chain;b_warm_chain::Certificate a{},b{},again{};
 need(chain.Bind(banks[0],data.slots,data.originals,nonce),"first chain bind");need(!chain.Bind(banks[0],data.slots,data.originals,nonce),"bind cannot reset");
 need(!chain.AuthorizeNext(banks[1],2,a),"early second refused");need(!chain.AuthorizeNext(banks[2],3,a),"skip generation refused");
 data.mode=1;set(banks[0],data);need(chain.CompletedCurrent(1),"actual predecessor predicates see first complete");
 data.mode=2;set(banks[1],data);need(!chain.AuthorizeNext(banks[1],2,a),"stopped next refused");data.mode=0;set(banks[1],data);
 need(!chain.AuthorizeNext(banks[0],2,a),"same bank reuse refused");
 need(chain.AuthorizeNext(banks[1],2,a),"first edge authorized");need(a.generation==2&&a.previous==uintptr_t(banks[0])&&a.next==uintptr_t(banks[1])&&a.attempt==77&&a.fileSha256[0]==17&&a.nonce[0]==0x7e,"first certificate exact lineage");
 need(!chain.AuthorizeNext(banks[1],2,b),"first edge replay refused");need(!chain.AuthorizeNext(banks[2],3,b),"third requires second complete");
 data.mode=1;data.seed=1;for(unsigned fault=1;fault<=4;++fault){data.fault=fault;set(banks[1],data);need(!chain.AuthorizeNext(banks[2],3,b),"active dirty protection or receipt mismatch refuses third");}
 data.fault=0;set(banks[1],data);slots[0]=nullptr;need(!chain.AuthorizeNext(banks[2],3,b),"third requires original slots");slots[0]=data.originals[0];
 need(!chain.AuthorizeNext(banks[0],3,b),"first module cannot return as third");
 need(chain.AuthorizeNext(banks[2],3,b),"independent second edge authorized third");
 need(b.generation==3&&b.previous==uintptr_t(banks[1])&&b.next==uintptr_t(banks[2])&&b.pid==a.pid&&b.birth==a.birth&&!memcmp(b.nonce,a.nonce,32),"third certificate bound same process and chain");
 need(b.attempt==78&&b.fileSha256[0]==18&&b.userCall==9&&b.identityCall==10&&b.loadCall==11,"third certificate uses second bank receipt, never first");
 need(chain.ReadCertificate(2,again)&&!memcmp(&a,&again,sizeof a),"first certificate immutable after third");need(!chain.ReadCertificate(4,again),"unissued certificate unavailable");
 need(!chain.CompletedCurrent(3),"third not falsely completed by authorization");set(banks[2],data);need(chain.CompletedCurrent(3),"third completion actual predecessor checks");
 need(!chain.AuthorizeNext(banks[0],4,again),"fourth exceeds explicit bound");need(!chain.CompletedCurrent(2),"retired generation not current");
 printf("{\"passed\":true,\"checks\":%u,\"banks\":3,\"edges\":2,\"report_double\":true,\"native_load_executed\":false}\n",checks);return 0;
}
