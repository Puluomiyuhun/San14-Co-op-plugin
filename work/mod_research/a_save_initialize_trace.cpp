#include "a_save_initialize_trace.h"
extern "C" {alignas(8) __declspec(dllexport) a_save_initialize_trace::Record ASaveInitializeFirstFailure={sizeof(a_save_initialize_trace::Record),1};}
namespace a_save_initialize_trace {
namespace {volatile LONG claimed=0;thread_local unsigned depth=0;thread_local Record context{};
void publish(LONG stage,std::uint64_t a,std::uint64_t b,std::uint64_t c,DWORD code,const checkpoint_native_input_pending::Report*input=nullptr)noexcept {
 if(!depth||InterlockedCompareExchange(&claimed,1,0)!=0)return;
 auto&r=ASaveInitializeFirstFailure;r.pid=GetCurrentProcessId();r.thread=GetCurrentThreadId();
 r.controller=context.controller;r.owner=context.owner;r.base=context.base;r.root=context.root;r.world=context.world;
 r.a=a;r.b=b;r.c=c;r.exceptionCode=code;
 if(input){const auto&i=*input;r.input={i.stack_count,i.queue_count,unsigned(i.error),unsigned(i.decision),unsigned(i.stage),i.menu_command,i.user_phase,i.game_transition,i.load_queued,i.advance,i.panel_advance};}
 MemoryBarrier();InterlockedExchange(&r.stage,stage);
}}
void Begin(const void*controller,const void*owner,uintptr_t base,uintptr_t root,uintptr_t world)noexcept {
 if(depth++==0){context.controller=reinterpret_cast<uintptr_t>(controller);context.owner=reinterpret_cast<uintptr_t>(owner);context.base=base;context.root=root;context.world=world;}
}
void End()noexcept {if(depth)--depth;}
bool Check(bool pass,LONG stage,std::uint64_t a,std::uint64_t b,std::uint64_t c)noexcept {if(!pass)publish(stage,a,b,c,0);return pass;}
bool Inspect(bool pass,const checkpoint_native_input_pending::Report&r)noexcept {if(!pass)publish(46,unsigned(r.error),unsigned(r.decision),(std::uint64_t(r.stack_count)<<32)|r.user_phase,0,&r);return pass;}
void Exception(LONG stage,DWORD code)noexcept {publish(stage,0,0,0,code);}
}
