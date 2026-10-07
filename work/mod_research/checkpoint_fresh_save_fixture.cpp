#include "checkpoint_fresh_save.h"
#include "checkpoint_push_pilot.h"
#include <cstdio>
#include <cstring>
#include <string>
namespace fs=checkpoint_fresh_save;
extern "C" std::uint64_t FreshDispatch(unsigned,std::uintptr_t);
extern "C" void FreshDispatchReturn();
static std::uintptr_t b=0,root=0,world=0,user=0;
static fs::Driver driver;static fs::Config cfg;static std::string mode;
static unsigned binds=0,queues=0,passed=0,failed=0,originals=0;static bool intentSeen=false;
template<class T>static void put(std::uintptr_t p,T v){*reinterpret_cast<T*>(p)=v;}
template<class T>static T get(std::uintptr_t p){return *reinterpret_cast<T*>(p);}
static void check(bool v,const char*s){if(v)++passed;else{++failed;fprintf(stderr,"FAIL %s\n",s);}}
static void pathFor(const char*name,wchar_t(&out)[1024]){swprintf_s(out,L"%ls\\%hs",cfg.save_directory,name);}
static bool __fastcall exists(void*,const char*name){if(mode=="stop-before-binder")driver.Stop();if(mode=="storage-drift")put<unsigned char>(world+0x37,21);wchar_t path[1024]{};pathFor(name,path);return mode=="remote-exists"||GetFileAttributesW(path)!=INVALID_FILE_ATTRIBUTES;}
static std::int32_t __fastcall nativeSize(void*,const char*name){wchar_t path[1024]{};pathFor(name,path);WIN32_FILE_ATTRIBUTE_DATA d{};return GetFileAttributesExW(path,GetFileExInfoStandard,&d)&&!d.nFileSizeHigh?std::int32_t(d.nFileSizeLow):-1;}
static std::int32_t __fastcall nativeRead(void*,const char*name,void*out,std::int32_t size){
 if(mode=="stop-in-read")driver.Stop();
 wchar_t path[1024]{};pathFor(name,path);HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(f==INVALID_HANDLE_VALUE)return -1;DWORD n=0;bool ok=ReadFile(f,out,DWORD(size),&n,nullptr)!=0;CloseHandle(f);
 if(mode=="native-bytes-mismatch"&&n)reinterpret_cast<unsigned char*>(out)[0]^=1;
 if(mode=="native-short-read"&&n)--n;return ok?std::int32_t(n):-1;
}
static bool validate(void*){return mode!="native-validation-loss"||queues==0;}
static void* __cdecl context(void*){return mode=="remote-null"?nullptr:reinterpret_cast<void*>(b+0x272000);}
static void __fastcall binder(SaveRequest*q){
 ++binds;wchar_t intent[1024]{};swprintf_s(intent,L"%ls\\%hs.intent",cfg.intent_directory,q->filename.data);
 intentSeen=GetFileAttributesW(intent)!=INVALID_FILE_ATTRIBUTES;
 check(q->slot==-1&&q->filename.size==14&&q->filename.capacity==15&&q->caption.size==0,"native request ABI");
 if(mode=="binder-exception")RaiseException(0xE123FE01,0,0,nullptr);
 if(mode=="stop-in-binder")driver.Stop();
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
static std::uint64_t originalUser(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){
 ++originals;check(self==user,"User original args");
 if(mode=="original-exception")RaiseException(0xE123FE02,0,0,nullptr);
 if(mode=="date-drift")put<unsigned char>(world+0x37,21);
 return 0xFEDCBA9876543210ULL;
}
static std::uint64_t originalSave(std::uint64_t self,std::uint64_t,std::uint64_t,std::uint64_t){
 ++originals;auto phase=get<unsigned>(self+0x470);
 if(mode=="save-exception"&&phase==2)RaiseException(0xE123FE03,0,0,nullptr);
 if(phase<4){if(mode!="stall"||phase!=2)put<unsigned>(self+0x470,phase+1);}
 if(phase==2){
  if(mode=="stop-in-worker")driver.Stop();
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
 put<int>(b+0x280000+0x88,-1);put<std::uintptr_t>(b+0x202000+0x480,b+0x2B0000);put<unsigned>(b+0x19E7510+0x13C,1);
 put<std::uintptr_t>(b+0x2025318,b+0x290000);put<int>(b+0x290000+0x3EC,-1);put<std::uintptr_t>(b+0x290000+0x10,b+0x2C0000);put<std::uintptr_t>(b+0x2C0000,b+0x2C0000);put<std::uintptr_t>(b+0x2C0008,b+0x2C0000);
 put<std::uintptr_t>(root+0xDCA0+12*8,root+0x8D000);put<unsigned short>(root+0x8D010,666);
 put<int>(b+0x201ED10,-1);put<std::uint64_t>(b+0x201ED18+24,15);put<std::uint64_t>(b+0x201ED38+24,15);
 memcpy(reinterpret_cast<void*>(b+0x12AA8E0),"CSaveState",11);
 put<std::uintptr_t>(b+0x123CB28,std::uintptr_t(&context));put<std::uintptr_t>(b+0x18D08B8,b+0x2FCB90);put<std::uintptr_t>(b+0x272000,b+0x270000);put<std::uintptr_t>(b+0x270000,b+0x271000);put<std::uintptr_t>(b+0x271000+0x68,std::uintptr_t(&exists));
}
static fs::Request request(unsigned generation){fs::Request q{};q.generation=generation;q.room_epoch=7;q.period=generation;q.cut=9;q.room_id[0]=1;q.year=203;q.month=8;q.day=generation==1?11:21;q.force=12;q.ruler=666;sprintf_s(q.filename,"mp%08x.s14",generation);return q;}
static void run(){
 check(dispatch(0,user)==(mode=="original-exception"?0xE123FE02u:0),"User original return/exception");
 auto r=driver.Snapshot();if(r.status!=fs::Status::Queued)return;
 put<std::uint64_t>(b+0x19E7310+0x30,0);put<std::uint64_t>(b+0x19E7310+0x10,6);put<std::uintptr_t>(b+0x210000+40,b+0x240000);
 if(mode=="wrong-save")put<std::uintptr_t>(b+0x210000+40,b+0x241000);
 if(mode=="phase-skip")put<unsigned>(b+0x240000+0x470,2);
 for(unsigned i=0;i<7&&get<std::uint64_t>(b+0x19E7310+0x10)==6;++i){
  auto e=dispatch(1,b+0x240000);if(e){check(mode=="save-exception"&&e==0xE123FE03u,"Save exception propagates");break;}
  if(driver.Snapshot().error)break;
 }
 if(get<std::uint64_t>(b+0x19E7310+0x10)==5)check(dispatch(0,user)==0,"returned User normal");
}
int main(int argc,char**argv){
 if(argc!=3)return 2;mode=argv[1];setup();cfg.base=b;cfg.claim=CheckpointPersistentClaim;cfg.owner=CheckpointPersistentCurrentOwner;cfg.binder=std::uintptr_t(&binder);cfg.queue=std::uintptr_t(&queue);cfg.caller=std::uintptr_t(&FreshDispatchReturn);
 cfg.storage.storage=reinterpret_cast<void*>(b+0x270000);cfg.storage.exists=&exists;cfg.storage.size=&nativeSize;cfg.storage.read=&nativeRead;cfg.storage.validate=&validate;
 MultiByteToWideChar(CP_UTF8,0,argv[2],-1,cfg.save_directory,512);wcscpy_s(cfg.intent_directory,cfg.save_directory);
 check(driver.Initialize(cfg),"initialize production component with explicit fixture native substitutes");
 CheckpointPersistentBridgeConfig bridge{};bridge.before=fs::Driver::BeforeCallback;bridge.after=fs::Driver::AfterCallback;bridge.finally=fs::Driver::FinallyCallback;bridge.context=&driver;bridge.original=reinterpret_cast<void*>(&originalUser);check(CheckpointPersistentBridgeConfigure(0,&bridge)==1,"configure User bridge");bridge.original=reinterpret_cast<void*>(&originalSave);check(CheckpointPersistentBridgeConfigure(1,&bridge)==1,"configure Save bridge");
 auto q=request(1);auto zero=q;zero.period=0;check(!driver.Submit(zero),"period zero refused");check(driver.Submit(q),"submit first request");check(!driver.Submit(q),"duplicate pending request refused");
 if(mode=="cancel")driver.Stop();if(mode=="selection")put<std::uintptr_t>(user+0x4A8,root+100);
 if(mode=="unowned"){
  CheckpointLoadWorkerFrame fake{};std::uintptr_t caller=cfg.caller;fake.caller_entry_rsp=std::uintptr_t(&caller);fake.slot=0;fake.thread_id=GetCurrentThreadId();fake.call_id=91;fake.args[0]=user;driver.Before(fake);CheckpointLoadWorkerExit e{};driver.Finally(fake,e);
 }else run();
 auto r=driver.Snapshot();
 if(mode=="success"||mode=="stop-in-binder"||mode=="stop-in-worker"||mode=="stop-in-read"){
  check(r.status==fs::Status::Complete&&r.phase_mask==31&&r.completed_requests==1&&intentSeen,"first native lifecycle complete");
  if(mode=="success"){
   check(!driver.Submit(q),"old generation refused after completion");auto q2=request(2);auto duplicate=q2;strcpy_s(duplicate.filename,q.filename);check(!driver.Submit(duplicate),"old basename refused");
   put<unsigned char>(world+0x37,21);check(driver.Submit(q2),"second distinct date and request");run();r=driver.Snapshot();check(r.status==fs::Status::Complete&&r.completed_requests==2&&binds==2&&queues==2,"two fresh saves without bridge reset");check(!driver.Submit(request(3)),"bounded retention limit");
  }else check(!driver.Submit(request(2))&&r.stop_after_commit,"Stop after binder does not cancel native completion or allow next request");
 }else if(mode=="stall")check(r.status==fs::Status::Queued&&!r.worker_joined,"no guessed completion on timeout");
 else if(mode=="cancel"||mode=="stop-before-binder")check(r.status==fs::Status::Cancelled&&binds==0&&queues==0,"cancel before native mutation");
 else check(r.error&&r.status!=fs::Status::Complete,"reject incomplete lifecycle");
 check(r.active==0&&r.entries==r.exits,"FINALLY balances entered scopes");check(!r.full_world&&!r.room_ready,"no world/room authority");
 fs::Artifact artifact;bool copied=driver.CopyArtifact(1,artifact);
 if(mode=="success"||mode=="stop-in-binder"||mode=="stop-in-worker"||mode=="stop-in-read"){
  check(copied&&artifact.bytes.size()==32&&artifact.bytes[0]==11&&artifact.report.file_bytes_verified,"first immutable file bytes exported");
  if(mode=="success"){fs::Artifact second;check(driver.CopyArtifact(2,second)&&second.bytes[0]==21&&memcmp(artifact.sha256,second.sha256,32),"different files and hashes for different dates");}
  wchar_t path[1024]{};pathFor(q.filename,path);HANDLE overwrite=CreateFileW(path,GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);check(overwrite==INVALID_HANDLE_VALUE,"exported file retained against overwrite");if(overwrite!=INVALID_HANDLE_VALUE)CloseHandle(overwrite);
 }else check(!copied,"incomplete source cannot export");
 for(unsigned i=0;i<2;++i){CheckpointPersistentBridgeStats s{};check(CheckpointPersistentBridgeSnapshot(i,&s)&&!s.active&&!s.cleanup_faults&&s.started==s.finally_calls,"physical bridge cleanup");}
 printf("{\"case\":\"%s\",\"result\":\"%s\",\"checks\":%u,\"failures\":%u,\"status\":%u,\"error\":%u,\"binds\":%u,\"queues\":%u,\"completed\":%u,\"game_access\":false}\n",mode.c_str(),failed?"FAIL":"PASS",passed,failed,unsigned(r.status),r.error,binds,queues,r.completed_requests);
 return failed?1:0;
}
