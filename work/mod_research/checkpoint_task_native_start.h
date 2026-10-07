#pragma once
#include "checkpoint_task_native_activation_v2.h"
#include "checkpoint_persistent_logical_adapter.h"
namespace checkpoint_task_native_start {
enum class Error:unsigned {None,Config,Binding,Occupied,Helper,DebugContext,Deadline,Restore,Source,Worker,Event,WaitStack,Pointer,Resume,Exception,Stopped};
struct Config {
    uintptr_t base=0;std::uint64_t generation=0;
    checkpoint_native_task_provider::Provider* provider=nullptr;
    checkpoint_dynamic_native_session::Session* sessionOwner=nullptr;
    checkpoint_task_native_activation_v2::Router* activation=nullptr;
    // Explicit opt-in for the SAME checked production path. Default observation.
    bool publishRunner=false;DWORD helperDeadlineMs=1000;
    CheckpointPushObserver nextBefore=nullptr,nextAfter=nullptr;
    checkpoint_persistent_logical_adapter::DispatchFinally nextFinally=nullptr;void* nextContext=nullptr;
#ifdef CHECKPOINT_TASK_NATIVE_START_FIXTURE
    uintptr_t fixtureUpdateCaller=0;
#endif
};
struct Sample {std::uint64_t rip=0,rcx=0,rdx=0,rbx=0,rdi=0,rsp=0;DWORD thread=0,flags=0;unsigned accepted=0;};
struct Report {
    std::uint64_t generation=0,call=0,creation=0;uintptr_t load=0,control=0,object=0,slot=0,original=0,replacement=0,waitRip=0;
    DWORD parentThread=0,workerThread=0,exception=0,osError=0;Error error=Error::None;
    unsigned armed=0,captured=0,finally=0,abnormal=0,restored=0,uncertain=0,stopped=0;
    unsigned workerSuspended=0,workerResumed=0,waitStackVerified=0,eventUnsignaled=0,publishOptIn=0,published=0,rolledBack=0,publicationClaimed=0,stopAfterClaim=0;
    LONG eventType=-1,eventState=-1;unsigned unwindFrames=0;std::uint64_t originalDr[6]{},restoredDr[6]{};Sample samples[2]{};
    bool globalFence=false,gameInstaller=false,fullWorld=false,ready=false;
};
class Adapter final {
public:
    // One retained instance per generation. Compose into logical Load callbacks;
    // original update always runs through the existing finally-capable bridge.
    bool Initialize(const Config&) noexcept;
    void Stop() noexcept;
    bool Snapshot(Report&) noexcept;
    static void Before(const CheckpointPushFrame*,void*) noexcept;
    static void After(const CheckpointPushFrame*,void*) noexcept;
    static void Finally(const CheckpointPushFrame*,const CheckpointLoadWorkerExit*,void*);
private:void* state_=nullptr;
};
}
