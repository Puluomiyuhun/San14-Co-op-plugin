#include "checkpoint_load_request_commit.h"
#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <vector>
#include <string>
#include <cstdio>
#include <cstring>
namespace core=checkpoint_load_request_commit;
namespace bounds=checkpoint_load_input_boundary;
using Layout=checkpoint_load_input_boundary_fixture::Layout;
struct Fixture {
    Layout layout;std::vector<unsigned char> bytes;std::string mode;
    unsigned reads=0,writes=0;bool validate=true;
};
static unsigned checks=0,failures=0;
static void check(bool value){++checks;if(!value)++failures;}
static bool exists(void*,const char*name){return !strcmp(name,"svdexccSC03.s14");}
static std::int32_t size(void*,const char*){return 274880;}
static std::int32_t read(void*ctx,const char*,void*destination,std::int32_t n){
    auto& f=*static_cast<Fixture*>(ctx);++f.reads;
    if(n!=274880)return -1;
    if(f.mode=="read-seh")RaiseException(0xE0144141,0,0,nullptr);
    memcpy(destination,f.bytes.data(),f.bytes.size());
    if(f.mode=="read-corrupt")static_cast<unsigned char*>(destination)[273000]^=1;
    return f.mode=="read-short"?n-1:n;
}
static bool storageValid(void*ctx){return static_cast<Fixture*>(ctx)->validate;}
static bool guard(void*ctx,core::Point point){
    auto&f=*static_cast<Fixture*>(ctx);
    if(f.mode=="reject-before-cas"&&point==core::Point::BeforeCas)return false;
    if(f.mode=="reject-after-cas"&&point==core::Point::AfterCas)return false;
    if(f.mode=="pending-after-cas"&&point==core::Point::AfterCas)Layout::put<LONG>(f.layout.config.cache+0x3EC,7);
    if(f.mode=="pending-during-read"&&point==core::Point::AfterRead)Layout::put<LONG>(f.layout.config.cache+0x3EC,7);
    return true;
}
static bool loadFile(const wchar_t* path,std::vector<unsigned char>&bytes){
    HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,0,nullptr);if(h==INVALID_HANDLE_VALUE)return false;
    bytes.resize(274880);DWORD n=0;bool ok=ReadFile(h,bytes.data(),DWORD(bytes.size()),&n,nullptr)&&n==bytes.size();CloseHandle(h);return ok;
}
int wmain(int argc,wchar_t**argv){
    if(argc!=5)return 2;SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    Fixture f;for(const wchar_t*p=argv[1];*p;++p)f.mode.push_back(char(*p));
    if(!f.layout.initialize(bounds::Stage::MenuAfter)||!loadFile(argv[2],f.bytes)||!CopyFileW(argv[2],argv[3],TRUE))return 3;
    core::Config cfg{};cfg.boundary=f.layout.config;cfg.localPath=argv[3];cfg.intentPath=argv[4];cfg.ownerBinding[0]=1;cfg.validate=guard;cfg.context=&f;
    cfg.storage={&f,exists,size,read,storageValid,&f};
    core::Committer commit;check(commit.Initialize(cfg));
    if(f.mode=="menu-selection")Layout::put<LONG>(f.layout.list+0x170,4);
    bool menu=false;if(f.mode!="missing-menu")menu=commit.ObserveMenuAfter(f.layout.call);
    if(f.mode=="menu-selection")check(!menu);else if(f.mode!="missing-menu")check(menu);
    f.layout.setStage(bounds::Stage::GameBefore);f.layout.call.callId=f.layout.call.pairedCallId=19;
    if(f.mode=="busy-user")Layout::put<std::uintptr_t>(f.layout.config.states[4]+0x50,f.layout.worker+0x1000);
    if(f.mode=="pending-before")Layout::put<LONG>(f.layout.config.cache+0x3EC,2);
    if(f.mode=="wrong-thread")++f.layout.call.thread;
    if(f.mode=="storage-changed")f.validate=false;
    if(f.mode=="existing-intent") {HANDLE h=CreateFileW(argv[4],GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);check(h!=INVALID_HANDLE_VALUE);if(h!=INVALID_HANDLE_VALUE)CloseHandle(h);}
    const bool ok=commit.CommitGameBefore(f.layout.call);const auto&r=commit.GetReport();const auto pending=Layout::get<LONG>(f.layout.config.cache+0x3EC);
    if(f.mode=="success"){
        check(ok);check(r.state==core::State::PendingCommitted&&r.casAttempts==1&&r.casApplied==1&&r.intentDurable&&r.postGuard&&r.read.matched&&f.reads==2&&pending==63);
        check(!commit.CommitGameBefore(f.layout.call));check(f.reads==2&&r.casAttempts==1&&pending==63);
    }else if(f.mode=="reject-after-cas"||f.mode=="pending-after-cas")check(!ok&&r.state==core::State::Uncertain&&r.casApplied==1&&pending==(f.mode=="pending-after-cas"?7:63)&&!r.postGuard);
    else {
        check(!ok&&r.casAttempts==0&&r.casApplied==0);
        check(pending==(f.mode=="pending-before"?2:f.mode=="pending-during-read"?7:-1));
        if(f.mode=="reject-before-cas")check(r.intentDurable&&r.state==core::State::Uncertain);
        if(f.mode=="read-seh")check(r.read.exceptionCode==0xE0144141);
    }
    check(!r.worldLoaded&&!r.identityRestored&&!r.planningReady);
    std::printf("{\"case\":\"%s\",\"passed\":%s,\"checks\":%u,\"failures\":%u,\"state\":%u,\"stage\":\"%s\",\"boundary_error\":%u,\"reads\":%u,\"cas_attempts\":%u,\"cas_applied\":%u,\"game_access\":false}\n",f.mode.c_str(),failures?"false":"true",checks,failures,unsigned(r.state),r.stage,unsigned(r.boundary.error),f.reads,r.casAttempts,r.casApplied);
    return failures?1:0;
}
