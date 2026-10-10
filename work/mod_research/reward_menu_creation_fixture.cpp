#include "reward_menu_creation.h"
#include <cstdio>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
static void need(bool ok,const char*why){if(!ok)throw std::runtime_error(why);}
extern "C" void CreationUserTail(void*,uintptr_t,unsigned);
extern "C" void CreationConsume(void*,uintptr_t);
extern "C" void CreationConsumeReturn();
extern "C" unsigned CreationProbeActivation(uintptr_t,uintptr_t,unsigned);
struct World {
 unsigned char*image=nullptr,*heap=nullptr;uintptr_t b=0,next=0,root=0,world=0,user=0,district=0,force=0,menu=0,layout=0,stack=0,allocator=0,states[5]{};
 unsigned allocationCalls=0,initializeCalls=0,listCalls=0,pauseCalls=0,resumeCalls=0;std::wstring mode;
 template<class T>void put(uintptr_t p,T v){memcpy(reinterpret_cast<void*>(p),&v,sizeof v);}
 uintptr_t alloc(size_t n){auto p=next;next+=(n+15)&~size_t(15);need(next<uintptr_t(heap)+0x200000,"owned memory exhausted");return p;}
 World(){image=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x2400000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));heap=static_cast<unsigned char*>(VirtualAlloc(nullptr,0x200000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE));need(image&&heap,"owned allocation");b=uintptr_t(image);next=uintptr_t(heap);root=alloc(0x86000);world=alloc(0x2000);district=alloc(0x100);force=alloc(0x100);layout=alloc(0x400);for(auto&s:states)s=alloc(0x700);user=states[4];stack=alloc(64*8);allocator=alloc(16);auto av=alloc(0x100);put(allocator,av);
  put(b+0x1FCA1E0,root);put(root+0x85130,world);put<unsigned short>(world+0x34,203);put<unsigned char>(world+0x36,8);put<unsigned char>(world+0x37,11);put<unsigned char>(world+0x3A,12);put<unsigned>(world+0x16A8,0xFFFFFFFF);put<unsigned char>(district+0x10,12);
  auto m=b+0x19E7310;put(m,allocator);put(m+8,allocator);put(m+0x28,allocator);put<std::uint64_t>(m+0x10,5);put<std::uint64_t>(m+0x18,64);put(m+0x20,stack);put(m+0x48,user);for(unsigned i=0;i<5;++i)put(stack+i*8,states[i]);put(user,b+0x12CC4A8);put<unsigned>(user+0x470,2);put<std::uint64_t>(m+0x38,64);put(m+0x40,alloc(64*16));}
 ~World(){VirtualFree(image,0,MEM_RELEASE);VirtualFree(heap,0,MEM_RELEASE);}
};
static World*w=nullptr;
template<class T=uintptr_t>T at(uintptr_t p){return *reinterpret_cast<const T*>(p);}
static uintptr_t manager(){return w->b+0x19E7310;}
static uintptr_t force(uintptr_t world){need(world==w->world,"world getter input");return w->force;}
static uintptr_t district(uintptr_t force){need(force==w->force,"force getter input");return w->district;}
static int valid(uintptr_t p){return p==w->district;}
static uintptr_t allocate(uintptr_t allocator,unsigned size,unsigned alignment,void*){need(allocator==w->allocator&&size==0x490&&alignment==16,"real creator allocation args");++w->allocationCalls;w->menu=w->alloc(0x500);return w->menu;}
static uintptr_t reallocate(uintptr_t,uintptr_t,unsigned,void*){throw std::runtime_error("unexpected native container realloc");}
static void release(uintptr_t,uintptr_t){} // only owned-vector service, no game heap
static void listCreate(uintptr_t list){need(list==w->menu+0x480,"actual constructor list owner");++w->listCalls;}
static void listClear(uintptr_t list){need(list==w->menu+0x480,"actual constructor list clear");if(w->mode==L"wrong-world")w->put<unsigned char>(w->world+0x37,21);if(w->mode==L"wrong-menu")w->put(w->menu,w->b+0x1331070);}
static void callbackCopy(uintptr_t,uintptr_t){}
static int pause(uintptr_t object,uintptr_t,uintptr_t){need(object==w->user,"exact prior User paused");++w->pauseCalls;return 1;}
static int initialize(uintptr_t object,uintptr_t,uintptr_t){need(object==w->menu||w->mode==L"wrong-queue-menu","menu initialize identity");++w->initializeCalls;w->put(object+0x478,w->layout);return 1;}
static int resume(uintptr_t,uintptr_t,uintptr_t){++w->resumeCalls;return 1;}
static void active(uintptr_t,unsigned,uintptr_t,uintptr_t,uintptr_t){}
static void grow(uintptr_t vector,std::uint64_t capacity){need(capacity&&capacity<=64,"bounded native temporary vector");const auto old=at(vector),end=at(vector+8);need(end>=old&&end-old<=capacity*16,"vector extent");auto p=w->alloc(size_t(capacity)*16);if(old)memcpy(reinterpret_cast<void*>(p),reinterpret_cast<void*>(old),size_t(end-old));w->put(vector,p);w->put(vector+8,p+end-old);w->put(vector+16,p+capacity*16);}
static void jump(uintptr_t address,void*target){unsigned char code[14]={0xff,0x25,0,0,0,0};const auto p=uintptr_t(target);memcpy(code+6,&p,8);memcpy(reinterpret_cast<void*>(address),code,14);}
static void patch(uintptr_t address,uintptr_t relay,void*target,unsigned n=5){jump(relay,target);const auto d=std::int32_t(relay-address-5);memset(reinterpret_cast<void*>(address),0x90,n);w->put<unsigned char>(address,0xe8);w->put(address+1,d);}
static void protect(DWORD value){DWORD old=0;need(VirtualProtect(w->image,0x2400000,value,&old)!=0,"owned protection");if(value==PAGE_EXECUTE_READ)need(VirtualProtect(w->image+0x19E7000,0x1000,PAGE_READWRITE,&old)!=0,"native manager writable data page");FlushInstructionCache(GetCurrentProcess(),w->image,0x2400000);}
static void load(const wchar_t*path){std::ifstream f(path,std::ios::binary);std::vector<char>d((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());need(bool(f)||!d.empty(),"private bounded input");const unsigned ranges[][2]={{0x3FA094,0x3FA0B4},{0x3FC270,0x3FCAB4},{0x3E2CF0,0x3E2E59},{0x509EC0,0x509EE2},{0x509E10,0x509EBD},{0x6082E0,0x6083A5},{0x50A7BA,0x50B3B6}};size_t off=0;for(auto&r:ranges){const size_t n=r[1]-r[0];need(off+n<=d.size(),"bounded code length");memcpy(w->image+r[0],d.data()+off,n);off+=n;}need(off==d.size(),"bounded code trailing bytes");memcpy(w->image+0x12CDB40,"CStrategyRewardState",21);
  auto av=at(w->allocator);w->put(av+0x40,uintptr_t(&allocate));w->put(av+0x48,uintptr_t(&reallocate));w->put(av+0x58,uintptr_t(&release));
  w->put(w->b+0x12CC4A8+0x20,uintptr_t(&pause));w->put(w->b+0x1331078+8,uintptr_t(&initialize));w->put(w->b+0x1331078+0x18,uintptr_t(&resume));w->put(w->b+0x1331078+0x58,uintptr_t(&active));
  jump(w->b+0xF690,reinterpret_cast<void*>(&manager));jump(w->b+0x2F21E0,reinterpret_cast<void*>(&force));jump(w->b+0x20C110,reinterpret_cast<void*>(&district));jump(w->b+0x2F2BB0,reinterpret_cast<void*>(&valid));jump(w->b+0x811620,reinterpret_cast<void*>(&listCreate));jump(w->b+0x1FEAC0,reinterpret_cast<void*>(&listClear));jump(w->b+0x3C6300,reinterpret_cast<void*>(&callbackCopy));jump(w->b+0x50B7A0,reinterpret_cast<void*>(&grow));jump(w->b+0x50B3B6,reinterpret_cast<void*>(&CreationConsumeReturn));}
static DWORD WINAPI foreign(void*){RewardMenuCreationDispatch(w->user,21);return 0;}
static LONG CALLBACK exceptionTrace(EXCEPTION_POINTERS*p){if(p->ExceptionRecord->ExceptionCode==EXCEPTION_ACCESS_VIOLATION)fprintf(stderr,"owned AV rip=%llx rva=%llx address=%llx\n",p->ContextRecord->Rip,p->ContextRecord->Rip-w->b,p->ExceptionRecord->ExceptionInformation[1]);return EXCEPTION_CONTINUE_SEARCH;}
int wmain(int argc,wchar_t**argv){if(argc!=3)return 2;try{World world;w=&world;auto handler=AddVectoredExceptionHandler(1,exceptionTrace);need(handler!=nullptr,"owned exception trace");w->mode=argv[2];load(argv[1]);namespace cr=reward_menu_creation;
 cr::Config c{};c.base=w->b;c.root=w->root;c.world=w->world;c.user=w->user;c.district=w->district;c.generation=7;c.thread=GetCurrentThreadId();c.year=203;c.month=8;c.day=11;c.force=12;memcpy(c.states,w->states,sizeof c.states);for(unsigned i=0;i<4;++i)c.relays[i]=w->b+0x900000+i*32;
 if(w->mode==L"raw-source-tamper")w->image[0x3FC2C8]=0x90;protect(PAGE_EXECUTE_READ);const bool bound=cr::Bind(c);
 if(w->mode==L"raw-source-tamper"){need(!bound&&cr::Snapshot().error==cr::Error::Source,"raw source tamper refused");}
 else{need(bound,"creation binding");protect(PAGE_EXECUTE_READWRITE);patch(w->b+0x3FA09A,c.relays[0],reinterpret_cast<void*>(&RewardMenuCreationDispatch));patch(w->b+0x3FC3F3,c.relays[1],reinterpret_cast<void*>(&RewardMenuCreationCreate));patch(w->b+0x3E2D80,c.relays[2],reinterpret_cast<void*>(&RewardMenuCreationName));patch(w->b+0x50B35B,c.relays[3],reinterpret_cast<void*>(&RewardMenuCreationActivation),8);if(w->mode==L"source-tamper")w->image[0x3FC2C8]=0x90;protect(PAGE_EXECUTE_READ);
  if(w->mode==L"wrong-thread"){auto h=CreateThread(nullptr,0,foreign,nullptr,0,nullptr);need(h&&WaitForSingleObject(h,3000)==WAIT_OBJECT_0,"owned foreign thread");CloseHandle(h);}else if(w->mode==L"foreign-call")RewardMenuCreationDispatch(w->user,21);else CreationUserTail(w->image+0x3FA094,w->user,w->mode==L"wrong-command"?20:21);
  auto before=cr::Snapshot();fprintf(stderr,"created phase=%u error=%u dispatch=%u create=%u named=%u queued=%u alloc=%u\n",unsigned(before.phase),unsigned(before.error),before.dispatch,before.create,before.named,before.queued,w->allocationCalls);cr::Evidence evidence{};need(!cr::Take(7,evidence),"creation queue alone not activation");
  if(before.phase==cr::Phase::Queued&&w->mode!=L"queued-only"){
   // Real constructor leaves a null native UI helper; substitute it only for
   // this limited scheduler/activation execution, not as game UI evidence.
   w->put(w->menu+0x60,w->alloc(16));w->put(manager()+0x48,uintptr_t(0));
   if(w->mode==L"wrong-queue-menu"){auto other=w->alloc(0x500);memcpy(reinterpret_cast<void*>(other),reinterpret_cast<void*>(w->menu),0x500);w->put(at(manager()+0x40)+8,other);}
   CreationConsume(w->image+0x50A7BA,manager());auto after=cr::Snapshot();fprintf(stderr,"consumed phase=%u error=%u count=%llu active=%u\n",unsigned(after.phase),unsigned(after.error),at<std::uint64_t>(manager()+0x10),after.activated);
  }
  if(w->mode==L"normal"||w->mode==L"wrong-generation"||w->mode==L"bridge-registers"){
   need(cr::Snapshot().phase==cr::Phase::Activated,"actual scheduler stack activation");if(w->mode==L"wrong-generation")need(!cr::Take(8,evidence),"wrong generation refuses evidence");need(cr::Take(7,evidence)&&evidence.menu==w->menu&&evidence.layout==w->layout&&evidence.creation_observed&&evidence.activation_observed&&!evidence.production_permit,"exact same menu evidence");need(!cr::Take(7,evidence),"take once");need(w->allocationCalls==1&&w->initializeCalls==1&&w->pauseCalls==1&&w->resumeCalls==1&&at<unsigned>(w->world+0x16A8)==0xFFFFDFFF,"bounded native path and precreation flag side effect");
   if(w->mode==L"bridge-registers"){need(CreationProbeActivation(manager(),w->menu,0xAD7)==1,"shadow pressure preserves GPR/XMM and CF/ZF/OF set");need(CreationProbeActivation(manager(),w->menu,0x202)==1,"shadow pressure preserves GPR/XMM and arithmetic flags clear");need(cr::Snapshot().phase==cr::Phase::Fault&&!cr::Take(7,evidence),"direct bridge cannot create activation evidence");}
  }else if(w->mode==L"queued-only")need(cr::Snapshot().phase==cr::Phase::Queued&&!cr::Take(7,evidence),"no activation no evidence");else need(cr::Snapshot().phase==cr::Phase::Fault&&!cr::Take(7,evidence),"negative source refusal");
 }
 auto r=cr::Snapshot();printf("{\"passed\":true,\"case\":\"%ls\",\"phase\":%u,\"error\":%u,\"dispatch\":%u,\"create\":%u,\"named\":%u,\"queued\":%u,\"activated\":%u,\"taken\":%u,\"allocation_double_calls\":%u,\"ui_initialize_double_calls\":%u,\"game_access\":false,\"production_permit\":false,\"parent_scope_proven\":false}\n",argv[2],unsigned(r.phase),unsigned(r.error),r.dispatch,r.create,r.named,r.queued,r.activated,r.taken,w->allocationCalls,w->initializeCalls);return 0;
 }catch(const std::exception&e){fprintf(stderr,"creation fixture: %s\n",e.what());return 1;}}
