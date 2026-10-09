#include "b_warm_refresh_owner.h"
#include <cstring>
#include <cwchar>
#include <vector>

namespace b_warm_refresh {
namespace sr=b_warm_storage_refresh;namespace sb=checkpoint_live_storage_binding;
namespace {
Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;
volatile LONG installed=0,executed=0;
HANDLE targetLease=INVALID_HANDLE_VALUE;
native_storage_read::Api currentApi{};
DWORD executingThread=0;
void text(char(&dst)[64],const char*src){std::memset(dst,0,sizeof dst);if(src)for(unsigned n=0;n<63&&src[n];++n)dst[n]=src[n];}
void stage(const char*s){AcquireSRWLockExclusive(&lock);text(report.stage,s);ReleaseSRWLockExclusive(&lock);}
bool fail(Error e,const char*s,DWORD ex=0,DWORD os=GetLastError()){AcquireSRWLockExclusive(&lock);if(!report.error){report.error=unsigned(e);text(report.firstFailure,s);report.osError=os;report.exceptionCode=ex;}report.state=unsigned(State::Failed);ReleaseSRWLockExclusive(&lock);return false;}
bool any(const unsigned char*x){unsigned v=0;for(unsigned i=0;i<32;++i)v|=x[i];return v!=0;}
bool path(const wchar_t*p){return p&&p[0]&&p[1]==L':'&&p[2]==L'\\'&&!p[511]&&!wcsstr(p,L"..")&&!wcschr(p+2,L':')&&!wcschr(p,L'/');}
bool name(const wchar_t*p){const auto q=wcsrchr(p,L'\\');return q&&!wcscmp(q+1,L"svdexccSC03.s14");}
bool identity(const BY_HANDLE_FILE_INFORMATION&i,const sr::Identity&v){return i.dwVolumeSerialNumber==v.volume&&i.nFileIndexHigh==v.indexHigh&&i.nFileIndexLow==v.indexLow&&i.ftLastWriteTime.dwLowDateTime==v.lastWrite.dwLowDateTime&&i.ftLastWriteTime.dwHighDateTime==v.lastWrite.dwHighDateTime;}
bool sameFile(const sr::Identity&a,const sr::Identity&b){return a.volume==b.volume&&a.indexHigh==b.indexHigh&&a.indexLow==b.indexLow;}
bool file(HANDLE h,unsigned size,const unsigned char*expected,const sr::Identity*id){
 BY_HANDLE_FILE_INFORMATION first{},last{};if(h==INVALID_HANDLE_VALUE||!GetFileInformationByHandle(h,&first)||(first.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))||first.nNumberOfLinks!=1||first.nFileSizeHigh||first.nFileSizeLow!=size||(id&&!identity(first,*id)))return false;
 LARGE_INTEGER zero{};if(!SetFilePointerEx(h,zero,nullptr,FILE_BEGIN))return false;
 std::vector<unsigned char> bytes(size);DWORD got=0;unsigned char hash[32]{};
 if(!ReadFile(h,bytes.data(),size,&got,nullptr)||got!=size||!native_storage_read::Sha256(bytes.data(),bytes.size(),hash)||memcmp(hash,expected,32)||!GetFileInformationByHandle(h,&last))return false;
 return first.dwVolumeSerialNumber==last.dwVolumeSerialNumber&&first.nFileIndexHigh==last.nFileIndexHigh&&first.nFileIndexLow==last.nFileIndexLow&&first.nFileSizeHigh==last.nFileSizeHigh&&first.nFileSizeLow==last.nFileSizeLow&&first.ftLastWriteTime.dwLowDateTime==last.ftLastWriteTime.dwLowDateTime&&first.ftLastWriteTime.dwHighDateTime==last.ftLastWriteTime.dwHighDateTime;
}
HANDLE open(const wchar_t*p){return CreateFileW(p,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);}
bool writeBinding(){
 const auto&c=config.warm.owner;const auto&e=config.write;
 if(e.moduleIndex!=c.vtableModuleIndex||e.moduleIndex>=c.storageModuleCount||!e.address)return false;
 const auto&m=c.storageModules[e.moduleIndex];if(e.address<m.base||e.address+32<e.address||e.address+32>m.base+m.sizeOfImage)return false;
 MEMORY_BASIC_INFORMATION page{};if(VirtualQuery(reinterpret_cast<void*>(e.address),&page,sizeof page)!=sizeof page||page.State!=MEM_COMMIT||page.Type!=MEM_IMAGE||uintptr_t(page.AllocationBase)!=m.base||(page.Protect&(PAGE_GUARD|PAGE_NOACCESS))||!(page.Protect&(PAGE_EXECUTE|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))return false;
 return *reinterpret_cast<const uintptr_t*>(c.storage)==c.storageVtable&&*reinterpret_cast<const uintptr_t*>(c.storageVtable)==e.address&&!memcmp(reinterpret_cast<const void*>(e.address),e.first32,32);
}
bool valid(void*) noexcept {
 __try{
  if(GetCurrentThreadId()!=executingThread||!currentApi.validate||!currentApi.validate(currentApi.validationContext))return false;
  const bool ok=writeBinding();if(!ok)fail(Error::WriteBinding,"write_endpoint_or_slot");
  return ok&&currentApi.validate(currentApi.validationContext)&&writeBinding();
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception,"write_binding_exception",GetExceptionCode());}
}
bool owner(void*,const sr::Input&i) noexcept {
 __try{return GetCurrentThreadId()==executingThread&&i.sourcePath==config.warm.owner.localPath&&i.intentPath==config.refreshIntent&&i.size==config.warm.profile.file.size&&i.previousSize==config.previousSize&&!memcmp(i.ownerBinding,config.warm.owner.ownerBinding,32)&&!sameFile(config.sourceIdentity,config.previousTargetIdentity)&&valid(nullptr);}
 __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool shape(){
 const auto&c=config;const auto&w=c.warm;const auto&o=w.owner;
 if(c.magic!=Magic||c.size!=sizeof c||c.version!=1||c.reserved||w.magic!=b_warm_profile::Magic||w.size!=sizeof w||w.version!=1||!b_warm_profile::Validate(w.profile)||!path(o.localPath)||!name(o.localPath)||!path(c.targetPath)||!name(c.targetPath)||!path(c.backupPath)||!path(c.refreshIntent)||!c.previousSize||c.previousSize>16u*1024*1024||!any(c.previousSha256)||!any(o.ownerBinding)||!(c.sourceIdentity.indexHigh||c.sourceIdentity.indexLow)||!(c.previousTargetIdentity.indexHigh||c.previousTargetIdentity.indexLow)||sameFile(c.sourceIdentity,c.previousTargetIdentity))return false;
 const wchar_t*paths[]={o.localPath,c.targetPath,c.backupPath,c.refreshIntent,o.installIntent,o.requestIntent,o.identityIntent};
 for(unsigned a=0;a<7;++a)for(unsigned b=0;b<a;++b)if(!_wcsicmp(paths[a],paths[b]))return false;
 return c.write.moduleIndex==o.vtableModuleIndex&&c.write.moduleIndex<o.storageModuleCount&&c.write.address&&any(c.write.first32);
}
bool executeBody(const native_storage_read::Api&a){
 if(InterlockedCompareExchange(&installed,0,0)!=2||InterlockedCompareExchange(&executed,1,0))return fail(Error::AlreadyUsed,"execute_once");
 AcquireSRWLockExclusive(&lock);++report.executeCalls;report.state=unsigned(State::Executing);ReleaseSRWLockExclusive(&lock);
 const auto&o=config.warm.owner;
 if(a.storage!=reinterpret_cast<void*>(o.storage)||a.exists!=reinterpret_cast<native_storage_read::FileExists>(o.exists.address)||a.size!=reinterpret_cast<native_storage_read::GetFileSize>(o.fileSize.address)||a.read!=reinterpret_cast<native_storage_read::FileRead>(o.read.address)||!a.validate)return fail(Error::Scope,"authenticated_api_identity");
 currentApi=a;executingThread=GetCurrentThreadId();stage("source_target_backup");
 HANDLE source=INVALID_HANDLE_VALUE,old=INVALID_HANDLE_VALUE,backup=INVALID_HANDLE_VALUE;bool ok=false;
 __try{
  source=open(o.localPath);old=open(config.targetPath);backup=open(config.backupPath);
  if(!file(source,config.warm.profile.file.size,config.warm.profile.file.sha256,&config.sourceIdentity)||!file(old,config.previousSize,config.previousSha256,&config.previousTargetIdentity)||!file(backup,config.previousSize,config.previousSha256,nullptr)){fail(Error::File,"source_target_backup_identity_or_hash");__leave;}
  if(!valid(nullptr)){fail(Error::Scope,"authenticated_game_before");__leave;}
  // The native writer must be able to open its target. Private source and
  // backup stay deny-write pinned across publication and readback.
  if(!CloseHandle(old)){old=INVALID_HANDLE_VALUE;fail(Error::File,"close_old_target");__leave;}old=INVALID_HANDLE_VALUE;
  sr::Input i{};i.sourcePath=o.localPath;i.intentPath=config.refreshIntent;i.basename=config.warm.profile.file.name;i.size=config.warm.profile.file.size;i.previousSize=config.previousSize;i.sourceIdentity=config.sourceIdentity;
  memcpy(i.sha256,config.warm.profile.file.sha256,32);memcpy(i.previousSha256,config.previousSha256,32);memcpy(i.ownerBinding,o.ownerBinding,32);
  sr::Api api{};api.read=a;api.read.validate=valid;api.read.validationContext=nullptr;api.write=reinterpret_cast<sr::FileWrite>(config.write.address);api.validateOwner=owner;
  sr::Evidence e{};stage("refresh_native_storage");const bool refreshed=sr::Refresh(i,api,e);
  AcquireSRWLockExclusive(&lock);report.writeAttempts=e.writeAttempts;report.writeReturned=e.writeReturned;report.intentCreated=e.intentCreated;report.intentDurable=e.intentDurable;report.previousReads=e.previousReads;report.newReads=e.readback.readCalls;text(report.stage,e.stage);ReleaseSRWLockExclusive(&lock);
  if(!refreshed){const auto failure=!strcmp(e.stage,"complete_new_native_readback_twice")?e.readback.stage:e.stage;fail(Error::Refresh,failure,e.exceptionCode,e.osError);__leave;}
  targetLease=open(config.targetPath);AcquireSRWLockExclusive(&lock);report.leaseHeld=targetLease!=INVALID_HANDLE_VALUE;ReleaseSRWLockExclusive(&lock);
  if(!file(targetLease,config.warm.profile.file.size,config.warm.profile.file.sha256,nullptr)){fail(Error::TargetReadback,"published_target_hash");__leave;}
  if(!valid(nullptr)){fail(Error::Scope,"post_publication_scope");__leave;}
  AcquireSRWLockExclusive(&lock);report.matched=1;report.state=unsigned(State::Matched);text(report.stage,"native_refresh_and_target_pinned");ReleaseSRWLockExclusive(&lock);ok=true;
 }__finally{if(old!=INVALID_HANDLE_VALUE)CloseHandle(old);if(source!=INVALID_HANDLE_VALUE)CloseHandle(source);if(backup!=INVALID_HANDLE_VALUE)CloseHandle(backup);executingThread=0;currentApi={};}
 return ok;
}
}
bool Execute(const native_storage_read::Api&a) noexcept {__try{return executeBody(a);}__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception,"execute_exception",GetExceptionCode());}}
bool ReleaseAfterRetirement() noexcept {
 AcquireSRWLockExclusive(&lock);++report.releaseCalls;bool ok=false;
 __try{if(report.state!=unsigned(State::Matched)||!report.matched||!report.leaseHeld||report.leaseReleased||targetLease==INVALID_HANDLE_VALUE)__leave;
 if(!CloseHandle(targetLease))__leave;targetLease=INVALID_HANDLE_VALUE;report.leaseHeld=0;report.leaseReleased=1;report.state=unsigned(State::Released);text(report.stage,"released_after_native_retirement");ok=true;
 }__finally{ReleaseSRWLockExclusive(&lock);}return ok||fail(Error::Release,"retirement_release");
}
void Snapshot(Report&r) noexcept {AcquireSRWLockShared(&lock);r=report;ReleaseSRWLockShared(&lock);}
bool Capture(const Config&c) noexcept {
 __try{
  if(InterlockedCompareExchange(&installed,1,0))return fail(Error::AlreadyUsed,"capture_once");config=c;
  if(!shape())return fail(Error::Config,"config_shape");
  AcquireSRWLockExclusive(&lock);report.captured=1;report.state=unsigned(State::Captured);report.previousSize=config.previousSize;report.newSize=config.warm.profile.file.size;report.attempt=config.warm.owner.attempt;report.epoch=config.warm.owner.epoch;report.generation=config.warm.owner.generation;memcpy(report.previousSha256,config.previousSha256,32);memcpy(report.newSha256,config.warm.profile.file.sha256,32);text(report.stage,"captured");ReleaseSRWLockExclusive(&lock);
  InterlockedExchange(&installed,2);return true;
 }__except(EXCEPTION_EXECUTE_HANDLER){return fail(Error::Exception,"capture_exception",GetExceptionCode());}
}
DWORD install(void*p) noexcept {
 __try{
  if(!p||!Capture(*static_cast<const Config*>(p)))return 1;
  const auto code=InstallBWarmProfileOwner(&config.warm);if(code){fail(Error::Install,"warm_install_rejected");return 3;}return 0;
 }__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Exception,"install_exception",GetExceptionCode());return 4;}
}
}
extern "C" DWORD WINAPI InstallBWarmRefreshOwner(void*p){return b_warm_refresh::install(p);}
extern "C" DWORD WINAPI GetBWarmRefreshReport(void*p){__try{if(!p)return 1;b_warm_refresh::Snapshot(*static_cast<b_warm_refresh::Report*>(p));return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 2;}}
extern "C" DWORD WINAPI DescribeBWarmRefreshOwner(void*p){__try{if(!p)return 1;b_warm_refresh::Description d{};if(DescribeBWarmProfileOwner(&d.warm))return 2;*static_cast<b_warm_refresh::Description*>(p)=d;return 0;}__except(EXCEPTION_EXECUTE_HANDLER){return 3;}}
