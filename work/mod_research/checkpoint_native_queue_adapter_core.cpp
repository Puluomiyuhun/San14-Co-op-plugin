#include "checkpoint_native_queue_adapter_core.h"
#include "checkpoint_native_queue_adapter_profile.h"
#include <cstring>
#include <limits>
namespace checkpoint_native_queue_adapter {
namespace {
LONG get(volatile LONG&v)noexcept{return InterlockedCompareExchange(&v,0,0);}
struct Lock{SRWLOCK*p;explicit Lock(SRWLOCK&l):p(&l){AcquireSRWLockExclusive(p);}~Lock(){ReleaseSRWLockExclusive(p);}};
template<class T>T at(std::uintptr_t p){return *reinterpret_cast<const T*>(p);}
bool readable(std::uintptr_t p,std::size_t n)noexcept{
    if(!p||!n||p>std::numeric_limits<std::uintptr_t>::max()-n)return false;
    const auto end=p+n;
    while(p<end){MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(p),&m,sizeof m)!=sizeof m||m.State!=MEM_COMMIT||
        m.Protect&(PAGE_NOACCESS|PAGE_GUARD)||!(m.Protect&(PAGE_READONLY|PAGE_READWRITE|PAGE_WRITECOPY|PAGE_EXECUTE_READ|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))return false;
        const auto next=reinterpret_cast<std::uintptr_t>(m.BaseAddress)+m.RegionSize;if(next<=p)return false;p=next<end?next:end;
    }return true;
}
bool same(const pd::Binding&a,const pd::Binding&b)noexcept{return a.attempt==b.attempt&&a.attachment==b.attachment&&a.owner_generation==b.owner_generation;}
bool overlap(pd::Span a,pd::Span b)noexcept{if(!a.size||!b.size)return false;auto x=reinterpret_cast<std::uintptr_t>(a.data),y=reinterpret_cast<std::uintptr_t>(b.data);return x<y+b.size&&y<x+a.size;}
pd::Span span(std::uintptr_t p,std::size_t n)noexcept{return{reinterpret_cast<const std::uint8_t*>(p),n};}
pd::Span neverResolve(void*,std::uintptr_t,std::size_t)noexcept{return{};}
struct Header{std::uint64_t count,capacity;std::uintptr_t pointer;};
Header header(std::uintptr_t m){return{at<std::uint64_t>(m+0x30),at<std::uint64_t>(m+0x38),at<std::uintptr_t>(m+0x40)};}
bool readHeader(std::uintptr_t m,Header&out)noexcept{__try{if(!readable(m,0x50))return false;out=header(m);return true;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool readCaller(std::uintptr_t p,std::uintptr_t expected)noexcept{__try{return readable(p,8)&&at<std::uintptr_t>(p)==expected;}__except(EXCEPTION_EXECUTE_HANDLER){return false;}}
bool same(const Header&a,const Header&b)noexcept{return a.count==b.count&&a.capacity==b.capacity&&a.pointer==b.pointer;}
}
void Adapter::fail(Error e,DWORD exception)noexcept{Lock l(lock_);if(report_.error==Error::None)report_.error=e;if(exception)report_.exception=exception;report_.stage=report_.may_have_queued?Stage::Uncertain:Stage::Rejected;}
bool Adapter::external(Point p)noexcept{
    __try{if(config_.validate_external&&config_.validate_external(config_.external_context,p))return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){fail(Error::ExternalGuard,GetExceptionCode());return false;}
    fail(Error::ExternalGuard);return false;
}
bool Adapter::profile()const noexcept{
    __try{
        auto base=config_.pending.profile_base;
        if(!base||base>std::numeric_limits<std::uintptr_t>::max()-0x2200000)return false;
#ifndef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
        if(base!=reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr)))return false;
#endif
        for(const auto&a:CheckpointNativeQueueAnchors){if(!readable(base+a.rva,a.size)||std::memcmp(reinterpret_cast<void*>(base+a.rva),a.bytes,a.size))return false;
#ifndef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
            MEMORY_BASIC_INFORMATION m{};if(VirtualQuery(reinterpret_cast<void*>(base+a.rva),&m,sizeof m)!=sizeof m||m.Type!=MEM_IMAGE)return false;
            if(a.rva!=0x12dd6e0&&m.Protect!=PAGE_EXECUTE_READ&&m.Protect!=PAGE_EXECUTE_WRITECOPY)return false;
#endif
        }return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
bool Adapter::Initialize(const Config&c)noexcept{
    if(InterlockedCompareExchange(&initialized_,1,0))return false;
    config_=c;
    if(!c.controller_identity||!c.cache||!c.validate_external||c.pending.expected_initial_cache_mode>1||
       reinterpret_cast<std::uintptr_t>(c.pending.load_cache.data)!=c.cache||!profile()){fail(Error::Config);return false;}
#ifdef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
    if(!c.fixture_native){fail(Error::Config);return false;}
#endif
    if(!external(Point::Initialize))return false;
    {Lock l(lock_);report_.stage=Stage::Initialized;report_.controller=reinterpret_cast<std::uintptr_t>(c.controller_identity);}
    InterlockedExchange(&initialized_,2);return true;
}
bool Adapter::planning()noexcept{
    __try{return planningBody();}__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());return false;}
}
bool Adapter::planningBody(){
        const auto&c=config_.pending;const auto m=c.profile_base+0x19e7310;
        const pd::Span all[]={c.user,c.toolbar,c.game,c.panel,c.manager,c.stack,c.queue,c.load_cache};
        for(unsigned i=0;i<8;++i){const auto&s=all[i];if(i==6&&!s.data&&!s.size)continue;if(!readable(reinterpret_cast<std::uintptr_t>(s.data),s.size))return false;}
        if(reinterpret_cast<std::uintptr_t>(c.manager.data)!=m||!readable(c.profile_base+0x2025318,8)||at<std::uintptr_t>(c.profile_base+0x2025318)!=config_.cache)return false;
        const auto h=header(m);if(h.count||h.capacity>4096||h.capacity>c.queue.size/16||h.pointer!=reinterpret_cast<std::uintptr_t>(c.queue.data)||
            (!h.capacity&&(h.pointer||c.queue.size)))return false;
        const auto cap=at<std::uint64_t>(m+0x18);
        if(cap<5||cap>4096||cap>c.stack.size/8)return false;
        pd::Adapter inspector;auto check=c;check.resolve_created_queue=neverResolve;check.queue_resolver_context=nullptr;
        if(inspector.Bind(check)!=pd::Error::None)return false;
        const auto r=inspector.InspectCurrent(c.binding);
        if(r.error!=pd::Error::None||r.decision!=pd::Decision::QuiescentObserved)return false;
        return same(h,header(m));
}
bool Adapter::Authorize(const pd::Ticket&t,const CheckpointPushFrame&f,const void* controller)noexcept{
    if(get(initialized_)!=2)return false;
    if(InterlockedCompareExchange(&authorization_,1,0)){fail(Error::Consumed);return false;}
    if(get(stopped_)){fail(Error::Stopped);return false;}
    if(controller!=config_.controller_identity){fail(Error::Controller);return false;}
    if(!t.serial||!t.call_id||t.call_id!=f.call_id||!same(t.binding,config_.pending.binding)){fail(Error::Ticket);return false;}
    if(f.slot!=0||f.args[0]!=config_.pending.states[4]||!f.caller_entry_rsp||f.thread_id!=GetCurrentThreadId()){fail(Error::Frame);return false;}
    auto expectedCaller=config_.pending.profile_base+0x50b785;
#ifdef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
    if(config_.fixture_user_caller)expectedCaller=config_.fixture_user_caller;
#endif
    if(!readCaller(f.caller_entry_rsp,expectedCaller)){fail(Error::Frame);return false;}
    if(!profile()||!external(Point::Authorize)||!planning()){fail(Error::Pending);return false;}
    Header h{};
    if(!readHeader(config_.pending.profile_base+0x19e7310,h)||h.count||h.pointer!=reinterpret_cast<std::uintptr_t>(config_.pending.queue.data)||
       h.capacity>config_.pending.queue.size/16){fail(Error::Header);return false;}
    {Lock l(lock_);
        if(report_.error!=Error::None||get(stopped_))return false;
        frame_=f;ticket_=t;old_queue_=h.pointer;old_capacity_=h.capacity;
        report_.thread=f.thread_id;report_.call_id=f.call_id;report_.ticket_serial=t.serial;report_.user=f.args[0];report_.authorized=1;report_.stage=Stage::Authorized;
    }
    InterlockedExchange(&authorization_,2);return true;
}
bool Adapter::returned()noexcept{
    __try{return returnedBody();}__except(EXCEPTION_EXECUTE_HANDLER){fail(Error::Memory,GetExceptionCode());return false;}
}
bool Adapter::returnedBody(){
        const auto&c=config_.pending;const auto m=c.profile_base+0x19e7310;
        if(!readable(m,0x50)||!readable(config_.cache,0x3f4))return false;
        const auto h=header(m);
        // With initial count zero, native 411A55..411A99 grows an empty vector
        // by exactly 64 entries; a nonempty capacity does not reallocate.
        if(h.count!=1||h.capacity!=(old_capacity_?old_capacity_:64)||!h.pointer||
           (old_capacity_&&h.pointer!=old_queue_)||h.capacity>4096||!readable(h.pointer,std::size_t(h.capacity)*16))return false;
        const auto menu=at<std::uintptr_t>(h.pointer+8);
        if(at<DWORD>(h.pointer)!=0||!readable(menu,0x4c0)||at<std::uintptr_t>(menu)!=c.profile_base+0x12db4c0||
           std::memcmp(reinterpret_cast<void*>(menu+0x70),"CSaveLoadState",15)||at<std::uintptr_t>(menu+0x48)||
           at<std::uintptr_t>(menu+0x50)||at<std::uint64_t>(menu+0x68)||at<std::uintptr_t>(menu+0x470)||at<std::uintptr_t>(menu+0x478))return false;
        const pd::Span q=span(h.pointer,std::size_t(h.capacity)*16),s=span(menu,0x4c0);
        const pd::Span protectedSpans[]={c.user,c.toolbar,c.game,c.panel,c.manager,c.stack,c.load_cache,span(reinterpret_cast<std::uintptr_t>(this),sizeof(*this))};
        if(overlap(q,s))return false;
        for(auto keep:protectedSpans)if(overlap(q,keep)||overlap(s,keep))return false;
        if(at<std::uintptr_t>(c.profile_base+0x2025318)!=config_.cache||at<DWORD>(config_.cache+8)!=0||at<DWORD>(config_.cache+0x3f0)||at<LONG>(config_.cache+0x3ec)!=-1||
           at<std::uint64_t>(m+0x10)!=5||at<std::uintptr_t>(m+0x20)!=reinterpret_cast<std::uintptr_t>(c.stack.data)||at<std::uintptr_t>(m+0x48)!=c.states[4])return false;
        for(unsigned i=0;i<5;++i)if(at<std::uintptr_t>(reinterpret_cast<std::uintptr_t>(c.stack.data)+8*i)!=c.states[i])return false;
        if(!same(h,header(m))||at<std::uintptr_t>(h.pointer+8)!=menu||at<DWORD>(h.pointer)!=0)return false;
        {Lock l(lock_);
            if(report_.queue&&(report_.menu!=menu||report_.queue!=h.pointer||report_.queue_capacity!=h.capacity||report_.queue_count!=h.count))return false;
            report_.menu=menu;report_.queue=h.pointer;report_.queue_capacity=h.capacity;report_.queue_count=h.count;
        }
        return true;
}
pd::Span Adapter::Queue(){
    if(get(initialized_)!=2||get(authorization_)!=2){fail(Error::Ticket);return{};}
    if(GetCurrentThreadId()!=frame_.thread_id){fail(Error::Thread);return{};}
    if(InterlockedCompareExchange(&queue_once_,1,0)){fail(Error::Consumed);return{};}
    {Lock l(lock_);report_.queue_capability_consumed=true;if(report_.error!=Error::None)return{};}
    if(get(stopped_)){fail(Error::Stopped);return{};}
    if(!profile()||!external(Point::BeforeNative)||!planning()){fail(Error::Pending);return{};}
    Header before{};
    if(!readHeader(config_.pending.profile_base+0x19e7310,before)||before.count||
       before.pointer!=old_queue_||before.capacity!=old_capacity_){fail(Error::Header);return{};}
    {Lock l(lock_);if(report_.error!=Error::None||get(stopped_))return{};report_.stage=Stage::Calling;report_.may_have_queued=true;++report_.native_calls;}
    DWORD mode[2]={0,0};alignas(16) unsigned char closure[64]{};
    auto native=reinterpret_cast<Native>(config_.pending.profile_base+0x411980);
#ifdef CHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE
    native=config_.fixture_native;
#endif
    // A native exception is rethrown after recording uncertainty. Never retry,
    // pop, free, undo a native allocation or fabricate an empty native queue.
    try{native(reinterpret_cast<void*>(config_.pending.profile_base+0x19e7310),reinterpret_cast<const char*>(config_.pending.profile_base+0x12dd6e0),mode,closure);}
    catch(...){fail(Error::NativeException);throw;}
    {Lock l(lock_);++report_.native_returned;}
    if(!returned()||!external(Point::AfterNative)||!returned()){fail(Error::NativeResult);return{};}
    {Lock l(lock_);if(get(stopped_)||report_.error!=Error::None){if(report_.error==Error::None)report_.error=Error::Stopped;report_.stage=Stage::Uncertain;return{};}
        ++report_.native_result_verified;report_.stage=Stage::Returned;return span(report_.menu,0x4c0);}
}
pd::Span Adapter::Resolve(std::uintptr_t address,std::size_t bytes)noexcept{
    if(get(initialized_)!=2||get(authorization_)!=2||GetCurrentThreadId()!=frame_.thread_id){fail(Error::Thread);return{};}
    if(InterlockedCompareExchange(&resolver_once_,1,0)){fail(Error::Consumed);return{};}
    {Lock l(lock_);++report_.resolver_calls;if(report_.error!=Error::None||report_.stage!=Stage::Returned||!report_.native_result_verified||get(stopped_)||
        address!=report_.queue||bytes!=report_.queue_capacity*16){if(report_.error==Error::None)report_.error=Error::Resolver;report_.stage=Stage::Uncertain;return{};}}
    if(!external(Point::Resolve)||!readable(address,bytes)||!returned()){fail(Error::Resolver);return{};}
    {Lock l(lock_);if(report_.error!=Error::None||get(stopped_)||address!=report_.queue||bytes!=report_.queue_capacity*16){report_.stage=Stage::Uncertain;return{};}
        report_.stage=Stage::Resolved;return span(address,bytes);}
}
void Adapter::Stop()noexcept{InterlockedExchange(&stopped_,1);}
bool Adapter::Snapshot(Report&out)const noexcept{if(!get(initialized_))return false;Lock l(lock_);out=report_;out.stopped=get(stopped_)!=0;return true;}
bool Adapter::AuthorizeCallback(void*c,const pd::Ticket&t,const CheckpointPushFrame&f,const void*owner)noexcept{return static_cast<Adapter*>(c)->Authorize(t,f,owner);}
pd::Span Adapter::QueueCallback(void*c){return static_cast<Adapter*>(c)->Queue();}
pd::Span Adapter::ResolveCallback(void*c,std::uintptr_t p,std::size_t n)noexcept{return static_cast<Adapter*>(c)->Resolve(p,n);}
}
