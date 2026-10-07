#pragma once
#include "checkpoint_dynamic_file_profile.h"
#include "checkpoint_load_input_boundary.h"
#include "checkpoint_push_bridge.h"
#include "native_storage_read_core.h"

// A one-shot request to load native slot63, not a completed world replacement.
// It runs inside the real parent Game Update BEFORE after a matched Menu AFTER.
// No menu row is fabricated and no interior native instruction is called.
// casApplied remains decisive even when CommitGameBefore returns false:
// once published, native Game can consume slot63. Keep load/identity observers
// armed on Uncertain; do not detach them or retry solely on a false return.
namespace checkpoint_dynamic_load_request_commit {
enum class Point:unsigned { MenuReceipt,Preflight,BeforeRead,AfterRead,BeforeIntent,BeforeCas,AfterCas };
enum class State:unsigned { New,Initialized,MenuObserved,Rejected,IntentDurable,NotApplied,PendingCommitted,Uncertain };
struct Config {
    const checkpoint_dynamic_file_profile::Profile* profile=nullptr;
    checkpoint_load_input_boundary::Config boundary{};
    native_storage_read::Api storage{};
    const wchar_t* localPath=nullptr;
    const wchar_t* intentPath=nullptr;
    unsigned char ownerBinding[32]{};
    // Exact supported image/attachment/current menu transaction, six observer
    // hooks armed, and live presentation-controller ownership are validated by
    // the integrator. A bool is not independently a native input/visibility proof.
    bool (*validate)(void*,Point)=nullptr;
    void* context=nullptr;
};
struct Report {
    State state=State::New;
    unsigned menuCalls=0,gameCalls=0,readAttempts=0,casAttempts=0,casApplied=0;
    bool menuObserved=false,intentCreated=false,intentDurable=false,postGuard=false;
    DWORD osError=0,exceptionCode=0;
    std::uint64_t attempt=0,menuCall=0,gameCall=0;
    DWORD menuThread=0,gameThread=0;
    LONG observedPending=-1;
    const char* stage="new";
    native_storage_read::Evidence read{};
    checkpoint_load_input_boundary::Report boundary{};
    bool worldLoaded=false,identityRestored=false,planningReady=false;
};
class Committer {
public:
    bool Initialize(const Config&) noexcept;
    bool ObserveMenuAfter(const checkpoint_load_input_boundary::Call&) noexcept;
    bool CommitGameBefore(const checkpoint_load_input_boundary::Call&) noexcept;
    // After owning calls return; diagnostics are not concurrently atomic.
    const checkpoint_dynamic_file_profile::Profile& GetProfile() const noexcept {return profile_;}
    const Report& GetReport() const noexcept {return report_;}
private:
    volatile LONG initialized_=0,menuOnce_=0,gameOnce_=0;
    Config config_{};Report report_{};
    checkpoint_dynamic_file_profile::Profile profile_{};
    wchar_t localPath_[512]{},intentPath_[512]{};
    native_storage_read::Lease lease_{};
    const checkpoint_load_input_boundary::Call* activeCall_=nullptr;
    bool guard(Point) noexcept;
    bool inspect() noexcept;
    bool reserve() noexcept;
    static bool validateStorage(void*) noexcept;
};
}
