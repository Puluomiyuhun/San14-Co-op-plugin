#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include "a_reward_save_owner.h"
extern "C" void ASaveUserOwnerBridgeCallOriginal(void*,CheckpointLoadWorkerFrame*);
namespace {
struct Slot {
    volatile LONG state=0;
    ASaveUserOwnerBridgeConfig config{};
    volatile LONG64 started=0,native_started=0,native_returned=0,before_calls=0,after_calls=0;
    volatile LONG64 finally_calls=0,abnormal_exits=0,cleanup_faults=0,scope_claims=0,rejected_claims=0,active=0;
    bool pinned=false;
};
Slot slots[2]{};
void(*rewardSuppressed)(const CheckpointLoadWorkerFrame*,void*)=nullptr;volatile LONG rewardConfigured=0;
struct Scope {
    Scope* previous;
    CheckpointLoadWorkerFrame* frame;
    CheckpointLoadWorkerStage stage;
    std::uint32_t depth;
    std::uint64_t token;
};
static thread_local Scope* current=nullptr;
std::uint64_t get64(volatile LONG64* v) noexcept {return InterlockedCompareExchange64(v,0,0);}
[[noreturn]] void badEntry() noexcept {
    RaiseFailFastException(nullptr,nullptr,0);TerminateProcess(GetCurrentProcess(),0xE0144001);__assume(0);
}
void cleanup(Slot& s,const CheckpointLoadWorkerFrame* frame,const CheckpointLoadWorkerExit* exit) noexcept {
    if(!s.config.finally)return;
    InterlockedIncrement64(&s.finally_calls);
    // /EHa is required. This inner boundary only contains cleanup-observer faults;
    // BEFORE, original and AFTER are never caught here or elsewhere in the bridge.
    __try {s.config.finally(frame,exit,s.config.context);}
    __except(EXCEPTION_EXECUTE_HANDLER) {InterlockedIncrement64(&s.cleanup_faults);}
}
}
extern "C" bool ARewardSaveOwnerSuppressedConfigure(void(*f)(const CheckpointLoadWorkerFrame*,void*)){if(!f||InterlockedCompareExchange(&rewardConfigured,1,0))return false;rewardSuppressed=f;return true;}
extern "C" int ASaveUserOwnerBridgeConfigure(unsigned slot,const ASaveUserOwnerBridgeConfig* c) noexcept {
    if(slot>1||!c||c->size!=sizeof(*c)||c->version!=1||!c->original)return 0;
    if(c->original==reinterpret_cast<void*>(&ASaveUserOwnerBridge0)||
       c->original==reinterpret_cast<void*>(&ASaveUserOwnerBridge1)||
       c->original==reinterpret_cast<void*>(&ASaveUserOwnerBridgeCallOriginal))return 0;
    auto& s=slots[slot];if(InterlockedCompareExchange(&s.state,1,0))return 0;
    HMODULE mod=nullptr;
    if(!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
          reinterpret_cast<LPCWSTR>(&ASaveUserOwnerBridgeConfigure),&mod)){
        InterlockedExchange(&s.state,0);return 0;
    }
    s.config=*c;s.pinned=true;InterlockedExchange(&s.state,2);return 1;
}
extern "C" int ASaveUserOwnerBridgeSnapshot(unsigned slot,CheckpointLoadWorkerBridgeStats* out) noexcept {
    if(slot>1||!out)return 0;auto& s=slots[slot];LONG configured=InterlockedCompareExchange(&s.state,0,0);
    *out={get64(&s.started),get64(&s.native_started),get64(&s.native_returned),get64(&s.before_calls),get64(&s.after_calls),
        get64(&s.finally_calls),get64(&s.abnormal_exits),get64(&s.cleanup_faults),get64(&s.scope_claims),get64(&s.rejected_claims),get64(&s.active),
        configured==2?1u:0u,configured==2&&s.pinned?1u:0u};return 1;
}
extern "C" int ASaveUserOwnerClaim(const CheckpointLoadWorkerFrame* f,std::uint64_t token) noexcept {
    if(!current||current->frame!=f)return 0;
    auto& s=slots[f->slot];
    bool valid=token&&current->stage==CheckpointLoadWorkerStage::Before;
    for(auto* p=current;p;p=p->previous)if(p->token)valid=false;
    if(!valid){InterlockedIncrement64(&s.rejected_claims);return 0;}
    current->token=token;InterlockedIncrement64(&s.scope_claims);return 1;
}
extern "C" int ASaveUserOwnerCurrentOwner(CheckpointLoadWorkerOwner* out) noexcept {
    if(!out)return 0;*out={};
    for(auto* p=current;p;p=p->previous)if(p->token){
        *out={p->token,p->frame->call_id,p->frame->slot,p->frame->thread_id,p->depth,current->depth};return 1;
    }
    return 0;
}
extern "C" __declspec(noinline) void ASaveUserOwnerBridgeInvoke(unsigned slot,CheckpointLoadWorkerFrame* f) {
    if(slot>1||!f||InterlockedCompareExchange(&slots[slot].state,0,0)!=2)badEntry();
    auto& s=slots[slot];const auto& c=s.config;
    f->slot=slot;f->thread_id=GetCurrentThreadId();f->call_id=InterlockedIncrement64(&s.started);
    Scope scope{current,f,CheckpointLoadWorkerStage::Done,current?current->depth+1:1,0};
    current=&scope;InterlockedIncrement64(&s.active);
    __try {
        const bool forward=!c.select||c.select(f,c.context);
        if(!forward&&slot!=0)badEntry();
        if(!forward&&f->reserved_58==5){
            if(!rewardSuppressed)badEntry();scope.stage=CheckpointLoadWorkerStage::Before;
            // A real PE owner scope, but no original User body or AFTER receipt.
            InterlockedIncrement64(&s.before_calls);rewardSuppressed(f,c.context);
        }
        if(forward){
            scope.stage=CheckpointLoadWorkerStage::Before;
            if(c.before){InterlockedIncrement64(&s.before_calls);c.before(f,c.context);}
            scope.stage=CheckpointLoadWorkerStage::Native;InterlockedIncrement64(&s.native_started);
            ASaveUserOwnerBridgeCallOriginal(c.original,f);InterlockedIncrement64(&s.native_returned);
            scope.stage=CheckpointLoadWorkerStage::After;
            if(c.after){InterlockedIncrement64(&s.after_calls);c.after(f,c.context);}
        }
        scope.stage=CheckpointLoadWorkerStage::Done;
    }__finally {
        const bool abnormal=AbnormalTermination()!=FALSE;
        const CheckpointLoadWorkerExit exit{abnormal?1u:0u,static_cast<std::uint32_t>(scope.stage),scope.token?1u:0u,scope.depth,scope.token};
        if(abnormal)InterlockedIncrement64(&s.abnormal_exits);
        scope.stage=CheckpointLoadWorkerStage::Finally;
        __try {cleanup(s,f,&exit);}
        __finally {current=scope.previous;InterlockedDecrement64(&s.active);}
    }
}
