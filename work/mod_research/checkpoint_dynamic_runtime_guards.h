#pragma once
#include "checkpoint_dynamic_native_session.h"
#include "checkpoint_persistent_planning_observer.h"
#include "checkpoint_persistent_logical_adapter.h"
#include "checkpoint_native_queue_adapter_core.h"

namespace checkpoint_dynamic_runtime_guards {
namespace ns=checkpoint_dynamic_native_session;
namespace rq=checkpoint_dynamic_load_request_commit;
namespace by=checkpoint_dynamic_cc_load_observer;
namespace lc=checkpoint_dynamic_cc_load_lifecycle;
namespace ti=checkpoint_dynamic_title_identity_adapter;
namespace pr=checkpoint_persistent_planning;
namespace qa=checkpoint_native_queue_adapter;
namespace fp=checkpoint_dynamic_file_profile;
struct Stamp {
 std::uint64_t attempt=0,epoch=0,generation=0;
 unsigned char owner_binding[32]{},checkpoint_sha256[32]{};
};
struct Config {
 DWORD pid=0;std::uint64_t birth=0;
 uintptr_t base=0,owner_module=0;
 Stamp expected{};const Stamp* current_stamp=nullptr;
 // Local recipient planning boundary BEFORE the incoming host checkpoint.
 // Its date and player need not match incoming.worldProfile.source/date.
 checkpoint_load_input_boundary::Config initial{};
 ti::Identity initialIdentity{};
 fp::Profile fileProfile{};ti::WorldProfile worldProfile{};
 // Physical owner installs immutable pure-forwarding entries BEFORE attaching
 // this generation. Initialize only copies immutable configuration; Session
 // Initialize/Arm and every active check require all six slots already owned.
 checkpoint_load_hook_set::Binding hooks[6]{};
 const qa::Adapter* queue=nullptr;
 bool(*storage_valid)(void*) noexcept=nullptr;void* storage_context=nullptr;
 const wchar_t* request_intent=nullptr;const wchar_t* identity_intent=nullptr;
 unsigned char supported_image_sha256[32]{};
#ifdef CHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE
 // Caller labels only. Actual persistent bridge/adapter mapping remains real.
 uintptr_t fixtureCallers[6]{};
#endif
};
enum class Error:unsigned {None,Config,Attachment,Image,Hook,Storage,Memory,Lifetime,Phase,Pending,Rng,Queue,Intent,Retired,Callback};
struct Report {
 unsigned calls[29]{},accepted[29]{},queue_calls[5]{};
 Error first_error=Error::None,last_error=Error::None;DWORD exception=0;
 unsigned failures=0,initialized=0;
 std::uint64_t queue_call=0;DWORD queue_thread=0;
 uintptr_t menu=0,load=0,title=0;unsigned load_completed=0,load_retired=0,identity_returned=0;
 bool full_input_hold=false,full_world_verified=false,full_loaded_image_verified=false;
 bool native_scheduler_fence=false,production_generation_publication=false;
};
class Context final {
public:
 bool Initialize(const Config&) noexcept;
 bool Snapshot(Report&)const noexcept;
 static bool SessionGuard(void*,ns::Point) noexcept;
 static bool RequestGuard(void*,rq::Point) noexcept;
 static bool BytesGuard(void*,by::Point,uintptr_t load,uintptr_t title) noexcept;
 static bool LifecycleGuard(void*,lc::Point,uintptr_t load,uintptr_t title) noexcept;
 static bool IdentityGuard(void*,ti::Point,uintptr_t title,uintptr_t root,uintptr_t world) noexcept;
 static bool PlanningGuard(void*,pr::Point,const CheckpointPushFrame&,std::uint64_t attempt,std::uint64_t epoch,std::uint64_t generation) noexcept;
 static bool QueueGuard(void*,qa::Point) noexcept;
 // Storage checks never recurse into storage_valid or Session::Snapshot.
 static bool AttachmentOnly(void*) noexcept;
 static bool OwnedReadBridgeOnly(void*) noexcept;
private:
 enum class Slots {Owned};
 bool common(Slots,bool storage) noexcept;
 bool image()const;bool slots(Slots)const;bool stamp()const;
 bool mapping(unsigned physical,unsigned stage,uintptr_t self=0,const void* exactFrame=nullptr)const;
 bool callback(unsigned family,unsigned point,uintptr_t a,uintptr_t b)const;
 bool identity(uintptr_t root,const ti::Identity&)const;
 bool initialGraph(unsigned count,uintptr_t current,LONG pending,bool rng)const;
 bool queuedMenu();
 bool loadGraph(uintptr_t,uintptr_t,bool current,bool allowCleared);
 bool titleGraph(uintptr_t,uintptr_t,uintptr_t,bool after,bool targetPair);
 bool planningGraph()const;
 bool check(unsigned family,unsigned point,uintptr_t a=0,uintptr_t b=0,uintptr_t c=0) noexcept;
 bool body(unsigned,unsigned,uintptr_t,uintptr_t,uintptr_t);
 bool fail(Error,DWORD=0) noexcept;
 Config config_{};Stamp expected_{};
 wchar_t request_intent_[512]{},identity_intent_[512]{};
 mutable SRWLOCK lock_=SRWLOCK_INIT;
 mutable volatile LONG initialized_=0;Report report_{};
};
}
