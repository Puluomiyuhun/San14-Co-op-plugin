#include "b_warm_storage_refresh_core.h"
#include <filesystem>
#include <cstdio>
#include <cstring>
#include <stdexcept>

namespace f=b_warm_storage_refresh;
namespace fs=std::filesystem;
struct Store { fs::path target,source;std::vector<unsigned char> cache;unsigned writes=0,reads=0;bool corrupt=false,sourceProtected=false,skipSecondRead=false; };
void require(bool b,const char* what){if(!b)throw std::runtime_error(what);}
void put(const fs::path&p,const std::vector<unsigned char>&v){HANDLE h=CreateFileW(p.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);require(h!=INVALID_HANDLE_VALUE,"create fixture");DWORD n=0;bool ok=WriteFile(h,v.data(),static_cast<DWORD>(v.size()),&n,nullptr)&&n==v.size();CloseHandle(h);require(ok,"write fixture");}
bool __fastcall exists(void*,const char*name){return !std::strcmp(name,"svdexccSC03.s14");}
std::int32_t __fastcall size(void*s,const char*){return static_cast<std::int32_t>(static_cast<Store*>(s)->cache.size());}
std::int32_t __fastcall read(void*s,const char*,void*out,std::int32_t n){auto&store=*static_cast<Store*>(s);++store.reads;if(store.skipSecondRead&&store.reads==2)return n;auto&v=store.cache;auto got=(std::min)(static_cast<std::size_t>(n),v.size());std::memcpy(out,v.data(),got);return static_cast<std::int32_t>(got);}
bool validate(void*){return true;}
bool owner(void*s,const f::Input&i){auto&v=*static_cast<Store*>(s);return v.source==i.sourcePath&&v.source!=v.target;}
bool __fastcall write(void*s,const char*,const void*bytes,std::int32_t n){
    auto&v=*static_cast<Store*>(s);++v.writes;
    HANDLE probe=CreateFileW(v.source.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    v.sourceProtected=probe==INVALID_HANDLE_VALUE&&GetLastError()==ERROR_SHARING_VIOLATION;if(probe!=INVALID_HANDLE_VALUE)CloseHandle(probe);
    HANDLE h=CreateFileW(v.target.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return false;
    DWORD got=0;bool ok=WriteFile(h,bytes,static_cast<DWORD>(n),&got,nullptr)&&got==static_cast<DWORD>(n)&&SetEndOfFile(h)&&FlushFileBuffers(h);CloseHandle(h);if(!ok)return false;
    auto p=static_cast<const unsigned char*>(bytes);v.cache.assign(p,p+n);if(v.corrupt)v.cache[0]^=1;return true;
}
f::Input input(Store&s,const fs::path&source,const fs::path&intent,const std::vector<unsigned char>&next,std::wstring&sp,std::wstring&ip){
    s.source=source;sp=source.wstring();ip=intent.wstring();f::Input i{};i.sourcePath=sp.c_str();i.intentPath=ip.c_str();i.basename="svdexccSC03.s14";i.size=static_cast<unsigned>(next.size());i.previousSize=static_cast<unsigned>(s.cache.size());i.ownerBinding[0]=17;
    require(native_storage_read::Sha256(next.data(),next.size(),i.sha256),"newhash");require(native_storage_read::Sha256(s.cache.data(),s.cache.size(),i.previousSha256),"oldhash");
    HANDLE h=CreateFileW(source.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);require(h!=INVALID_HANDLE_VALUE,"source identity open");BY_HANDLE_FILE_INFORMATION info{};require(GetFileInformationByHandle(h,&info)!=FALSE,"source identity");CloseHandle(h);i.sourceIdentity={info.dwVolumeSerialNumber,info.nFileIndexHigh,info.nFileIndexLow,info.ftLastWriteTime};return i;
}
int wmain(int argc,wchar_t**argv){
    try{
        require(argc==3,"args");const std::wstring mode=argv[1];fs::path dir=argv[2];fs::create_directories(dir/"a");fs::create_directories(dir/"b");
        Store s{};s.target=dir/"svdexccSC03.s14";s.cache=std::vector<unsigned char>(701,0x17);put(s.target,s.cache);
        std::vector<unsigned char> one(903,0x29),two(1127,0x38);auto src=dir/"a"/(mode==L"wrong-name"?"other.s14":"svdexccSC03.s14");put(src,one);
        std::wstring sp,ip;auto in=input(s,src,dir/"a.intent",one,sp,ip);f::Api api{};api.read={&s,exists,size,read,validate,&s};api.write=write;api.validateOwner=owner;api.ownerContext=&s;f::Evidence e{};HANDLE lock=INVALID_HANDLE_VALUE;
        if(mode==L"wrong-previous")in.previousSha256[0]^=1;
        if(mode==L"wrong-name")in.basename="other.s14";
        if(mode==L"previous-second-no-write")s.skipSecondRead=true;
        if(mode==L"target-read-lock"){lock=CreateFileW(s.target.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);require(lock!=INVALID_HANDLE_VALUE,"target lock");}
        if(mode==L"readback-corrupt")s.corrupt=true;
        bool ok=f::Refresh(in,api,e);if(lock!=INVALID_HANDLE_VALUE)CloseHandle(lock);
        if(mode==L"wrong-name"){require(!ok&&e.state==f::State::Rejected&&!std::strcmp(e.stage,"input")&&!e.intentCreated&&s.writes==0,"non-CC03 name must reject at input");}
        else if(mode==L"previous-second-no-write"){require(!ok&&e.state==f::State::Rejected&&!std::strcmp(e.stage,"previous_native_second")&&e.previousReads==2&&!e.intentCreated&&s.writes==0,"second prior read cannot inherit first buffer");}
        else if(mode==L"wrong-previous"){require(!ok&&e.state==f::State::Rejected&&!e.intentCreated&&s.writes==0,"wrong prior must reject before intent/write");}
        else if(mode==L"target-read-lock"||mode==L"readback-corrupt"){
            require(!ok&&e.state==f::State::Uncertain&&e.intentDurable&&e.writeAttempts==1&&s.writes==1&&s.sourceProtected,"post intent terminal");
            f::Evidence again{};require(!f::Refresh(in,api,again)&&s.writes==1,"old intent cannot write again");
            if(mode==L"target-read-lock")require(e.writeReturned==1&&!e.nativeWriteReturn&&s.cache.size()==701,"real target lock fails FileWrite");
        }else if(mode==L"two-generations"){
            require(ok&&e.matched&&e.previousReads==2&&e.readback.readCalls==2&&e.sourcePinHeldAtWrite&&s.sourceProtected&&s.cache==one,"first complete refresh");
            f::Evidence repeat{};require(!f::Refresh(in,api,repeat)&&s.writes==1,"first once no replay");
            auto second=dir/"b"/"svdexccSC03.s14";put(second,two);std::wstring sp2,ip2;auto in2=input(s,second,dir/"b.intent",two,sp2,ip2);f::Evidence e2{};require(f::Refresh(in2,api,e2)&&e2.matched&&e2.previousReads==2&&e2.readback.readCalls==2&&s.writes==2&&s.cache==two&&s.sourceProtected,"second complete refresh");
        }else require(false,"unknown case");
        std::printf("{\"passed\":true,\"writes\":%u,\"state\":%u,\"stage\":\"%s\",\"previous_reads\":%u,\"readback_reads\":%u,\"source_pin_held\":%s,\"native_load_authorized\":false}\n",s.writes,static_cast<unsigned>(e.state),e.stage,e.previousReads,e.readback.readCalls,s.sourceProtected?"true":"false");return 0;
    }catch(const std::exception&e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
