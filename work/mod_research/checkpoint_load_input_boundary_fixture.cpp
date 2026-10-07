#include "checkpoint_load_input_boundary_fixture_layout.h"
#include <cstdio>
#include <vector>
namespace core=checkpoint_load_input_boundary;
using L=checkpoint_load_input_boundary_fixture::Layout;
struct Test {const char* name;void(*edit)(L&);bool pass=false;};
int main(){
    const Test tests[]={
        {"GameBefore_valid",[](L&){},true},
        {"MenuAfter_valid",[](L&x){x.setStage(core::Stage::MenuAfter);},true},
        {"wrong_thread",[](L&x){++x.call.thread;}},
        {"wrong_pair_call",[](L&x){++x.call.pairedCallId;}},
        {"wrong_pair_thread",[](L&x){++x.call.pairedThread;}},
        {"wrong_pair_worker",[](L&x){x.call.pairedWorker+=0x1000;}},
        {"caller_mismatch",[](L&x){L::put<std::uintptr_t>(x.call.callerEntryRsp,x.config.base+0x50B784);}},
        {"argument_mismatch",[](L&x){++x.call.args[2];}},
        {"root_worker_not_drained",[](L&x){L::put<std::uintptr_t>(x.config.states[0]+0x50,x.worker+0x800);}},
        {"user_worker_not_drained",[](L&x){L::put<std::uintptr_t>(x.config.states[4]+0x50,x.worker+0x800);}},
        {"menu_worker_not_drained",[](L&x){L::put<std::uintptr_t>(x.config.menu+0x50,x.worker+0x800);}},
        {"yielded_current",[](L&x){L::put<DWORD>(x.worker+0x78,1);}},
        {"completed_current",[](L&x){L::put<DWORD>(x.worker+0x58,1);}},
        {"stopping_current",[](L&x){L::put<DWORD>(x.worker+0x5C,1);}},
        {"native_tid_mismatch",[](L&x){L::put<DWORD>(x.handle+0x10,GetCurrentThreadId()+1);}},
        {"iterator_not_official",[](L&x){L::put<std::uintptr_t>(x.iterator,x.stack+5*8);}},
        {"wrong_callable_vtable",[](L&x){L::put<std::uintptr_t>(x.worker+0x18,x.config.base+0x12F2448);}},
        {"wrong_call_stage",[](L&x){x.call.originalReturned=true;}},
        {"not_six_states",[](L&x){L::put<std::uint64_t>(x.manager+0x10,5);}},
        {"foreign_current",[](L&x){L::put<std::uintptr_t>(x.manager+0x48,x.config.menu);}},
        {"queue_pending",[](L&x){L::put<std::uint64_t>(x.manager+0x30,1);}},
        {"menu_selected",[](L&x){L::put<std::int32_t>(x.list+0x170,63);}},
        {"toolbar_command",[](L&x){L::put<std::int32_t>(x.toolbar+0x88,4);}},
        {"advance_game",[](L&x){L::put<DWORD>(x.config.states[2]+0x47C,1);}},
        {"advance_panel",[](L&x){L::put<DWORD>(x.panel+0x1B0,1);}},
        {"control_not_paused",[](L&x){L::put<DWORD>(x.config.base+0x1A38EC8+0x28,0);}},
        {"cursor_enabled",[](L&x){L::put<DWORD>(x.config.base+0x19E7510+0x13C,1);}},
        {"coordinator_input_enabled",[](L&x){L::put<std::uint16_t>(x.config.base+0x19E7690,0x27);}},
        {"coordinator_other_flags_allowed",[](L&x){L::put<std::uint16_t>(x.config.base+0x19E7690,0x26);},true},
        {"coordinator_callback_still_live",[](L&x){L::put<std::uintptr_t>(x.config.base+0x19E7690+0x328,x.toolbar);}},
        {"state_disabled",[](L&x){L::put<DWORD>(x.config.states[4]+0x68,1);}},
        {"current_wrong_dispatch_phase",[](L&x){L::put<DWORD>(x.config.states[2]+0x6C,4);}},
        {"pending_preexisting",[](L&x){L::put<std::int32_t>(x.config.cache+0x3EC,34);}},
        {"save_mode",[](L&x){L::put<DWORD>(x.config.cache+8,1);}},
        {"rng_changed",[](L&x){L::put<DWORD>(x.config.base+0x18EB8B0,4);}},
        {"date_changed",[](L&x){L::put<std::uint8_t>(x.config.world+0x37,21);}},
        {"normalized_button",[](L&x){L::put<DWORD>(x.config.base+0x1FCA0A0+0x14,0x10);}},
        {"special_key_repeat",[](L&x){L::put<DWORD>(x.config.base+0x1FCA0A0+0x68,1);}},
        {"mouse_button",[](L&x){L::put<DWORD>(x.config.base+0x19E1D30+0xC,1);}},
        {"raw_modifier",[](L&x){L::put<DWORD>(x.config.keyboard+0x50,0x22);}},
        {"raw_key_down",[](L&x){L::put<unsigned char>(x.config.keyboard+0x158+0x1C,0x80);}},
        {"key_buffer_pending",[](L&x){L::put<DWORD>(x.config.keyboard+0x54,1);}},
        {"input_index_invalid",[](L&x){L::put<DWORD>(x.config.base+0x1FCA0A0+8,2);}},
        {"optional_service_panel_clear",[](L&x){L::put<std::uintptr_t>(x.config.base+0x1FC8488,x.handle);},true},
        {"optional_service_world_minus1",[](L&x){L::put<std::uintptr_t>(x.config.base+0x1FC8488,x.handle);L::put<std::int8_t>(x.config.world+0xBC,-1);L::put<DWORD>(x.panel+0x1F4,1);},true},
        {"optional_service_modal_pending",[](L&x){L::put<std::uintptr_t>(x.config.base+0x1FC8488,x.handle);L::put<DWORD>(x.panel+0x1F4,1);}},
        {"keyboard_noaccess",[](L&x){DWORD old=0;VirtualProtect(reinterpret_cast<void*>(x.config.keyboard),0x1000,PAGE_NOACCESS,&old);}}
    };
    unsigned failed=0,n=0;std::printf("{\"cases\":[");
    for(const auto& t:tests){L x;if(!x.initialize())return 2;t.edit(x);core::Report r{};
        bool got=core::Inspect(x.config,x.call,r);bool okay=got==t.pass&&r.passed==got&&
            !r.globalPauseProved&&!r.allInputChannelsProved&&r.checkCount<=160;
        if(!got&&r.error==core::Error::None)okay=false;
        if(!okay)++failed;const core::Check* check=r.checkCount?&r.checks[r.checkCount-1]:nullptr;
        std::printf("%s{\"name\":\"%s\",\"result\":\"%s\",\"accepted\":%s,\"checks\":%u,\"error\":%u,\"exception\":%lu,\"last_field\":\"%s\"}",
            n++?",":"",t.name,okay?"PASS":"FAIL",got?"true":"false",r.checkCount,unsigned(r.error),r.exceptionCode,check?check->field:"");}
    // A positive check must leave its entire synthetic arena/image byte-exact.
    {L x;if(!x.initialize())return 3;std::vector<unsigned char> beforeImage(0x2200000),beforeArena(0x100000);
        std::memcpy(beforeImage.data(),x.image,beforeImage.size());std::memcpy(beforeArena.data(),x.arena,beforeArena.size());
        core::Report r{};bool okay=core::Inspect(x.config,x.call,r)&&
            !std::memcmp(beforeImage.data(),x.image,beforeImage.size())&&!std::memcmp(beforeArena.data(),x.arena,beforeArena.size());
        if(!okay)++failed;++n;std::printf(",{\"name\":\"entire_fixture_memory_unchanged\",\"result\":\"%s\"}",okay?"PASS":"FAIL");}
    std::printf("],\"total\":%u,\"failed\":%u,\"game_access\":false,\"result\":\"%s\"}\n",n,failed,failed?"FAIL":"PASS");
    return failed?1:0;
}
