#include "a_save_abort_owner.h"
// Owned memory model for debugger transactions; no game code executes.
#include "a_save_runtime_exports.h"
#include <cstdio>
#include <cstring>
#include <string>
namespace w=a_save_runtime_wire;using A=std::uint64_t;
#ifdef OWN_STAGE
extern "C" {alignas(8) a_save_abort::Receipt ASaveAbortReceipt{};}
struct Data{A counts[14];w::HostCache cache;};
static Data data{};
extern "C" __declspec(dllexport) Data* GetData(){return &data;}
extern "C" __declspec(dllexport) void Hook(){}
BOOL WINAPI DllMain(HINSTANCE,DWORD,LPVOID){return TRUE;}
#else
#pragma section(".owned",read,write)
__declspec(allocate(".owned")) volatile unsigned char padding[0x1400000]{};
struct Data{A counts[14];w::HostCache cache;};
void need(bool v){if(!v){printf("ERROR %lu\n",GetLastError());fflush(stdout);ExitProcess(91);}}
template<class T>void put(const wchar_t*path,const T&v){FILE*f=nullptr;need(_wfopen_s(&f,path,L"wb")==0);need(fwrite(&v,sizeof v,1,f)==1);need(fclose(f)==0);}
void write(A at,const void*bytes,size_t n,DWORD prot){DWORD old=0;need(VirtualProtect(reinterpret_cast<void*>(at),n,PAGE_READWRITE,&old)!=0);memcpy(reinterpret_cast<void*>(at),bytes,n);need(VirtualProtect(reinterpret_cast<void*>(at),n,prot,&old)!=0);}
int wmain(int argc,wchar_t**argv){need(argc==2);padding[0]=1;auto dll=LoadLibraryW(argv[1]);need(dll!=nullptr);auto data=reinterpret_cast<Data*(*)()>(GetProcAddress(dll,"GetData"))();auto hook=A(GetProcAddress(dll,"Hook"));auto receipt=reinterpret_cast<a_save_abort::Receipt*>(GetProcAddress(dll,"ASaveAbortReceipt"));need(receipt!=nullptr);
 w::Plans p{};w::Snapshot s{};p.header={w::Magic,w::Version,sizeof p,unsigned(w::Op::Plans),0};s.header={w::Magic,w::Version,sizeof s,unsigned(w::Op::Snapshot),0};p.nonce[0]=s.nonce[0]=42;p.pid=GetCurrentProcessId();FILETIME a{},b{},c{},d{};need(GetProcessTimes(GetCurrentProcess(),&a,&b,&c,&d)!=0);p.birth=(A(a.dwHighDateTime)<<32)|a.dwLowDateTime;p.base=A(GetModuleHandleW(nullptr));p.module=A(dll);s.prepared=s.ownerArmed=1;s.hostCacheAddress=A(&data->cache);
 A relay=0;for(A n=0x1000000;n<0x40000000&&!relay;n+=0x10000)relay=A(VirtualAlloc(reinterpret_cast<void*>(p.base+n),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(relay!=0);
 const unsigned char jump[]={0xff,0x25,0,0,0,0};for(unsigned i=0;i<3;++i){const A to=relay+i*32;memcpy(reinterpret_cast<void*>(to),jump,6);memcpy(reinterpret_cast<void*>(to+6),&hook,8);}DWORD old=0;need(VirtualProtect(reinterpret_cast<void*>(relay),4096,PAGE_EXECUTE_READ,&old)!=0);
 const A sites[]={0x3F8606,0x3F9B16,0x13DC09},slots[]={0x12CC4D0,0x12DC620,0x12CC9E0,0x1297D10},originals[]={0x3F9B00,0x4AA650,0x3F8140,0x1AC3C0};const unsigned char raw[3][5]={{0xe8,0x15,0x22,0,0},{0xe8,5,0x5f,0xd6,0xff},{0xe8,0xd2,0xc3,0x3c,0}};
 for(unsigned i=0;i<3;++i){auto&v=p.inlines[i];v.address=p.base+sites[i];v.relay=i==2?relay+64:relay;v.size=5;v.protection=PAGE_EXECUTE_READ;memcpy(v.before,raw[i],5);v.after[0]=0xe8;auto rel=std::int32_t(relay+i*32-v.address-5);memcpy(v.after+1,&rel,4);write(v.address,v.before,5,v.protection);}
 // Parent relay needs its own allocation identity, as production Prepare does.
 auto parent=A(VirtualAlloc(reinterpret_cast<void*>(relay+0x10000),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(parent!=0);memcpy(reinterpret_cast<void*>(parent),jump,6);memcpy(reinterpret_cast<void*>(parent+6),&hook,8);need(VirtualProtect(reinterpret_cast<void*>(parent),4096,PAGE_EXECUTE_READ,&old)!=0);p.inlines[2].relay=parent;auto rel=std::int32_t(parent-p.inlines[2].address-5);memcpy(p.inlines[2].after+1,&rel,4);
 for(unsigned i=0;i<4;++i){auto&v=p.slots[i];v={p.base+slots[i],p.base+originals[i],hook,PAGE_READONLY};auto value=i<2?hook:v.original;write(v.address,&value,8,v.protection);}
 for(unsigned i=0;i<7;++i){p.counters[i]={A(&data->counts[2*i]),A(&data->counts[2*i+1]),0,0};s.counters[i]=p.counters[i];}put(L"plans.bin",p);put(L"snapshot.bin",s);printf("{\"pid\":%u,\"birth\":%llu,\"base\":%llu,\"module\":%llu}\n",p.pid,p.birth,p.base,p.module);fflush(stdout);
 char command[64]{};while(fgets(command,sizeof command,stdin)){std::string op(command);if(op=="exit\n")break;if(op.rfind("abort-",0)==0){
 s.stopped=s.ownerStopped=s.mailboxStopped=s.hostInitialized=s.restoreReady=1;s.hostThread=GetCurrentThreadId();s.ownerError=11;s.saveStatus=7;s.saveError=54;s.saveGeneration=1;s.binds=s.queues=s.workerJoined=1;s.phaseMask=31;s.originalReturned=12;
 if(op=="abort-complete\n"||op=="abort-repeat-pending\n"||op=="abort-ready-encoding\n"){s.saveStatus=5;s.saveError=s.ownerError=0;s.fileVerified=1;}
 if(op=="abort-cancelled\n"){s.saveStatus=8;s.saveError=s.ownerError=0;s.binds=s.queues=s.phaseMask=s.workerJoined=s.originalReturned=0;}
 if(op=="abort-repeat-pending\n")s.restoreReady=0;if(op=="abort-ready-encoding\n")s.restoreReady=2;data->cache={2,1,op=="abort-lease\n"?1u:0u,0,5};*receipt={};receipt->sequence=2;receipt->base=p.base;receipt->owner=A(data);receipt->generation=op=="abort-generation\n"?2:1;receipt->thread=s.hostThread;receipt->ownerError=11;receipt->driverError=54;receipt->retired=op=="abort-missing\n"?0:1;put(L"snapshot.bin",s);puts("OK");fflush(stdout);continue;}
if(op=="stop\n"||op=="lease\n"){s.stopped=s.ownerStopped=s.mailboxStopped=1;s.hostInitialized=1;data->cache={2,1,op=="lease\n"?1u:0u,0,0};put(L"snapshot.bin",s);}else if(op=="active\n")data->counts[1]=1;else if(op=="inactive\n")data->counts[1]=0;else if(op=="check-installed\n"||op=="check-restored\n"||op=="check-original\n"){bool installed=op=="check-installed\n";for(auto&v:p.inlines)need(!memcmp(reinterpret_cast<void*>(v.address),installed?v.after:v.before,5));if(op=="check-restored\n")for(auto&v:p.slots)need(*reinterpret_cast<A*>(v.address)==v.original);else for(unsigned i=0;i<4;++i)need(*reinterpret_cast<A*>(p.slots[i].address)==(i<2?hook:p.slots[i].original));}else need(false);puts("OK");fflush(stdout);}return 0;}
#endif
