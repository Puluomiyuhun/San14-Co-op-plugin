#include "checkpoint_planning_hold_user_dry.h"
#include <cstdio>
static std::uint64_t body(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t){return 1;}
int main(){
    checkpoint_planning_hold_user_dry::Adapter a;checkpoint_planning_hold_user_dry::Config c{};
    // Configuration-only rejection test; no pointer is dereferenced or invoked.
    c.hold=reinterpret_cast<checkpoint_planning_hold::Context*>(0x1000);c.original=&body;c.request_owned_dry_skip=true;
    if(a.Initialize(c))return 1;
    std::puts("{\"result\":\"PASS\",\"case\":\"production-skip-refusal\",\"production_skip_enabled\":false,\"game_access\":false}");return 0;
}
