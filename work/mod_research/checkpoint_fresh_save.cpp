#include "checkpoint_fresh_save.h"
#include "checkpoint_push_pilot.h"
#include "checkpoint_push_profile.h"
#include <mutex>
#include <cstring>
#include <cwchar>
#include <bcrypt.h>
#pragma comment(lib,"bcrypt.lib")
namespace checkpoint_fresh_save {
namespace {
template<class T>T at(std::uintptr_t p){return *reinterpret_cast<T*>(p);}
const SaveShortString& stringAt(std::uintptr_t p){return *reinterpret_cast<const SaveShortString*>(p);}
bool text(const SaveShortString&s,const char* want){
 auto n=strlen(want);auto len=s.size,cap=s.capacity;
 if(len!=n||len>cap||cap>32768||(cap<16&&cap!=15))return false;
 const char*data=cap<16?s.data:reinterpret_cast<const char*>(at<std::uintptr_t>(std::uintptr_t(&s)));
 if(std::uintptr_t(data)<0x10000||std::uintptr_t(data)>0x7FFFFFFFFFFFULL-n)return false;
 return !memcmp(data,want,n+1)&&s.size==len&&s.capacity==cap;
}
bool filename(const char*s){
 if(s[0]!='m'||s[1]!='p'||memcmp(s+10,".s14\0",5)||s[15])return false;
 for(unsigned i=2;i<10;++i)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return false;
 return true;
}
bool directory(const wchar_t*p){
 if(!p[0]||p[511]||wcsstr(p,L"..")||wcsstr(p,L"/"))return false;
 wchar_t full[512]{};DWORD n=GetFullPathNameW(p,512,full,nullptr);
 if(!n||n>=512||wcscmp(p,full)||p[wcslen(p)-1]==L'\\')return false;
 DWORD a=GetFileAttributesW(p);
 return a!=INVALID_FILE_ATTRIBUTES&&(a&FILE_ATTRIBUTE_DIRECTORY)&&!(a&FILE_ATTRIBUTE_REPARSE_POINT);
}
bool absent(const wchar_t*p){return GetFileAttributesW(p)==INVALID_FILE_ATTRIBUTES&&GetLastError()==ERROR_FILE_NOT_FOUND;}
bool imageMatches(std::uintptr_t base){
#ifndef CHECKPOINT_FRESH_SAVE_FIXTURE
 if(base!=std::uintptr_t(GetModuleHandleW(nullptr)))return false;
 wchar_t path[32768]{};if(!GetModuleFileNameW(nullptr,path,32768))return false;
 HANDLE f=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);
 if(f==INVALID_HANDLE_VALUE)return false;
 BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;unsigned char block[65536],out[32];DWORD n=0;
 bool ok=BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0;
 if(ok)ok=BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0)>=0;
 while(ok){if(!ReadFile(f,block,sizeof block,&n,nullptr)){ok=false;break;}if(!n)break;ok=BCryptHashData(hash,block,n,0)>=0;}
 if(ok)ok=BCryptFinishHash(hash,out,32,0)>=0&&!memcmp(out,SAVE_EXE_SHA,32);
 if(hash)BCryptDestroyHash(hash);if(alg)BCryptCloseAlgorithmProvider(alg,0);CloseHandle(f);
 if(!ok)return false;
 for(const auto&a:SAVE_FINGERPRINTS)if(memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size))return false;
#else
 if(!base)return false;
