#include "checkpoint_session_generation_owner.h"
#include <cstring>
namespace checkpoint_session_generation {
static bool inModule(HMODULE m,const void* p){HMODULE found=nullptr;return p&&GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,reinterpret_cast<LPCWSTR>(p),&found)&&found==m;}
static bool active(const ns::Report&r){if(r.requestInFlight||r.activeDispatch||r.activeWorker||r.activeRead||r.workerStats.active||r.readStats.active)return true;for(const auto&s:r.dispatchStats)if(s.active)return true;return false;}
static bool abnormal(const ns::Report&r){if(r.workerStats.abnormal_exits||r.readStats.abnormal_exits||r.workerStats.cleanup_faults||r.readStats.cleanup_faults)return true;for(const auto&s:r.dispatchStats)if(s.abnormal_exits)return true;return false;}
bool Owner::fail(Error e) noexcept {error_=e;return false;}
bool Owner::enter() noexcept {if(GetCurrentThreadId()!=thread_)return false;if(InterlockedCompareExchange(&busy_,1,0))return fail(Error::Busy);return true;}
void Owner::leave() noexcept {InterlockedExchange(&busy_,0);}
bool Owner::Prepare(HMODULE m,const Identity&i,const ns::Config&c) noexcept {
    if(!enter())return false;bool ok=false;__try {__try {ok=prepare(m,i,c);}__except(EXCEPTION_EXECUTE_HANDLER){exception_=GetExceptionCode();fail(Error::Memory);}}__finally{leave();}return ok;
}
bool Owner::prepare(HMODULE m,const Identity&id,const ns::Config&c){
    if(count_>=Capacity)return fail(Error::Capacity);
    unsigned char sum=0;for(auto x:id.attachment)sum|=x;
    if(!m||!id.generation||!id.attempt||!sum||id.attempt!=c.request.boundary.attempt||std::memcmp(id.attachment,c.request.ownerBinding,32))return fail(Error::Binding);
    for(unsigned j=0;j<count_;++j){const auto&old=banks_[j];if(m==old.module||id.attempt==old.description.identity.attempt)return fail(Error::Duplicate);}
    if(count_){const auto&old=banks_[count_-1].description;if(old.identity.generation==UINT64_MAX||id.generation!=old.identity.generation+1||std::memcmp(id.attachment,old.identity.attachment,32))return fail(Error::Binding);
        for(unsigned k=0;k<6;++k)if(c.hooks[k].slot!=old.hooks[k].slot||c.hooks[k].original!=old.hooks[k].original)return fail(Error::Binding);
    }
    auto get=reinterpret_cast<GetBankApi>(GetProcAddress(m,"CheckpointSessionGenerationGetApi"));
    if(!get||!inModule(m,reinterpret_cast<void*>(get)))return fail(Error::Module);
    const auto*api=get();if(!api||!inModule(m,api)||api->size!=sizeof(BankApi)||api->version!=BankAbi||api->configBytes!=sizeof(ns::Config)||api->reportBytes!=sizeof(ns::Report))return fail(Error::Module);
    const void* funcs[]={reinterpret_cast<void*>(api->initialize),reinterpret_cast<void*>(api->describe),reinterpret_cast<void*>(api->arm),reinterpret_cast<void*>(api->stop),reinterpret_cast<void*>(api->restoreBeforeCommit),reinterpret_cast<void*>(api->snapshot),reinterpret_cast<void*>(api->bindQueuedMenu)};
    for(auto f:funcs)if(!inModule(m,f))return fail(Error::Module);
    for(const auto&b:c.hooks){if(!b.slot||!b.original||inModule(m,b.original))return fail(Error::Binding);for(unsigned j=0;j<count_;++j)if(inModule(banks_[j].module,b.original))return fail(Error::Binding);}
    HMODULE pinned=nullptr;if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(get),&pinned)||pinned!=m)return fail(Error::Module);
    // Capacity is consumed before any configuration. Failed partially initialized
    // banks remain pinned and cannot be recycled as another generation.
    auto&b=banks_[count_++];b.module=m;b.api=api;b.pinned=true;b.state=State::Failed;b.description.identity=id;
    if(!api->initialize(&id,&c))return fail(Error::Initialize);
    if(!api->describe(&b.description)||std::memcmp(&b.description.identity,&id,sizeof id)||!inModule(m,b.description.session))return fail(Error::Describe);
    for(unsigned k=0;k<6;++k){const auto&h=b.description.hooks[k];if(h.slot!=c.hooks[k].slot||h.original!=c.hooks[k].original||!inModule(m,h.hook))return fail(Error::Describe);
        for(unsigned n=0;n<k;++n)if(h.hook==b.description.hooks[n].hook)return fail(Error::Describe);
    }
    ns::Report r{};api->snapshot(&r);if(!r.initialized||r.armed||r.error||r.attempt!=id.attempt||r.casPublished||r.mayHavePublished||active(r))return fail(Error::Initialize);
    b.state=State::Prepared;return true;
}
bool Owner::Activate(unsigned index) noexcept {if(!enter())return false;bool ok=false;__try {__try {ok=activate(index);}__except(EXCEPTION_EXECUTE_HANDLER){exception_=GetExceptionCode();fail(Error::Memory);}}__finally{leave();}return ok;}
bool Owner::activate(unsigned index){
    if(index>=count_||banks_[index].state!=State::Prepared||index!=unsigned(driving_+1))return fail(Error::NotNext);
    if(driving_>=0){auto&old=banks_[driving_];old.api->stop();old.state=State::StoppedRetained;
        ns::Report r{};old.api->snapshot(&r);
        if(r.casPublished||r.mayHavePublished)return fail(Error::Published);
        if(active(r))return fail(Error::Active);
        if(r.error||abnormal(r))return fail(Error::Abnormal);
        if(r.menuBound||r.request.menuObserved)return fail(Error::MenuOutstanding);
        if(!old.api->restoreBeforeCommit())return fail(Error::Restore);
        old.api->snapshot(&r);if(!r.hooksRestored||r.casPublished||r.mayHavePublished||active(r))return fail(Error::Restore);
        old.state=State::Restored;
    }
    auto&next=banks_[index];if(!next.api->arm()){next.state=State::Failed;return fail(Error::Arm);}
    ns::Report r{};next.api->snapshot(&r);if(!r.armed||r.error||r.stopRequested){next.api->stop();next.state=State::StoppedRetained;return fail(Error::Arm);}
    driving_=int(index);next.state=State::Driving;return true;
}
bool Owner::StopRetaining(unsigned i) noexcept {if(!enter())return false;bool ok=false;__try {__try{ok=stop(i);}__except(EXCEPTION_EXECUTE_HANDLER){exception_=GetExceptionCode();fail(Error::Memory);}}__finally{leave();}return ok;}
bool Owner::stop(unsigned i){if(i>=count_)return fail(Error::Binding);banks_[i].api->stop();banks_[i].state=State::StoppedRetained;return true;}
bool Owner::Snapshot(Report&out) noexcept {if(!enter())return false;bool ok=false;__try {__try {out={};out.count=count_;out.driving=driving_;out.lastError=error_;out.exception=exception_;
    for(unsigned i=0;i<count_;++i){auto&e=out.entries[i];auto&b=banks_[i];e.identity=b.description.identity;e.state=b.state;e.module=reinterpret_cast<std::uintptr_t>(b.module);e.pinned=b.pinned;b.api->snapshot(&e.session);}ok=true;
    }__except(EXCEPTION_EXECUTE_HANDLER){exception_=GetExceptionCode();fail(Error::Memory);}}__finally{leave();}return ok;}
}
