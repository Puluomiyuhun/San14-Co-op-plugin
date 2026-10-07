#include "checkpoint_ready_input_gate.h"
#include <intrin.h>
#include <new>
#include <cstring>
namespace checkpoint_ready_input {
namespace {
struct Lock{SRWLOCK&l;explicit Lock(SRWLOCK&v):l(v){AcquireSRWLockExclusive(&l);}~Lock(){ReleaseSRWLockExclusive(&l);}};
bool same(const ph::Binding&a,const ph::Binding&b){return a.native.attempt==b.native.attempt&&a.native.attachment==b.native.attachment&&a.native.owner_generation==b.native.owner_generation&&a.period==b.period&&a.epoch==b.epoch&&a.room_input_digest==b.room_input_digest;}
struct Scope{Gate*gate=nullptr;Scope*previous=nullptr;std::uint64_t call=0,game=0;DWORD thread=0;bool claimed=false,entered=false,returned=false;};thread_local Scope*top=nullptr;
SRWLOCK fallbackLock=SRWLOCK_INIT;Original uiFallback=nullptr,panelFallback=nullptr;
}
struct Gate::Impl {
 Config config{};Report report{};SRWLOCK lock=SRWLOCK_INIT;bool initialized=false;
 void stop(Error e){report.error=e;report.stopped=true;report.requested=true;config.user->Disconnect();}
 bool current(Scope*s){CheckpointLoadWorkerOwner o{};return s&&s->claimed&&s->thread==GetCurrentThreadId()&&config.current_owner(&o)&&o.slot==2&&o.token==config.binding.native.owner_generation&&o.call_id==s->call&&o.thread_id==s->thread&&o.current_depth==o.owner_depth;}
 bool inspect(dp::Source&source){if(!config.sample(config.context,source)||!same(source.admission.binding,config.binding)||!same(source.reward.binding,config.binding)||source.reward.base!=config.base||source.admission.pending.profile_base!=config.base)return false;ph::pd::Adapter p;if(p.Bind(source.admission.pending)!=ph::pd::Error::None)return false;const auto r=p.InspectCurrent(config.binding.native);return r.error==ph::pd::Error::None&&r.decision==ph::pd::Decision::QuiescentObserved&&r.stack_count==5&&r.user_phase==2;}
};
Gate::Gate():p_(new(std::nothrow)Impl){}Gate::~Gate(){delete p_;}
bool ConfigureFallbacks(Original ui,Original panel)noexcept{Lock l(fallbackLock);if(!ui||!panel||uiFallback||panelFallback)return false;uiFallback=ui;panelFallback=panel;return true;}
bool Gate::Initialize(const Config&c)noexcept{if(!p_||p_->initialized||!c.base||!c.user||!c.game||!c.global_ui||!c.panel||!c.claim||!c.current_owner||!c.sample||!c.binding.native.owner_generation)return false;
#ifndef CHECKPOINT_READY_INPUT_OWNED_FIXTURE
 if(std::uintptr_t(c.game)!=c.base+0x3F8140||std::uintptr_t(c.global_ui)!=c.base+0x1AC3C0||std::uintptr_t(c.panel)!=c.base+0x3FA820)return false;
#endif
 {Lock l(fallbackLock);if(uiFallback!=c.global_ui||panelFallback!=c.panel)return false;}p_->config=c;p_->initialized=true;return true;}
bool Gate::Request(const ph::Binding&b,dp::Action op,std::uint64_t action)noexcept{if(!p_)return false;auto&s=*p_;Lock l(s.lock);if(!s.initialized||!same(b,s.config.binding)||s.report.stopped||action<=s.report.action)return false;
 // Actual User dispatcher request precedes this parent-consumer request. On
 // failure no room acknowledgment or consumer suppression receipt is issued.
 if(!s.config.user->Request(b,op,action))return false;s.report.action=action;
 if(op==dp::Action::Release)s.report.release_pending=true;else s.report.requested=true;return true;}
void Gate::Disconnect()noexcept{if(p_){Lock l(p_->lock);p_->stop(Error::Stopped);}}
Report Gate::Snapshot()noexcept{if(!p_)return{};Lock l(p_->lock);return p_->report;}
void Gate::Before(const CheckpointLoadWorkerFrame&f)noexcept{if(!p_||!p_->initialized)return;auto&s=*p_;auto*v=new(std::nothrow)Scope;if(!v){Lock l(s.lock);s.stop(Error::Scope);return;}v->gate=this;v->previous=top;v->call=f.call_id;v->thread=f.thread_id;v->game=f.args[0];top=v;
 CheckpointLoadWorkerOwner prior{};bool eligible=f.slot==2&&f.call_id&&f.thread_id==GetCurrentThreadId()&&f.caller_entry_rsp;
 bool inherited=eligible&&s.config.current_owner(&prior)&&prior.slot==2&&prior.call_id==f.call_id&&prior.token==s.config.binding.native.owner_generation&&prior.thread_id==f.thread_id&&prior.owner_depth==prior.current_depth;
 v->claimed=eligible&&(inherited||s.config.claim(&f,s.config.binding.native.owner_generation));{Lock l(s.lock);++s.report.game_entries;++s.report.active_game;if(!v->claimed||s.report.active_game!=1)s.stop(Error::Scope);}
}
std::uint64_t Gate::Game(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){if(!p_||!p_->initialized)return 0;auto&s=*p_;auto*v=top;bool valid=v&&v->gate==this&&!v->entered&&v->game==a&&s.current(v);if(valid)v->entered=true;else{Lock l(s.lock);s.stop(Error::Scope);}
 try{auto result=s.config.game(a,b,c,d);if(valid)v->returned=true;return result;}catch(...){Lock l(s.lock);++s.report.abnormal;s.stop(Error::Exception);throw;}}
std::uint64_t Gate::Consumer(bool ui,std::uintptr_t caller,std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){auto&s=*p_;auto*v=top;bool hold=false;{Lock l(s.lock);hold=s.report.requested;}
 auto original=ui?s.config.global_ui:s.config.panel;std::uintptr_t expected=s.config.base+(ui?0x3F85F6:0x3F860B);
#ifdef CHECKPOINT_READY_INPUT_OWNED_FIXTURE
 expected=ui?s.config.fixture_global_return:s.config.fixture_panel_return;
#endif
 bool owned=v&&v->gate==this&&v->entered&&s.current(v)&&caller==expected;
 try{if(hold&&owned){dp::Source source{};bool idle=s.inspect(source);bool object=ui?(a==s.config.base+0x1FC8410&&*reinterpret_cast<const std::uintptr_t*>(a)==s.config.base+0x1297CF8):(a==source.admission.pending.states[2]&&a==v->game);
   if(idle&&object){Lock l(s.lock);if(ui)++s.report.ui_suppressed;else++s.report.panel_suppressed;return 0;}
   {Lock l(s.lock);s.stop(Error::Pending);} // Unknown modal/transition retains native handling.
  }
  {Lock l(s.lock);if(hold&&!owned){++s.report.foreign_calls;s.stop(Error::Scope);}if(ui)++s.report.ui_forwarded;else++s.report.panel_forwarded;}
  return original(a,b,c,d);
 }catch(...){Lock l(s.lock);++s.report.abnormal;s.stop(Error::Exception);throw;}}
std::uint64_t Gate::GlobalUi(std::uintptr_t caller,std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return Consumer(true,caller,a,b,c,d);}
std::uint64_t Gate::Panel(std::uintptr_t caller,std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){return Consumer(false,caller,a,b,c,d);}
void Gate::Finally(const CheckpointLoadWorkerFrame&f,const CheckpointLoadWorkerExit&e)noexcept{if(!p_)return;auto&s=*p_;auto*v=top;if(!v||v->gate!=this||v->call!=f.call_id||v->thread!=GetCurrentThreadId()){Lock l(s.lock);s.stop(Error::Scope);return;}
 {Lock l(s.lock);++s.report.game_finally;if(s.report.active_game)--s.report.active_game;else s.stop(Error::Scope);if(e.abnormal||!v->returned)s.stop(Error::Exception);
  const auto user=s.config.user->Snapshot();if(s.report.release_pending&&!s.report.stopped&&!s.report.active_game&&!user.gate_requested&&!user.active&&!user.stopped){s.report.requested=false;s.report.release_pending=false;}
 }top=v->previous;delete v;
}
void Gate::BeforeCallback(const CheckpointLoadWorkerFrame*f,void*p)noexcept{if(f&&p)static_cast<Gate*>(p)->Before(*f);}void Gate::FinallyCallback(const CheckpointLoadWorkerFrame*f,const CheckpointLoadWorkerExit*e,void*p)noexcept{if(f&&e&&p)static_cast<Gate*>(p)->Finally(*f,*e);}
}
extern "C" __declspec(noinline) std::uint64_t ReadyInputGlobalUiEntry(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){using namespace checkpoint_ready_input;auto*v=top;if(v)return v->gate->GlobalUi(reinterpret_cast<std::uintptr_t>(_ReturnAddress()),a,b,c,d);Original f;{Lock l(fallbackLock);f=uiFallback;}return f?f(a,b,c,d):0;}
extern "C" __declspec(noinline) std::uint64_t ReadyInputPanelEntry(std::uint64_t a,std::uint64_t b,std::uint64_t c,std::uint64_t d){using namespace checkpoint_ready_input;auto*v=top;if(v)return v->gate->Panel(reinterpret_cast<std::uintptr_t>(_ReturnAddress()),a,b,c,d);Original f;{Lock l(fallbackLock);f=panelFallback;}return f?f(a,b,c,d):0;}
