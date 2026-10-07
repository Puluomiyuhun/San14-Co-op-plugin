#define CHECKPOINT_PLANNING_HOLD_EXPORTS
#include "checkpoint_planning_hold_adapter.h"
#include <cstring>
#include <memory>
#include <new>
#include <vector>
namespace checkpoint_planning_hold {
namespace {
bool same(const Binding&a,const Binding&b)noexcept{return a.native.attempt==b.native.attempt&&a.native.attachment==b.native.attachment&&a.native.owner_generation==b.native.owner_generation&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
bool any(const std::array<unsigned char,32>&v)noexcept{for(auto b:v)if(b)return true;return false;}
struct Lock {SRWLOCK&lock;explicit Lock(SRWLOCK&v):lock(v){AcquireSRWLockExclusive(&lock);}~Lock(){ReleaseSRWLockExclusive(&lock);}};
struct Route {Context* context;Kind kind;const ReplayTicket*ticket;Route*previous;bool used=false;};
thread_local Route* route=nullptr;
struct Scope {Route value;Scope(Context*c,Kind k,const ReplayTicket*t):value{c,k,t,route,false}{route=&value;}~Scope(){route=value.previous;}};
}
struct ReplayTicket {Binding binding;SemanticReceipt semantic{};std::uint64_t sequence=0,revision=0;Kind kind=Kind::Reward;void* args=nullptr;int flags=0;std::array<unsigned char,104> bytes{};bool used=false;};
struct Context::Impl {
    SRWLOCK lock=SRWLOCK_INIT;Config config{};Report report{};DWORD owner=0;bool initialized=false;
    pd::Adapter pending;ni::Adapter neutral;checkpoint_native_input_consumer::MouseQueryBridge mouse;
    bool before=false,prefetch=false,clean=false;std::uint64_t call=0,cycle=0;
    std::vector<std::unique_ptr<ReplayTicket>> tickets;ReplayTicket*open=nullptr;
    void revoke()noexcept{if(open){open->used=true;open=nullptr;}report.open_replay_tickets=0;}
    void stop(Status s)noexcept{report.status=s;report.phase=Phase::FailStop;report.covered_local_gate_closed=true;report.covered_operation_completed=false;report.paired_planning_boundary=false;++report.revision;revoke();}
    bool ownerThread()noexcept{return owner==GetCurrentThreadId();}
    bool validate(const Binding&b)noexcept{return initialized&&same(config.binding,b);}
    bool held()const noexcept{return report.phase!=Phase::Open;}
    ReplayTicket* authorize(const Binding&b,std::uint64_t sequence,Kind kind,void*args,int flags)noexcept{
        Lock guard(lock);
        if(!validate(b)){report.status=Status::Binding;return nullptr;}
        if(!ownerThread()){report.status=Status::WrongThread;return nullptr;}
        if(report.phase==Phase::FailStop){report.status=Status::Stopped;return nullptr;}
        if(!args||!config.capture_owned_command||open||report.local_inflight||report.replay_inflight||sequence!=report.last_replay_sequence+1||!sequence){report.status=Status::ReplayBinding;return nullptr;}
        try {auto t=std::make_unique<ReplayTicket>();t->binding=b;t->sequence=sequence;t->revision=report.revision;t->kind=kind;t->args=args;t->flags=flags;
            if(!config.capture_owned_command(config.replay_source_context,kind,args,flags,t->semantic)||!any(t->semantic.digest)||!t->semantic.ownership_token||!t->semantic.payload_epoch){report.status=Status::ReplayBinding;return nullptr;}
            std::memcpy(t->bytes.data(),args,kind==Kind::Reward?sizeof(RewardArgs):104);open=t.get();tickets.push_back(std::move(t));report.open_replay_tickets=1;report.covered_replays_drained=false;report.covered_operation_completed=false;report.status=Status::Ok;return open;
        }catch(...){stop(Status::NativeException);return nullptr;}
    }
};
Context::Context():p_(new(std::nothrow) Impl){}
Context::~Context(){delete p_;}
bool Context::Initialize(const Config&c)noexcept{
    if(!p_)return false;Lock guard(p_->lock);
    if(p_->initialized||!c.binding.period||!c.binding.epoch||!any(c.binding.room_input_digest)||!c.reward||!c.sortie||!c.mouse||
        c.pending.binding.attempt!=c.binding.native.attempt||c.pending.binding.attachment!=c.binding.native.attachment||c.pending.binding.owner_generation!=c.binding.native.owner_generation)return false;
    if(p_->pending.Bind(c.pending)!=pd::Error::None||p_->neutral.Bind(c.binding.native,c.buffers)!=ni::Status::Ok||p_->mouse.Bind(c.binding.native,c.buffers,c.mouse)!=checkpoint_native_input_consumer::Status::Ok)return false;
    p_->config=c;p_->owner=GetCurrentThreadId();p_->initialized=true;p_->report.phase=Phase::Open;p_->report.status=Status::Ok;return true;
}
bool Context::BoundTo(const Binding&b)const noexcept{return p_&&p_->initialized&&same(p_->config.binding,b);}
bool Context::InspectOwnedUserSkipCandidate(std::uintptr_t user)noexcept{
    if(!p_)return false;Lock guard(p_->lock);
    if(!p_->initialized||!p_->ownerThread()||p_->report.phase!=Phase::Held||p_->before||p_->report.local_inflight||p_->report.replay_inflight||user!=p_->config.pending.states[4])return false;
    const auto observed=p_->pending.InspectCurrent(p_->config.binding.native);
    return observed.error==pd::Error::None&&observed.decision==pd::Decision::QuiescentObserved;
}
Status Context::Request(const Binding&b,Operation op,std::uint64_t generation)noexcept{
    if(!p_)return Status::Config;Lock guard(p_->lock);auto&r=p_->report;
    if(!p_->validate(b))return r.status=Status::Binding;
    if(r.phase==Phase::FailStop)return r.status=Status::Stopped;
    if(!generation||generation<=r.action_generation)return r.status=Status::StaleAction;
    if(op==Operation::Hold){if(r.phase!=Phase::Open)return r.status=Status::State;r.phase=Phase::HoldPending;}
    else if(op==Operation::Drain){if(r.phase!=Phase::Held)return r.status=Status::State;r.phase=Phase::DrainPending;}
    else if(op==Operation::Release){if(r.phase!=Phase::Held&&r.phase!=Phase::HoldPending&&r.phase!=Phase::DrainPending)return r.status=Status::State;r.phase=Phase::ReleasePending;++r.cancellations;p_->revoke();}
    else return r.status=Status::State;
    // Closed before any later neutralization/ack. Remote grants survive HOLD;
    // RELEASE invalidates them before a later boundary may open local commands.
    ++r.revision;if(p_->open)p_->open->revision=r.revision;
    r.action_generation=generation;r.covered_local_gate_closed=true;r.covered_operation_completed=false;r.paired_planning_boundary=false;r.covered_local_drained=false;r.covered_replays_drained=false;return r.status=Status::Ok;
}
void Context::Disconnect()noexcept{if(p_){Lock guard(p_->lock);p_->stop(Status::Stopped);}}
bool Context::Snapshot(Report&out)noexcept{if(!p_)return false;Lock guard(p_->lock);out=p_->report;return p_->initialized;}
void Context::Before(const CheckpointPushFrame&f)noexcept{
    if(!p_)return;Lock guard(p_->lock);if(!p_->initialized||!p_->ownerThread()){p_->stop(Status::WrongThread);return;}
    if(p_->before){p_->stop(Status::Reentrant);return;}
    auto observed=p_->pending.ObserveBefore(p_->config.binding.native,f);
    p_->before=observed.error==pd::Error::None;p_->prefetch=false;p_->clean=observed.decision==pd::Decision::QuiescentObserved;p_->call=f.call_id;
    if(!p_->before)p_->stop(Status::Pending);
}
void Context::BeforeMenuFetch(std::uint64_t call,const void*rsi)noexcept{
    if(!p_)return;Lock guard(p_->lock);if(!p_->initialized||!p_->ownerThread()||!p_->before||p_->prefetch||call!=p_->call){p_->stop(Status::Pending);return;}
    auto observed=p_->pending.ObserveBeforeFetch(p_->config.binding.native,call,rsi);p_->prefetch=true;
    p_->clean=p_->clean&&observed.error==pd::Error::None&&observed.pending_admission_candidate;
}
void Context::After(const CheckpointPushFrame&f)noexcept{
    if(!p_)return;Lock guard(p_->lock);auto&r=p_->report;
    if(!p_->initialized||!p_->ownerThread()||!p_->before){p_->stop(Status::Pending);return;}
    auto observed=p_->pending.ObserveAfter(p_->config.binding.native,f);
    const bool clean=p_->prefetch&&p_->clean&&observed.error==pd::Error::None&&observed.pending_admission_candidate;
    const auto closed=p_->pending.CloseAfter(p_->config.binding.native,f.call_id);p_->before=false;p_->prefetch=false;
    if(closed!=pd::Error::None){p_->stop(Status::Pending);return;}
    if(r.phase==Phase::FailStop||r.phase==Phase::Open)return;
    if(!clean||r.local_inflight||r.replay_inflight){r.status=Status::Busy;return;}
    auto publication=p_->neutral.PublishNeutral(p_->config.binding.native,++p_->cycle);
    if(publication.status!=ni::Status::Ok){p_->stop(Status::Pending);return;}
    r.neutral_cycle=p_->cycle;r.boundary_call=f.call_id;r.paired_planning_boundary=true;r.covered_local_drained=true;
    r.covered_replays_drained=!p_->open&&!r.replay_inflight;
    if(r.phase==Phase::DrainPending&&!r.covered_replays_drained){r.status=Status::Busy;return;}
    if(r.phase==Phase::ReleasePending){if(p_->open){r.status=Status::Busy;return;}r.phase=Phase::Open;r.covered_local_gate_closed=false;}
    else r.phase=Phase::Held;
    r.covered_operation_completed=true;r.status=Status::Ok;
    // No full_input_hold, input_held, or room_ack_eligible is ever asserted.
}
void Context::OriginalAbnormal()noexcept{if(p_){Lock guard(p_->lock);++p_->report.exceptions;p_->stop(Status::NativeException);}}
const ReplayTicket* Context::AuthorizeReward(const Binding&b,std::uint64_t s,RewardArgs*a)noexcept{return p_?p_->authorize(b,s,Kind::Reward,a,0):nullptr;}
const ReplayTicket* Context::AuthorizeSortie(const Binding&b,std::uint64_t s,std::uint32_t*a,int f)noexcept{return p_?p_->authorize(b,s,Kind::Sortie,a,f):nullptr;}
std::uint64_t Context::Invoke(Kind kind,void*args,int flags,const ReplayTicket*ticket){
    if(!p_)return 0;bool remote=ticket!=nullptr;std::uint64_t replaySequence=0;
    {Lock guard(p_->lock);auto&r=p_->report;auto reject=[&](Status s){r.status=s;if(remote)++r.remote_rejected;else++r.local_rejected;};
        if(!p_->initialized||!p_->ownerThread()){reject(Status::WrongThread);return 0;}
        if(r.phase==Phase::FailStop){reject(Status::Stopped);return 0;}
        if(!args){reject(Status::Config);return 0;}
        if(remote){
            // Pointer equality first: foreign caller pointers are never read.
            if(ticket!=p_->open||p_->open->used){reject(Status::MissingReplayTicket);return 0;}
            auto&t=*p_->open;
            bool contentSame=false;
            try {
                SemanticReceipt fresh{};
                contentSame=t.kind==kind&&t.args==args&&t.flags==flags&&t.revision==r.revision&&same(t.binding,p_->config.binding)&&t.sequence==r.last_replay_sequence+1&&
                    !std::memcmp(t.bytes.data(),args,kind==Kind::Reward?sizeof(RewardArgs):104)&&p_->config.capture_owned_command&&
                    p_->config.capture_owned_command(p_->config.replay_source_context,kind,args,flags,fresh)&&fresh.digest==t.semantic.digest&&fresh.ownership_token==t.semantic.ownership_token&&fresh.payload_epoch==t.semantic.payload_epoch;
            }catch(...){++r.exceptions;p_->stop(Status::NativeException);throw;}
            if(!contentSame){p_->revoke();reject(Status::ReplayBinding);return 0;}
            replaySequence=t.sequence;p_->revoke();++r.remote_entered;++r.replay_inflight;
        }else {if(p_->held()){reject(Status::Held);return 0;}if(r.local_inflight||r.replay_inflight){reject(Status::Reentrant);return 0;}++r.local_entered;++r.local_inflight;}
        r.covered_local_drained=false;r.covered_replays_drained=false;r.covered_operation_completed=false;r.status=Status::Ok;
    }
    std::uint64_t result=0;
    try {result=kind==Kind::Reward?std::uint64_t(std::uint32_t(p_->config.reward(static_cast<RewardArgs*>(args)))):reinterpret_cast<std::uint64_t>(p_->config.sortie(static_cast<std::uint32_t*>(args),flags));}
    catch(...){Lock guard(p_->lock);auto&r=p_->report;if(remote)--r.replay_inflight;else--r.local_inflight;++r.exceptions;p_->stop(Status::NativeException);throw;}
    {Lock guard(p_->lock);auto&r=p_->report;if(remote){--r.replay_inflight;r.last_replay_sequence=replaySequence;}else--r.local_inflight;++r.native_returns;if(!result&&remote)p_->stop(Status::NativeFailure);}
    return result;
}
int RewardEntry(RewardArgs*a){auto*r=route;if(!r||r->used||r->kind!=Kind::Reward)return 0;r->used=true;return int(std::uint32_t(r->context->Invoke(Kind::Reward,a,0,r->ticket)));}
void* SortieEntry(std::uint32_t*a,int f){auto*r=route;if(!r||r->used||r->kind!=Kind::Sortie)return nullptr;r->used=true;return reinterpret_cast<void*>(r->context->Invoke(Kind::Sortie,a,f,r->ticket));}
int Context::LocalReward(RewardArgs*a){Scope scope(this,Kind::Reward,nullptr);return RewardEntry(a);}
void* Context::LocalSortie(std::uint32_t*a,int f){Scope scope(this,Kind::Sortie,nullptr);return SortieEntry(a,f);}
int Context::ReplayReward(const ReplayTicket*t,RewardArgs*a){if(!t)return 0;Scope scope(this,Kind::Reward,t);return RewardEntry(a);}
void* Context::ReplaySortie(const ReplayTicket*t,std::uint32_t*a,int f){if(!t)return nullptr;Scope scope(this,Kind::Sortie,t);return SortieEntry(a,f);}
std::uint32_t Context::Mouse(const void*cache,std::uint32_t button){
    if(!p_)return 0;checkpoint_native_input_consumer::Request req{};
    {Lock guard(p_->lock);if(!p_->initialized||!p_->ownerThread()){p_->stop(Status::WrongThread);return 0;}
        req.binding=p_->config.binding.native;req.publication_cycle=++p_->cycle;req.mode=p_->held()?checkpoint_native_input_consumer::Mode::NeutralizeThenForward:checkpoint_native_input_consumer::Mode::ForwardUntouched;}
    checkpoint_native_input_consumer::Report observed{};
    try{auto value=p_->mouse.Invoke(req,cache,button,observed);if(observed.status!=checkpoint_native_input_consumer::Status::Ok){Lock guard(p_->lock);p_->stop(Status::Pending);}return value;}
    catch(...){OriginalAbnormal();throw;}
}
std::uint32_t MouseEntry(const void*cache,std::uint32_t button){return route&&route->context?route->context->Mouse(cache,button):0;}
}
using namespace checkpoint_planning_hold;
Context* PlanningHoldCreate(const Config*c)noexcept{if(!c)return nullptr;auto*p=new(std::nothrow)Context;if(!p)return nullptr;if(!p->Initialize(*c)){delete p;return nullptr;}return p;}
void PlanningHoldDestroy(Context*p)noexcept{delete p;}
unsigned PlanningHoldRequest(Context*p,const Binding*b,unsigned op,std::uint64_t g)noexcept{return unsigned(p&&b?p->Request(*b,Operation(op),g):Status::Config);}
void PlanningHoldDisconnect(Context*p)noexcept{if(p)p->Disconnect();}
bool PlanningHoldSnapshot(Context*p,Report*r)noexcept{return p&&r&&p->Snapshot(*r);}
void PlanningHoldBefore(Context*p,const CheckpointPushFrame*f)noexcept{if(p&&f)p->Before(*f);}
void PlanningHoldPrefetch(Context*p,std::uint64_t c,const void*u)noexcept{if(p)p->BeforeMenuFetch(c,u);}
void PlanningHoldAfter(Context*p,const CheckpointPushFrame*f)noexcept{if(p&&f)p->After(*f);}
void PlanningHoldAbnormal(Context*p)noexcept{if(p)p->OriginalAbnormal();}
bool PlanningHoldUserSkipCandidate(Context*p,std::uintptr_t u)noexcept{return p&&p->InspectOwnedUserSkipCandidate(u);}
int PlanningHoldLocalReward(Context*p,RewardArgs*a){return p?p->LocalReward(a):0;}
void* PlanningHoldLocalSortie(Context*p,std::uint32_t*a,int f){return p?p->LocalSortie(a,f):nullptr;}
std::uint32_t PlanningHoldMouse(Context*p,const void*c,std::uint32_t b){return p?p->Mouse(c,b):0;}
const ReplayTicket* PlanningHoldAuthorizeReward(Context*p,const Binding*b,std::uint64_t s,RewardArgs*a)noexcept{return p&&b?p->AuthorizeReward(*b,s,a):nullptr;}
int PlanningHoldReplayReward(Context*p,const ReplayTicket*t,RewardArgs*a){return p?p->ReplayReward(t,a):0;}
const ReplayTicket* PlanningHoldAuthorizeSortie(Context*p,const Binding*b,std::uint64_t s,std::uint32_t*a,int f)noexcept{return p&&b?p->AuthorizeSortie(*b,s,a,f):nullptr;}
void* PlanningHoldReplaySortie(Context*p,const ReplayTicket*t,std::uint32_t*a,int f){return p?p->ReplaySortie(t,a,f):nullptr;}
