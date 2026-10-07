#include "native_storage_publish_core.h"
#include <cstring>
#include <cwchar>

namespace native_storage_publish {
const unsigned char TargetSha256[32]={0x88,0xdd,0xc3,0x9f,0xd2,0xfd,0x76,0xc0,0xc4,0xb1,0x30,0xbd,0x9a,0x2d,0xad,0x12,0xef,0xfa,0x9c,0xfd,0x20,0xa1,0xcb,0x33,0x39,0x81,0xd5,0x41,0xe8,0x76,0x1b,0x8c};
namespace {
struct Handle {
    HANDLE value=INVALID_HANDLE_VALUE;
    ~Handle(){if(value!=INVALID_HANDLE_VALUE)CloseHandle(value);}
    bool close(){if(value==INVALID_HANDLE_VALUE)return true;auto h=value;value=INVALID_HANDLE_VALUE;return CloseHandle(h)!=FALSE;}
};
#pragma pack(push,1)
struct Intent {
    char magic[32]{};
    std::uint32_t version=1,recordSize=sizeof(Intent),size=TargetSize;
    char basename[sizeof(TargetName)]{};
    Identity identity{};
    unsigned char ownerBinding[32]{},sourceSha256[32]{},localPathSha256[32]{};
};
#pragma pack(pop)
bool sameIdentity(const Identity&a,const Identity&b){return a.volume==b.volume&&a.indexHigh==b.indexHigh&&a.indexLow==b.indexLow&&a.lastWrite.dwHighDateTime==b.lastWrite.dwHighDateTime&&a.lastWrite.dwLowDateTime==b.lastWrite.dwLowDateTime;}
Identity identity(const BY_HANDLE_FILE_INFORMATION&i){return {i.dwVolumeSerialNumber,i.nFileIndexHigh,i.nFileIndexLow,i.ftLastWriteTime};}
bool inputOkay(const Input&in,const Api&a){
    if(!in.localPath||!in.intentPath||!*in.localPath||!*in.intentPath||std::wcslen(in.localPath)>32760||std::wcslen(in.intentPath)>32760||!_wcsicmp(in.localPath,in.intentPath))return false;
    auto last=std::wcsrchr(in.localPath,L'\\');last=last?last+1:in.localPath;if(std::wcscmp(last,TargetWideName))return false;
    unsigned char any=0;for(auto value:in.ownerBinding)any|=value;
    return any&&(in.expectedStage.indexHigh||in.expectedStage.indexLow)&&a.read.storage&&a.read.exists&&a.read.size&&a.read.read&&a.read.validate&&a.write&&a.validateStage;
}
bool context(const Input&in,const Api&a,Evidence&e) noexcept {
    __try{return a.read.validate(a.read.validationContext)&&a.validateStage(a.stageContext,in);}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
bool absent(const Input&in,const Api&a,Evidence&e) noexcept {
    if(!context(in,a,e))return false;
    __try{
        ++e.existsCalls;bool exists=a.read.exists(a.read.storage,TargetName);if(exists||!context(in,a,e)||e.sizeCalls>=3)return false;
        auto index=e.sizeCalls++;e.absentSizes[index]=a.read.size(a.read.storage,TargetName);
        return e.absentSizes[index]==0&&context(in,a,e);
    }
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
bool nativeWrite(const Input&in,const Api&a,const void*bytes,Evidence&e) noexcept {
    if(!context(in,a,e))return false;
    __try{++e.writeAttempts;e.state=State::WriteEntered;e.nativeWriteReturn=a.write(a.read.storage,TargetName,bytes,std::int32_t(TargetSize));++e.writeReturned;return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
}
bool Publish(const Input&in,const Api&a,Evidence&e) noexcept {
    e={};Handle local,intent;
    auto fail=[&](){e.osError=GetLastError();e.state=e.intentCreated||e.writeAttempts?State::Uncertain:State::Rejected;return false;};
    try {
        e.stage="input";if(!inputOkay(in,a))return fail();
        e.stage="owner_and_context";if(!context(in,a,e))return fail();
        e.stage="local_open";
        local.value=CreateFileW(in.localPath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        if(local.value==INVALID_HANDLE_VALUE)return fail();
        e.stage="exact_own_stage_identity";BY_HANDLE_FILE_INFORMATION before{},after{};
        if(!GetFileInformationByHandle(local.value,&before)||(before.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))||before.nFileSizeHigh||before.nFileSizeLow!=TargetSize||before.nNumberOfLinks!=1)return fail();
        e.sourceIdentity=identity(before);if(!sameIdentity(e.sourceIdentity,in.expectedStage))return fail();
        std::vector<unsigned char> source(TargetSize);DWORD got=0;
        e.stage="load_exact_local_bytes";if(!ReadFile(local.value,source.data(),TargetSize,&got,nullptr)||got!=TargetSize)return fail();
        e.stage="local_full_sha";if(!native_storage_read::Sha256(source.data(),source.size(),e.sourceSha256)||std::memcmp(e.sourceSha256,TargetSha256,32))return fail();
        if(!GetFileInformationByHandle(local.value,&after)||!sameIdentity(identity(after),e.sourceIdentity)||after.nFileSizeHigh||after.nFileSizeLow!=TargetSize)return fail();
        e.sourceMatched=true;
        e.stage="native_absent_first";if(!absent(in,a,e))return fail();
        e.stage="native_absent_second";if(!absent(in,a,e))return fail();
        Intent record{};std::memcpy(record.magic,"san14.cc03.publish.intent.v1",28);std::memcpy(record.basename,TargetName,sizeof(TargetName));record.identity=e.sourceIdentity;
        std::memcpy(record.ownerBinding,in.ownerBinding,32);std::memcpy(record.sourceSha256,e.sourceSha256,32);
        if(!native_storage_read::Sha256(in.localPath,std::wcslen(in.localPath)*sizeof(wchar_t),record.localPathSha256))return fail();
        e.stage="claim_unique_durable_intent";
        intent.value=CreateFileW(in.intentPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
        if(intent.value==INVALID_HANDLE_VALUE)return fail();e.intentCreated=true;
        DWORD wrote=0;if(!WriteFile(intent.value,&record,sizeof(record),&wrote,nullptr)||wrote!=sizeof(record)||!FlushFileBuffers(intent.value))return fail();
        e.intentDurable=true;e.state=State::IntentDurable;
        e.stage="release_deny_write_pin";if(!context(in,a,e)||!local.close())return fail();e.localPinReleased=true;
        // Native storage can see a different namespace/cache than the physical
        // stage. Recheck immediately before writing, after intent and pin release.
        e.stage="native_absent_final";if(!absent(in,a,e))return fail();
        e.stage="native_file_write_once";if(!nativeWrite(in,a,source.data(),e)||!e.nativeWriteReturn)return fail();
        e.state=State::WrittenUnverified;
        unsigned char afterHash[32]{};
        e.stage="post_write_source_and_context";
        if(!native_storage_read::Sha256(source.data(),source.size(),afterHash)||std::memcmp(afterHash,TargetSha256,32)||!context(in,a,e))return fail();
        native_storage_read::Input readInput{};readInput.localPath=in.localPath;readInput.basename=TargetName;readInput.expectedSize=TargetSize;std::memcpy(readInput.expectedSha256,TargetSha256,32);
        native_storage_read::Lease readback;
        e.stage="complete_native_readback_twice";++e.readbackAttempts;if(!native_storage_read::Verify(readInput,a.read,readback,e.readback)||!context(in,a,e))return fail();
        // Lease is deliberately released on return. This establishes the two
        // observed full reads, never the bytes consumed by a future world load.
        e.matched=true;e.state=State::Matched;e.stage="published_and_observed_twice";return true;
    }catch(...){e.stage="allocation_or_cpp_exception";return fail();}
}
}
