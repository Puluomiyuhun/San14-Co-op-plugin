// Executes only the actual WorldProfile validator. Every other dependency is
// an explicit aborting double, so accidental callback execution fails loudly.
#include "checkpoint_dynamic_title_identity_adapter.h"
#include "checkpoint_persistent_logical_adapter.h"
#include <cstdio>
#include <cstdlib>
namespace checkpoint_dynamic_file_profile {
bool Validate(const Profile&) noexcept {std::abort();}
bool Equal(const Profile&,const Profile&) noexcept {std::abort();}
}
namespace checkpoint_dynamic_cc_load_observer {void Snapshot(Observer&,Report&) noexcept {std::abort();}}
namespace checkpoint_dynamic_cc_load_lifecycle {void Snapshot(Lifecycle&,Report&) noexcept {std::abort();}}
namespace checkpoint_identity_pair_commit {bool Committer::Commit(const Input&,const Access&) noexcept {std::abort();}}
namespace checkpoint_persistent_logical_adapter {
bool Claim(const CheckpointLoadWorkerFrame*,std::uint64_t) noexcept {std::abort();}
bool CurrentOwner(CheckpointLoadWorkerOwner*) noexcept {std::abort();}
}
int main(){
    namespace ti=checkpoint_dynamic_title_identity_adapter;
    unsigned checks=0,bad=0;auto check=[&](bool value){++checks;if(!value)++bad;};
    ti::WorldProfile p{203,8,11,{666,12,11},{952,2,2}};
    check(ti::ValidWorldProfile(p));auto q=p;
    q.target.district=q.source.district;check(!ti::ValidWorldProfile(q));
    q=p;q.target.force=q.source.force;check(!ti::ValidWorldProfile(q));
    q=p;q.target.ruler=q.source.ruler;check(!ti::ValidWorldProfile(q));
    q=p;q.source.force=0;check(!ti::ValidWorldProfile(q));
    q=p;q.target.force=52;check(!ti::ValidWorldProfile(q));
    q=p;q.source.district=0;check(!ti::ValidWorldProfile(q));
    q=p;q.target.district=52;check(!ti::ValidWorldProfile(q));
    q=p;q.source.ruler=0;check(!ti::ValidWorldProfile(q));
    q=p;q.target.ruler=6000;check(!ti::ValidWorldProfile(q));
    q=p;q.year=0;check(!ti::ValidWorldProfile(q));
    q=p;q.month=0;check(!ti::ValidWorldProfile(q));
    q=p;q.month=13;check(!ti::ValidWorldProfile(q));
    q=p;q.day=2;check(!ti::ValidWorldProfile(q));
    q=p;q.day=21;q.source.ruler=766;q.target.ruler=1052;q.target.force=7;check(ti::ValidWorldProfile(q));
    std::printf("{\"passed\":%s,\"checks\":%u,\"failures\":%u,\"game_access\":false,\"native_range_semantics_proven\":false}\n",bad?"false":"true",checks,bad);
    return bad?1:0;
}
