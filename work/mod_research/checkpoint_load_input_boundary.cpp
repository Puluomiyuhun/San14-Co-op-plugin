#include "checkpoint_load_input_boundary.h"
#include <cstring>
#include <initializer_list>

namespace checkpoint_load_input_boundary {
namespace {
struct Inspector {
    Report& r;
    bool check(const char* name,std::uintptr_t address,std::uint64_t got,std::uint64_t expected,
               unsigned size,bool ok,Error why=Error::Mismatch) noexcept {
        if(r.checkCount>=160){r.error=Error::Capacity;return false;}
        r.checks[r.checkCount++]={name,address,got,expected,size,ok?Error::None:why};
        if(!ok&&r.error==Error::None)r.error=why;
        return ok;
    }
    template<class T> bool read(const char* name,std::uintptr_t p,T& out) noexcept {
        __try {out=*reinterpret_cast<const T*>(p);return true;}
        __except(EXCEPTION_EXECUTE_HANDLER){r.exceptionCode=GetExceptionCode();
            return check(name,p,0,0,sizeof(T),false,Error::ReadFault);}
    }
    template<class T> bool eq(const char* name,std::uintptr_t p,T expected,Error why=Error::Mismatch) noexcept {
        T got{};return read(name,p,got)&&check(name,p,std::uint64_t(got),std::uint64_t(expected),sizeof(T),got==expected,why);
    }
    bool pointer(const char* name,std::uintptr_t p,std::uintptr_t& out) noexcept {
        return read(name,p,out)&&check(name,p,out,0,sizeof(out),out>=0x10000&&out<=0x00007FFFFFFFF000ULL,Error::Range);
    }
    bool zero(const char* name,std::uintptr_t p,unsigned n,unsigned char mask=0xFF) noexcept {
        // One aggregate success check; on failure record the exact offending byte.
        for(unsigned i=0;i<n;++i){unsigned char value=0;
            if(!read(name,p+i,value))return false;
            if(value&mask)return check(name,p+i,value,0,1,false,Error::InputPending);}
        return check(name,p,0,0,n,true);
    }
    bool name(std::uintptr_t p,const char* expected) noexcept {
        for(unsigned i=0;;++i){unsigned char got=0;if(!read("state.name",p+i,got))return false;
            if(got!=static_cast<unsigned char>(expected[i]))return check("state.name",p+i,got,expected[i],1,false);
            if(!expected[i])break;}
        return check("state.name",p,1,1,0,true);
    }
};
bool body(const Config& c,const Call& call,Report& r) noexcept {
    Inspector q{r};r.stage=call.stage;r.attempt=c.attempt;r.callId=call.callId;r.thread=call.thread;
    const bool menu=call.stage==Stage::MenuAfter;
    if(!q.check("stage",0,unsigned(call.stage),0,4,menu||call.stage==Stage::GameBefore,Error::Input)||
       !q.check("config.binding",0,c.attempt,0,8,c.base&&c.attempt&&c.menu&&c.root&&c.world&&c.cache&&c.keyboard,Error::Input)||
       !q.check("call.pair",0,call.callId,call.pairedCallId,8,call.callId&&call.callId==call.pairedCallId,Error::Input)||
       !q.check("call.thread",0,call.thread,GetCurrentThreadId(),4,call.thread==GetCurrentThreadId()&&call.thread==call.pairedThread,Error::Input)||
       !q.check("call.returned",0,call.originalReturned,menu,1,call.originalReturned==menu,Error::Input))return false;
    r.current=menu?c.menu:c.states[2];
    if(!q.check("call.this",0,call.args[0],r.current,8,call.args[0]==r.current)||
       !q.eq<std::uintptr_t>("call.native_return",call.callerEntryRsp,c.base+0x50B785))return false;
    const auto manager=c.base+0x19E7310;
    if(!q.eq<std::uint64_t>("manager.stack_count",manager+0x10,6)||
       !q.eq<std::uint64_t>("manager.queue_count",manager+0x30,0,Error::InputPending)||
       !q.eq<std::uintptr_t>("manager.current",manager+0x48,r.current)||
       !q.pointer("manager.stack",manager+0x20,r.stack))return false;
    const char* names[]={"CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState","CSaveLoadState"};
    for(unsigned i=0;i<6;++i){const auto expected=i<5?c.states[i]:c.menu;
        if(!q.check("state.nonnull",0,expected,0,8,expected>=0x10000,Error::Input)||
           !q.eq<std::uintptr_t>("stack.state",r.stack+i*8,expected)||!q.name(expected+0x70,names[i])||
           !q.eq<DWORD>("state.disabled",expected+0x68,0,Error::InputPending))return false;
        if(!q.read("state.worker",expected+0x50,r.stateWorkers[i]))return false;
        if(expected!=r.current&&!q.check("noncurrent.worker_zero",expected+0x50,r.stateWorkers[i],0,8,
                !r.stateWorkers[i],Error::NotQuiescent))return false;
    }
    r.worker=r.stateWorkers[menu?5:2];
    if(!q.eq<DWORD>("current.dispatch_phase",r.current+0x6C,3)||
       !q.check("current.worker_pair",r.current+0x50,r.worker,call.pairedWorker,8,
                r.worker>=0x10000&&r.worker==call.pairedWorker,Error::NotQuiescent)||
       !q.eq<DWORD>("current.worker_yield",r.worker+0x78,0,Error::NotQuiescent)||
       !q.eq<DWORD>("current.worker_done",r.worker+0x58,0,Error::NotQuiescent)||
       !q.eq<DWORD>("current.worker_stop",r.worker+0x5C,0,Error::NotQuiescent)||
       !q.pointer("current.callable",r.worker+0x50,r.callable)||
       !q.eq<std::uintptr_t>("callable.vtable",r.callable,c.base+0x12F2440)||
       !q.eq<std::uintptr_t>("callable.original",c.base+0x12F2440+0x10,c.base+0x50B730))return false;
    std::uintptr_t iterator=0,slot=0,nativeHandle=0;
    if(!q.pointer("callable.iterator",r.callable+8,iterator)||
       !q.pointer("callable.state_slot",iterator,slot)||
       !q.check("callable.slot_is_formal",iterator,slot,r.stack+(menu?5:2)*8,8,slot==r.stack+(menu?5:2)*8)||
       !q.eq<std::uintptr_t>("callable.slot_this",slot,r.current)||
       !q.pointer("worker.native_handle",r.worker+8,nativeHandle)||
       !q.eq<DWORD>("worker.native_thread",nativeHandle+0x10,call.thread))return false;
    for(unsigned i=1;i<4;++i)if(!q.eq<std::uint64_t>("callable.original_argument",r.callable+8+i*8,call.args[i]))return false;
    const auto user=c.states[4],game=c.states[2];
    const auto coordinator=c.base+0x19E7690;std::uint16_t coordinatorFlags=0;
    if(!q.read("native.coordinator_flags",coordinator,coordinatorFlags)||
       !q.check("native.coordinator_input_bit",coordinator,coordinatorFlags,0,2,(coordinatorFlags&1)==0)||
       !q.eq<std::uintptr_t>("native.coordinator_callback_2B0",coordinator+0x2E8,0)||
       !q.eq<std::uintptr_t>("native.coordinator_callback_2F0",coordinator+0x328,0)||
       !q.eq<std::uintptr_t>("native.coordinator_callback_330",coordinator+0x368,0))return false;
    if(!q.eq<std::uintptr_t>("Game.vtable",game,c.base+0x12CC9B8)||
       !q.eq<std::uintptr_t>("User.vtable",user,c.base+0x12CC4A8)||
       !q.eq<std::uintptr_t>("SaveLoad.vtable",c.menu,c.base+0x12DB4C0)||
       !q.eq<DWORD>("User.phase",user+0x470,2)||
       !q.eq<DWORD>("Game.transition",game+0x474,0,Error::InputPending)||
       !q.eq<DWORD>("Game.load_queued",game+0x478,0,Error::InputPending)||
       !q.eq<DWORD>("Game.advance",game+0x47C,0,Error::InputPending)||
       !q.eq<DWORD>("native.control_pause",c.base+0x1A38EC8+0x28,1)||
       !q.eq<DWORD>("native.cursor_enabled",c.base+0x19E7510+0x13C,0)||
       !q.eq<std::uintptr_t>("SaveLoad.return_callback",c.menu+0x48,0)||
       !q.pointer("SaveLoad.list",c.menu+0x470,r.list)||
       !q.pointer("SaveLoad.dialog",c.menu+0x478,r.dialog)||
       !q.eq<std::uintptr_t>("SaveLoad.list_vtable",r.list,c.base+0x12DBA18)||
       !q.eq<std::int32_t>("SaveLoad.selection",r.list+0x170,-1,Error::InputPending))return false;
    std::uintptr_t toolbar=0,panel=0,special=0,optional=0;
    if(!q.pointer("User.toolbar",user+0x478,toolbar)||
       !q.eq<std::int32_t>("User.menu_command",toolbar+0x88,-1,Error::InputPending)||
       !q.pointer("Game.panel",game+0x480,panel)||
       !q.eq<DWORD>("Game.panel_advance",panel+0x1B0,0,Error::InputPending))return false;
    for(auto off:{0x4A8,0x4B0,0x4B8})if(!q.eq<std::uintptr_t>("User.selection",user+off,0,Error::InputPending))return false;
    if(!q.read("special.context",c.base+0x201EC70,special)||
       (special&&!q.eq<DWORD>("special.active",special,0))||
       !q.read("Game.optional_service",c.base+0x1FC8488,optional))return false;
    // Actual3F819C..3F81EE only enters the optional modal branch if service is
    // present, native1C0CD0(world+BC) is not-1 AND panel+1F4 is nonzero.
    if(optional){std::int8_t kind=0;DWORD panelRequest=0;
        if(!q.read("Game.optional_world_kind",c.world+0xBC,kind)||
           !q.read("Game.optional_panel_request",panel+0x1F4,panelRequest)||
           !q.check("Game.optional_branch_inactive",panel+0x1F4,panelRequest,0,4,
                    kind==-1||panelRequest==0,Error::InputPending))return false;}
    if(!q.eq<std::uintptr_t>("root.binding",c.base+0x1FCA1E0,c.root)||
       !q.eq<std::uintptr_t>("world.binding",c.root+0x85130,c.world)||
       !q.eq<std::uintptr_t>("cache.binding",c.base+0x2025318,c.cache)||
       !q.eq<DWORD>("cache.mode",c.cache+8,0)||
       !q.eq<DWORD>("cache.secondary",c.cache+0x3F0,0)||
       !q.eq<std::int32_t>("cache.pending",c.cache+0x3EC,-1,Error::InputPending)||
       !q.eq<std::uint16_t>("world.year",c.world+0x34,c.year)||
       !q.eq<std::uint8_t>("world.month",c.world+0x36,c.month)||
       !q.eq<std::uint8_t>("world.day",c.world+0x37,c.day)||
       !q.eq<std::uint8_t>("world.player",c.world+0x3A,c.force)||
       !q.eq<DWORD>("world.planning",c.world+0x40,1)||
       !q.eq<DWORD>("global_rng",c.base+0x18EB8B0,c.expectedRng))return false;
    const auto input=c.base+0x1FCA0A0,mouse=c.base+0x19E1D30;
    if(!q.eq<std::uintptr_t>("input.keyboard_binding",input,c.keyboard))return false;
    DWORD index=0,previous=0;
    if(!q.read("input.index",input+8,index)||!q.read("input.previous_index",input+12,previous)||
       !q.check("input.indices",input+8,(std::uint64_t(previous)<<32)|index,0,8,index<=1&&previous<=1,Error::Range)||
       !q.zero("input.button_buffers",input+0x14,8)||
       !q.zero("input.repeat_latches",input+0x1C,5)||
       !q.zero("input.axes_and_repeats",input+0x24,0x34)||
       !q.zero("input.key_buffers_and_repeat",input+0x58,13)||
       !q.zero("input.special_key_repeats",input+0x68,16)||
       !q.read("mouse.buffer_index",mouse,index)||
       !q.check("mouse.buffer_index",mouse,index,0,4,index<=1,Error::Range)||
       !q.zero("mouse.button_buffers",mouse+0xC,24)||
       !q.zero("mouse.pending_gesture",mouse+0x24,15)||
       !q.zero("mouse.pending_repeat",mouse+0x60,4)||
       !q.zero("keyboard.modifiers",c.keyboard+0x50,4)||
       !q.eq<DWORD>("keyboard.buffer_count",c.keyboard+0x54,0,Error::InputPending)||
       !q.zero("keyboard.held_key_highbits",c.keyboard+0x158,256,0x80))return false;
    // Re-read ownership after the longer input scan. This detects observed
    // changes; it is not a lock or an all-thread memory snapshot.
    if(!q.eq<std::uint64_t>("final.stack_count",manager+0x10,6)||
       !q.eq<std::uintptr_t>("final.current",manager+0x48,r.current)||
       !q.eq<std::uintptr_t>("final.current_worker",r.current+0x50,r.worker)||
       !q.eq<DWORD>("final.worker_yield",r.worker+0x78,0,Error::NotQuiescent)||
       !q.eq<std::uint64_t>("final.queue_count",manager+0x30,0,Error::InputPending)||
       !q.eq<std::int32_t>("final.pending",c.cache+0x3EC,-1,Error::InputPending)||
       !q.eq<std::int32_t>("final.menu_selection",r.list+0x170,-1,Error::InputPending))return false;
    r.passed=true;return true;
}
}
bool Inspect(const Config& config,const Call& call,Report& report) noexcept {
    report=Report{};
    __try {const Config c=config;const Call f=call;return body(c,f,report);}
    __except(EXCEPTION_EXECUTE_HANDLER){report.exceptionCode=GetExceptionCode();report.error=Error::ReadFault;return false;}
}
}
