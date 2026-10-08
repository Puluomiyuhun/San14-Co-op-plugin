#pragma once
#include "a_save_user_owner.h"
#include "checkpoint_reward_owned_replay.h"
namespace a_reward_save_owner {
namespace ph=checkpoint_planning_hold;namespace rw=checkpoint_reward_owned_replay;
struct Source {ph::Config admission{};rw::Config reward{};};
struct Config {ph::Binding binding{};bool(*sample)(void*,uintptr_t,unsigned,Source&)=nullptr;void* context=nullptr;};
enum class Error:unsigned {None,Config,Source,Scope,Replay,Cleanup,Exception,Cancelled,Stopped};
struct Report {Error error=Error::None;std::uint64_t submitted=0,completed=0,cancelled=0,active=0,finally=0,abnormal=0,readyRevision=0;unsigned created=0,destroyed=0;DWORD thread=0;bool bound=false,queued=false,readyFence=false,uncertain=false;rw::Report reward{};ph::Report admission{};bool roomReady=false,fullWorld=false,allInputHeld=false;};
// Same retained User/Save owner only; immutable trusted binding and fresh sampler.
bool Bind(a_save_user_owner::Owner&,const Config&) noexcept;
bool Submit(a_save_user_owner::Owner&,const ph::Binding&,std::uint64_t,const rw::Command&) noexcept;
bool Cancel(a_save_user_owner::Owner&,const ph::Binding&,std::uint64_t) noexcept;
// Local admission fence only, never a network Ready acknowledgement.
bool ReadyFence(a_save_user_owner::Owner&,const ph::Binding&,bool,std::uint64_t) noexcept;
bool Snapshot(a_save_user_owner::Owner&,Report&) noexcept;
}
extern "C" bool ARewardSaveOwnerSuppressedConfigure(void(*)(const CheckpointLoadWorkerFrame*,void*));
