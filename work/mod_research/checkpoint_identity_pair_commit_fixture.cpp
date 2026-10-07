#include "checkpoint_identity_pair_commit.h"
#include <cstdio>
#include <cstring>
#include <string>
using namespace checkpoint_identity_pair_commit;
static std::wstring scenario;
static unsigned checks=0,failures=0;
static Pair other{0x9999000011110000ull,0xAAAA000022220000ull};
static void check(bool ok,const char*message){++checks;if(!ok){++failures;std::printf("FAIL %s\n",message);}}
static bool equal(Pair a,Pair b){return a.force==b.force&&a.person==b.person;}
static bool validate(void*,Point point,const Input&in){
    if(scenario==L"reject-before"&&point==Point::Preflight)return false;
    if(scenario==L"reject-intent"&&point==Point::BeforeIntent)return false;
    if(scenario==L"reject-commit"&&point==Point::BeforeCompareExchange)return false;
    if(scenario==L"reject-after"&&point==Point::AfterCompareExchange)return false;
    if(scenario==L"guard-seh"&&point==Point::Preflight)RaiseException(0xE0143011,0,0,nullptr);
    if(scenario==L"after-seh"&&point==Point::AfterCompareExchange)RaiseException(0xE0143012,0,0,nullptr);
    if(scenario==L"cas-conflict"&&point==Point::BeforeCompareExchange)*in.destination=other;
    return true;
}
int wmain(int argc,wchar_t**argv){
    if(argc!=3)return 2;scenario=argv[1];SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);
    auto page=static_cast<unsigned char*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    if(!page)return 3;memset(page,0xA5,4096);
    Pair*pair=reinterpret_cast<Pair*>(page+0x4A0);
    Input in{};in.destination=pair;in.source={0x1111222233334444ull,0x5555666677778888ull};
    in.target={0x123456789ABCDEF0ull,0xFEDCBA9876543210ull};*pair=in.source;
    in.attempt=123;in.callId=5;in.thread=GetCurrentThreadId();in.intentPath=argv[2];memset(in.ownerBinding,0x5A,32);
    if(scenario==L"wrong-thread")++in.thread;
    if(scenario==L"wrong-source")*pair=other;
    if(scenario==L"null")in.destination=nullptr;
    if(scenario==L"unaligned")in.destination=reinterpret_cast<Pair*>(page+0x4A8);
    if(scenario==L"zero-owner")memset(in.ownerBinding,0,32);
    if(scenario==L"same-target")in.target=in.source;
    wchar_t unterminated[1024];for(auto&c:unterminated)c=L'x';
    void*badPath=nullptr;
    if(scenario==L"path-no-terminator")in.intentPath=unterminated;
    if(scenario==L"path-unreadable"){
        badPath=VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_NOACCESS);
        in.intentPath=reinterpret_cast<const wchar_t*>(badPath);
    }
    DWORD old=0;if(scenario==L"readonly")check(VirtualProtect(page,4096,PAGE_READONLY,&old)!=FALSE,"set readonly");
    if(scenario==L"existing-intent"){
        HANDLE f=CreateFileW(argv[2],GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
        check(f!=INVALID_HANDLE_VALUE,"prior intent");if(f!=INVALID_HANDLE_VALUE)CloseHandle(f);
    }
    Committer commit;Access access{nullptr,validate};bool ok=commit.Commit(in,access);
    Report r=commit.GetReport();
    const bool applied=scenario==L"success"||scenario==L"repeat"||scenario==L"reject-after"||scenario==L"after-seh";
    const bool success=scenario==L"success"||scenario==L"repeat";
    check(ok==success,"result classification");check(r.casApplied==unsigned(applied),"atomic applied classification");
    check(equal(*pair,applied?in.target:(scenario==L"cas-conflict"||scenario==L"wrong-source")?other:in.source),"observed pair exact");
    check(r.casAttempts<=1,"at most one cmpxchg16b");
    for(unsigned i=0;i<4096;++i)if(i<0x4A0||i>=0x4B0)check(page[i]==0xA5,"adjacent bytes untouched");
    if(applied)check(r.intentCreated&&r.intentDurable&&r.casAttempts==1,"intent precedes actual commit");
    if(success)check(r.state==State::PairCommitted&&r.postGuard&&equal(r.observed,in.target),"complete pair receipt");
    if(scenario==L"cas-conflict")check(r.state==State::NotApplied&&!r.casApplied&&equal(r.observed,other)&&r.intentDurable,"conflict not applied, no rollback");
    if(scenario==L"reject-commit")check(r.state==State::Uncertain&&r.intentDurable&&r.casAttempts==0,"late guard consumes intent");
    if(scenario==L"reject-after"||scenario==L"after-seh")check(r.state==State::Uncertain&&r.casApplied&&!r.postGuard,"late failure keeps committed pair");
    if(scenario==L"guard-seh"||scenario==L"after-seh")check(r.exceptionCode==(scenario==L"guard-seh"?0xE0143011u:0xE0143012u),"guard exception observed");
    if(scenario==L"path-unreadable")check(r.exceptionCode==EXCEPTION_ACCESS_VIOLATION&&!r.intentCreated&&r.casAttempts==0,"bad path fails before intent");
    if(scenario==L"path-no-terminator")check(!r.intentCreated&&r.casAttempts==0,"bounded path rejects");
    if(scenario==L"repeat"){
        check(!commit.Commit(in,access),"second Commit returns false");
        check(commit.GetReport().casAttempts==1&&equal(*pair,in.target),"repeat cannot commit again");
        Committer restarted;in.source=in.target;in.target=other;
        check(!restarted.Commit(in,access)&&restarted.GetReport().casAttempts==0,"durable intent blocks fresh object retry");
    }
    check(!r.worldInitialized&&!r.planningReady,"no initializer or readiness claim");
    std::printf("{\"case\":\"%ls\",\"passed\":%s,\"checks\":%u,\"failures\":%u,\"state\":%u,\"cas_attempts\":%u,\"cas_applied\":%u,\"game_access\":false}\n",
        scenario.c_str(),failures?"false":"true",checks,failures,unsigned(r.state),r.casAttempts,r.casApplied);
    if(badPath)VirtualFree(badPath,0,MEM_RELEASE);
    VirtualFree(page,0,MEM_RELEASE);return failures?1:0;
}
