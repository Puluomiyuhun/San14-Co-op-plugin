#include "checkpoint_persistent_route_six_adapter.h"
namespace checkpoint_persistent_route {
CheckpointPersistentBridgeConfig SixAdapter::Configuration(void* original) noexcept {
    CheckpointPersistentBridgeConfig c{};c.original=original;c.before=Before;c.after=After;c.finally=Finally;c.context=this;return c;
}
bool SixAdapter::Claim(const CheckpointLoadWorkerFrame* f,std::uint64_t token) noexcept{return CheckpointPersistentClaim(f,token)==1;}
bool SixAdapter::CurrentOwner(CheckpointLoadWorkerOwner& o) noexcept{return CheckpointPersistentCurrentOwner(&o)==1;}
void SixAdapter::Before(const CheckpointLoadWorkerFrame* f,void* p){WorkerAdapter::Before(f,&static_cast<SixAdapter*>(p)->engine_);}
void SixAdapter::After(const CheckpointLoadWorkerFrame* f,void* p){WorkerAdapter::After(f,&static_cast<SixAdapter*>(p)->engine_);}
void SixAdapter::Finally(const CheckpointLoadWorkerFrame* f,const CheckpointLoadWorkerExit* x,void* p){WorkerAdapter::Finally(f,x,&static_cast<SixAdapter*>(p)->engine_);}
}
