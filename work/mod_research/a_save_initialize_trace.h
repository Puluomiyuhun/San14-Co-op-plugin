#pragma once
#include <Windows.h>
#include <cstdint>
#include <cstddef>
#include "checkpoint_native_input_pending_adapter.h"
namespace a_save_initialize_trace {
struct Input {
 std::uint64_t stackCount,queueCount;
 std::uint32_t error,decision,stage;
 std::int32_t menuCommand;
 std::uint32_t userPhase,gameTransition,loadQueued,advance,panelAdvance;
};
// Zero stage means no initialization failure has been published, not readiness.
struct Record {
 std::uint32_t size,version,pid,thread;
 std::uint64_t controller,owner,base,root,world,a,b,c;
 Input input;
 std::uint32_t exceptionCode;
 volatile LONG stage;
};
static_assert(sizeof(Record)==144 && offsetof(Record,stage)==140,"trace ABI");
void Begin(const void*controller,const void*owner,uintptr_t base,uintptr_t root,uintptr_t world)noexcept;
void End()noexcept;
bool Check(bool pass,LONG stage,std::uint64_t a=0,std::uint64_t b=0,std::uint64_t c=0)noexcept;
bool Inspect(bool pass,const checkpoint_native_input_pending::Report&)noexcept;
void Exception(LONG stage,DWORD code)noexcept;
}
extern "C" __declspec(dllexport) a_save_initialize_trace::Record ASaveInitializeFirstFailure;
