#pragma once
#include "checkpoint_forward_planning_observer.h"
// V2 changes only address-reuse handling. Existing POD layout and Point ABI
// remain identical; all objects still belong to a single retained attempt.
namespace checkpoint_forward_planning_observer_v2 {
using Point=checkpoint_forward_planning_observer::Point;
using Error=checkpoint_forward_planning_observer::Error;
using Config=checkpoint_forward_planning_observer::Config;
using Sample=checkpoint_forward_planning_observer::Sample;
using Report=checkpoint_forward_planning_observer::Report;
using Observer=checkpoint_forward_planning_observer::Observer;
bool Initialize(Observer&,const Config&) noexcept;
void Before(const CheckpointPushFrame*,void*) noexcept;
void After(const CheckpointPushFrame*,void*) noexcept;
void Snapshot(Observer&,Report&) noexcept;
}
