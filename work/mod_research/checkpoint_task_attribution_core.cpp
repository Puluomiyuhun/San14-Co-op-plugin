#include "checkpoint_task_attribution_core.h"
#include <cstring>
#include <limits>
namespace checkpoint_task_attribution {
thread_local Execution* Core::current_=nullptr;
namespace {
struct Guard {SRWLOCK* p;explicit Guard(SRWLOCK* v):p(v){AcquireSRWLockExclusive(p);}~Guard(){ReleaseSRWLockExclusive(p);}};
bool embedded(Kind k){return unsigned(k)>=unsigned(Kind::EmbeddedLoad);}
std::uint64_t createRva(Kind k){switch(k){case Kind::EmbeddedLoad:return 0x4DA2EF;case Kind::Title520:return 0x4BEEBD;case Kind::Title590:return 0x4BEF26;default:return 0x50B598;}}
std::uint64_t offset(Kind k){switch(k){case Kind::EmbeddedLoad:return 0x478;case Kind::Title520:return 0x520;case Kind::Title590:return 0x590;default:return 0;}}
std::uint64_t payload(Kind k){switch(k){case Kind::EmbeddedLoad:return 0x508B40;case Kind::Title520:return 0x4DA390;case Kind::Title590:return 0x466600;default:return 0x50B730;}}
std::uint64_t completionRva(Kind k){switch(k){case Kind::EmbeddedLoad:return 0x4F7079;case Kind::Title520:return 0x4AAF64;case Kind::Title590:return 0x4AAF89;default:return 0x50B632;}}
}
bool Core::reject(Error e) noexcept {++report_.rejected;report_.lastError=e;return false;}
bool Core::Initialize(std::uint64_t b) noexcept {
    if(InterlockedCompareExchange(&once_,1,0))return false;
    if(!b||b>(std::numeric_limits<std::uint64_t>::max)()-0x3000000){InterlockedExchange(&once_,-1);return false;}
    HMODULE module=nullptr;static const unsigned anchor=0x5441534B;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCWSTR>(&anchor),&module)){InterlockedExchange(&once_,-1);return false;}
    base_=b;report_.initialized=1;InterlockedExchange(&once_,2);return true;
}
bool Core::RegisterGeneration(const Generation& g) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);
    unsigned char bits=0;for(auto x:g.attachment)bits|=x;
    if(!g.callbacks.id||!g.attempt||!g.epoch||!bits||!g.callbacks.finally||!g.callbacks.before)return reject(Error::Generation);
    for(unsigned i=0;i<report_.generations;i++)if(generations_[i].callbacks.id==g.callbacks.id)return reject(Error::Duplicate);
    if(report_.generations==16)return reject(Error::Capacity);
    generations_[report_.generations++]=g;return true;
}
Core::Task* Core::task(Ticket& t) noexcept {
    if(t.core_!=this||!t.serial_||t.index_>=report_.tasks||tasks_[t.index_].c.serial!=t.serial_)return nullptr;
    return &tasks_[t.index_];
}
bool Core::RecordCreation(std::uint64_t generation,const Creation& c,Ticket& ticket) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);
    unsigned gi=0;for(;gi<report_.generations;gi++)if(generations_[gi].callbacks.id==generation)break;
    if(gi==report_.generations)return reject(Error::Generation);
    if(ticket.core_||unsigned(c.kind)>unsigned(Kind::Title590)||!c.serial||c.serial<=lastSerial_||!c.state||!c.worker||!c.callable||
       !c.workerThread||c.parentThread!=GetCurrentThreadId()||c.workerThread==c.parentThread||c.creationSite!=base_+createRva(c.kind)||c.payload!=base_+payload(c.kind))return reject(Error::Receipt);
    if(embedded(c.kind)){
        if(c.selectionSite||c.formalSlot||c.state>UINT64_MAX-offset(c.kind)||c.worker!=c.state+offset(c.kind))return reject(Error::Receipt);
    }else if(c.selectionSite!=base_+0x50B4B3||!c.formalSlot)return reject(Error::Receipt);
    for(unsigned i=0;i<report_.tasks;i++)if(!tasks_[i].completed&&(tasks_[i].c.worker==c.worker||tasks_[i].c.callable==c.callable))return reject(Error::Duplicate);
    if(report_.tasks==256)return reject(Error::Capacity);
    const unsigned index=report_.tasks++;tasks_[index].c=c;tasks_[index].generation=gi;
    ticket.core_=this;ticket.index_=index;ticket.serial_=c.serial;lastSerial_=c.serial;++report_.created;return true;
}
bool Core::RecordYield(Ticket& t,std::uint64_t site,DWORD workerThread) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);auto* v=task(t);
    if(!v)return reject(Error::Ticket);
    if(embedded(v->c.kind)||v->completed||v->abnormal||!v->active||v->yielded||site!=base_+0x50B690||workerThread!=GetCurrentThreadId()||workerThread!=v->c.workerThread)return reject(Error::Receipt);
    v->yielded=true;return true;
}
bool Core::RecordResume(Ticket& t,std::uint64_t site,DWORD parentThread) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);auto* v=task(t);
    if(!v)return reject(Error::Ticket);
    if(embedded(v->c.kind)||v->completed||v->abnormal||!v->active||!v->yielded||site!=base_+0x50B4AE||parentThread!=GetCurrentThreadId()||parentThread!=v->c.parentThread)return reject(Error::Receipt);
    v->yielded=false;++report_.resumed;return true;
}
bool Core::Enter(Ticket& t,const Entry& e,Execution& x) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);auto* v=task(t);
    if(!v)return reject(Error::Ticket);
    if(x.used_||v->started||v->active||v->completed||v->abnormal||v->returned)return reject(Error::Scope);
    if(e.serial!=v->c.serial||e.thread!=GetCurrentThreadId()||e.thread!=v->c.workerThread||e.state!=v->c.state||e.worker!=v->c.worker||e.callable!=v->c.callable||
       e.site!=base_+(embedded(v->c.kind)?0x4FABC0:0x50B730)||e.caller!=base_+0x834D9B)return reject(Error::Receipt);
    x.core_=this;x.previous_=current_;x.index_=t.index_;x.thread_=e.thread;x.used_=x.active_=true;current_=&x;
    v->started=v->active=true;v->yielded=v->resume=false;++report_.entered;++report_.activeExecutions;return true;
}
bool Core::Leave(Execution& x,Outcome outcome) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);
    if(x.core_!=this||!x.active_||x.thread_!=GetCurrentThreadId()||current_!=&x||unsigned(outcome)>unsigned(Outcome::Abnormal))return reject(Error::Scope);
    auto& v=tasks_[x.index_];v.active=false;v.yielded=false;v.returned=outcome==Outcome::Returned;v.abnormal=outcome==Outcome::Abnormal;
    if(v.returned)++report_.returned;if(v.abnormal)++report_.abnormal;
    --report_.activeExecutions;x.active_=false;current_=x.previous_;return true;
}
bool Core::RecordCompletion(Ticket& t,const Completion& c) noexcept {
    if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);auto* v=task(t);
    if(!v)return reject(Error::Ticket);
    if(v->completed||v->active||v->abnormal||!v->returned||c.serial!=v->c.serial||c.site!=base_+completionRva(v->c.kind)||c.worker!=v->c.worker||c.callable!=v->c.callable||
       c.thread!=GetCurrentThreadId()||(!embedded(v->c.kind)&&c.thread!=v->c.parentThread)||
       (embedded(v->c.kind)&&c.thread==v->c.workerThread)||c.attached||c.done!=1||c.yielded)return reject(Error::Receipt);
    v->completed=true;++report_.completed;return true;
}
bool Core::Select(Selection& s) noexcept {
    s={};if(InterlockedCompareExchange(&once_,0,0)!=2)return false;Guard lock(&lock_);
    auto* x=current_;if(!x||x->core_!=this||!x->active_||x->thread_!=GetCurrentThreadId())return false;
    const auto& v=tasks_[x->index_];if(!v.active||v.yielded||v.completed||v.abnormal)return false;
    const auto& g=generations_[v.generation];s.callbacks=g.callbacks;s.serial=v.c.serial;s.attempt=g.attempt;s.epoch=g.epoch;s.state=v.c.state;s.callable=v.c.callable;s.kind=v.c.kind;return true;
}
void Core::Snapshot(Report& r) noexcept {r={};if(InterlockedCompareExchange(&once_,0,0)!=2)return;Guard lock(&lock_);r=report_;}
}
