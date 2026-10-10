// B User-only mode-zero inspector successor; current must still be exact User.
// Same-ABI successor for A: accept native unallocated EMPTY vectors for
// read-only inspection. Link instead of the frozen adapter, never alongside it.
// Does not follow a newly allocated queue or authorize an empty-vector load.
#include "checkpoint_native_input_pending_adapter.h"
#include <cstring>
#include <limits>

namespace checkpoint_native_input_pending {
namespace {
template<class T> T Read(Span s, std::size_t offset) noexcept {
    T value{}; std::memcpy(&value, s.data + offset, sizeof(value)); return value;
}
std::uintptr_t Address(Span s) noexcept { return reinterpret_cast<std::uintptr_t>(s.data); }
bool Same(const Binding& a, const Binding& b) noexcept {
    return a.attempt == b.attempt && a.attachment == b.attachment && a.owner_generation == b.owner_generation;
}
bool Token(const checkpoint_native_input::Identity& token) noexcept {
    for (auto value : token) if (value) return true;
    return false;
}
bool Extent(Span s, std::size_t minimum) noexcept {
    return s.data && s.size >= minimum && s.size <= std::numeric_limits<std::uintptr_t>::max() - Address(s);
}
bool Overlap(Span a, Span b) noexcept {
    return Address(a) < Address(b) + b.size && Address(b) < Address(a) + a.size;
}
bool Name(Span s, const char* expected) noexcept {
    return std::memcmp(s.data + 0x70, expected, std::strlen(expected) + 1) == 0;
}
Error Spans(const Config& c, const void* self, std::size_t own_size) noexcept {
    const Span spans[] = {c.user,c.toolbar,c.game,c.panel,c.manager,c.stack,c.queue,c.load_cache};
    constexpr std::size_t minimum[] = {0x668,0x8c,0x488,0x1f8,0x50,0x30,0x10,0x3f4};
    const Span own{static_cast<const std::uint8_t*>(self),own_size};
    for (unsigned i=0;i<8;++i) {
        // An unallocated native vector is valid only as an exact null/zero span.
        if(i==6&&!spans[i].data&&!spans[i].size)continue;
        if (!Extent(spans[i],minimum[i])) return Error::Span;
        if (Overlap(spans[i],own)) return Error::Alias;
        for(unsigned j=0;j<i;++j) if(Overlap(spans[i],spans[j])) return Error::Alias;
    }
    return Error::None;
}
Report Failure(Stage stage, std::uint64_t call, Error error) noexcept {
    Report r; r.stage=stage; r.call_id=call; r.error=error; return r;
}
} // namespace

const char* ErrorName(Error e) noexcept {
    switch(e) {
#define E(x) case Error::x:return #x;
        E(None) E(NotBound) E(AlreadyBound) E(Identity) E(WrongThread) E(Span) E(Alias) E(Pointer)
        E(Layout) E(Reentrant) E(CallPair) E(StaleCall) E(WrongStage) E(NoCleanPrefetch)
        E(NoAuthorization) E(TicketMismatch) E(AuthorizationUsed)
#undef E
    } return "Unknown";
}
const char* DecisionName(Decision d) noexcept {
    switch(d) {
#define D(x) case Decision::x:return #x;
        D(Invalid) D(QuiescentObserved) D(PlayerMenuPending) D(AdvancePending) D(StateTransition)
        D(SelectionPending) D(UnownedStateQueue) D(UnownedLoadMenu) D(AuthorizedLoadQueued) D(AuthorizedLoadActive)
#undef D
    } return "Unknown";
}

Error Adapter::Bind(const Config& c) noexcept {
    if(bound_) return Error::AlreadyBound;
    if(!Token(c.binding.attempt)||!Token(c.binding.attachment)||!c.binding.owner_generation||
       c.profile_base<0x10000||c.profile_base>std::numeric_limits<std::uintptr_t>::max()-0x12DB4C0)
        return Error::Identity;
    const auto e=Spans(c,this,sizeof(*this)); if(e!=Error::None)return e;
    for(auto state:c.states)if(!state)return Error::Identity;
    if(c.states[2]!=Address(c.game)||c.states[4]!=Address(c.user))return Error::Pointer;
    config_=c;owner_thread_=GetCurrentThreadId();bound_=true;return Error::None;
}
Error Adapter::ValidateBinding(const Binding& b) const noexcept {
    if(!bound_)return Error::NotBound;
    if(GetCurrentThreadId()!=owner_thread_)return Error::WrongThread;
    if(!Same(b,config_.binding))return Error::Identity;
    return Error::None;
}
Error Adapter::ValidateMenu(Span menu) const noexcept {
    if(!Extent(menu,0x480))return Error::Span;
    const Span all[]={config_.user,config_.toolbar,config_.game,config_.panel,config_.manager,
                      config_.stack,config_.queue,config_.load_cache,
                      {reinterpret_cast<const std::uint8_t*>(this),sizeof(*this)}};
    for(auto s:all)if(Overlap(s,menu))return Error::Alias;
    if(Read<std::uintptr_t>(menu,0)!=config_.profile_base+0x12DB4C0||
       !Name(menu,"CSaveLoadState")||Read<std::uintptr_t>(menu,0x48)!=0||
       Read<std::uint32_t>(menu,0x68)!=0)return Error::Layout;
    return Error::None;
}

Report Adapter::Inspect(Stage stage, std::uint64_t call) noexcept {
    auto r=Failure(stage,call,Spans(config_,this,sizeof(*this)));
    if(r.error!=Error::None)return r;
    const auto& c=config_;
    if(Read<std::uintptr_t>(c.user,0)!=c.profile_base+0x12CC4A8||
       Read<std::uintptr_t>(c.game,0)!=c.profile_base+0x12CC9B8||
       !Name(c.user,"CUserStrategyState")||!Name(c.game,"CGameState")) {r.error=Error::Layout;return r;}
    if(Read<std::uintptr_t>(c.user,0x478)!=Address(c.toolbar)||
       Read<std::uintptr_t>(c.game,0x480)!=Address(c.panel)||
       Read<std::uintptr_t>(c.manager,0x20)!=Address(c.stack)||
       Read<std::uintptr_t>(c.manager,0x40)!=Address(c.queue)) {r.error=Error::Pointer;return r;}
    const auto capacity=Read<std::uint64_t>(c.manager,0x38);
    if(capacity>4096||capacity>c.queue.size/16||
       Read<std::uint64_t>(c.manager,0x30)>capacity||
       (!capacity&&(c.queue.data||c.queue.size))) {r.error=Error::Layout;return r;}
    r.user_phase=Read<std::uint32_t>(c.user,0x470);
    r.menu_command=Read<std::int32_t>(c.toolbar,0x88);
    r.game_transition=Read<std::uint32_t>(c.game,0x474);
    r.load_queued=Read<std::uint32_t>(c.game,0x478);
    r.advance=Read<std::uint32_t>(c.game,0x47c);
    r.panel_advance=Read<std::uint32_t>(c.panel,0x1b0);
    r.stack_count=Read<std::uint64_t>(c.manager,0x10);
    r.queue_count=Read<std::uint64_t>(c.manager,0x30);
    // Every nonempty toolbar request remains player/unknown, even if the value
    // might open a load menu. Authorization is for our exact state queue object.
    if(r.menu_command!=-1){r.decision=Decision::PlayerMenuPending;return r;}
    if(r.advance||r.panel_advance){r.decision=Decision::AdvancePending;return r;}
    if(r.user_phase!=2||r.game_transition||r.load_queued||Read<std::uint32_t>(c.user,0x660)||
       Read<std::uint32_t>(c.user,0x68)||Read<std::uint32_t>(c.game,0x68)||
       Read<std::int32_t>(c.load_cache,0x3ec)!=-1||Read<std::uint32_t>(c.load_cache,0x3f0)) {
        r.decision=Decision::StateTransition;return r;
    }
    for(auto off:{0x4a8u,0x4b0u,0x4b8u})if(Read<std::uintptr_t>(c.user,off)) {
        r.decision=Decision::SelectionPending;return r;
    }
    if(r.stack_count!=5&&r.stack_count!=6){r.decision=Decision::StateTransition;return r;}
    for(unsigned i=0;i<5;++i)if(Read<std::uintptr_t>(c.stack,i*8)!=c.states[i]) {
        r.error=Error::Pointer;return r;
    }
    const auto current=Read<std::uintptr_t>(c.manager,0x48);
    if(r.queue_count) {
        r.decision=Decision::UnownedStateQueue;
        if(authorized_&&!authorization_retired_&&!authorized_active_observed_&&r.queue_count==1&&r.stack_count==5&&current==Address(c.user)&&
           ValidateMenu(authorized_menu_)==Error::None&&Read<std::uint32_t>(c.queue,0)==0&&
           Read<std::uintptr_t>(c.queue,8)==Address(authorized_menu_)&&Read<std::uint32_t>(c.load_cache,8)==0)
            r.decision=Decision::AuthorizedLoadQueued;
        return r;
    }
    if(r.stack_count==6) {
        r.decision=Decision::UnownedLoadMenu;
        if(authorized_&&!authorization_retired_&&ValidateMenu(authorized_menu_)==Error::None&&current==Address(authorized_menu_)&&
           Read<std::uintptr_t>(c.stack,40)==Address(authorized_menu_)&&Read<std::uint32_t>(c.load_cache,8)==0) {
            r.decision=Decision::AuthorizedLoadActive;
            authorized_active_observed_=true;
        }
        return r;
    }
    if(current!=Address(c.user)){r.error=Error::Pointer;return r;}
    // Once the observed menu transition leaves the stack/queue, this attempt's
    // object identity cannot authorize a later reused pointer or player menu.
    if(authorized_) {authorization_retired_=true;r.decision=Decision::StateTransition;return r;}
    if(Read<std::uint32_t>(c.load_cache,8)!=0){r.decision=Decision::StateTransition;return r;}
    r.decision=Decision::QuiescentObserved;
    r.pending_admission_candidate=stage==Stage::BeforeMenuFetch;
    return r;
}

bool Adapter::Matches(const CheckpointPushFrame& f) const noexcept {
    return active_&&f.slot==frame_.slot&&f.thread_id==frame_.thread_id&&f.call_id==frame_.call_id&&
        f.caller_entry_rsp==frame_.caller_entry_rsp&&!std::memcmp(f.args,frame_.args,sizeof(f.args));
}
Report Adapter::ObserveBefore(const Binding& b,const CheckpointPushFrame& f) noexcept {
    const auto e=ValidateBinding(b);if(e!=Error::None)return Failure(Stage::BeforeUserUpdate,f.call_id,e);
    if(active_)return Failure(Stage::BeforeUserUpdate,f.call_id,Error::Reentrant);
    if(f.slot!=0||f.thread_id!=owner_thread_||f.args[0]!=Address(config_.user)||!f.caller_entry_rsp)
        return Failure(Stage::BeforeUserUpdate,f.call_id,Error::CallPair);
    if(!f.call_id||f.call_id<=last_call_)return Failure(Stage::BeforeUserUpdate,f.call_id,Error::StaleCall);
    active_=true;after_=false;frame_=f;last_call_=f.call_id;
    before_clean_=false;prefetch_clean_=false;after_clean_=false;prefetch_seen_=false;
    auto r=Inspect(Stage::BeforeUserUpdate,f.call_id);
    before_clean_=r.error==Error::None&&r.decision==Decision::QuiescentObserved;
    return r;
}
Report Adapter::ObserveBeforeFetch(const Binding& b,std::uint64_t call,const void* saved_rsi) noexcept {
    const auto e=ValidateBinding(b);if(e!=Error::None)return Failure(Stage::BeforeMenuFetch,call,e);
    if(!active_||after_||prefetch_seen_)return Failure(Stage::BeforeMenuFetch,call,Error::WrongStage);
    if(call!=frame_.call_id||reinterpret_cast<std::uintptr_t>(saved_rsi)!=Address(config_.user))
        return Failure(Stage::BeforeMenuFetch,call,Error::CallPair);
    prefetch_seen_=true;
    auto r=Inspect(Stage::BeforeMenuFetch,call);
    prefetch_clean_=r.error==Error::None&&r.decision==Decision::QuiescentObserved;
    // Entry's old pending request cannot be erased by original and relabeled as
    // a clean same-call transition later.
    r.pending_admission_candidate=r.pending_admission_candidate&&before_clean_;
    return r;
}
Report Adapter::ObserveAfter(const Binding& b,const CheckpointPushFrame& f) noexcept {
    const auto e=ValidateBinding(b);if(e!=Error::None)return Failure(Stage::AfterUserUpdate,f.call_id,e);
    if(after_||!Matches(f))return Failure(Stage::AfterUserUpdate,f.call_id,Error::CallPair);
    after_=true;
    auto r=Inspect(Stage::AfterUserUpdate,f.call_id);
    after_clean_=r.error==Error::None&&r.decision==Decision::QuiescentObserved;
    if(!prefetch_seen_&&r.error==Error::None)r.error=Error::NoCleanPrefetch;
    r.pending_admission_candidate=before_clean_&&prefetch_clean_&&after_clean_;
    return r;
}
Error Adapter::CloseAfter(const Binding& b,std::uint64_t call) noexcept {
    const auto e=ValidateBinding(b);if(e!=Error::None)return e;
    if(!active_||!after_||call!=frame_.call_id)return Error::WrongStage;
    active_=false;after_=false;ticket_open_=false;return Error::None;
}
Report Adapter::InspectCurrent(const Binding& b) noexcept {
    const auto e=ValidateBinding(b);if(e!=Error::None)return Failure(Stage::Standalone,0,e);
    return Inspect(Stage::Standalone,0);
}
Error Adapter::BeginAuthorizedLoadPush(const Binding& b,std::uint64_t call,Ticket& out) noexcept {
    const auto e=ValidateBinding(b);if(e!=Error::None)return e;
    if(!active_||!after_||call!=frame_.call_id)return Error::WrongStage;
    if(authorization_started_)return Error::AuthorizationUsed;
    // This same-ABI A inspector never authorizes a load that would allocate a
    // new queue. Such loads require the separate bound resolver implementation.
    if(!config_.queue.data&&!config_.queue.size)return Error::NoAuthorization;
    if(!before_clean_||!prefetch_clean_||!after_clean_)return Error::NoCleanPrefetch;
    const auto current=Inspect(Stage::AfterUserUpdate,call);
    if(current.error!=Error::None||current.decision!=Decision::QuiescentObserved)return Error::NoAuthorization;
    ticket_={b,++serial_,call};ticket_open_=true;authorization_started_=true;out=ticket_;return Error::None;
}
Error Adapter::CommitAuthorizedLoadPush(const Ticket& t,Span menu) noexcept {
    const auto e=ValidateBinding(t.binding);if(e!=Error::None)return e;
    if(!active_||!after_||!ticket_open_)return Error::WrongStage;
    if(t.serial!=ticket_.serial||t.call_id!=ticket_.call_id||!Same(t.binding,ticket_.binding))return Error::TicketMismatch;
    ticket_open_=false; // One commit observation only; an uncertain push is not retried.
    const auto menu_error=ValidateMenu(menu);if(menu_error!=Error::None)return menu_error;
    const auto current=Inspect(Stage::AfterUserUpdate,t.call_id);
    if(current.error!=Error::None||current.decision!=Decision::UnownedStateQueue||
       current.stack_count!=5||current.queue_count!=1||
       Read<std::uintptr_t>(config_.manager,0x48)!=Address(config_.user)||
       Read<std::uint32_t>(config_.queue,0)!=0||Read<std::uintptr_t>(config_.queue,8)!=Address(menu)||
       Read<std::uint32_t>(config_.load_cache,8)!=0)return Error::NoAuthorization;
    authorized_menu_=menu;authorized_=true;return Error::None;
}
} // namespace checkpoint_native_input_pending
