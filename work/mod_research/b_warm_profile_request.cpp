#include "b_warm_profile.h"
static const b_warm_profile::Profile& wp() noexcept {return b_warm_profile::Get();}
#include "checkpoint_load_request_commit.h"
#include <cstring>
#include <cwchar>
namespace checkpoint_load_request_commit {
namespace boundary=checkpoint_load_input_boundary;
namespace {
bool copyPath(const wchar_t* source,wchar_t* target) {
    if(!source||!*source)return false;
    for(unsigned i=0;i<512;++i){target[i]=source[i];if(!target[i])return true;}
    return false;
}
bool writable(volatile LONG*p){
    MEMORY_BASIC_INFORMATION m{};const auto address=reinterpret_cast<std::uintptr_t>(p);
    return address>=0x10000&&!(address&3)&&VirtualQuery(const_cast<LONG*>(p),&m,sizeof m)==sizeof m&&m.State==MEM_COMMIT&&
        (m.Protect==PAGE_READWRITE||m.Protect==PAGE_WRITECOPY)&&address+sizeof(LONG)<=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize;
}
}
bool Committer::Initialize(const Config&c) noexcept {
    if(InterlockedCompareExchange(&initialized_,1,0))return false;
    __try{
        config_=c;unsigned char nonzero=0;for(auto b:c.ownerBinding)nonzero|=b;
        if(!b_warm_profile::Ready()||!c.validate||!c.boundary.attempt||!c.boundary.cache||!nonzero||!c.storage.storage||!c.storage.exists||!c.storage.size||!c.storage.read||!c.storage.validate||
           !copyPath(c.localPath,localPath_)||!copyPath(c.intentPath,intentPath_))return false;
        config_.localPath=localPath_;config_.intentPath=intentPath_;report_.attempt=c.boundary.attempt;
        report_.state=State::Initialized;report_.stage="initialized";InterlockedExchange(&initialized_,2);return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();report_.state=State::Rejected;return false;}
}
bool Committer::guard(Point p) noexcept {
    __try {return config_.validate(config_.context,p);}
    __except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();return false;}
}
bool Committer::inspect() noexcept {
    return activeCall_&&boundary::Inspect(config_.boundary,*activeCall_,report_.boundary);
}
bool Committer::ObserveMenuAfter(const boundary::Call&call) noexcept {
    if(InterlockedCompareExchange(&initialized_,0,0)!=2||InterlockedCompareExchange(&menuOnce_,1,0))return false;
    ++report_.menuCalls;activeCall_=&call;
    const bool ok=call.stage==boundary::Stage::MenuAfter&&guard(Point::MenuReceipt)&&inspect();
    activeCall_=nullptr;
    if(!ok){report_.state=State::Rejected;report_.stage="menu_receipt_rejected";InterlockedExchange(&menuOnce_,3);return false;}
    report_.menuObserved=true;report_.menuCall=call.callId;report_.menuThread=call.thread;
    report_.state=State::MenuObserved;report_.stage="menu_native_pause_observed";InterlockedExchange(&menuOnce_,2);return true;
}
bool Committer::validateStorage(void*context) noexcept {
    auto& self=*static_cast<Committer*>(context);
    __try{return self.guard(Point::BeforeRead)&&self.inspect()&&self.config_.storage.validate(self.config_.storage.validationContext);}
    __except(EXCEPTION_EXECUTE_HANDLER){self.report_.exceptionCode=GetExceptionCode();return false;}
}
bool Committer::reserve() noexcept {
    struct Intent {char magic[32];std::uint32_t version,size,pid,thread;std::uint64_t attempt,game,menu,cache,menuCall,gameCall;LONG before,after;unsigned char owner[32],sha[32];};
    Intent data{};memcpy(data.magic,"san14.load.slot63.intent.v1",26);data.version=1;data.size=sizeof data;
    data.pid=GetCurrentProcessId();data.thread=GetCurrentThreadId();data.attempt=config_.boundary.attempt;
    data.game=config_.boundary.states[2];data.menu=config_.boundary.menu;data.cache=config_.boundary.cache;
    data.menuCall=report_.menuCall;data.gameCall=report_.gameCall;data.before=-1;data.after=63;
    memcpy(data.owner,config_.ownerBinding,32);memcpy(data.sha,wp().file.sha256,32);
    HANDLE file=CreateFileW(config_.intentPath,GENERIC_WRITE,FILE_SHARE_READ,nullptr,CREATE_NEW,FILE_FLAG_WRITE_THROUGH|FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE){report_.osError=GetLastError();return false;}
    report_.intentCreated=true;DWORD count=0;
    bool ok=WriteFile(file,&data,sizeof data,&count,nullptr)&&count==sizeof data&&FlushFileBuffers(file);
    if(!ok)report_.osError=GetLastError();
    if(!CloseHandle(file)){if(!report_.osError)report_.osError=GetLastError();ok=false;}
    report_.intentDurable=ok;return ok;
}
bool Committer::CommitGameBefore(const boundary::Call&call) noexcept {
    if(InterlockedCompareExchange(&initialized_,0,0)!=2||InterlockedCompareExchange(&gameOnce_,1,0))return false;
    ++report_.gameCalls;report_.gameCall=call.callId;report_.gameThread=call.thread;activeCall_=&call;
    bool ok=false;
    __try {__try {
        report_.stage="game_before_preflight";
        if(InterlockedCompareExchange(&menuOnce_,0,0)!=2||report_.state!=State::MenuObserved||!report_.menuObserved||call.stage!=boundary::Stage::GameBefore||!guard(Point::Preflight)||!inspect())__leave;
        report_.stage="fresh_complete_native_reads";
        native_storage_read::Input input{};input.localPath=config_.localPath;input.basename=wp().file.name;input.expectedSize=wp().file.size;memcpy(input.expectedSha256,wp().file.sha256,32);
        auto api=config_.storage;api.validate=&validateStorage;api.validationContext=this;
        ++report_.readAttempts;
        if(!native_storage_read::Verify(input,api,lease_,report_.read)||!guard(Point::AfterRead)||!inspect())__leave;
        report_.stage="unique_durable_load_intent";
        if(!guard(Point::BeforeIntent)||!inspect()||!reserve())__leave;
        report_.state=State::IntentDurable;
        report_.stage="before_slot_cas";
        auto pending=reinterpret_cast<volatile LONG*>(config_.boundary.cache+0x3EC);
        if(!guard(Point::BeforeCas)||!inspect()||!writable(pending))__leave;
        report_.stage="slot_cas_once";++report_.casAttempts;
        report_.observedPending=InterlockedCompareExchange(pending,63,-1);
        if(report_.observedPending!=-1){report_.state=State::NotApplied;report_.stage="pending_conflict_not_applied";__leave;}
        report_.casApplied=1;
        // Inspect requires -1, so it must not run after our successful CAS.
        // The native original executes immediately after this callback returns.
        report_.stage="pending_committed_native_original_not_yet_called";
        report_.postGuard=*pending==63&&guard(Point::AfterCas)&&*pending==63;
        if(!report_.postGuard)__leave;
        report_.state=State::PendingCommitted;ok=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){report_.exceptionCode=GetExceptionCode();}}
    __finally{activeCall_=nullptr;}
    if(!ok&&report_.state!=State::NotApplied)report_.state=(report_.intentCreated||report_.casAttempts)?State::Uncertain:State::Rejected;
    return ok;
}
}
