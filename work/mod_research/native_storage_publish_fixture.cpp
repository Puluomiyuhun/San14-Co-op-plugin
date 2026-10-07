#include "native_storage_publish_core.h"
#include <atomic>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <mutex>
#include <stdexcept>
#include <thread>
namespace p=native_storage_publish;
namespace fs=std::filesystem;
void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
struct Store {std::mutex lock;std::vector<unsigned char> bytes;std::atomic<unsigned>writes{0},reads{0};std::atomic<bool>visible{false};};
struct Context {std::string name;Store*store;std::wstring local,intent;p::Input input{};p::Api api{};p::Evidence*e=nullptr;unsigned exists=0;bool valid=true;};
bool validate(void*ctx){auto*c=static_cast<Context*>(ctx);if(c->name=="cancel_after_intent"&&c->e->intentDurable)return false;return c->valid&&c->name!="context_rejected";}
bool stage(void*ctx,const p::Input&i){auto*c=static_cast<Context*>(ctx);return c->name!="owner_rejected"&&c->local==i.localPath&&c->intent==i.intentPath&&i.ownerBinding[0]==0x73;}
bool __fastcall exists(void*ctx,const char*name){auto*c=static_cast<Context*>(ctx);need(!std::strcmp(name,p::TargetName),"fixed exists filename");++c->exists;
    if(c->name=="native_exists_exception")RaiseException(0xE140C001,0,0,nullptr);
    if(c->name=="native_present"||(c->name=="native_present_second"&&c->exists>=2)||(c->name=="native_present_after_intent"&&c->e->intentDurable))return true;
    if(c->name=="readback_missing"&&c->store->writes)return false;
    return c->store->visible;
}
std::int32_t __fastcall size(void*ctx,const char*name){auto*c=static_cast<Context*>(ctx);need(!std::strcmp(name,p::TargetName),"fixed size filename");
    if(!c->store->visible){if(c->name=="absence_negative_size")return -1;if(c->name=="absence_positive_size")return p::TargetSize;return 0;}
    return c->name=="readback_size"?1:std::int32_t(p::TargetSize);
}
std::int32_t __fastcall read(void*ctx,const char*name,void*out,std::int32_t n){auto*c=static_cast<Context*>(ctx);need(!std::strcmp(name,p::TargetName)&&n==p::TargetSize,"readback ABI");++c->store->reads;
    if(c->name=="readback_exception")RaiseException(0xE140C002,0,0,nullptr);
    std::lock_guard<std::mutex>lock(c->store->lock);need(c->store->bytes.size()==p::TargetSize,"published bytes");std::memcpy(out,c->store->bytes.data(),n);
    if(c->name=="readback_corrupt")static_cast<unsigned char*>(out)[500]^=1;
    return c->name=="readback_short"?n-1:n;
}
bool __fastcall write(void*ctx,const char*name,const void*data,std::int32_t n){auto*c=static_cast<Context*>(ctx);
    need(!std::strcmp(name,p::TargetName)&&n==p::TargetSize,"write ABI fixed filename/size");
    need(c->e->intentCreated&&c->e->intentDurable&&c->e->localPinReleased&&c->e->writeAttempts==1,"durable intent and pin release precede native call");
    HANDLE intent=CreateFileW(c->intent.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
    need(intent!=INVALID_HANDLE_VALUE,"intent exists at native call");char magic[32]{};DWORD got=0;need(ReadFile(intent,magic,sizeof magic,&got,nullptr)&&got==sizeof magic,"intent bytes present");CloseHandle(intent);need(!std::strcmp(magic,"san14.cc03.publish.intent.v1"),"intent binding format");
    ++c->store->writes;
    if(c->name=="reentrant_publish"){p::Evidence nested{};auto*old=c->e;c->e=&nested;bool result=p::Publish(c->input,c->api,nested);c->e=old;need(!result&&nested.writeAttempts==0,"reentrant publication cannot reuse intent");}
    HANDLE target=CreateFileW(c->local.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(target==INVALID_HANDLE_VALUE){need(c->name=="concurrent_publish","local deny-write pin really released");return false;}
    DWORD wrote=0;need(WriteFile(target,data,n,&wrote,nullptr)&&wrote==DWORD(n)&&FlushFileBuffers(target),"fixture native method writes its own target");CloseHandle(target);
    {std::lock_guard<std::mutex>lock(c->store->lock);c->store->bytes.assign(static_cast<const unsigned char*>(data),static_cast<const unsigned char*>(data)+n);}
    c->store->visible=true;
    if(c->name=="write_exception")RaiseException(0xE140C003,0,0,nullptr);
    if(c->name=="cancel_during_write")c->valid=false;
    if(c->name=="write_clobber_source")const_cast<unsigned char*>(static_cast<const unsigned char*>(data))[500]^=1;
    return c->name!="write_false";
}
void initialize(Context&c,Store&s,const fs::path&folder,const std::string&name){c.name=name;c.store=&s;c.local=(folder/p::TargetWideName).wstring();c.intent=(folder/L"publish-once.intent").wstring();c.input.localPath=c.local.c_str();c.input.intentPath=c.intent.c_str();c.input.ownerBinding[0]=0x73;
    HANDLE h=CreateFileW(c.local.c_str(),GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);need(h!=INVALID_HANDLE_VALUE,"own stage open");BY_HANDLE_FILE_INFORMATION info{};need(GetFileInformationByHandle(h,&info),"own stage identity");CloseHandle(h);
    c.input.expectedStage={info.dwVolumeSerialNumber,info.nFileIndexHigh,info.nFileIndexLow,info.ftLastWriteTime};
    c.api.read={&c,exists,size,read,validate,&c};c.api.write=write;c.api.validateStage=stage;c.api.stageContext=&c;
}
int wmain(int argc,wchar_t**argv){try{
    need(argc==4,"case archive fixture-folder");std::string name;for(auto ch=argv[1];*ch;++ch){need(*ch<128,"ascii case");name+=char(*ch);}
    fs::path folder(argv[3]);fs::create_directories(folder);fs::path target=folder/p::TargetWideName;need(!fs::exists(target),"fixture directory new");fs::copy_file(fs::path(argv[2]),target);
    Store store;Context c;initialize(c,store,folder,name);p::Evidence e{};c.e=&e;
    if(name=="wrong_hash"){std::fstream f(target,std::ios::binary|std::ios::in|std::ios::out);f.seekp(500);f.put('X');f.close();initialize(c,store,folder,name);c.e=&e;}
    if(name=="wrong_identity")++c.input.expectedStage.indexLow;
    if(name=="missing_owner_binding")std::memset(c.input.ownerBinding,0,32);
    if(name=="existing_intent"){std::ofstream f(c.intent);f<<"old durable intent";}
    if(name=="intent_missing_directory"){c.intent=(folder/L"missing"/L"publish-once.intent").wstring();c.input.intentPath=c.intent.c_str();}
    if(name=="wrong_basename"){c.local=(folder/L"wrong.s14").wstring();c.input.localPath=c.local.c_str();}
    bool result=false;
    if(name=="concurrent_publish"){
        Context other;initialize(other,store,folder,name);p::Evidence second{};other.e=&second;std::atomic<bool>go{false};
        std::thread a([&]{while(!go)std::this_thread::yield();result=p::Publish(c.input,c.api,e);});
        bool secondResult=false;std::thread b([&]{while(!go)std::this_thread::yield();secondResult=p::Publish(other.input,other.api,second);});go=true;a.join();b.join();
        need(e.writeAttempts+second.writeAttempts<=1&&store.writes<=1,"concurrent intent at most one native call");need(e.intentDurable||second.intentDurable,"one durable claimant");need(!(result&&secondResult),"cannot both succeed");
    }else{
        result=p::Publish(c.input,c.api,e);
        bool expected=name=="success"||name=="reentrant_publish";need(result==expected,"expected publication result");
        need(e.writeAttempts<=1&&store.writes==e.writeAttempts,"one write attempt count");
        if(result)need(e.state==p::State::Matched&&e.readbackAttempts==1&&e.readback.readCalls==2&&store.reads==2,"two exact readbacks required");
        if(e.writeAttempts&&!result)need(e.state==p::State::Uncertain&&e.intentDurable,"write failure is uncertain with persistent intent");
        if(name=="cancel_after_intent")need(e.intentDurable&&e.writeAttempts==0&&e.state==p::State::Uncertain,"cancel burns intent before write");
        if(name=="native_present_after_intent")need(e.intentDurable&&e.writeAttempts==0,"post-intent collision does not write");
    }
    auto previous=store.writes.load();
    if(e.intentCreated||name=="existing_intent"||name=="concurrent_publish"){
        // A fresh context represents reopening after lost response/crash. Even
        // with native absence again, the same intent never permits another call.
        store.visible=false;Context reopened;initialize(reopened,store,folder,"reopen");p::Evidence again{};reopened.e=&again;
        need(!p::Publish(reopened.input,reopened.api,again)&&again.writeAttempts==0&&store.writes==previous,"reopen cannot retry existing intent");
        need(fs::exists(c.intent),"intent is never deleted");
    }
    need(!e.nativeLoadAuthorized&&!e.metadataRegistered,"no load or metadata grant");
    printf("{\"passed\":true,\"matched\":%s,\"state\":%u,\"write_attempts\":%u,\"write_returned\":%u,\"intent_durable\":%s,\"local_pin_released\":%s,\"readback_attempts\":%u,\"native_reads\":%u,\"exception\":%u,\"native_calls_are_fixture_stubs\":true}\n",result?"true":"false",unsigned(e.state),e.writeAttempts,e.writeReturned,e.intentDurable?"true":"false",e.localPinReleased?"true":"false",e.readbackAttempts,e.readback.readCalls,e.exceptionCode);return 0;
}catch(const std::exception&e){fprintf(stderr,"FAIL %s\n",e.what());return 1;}catch(...){fputs("FAIL unknown\n",stderr);return 2;}}
