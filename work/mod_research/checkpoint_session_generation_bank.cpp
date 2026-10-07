#include "checkpoint_session_generation_bank.h"
#include <cstring>
namespace sg=checkpoint_session_generation;
namespace {
sg::ns::Session session;
sg::Description description{};
volatile LONG once=0;
bool initialize(const sg::Identity* id,const sg::ns::Config* input) noexcept {
    if(!id||!input||InterlockedCompareExchange(&once,1,0))return false;
    if(!id->generation||!id->attempt||id->attempt!=input->request.boundary.attempt||
       std::memcmp(id->attachment,input->request.ownerBinding,32))return false;
    auto c=*input;
    void* bridges[]={reinterpret_cast<void*>(&CheckpointLoadDispatchBridge0),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge1),
        reinterpret_cast<void*>(&CheckpointLoadDispatchBridge2),reinterpret_cast<void*>(&CheckpointLoadDispatchBridge3),
        reinterpret_cast<void*>(&CheckpointLoadWorkerBridge0),reinterpret_cast<void*>(&CheckpointLoadWorkerBridge1)};
    for(unsigned i=0;i<6;++i)c.hooks[i].hook=bridges[i];
    if(!session.Initialize(c))return false;
    description.identity=*id;description.session=&session;
    std::memcpy(description.hooks,c.hooks,sizeof description.hooks);
    InterlockedExchange(&once,2);return true;
}
bool describe(sg::Description* out) noexcept {if(!out||InterlockedCompareExchange(&once,0,0)!=2)return false;*out=description;return true;}
bool arm() noexcept {return session.ArmHooks();}
void stop() noexcept {session.Stop();}
bool restore() noexcept {return session.RestoreBeforeCommit();}
void snapshot(sg::ns::Report* r) noexcept {if(r)session.Snapshot(*r);}
bool bind(const sg::ns::QueueReceipt* r) noexcept {return r&&session.BindQueuedMenu(*r);}
const sg::BankApi api{sizeof(sg::BankApi),sg::BankAbi,sizeof(sg::ns::Config),sizeof(sg::ns::Report),initialize,describe,arm,stop,restore,snapshot,bind};
}
extern "C" __declspec(dllexport) const sg::BankApi* CheckpointSessionGenerationGetApi() noexcept {return &api;}
#ifdef CHECKPOINT_SESSION_GENERATION_FIXTURE
// Fixture-only caller label adaptation; never exported by a production build.
extern "C" void CheckpointLoadDispatchBridgeInvoke(unsigned,CheckpointPushFrame*);
extern "C" __declspec(dllexport) void CheckpointSessionGenerationFixtureDispatch(unsigned slot,CheckpointPushFrame* f){CheckpointLoadDispatchBridgeInvoke(slot,f);}
#endif
