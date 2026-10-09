#include "b_warm_profile.h"
#include "b_warm_retire_session.h"
#include <cstdio>
#include <cstring>

namespace bp=b_warm_profile;
using Fn=DWORD(WINAPI*)(void*);
static unsigned failures=0;
static void check(bool ok,const char* why){if(!ok){++failures;printf("FAIL %s\n",why);}}
static Fn entry(HMODULE m,const char*n){auto f=reinterpret_cast<Fn>(GetProcAddress(m,n));check(f!=nullptr,n);return f;}
static bp::Profile profile(unsigned bank){
    bp::Profile p{};strcpy_s(p.file.name,"svdexccSC03.s14");p.file.slot=63;p.file.size=1024+bank;
    memset(p.file.sha256,int(0x31+bank),32);p.before={203,8,11};p.loaded={203,8,static_cast<BYTE>(bank?21:11)};
    p.source={666,12,11};p.target={952,2,2};p.currentForce=bank?2:12;return p;
}
int wmain(int argc,wchar_t**argv){
    if(argc!=4)return 2;
    // Only private production DLL copies in this child process. No process
    // discovery, remote thread, game memory handle or hook installation.
    HMODULE a=LoadLibraryExW(argv[1],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);
    HMODULE b=LoadLibraryExW(argv[2],nullptr,LOAD_WITH_ALTERED_SEARCH_PATH);
    check(a&&b&&a!=b,"two physically distinct resident modules");if(!a||!b||a==b)return 1;
    Fn describe[2]{entry(a,"DescribeBWarmProfileOwner"),entry(b,"DescribeBWarmProfileOwner")};
    Fn install[2]{entry(a,"InstallBWarmProfileOwner"),entry(b,"InstallBWarmProfileOwner")};
    Fn report[2]{entry(a,"GetBWarmProfileReport"),entry(b,"GetBWarmProfileReport")};
    Fn retire[2]{entry(a,"GetBWarmRetireReport"),entry(b,"GetBWarmRetireReport")};
    Fn ownerReport[2]{entry(a,"GetCheckpointCompleteLiveOwnerReport"),entry(b,"GetCheckpointCompleteLiveOwnerReport")};
    Fn stop=entry(a,"StopCheckpointCompleteLiveOwner");if(failures)return 1;
    bp::Description d[2]{};bp::Report r[2]{};b_warm_retire::Report rr[2]{};
    for(unsigned i=0;i<2;++i){
        check(!describe[i](&d[i])&&!report[i](&r[i])&&!retire[i](&rr[i]),"actual typed describe/report");
        check(d[i].magic==bp::Magic&&d[i].size==sizeof d[i]&&d[i].configSize==sizeof(bp::Config)&&d[i].profileSize==sizeof(bp::Profile)&&d[i].reportSize==sizeof(bp::Report),"description native layout");
        check(d[i].bank.module==uintptr_t(i?b:a),"description belongs to exact module");
        check(!r[i].configured&&!r[i].ready&&!r[i].error&&!rr[i].bound&&!rr[i].sealed,"independent initial states");
        check(describe[i](nullptr)!=0&&report[i](nullptr)!=0&&retire[i](nullptr)!=0,"null outputs refused");
    }
    check(d[0].bank.dispatchBridge[0]!=d[1].bank.dispatchBridge[0],"immutable separate physical bridge addresses");
    bp::Config c{};c.profile=profile(0);memset(c.profile.file.sha256,0,32);
    check(install[0](&c)!=0&&!report[0](&r[0]),"bad profile rejected");
    check(r[0].configured&&!r[0].ready&&r[0].error,"failed profile attempt is terminal");
    c.profile=profile(0);check(install[0](&c)!=0,"cannot reset first bank once");
    check(!report[1](&r[1])&&!r[1].configured,"first attempt never configures second bank");
    check(!stop(nullptr),"first bank Stop returns");
    checkpoint_complete_live_owner::Report owner{};check(!ownerReport[1](&owner)&&!owner.value[unsigned(checkpoint_complete_live_owner::Value::StopRequested)],"Stop remains local to first bank");
    c.profile=profile(1);check(install[1](&c)!=0,"unbound owner rejected despite valid data profile");
    check(!report[1](&r[1])&&r[1].configured&&r[1].ready&&!r[1].error&&!memcmp(&r[1].profile,&c.profile,sizeof c.profile),"second independent profile captured exactly");
    c.profile.file.sha256[0]^=1;check(install[1](&c)!=0,"second profile also immutable");
    check(!report[1](&r[1])&&r[1].profile.file.sha256[0]!=c.profile.file.sha256[0],"failed retry did not change second profile");
    for(unsigned i=0;i<2;++i){check(!retire[i](&rr[i])&&!rr[i].bound&&!rr[i].sealed,"no fabricated load completion");check(!ownerReport[i](&owner)&&!owner.value[unsigned(checkpoint_complete_live_owner::Value::Armed)]&&!owner.value[unsigned(checkpoint_complete_live_owner::Value::CasPublished)],"no hooks or requests armed");}
    FILE*out=nullptr;check(!_wfopen_s(&out,argv[3],L"wb")&&out,"binary reports output");
    if(out){check(fwrite(d,sizeof d,1,out)==1&&fwrite(r,sizeof r,1,out)==1&&fwrite(rr,sizeof rr,1,out)==1,"reports written");fclose(out);}
    // No FreeLibrary: each bank's code and static data stay resident to exit.
    printf("{\"passed\":%s,\"two_modules\":true,\"successful_loads\":0,\"game_access\":false}\n",failures?"false":"true");return failures?1:0;
}
