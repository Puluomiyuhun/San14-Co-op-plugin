#include "a_save_user_owner.h"
#include "checkpoint_push_pilot.h"
#include "checkpoint_fresh_save_packet.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>
namespace fs=checkpoint_fresh_save;
namespace ss=a_save_user_owner;
namespace sb=checkpoint_live_storage_binding;
extern "C" std::uint64_t FreshDispatch(unsigned,std::uintptr_t);
extern "C" void FreshDispatchReturn();
static std::uintptr_t b=0,root=0,world=0,user=0;
static ss::Owner* session=new ss::Owner;static ss::Config cfg;static std::string mode;
static HANDLE nativeEntered=nullptr,nativeRelease=nullptr;
static fs::Report saveReport(){ss::Report r{};session->Snapshot(r);return r.save;}
extern "C" {std::uint64_t BindingFixtureGeneration=1;void BindingFixtureContextInit();}
alignas(16) static std::uintptr_t storageVtable[16]{},storageObject[2]{};
static unsigned nativeReads=0,contextChecks=0;
static std::uint64_t birth(){FILETIME a{},z{},y{},x{};GetProcessTimes(GetCurrentProcess(),&a,&z,&y,&x);return(std::uint64_t(a.dwHighDateTime)<<32)|a.dwLowDateTime;}
static void hex(const char*p,unsigned char*out){for(unsigned i=0;i<32;++i){unsigned v=0;sscanf_s(p+i*2,"%2x",&v);out[i]=static_cast<unsigned char>(v);}}
static sb::Endpoint endpoint(void*p){sb::Endpoint e{};e.address=std::uintptr_t(p);memcpy(e.first32,p,32);return e;}
static bool ownerCheck(void*,const sb::Attachment&a,sb::Point)noexcept {
 ++contextChecks;auto&e=cfg.storage.attachment;
 return a.pid==GetCurrentProcessId()&&a.birth==birth()&&a.base==b&&a.attempt==e.attempt&&a.generation==e.generation&&!memcmp(a.id,e.id,32);
}
static bool inputSample(void*,checkpoint_native_input_pending::Config&c)noexcept {
 c.binding=cfg.input_binding;c.profile_base=b;
 auto span=[](std::uintptr_t a,std::size_t n){return checkpoint_native_input_pending::Span{reinterpret_cast<const unsigned char*>(a),n};};
 c.user=span(user,0x668);c.toolbar=span(b+0x280000,0x8C);c.game=span(b+0x202000,0x488);c.panel=span(b+0x2B0000,0x1F8);
 c.manager=span(b+0x19E7310,0x50);c.stack=span(b+0x210000,0x30);c.queue=span(b+0x250000,64*16);c.load_cache=span(b+0x290000,0x3F4);
 for(unsigned i=0;i<5;++i)c.states[i]=b+0x200000+i*0x1000;
 if(mode=="hold-binding-drift")++c.binding.owner_generation;
 return true;
}
static unsigned binds=0,queues=0,passed=0,failed=0,originals=0;static bool intentSeen=false;
template<class T>static void put(std::uintptr_t p,T v){*reinterpret_cast<T*>(p)=v;}
template<class T>static T get(std::uintptr_t p){return *reinterpret_cast<T*>(p);}
static void check(bool v,const char*s){if(v)++passed;else{++failed;fprintf(stderr,"FAIL %s\n",s);}}
static void pathFor(const char*name,wchar_t(&out)[1024]){swprintf_s(out,L"%ls\\%hs",cfg.save_directory,name);}
static void packet(const fs::Artifact&a,const char*name){
 std::vector<unsigned char>bytes;check(checkpoint_fresh_save_packet::Encode(a,bytes)==checkpoint_fresh_save_packet::Error::None,"encode actual retained Owner artifact");
 if(bytes.empty())return;wchar_t path[1024]{};pathFor(name,path);
 HANDLE f=CreateFileW(path,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);check(f!=INVALID_HANDLE_VALUE,"create own-process transfer packet once");
 if(f==INVALID_HANDLE_VALUE)return;DWORD count=0;bool ok=WriteFile(f,bytes.data(),DWORD(bytes.size()),&count,nullptr)!=0;
 ok=FlushFileBuffers(f)&&ok;CloseHandle(f);check(ok&&count==bytes.size(),"all encoded artifact packet bytes written");
}
__declspec(noinline) static bool __fastcall exists(void*,const char*name){if(mode=="stop-before-binder")session->Stop();if(mode=="storage-drift")put<unsigned char>(world+0x37,21);wchar_t path[1024]{};pathFor(name,path);return mode=="remote-exists"||GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES;}
__declspec(noinline) static std::int32_t __fastcall nativeSize(void*,const char*name){wchar_t path[1024]{};pathFor(name,path);WIN32_FILE_ATTRIBUTE_DATA d{};return GetFileAttributesExW(path,GetFileExInfoStandard,&d)&&!d.nFileSizeHigh?std::int32_t(d.nFileSizeLow):-1;}
__declspec(noinline) static std::int32_t __fastcall nativeRead(void*,const char*name,void*out,std::int32_t size){
 ++nativeReads;
 if(mode=="stop-in-read")session->Stop();
 wchar_t path[1024]{};pathFor(name,path);HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(f==INVALID_HANDLE_VALUE)return -1;DWORD n=0;bool ok=ReadFile(f,out,DWORD(size),&n,nullptr)!=0;CloseHandle(f);
 if(mode=="native-bytes-mismatch"&&n)reinterpret_cast<unsigned char*>(out)[0]^=1;
 if(mode=="native-short-read"&&n)--n;return ok?std::int32_t(n):-1;
}
static void __fastcall binder(SaveRequest*q){
 ++binds;wchar_t intent[1024]{};swprintf_s(intent,L"%ls\\%hs.intent",cfg.intent_directory,q->filename.data);
 intentSeen=GetFileAttributesW(intent)!=INVALID_FILE_ATTRIBUTES;
 check(q->slot==-1&&q->filename.size==14&&q->filename.capacity==15&&q->caption.size==0,"native request ABI");
 if(mode=="binder-exception")RaiseException(0xE123FE01,0,0,nullptr);
 if(mode=="stop-in-binder")session->Stop();
 put<int>(b+0x201ED10,q->slot);memcpy(reinterpret_cast<void*>(b+0x201ED18),&q->filename,32);memcpy(reinterpret_cast<void*>(b+0x201ED38),&q->caption,32);
 q->filename.size=q->caption.size=0;q->filename.data[0]=q->caption.data[0]=0;
 if(mode=="wrong-binder")put<int>(b+0x201ED10,34);
}
static void __fastcall queue(void*m,const char*name,std::uintptr_t argument,void*carrier){
 ++queues;check(std::uintptr_t(m)==b+0x19E7310&&std::uintptr_t(name)==b+0x12AA8E0&&argument==0,"type0 queue arguments");
 bool empty=carrier!=nullptr;for(unsigned i=0;i<64&&empty;++i)empty&=reinterpret_cast<unsigned char*>(carrier)[i]==0;check(empty,"empty native callback");
 auto data=b+0x250000,s=b+0x240000;put<std::uint64_t>(b+0x19E7310+0x30,1);put<unsigned>(data,mode=="wrong-type"?2:0);put<std::uintptr_t>(data+8,s);
 put<std::uintptr_t>(s,b+0x12DC5F8);put<unsigned>(s+0x470,0);memcpy(reinterpret_cast<void*>(s+0x70),"CSaveState",11);
}
extern "C" std::uint64_t FixtureUserBody(std::uint64_t self,std::uint64_t a,std::uint64_t c,std::uint64_t d){
 ++originals;check(self==user&&a==0x1122&&c==0x3344&&d==0x5566,"User original four args");
 if(mode=="original-exception")RaiseException(0xE123FE02,0,0,nullptr);
 if(mode=="date-drift")put<unsigned char>(world+0x37,21);
 if(mode=="hold-in-native")check(!session->SetUserHold(true,99),"running original cannot be relabeled as suppressed");
 if(mode=="inflight-admission"){SetEvent(nativeEntered);if(WaitForSingleObject(nativeRelease,10000)!=WAIT_OBJECT_0)ExitProcess(9);}
 return 0xFEDCBA9876543210ULL;
}
extern "C" std::uint64_t FixtureSaveBody(std::uint64_t self,std::uint64_t a,std::uint64_t c,std::uint64_t d){
 check(a==0x1122&&c==0x3344&&d==0x5566,"Save original four args");
 ++originals;auto phase=get<unsigned>(self+0x470);
 if(mode=="save-exception"&&phase==2)RaiseException(0xE123FE03,0,0,nullptr);
 if(phase<4){if(mode!="stall"||phase!=2)put<unsigned>(self+0x470,phase+1);}
 if(phase==2){
  if(mode=="stop-in-worker")session->Stop();
  put<unsigned>(b+0x201EC2C,mode=="save-failure"?0:1);
  auto name=reinterpret_cast<SaveShortString*>(b+0x201ED18);wchar_t path[1024]{};swprintf_s(path,L"%ls\\%hs",cfg.save_directory,name->data);
  HANDLE f=CreateFileW(path,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
  if(f!=INVALID_HANDLE_VALUE){unsigned char payload[32]{};payload[0]=get<unsigned char>(world+0x37);memcpy(payload+1,name->data,15);DWORD n=0;WriteFile(f,payload,32,&n,nullptr);FlushFileBuffers(f);CloseHandle(f);}
 }
 if(phase==4){
  if(mode!="uncleared"){put<std::uint64_t>(b+0x201ED18+16,0);put<char>(b+0x201ED18,0);put<std::uint64_t>(b+0x201ED38+16,0);put<char>(b+0x201ED38,0);}
  auto manager=b+0x19E7310;put<std::uint64_t>(manager+0x10,5);put<std::uint64_t>(manager+0x30,0);
  if(mode=="return-drift")put<unsigned char>(world+0x37,21);
 }
 return 0x123456789ABCDEF0ULL;
}
static DWORD dispatch(unsigned slot,std::uintptr_t self){
 __try {auto result=FreshDispatch(slot,self);return result==(slot?0x123456789ABCDEF0ULL:0xFEDCBA9876543210ULL)?0:1;}
 __except(EXCEPTION_EXECUTE_HANDLER){return GetExceptionCode();}
}
extern "C" void FreshRawUser();
extern "C" void FreshRawSave();
extern "C" std::uint64_t FreshSuppressed(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
static void jump(std::uintptr_t target,void*fn){
 unsigned char op[14]={0xff,0x25,0,0,0,0};memcpy(op+6,&fn,8);memcpy(reinterpret_cast<void*>(target),op,14);
 DWORD old=0;check(VirtualProtect(reinterpret_cast<void*>(target&~std::uintptr_t(4095)),4096,PAGE_EXECUTE_READ,&old)!=0,"owned original RX");
 FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(target),14);
}
static void storageSetup(const char*exeSha){
 auto&c=cfg.storage;auto exe=std::uintptr_t(GetModuleHandleW(nullptr));
 c.attachment.pid=GetCurrentProcessId();c.attachment.birth=birth();c.attachment.base=b;c.attachment.attempt=77;c.attachment.generation=5;c.attachment.id[0]=9;
 hex("42d53bb42c033c6027b6da75e8077f4170f4d684abb0f57483a661225d052025",c.attachment.gameSha256);
 c.moduleCount=1;auto&m=c.modules[0];m.base=exe;GetModuleFileNameW(nullptr,m.path,1024);
 auto*pe=reinterpret_cast<IMAGE_NT_HEADERS64*>(exe+reinterpret_cast<IMAGE_DOS_HEADER*>(exe)->e_lfanew);
 m.sizeOfImage=pe->OptionalHeader.SizeOfImage;m.timestamp=pe->FileHeader.TimeDateStamp;
 WIN32_FILE_ATTRIBUTE_DATA data{};GetFileAttributesExW(m.path,GetFileExInfoStandard,&data);m.fileSize=(std::uint64_t(data.nFileSizeHigh)<<32)|data.nFileSizeLow;
 hex(exeSha,m.fileSha256);native_storage_read::Sha256(reinterpret_cast<void*>(exe),4096,m.headerSha256);
 c.contextInit=endpoint(reinterpret_cast<void*>(&BindingFixtureContextInit));c.exists=endpoint(reinterpret_cast<void*>(&exists));c.size=endpoint(reinterpret_cast<void*>(&nativeSize));c.read=endpoint(reinterpret_cast<void*>(&nativeRead));
 c.counter=std::uintptr_t(&BindingFixtureGeneration);c.cachedGeneration=1;c.vtable=std::uintptr_t(storageVtable);c.storage=std::uintptr_t(storageObject);c.checkOwner=ownerCheck;
 storageObject[0]=c.vtable;storageVtable[1]=c.read.address;storageVtable[13]=c.exists.address;storageVtable[15]=c.size.address;
 memcpy(c.contextCode,reinterpret_cast<void*>(c.contextInit.address),sizeof c.contextCode);
 put<std::uintptr_t>(b+0x123CB28,c.contextInit.address);auto token=reinterpret_cast<std::uintptr_t*>(b+0x18D08B8);token[0]=b+0x2FCB90;token[1]=1;token[2]=c.storage;
 constexpr char version[]="STEAMREMOTESTORAGE_INTERFACE_VERSION014";memcpy(reinterpret_cast<void*>(b+0x12AA6B8),version,sizeof version);
}
static void setup(){
 b=std::uintptr_t(VirtualAlloc(nullptr,0x2300000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));root=std::uintptr_t(VirtualAlloc(nullptr,0x100000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
 if(!b||!root)ExitProcess(9);world=root+0x86000;user=b+0x204000;
 put<std::uintptr_t>(b+0x1FCA1E0,root);put<std::uintptr_t>(root,b+0x12AA6B0);put<std::uintptr_t>(root+0x85130,world);put<std::uintptr_t>(world,b+0x12AA638);
 put<unsigned short>(world+0x34,203);put<unsigned char>(world+0x36,8);put<unsigned char>(world+0x37,11);put<unsigned char>(world+0x3A,12);put<unsigned>(world+0x40,1);
 auto m=b+0x19E7310,stack=b+0x210000;put<std::uint64_t>(m+0x10,5);put<std::uintptr_t>(m+0x20,stack);put<std::uint64_t>(m+0x38,64);put<std::uintptr_t>(m+0x40,b+0x250000);
 put<std::uintptr_t>(m,b+0x260000);put<std::uintptr_t>(m+0x28,b+0x260000);put<std::uintptr_t>(b+0x260000,b+0x1283498);
 const unsigned off[]={0x28,0x38,0x40,0x48},rv[]={0x12C840,0x12C290,0x8388D0,0x1479B0};for(unsigned i=0;i<4;++i)put<std::uintptr_t>(b+0x1283498+off[i],b+rv[i]);
 const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
 for(unsigned i=0;i<5;++i){auto s=b+0x200000+i*0x1000;put<std::uintptr_t>(stack+i*8,s);memcpy(reinterpret_cast<void*>(s+0x70),names[i],strlen(names[i])+1);}
 put<std::uintptr_t>(user,b+0x12CC4A8);put<unsigned>(user+0x470,2);put<std::uintptr_t>(user+0x478,b+0x280000);put<std::uintptr_t>(user+0x618,b+0x281000);
 put<std::uintptr_t>(b+0x202000,b+0x12CC9B8);put<std::uintptr_t>(m+0x48,user);
 put<int>(b+0x280000+0x88,-1);put<std::uintptr_t>(b+0x202000+0x480,b+0x2B0000);put<unsigned>(b+0x19E7510+0x13C,1);
 put<std::uintptr_t>(b+0x2025318,b+0x290000);put<int>(b+0x290000+0x3EC,-1);put<std::uintptr_t>(b+0x290000+0x10,b+0x2C0000);put<std::uintptr_t>(b+0x2C0000,b+0x2C0000);put<std::uintptr_t>(b+0x2C0008,b+0x2C0000);
 put<unsigned>(b+0x290000+8,1);
 put<std::uintptr_t>(root+0xDCA0+12*8,root+0x8D000);put<unsigned short>(root+0x8D010,666);
 put<int>(b+0x201ED10,-1);put<std::uint64_t>(b+0x201ED18+24,15);put<std::uint64_t>(b+0x201ED38+24,15);
 memcpy(reinterpret_cast<void*>(b+0x12AA8E0),"CSaveState",11);
 jump(b+0x3F9B00,reinterpret_cast<void*>(&FreshRawUser));jump(b+0x4AA650,reinterpret_cast<void*>(&FreshRawSave));
 put<std::uintptr_t>(b+0x12CC4A8+0x28,b+0x3F9B00);put<std::uintptr_t>(b+0x12DC5F8+0x28,b+0x4AA650);
 DWORD prot=0;check(VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READONLY,&prot)!=0,"User slot readonly");
 check(VirtualProtect(reinterpret_cast<void*>(b+0x12DC000),4096,PAGE_READONLY,&prot)!=0,"Save slot readonly");
}
static fs::Request request(unsigned generation){fs::Request q{};q.generation=generation;q.room_epoch=7;q.period=generation;q.cut=9;q.room_id[0]=1;q.year=203;q.month=8;q.day=generation==1?11:21;q.force=12;q.ruler=666;sprintf_s(q.filename,"mp%08x.s14",generation);return q;}
static void run(){
 check(dispatch(0,user)==(mode=="original-exception"?0xE123FE02u:0),"User original return/exception");
 auto r=saveReport();if(r.status!=fs::Status::Queued)return;
 put<std::uint64_t>(b+0x19E7310+0x30,0);put<std::uint64_t>(b+0x19E7310+0x10,6);put<std::uintptr_t>(b+0x210000+40,b+0x240000);
 if(mode=="wrong-save")put<std::uintptr_t>(b+0x210000+40,b+0x241000);
 if(mode=="phase-skip")put<unsigned>(b+0x240000+0x470,2);
 for(unsigned i=0;i<7&&get<std::uint64_t>(b+0x19E7310+0x10)==6;++i){
  auto e=dispatch(1,b+0x240000);if(e){check(mode=="save-exception"&&e==0xE123FE03u,"Save exception propagates");break;}
  if(saveReport().error)break;
 }
 if(get<std::uint64_t>(b+0x19E7310+0x10)==5)check(dispatch(0,user)==0,"returned User normal");
}
int main(int argc,char**argv){
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
 if(argc!=4)return 2;mode=argv[1];setup();cfg.base=b;cfg.binder=std::uintptr_t(&binder);cfg.queue=std::uintptr_t(&queue);cfg.caller=std::uintptr_t(&FreshDispatchReturn);cfg.room_epoch=7;cfg.room_id[0]=1;
 cfg.input_binding.attempt[0]=4;cfg.input_binding.attachment[0]=5;cfg.input_binding.owner_generation=77;cfg.sample_input=inputSample;
 MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);storageSetup(argv[3]);
 if(mode=="suppress-original-refused"){
  DWORD protection=0;VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,PAGE_READWRITE,&protection);
  put<std::uintptr_t>(b+0x12CC4A8+0x28,std::uintptr_t(&FreshSuppressed));VirtualProtect(reinterpret_cast<void*>(b+0x12CC000),4096,protection,&protection);
  check(!session->Initialize(cfg),"planning suppression wrapper rejected as raw original");ss::Report report{};session->Snapshot(report);
  check(report.error==ss::Error::RawSlot&&!report.initialized&&!report.armed&&!binds&&!queues,"no binding or publication on wrapper refusal");
  printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed);return failed?1:0;
 }
 check(session->Initialize(cfg),"real Owner factory with production Gate and owned-PE Context");
 check(!session->Submit(request(1)),"cannot submit before hooks armed");
 if(mode=="entry-replaced-before-arm"){
  DWORD protection=0;VirtualProtect(reinterpret_cast<void*>(b+0x3F9000),4096,PAGE_READWRITE,&protection);
  jump(b+0x3F9B00,reinterpret_cast<void*>(&FreshSuppressed));
  check(!session->Arm()&&!session->Submit(request(1)),"changed raw entry cannot become native return evidence");ss::Report report{};session->Snapshot(report);
  check(report.error==ss::Error::RawSlot&&!report.armed&&!report.hooks.entries[0].published&&!report.hooks.entries[1].published,"entry drift refuses before publication");
  printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed);return failed?1:0;
 }
 if(mode=="stop-before-arm"){
  session->Stop();check(!session->Arm()&&!session->Submit(request(1)),"Stop prevents Arm/Submit");ss::Report report{};session->Snapshot(report);
  check(!report.armed&&report.stopped&&!report.hooks.entries[0].published&&!report.hooks.entries[1].published,"Stop leaves originals untouched");
  printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed);return failed?1:0;
 }
 check(session->Arm(),"real two-slot CAS and protection publication");
 check(!session->Arm(),"same physical bridge bank cannot be armed again");
 if(failed){fprintf(stderr,"setup refused; not dispatching incomplete bridge\n");return 3;}
 if(mode=="inflight-admission"){
  nativeEntered=CreateEventW(nullptr,TRUE,FALSE,nullptr);nativeRelease=CreateEventW(nullptr,TRUE,FALSE,nullptr);check(nativeEntered&&nativeRelease,"owned native rendezvous events");
  std::uint64_t result=0;std::thread worker([&]{result=FreshDispatch(0,user);});
  check(WaitForSingleObject(nativeEntered,5000)==WAIT_OBJECT_0,"actual User native body is running on worker");
  const bool saveAllowed=session->Submit(request(1)),holdAllowed=session->SetUserHold(true,1);
  ss::Report active{};session->Snapshot(active);SetEvent(nativeRelease);worker.join();CloseHandle(nativeEntered);CloseHandle(nativeRelease);
  check(!saveAllowed&&!holdAllowed&&active.active_scopes==1&&!active.save_lane,"concurrent control cannot admit save or relabel running body held");
  check(result==0xFEDCBA9876543210ULL,"ordinary native return preserved after control contention");
  check(session->SetUserHold(true,2)&&FreshDispatch(0,user)==0,"subsequent actual invocation can be suppressed");
  ss::Report done{};session->Snapshot(done);check(done.user_subset_held&&!done.active_scopes&&!done.save.entries&&!binds&&!queues,"no false save boundary during shared-owner contention");
  printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed);return failed?1:0;
 }
 if(mode=="success"||mode=="held-no-save"||mode=="held-pending-menu"||mode=="hold-binding-drift"||mode=="held-foreign-caller"||mode=="stop-while-held"){
  check(session->SetUserHold(true,1),"request User subset hold on same physical owner");
  check(!session->Submit(request(1)),"save while User held is refused, never auto-released");
  check(!session->SetUserHold(false,1),"stale hold action cannot release");
  if(mode=="held-pending-menu")put<int>(b+0x280000+0x88,4);
  const bool invalid=mode=="held-pending-menu"||mode=="hold-binding-drift"||mode=="held-foreign-caller";
  auto entry=reinterpret_cast<CheckpointLoadWorkerEntry>(get<std::uintptr_t>(b+0x12CC4A8+0x28));
  auto heldResult=mode=="held-foreign-caller"?entry(user,0x1122,0x3344,0x5566):FreshDispatch(0,user);ss::Report held{};session->Snapshot(held);
  check(heldResult==(invalid?0xFEDCBA9876543210ULL:0),"subset suppression/unknown-state native-forward result");
  check(!held.save.entries&&!held.save.original_returned&&!binds&&!queues,"no fresh-save receipt from suppressed/ordinary return");
  check(held.bridges[0].native_returned==(invalid?1u:0u)&&held.bridges[0].after_calls==(invalid?1u:0u)&&!held.active_scopes,"physical bridge distinguishes real native and skipped call");
  check(held.user_subset_held!=invalid&&!held.all_input_held&&!held.room_ready,"only observed subset hold, never full Ready");
  if(mode=="stop-while-held"){
   session->Stop();check(!session->SetUserHold(false,2)&&!session->Submit(request(1)),"Stop revokes later control admission");
   check(FreshDispatch(0,user)==0xFEDCBA9876543210ULL,"Stop while held restores transparent raw forwarding");
   ss::Report stopped{};session->Snapshot(stopped);
   check(stopped.stopped&&!stopped.user_hold_requested&&!stopped.user_subset_held&&!stopped.active_scopes&&stopped.held_scopes==1,"stopped report agrees with released User subset");
   check(stopped.bridges[0].started==2&&stopped.bridges[0].native_returned==1&&stopped.bridges[0].after_calls==1&&stopped.bridges[0].finally_calls==2&&!stopped.save.entries&&!stopped.save.original_returned&&!binds&&!queues,"real forwarded AFTER does not become an unrequested fresh-save receipt");
  }
  if(mode!="success"){
   if(invalid){
    check(held.error==ss::Error::Input&&!session->SetUserHold(false,2)&&!session->Submit(request(1)),"uncertain input revokes later admission");
    check(FreshDispatch(0,user)==0xFEDCBA9876543210ULL,"sticky error cannot trap User in a hold that no longer admits release");
    ss::Report errored{};session->Snapshot(errored);check(errored.bridges[0].native_returned==2&&!errored.user_subset_held&&!errored.save.entries,"later raw returns after failure never forge hold/save success");
   }
   printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed);return failed?1:0;
  }
  check(session->SetUserHold(false,2),"explicit release preserves original slot owner");
 }
 auto wrongRoom=request(1);wrongRoom.room_id[3]=1;check(!session->Submit(wrongRoom),"immutable room binding rejects mismatch");
 auto q=request(1);auto zero=q;zero.period=0;check(!session->Submit(zero),"period zero refused");check(session->Submit(q),"submit first request");check(!session->Submit(q),"duplicate pending request refused");
 check(!session->SetUserHold(true,3),"pending save excludes new hold admission");
 if(mode=="cancel")session->Stop();if(mode=="selection")put<std::uintptr_t>(user+0x4A8,root+100);
 if(mode=="suppressed-no-return"){
  check(FreshSuppressed(user,0,0,0)==0x7777,"actual suppression wrapper returns locally");
  auto unstarted=saveReport();ss::Report report{};session->Snapshot(report);
  check(unstarted.status==fs::Status::Armed&&!unstarted.original_returned&&!unstarted.entries&&!report.bridges[0].started&&!binds&&!queues,"suppressed wrapper never supplies native User AFTER");
  session->Stop();
 }
 if(mode=="storage-generation-drift")++BindingFixtureGeneration;
 run();
 auto r=saveReport();
 if(mode=="success"||mode=="hold-in-native"||mode=="stop-in-binder"||mode=="stop-in-worker"||mode=="stop-in-read"){
  check(r.status==fs::Status::Complete&&r.phase_mask==31&&r.completed_requests==1&&intentSeen,"first native lifecycle complete");
  if(mode=="success"){
   check(!session->Submit(q),"old generation refused after completion");auto q2=request(2);auto duplicate=q2;strcpy_s(duplicate.filename,q.filename);check(!session->Submit(duplicate),"old basename refused");
   put<unsigned char>(world+0x37,21);check(session->Submit(q2),"second distinct date and request");run();r=saveReport();check(r.status==fs::Status::Complete&&r.completed_requests==2&&binds==2&&queues==2,"two fresh saves without bridge reset");check(!session->Submit(request(3)),"bounded retention limit");
  }else if(mode!="hold-in-native")check(!session->Submit(request(2))&&r.stop_after_commit,"Stop after binder does not cancel native completion or allow next request");
 }else if(mode=="stall")check(r.status==fs::Status::Queued&&!r.worker_joined,"no guessed completion on timeout");
 else if(mode=="cancel"||mode=="stop-before-binder"||mode=="suppressed-no-return")check(r.status==fs::Status::Cancelled&&binds==0&&queues==0,"cancel before native mutation");
 else check(r.error&&r.status!=fs::Status::Complete,"reject incomplete lifecycle");
 check(r.active==0&&r.entries==r.exits,"FINALLY balances entered scopes");check(!r.full_world&&!r.room_ready,"no world/room authority");
 fs::Artifact artifact;bool copied=session->CopyArtifact(1,artifact);
 if(mode=="success"||mode=="hold-in-native"||mode=="stop-in-binder"||mode=="stop-in-worker"||mode=="stop-in-read"){
  check(copied&&artifact.bytes.size()==32&&artifact.bytes[0]==11&&artifact.report.file_bytes_verified,"first immutable file bytes exported");
  if(mode=="success"){fs::Artifact second;check(session->CopyArtifact(2,second)&&second.bytes[0]==21&&memcmp(artifact.sha256,second.sha256,32),"different files and hashes for different dates");packet(artifact,"first.packet");packet(second,"second.packet");}
  wchar_t path[1024]{};pathFor(q.filename,path);HANDLE overwrite=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);check(overwrite==INVALID_HANDLE_VALUE,"exported file retained against overwrite");if(overwrite!=INVALID_HANDLE_VALUE)CloseHandle(overwrite);
 }else check(!copied,"incomplete source cannot export");
 for(unsigned i=0;i<2;++i){CheckpointLoadWorkerBridgeStats s{};check(ASaveUserOwnerBridgeSnapshot(i,&s)&&!s.active&&!s.cleanup_faults&&s.started==s.finally_calls,"physical bridge cleanup");}
 ss::Report full{};session->Snapshot(full);
 if(mode=="success"){
  auto previousEntries=full.save.entries;check(session->SetUserHold(true,3),"hold can follow two fresh exports without bridge reset");
  check(FreshDispatch(0,user)==0,"same published physical slot now truly suppresses User");session->Snapshot(full);
  check(full.save.entries==previousEntries&&full.user_subset_held&&!full.save_lane,"later suppression never alters completed raw save evidence");
 }
 check(!full.room_ready&&!full.full_world&&!full.all_input_held&&full.retained,"diagnostics never authorize input/Room Ready");
 check(full.storage.lastBinding.fixtureBuild&&full.storage.opened,"actual Gate and Context run, only owned-PE layout adapted");
 if(mode=="success")check(nativeReads==4&&contextChecks>4,"two native API reads per request through Gate");
 for(unsigned i=0;i<2;++i)check(full.hooks.entries[i].published&&!full.hooks.entries[i].dirty&&full.hooks.entries[i].lastProtection==PAGE_READONLY,"hooks retained and pages readonly");
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"status\":%u,\"error\":%u,\"binds\":%u,\"queues\":%u,\"completed\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,unsigned(r.status),r.error,binds,queues,r.completed_requests);
 return failed?1:0;
}
