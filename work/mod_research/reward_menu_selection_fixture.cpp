// Archived caller/creator/wait/result handler execution; NOT a UI or scheduler
// suspension test. Activation, event delivery, containers and task services are
// explicit owned doubles. No hook publisher, process access or gameplay permit.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <vector>
#include <string>
#include <stdexcept>
static void need(bool v,const char*s){if(!v){fprintf(stderr,"selection assertion: %s\n",s);fflush(stderr);throw std::runtime_error(s);}}
template<class T=uintptr_t>static T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
template<class T>static void put(uintptr_t p,T v){memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
struct World{
 unsigned char*image=nullptr,*heap=nullptr;uintptr_t b=0,next=0,manager=0,reward=0,layout=0,district=0,city=0,stack=0,selection=0,allocator=0,task=0,heads=0,counts=0,handles[2]{},callback=0;
 unsigned handleCalls=0,allocations=0,waits=0,events=0,clearCalls=0,appendCalls=0,refreshCalls=0,resetCalls=0,callbackCopies=0,wakeCalls=0;
 unsigned code=0x7FFFFFFD;bool taskless=false;uintptr_t initialSelection=0x5555;
 uintptr_t alloc(size_t n){const auto out=next;next+=(n+15)&~size_t(15);need(next<uintptr_t(heap)+0x20000,"owned allocation bounds");return out;}
 World(){image=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2400000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));heap=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x20000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(image&&heap,"owned allocation");b=uintptr_t(image);next=uintptr_t(heap);manager=b+0x19E7310;reward=alloc(0x700);layout=alloc(0x400);district=alloc(0x100);city=alloc(0x100);stack=alloc(64*8);allocator=alloc(16);task=alloc(0x100);heads=alloc(64*8);counts=alloc(64*8);
  put(manager,allocator);put(manager+0x28,allocator);put<uint64_t>(manager+0x10,6);put(manager+0x20,stack);put(manager+0x48,reward);put<uint64_t>(manager+0x38,64);put(manager+0x40,alloc(64*16));
  for(unsigned i=0;i<5;++i)put(stack+i*8,alloc(0x600));put(stack+40,reward);put(reward+0x470,district);put(reward+0x478,layout);put(reward+0x480,initialSelection);put<unsigned>(layout+0x170,1);put<unsigned>(reward+0x58,7);put(reward+0x50,task);
  auto mutex=alloc(0x40),join=alloc(0x40);put(task+0x10,mutex);put(task+8,join);put(join+0x20,uintptr_t(0x123456));
  for(unsigned i=0;i<2;++i){handles[i]=alloc(8);put<unsigned>(handles[i],i+1);put(counts+(i+1)*8,uint64_t(2));put(heads+(i+1)*8,alloc(24));}
  put(b+0x201D3A0,uintptr_t(1));put(b+0x201D3A8,uintptr_t(1));put(b+0x201D3B0,heads);put(b+0x201D3C8,counts);put<unsigned>(b+0x201D3E0,64);put(b+0x201D418,uintptr_t(1));put(b+0x201D420,uintptr_t(2));put(b+0x1923F90,uintptr_t(0x12345678abcd));
 }
 ~World(){if(heap)VirtualFree(heap,0,MEM_RELEASE);if(image)VirtualFree(image,0,MEM_RELEASE);}
};
static World*w=nullptr;
static uintptr_t managerGet(){return w->manager;}
static unsigned blocked(){return 0;}
static uintptr_t handle(uintptr_t,unsigned,unsigned){need(w->handleCalls<2,"two declared parameter lists");return w->handles[w->handleCalls++];}
static int candidates(uintptr_t district,uintptr_t){need(district==w->district,"original reward district");return 1;}
static uintptr_t cityGet(uintptr_t district){need(district==w->district,"same reward district");return w->city;}
static int money(uintptr_t city){need(city==w->city,"same funding city");return 300;}
static void normalize(uintptr_t,unsigned,unsigned){}
static void outputNormalize(uintptr_t,unsigned){}
static void parameterInit(uintptr_t p){memset(reinterpret_cast<void*>(p),0,0xA8);}
static void parameterCopy(uintptr_t dst,uintptr_t src){memcpy(reinterpret_cast<void*>(dst),reinterpret_cast<void*>(src),0xA8);}
static void parameterDestroy(uintptr_t){}
static void functorPrepare(uintptr_t dst,uintptr_t){memset(reinterpret_cast<void*>(dst),0,0x40);}
static void functorDestroy(uintptr_t,unsigned){}
static uintptr_t label(unsigned id){need(id==0x32E,"selection caption ID");return w->b+0x1000000;}
static uintptr_t allocate(uintptr_t a,unsigned size,unsigned alignment,void*){need(a==w->allocator&&size==0x870&&alignment==16,"actual selection creator allocation");++w->allocations;w->selection=w->alloc(0x870);return w->selection;}
static uintptr_t reallocate(uintptr_t,uintptr_t,uintptr_t,void*){throw std::runtime_error("unexpected queue reallocation");}
static void callbackCopy(uintptr_t dst,uintptr_t src){
 auto object=at(src+0x38);need(object&&at(object+8)==w->reward,"actual cloned callback retains original reward");
 reinterpret_cast<uintptr_t(*)(uintptr_t,uintptr_t)>(at(at(object)))(object,dst);put(dst+0x38,dst);w->callback=dst;++w->callbackCopies;
}
static void lockService(uintptr_t){}
static void counterService(uintptr_t,int,int){}
static void eventReset(uintptr_t){++w->resetCalls;}
static void eventWake(uintptr_t){++w->wakeCalls;}
static unsigned waitService(uintptr_t handle,int timeout){
 need(handle==0x123456&&timeout==-1,"original task wait service arguments");++w->waits;
 need(at(w->manager+0x30)==1,"actual creator enqueued exactly one state");auto q=at(w->manager+0x40);
 need(at<unsigned>(q)==0&&at(q+8)==w->selection,"actual type-zero queue owns created selection");
 need(at(w->selection)==w->b+0x12A6458&&!strcmp(reinterpret_cast<char*>(w->selection+0x70),"CDataSelectState<Data>"),"original constructor vtable and state name");
 need(at(w->selection+0x478+0x30)==w->reward+0x480,"original reward selection owner survives descriptor copies");
 need(w->callback==w->selection+0x10&&at(w->callback+8)==w->reward,"callback belongs to same creator and original reward");
 need(at(w->manager+0x10)==6&&at(w->stack+40)==w->reward&&at(w->manager+0x48)==w->reward,"original six-state/current reward before modeled activation");
 // This controlled synchronous stand-in does NOT execute the native scheduler
 // push/pop, UI interaction or suspend/resume. They remain unproved.
 put(w->stack+48,w->selection);put<uint64_t>(w->manager+0x10,7);put(w->manager+0x48,w->selection);put<uint64_t>(w->manager+0x30,0);
 auto event=w->alloc(24);put<unsigned>(event+8,w->code);auto eventPointer=event;
 reinterpret_cast<void(*)(uintptr_t,uintptr_t)>(at(at(w->callback)+0x10))(w->callback,uintptr_t(&eventPointer));++w->events;
 put<uint64_t>(w->manager+0x10,6);put(w->manager+0x48,w->reward);put<uintptr_t>(w->stack+48,0);
 return 0;
}
static void clearSelection(uintptr_t owner){need(owner==w->reward+0x480,"same original selection cleared");++w->clearCalls;put(owner,uintptr_t(0));}
static void appendSelection(uintptr_t owner,uintptr_t,uintptr_t begin,uintptr_t){need(owner==w->reward+0x480&&at(begin)==at(w->heads+16),"original return uses declared output range");++w->appendCalls;put(owner,uintptr_t(0x9999));}
static void refresh(uintptr_t layout,uintptr_t owner){need(layout==w->layout&&owner==w->reward+0x480,"same reward layout refreshed");++w->refreshCalls;}
static void refreshOther(uintptr_t layout){need(layout==w->layout,"same reward layout post-selection");++w->refreshCalls;}
static void listClear(uintptr_t,unsigned){}
static void listRelease(uintptr_t,uintptr_t){}
static void jump(uintptr_t where,void*fn){unsigned char b[14]={0xFF,0x25,0,0,0,0};auto target=uintptr_t(fn);memcpy(b+6,&target,8);memcpy(reinterpret_cast<void*>(where),b,14);}
static void load(const wchar_t*path){std::ifstream f(path,std::ios::binary);std::vector<char>raw((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
 const unsigned ranges[][2]={{0x68F760,0x68FBE3},{0x21ED10,0x21EDF8},{0x21EFB0,0x21F12D},{0x50B690,0x50B6FF},{0x22C450,0x22C4FF},{0x509450,0x509455},{0x509EC0,0x509EE2},{0x509E10,0x509EBD},{0x2D0350,0x2D036B},{0x4FABD0,0x4FABDC},{0x4F9D30,0x4F9D43},{0x509F50,0x509FD2},{0xEF9F20,0xEF9F41}};
 size_t off=0;for(auto&r:ranges){need(off+r[1]-r[0]<=raw.size(),"bounded archive length");memcpy(w->image+r[0],raw.data()+off,r[1]-r[0]);off+=r[1]-r[0];}need(off==raw.size(),"bounded archive exact extent");
 memcpy(w->image+0x12A64D0,"CDataSelectState<Data>",22);
 put(w->b+0x12A7010,w->b+0x2D0350);put(w->b+0x12A7020,w->b+0x4FABD0);put(w->b+0x12A7030,w->b+0x4F9D30);put(w->b+0x12CE760,uintptr_t(&functorDestroy));
 auto av=w->alloc(0x100);put(w->allocator,av);put(av+0x40,uintptr_t(&allocate));put(av+0x48,uintptr_t(&reallocate));auto cv=w->alloc(0x100);put(w->city,cv);put(cv+0x90,uintptr_t(&money));
 struct Stub{unsigned rva;void*fn;};const Stub stubs[]={
 {0xF690,reinterpret_cast<void*>(&managerGet)},{0x2F5F70,reinterpret_cast<void*>(&blocked)},{0x17040,reinterpret_cast<void*>(&handle)},
 {0x62E140,reinterpret_cast<void*>(&candidates)},{0x20AEA0,reinterpret_cast<void*>(&cityGet)},{0x601CC0,reinterpret_cast<void*>(&normalize)},
 {0x22C9F0,reinterpret_cast<void*>(&parameterInit)},{0x22DEB0,reinterpret_cast<void*>(&parameterCopy)},{0x22D610,reinterpret_cast<void*>(&parameterDestroy)},
 {0x21E7A0,reinterpret_cast<void*>(&functorPrepare)},{0x2D7160,reinterpret_cast<void*>(&label)},{0x3C6300,reinterpret_cast<void*>(&callbackCopy)},
 {0x50C710,reinterpret_cast<void*>(&counterService)},{0x834820,reinterpret_cast<void*>(&eventReset)},{0x834640,reinterpret_cast<void*>(&eventWake)},
 {0x1FEAC0,reinterpret_cast<void*>(&clearSelection)},{0x408B00,reinterpret_cast<void*>(&appendSelection)},{0x601C40,reinterpret_cast<void*>(&outputNormalize)},
 {0x69B660,reinterpret_cast<void*>(&refresh)},{0x6CB5F0,reinterpret_cast<void*>(&refreshOther)},{0x16C50,reinterpret_cast<void*>(&listClear)},{0x16D10,reinterpret_cast<void*>(&listRelease)}};
 for(const auto&s:stubs)jump(w->b+s.rva,s.fn);
 put(w->b+0x123C328,uintptr_t(&lockService));put(w->b+0x123C0D8,uintptr_t(&lockService));put(w->b+0x123C1E0,uintptr_t(&waitService));
 DWORD old=0;need(VirtualProtect(w->image,0x2400000,PAGE_EXECUTE_READWRITE,&old)!=0,"owned code protection");FlushInstructionCache(GetCurrentProcess(),w->image,0x2400000);
}
static LONG CALLBACK failure(EXCEPTION_POINTERS*p){if(p->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION)fprintf(stderr,"owned AV rva=%llx address=%llx\n",p->ContextRecord->Rip-w->b,p->ExceptionRecord->ExceptionInformation[1]);return EXCEPTION_CONTINUE_SEARCH;}
int wmain(int argc,wchar_t**argv){if(argc!=3)return 2;try{
 World world;w=&world;auto veh=AddVectoredExceptionHandler(1,failure);need(veh!=nullptr,"owned diagnostic handler");load(argv[1]);std::wstring mode=argv[2];
 if(mode==L"cancel-result")w->code=0x7FFFFFFE;else if(mode==L"unknown-result")w->code=0x1234;else if(mode==L"taskless"){w->taskless=true;put<uintptr_t>(w->reward+0x50,0);put<unsigned>(w->reward+0x58,0);}else need(mode==L"accept-result","known case");
 reinterpret_cast<void(*)(uintptr_t)>(w->b+0x68F760)(w->reward);
 const bool selected=mode==L"accept-result"||mode==L"unknown-result";
 need(w->allocations==1&&w->callbackCopies==1,"real selection creator and callback association executed");
 need(w->waits==(w->taskless?0u:1u)&&w->events==w->waits&&w->resetCalls==w->waits&&w->wakeCalls==w->waits,"actual wait path and explicit event-delivery service counts");
 need(w->clearCalls==(selected?1u:0u)&&w->appendCalls==(selected?1u:0u)&&at(w->reward+0x480)==(selected?uintptr_t(0x9999):w->initialSelection),"original zero/nonzero return branch effect");
 need(w->refreshCalls==2&&at<unsigned>(w->layout+0x170)==0&&at(w->manager+0x10)==6&&at(w->stack+40)==w->reward&&at(w->manager+0x48)==w->reward,"original caller refresh/reset preserves exact reward identity");
 const auto value=at<unsigned>(w->reward+0x58);need(value==(mode==L"accept-result"?1u:mode==L"unknown-result"?7u:0u),"actual 509F50 event mapping or unchanged stale result");
 need(at(w->manager+0x30)==(w->taskless?1u:0u),"taskless return leaves created selection only queued");
 printf("{\"passed\":true,\"case\":\"%ls\",\"result_value\":%u,\"allocations\":%u,\"wait_services\":%u,\"result_callbacks\":%u,\"selection_clears\":%u,\"selection_appends\":%u,\"refresh_calls\":%u,\"queue_remaining\":%llu,\"full_archived_caller_creator_wait\":true,\"original_callback_result_handler\":%s,\"activation_double\":%s,\"ui_and_container_services_double\":true,\"task_services_double\":true,\"native_suspend_proven\":false,\"native_activation_proven\":false,\"cancel_key_mapping_proven\":false,\"game_access\":false,\"production_permit\":false}\n",mode.c_str(),value,w->allocations,w->waits,w->events,w->clearCalls,w->appendCalls,w->refreshCalls,at<unsigned long long>(w->manager+0x30),w->events?"true":"false",w->waits?"true":"false");
 RemoveVectoredExceptionHandler(veh);return 0;
 }catch(const std::exception&e){fprintf(stderr,"selection fixture: %s\n",e.what());return 1;}}
