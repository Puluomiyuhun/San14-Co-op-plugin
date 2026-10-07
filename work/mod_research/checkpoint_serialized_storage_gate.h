#pragma once
#include "checkpoint_live_storage_binding.h"

// One retained owner uses this entrance for ALL binding validation, including
// guards and native_storage_read::Api.validate. No Steam/ContextInit/IPC calls.
// Caller keeps this object/callback owner resident for process lifetime.
namespace checkpoint_serialized_storage_gate {
namespace binding=checkpoint_live_storage_binding;
enum class State:LONG {New,Opening,Open,Invalidated,Stopped};
enum class Error:LONG {None,AlreadyOpened,OpenFailed,ValidationFailed,Recursion,Invalidated,Stopped};
struct Report {
    State state=State::New;Error error=Error::None;
    unsigned openAttempts=0,opened=0,validationAttempts=0,validationSucceeded=0;
    unsigned validationRejected=0,recursionRejected=0,queued=0;
    unsigned activeChecks=0,maxActiveChecks=0;
    DWORD lastThread=0;
    binding::Report lastBinding{}; // Diagnostic copy, never authorization.
    bool fixtureBuild=false,nativeCalls=false,worldReady=false,inputHeld=false;
};
class Gate final {
public:
    Gate()=default;
    Gate(const Gate&)=delete;Gate& operator=(const Gate&)=delete;
    bool Open(const binding::Config&) noexcept;
    bool Valid() noexcept;
    native_storage_read::Api Api() noexcept;
    // Permanent retirement. Does not cancel an already-running native method.
    // Post-CAS Session.Stop may need continued observations: owner must NOT
    // translate it into Gate.Stop until it intends to retire those validators.
    void Invalidate() noexcept;
    void Stop() noexcept;
    void Snapshot(Report&)const noexcept; // Copies gate-owned POD only.
private:
    binding::Context context_{};native_storage_read::Api api_{};
    SRWLOCK validationLock_=SRWLOCK_INIT;
    mutable SRWLOCK reportLock_=SRWLOCK_INIT;Report report_{};
    volatile LONG once_=0,state_=LONG(State::New);
    bool retire(Error,State)noexcept;
    void bindingSnapshot()noexcept;
    static bool Validate(void*)noexcept;
};
}
