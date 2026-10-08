#pragma once
#include "b_reload_root_activation.h"
#include "checkpoint_load_worker_bridge.h"
// Startup-only successor. It prepares one exact pool-initialization source;
// publication requires a separately proved stopped startup lifecycle.
namespace b_reload_lifecycle {
using Config=b_reload_root_activation::Config;
enum class Error:unsigned {None,Config,Source,AlreadyRunning,Relay,Bridge,NotArmed,Order,Activation,Exception,Stopped};
struct Plan {uintptr_t address=0,relay=0;unsigned char before[5]{},after[5]{};};
struct Report {Error error=Error::None;unsigned initialized=0,armed=0,entered=0,returned=0,finally=0,abnormal=0,coldPools=0,unownedTasks=0;Plan plan{};bool startupInstaller=false,runningPoolTakeover=false,roomReady=false;};
bool Initialize(const Config&) noexcept;
bool PreparedPlan(Plan&) noexcept;
bool Arm() noexcept;
void Stop() noexcept;
void Snapshot(Report&) noexcept;
// Internal After callback; rejects callers without this bank's actual PE owner.
bool RegisterColdPool(const CheckpointLoadWorkerFrame*) noexcept;
void WorkerStatistics(unsigned&registered,unsigned&unowned) noexcept;
}
