#include "b_warm_storage_refresh_core.h"
#include <cstring>
#include <cwchar>

namespace b_warm_storage_refresh {
namespace {
struct Handle { HANDLE value=INVALID_HANDLE_VALUE; ~Handle(){if(value!=INVALID_HANDLE_VALUE)CloseHandle(value);} };
#pragma pack(push,1)
struct Intent {
    char magic[32]{};
    std::uint32_t version=1,recordSize=sizeof(Intent),size=0,previousSize=0;
    char basename[64]{};
    Identity source{};
    unsigned char nextSha[32]{},previousSha[32]{},owner[32]{},pathSha[32]{};
};
#pragma pack(pop)
bool any(const unsigned char* p){unsigned char v=0;for(unsigned i=0;i<32;++i)v|=p[i];return v!=0;}
bool same(const Identity&a,const Identity&b){return a.volume==b.volume&&a.indexHigh==b.indexHigh&&a.indexLow==b.indexLow&&a.lastWrite.dwLowDateTime==b.lastWrite.dwLowDateTime&&a.lastWrite.dwHighDateTime==b.lastWrite.dwHighDateTime;}
Identity identity(const BY_HANDLE_FILE_INFORMATION&i){return {i.dwVolumeSerialNumber,i.nFileIndexHigh,i.nFileIndexLow,i.ftLastWriteTime};}
bool inputOkay(const Input&i,const Api&a){
    if(!i.sourcePath||!i.intentPath||!i.basename||!*i.sourcePath||!*i.intentPath||!_wcsicmp(i.sourcePath,i.intentPath)||std::wcslen(i.sourcePath)>32760||std::wcslen(i.intentPath)>32760)return false;
    if(std::strcmp(i.basename,"svdexccSC03.s14"))return false;
    const auto n=std::strlen(i.basename);
    const wchar_t* leaf=std::wcsrchr(i.sourcePath,L'\\');leaf=leaf?leaf+1:i.sourcePath;
    if(std::wcslen(leaf)!=n)return false;
    for(std::size_t j=0;j<n;++j){const auto c=i.basename[j];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.')||leaf[j]!=c)return false;}
    return i.size&&i.size<=16u*1024*1024&&i.previousSize&&i.previousSize<=16u*1024*1024&&any(i.sha256)&&any(i.previousSha256)&&any(i.ownerBinding)&&(i.sourceIdentity.indexHigh||i.sourceIdentity.indexLow)&&a.read.storage&&a.read.exists&&a.read.size&&a.read.read&&a.read.validate&&a.write&&a.validateOwner;
}
bool context(const Input&i,const Api&a,Evidence&e) noexcept {
    __try{return a.read.validate(a.read.validationContext)&&a.validateOwner(a.ownerContext,i);}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
bool previous(const Input&i,const Api&a,Evidence&e,void* buffer,unsigned pass) noexcept {
    __try{
        if(!context(i,a,e)||!a.read.exists(a.read.storage,i.basename)||!context(i,a,e))return false;
        e.previousSizes[pass]=a.read.size(a.read.storage,i.basename);
        if(e.previousSizes[pass]!=static_cast<std::int32_t>(i.previousSize)||!context(i,a,e))return false;
        std::memset(buffer,0xA5,i.previousSize);
        ++e.previousReads;e.previousReturns[pass]=a.read.read(a.read.storage,i.basename,buffer,static_cast<std::int32_t>(i.previousSize));
        if(e.previousReturns[pass]!=static_cast<std::int32_t>(i.previousSize)||!native_storage_read::Sha256(buffer,i.previousSize,e.previousHashes[pass])||std::memcmp(e.previousHashes[pass],i.previousSha256,32)||!context(i,a,e))return false;
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
bool write(const Input&i,const Api&a,const void* bytes,Evidence&e) noexcept {
    __try{
        if(!context(i,a,e))return false;
        e.previousSizes[2]=a.read.size(a.read.storage,i.basename);
        if(e.previousSizes[2]!=static_cast<std::int32_t>(i.previousSize)||!context(i,a,e))return false;
        e.state=State::WriteEntered;++e.writeAttempts;e.sourcePinHeldAtWrite=true;
        e.nativeWriteReturn=a.write(a.read.storage,i.basename,bytes,static_cast<std::int32_t>(i.size));++e.writeReturned;return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
}
bool Refresh(const Input&i,const Api&a,Evidence&e) noexcept {
    e={};Handle source,intent;
    auto fail=[&](){e.osError=GetLastError();e.state=e.intentCreated||e.writeAttempts?State::Uncertain:State::Rejected;return false;};
    try{
        e.stage="input";if(!inputOkay(i,a))return fail();
        e.stage="owner_and_context";if(!context(i,a,e))return fail();
        e.stage="private_source_open";source.value=CreateFileW(i.sourcePath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);if(source.value==INVALID_HANDLE_VALUE)return fail();
        BY_HANDLE_FILE_INFORMATION before{},after{};
        e.stage="private_source_identity";if(!GetFileInformationByHandle(source.value,&before)||(before.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))||before.nNumberOfLinks!=1||before.nFileSizeHigh||before.nFileSizeLow!=i.size||!same(identity(before),i.sourceIdentity))return fail();
        std::vector<unsigned char> bytes(i.size),old(i.previousSize);DWORD got=0;
        e.stage="private_source_bytes";if(!ReadFile(source.value,bytes.data(),i.size,&got,nullptr)||got!=i.size||!native_storage_read::Sha256(bytes.data(),bytes.size(),e.sourceSha256)||std::memcmp(e.sourceSha256,i.sha256,32))return fail();
        e.stage="previous_native_first";if(!previous(i,a,e,old.data(),0))return fail();
        e.stage="previous_native_second";if(!previous(i,a,e,old.data(),1))return fail();
        if(!GetFileInformationByHandle(source.value,&after)||!same(identity(after),i.sourceIdentity)||after.nFileSizeHigh||after.nFileSizeLow!=i.size||!context(i,a,e))return fail();
        Intent record{};std::memcpy(record.magic,"san14.warm.refresh.intent.v1",28);record.size=i.size;record.previousSize=i.previousSize;std::strcpy(record.basename,i.basename);record.source=i.sourceIdentity;
        std::memcpy(record.nextSha,i.sha256,32);std::memcpy(record.previousSha,i.previousSha256,32);std::memcpy(record.owner,i.ownerBinding,32);
        if(!native_storage_read::Sha256(i.sourcePath,std::wcslen(i.sourcePath)*sizeof(wchar_t),record.pathSha))return fail();
        e.stage="claim_unique_durable_intent";intent.value=CreateFileW(i.intentPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);if(intent.value==INVALID_HANDLE_VALUE)return fail();e.intentCreated=true;
        DWORD wrote=0;if(!WriteFile(intent.value,&record,sizeof(record),&wrote,nullptr)||wrote!=sizeof(record)||!FlushFileBuffers(intent.value))return fail();e.intentDurable=true;e.state=State::IntentDurable;
        e.stage="native_write_once";if(!write(i,a,bytes.data(),e)||!e.nativeWriteReturn)return fail();e.state=State::WrittenUnverified;
        e.stage="complete_new_native_readback_twice";native_storage_read::Input ri{};ri.localPath=i.sourcePath;ri.basename=i.basename;ri.expectedSize=i.size;std::memcpy(ri.expectedSha256,i.sha256,32);native_storage_read::Lease lease;
        if(!native_storage_read::Verify(ri,a.read,lease,e.readback)||!context(i,a,e))return fail();
        if(!GetFileInformationByHandle(source.value,&after)||!same(identity(after),i.sourceIdentity)||after.nFileSizeHigh||after.nFileSizeLow!=i.size)return fail();
        e.state=State::Matched;e.matched=true;e.stage="refreshed_and_observed_twice";return true;
    }catch(...){e.stage="allocation_or_cpp_exception";return fail();}
}
}
