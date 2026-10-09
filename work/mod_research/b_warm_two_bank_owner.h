#pragma once
#include "b_warm_profile.h"
#include "b_warm_retire_session.h"
// Trusted local host policy. Does not stop other writers or install hooks.
// One retained first module; permission is based on its actual complete receipts.
namespace b_warm_two_bank {
class Handover {
    HMODULE first_=nullptr,second_=nullptr;
    void** slots_[6]{};void* originals_[6]{};
    bool issued_=false;
public:
    bool Bind(HMODULE first,void** const (&slots)[6],void* const (&originals)[6]) noexcept;
    bool AuthorizeSecond(HMODULE second) noexcept;
    bool Completed(HMODULE bank)const noexcept;
};
}
