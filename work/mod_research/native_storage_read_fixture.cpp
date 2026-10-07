#include "native_storage_read_core.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace native_storage_read;
struct Sim {
    std::string test;std::wstring path;std::vector<unsigned char> data;
    unsigned sizes=0,reads=0,exists=0,checks=0;bool args=true,pinBlocked=false;
};
static bool args(Sim& s,const char* name){s.args=s.args&&!std::strcmp(name,"mppush01.s14");return s.args;}
static bool exists(void* p,const char* name){auto& s=*static_cast<Sim*>(p);args(s,name);++s.exists;return s.test!="missing"&&!(s.test=="vanished"&&s.exists>1);}
static int32_t size(void* p,const char* name){auto& s=*static_cast<Sim*>(p);args(s,name);++s.sizes;
    if(s.test=="size_zero")return 0;if(s.test=="size_negative")return -1;if(s.test=="size_huge")return INT_MAX;
    if(s.test=="size_wrong"||(s.test=="size_changed"&&s.sizes>1))return int32_t(s.data.size()+1);
    return int32_t(s.data.size());}
static int32_t read(void* p,const char* name,void* buffer,int32_t bytes){auto& s=*static_cast<Sim*>(p);args(s,name);++s.reads;
    s.args=s.args&&bytes==int32_t(s.data.size())&&buffer;
    if(s.test=="api_exception")RaiseException(0xE014F001,0,0,nullptr);
    auto handle=CreateFileW(s.path.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    s.pinBlocked=handle==INVALID_HANDLE_VALUE&&GetLastError()==ERROR_SHARING_VIOLATION;
    if(handle!=INVALID_HANDLE_VALUE)CloseHandle(handle);
    std::memcpy(buffer,s.data.data(),s.data.size());
    if(s.test=="first_bytes_wrong"||(s.test=="second_bytes_wrong"&&s.reads==2))static_cast<unsigned char*>(buffer)[97]^=0x40;
    if(s.test=="read_zero")return 0;if(s.test=="read_negative")return -1;
    if(s.test=="read_short")return bytes-1;if(s.test=="read_excess")return bytes+1;
    return bytes;}
static bool validate(void* p){auto& s=*static_cast<Sim*>(p);++s.checks;return s.test!="context_invalid"&&!(s.test=="context_drift"&&s.reads>0);}
static bool run(const char* test,const std::wstring& directory,const wchar_t* archive=nullptr){
    Sim s;s.test=test;s.path=directory+L"\\mppush01.s14";s.data.resize(274880);
    for(size_t i=0;i<s.data.size();++i)s.data[i]=static_cast<unsigned char>((i*17+31)^(i>>8));
    if(archive){
        auto input=CreateFileW(archive,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(input==INVALID_HANDLE_VALUE)return false;
        LARGE_INTEGER length{};DWORD got=0;
        bool valid=GetFileSizeEx(input,&length)&&length.QuadPart==274880&&ReadFile(input,s.data.data(),DWORD(s.data.size()),&got,nullptr)&&got==s.data.size();
        CloseHandle(input);if(!valid)return false;
        unsigned char digest[32]{};Sha256(s.data.data(),s.data.size(),digest);
        const unsigned char expected[32]={0x88,0xdd,0xc3,0x9f,0xd2,0xfd,0x76,0xc0,0xc4,0xb1,0x30,0xbd,0x9a,0x2d,0xad,0x12,0xef,0xfa,0x9c,0xfd,0x20,0xa1,0xcb,0x33,0x39,0x81,0xd5,0x41,0xe8,0x76,0x1b,0x8c};
        if(std::memcmp(digest,expected,32))return false;
    }
    auto file=CreateFileW(s.path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;DWORD wrote=0;bool written=WriteFile(file,s.data.data(),DWORD(s.data.size()),&wrote,nullptr)&&wrote==s.data.size();CloseHandle(file);if(!written)return false;
    Input in{};in.localPath=s.path.c_str();in.basename="mppush01.s14";in.expectedSize=uint32_t(s.data.size());Sha256(s.data.data(),s.data.size(),in.expectedSha256);
    Api api{&s,&exists,&size,&read,&validate,&s};Evidence e;bool ok=false;bool reuseRefused=true;
    if(s.test=="local_hash_wrong")in.expectedSha256[0]^=1;
    if(s.test=="local_size_wrong")++in.expectedSize;
    if(s.test=="name_wrong")in.basename="svdexSC34.s14";
    if(s.test=="path_escape")in.basename="../mppush01.s14";
    if(s.test=="null_api")api.read=nullptr;
    if(s.test=="input_zero")in.expectedSize=0;
    if(s.test=="input_huge")in.expectedSize=32*1024*1024;
    bool stillPinned=false;
    {Lease lease;ok=Verify(in,api,lease,e);
        if(ok){
            stillPinned=lease.file!=INVALID_HANDLE_VALUE&&lease.bytes==s.data&&e.readCalls==2&&e.sizeCalls==3&&e.existsCalls==3;
            Evidence again;reuseRefused=!Verify(in,api,lease,again)&&!again.matched;
        }
    }
    auto after=CreateFileW(s.path.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    bool released=after!=INVALID_HANDLE_VALUE;if(released)CloseHandle(after);
    bool expected=s.test=="match"||s.test=="pin_blocks_write"||s.test=="archive_match";
    bool passed=written&&released&&s.args&&ok==expected&&e.matched==expected&&reuseRefused&&(!expected||(stillPinned&&s.pinBlocked));
    if(s.test=="api_exception")passed=passed&&e.exceptionCode==0xE014F001;
    std::printf("{\"case\":\"%s\",\"passed\":%s,\"matched\":%s,\"stage\":\"%s\",\"read_calls\":%u,\"size_calls\":%u,\"exists_calls\":%u,\"pin_blocks_write\":%s,\"handle_released\":%s,\"game_access\":false}\n",test,passed?"true":"false",ok?"true":"false",e.stage,e.readCalls,e.sizeCalls,e.existsCalls,s.pinBlocked?"true":"false",released?"true":"false");
    return passed;
}
int wmain(int argc,wchar_t** argv){if(argc!=3&&argc!=4)return 2;std::string test;for(const wchar_t* p=argv[1];*p;++p){if(*p<32||*p>127)return 2;test.push_back(static_cast<char>(*p));}return run(test.c_str(),argv[2],argc==4?argv[3]:nullptr)?0:1;}
