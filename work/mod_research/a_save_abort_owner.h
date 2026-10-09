#pragma once
#include "a_save_user_owner.h"
// Terminal failure retirement, never a successful artifact or a retry permit.
// Retire is a local Host-only entry; it requires the actual Parent control TLS.
namespace a_save_abort {
struct Receipt {
 std::uint64_t sequence=0;
 std::uint32_t size=sizeof(Receipt),version=1;
 std::uint64_t base=0,owner=0,generation=0;
 std::uint32_t thread=0,ownerError=0,driverError=0,retired=0;
};
bool Retire(a_save_user_owner::Owner&,std::uint64_t generation)noexcept;
bool Snapshot(std::uintptr_t base,std::uint64_t generation,DWORD hostThread,Receipt&)noexcept;
}
extern "C" __declspec(dllexport) a_save_abort::Receipt ASaveAbortReceipt;
