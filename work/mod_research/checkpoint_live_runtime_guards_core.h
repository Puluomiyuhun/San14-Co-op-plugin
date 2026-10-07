#pragma once
#include "checkpoint_forward_native_session.h"
#include "checkpoint_forward_planning_observer.h"
#include "checkpoint_native_queue_adapter_core.h"

namespace checkpoint_live_runtime_guards {
namespace ns=checkpoint_forward_native_session;
namespace rq=checkpoint_load_request_commit;
namespace by=checkpoint_cc_load_observer;
namespace lc=checkpoint_cc_load_lifecycle;
namespace ti=checkpoint_title_identity_adapter;
namespace pr=checkpoint_forward_planning_observer;
namespace qa=checkpoint_native_queue_adapter;
// Owner retains this real transaction record and all pointed-to objects/module
// state. It is compared on every guard, not accepted as an authorization bool.
struct Stamp {
 std::uint64_t attempt=0,epoch=0;
 unsigned char owner_binding[32]{},checkpoint_sha256[32]{};
};
struct Config {
 DWORD pid=0;std::uint64_t birth=0;
 uintptr_t base=0,owner_module=0;
 Stamp expected{};const Stamp* current_stamp=nullptr;
 // Fresh initial values, not the older data-only manifest. Menu must be zero.
 checkpoint_load_input_boundary::Config initial{};
 checkpoint_load_hook_set::Binding hooks[6]{};
 qa::Adapter* queue=nullptr;
 // The owner's serialized Gate.Valid thunk. Never point this back at one of
 // these guards; storage owner/hook callbacks must be direct nonrecursive reads.
 bool(*storage_valid)(void*) noexcept=nullptr;void* storage_context=nullptr;
 const wchar_t* request_intent=nullptr;const wchar_t* identity_intent=nullptr;
 // Main EXE hash is verified by the launcher and bound here to the supported
 // profile. Guards also recheck actual module ownership/PE/archived code bytes.
 unsigned char supported_image_sha256[32]{};
};
enum class Error:unsigned {None,Config,Attachment,Image,Hook,Storage,Memory,Lifetime,Phase,Pending,Rng,Queue,Intent,Retired};
struct Report {
 unsigned calls[29]{},accepted[29]{};unsigned queue_calls[5]{};
 Error first_error=Error::None,last_error=Error::None;DWORD exception=0;
 unsigned failures=0,initialized=0;
 uintptr_t menu=0,load=0,title=0;unsigned load_completed=0,load_retired=0,identity_returned=0;
 bool full_input_hold=false,full_world_verified=false,full_loaded_image_verified=false;
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
 static bool PlanningGuard(void*,pr::Point,std::uint64_t attempt,std::uint64_t epoch) noexcept;
 static bool QueueGuard(void*,qa::Point) noexcept;
 // Optional helpers for storage's direct owner/hook checks. No storage_valid,
 // Session::Snapshot, old world/UI reads or external callbacks are invoked.
 static bool AttachmentOnly(void*) noexcept;
 static bool OwnedReadBridgeOnly(void*) noexcept;
private:
 enum class Slots {Original,Owned,Either};
 bool common(Slots,bool storage) noexcept;
 bool image()const;
 bool slots(Slots)const;
 bool stamp()const;
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
