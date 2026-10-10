#pragma once
#include "b_warm_two_bank_owner.h"
// Three distinct retained banks, two independent once-only predecessor edges.
// Local ownership proof only: does not install/load or grant room/input permission.
namespace b_warm_chain {
struct Certificate {
 std::uint32_t version=1,pid=0;std::uint64_t birth=0,generation=0,attempt=0;
 uintptr_t previous=0,next=0;unsigned char nonce[32]{},fileSha256[32]{};
 std::uint64_t userCall=0,identityCall=0,loadCall=0;
};
class Chain {
 SRWLOCK lock_=SRWLOCK_INIT;
 b_warm_two_bank::Handover edges_[2];bool edgeBound_[2]{};
 HMODULE banks_[3]{};void**slots_[6]{};void*originals_[6]{};
 Certificate certificates_[2]{};unsigned generation_=0;DWORD pid_=0;
 std::uint64_t birth_=0;unsigned char nonce_[32]{};
 bool current()const noexcept;
public:
 Chain()=default;Chain(const Chain&)=delete;Chain&operator=(const Chain&)=delete;
 bool Bind(HMODULE first,void**const(&slots)[6],void*const(&originals)[6],const unsigned char(&nonce)[32])noexcept;
 bool AuthorizeNext(HMODULE next,unsigned generation,Certificate&out)noexcept;
 bool ReadCertificate(unsigned generation,Certificate&out)noexcept;
 bool CompletedCurrent(unsigned generation)noexcept;
};
}
