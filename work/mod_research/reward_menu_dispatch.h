#pragma once
#include "reward_menu_lifecycle.h"
// Concrete callback guard; no installer or production continuation address.
// The owned test executes the whole archived function. The external task/pool
// environment and native exception handler are not production-proven.
namespace reward_menu_dispatch {
struct Report {unsigned error=0;uint64_t entered=0,selected=0,storageReleased=0,boundaries=0,returned=0;bool active=false,rejected=false,production_permit=false;};
class Guard final {
public:
 bool Enter(uint64_t base,uint64_t manager,reward_menu_lifecycle::Owner&)noexcept;
 bool Select(uint64_t manager,uint64_t menu,uint64_t request,uint64_t end)noexcept;
 bool Finalized(uint64_t manager,uint64_t menu)noexcept;
 bool Freed(uint64_t manager,uint64_t old_menu)noexcept;
 bool CopiedStorageReleased(uint64_t storage)noexcept;
 bool AfterCleanup()noexcept;
 bool Returned()noexcept;
 Report Snapshot()const noexcept{return report_;}
private:
 bool reject(unsigned)noexcept;bool scope()const noexcept;
 uint64_t base_=0,manager_=0,copied_=0;unsigned thread_=0;
 reward_menu_lifecycle::Owner*life_=nullptr;Report report_{};
};
}
