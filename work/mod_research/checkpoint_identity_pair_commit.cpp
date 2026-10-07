#include "checkpoint_identity_pair_commit.h"
#include <intrin.h>
#include <cstring>
#include <cwchar>

namespace checkpoint_identity_pair_commit {
namespace {
bool equal(Pair a,Pair b){return a.force==b.force&&a.person==b.person;}
bool guard(const Input&i,const Access&a,Point point,Report&r) noexcept {
    __try{return GetCurrentThreadId()==i.thread&&a.validate(a.context,point,i);}
    __except(EXCEPTION_EXECUTE_HANDLER){r.exceptionCode=GetExceptionCode();return false;}
}
bool inspect(Pair*address,Pair&pair,Report&r) noexcept {
    __try{pair=*address;return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){r.exceptionCode=GetExceptionCode();return false;}
}
bool capture(const Input*source,const Access*access,Input&i,Access&a,wchar_t*path,Report&r) noexcept {
    __try{
        i=*source;a=*access;
        if(!i.intentPath||!*i.intentPath)return false;
        for(unsigned n=0;n<1024;++n){
            path[n]=i.intentPath[n];
            if(!path[n]){i.intentPath=path;return true;}
        }
        return false;
    }__except(EXCEPTION_EXECUTE_HANDLER){r.exceptionCode=GetExceptionCode();return false;}
}
bool writable(Pair*address) noexcept {
    const auto p=reinterpret_cast<std::uintptr_t>(address);MEMORY_BASIC_INFORMATION m{};
    return p>=0x10000&&!(p&15)&&p<=0x00007FFFFFFFFFEFULL&&
        VirtualQuery(address,&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&
        (m.Protect==PAGE_READWRITE||m.Protect==PAGE_WRITECOPY)&&
        p+16<=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize;
}
bool compareExchange(const Input&i,Report&r) noexcept {
    alignas(16) long long observed[2]={static_cast<long long>(i.source.force),static_cast<long long>(i.source.person)};
    __try{
        ++r.casAttempts;
        r.casApplied=_InterlockedCompareExchange128(reinterpret_cast<volatile long long*>(i.destination),
            static_cast<long long>(i.target.person),static_cast<long long>(i.target.force),observed)!=0;
        r.observed={static_cast<std::uint64_t>(observed[0]),static_cast<std::uint64_t>(observed[1])};
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){r.exceptionCode=GetExceptionCode();return false;}
}
struct Intent {
    char magic[32]{};
    std::uint32_t version=1,size=sizeof(Intent),pid=0,thread=0;
    std::uint64_t destination=0,attempt=0,callId=0;
    Pair source{},target{};
    unsigned char ownerBinding[32]{};
};
bool reserve(const Input&i,Report&r) noexcept {
    Intent data{};memcpy(data.magic,"san14.title.pair.intent.v1",26);
    data.pid=GetCurrentProcessId();data.thread=i.thread;data.destination=reinterpret_cast<std::uintptr_t>(i.destination);
    data.attempt=i.attempt;data.callId=i.callId;data.source=i.source;data.target=i.target;memcpy(data.ownerBinding,i.ownerBinding,32);
    HANDLE file=CreateFileW(i.intentPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr);
    if(file==INVALID_HANDLE_VALUE){r.osError=GetLastError();return false;}
    r.intentCreated=true;DWORD count=0;
    bool ok=WriteFile(file,&data,sizeof data,&count,nullptr)&&count==sizeof data&&FlushFileBuffers(file);
    if(!ok)r.osError=GetLastError();
    if(!CloseHandle(file)){if(!r.osError)r.osError=GetLastError();ok=false;}
    r.intentDurable=ok;return ok;
}
}
bool Committer::Commit(const Input&in,const Access&access) noexcept {
    if(InterlockedCompareExchange(&entered_,1,0))return false;
    report_.invocations=1;auto&r=report_;
    // Capture bounded path contents before guard/native work; no borrowed path
    // dereference occurs outside the SEH boundary. Context lifetime is caller-owned.
    Input i{};Access a{};wchar_t path[1024]{};
    auto fail=[&](){r.state=r.intentCreated||r.casAttempts?State::Uncertain:State::Rejected;return false;};
    r.stage="capture_input";if(!capture(&in,&access,i,a,path,r))return fail();
    r.stage="input";unsigned char nonzero=0;for(auto c:i.ownerBinding)nonzero|=c;
    if(!i.destination||!a.validate||
       !i.attempt||!i.callId||!i.thread||!nonzero||!i.source.force||!i.source.person||!i.target.force||!i.target.person||
       equal(i.source,i.target)||i.source.force==i.source.person||i.target.force==i.target.person)return fail();
    r.stage="atomic_instruction_and_target";
    if(!IsProcessorFeaturePresent(PF_COMPARE_EXCHANGE128)||!writable(i.destination))return fail();
    r.stage="owned_native_boundary";if(!guard(i,a,Point::Preflight,r))return fail();
    r.stage="expected_source_pair";if(!inspect(i.destination,r.observed,r)||!equal(r.observed,i.source))return fail();
    r.stage="before_intent_guard";if(!guard(i,a,Point::BeforeIntent,r))return fail();
    r.stage="unique_durable_intent";if(!reserve(i,r))return fail();
    r.state=State::IntentDurable;
    r.stage="before_atomic_commit";if(!guard(i,a,Point::BeforeCompareExchange,r)||!writable(i.destination))return fail();
    r.stage="atomic_compare_exchange_once";if(!compareExchange(i,r))return fail();
    if(!r.casApplied){r.state=State::NotApplied;r.stage="source_changed_not_applied";return false;}
    r.stage="after_atomic_commit";
    if(!inspect(i.destination,r.observed,r)||!equal(r.observed,i.target)||!guard(i,a,Point::AfterCompareExchange,r))return fail();
    r.postGuard=true;r.state=State::PairCommitted;r.stage="pair_committed_initializer_not_called";return true;
}
}
