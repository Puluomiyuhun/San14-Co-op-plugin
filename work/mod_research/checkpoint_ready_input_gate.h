#pragma once
#include "checkpoint_planning_dispatcher.h"
namespace checkpoint_ready_input {
namespace dp=checkpoint_planning_dispatcher;namespace ph=checkpoint_planning_hold;
using Original=dp::Original;
enum class Error:unsigned {None,Config,Binding,Scope,Pending,Exception,Stopped};
struct Config {
 ph::Binding binding{};std::uintptr_t base=0;dp::Dispatcher*user=nullptr;
 Original game=nullptr,global_ui=nullptr,panel=nullptr;
 int(*claim)(const CheckpointLoadWorkerFrame*,std::uint64_t)noexcept=nullptr;
 int(*current_owner)(CheckpointLoadWorkerOwner*)noexcept=nullptr;
 bool(*sample)(void*,dp::Source&)=nullptr;void*context=nullptr;
#ifdef CHECKPOINT_READY_INPUT_OWNED_FIXTURE
 std::uintptr_t fixture_global_return=0,fixture_panel_return=0;
#endif
};
struct Report {
 Error error=Error::None;std::uint64_t action=0,game_entries=0,active_game=0,game_finally=0;
 std::uint64_t ui_forwarded=0,ui_suppressed=0,panel_forwarded=0,panel_suppressed=0,foreign_calls=0,abnormal=0;
 bool requested=false,release_pending=false,stopped=false;
 // This first version is intentionally only a controlled, idle-planning smoke.
 bool full_input_hold=false,room_ready_eligible=false,all_gameplay_consumers_covered=false,installed=false;
};
class Gate final {
public:
 Gate();~Gate();Gate(const Gate&)=delete;Gate&operator=(const Gate&)=delete;
 bool Initialize(const Config&)noexcept;
 bool Request(const ph::Binding&,dp::Action,std::uint64_t)noexcept;
 void Disconnect()noexcept;
 Report Snapshot()noexcept;
 void Before(const CheckpointLoadWorkerFrame&)noexcept;
 std::uint64_t Game(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
 void Finally(const CheckpointLoadWorkerFrame&,const CheckpointLoadWorkerExit&)noexcept;
 std::uint64_t GlobalUi(std::uintptr_t caller,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
 std::uint64_t Panel(std::uintptr_t caller,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
 static void BeforeCallback(const CheckpointLoadWorkerFrame*,void*)noexcept;
 static void FinallyCallback(const CheckpointLoadWorkerFrame*,const CheckpointLoadWorkerExit*,void*)noexcept;
private:struct Impl;Impl*p_=nullptr;std::uint64_t Consumer(bool,std::uintptr_t,std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
};
// Parent Game bridge owns TLS route. Consumer entry shims capture real native
// return addresses, never a packet-provided caller. Unrouted calls require a
// retained globally configured original: ConfigureFallbacks is once-only.
bool ConfigureFallbacks(Original global_ui,Original panel)noexcept;
}
extern "C" std::uint64_t ReadyInputGlobalUiEntry(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
extern "C" std::uint64_t ReadyInputPanelEntry(std::uint64_t,std::uint64_t,std::uint64_t,std::uint64_t);