#endif
 return true;
}
struct Scope {Driver*driver=nullptr;std::uint64_t call=0;unsigned slot=0,phase=0;bool claim=false,related=false,terminal=false;};
thread_local Scope local;
}
struct Driver::Impl {
 std::mutex mu;Config cfg{};Request request{},history[2]{};Report r{};
 bool initialized=false;volatile LONG stopped=0;unsigned count=0;
 std::uintptr_t root=0,world=0,states[5]{},cache=0;unsigned rng=0,cacheMode=0;
 wchar_t target[1024]{},intent[1024]{};SaveBinder binder=nullptr;SaveQueue queue=nullptr;
 std::uintptr_t caller=0;
 std::uintptr_t nativeStorage=0;native_storage_read::Lease files[2];
 native_storage_read::Evidence fileEvidence[2];Report completed[2]{};
 const CheckpointLoadWorkerFrame*readFrame=nullptr;
 bool fail(unsigned code){if(!r.error)r.error=code;r.status=r.binds||r.queues?Status::Uncertain:Status::Rejected;return false;}
 bool idleStrings(){return at<int>(cfg.base+0x201ED10)==-1&&text(stringAt(cfg.base+0x201ED18),"")&&text(stringAt(cfg.base+0x201ED38),"");}
 bool bound(){return at<int>(cfg.base+0x201ED10)==-1&&text(stringAt(cfg.base+0x201ED18),request.filename)&&text(stringAt(cfg.base+0x201ED38),"");}
 bool cacheReady(bool cleared=false){
  auto c=at<std::uintptr_t>(cfg.base+0x2025318);
  if(c!=cache||at<unsigned>(c+8)!=cacheMode||cacheMode>1||at<int>(c+0x3EC)!=-1||at<unsigned>(c+0x3F0)||at<std::uint64_t>(c+0x18))return false;
  auto h=at<std::uintptr_t>(c+0x10);if(!h||at<std::uintptr_t>(h)!=h||at<std::uintptr_t>(h+8)!=h)return false;
  unsigned entries=0;auto first=at<std::uintptr_t>(c+0x20);
  for(unsigned i=0;i<120;++i){auto value=at<std::uintptr_t>(c+0x20+i*8);if(value){++entries;if(cleared||i>=50||value!=first+i*0x1E0)return false;}}
  return entries==0||(entries==50&&cacheMode==1&&first>=0x10000&&first<0x7FFFFFFFFFFFULL-50*0x1E0);
 }
 bool planning(std::uintptr_t user,bool pin){
  const auto b=cfg.base,m=b+0x19E7310;auto s=at<std::uintptr_t>(m+0x20);
  if(!s||at<std::uint64_t>(m+0x10)!=5||at<std::uint64_t>(m+0x30))return fail(10);
  const char*names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"};
  for(unsigned i=0;i<5;++i){auto v=at<std::uintptr_t>(s+i*8);if(v<0x10000||memcmp(reinterpret_cast<void*>(v+0x70),names[i],strlen(names[i])+1))return fail(11);if(pin)states[i]=v;else if(v!=states[i])return fail(12);}
  if(user!=states[4]||at<std::uintptr_t>(user)!=b+0x12CC4A8||at<unsigned>(user+0x470)!=2||!at<std::uintptr_t>(user+0x618))return fail(13);
  auto toolbar=at<std::uintptr_t>(user+0x478),panel=at<std::uintptr_t>(states[2]+0x480);
  if(!toolbar||!panel||at<int>(toolbar+0x88)!=-1||at<unsigned>(states[2]+0x47C)||at<unsigned>(panel+0x1B0))return fail(14);
  for(auto off:{0x4A8,0x4B0,0x4B8})if(at<std::uintptr_t>(user+off))return fail(15);
  auto special=at<std::uintptr_t>(b+0x201EC70);
  if((special&&at<unsigned>(special))||at<unsigned>(b+0x1A38EC8+0x28)||at<unsigned>(b+0x19E7510+0x13C)!=1)return fail(16);
  auto cap=at<std::uint64_t>(m+0x38),data=at<std::uintptr_t>(m+0x40);
  if(cap>4096||((cap==0)!=(data==0))||(data&&(data<0x10000||data>0x7FFFFFFFFFFFULL-cap*16)))return fail(17);
  for(auto off:{0,0x28}){auto a=at<std::uintptr_t>(m+off);if(a<0x10000||at<std::uintptr_t>(a)!=b+0x1283498)return fail(18);}
  const unsigned offsets[]={0x28,0x38,0x40,0x48},rv[]={0x12C840,0x12C290,0x8388D0,0x1479B0};
  for(unsigned i=0;i<4;++i)if(at<std::uintptr_t>(b+0x1283498+offsets[i])!=b+rv[i])return fail(18);
  auto rt=at<std::uintptr_t>(b+0x1FCA1E0);auto w=at<std::uintptr_t>(rt+0x85130);
  if(at<std::uintptr_t>(rt)!=b+0x12AA6B0||at<std::uintptr_t>(w)!=b+0x12AA638)return fail(19);
  if(pin){root=rt;world=w;rng=at<unsigned>(b+0x18EB8B0);cache=at<std::uintptr_t>(b+0x2025318);cacheMode=at<unsigned>(cache+8);}
  if(rt!=root||w!=world||at<unsigned>(b+0x18EB8B0)!=rng)return fail(20);
  if(at<std::uint16_t>(w+0x34)!=request.year||at<std::uint8_t>(w+0x36)!=request.month||at<std::uint8_t>(w+0x37)!=request.day||at<std::uint8_t>(w+0x3A)!=request.force||at<unsigned>(w+0x40)!=1||(at<unsigned>(w+0x16A8)&0x100))return fail(21);
  auto force=at<std::uintptr_t>(rt+0xDCA0+request.force*8);
  if(!force||at<std::uint16_t>(force+0x10)!=request.ruler||!idleStrings()||!cacheReady())return fail(22);
  return true;
 }
 bool vacant(){
  if(!absent(target))return fail(30);
  if(!cfg.storage.validate(cfg.storage.validationContext))return fail(31);
  const auto b=cfg.base;
  if(at<std::uintptr_t>(b+0x18D08B8)!=b+0x2FCB90)return fail(31);
  auto init=reinterpret_cast<void*(__cdecl*)(void*)>(at<std::uintptr_t>(b+0x123CB28));if(!init)return fail(31);
  auto result=std::uintptr_t(init(reinterpret_cast<void*>(b+0x18D08B8)));if(!result)return fail(31);
  auto object=at<std::uintptr_t>(result);if(!object)return fail(31);auto table=at<std::uintptr_t>(object);if(!table)return fail(31);
  if(reinterpret_cast<void*>(object)!=cfg.storage.storage)return fail(31);nativeStorage=object;
  auto fn=reinterpret_cast<bool(__fastcall*)(void*,const char*)>(at<std::uintptr_t>(table+0x68));
  if(!fn||fn(reinterpret_cast<void*>(object),request.filename))return fail(32);
  return true;
 }
 bool reserve(){
  struct Intent {std::uint64_t magic=0x53414E1446525331ULL;unsigned size=sizeof(Intent),pid=GetCurrentProcessId();FILETIME birth{};Request request{};} value{};
  FILETIME a{},b{},c{};if(!GetProcessTimes(GetCurrentProcess(),&value.birth,&a,&b,&c))return fail(33);value.request=request;
  HANDLE f=CreateFileW(intent,GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
  if(f==INVALID_HANDLE_VALUE)return fail(34);r.intents=1;DWORD written=0;
  bool ok=WriteFile(f,&value,sizeof value,&written,nullptr)!=0;ok=FlushFileBuffers(f)&&ok;CloseHandle(f);
  if(!ok||written!=sizeof value)return fail(35);r.flushed=1;return true;
 }
 void enqueue(std::uintptr_t user){
  if(InterlockedCompareExchange(&stopped,0,0)){r.status=Status::Cancelled;return;}
  if(!planning(user,false)||!vacant()||!planning(user,false)||!reserve()||!planning(user,false)||!vacant()||!planning(user,false))return;
  if(InterlockedCompareExchange(&stopped,0,0)){r.status=Status::Cancelled;return;}
  // The binder below is the irreversible boundary; Stop never retries/rewinds it.
  SaveRequest input{};input.slot=-1;input.filename.capacity=input.caption.capacity=15;
  input.filename.size=strlen(request.filename);memcpy(input.filename.data,request.filename,input.filename.size+1);
  ++r.binds;binder(&input);
  if(!text(input.filename,"")||!text(input.caption,"")||!bound()){fail(36);return;}
  auto m=cfg.base+0x19E7310;if(at<std::uint64_t>(m+0x30)){fail(37);return;}
  alignas(16) unsigned char carrier[64]{};++r.queues;
  queue(reinterpret_cast<void*>(m),reinterpret_cast<const char*>(cfg.base+0x12AA8E0),0,carrier);
  if(at<std::uint64_t>(m+0x30)!=1){fail(38);return;}
  auto data=at<std::uintptr_t>(m+0x40),s=at<std::uintptr_t>(data+8);
  if(at<unsigned>(data)!=0||!s||at<std::uintptr_t>(s)!=cfg.base+0x12DC5F8||at<unsigned>(s+0x470)||memcmp(reinterpret_cast<void*>(s+0x70),"CSaveState",11)){fail(39);return;}
  r.save_state=s;r.status=Status::Queued;r.stop_after_commit=InterlockedCompareExchange(&stopped,0,0)?1:0;
 }
 bool source(const CheckpointLoadWorkerFrame&f){
  CheckpointLoadWorkerOwner o{};
  return cfg.owner(&o)&&o.call_id==f.call_id&&o.thread_id==GetCurrentThreadId()&&o.slot==f.slot&&o.current_depth==1&&o.owner_depth==1&&o.token==request.generation;
 }
 static bool validateRead(void* context){
  auto*p=static_cast<Impl*>(context);
  return p->readFrame&&p->r.status==Status::Finalized&&p->source(*p->readFrame)&&p->planning(p->readFrame->args[0],false)&&
   reinterpret_cast<void*>(p->nativeStorage)==p->cfg.storage.storage&&p->cfg.storage.validate(p->cfg.storage.validationContext);
 }
 bool copyFresh(const CheckpointLoadWorkerFrame&f){
  // Pin the first local observation while the immutable storage core obtains
  // its own retained lease and compares two native reads of this exact name.
  native_storage_read::Lease first;first.file=CreateFileW(target,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
  if(first.file==INVALID_HANDLE_VALUE)return fail(50);
  BY_HANDLE_FILE_INFORMATION info{};
  if(!GetFileInformationByHandle(first.file,&info)||(info.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))||info.nFileSizeHigh||!info.nFileSizeLow||info.nFileSizeLow>16*1024*1024)return fail(51);
  first.bytes.resize(info.nFileSizeLow);DWORD n=0;
  if(!ReadFile(first.file,first.bytes.data(),info.nFileSizeLow,&n,nullptr)||n!=info.nFileSizeLow)return fail(52);
  native_storage_read::Input input{};input.localPath=target;input.basename=request.filename;input.expectedSize=n;
  if(!native_storage_read::Sha256(first.bytes.data(),first.bytes.size(),input.expectedSha256))return fail(53);
  auto api=cfg.storage;api.validate=&Impl::validateRead;api.validationContext=this;readFrame=&f;
  const bool matched=native_storage_read::Verify(input,api,files[count-1],fileEvidence[count-1]);readFrame=nullptr;
  if(!matched)return fail(54);r.file_bytes_verified=true;return true;
 }
};
Driver::Driver():p_(new Impl){} Driver::~Driver(){delete p_;}
bool Driver::Initialize(const Config&c)noexcept{
 try{std::lock_guard<std::mutex>l(p_->mu);if(p_->initialized||!c.claim||!c.owner||!c.storage.storage||!c.storage.exists||!c.storage.size||!c.storage.read||!c.storage.validate||c.user_slot==c.save_slot||c.user_slot>=6||c.save_slot>=6||!directory(c.save_directory)||!directory(c.intent_directory)||!imageMatches(c.base))return false;
  p_->cfg=c;p_->caller=c.base+0x50B785;p_->binder=reinterpret_cast<SaveBinder>(c.base+0x2FC750);p_->queue=reinterpret_cast<SaveQueue>(c.base+0x2DF990);
#ifdef CHECKPOINT_FRESH_SAVE_FIXTURE
  p_->caller=c.caller;p_->binder=reinterpret_cast<SaveBinder>(c.binder);p_->queue=reinterpret_cast<SaveQueue>(c.queue);
#endif
  if(!p_->binder||!p_->queue||!p_->caller)return false;p_->initialized=true;return true;
 }catch(...){return false;}
}
bool Driver::Submit(const Request&q)noexcept{
 try{std::lock_guard<std::mutex>l(p_->mu);auto&r=p_->r;
  if(!p_->initialized||InterlockedCompareExchange(&p_->stopped,0,0)||r.active||p_->count>=2||(r.status!=Status::Idle&&r.status!=Status::Complete)||!q.generation||!q.room_epoch||!q.period||!q.year||q.month<1||q.month>12||(q.day!=1&&q.day!=11&&q.day!=21)||q.force==0||q.force>=52||q.ruler>=1000||q.reserved||!filename(q.filename))return false;
  bool id=false;for(auto v:q.room_id)id|=v!=0;if(!id)return false;
  for(unsigned i=0;i<p_->count;++i){auto&h=p_->history[i];if(q.generation<=h.generation||!strcmp(q.filename,h.filename)||q.room_epoch!=h.room_epoch||memcmp(q.room_id,h.room_id,32)||q.period<=h.period||q.cut<h.cut)return false;}
  if(swprintf_s(p_->target,L"%ls\\%hs",p_->cfg.save_directory,q.filename)<0||swprintf_s(p_->intent,L"%ls\\%hs.intent",p_->cfg.intent_directory,q.filename)<0||!absent(p_->target)||!absent(p_->intent))return false;
  p_->request=q;p_->history[p_->count++]=q;r={};r.generation=q.generation;r.status=Status::Armed;r.completed_requests=p_->count-1;return true;
 }catch(...){return false;}
}
void Driver::Stop()noexcept{InterlockedExchange(&p_->stopped,1);}
Report Driver::Snapshot()noexcept{std::lock_guard<std::mutex>l(p_->mu);if(p_->r.binds&&InterlockedCompareExchange(&p_->stopped,0,0))p_->r.stop_after_commit=1;return p_->r;}
bool Driver::CopyArtifact(std::uint64_t generation,Artifact&out)noexcept{
 try{std::lock_guard<std::mutex>l(p_->mu);for(unsigned i=0;i<p_->count;++i){
  if(p_->history[i].generation!=generation||p_->completed[i].status!=Status::Complete||!p_->completed[i].file_bytes_verified)continue;
  Artifact value{};value.request=p_->history[i];value.report=p_->completed[i];value.bytes=p_->files[i].bytes;memcpy(value.sha256,p_->fileEvidence[i].localSha256,32);out=std::move(value);return true;
 }return false;}catch(...){return false;}
}
void Driver::Before(const CheckpointLoadWorkerFrame&f)noexcept{
 try{std::lock_guard<std::mutex>l(p_->mu);auto&r=p_->r;if(!p_->initialized||r.status==Status::Idle||r.status==Status::Complete||r.status==Status::Rejected||r.status==Status::Uncertain||r.status==Status::Cancelled)return;
  if(f.slot!=p_->cfg.user_slot&&f.slot!=p_->cfg.save_slot)return;
  if(local.driver||r.active){p_->fail(40);return;}
  local={this,f.call_id,f.slot,0,false,false,false};++r.entries;++r.active;
  if(f.thread_id!=GetCurrentThreadId()||!f.caller_entry_rsp||at<std::uintptr_t>(f.caller_entry_rsp)!=p_->caller||!p_->cfg.claim(&f,p_->request.generation)||!p_->source(f)){p_->fail(41);return;}local.claim=true;
  if(f.slot==p_->cfg.user_slot){
   if(r.status==Status::Armed){if(InterlockedCompareExchange(&p_->stopped,0,0)){r.status=Status::Cancelled;return;}if(!p_->planning(f.args[0],true))return;r.first_call=f.call_id;r.executor_thread=f.thread_id;local.related=true;}
   else if(r.status==Status::Finalized){if(!p_->planning(f.args[0],false))return;local.related=true;}
  }else if(r.status==Status::Queued){
   auto s=f.args[0],m=p_->cfg.base+0x19E7310,stack=at<std::uintptr_t>(m+0x20);
   if(s!=r.save_state||at<std::uint64_t>(m+0x10)!=6||!stack||at<std::uintptr_t>(stack+40)!=s||at<std::uintptr_t>(s)!=p_->cfg.base+0x12DC5F8||!p_->bound()){p_->fail(42);return;}
   for(unsigned i=0;i<5;++i)if(at<std::uintptr_t>(stack+i*8)!=p_->states[i]){p_->fail(43);return;}
   auto phase=at<unsigned>(s+0x470);if(phase>4){p_->fail(44);return;}
   // Native phases may repeat but must not skip or regress.
   if((phase&&!(r.phase_mask&(1u<<(phase-1))))||(r.phase_mask&~((1u<<(phase+1))-1))){p_->fail(45);return;}
   r.phase_mask|=1u<<phase;local.phase=phase;local.related=true;local.terminal=phase==4;
   if(local.terminal)r.native_success=at<unsigned>(p_->cfg.base+0x201EC2C)==1;
  }
 }catch(...){std::lock_guard<std::mutex>l(p_->mu);p_->fail(90);}
}
void Driver::After(const CheckpointLoadWorkerFrame&f)noexcept{
 try{std::lock_guard<std::mutex>l(p_->mu);auto&r=p_->r;
  if(local.driver!=this||local.call!=f.call_id||!local.claim||!local.related||r.error)return;
  if(!p_->source(f)){p_->fail(46);return;}++r.original_returned;
  if(f.slot==p_->cfg.user_slot){
   if(r.status==Status::Armed&&f.call_id==r.first_call)p_->enqueue(f.args[0]);
   else if(r.status==Status::Finalized){if(!p_->planning(f.args[0],false)||!p_->copyFresh(f)||!p_->planning(f.args[0],false))return;r.return_matched=1;r.last_call=f.call_id;r.status=Status::Returned;}
  }else if(f.slot==p_->cfg.save_slot&&r.status==Status::Queued){
   if(local.terminal){r.finalizer_returned=1;if(!r.native_success||!p_->idleStrings()||!p_->cacheReady(true)){p_->fail(47);return;}r.status=Status::Finalized;}
   else{auto next=at<unsigned>(f.args[0]+0x470);if(next!=local.phase&&next!=local.phase+1){p_->fail(48);return;}if(local.phase==1&&next==2)r.worker_started=1;if(local.phase==2&&next==3)r.worker_joined=1;}
  }
 }catch(...){std::lock_guard<std::mutex>l(p_->mu);p_->readFrame=nullptr;p_->fail(91);}
}
void Driver::Finally(const CheckpointLoadWorkerFrame&f,const CheckpointLoadWorkerExit&e)noexcept{
 try{std::lock_guard<std::mutex>l(p_->mu);auto&r=p_->r;if(local.driver!=this||local.call!=f.call_id)return;
  if(r.binds&&InterlockedCompareExchange(&p_->stopped,0,0))r.stop_after_commit=1;
  if(e.abnormal){++r.abnormal;p_->fail(49);}if(r.active)--r.active;++r.exits;local={};
  if(r.status==Status::Returned&&!r.error&&r.return_matched&&r.worker_started&&r.worker_joined&&r.phase_mask==31&&r.finalizer_returned&&r.file_bytes_verified&&!r.active){r.status=Status::Complete;r.completed_requests=p_->count;p_->completed[p_->count-1]=r;}
 }catch(...){std::lock_guard<std::mutex>l(p_->mu);p_->fail(92);local={};}
}
void Driver::BeforeCallback(const CheckpointLoadWorkerFrame*f,void*c)noexcept{if(f&&c)static_cast<Driver*>(c)->Before(*f);}
void Driver::AfterCallback(const CheckpointLoadWorkerFrame*f,void*c)noexcept{if(f&&c)static_cast<Driver*>(c)->After(*f);}
void Driver::FinallyCallback(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*c)noexcept{if(f&&e&&c)static_cast<Driver*>(c)->Finally(*f,*e);}
}
