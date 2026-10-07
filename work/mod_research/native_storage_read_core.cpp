#include "native_storage_read_core.h"
#include <bcrypt.h>
#include <cstring>
#include <cwchar>
#include <limits>
#pragma comment(lib,"bcrypt.lib")

namespace native_storage_read {
bool Sha256(const void* data,std::size_t n,unsigned char out[32]) noexcept {
    if(n>MAXDWORD)return false;
    BCRYPT_ALG_HANDLE alg=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;
    bool ok=BCryptOpenAlgorithmProvider(&alg,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0;
    if(ok)ok=BCryptCreateHash(alg,&hash,nullptr,0,nullptr,0,0)>=0;
    if(ok)ok=BCryptHashData(hash,(PUCHAR)data,ULONG(n),0)>=0;
    if(ok)ok=BCryptFinishHash(hash,out,32,0)>=0;
    if(hash)BCryptDestroyHash(hash);if(alg)BCryptCloseAlgorithmProvider(alg,0);
    return ok;
}
static bool context(const Api& a,Evidence& e) noexcept {
    __try{return a.validate(a.validationContext);}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
static bool exists(const Api& a,const char* n,Evidence& e) noexcept {
    if(!context(a,e))return false;
    __try{++e.existsCalls;return a.exists(a.storage,n);}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
static bool size(const Api& a,const char* n,std::int32_t& result,Evidence& e) noexcept {
    if(!context(a,e))return false;
    __try{++e.sizeCalls;result=a.size(a.storage,n);return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
static bool read(const Api& a,const char* n,void* out,std::int32_t amount,std::int32_t& result,Evidence& e) noexcept {
    if(!context(a,e))return false;
    __try{++e.readCalls;result=a.read(a.storage,n,out,amount);return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){e.exceptionCode=GetExceptionCode();return false;}
}
static bool validName(const Input& in) {
    if(!in.localPath||!in.basename||!*in.localPath)return false;
    auto len=std::strlen(in.basename);if(len<5||len>63||std::strcmp(in.basename+len-4,".s14"))return false;
    for(std::size_t i=0;i<len;++i){char c=in.basename[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'))return false;}
    if(std::strstr(in.basename,".."))return false;
    auto last=std::wcsrchr(in.localPath,L'\\');last=last?last+1:in.localPath;
    if(std::wcslen(last)!=len)return false;
    for(std::size_t i=0;i<len;++i)if(last[i]!=static_cast<unsigned char>(in.basename[i]))return false;
    return true;
}
static bool sameInfo(const BY_HANDLE_FILE_INFORMATION& a,const BY_HANDLE_FILE_INFORMATION& b){
    return a.dwVolumeSerialNumber==b.dwVolumeSerialNumber&&a.nFileIndexHigh==b.nFileIndexHigh&&a.nFileIndexLow==b.nFileIndexLow&&
        a.nFileSizeHigh==b.nFileSizeHigh&&a.nFileSizeLow==b.nFileSizeLow&&
        a.ftLastWriteTime.dwHighDateTime==b.ftLastWriteTime.dwHighDateTime&&a.ftLastWriteTime.dwLowDateTime==b.ftLastWriteTime.dwLowDateTime;
}
bool Verify(const Input& in,const Api& api,Lease& out,Evidence& e) noexcept {
    e={};HANDLE pinned=INVALID_HANDLE_VALUE;
    auto fail=[&](){e.osError=GetLastError();if(pinned!=INVALID_HANDLE_VALUE)CloseHandle(pinned);return false;};
    try {
        e.stage="input";
        if(out.file!=INVALID_HANDLE_VALUE||!out.bytes.empty()||!validName(in)||!in.expectedSize||in.expectedSize>16*1024*1024||
           !api.storage||!api.exists||!api.size||!api.read||!api.validate)return fail();
        e.stage="context";if(!context(api,e))return fail();
        e.stage="local_open";
        pinned=CreateFileW(in.localPath,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(pinned==INVALID_HANDLE_VALUE)return fail();
        BY_HANDLE_FILE_INFORMATION before{},after{};
        e.stage="local_identity";
        if(!GetFileInformationByHandle(pinned,&before)||before.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY||before.nFileSizeHigh||before.nFileSizeLow!=in.expectedSize)return fail();
        std::vector<unsigned char> local(in.expectedSize),native(in.expectedSize);
        e.stage="local_read";DWORD got=0;
        if(!ReadFile(pinned,local.data(),in.expectedSize,&got,nullptr)||got!=in.expectedSize)return fail();
        e.stage="local_hash";
        if(!Sha256(local.data(),local.size(),e.localSha256)||std::memcmp(e.localSha256,in.expectedSha256,32))return fail();
        e.stage="native_exists_before";if(!exists(api,in.basename,e))return fail();
        e.stage="native_size_before";
        if(!size(api,in.basename,e.sizes[0],e)||e.sizes[0]<=0||std::uint32_t(e.sizes[0])!=in.expectedSize)return fail();
        for(unsigned pass=0;pass<2;++pass){
            std::memset(native.data(),0xA5,native.size());
            e.stage=pass?"native_read_second":"native_read_first";
            if(!read(api,in.basename,native.data(),std::int32_t(in.expectedSize),e.readReturns[pass],e)||e.readReturns[pass]!=std::int32_t(in.expectedSize))return fail();
            e.stage=pass?"native_hash_second":"native_hash_first";
            if(!Sha256(native.data(),native.size(),e.nativeSha256[pass])||std::memcmp(e.nativeSha256[pass],in.expectedSha256,32)||std::memcmp(native.data(),local.data(),local.size()))return fail();
            e.stage=pass?"native_size_after_second":"native_size_after_first";
            if(!size(api,in.basename,e.sizes[pass+1],e)||e.sizes[pass+1]!=e.sizes[0])return fail();
            e.stage=pass?"native_exists_after_second":"native_exists_after_first";
            if(!exists(api,in.basename,e))return fail();
        }
        e.stage="local_final_identity";
        if(!GetFileInformationByHandle(pinned,&after)||!sameInfo(before,after)||!context(api,e))return fail();
        e.stage="matched_observed_reads";out.file=pinned;pinned=INVALID_HANDLE_VALUE;out.bytes=std::move(local);e.matched=true;return true;
    }catch(...){e.stage="allocation_or_cpp_exception";return fail();}
}
}
