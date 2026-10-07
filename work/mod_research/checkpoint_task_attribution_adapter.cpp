#include "checkpoint_task_attribution_core.h"
namespace checkpoint_task_attribution {
namespace {
struct Frame {Adapter* adapter=nullptr;const CheckpointLoadWorkerFrame* frame=nullptr;Selection selected{};bool routed=false,after=false;};
thread_local Frame frames[64];thread_local unsigned depth=0,overflow=0;
bool matches(const Selection& s,const CheckpointLoadWorkerFrame& f){
    if(f.slot<4)return unsigned(s.kind)==f.slot&&f.args[0]==s.state;
    if(f.slot==4)return unsigned(s.kind)>=unsigned(Kind::EmbeddedLoad)&&f.args[0]==s.callable;
    return false;
}
Frame* match(Adapter* a,const CheckpointLoadWorkerFrame* f){if(!depth||frames[depth-1].adapter!=a||frames[depth-1].frame!=f)return nullptr;return &frames[depth-1];}
}
bool Adapter::Initialize(Core& c) noexcept {if(InterlockedCompareExchange(&once_,1,0))return false;Report r{};c.Snapshot(r);if(!r.initialized){InterlockedExchange(&once_,-1);return false;}core_=&c;InterlockedExchange(&once_,2);return true;}
CheckpointPersistentBridgeConfig Adapter::Configuration(void* original) noexcept {CheckpointPersistentBridgeConfig c{};c.original=original;c.before=Before;c.after=After;c.finally=Finally;c.context=this;return c;}
checkpoint_persistent_route::Generation Adapter::ProxyGeneration(std::uint64_t id) noexcept {return {id,Before,After,Finally,this};}
std::uint64_t Adapter::ForwardedUnknown() noexcept{return InterlockedCompareExchange64(&unknown_,0,0);}
std::uint64_t Adapter::Faults() noexcept{return InterlockedCompareExchange64(&faults_,0,0);}
void Adapter::Before(const CheckpointLoadWorkerFrame* f,void* p){
    auto* a=static_cast<Adapter*>(p);if(!a||!f||!a->core_)return;
    if(depth==64||overflow){++overflow;InterlockedIncrement64(&a->faults_);return;}
    auto& e=frames[depth++];e={};e.adapter=a;e.frame=f;
    if(f->thread_id!=GetCurrentThreadId()||f->slot>=6||!f->call_id){InterlockedIncrement64(&a->faults_);return;}
    if(!a->core_->Select(e.selected)){InterlockedIncrement64(&a->unknown_);return;}
    if(f->slot==5){
        // FileRead has no root attribution. It inherits only an active owned
        // EmbeddedLoad callable frame on this same thread and creation serial.
        for(unsigned i=depth-1;i;i--){const auto& parent=frames[i-1];
            if(parent.adapter==a&&parent.routed&&parent.frame->slot==4&&parent.selected.kind==Kind::EmbeddedLoad&&
               parent.selected.serial==e.selected.serial&&parent.selected.callbacks.id==e.selected.callbacks.id){e.routed=true;break;}}
    }else e.routed=matches(e.selected,*f);
    if(!e.routed){InterlockedIncrement64(&a->unknown_);return;}
    if(e.selected.callbacks.before)e.selected.callbacks.before(f,e.selected.callbacks.context);
}
void Adapter::After(const CheckpointLoadWorkerFrame* f,void* p){
    auto* a=static_cast<Adapter*>(p);if(!a||overflow)return;auto* e=match(a,f);
    if(!e||e->after||f->thread_id!=GetCurrentThreadId()){InterlockedIncrement64(&a->faults_);return;}
    e->after=true;if(e->routed&&e->selected.callbacks.after)e->selected.callbacks.after(f,e->selected.callbacks.context);
}
void Adapter::Finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){
    auto* a=static_cast<Adapter*>(p);if(!a)return;if(overflow){--overflow;return;}auto* e=match(a,f);
    if(!e){InterlockedIncrement64(&a->faults_);return;}
    __try {if(e->routed&&e->selected.callbacks.finally)e->selected.callbacks.finally(f,x,e->selected.callbacks.context);}
    __finally {*e={};--depth;}
}
}
