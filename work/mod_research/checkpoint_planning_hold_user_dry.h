#pragma once
#include "checkpoint_planning_hold_adapter.h"
namespace checkpoint_planning_hold_user_dry {
using Original=std::uint64_t(*)(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
struct Config {checkpoint_planning_hold::Context*hold=nullptr;Original original=nullptr;void(*owned_replay_pump)(void*)=nullptr;void*context=nullptr;bool request_owned_dry_skip=false;};
struct Report {std::uint64_t entries=0,forwarded=0,body_returned=0,skipped=0,replay_pumps=0,abnormal=0;bool native_body_returned_last=false,full_input_hold=false,production_skip_enabled=false;};
class Adapter final {
public:
    bool Initialize(const Config&) noexcept;
    std::uint64_t Invoke(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
    Report Snapshot()const noexcept{return report_;}
private:Config config_{};Report report_{};DWORD owner_=0;bool initialized_=false,inside_=false;
};
// Scoped original only for an already owned four-integer physical bridge.
// Production compilation rejects request_owned_dry_skip; no hooks installed.
}
