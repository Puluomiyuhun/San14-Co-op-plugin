#pragma once
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <cstdint>
#include "checkpoint_persistent_bridge.h"
#include "native_storage_read_core.h"

// A retained, two-request native Save driver. This is a callback component, not
// an installer. The owner must provide unmodified User/Save originals, retain
// all code/state, and prevent player input while an export is pending.
namespace checkpoint_fresh_save {
enum class Status:unsigned {Idle,Armed,Queued,Finalized,Returned,Complete,Rejected,Uncertain,Cancelled};
struct Request {
 std::uint64_t generation=0,room_epoch=0,period=0,cut=0;
 unsigned char room_id[32]{}; // Opaque binding data; no room-authority assertion.
 std::uint16_t year=0,ruler=0;std::uint8_t month=0,day=0,force=0,reserved=0;
 char filename[16]{}; // Exactly mp + eight lowercase hex digits + .s14.
};
struct Config {
 std::uintptr_t base=0;
 wchar_t save_directory[512]{},intent_directory[512]{};
 unsigned user_slot=0,save_slot=1;
 int(*claim)(const CheckpointLoadWorkerFrame*,std::uint64_t)noexcept=nullptr;
 int(*owner)(CheckpointLoadWorkerOwner*)noexcept=nullptr;
 // Supply the existing approved live-storage binding's Api(). This driver also
 // checks exact User scope, world and returned native ContextInit object.
 native_storage_read::Api storage{};
#ifdef CHECKPOINT_FRESH_SAVE_FIXTURE
 std::uintptr_t binder=0,queue=0,caller=0;
#endif
};
struct Report {
 Status status=Status::Idle;unsigned error=0;
 std::uint64_t generation=0,active=0,entries=0,exits=0,abnormal=0;
 std::uint64_t first_call=0,last_call=0,save_state=0;
 unsigned intents=0,flushed=0,binds=0,queues=0,phase_mask=0;
 unsigned worker_started=0,worker_joined=0,native_success=0,finalizer_returned=0;
 unsigned return_matched=0,original_returned=0,stop_after_commit=0;
 DWORD executor_thread=0;unsigned completed_requests=0;
 bool full_world=false,room_ready=false,file_bytes_verified=false;
};
struct Artifact {Request request{};Report report{};std::vector<unsigned char>bytes;unsigned char sha256[32]{};};
class Driver final {
public:
 Driver();~Driver();Driver(const Driver&)=delete;Driver&operator=(const Driver&)=delete;
 bool Initialize(const Config&)noexcept;
 bool Submit(const Request&)noexcept;
 void Stop()noexcept;
 Report Snapshot()noexcept;
 bool CopyArtifact(std::uint64_t generation,Artifact&)noexcept;
 void Before(const CheckpointLoadWorkerFrame&)noexcept;
 void After(const CheckpointLoadWorkerFrame&)noexcept;
 void Finally(const CheckpointLoadWorkerFrame&,const CheckpointLoadWorkerExit&)noexcept;
 static void BeforeCallback(const CheckpointLoadWorkerFrame*,void*)noexcept;
 static void AfterCallback(const CheckpointLoadWorkerFrame*,void*)noexcept;
 static void FinallyCallback(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*)noexcept;
private:struct Impl;Impl*p_;
};
}
