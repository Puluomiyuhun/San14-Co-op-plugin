#pragma once
#include "checkpoint_dynamic_file_profile.h"
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <cstdint>
#include "checkpoint_load_worker_bridge.h"

// Observation only: no process discovery, slot writes, native calls, load
// submission, identity changes, or receipt authorizing a future load.
namespace checkpoint_dynamic_cc_load_observer {
enum class Point:std::uint32_t { Bind=1,WorkerBefore,WorkerAfter,ReadBefore,ReadAfter };
enum class Error:LONG { None=0,Configuration=1,Binding=2,Guard=3,Memory=4,WorkerIdentity=5,
    WorkerDuplicate=6,Owner=7,ReadDuplicate=8,ReadPath=9,ReadArguments=10,ReadReturn=11,
    ReadHash=12,MissingRead=13,NativeResult=14,Abnormal=15,Unpaired=16,Stopped=17 };
struct Config {
    const checkpoint_dynamic_file_profile::Profile* profile=nullptr;
    uintptr_t base=0,storage=0,storageVtable=0,readMethod=0;
    std::uint64_t attemptToken=0;
    // Must independently pin/recheck v014 storage/method ownership, supported
    // image, current transaction, Load/Title relationship and exact CC63 target.
    // Bind is before Load phase1 original Update. Later points must not require
    // stale world ID maps, a published worker phase, or the old planning stack.
    // The read VT slot may be the caller's owned bridge; captured readMethod
    // remains immutable. No lock is held while this callback runs. Must not throw.
    bool (*validateAttachment)(void*,Point,uintptr_t load,uintptr_t title)=nullptr;
    void* validationContext=nullptr;
#ifdef CHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE
    // Own-PE fixture labels replace ONLY native caller addresses. Synthetic
    // Load/worker/storage objects retain the real offsets used by production.
    uintptr_t fixtureWorkerCaller=0,fixtureReadCaller=0,fixtureParentCaller=0;
#endif
};
struct Report {
    std::uint32_t version=1,size=sizeof(Report);
    LONG error=0;std::uint32_t exceptionCode=0;
    std::uint64_t token=0,load=0,title=0,worker=0,callable=0;
    std::uint64_t workerCall=0,readCall=0,workerCaller=0,readCaller=0,parentCaller=0;
    std::uint64_t buffer=0,workerRax=0,readRax=0;
    std::uint32_t workerThread=0,readThread=0,requested=0,returned=0,nativeResult=0;
    std::uint32_t workerBefore=0,workerAfter=0,workerFinally=0,workerAbnormal=0;
    std::uint32_t readBefore=0,readAfter=0,readFinally=0,readAbnormal=0;
    std::uint32_t otherWorkers=0,titleWorkers=0,unownedReads=0,ownedReadCandidates=0;
    std::uint32_t activeWorker=0,activeRead=0,bytesMatched=0,workerReturned=0;
    std::uint32_t observedWorkerAndBytes=0,stopped=0,loadAuthorized=0,joined=0,planningReady=0;
    unsigned char sha256[32]{},workerXmm0[16]{},readXmm0[16]{};
};
static_assert(sizeof(Report)==288);
// Caller must preserve this object, Config callback and all original bridge
// pointers until process exit. There is deliberately no reset/retry API.
struct Observer {
    SRWLOCK lock=SRWLOCK_INIT;
    Config config{};Report report{};checkpoint_dynamic_file_profile::Profile profile{};
    volatile LONG initialized=0,bound=0,workerClaimed=0,readClaimed=0,error=0,stopped=0;
#ifdef CHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE
    std::uint32_t alignmentPadding[4]{};
#else
    std::uint32_t alignmentPadding[2]{};
#endif
    CheckpointLoadWorkerFrame workerFrame{},readFrame{};
};
bool Initialize(Observer&,const Config&) noexcept;
bool BindLoad(Observer&,uintptr_t load,uintptr_t title) noexcept;
void Stop(Observer&) noexcept;
void Snapshot(Observer&,Report&) noexcept;
void WorkerBefore(const CheckpointLoadWorkerFrame*,void*) noexcept;
void WorkerAfter(const CheckpointLoadWorkerFrame*,void*) noexcept;
void WorkerFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
void ReadBefore(const CheckpointLoadWorkerFrame*,void*) noexcept;
void ReadAfter(const CheckpointLoadWorkerFrame*,void*) noexcept;
void ReadFinally(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*) noexcept;
}
