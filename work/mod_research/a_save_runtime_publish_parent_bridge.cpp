#include "b_reload_parent_bridge.cpp"
#include "a_save_runtime_publish_evidence.h"
bool ASaveRuntimeParentCounters(a_save_runtime_wire::Counter*out)noexcept {
 if(!out)return false;for(unsigned i=0;i<2;++i){auto&s=slots[i];out[i]={uintptr_t(&s.started),uintptr_t(&s.active),get64(&s.started),get64(&s.active)};}return true;
}
