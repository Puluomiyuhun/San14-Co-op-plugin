#include "checkpoint_complete_live_owner.h"
#include <cstdio>
using namespace checkpoint_complete_live_owner;
int main(){
    std::printf("{\"config_size\":%zu,\"report_size\":%zu,\"description_size\":%zu,\"value_count\":%u,\"module_size\":%zu,\"endpoint_size\":%zu,\"config\":{",sizeof(Config),sizeof(Report),sizeof(Description),unsigned(Value::Count),sizeof(checkpoint_live_storage_binding::ModuleApproval),sizeof(checkpoint_live_storage_binding::Endpoint));
#define C(x) std::printf("\"" #x "\":%zu,",offsetof(Config,x));
    C(pid) C(birth) C(base) C(attempt) C(epoch) C(generation) C(attachment) C(ownerBinding) C(nonce) C(gameSha256) C(states) C(root) C(world) C(cache) C(keyboard) C(toolbar) C(panel) C(stack) C(stackCapacity) C(queue) C(queueCapacity) C(rng) C(expectedMode) C(helperDeadlineMs) C(localPath) C(installIntent) C(requestIntent) C(identityIntent) C(storageModules) C(storageModuleCount) C(contextInit) C(exists) C(fileSize) C(read) C(ownedReadBridge) C(storage) C(storageVtable) C(storageCounter) C(cachedGeneration)
#undef C
    std::printf("\"contextCode\":%zu},\"report\":{",offsetof(Config,contextCode));
#define R(x) std::printf("\"" #x "\":%zu,",offsetof(Report,x));
    R(sequence) R(attempt) R(epoch) R(value) R(hooks) R(bridges) R(bytesReceipt) R(lifecycleReceipt) R(identityReceipt) R(hardwareReceipt) R(requestReadSha) R(planningAttempt) R(planningEpoch) R(planningUserCall) R(planningIdentityCall) R(planningCompletedCall) R(planningUser) R(planningBeforeSample) R(planningAfterSample) R(requestStage)
#undef R
    std::printf("\"planningFailure\":%zu}}\n",offsetof(Report,planningFailure));return 0;
}
